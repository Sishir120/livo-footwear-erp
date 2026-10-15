from decimal import Decimal
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from pydantic import BaseModel, Field

from app.core.sequence import generate_document_number
from app.core.nepali_date import ad_to_bs_str
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.sales import Client, SalesOrder, Payment
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry, PaymentAllocation
from app.db.repository import TenantRepository

router = APIRouter(prefix="/receivables", tags=["Accounts Receivable Subledger"])


class InvoiceAllocationItem(BaseModel):
    invoice_id: int
    amount_paisa: int = Field(..., gt=0, description="Amount allocated to this invoice in integer paisa")


class PaymentReceiptCreate(BaseModel):
    client_id: int
    amount_paisa: int = Field(..., gt=0, description="Total payment amount in integer paisa")
    payment_method: str = Field("CASH", description="'CASH' or 'BANK'")
    reference: Optional[str] = Field(None, max_length=64, description="Cheque / Voucher / Bank Ref")
    payment_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    notes: Optional[str] = Field(None, max_length=255)
    invoice_allocations: Optional[List[InvoiceAllocationItem]] = None


class DisputeTogglePayload(BaseModel):
    is_disputed: bool
    dispute_notes: Optional[str] = Field(None, max_length=255)


@router.get("/aging")
def get_ar_aging_report(
    as_of_date: Optional[str] = Query(None, description="As-of evaluation date YYYY-MM-DD"),
    client_id: Optional[int] = Query(None, description="Filter to a single client (optional)"),
    limit: int = Query(200, ge=1, le=1000, description="Max clients per page"),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes party-level accounts receivable aging matrix with statutory buckets.

    PERFORMANCE ARCHITECTURE (post C15.1 redesign):
    Aggregation is pushed into PostgreSQL/SQLite via SQL SUM/CASE expressions.
    Python receives only the per-client summary row, NOT every historical entry.
    Memory usage is O(clients_per_page), not O(total_receivable_entries).

    Buckets:
    - current_paisa: unpaid invoices 0-30 days overdue
    - days_31_60_paisa, days_61_90_paisa, over_90_paisa: aging buckets
    - total_due_paisa: net outstanding
    - unallocated_credit_paisa: payments not matched to specific invoices
    """
    from sqlalchemy import case as sa_case, literal_column

    target_date: date = date.today()
    if as_of_date:
        try:
            target_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid as_of_date format. Expected YYYY-MM-DD")

    cutoff_dt = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)

    # ── Query 1: Bounded client page ─────────────────────────────────────────
    client_stmt = db.query(Client).filter(Client.company_id == current_user.company_id)
    if client_id is not None:
        client_stmt = client_stmt.filter(Client.id == client_id)
    clients = client_stmt.offset(offset).limit(limit).all()
    if not clients:
        return {"as_of_date": str(target_date), "total_parties": 0, "summary": {
            "current_paisa": 0, "days_31_60_paisa": 0, "days_61_90_paisa": 0,
            "over_90_paisa": 0, "total_due_paisa": 0, "unallocated_credit_paisa": 0
        }, "items": []}

    client_ids = [c.id for c in clients]

    # ── Query 2: SQL-aggregated payment totals per client ────────────────────
    # Aggregate payment (credit) entries entirely in SQL — no Python loop over rows
    payment_agg = db.query(
        ReceivableEntry.client_id,
        func.coalesce(func.sum(ReceivableEntry.amount_paisa), 0).label("total_payments_paisa")
    ).filter(
        ReceivableEntry.company_id == current_user.company_id,
        ReceivableEntry.client_id.in_(client_ids),
        ReceivableEntry.direction == -1,
        ReceivableEntry.occurred_at <= cutoff_dt
    ).group_by(ReceivableEntry.client_id).all()
    payment_map = {row.client_id: int(row.total_payments_paisa) for row in payment_agg}

    # ── Query 3: SQL-aggregated allocation totals per client ─────────────────
    alloc_agg = db.query(
        ReceivableEntry.client_id,
        func.coalesce(func.sum(PaymentAllocation.allocated_paisa), 0).label("total_allocated_paisa")
    ).join(
        PaymentAllocation,
        PaymentAllocation.invoice_entry_id == ReceivableEntry.id
    ).filter(
        ReceivableEntry.company_id == current_user.company_id,
        ReceivableEntry.client_id.in_(client_ids),
        PaymentAllocation.company_id == current_user.company_id,
        PaymentAllocation.created_at <= cutoff_dt
    ).group_by(ReceivableEntry.client_id).all()
    alloc_map = {row.client_id: int(row.total_allocated_paisa) for row in alloc_agg}

    # ── Query 4: Debit invoice entries needed for per-invoice due_date aging ─
    # We must know individual due_dates to classify into buckets. Fetch only
    # debit entries for the current client page (bounded by client_ids IN clause).
    debit_entries = db.query(
        ReceivableEntry.id,
        ReceivableEntry.client_id,
        ReceivableEntry.amount_paisa,
        ReceivableEntry.due_date,
        ReceivableEntry.occurred_at,
    ).filter(
        ReceivableEntry.company_id == current_user.company_id,
        ReceivableEntry.client_id.in_(client_ids),
        ReceivableEntry.direction == 1,
        ReceivableEntry.occurred_at <= cutoff_dt
    ).all()

    # Per-invoice allocation amounts (query 4b): group allocations by invoice_entry_id
    debit_entry_ids = [e.id for e in debit_entries]
    if debit_entry_ids:
        invoice_alloc_rows = db.query(
            PaymentAllocation.invoice_entry_id,
            func.coalesce(func.sum(PaymentAllocation.allocated_paisa), 0).label("allocated")
        ).filter(
            PaymentAllocation.company_id == current_user.company_id,
            PaymentAllocation.invoice_entry_id.in_(debit_entry_ids)
        ).group_by(PaymentAllocation.invoice_entry_id).all()
        invoice_alloc_map = {row.invoice_entry_id: int(row.allocated) for row in invoice_alloc_rows}
    else:
        invoice_alloc_map = {}

    # Group debit entries by client
    debit_map: Dict[int, list] = {}
    for entry in debit_entries:
        debit_map.setdefault(entry.client_id, []).append(entry)

    # ── Query 5: Legacy fallback aggregation ─────────────────────────────────
    legacy_orders = db.query(
        SalesOrder.client_id,
        func.coalesce(func.sum(SalesOrder.receivable_amount), Decimal('0.0')).label("legacy_receivable")
    ).filter(
        SalesOrder.company_id == current_user.company_id,
        SalesOrder.client_id.in_(client_ids)
    ).group_by(SalesOrder.client_id).all()
    legacy_map = {row.client_id: Decimal(row.legacy_receivable) for row in legacy_orders}

    # ── Python-side: classify per-invoice aging bucket (O(invoices per page)) ─
    party_rows = []
    total_summary = {
        "current_paisa": 0, "days_31_60_paisa": 0,
        "days_61_90_paisa": 0, "over_90_paisa": 0,
        "total_due_paisa": 0, "unallocated_credit_paisa": 0
    }

    for client in clients:
        credit_limit_paisa = int(round((client.credit_limit or Decimal('0.0')) * 100))
        debits = debit_map.get(client.id, [])

        if not debits:
            # Fallback for legacy rows without AR subledger entries
            legacy_amt = legacy_map.get(client.id, Decimal('0.0'))
            legacy_paisa = int(round(legacy_amt * 100))
            if legacy_paisa > 0:
                party_rows.append({
                    "client_id": client.id, "client_code": client.code, "client_name": client.name,
                    "pan_number": getattr(client, "pan_number", "") or "",
                    "contact_person": client.contact_person or "", "phone": client.phone or "",
                    "credit_limit_paisa": credit_limit_paisa, "current_paisa": legacy_paisa,
                    "days_31_60_paisa": 0, "days_61_90_paisa": 0, "over_90_paisa": 0,
                    "total_due_paisa": legacy_paisa, "unallocated_credit_paisa": 0,
                    "credit_limit_exceeded": bool(credit_limit_paisa > 0 and legacy_paisa > credit_limit_paisa),
                    "active_invoice_count": 0
                })
                total_summary["current_paisa"] += legacy_paisa
                total_summary["total_due_paisa"] += legacy_paisa
            continue

        current_paisa = days_31_60_paisa = days_61_90_paisa = over_90_paisa = 0
        active_inv_count = 0
        total_payments_paisa = payment_map.get(client.id, 0)
        total_allocated_paisa = alloc_map.get(client.id, 0)

        for entry in debits:
            allocated = invoice_alloc_map.get(entry.id, 0)
            unpaid_paisa = max(0, entry.amount_paisa - allocated)
            if unpaid_paisa <= 0:
                continue
            active_inv_count += 1
            due_d = entry.due_date.date() if entry.due_date else (
                entry.occurred_at.date() + timedelta(days=30) if entry.occurred_at else target_date
            )
            days_overdue = (target_date - due_d).days
            if days_overdue <= 30:
                current_paisa += unpaid_paisa
            elif days_overdue <= 60:
                days_31_60_paisa += unpaid_paisa
            elif days_overdue <= 90:
                days_61_90_paisa += unpaid_paisa
            else:
                over_90_paisa += unpaid_paisa

        unallocated_credit_paisa = max(0, total_payments_paisa - total_allocated_paisa)
        net_due_paisa = current_paisa + days_31_60_paisa + days_61_90_paisa + over_90_paisa
        actual_net_due_paisa = max(0, net_due_paisa - unallocated_credit_paisa)

        # Deduct unallocated credits from oldest buckets first
        if unallocated_credit_paisa > 0:
            rem = unallocated_credit_paisa
            for attr in ["over_90_paisa", "days_61_90_paisa", "days_31_60_paisa", "current_paisa"]:
                val = locals()[attr]
                if rem > 0 and val > 0:
                    d = min(val, rem)
                    locals()[attr]  # reference
                    if attr == "over_90_paisa":
                        over_90_paisa -= d
                    elif attr == "days_61_90_paisa":
                        days_61_90_paisa -= d
                    elif attr == "days_31_60_paisa":
                        days_31_60_paisa -= d
                    else:
                        current_paisa -= d
                    rem -= d

        party_rows.append({
            "client_id": client.id, "client_code": client.code, "client_name": client.name,
            "pan_number": getattr(client, "pan_number", "") or "",
            "contact_person": client.contact_person or "", "phone": client.phone or "",
            "credit_limit_paisa": credit_limit_paisa,
            "current_paisa": current_paisa, "days_31_60_paisa": days_31_60_paisa,
            "days_61_90_paisa": days_61_90_paisa, "over_90_paisa": over_90_paisa,
            "total_due_paisa": actual_net_due_paisa,
            "unallocated_credit_paisa": unallocated_credit_paisa,
            "credit_limit_exceeded": bool(credit_limit_paisa > 0 and actual_net_due_paisa > credit_limit_paisa),
            "active_invoice_count": active_inv_count
        })
        total_summary["current_paisa"] += current_paisa
        total_summary["days_31_60_paisa"] += days_31_60_paisa
        total_summary["days_61_90_paisa"] += days_61_90_paisa
        total_summary["over_90_paisa"] += over_90_paisa
        total_summary["total_due_paisa"] += actual_net_due_paisa
        total_summary["unallocated_credit_paisa"] += unallocated_credit_paisa

    party_rows.sort(key=lambda r: r["total_due_paisa"], reverse=True)
    return {
        "as_of_date": str(target_date),
        "total_parties": len(party_rows),
        "summary": total_summary,
        "items": party_rows
    }


@router.get("/statement/{client_id}")
def get_party_statement(
    client_id: int,
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    include_disputed: bool = Query(True, description="Whether to include disputed items"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns an append-only customer statement with exact running balance in integer paisa.
    Uses window function: SUM(direction * amount_paisa) OVER (PARTITION BY client_id ORDER BY occurred_at ASC, id ASC)
    """
    client_repo = TenantRepository(Client, db, current_user.company_id)
    client = client_repo.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in current company")

    # 1. Base query with window function computing true running balance
    subq = db.query(
        ReceivableEntry.id.label("e_id"),
        ReceivableEntry.company_id,
        ReceivableEntry.client_id,
        ReceivableEntry.entry_type,
        ReceivableEntry.direction,
        ReceivableEntry.amount_paisa,
        ReceivableEntry.source_doc_ref,
        ReceivableEntry.invoice_id,
        ReceivableEntry.actor_id,
        ReceivableEntry.occurred_at,
        ReceivableEntry.due_date,
        ReceivableEntry.is_disputed,
        ReceivableEntry.dispute_notes,
        ReceivableEntry.notes,
        func.sum(ReceivableEntry.direction * ReceivableEntry.amount_paisa).over(
            partition_by=ReceivableEntry.client_id,
            order_by=[ReceivableEntry.occurred_at.asc(), ReceivableEntry.id.asc()]
        ).label("running_balance_paisa")
    ).filter(
        ReceivableEntry.company_id == current_user.company_id,
        ReceivableEntry.client_id == client_id
    )

    if not include_disputed:
        subq = subq.filter(ReceivableEntry.is_disputed == False)

    subquery = subq.subquery()
    query = db.query(subquery)

    if date_from:
        try:
            d_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(subquery.c.occurred_at >= d_from)
        except ValueError:
            pass

    if date_to:
        try:
            d_to = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(subquery.c.occurred_at < d_to)
        except ValueError:
            pass

    rows = query.order_by(subquery.c.occurred_at.asc(), subquery.c.e_id.asc()).all()

    # Pre-fetch user details for actor names
    actor_ids = list({r.actor_id for r in rows if r.actor_id})
    user_map = {u.id: u.name or u.username for u in db.query(User).filter(User.id.in_(actor_ids), User.company_id == current_user.company_id).all()} if actor_ids else {}

    statement_lines = []
    total_debit = 0
    total_credit = 0

    for r in rows:
        debit = r.amount_paisa if r.direction == 1 else 0
        credit = r.amount_paisa if r.direction == -1 else 0
        total_debit += debit
        total_credit += credit

        statement_lines.append({
            "id": r.e_id,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            "entry_type": r.entry_type,
            "source_doc_ref": r.source_doc_ref or "",
            "invoice_id": r.invoice_id,
            "direction": r.direction,
            "amount_paisa": r.amount_paisa,
            "debit_paisa": debit,
            "credit_paisa": credit,
            "running_balance_paisa": int(r.running_balance_paisa or 0),
            "due_date": r.due_date.isoformat() if r.due_date else None,
            "is_disputed": r.is_disputed,
            "dispute_notes": r.dispute_notes or "",
            "notes": r.notes or "",
            "actor_name": user_map.get(r.actor_id, "System")
        })

    # Summary calculations
    net_bal = total_debit - total_credit

    return {
        "client": {
            "id": client.id,
            "code": client.code,
            "name": client.name,
            "pan_number": getattr(client, "pan_number", "") or "",
            "contact_person": client.contact_person or "",
            "phone": client.phone or "",
            "address": client.address or "",
            "credit_limit": client.credit_limit or Decimal('0.0'),
            "credit_limit_paisa": int(round((client.credit_limit or Decimal('0.0')) * 100))
        },
        "summary": {
            "total_debit_paisa": total_debit,
            "total_credit_paisa": total_credit,
            "net_balance_paisa": net_bal,
            "statement_lines_count": len(statement_lines)
        },
        "lines": statement_lines
    }


@router.post("/payments")
def record_ar_payment(
    payload: PaymentReceiptCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Records customer payment receipt into the append-only AR subledger.
    Allocates payment to specified invoices.
    Restricted to editor and admin roles.
    """
    if payload.amount_paisa <= 0:
        raise HTTPException(status_code=400, detail="Payment amount_paisa must be greater than zero")

    client_repo = TenantRepository(Client, db, current_user.company_id)
    client = client_repo.get_by_id(payload.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in current company")

    method = payload.payment_method.upper()
    if method not in ("CASH", "BANK"):
        raise HTTPException(status_code=400, detail="payment_method must be 'CASH' or 'BANK'")

    # Validate allocations do not exceed total payment
    if payload.invoice_allocations:
        sum_alloc = sum(a.amount_paisa for a in payload.invoice_allocations)
        if sum_alloc > payload.amount_paisa:
            raise HTTPException(
                status_code=422,
                detail=f"Total invoice allocations ({sum_alloc} paisa) exceed receipt amount ({payload.amount_paisa} paisa)"
            )

    doc_ref = payload.reference or generate_document_number(db, current_user.company_id, "RECEIPT", "RCPT")
    entry_type = "PAYMENT_CASH" if method == "CASH" else "PAYMENT_BANK"

    occurred = datetime.now(timezone.utc)
    if payload.payment_date:
        try:
            occurred = datetime.combine(
                datetime.strptime(payload.payment_date, "%Y-%m-%d").date(),
                datetime.now(timezone.utc).time(),
                tzinfo=timezone.utc
            )
        except ValueError:
            pass

    entry_repo = TenantRepository(ReceivableEntry, db, current_user.company_id)
    payment_entry = entry_repo.create(
        client_id=client.id,
        entry_type=entry_type,
        direction=-1,
        amount_paisa=payload.amount_paisa,
        source_doc_ref=doc_ref,
        invoice_id=None,
        actor_id=current_user.id,
        occurred_at=occurred,
        due_date=None,
        is_disputed=False,
        notes=payload.notes or f"Customer payment via {method}"
    )

    created_allocations = []
    if payload.invoice_allocations:
        alloc_repo = TenantRepository(PaymentAllocation, db, current_user.company_id)
        for item in payload.invoice_allocations:
            # 1. Verify invoice belongs to the caller's company (Tenant Isolation / IDOR)
            inv = db.query(Invoice).filter(
                Invoice.id == item.invoice_id,
                Invoice.company_id == current_user.company_id
            ).first()
            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Invoice #{item.invoice_id} not found in current company"
                )

            # 2. Verify invoice belongs to this specific client
            so = db.query(SalesOrder).filter(
                SalesOrder.id == inv.sales_order_id,
                SalesOrder.company_id == current_user.company_id
            ).first()
            if not so or so.client_id != client.id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invoice #{item.invoice_id} does not belong to client #{client.id}"
                )

            # 3. Find the corresponding debit receivable entry for this invoice
            inv_entry = db.query(ReceivableEntry).filter(
                ReceivableEntry.company_id == current_user.company_id,
                ReceivableEntry.client_id == client.id,
                ReceivableEntry.invoice_id == item.invoice_id,
                ReceivableEntry.entry_type == "INVOICE_POSTED"
            ).first()

            if not inv_entry:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invoice #{item.invoice_id} has no posted receivable entry available for allocation"
                )

            alloc = alloc_repo.create(
                payment_entry_id=payment_entry.id,
                invoice_entry_id=inv_entry.id,
                allocated_paisa=item.amount_paisa
            )
            created_allocations.append({
                "id": alloc.id,
                "invoice_id": item.invoice_id,
                "allocated_paisa": alloc.allocated_paisa
            })

    # Also sync with legacy Payment table if order exists
    try:
        last_order = db.query(SalesOrder).filter(
            SalesOrder.company_id == current_user.company_id,
            SalesOrder.client_id == client.id
        ).order_by(SalesOrder.id.desc()).first()
        if last_order:
            ad_str = occurred.strftime("%Y-%m-%d")
            bs_str = ad_to_bs_str(occurred.date())
            legacy_payment = Payment(
                company_id=current_user.company_id,
                sales_order_id=last_order.id,
                client_id=client.id,
                amount=payload.amount_paisa / Decimal('100.0'),
                payment_date_ad=ad_str,
                payment_date_bs=bs_str,
                payment_method=method.lower(),
                notes=payload.notes or f"AR receipt {doc_ref}"
            )
            db.add(legacy_payment)
    except Exception:
        pass

    db.commit()
    db.refresh(payment_entry)

    return {
        "id": payment_entry.id,
        "client_id": payment_entry.client_id,
        "entry_type": payment_entry.entry_type,
        "direction": payment_entry.direction,
        "amount_paisa": payment_entry.amount_paisa,
        "source_doc_ref": payment_entry.source_doc_ref,
        "occurred_at": payment_entry.occurred_at.isoformat() if payment_entry.occurred_at else None,
        "allocations": created_allocations
    }


@router.post("/dispute/{entry_id}")
def toggle_entry_dispute(
    entry_id: int,
    payload: DisputeTogglePayload,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Flags an invoice as disputed for Schedule-5 audit resolution without mutating ledger balance math.
    """
    entry = db.query(ReceivableEntry).filter(
        ReceivableEntry.id == entry_id,
        ReceivableEntry.company_id == current_user.company_id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Receivable entry not found in current company")

    entry.is_disputed = payload.is_disputed
    entry.dispute_notes = payload.dispute_notes
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "is_disputed": entry.is_disputed,
        "dispute_notes": entry.dispute_notes
    }


@router.get("/invoices/{client_id}")
def get_client_open_invoices(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns list of issued invoices with remaining balance in integer paisa for payment allocation.
    """
    client_repo = TenantRepository(Client, db, current_user.company_id)
    client = client_repo.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found in current company")

    inv_entries = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == current_user.company_id,
        ReceivableEntry.client_id == client_id,
        ReceivableEntry.entry_type == "INVOICE_POSTED"
    ).order_by(ReceivableEntry.occurred_at.asc(), ReceivableEntry.id.asc()).all()

    # Pre-fetch allocations for these invoices
    entry_ids = [e.id for e in inv_entries]
    allocs = db.query(
        PaymentAllocation.invoice_entry_id,
        func.coalesce(func.sum(PaymentAllocation.allocated_paisa), 0).label("total_alloc")
    ).filter(
        PaymentAllocation.company_id == current_user.company_id,
        PaymentAllocation.invoice_entry_id.in_(entry_ids)
    ).group_by(PaymentAllocation.invoice_entry_id).all() if entry_ids else []

    alloc_map = {row.invoice_entry_id: int(row.total_alloc) for row in allocs}

    open_invoices = []
    for entry in inv_entries:
        allocated = alloc_map.get(entry.id, 0)
        unpaid = max(0, entry.amount_paisa - allocated)
        open_invoices.append({
            "entry_id": entry.id,
            "invoice_id": entry.invoice_id,
            "invoice_number": entry.source_doc_ref or "",
            "occurred_at": entry.occurred_at.isoformat() if entry.occurred_at else None,
            "due_date": entry.due_date.isoformat() if entry.due_date else None,
            "amount_paisa": entry.amount_paisa,
            "allocated_paisa": allocated,
            "unpaid_paisa": unpaid,
            "is_disputed": entry.is_disputed,
            "notes": entry.notes or ""
        })

    return open_invoices
