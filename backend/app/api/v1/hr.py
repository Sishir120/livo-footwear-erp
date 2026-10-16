import os
import uuid
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.api.deps import get_db, get_current_user, require_editor, require_admin
from app.models.user import User
from app.models.worker import Worker, WorkerAdvance, WorkerMonthlyRecord, CompanyHRSettings
from app.schemas.worker import (
    WorkerCreate,
    WorkerUpdate,
    WorkerStatusUpdate,
    WorkerResponse,
    CitizenshipDocResponse,
    CurrentMonthHours,
    AdvanceCreate,
    AdvanceResponse,
    MonthlyPayrollRequest,
    MonthlyRecordResponse,
    WorkerHistoryResponse,
    HRSettingsResponse,
    HRSettingsUpdate,
)

router = APIRouter(prefix="/hr", tags=["HR Management & Payroll Ledger"])

# Storage Directories
UPLOAD_PHOTO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "static",
    "uploads",
    "workers"
)
os.makedirs(UPLOAD_PHOTO_DIR, exist_ok=True)

SECURE_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "storage",
    "secure_hr"
)
os.makedirs(SECURE_DOCS_DIR, exist_ok=True)

ALLOWED_PHOTO_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_PHOTO_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB

ALLOWED_DOC_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_DOC_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _safe_resolve_path(base_dir: str, file_name: str) -> str:
    """
    Prevents directory traversal (e.g., ../../etc/passwd or absolute path escape)
    by ensuring the canonical resolved path strictly resides inside base_dir.
    """
    canonical_base = os.path.realpath(base_dir)
    safe_name = os.path.basename(file_name)
    resolved = os.path.realpath(os.path.join(canonical_base, safe_name))
    if os.path.commonpath([canonical_base, resolved]) != canonical_base:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal path traversal attempt detected."
        )
    return resolved


def _sanitize_filename(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    return clean[:100] if len(clean) > 100 else clean


def _worker_to_response(
    worker: Worker,
    outstanding_advance: int = 0,
    current_month: Optional[CurrentMonthHours] = None,
    redact_compensation: bool = False
) -> WorkerResponse:
    if redact_compensation:
        cm = None
        if current_month:
            cm = CurrentMonthHours(
                month_year=current_month.month_year,
                total_working_hours=current_month.total_working_hours,
                overtime_hours=current_month.overtime_hours,
                status=current_month.status
            )
        return WorkerResponse(
            id=worker.id,
            company_id=worker.company_id,
            worker_code=worker.worker_code,
            name=worker.name,
            join_date=worker.join_date,
            pay_type=worker.pay_type,
            phone=worker.phone,
            photo_url=worker.photo_url,
            temporary_address=worker.temporary_address,
            permanent_address=worker.permanent_address,
            is_active=worker.is_active,
            inactive_date=worker.inactive_date,
            inactive_reason=worker.inactive_reason,
            has_citizenship_doc=bool(worker.citizenship_doc_path),
            citizenship_doc_name=worker.citizenship_doc_name,
            standard_monthly_hours_override=worker.standard_monthly_hours_override,
            created_at=worker.created_at,
            current_month=cm
        )

    return WorkerResponse(
        id=worker.id,
        company_id=worker.company_id,
        worker_code=worker.worker_code,
        name=worker.name,
        join_date=worker.join_date,
        pay_type=worker.pay_type,
        basic_rate_paisa=worker.basic_rate_paisa,
        phone=worker.phone,
        photo_url=worker.photo_url,
        temporary_address=worker.temporary_address,
        permanent_address=worker.permanent_address,
        is_active=worker.is_active,
        inactive_date=worker.inactive_date,
        inactive_reason=worker.inactive_reason,
        has_citizenship_doc=bool(worker.citizenship_doc_path),
        citizenship_doc_name=worker.citizenship_doc_name,
        standard_monthly_hours_override=worker.standard_monthly_hours_override,
        overtime_rate_paisa_override=worker.overtime_rate_paisa_override,
        created_at=worker.created_at,
        outstanding_advance_paisa=outstanding_advance,
        current_month=current_month
    )


def _reconcile_worker_advances(db: Session, company_id: int, worker_id: int, for_update: bool = False) -> dict:
    """
    Deterministic advance balance reconciliation engine (Phase 4B.4.2-C1).
    Reconciles:
    1. Total issued principal vs total recovered entries across all history.
    2. Explicitly linked child recoveries (parent_advance_id is set) against their parent advances.
    3. Legacy unlinked recoveries (parent_advance_id IS NULL) allocated strictly in FIFO order
       (WorkerAdvance.date.asc(), WorkerAdvance.id.asc()) against remaining balances of older advances.

    Guarantees:
    - Per-advance remaining principal is never negative.
    - Sum of per-advance remaining principal strictly equals total outstanding principal when consistent.
    - Inconsistent ledgers (total_recovered > total_issued or unabsorbable legacy pool) are flagged.

    Returns:
    {
        "total_issued_paisa": int,
        "total_recovered_paisa": int,
        "total_outstanding_paisa": int,
        "is_ledger_consistent": bool,
        "discrepancy_paisa": int,
        "per_advance_remaining": dict[int, int],  # adv.id -> remaining_principal_paisa
        "issued_advances": list[WorkerAdvance]     # sorted FIFO (date ASC, id ASC)
    }
    """
    adv_query = db.query(WorkerAdvance).filter(
        WorkerAdvance.company_id == company_id,
        WorkerAdvance.worker_id == worker_id,
        WorkerAdvance.entry_type == "ISSUED"
    ).order_by(WorkerAdvance.date.asc(), WorkerAdvance.id.asc())

    if for_update:
        adv_query = adv_query.with_for_update()

    issued_advances = adv_query.all()

    rec_query = db.query(WorkerAdvance).filter(
        WorkerAdvance.company_id == company_id,
        WorkerAdvance.worker_id == worker_id,
        WorkerAdvance.entry_type == "RECOVERED"
    ).order_by(WorkerAdvance.date.asc(), WorkerAdvance.id.asc())

    if for_update:
        rec_query = rec_query.with_for_update()

    recovered_entries = rec_query.all()

    total_issued = sum(a.amount_paisa for a in issued_advances)
    total_recovered = sum(r.amount_paisa for r in recovered_entries)
    raw_outstanding = total_issued - total_recovered

    # Group explicitly linked recoveries by parent_advance_id
    linked_recoveries_by_parent: dict[int, int] = {}
    legacy_unlinked_pool = 0

    for r in recovered_entries:
        if r.parent_advance_id is not None:
            linked_recoveries_by_parent[r.parent_advance_id] = (
                linked_recoveries_by_parent.get(r.parent_advance_id, 0) + r.amount_paisa
            )
        else:
            legacy_unlinked_pool += r.amount_paisa

    # Distribute recoveries per advance in FIFO order
    per_advance_remaining: dict[int, int] = {}
    unallocated_legacy = legacy_unlinked_pool

    for adv in issued_advances:
        linked_rec = linked_recoveries_by_parent.get(adv.id, 0)
        # Advance balance after explicitly linked recoveries
        bal_after_linked = max(0, adv.amount_paisa - linked_rec)

        # Allocate from unlinked legacy pool in FIFO order
        legacy_alloc = min(bal_after_linked, unallocated_legacy)
        rem_principal = bal_after_linked - legacy_alloc
        unallocated_legacy -= legacy_alloc

        per_advance_remaining[adv.id] = rem_principal

    # Consistency evaluation
    has_over_recovered_advance = any(
        linked_recoveries_by_parent.get(adv.id, 0) > adv.amount_paisa for adv in issued_advances
    )
    over_recovery_excess = sum(
        max(0, linked_recoveries_by_parent.get(adv.id, 0) - adv.amount_paisa) for adv in issued_advances
    )

    is_consistent = (total_recovered <= total_issued) and (unallocated_legacy == 0) and not has_over_recovered_advance
    discrepancy = (total_recovered - total_issued) if total_recovered > total_issued else (unallocated_legacy or over_recovery_excess)

    return {
        "total_issued_paisa": total_issued,
        "total_recovered_paisa": total_recovered,
        "total_outstanding_paisa": max(0, raw_outstanding) if is_consistent else 0,
        "raw_outstanding_paisa": raw_outstanding,
        "is_ledger_consistent": is_consistent,
        "discrepancy_paisa": discrepancy,
        "per_advance_remaining": per_advance_remaining,
        "issued_advances": issued_advances
    }


def _calculate_outstanding_advance(db: Session, company_id: int, worker_id: int) -> int:
    """Returns exact integer paisa reconciled outstanding advance balance."""
    recon = _reconcile_worker_advances(db, company_id, worker_id)
    return recon["total_outstanding_paisa"]


@router.get("/workers", response_model=List[WorkerResponse], response_model_exclude_unset=True)
def get_workers(
    status_filter: str = Query("all", alias="status", description="'active', 'inactive', or 'all'"),
    pay_type: Optional[str] = Query(None, description="'SALARY' or 'WAGE'"),
    search: Optional[str] = Query(None, description="Search by name, worker_code, or phone"),
    month_year: Optional[str] = Query(None, description="Active month (YYYY-MM) for hours lookup"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all workers within tenant company with real-time calculated:
    - outstanding_advance_paisa: sum(ISSUED) - sum(RECOVERED)
    - current_month: hours, overtime, gross pay, and payment status for the target month
    """
    query = db.query(Worker).filter(Worker.company_id == current_user.company_id)

    # Status filter
    if status_filter.lower() == "active":
        query = query.filter(Worker.is_active == True)
    elif status_filter.lower() == "inactive":
        query = query.filter(Worker.is_active == False)

    # Pay type filter
    if pay_type:
        query = query.filter(Worker.pay_type == pay_type.upper())

    # Text search
    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Worker.worker_code).like(s),
                func.lower(Worker.name).like(s),
                func.lower(Worker.phone).like(s)
            )
        )

    workers = query.order_by(Worker.worker_code.asc()).all()

    # Determine evaluation month
    eval_month = month_year or datetime.now().strftime("%Y-%m")

    # Pre-fetch monthly records for evaluation month for these workers
    worker_ids = [w.id for w in workers]
    monthly_records = {}
    if worker_ids:
        records = db.query(WorkerMonthlyRecord).filter(
            WorkerMonthlyRecord.company_id == current_user.company_id,
            WorkerMonthlyRecord.worker_id.in_(worker_ids),
            WorkerMonthlyRecord.month_year == eval_month
        ).all()
        for r in records:
            monthly_records[r.worker_id] = r

    # Pre-fetch advances to compute outstanding balances efficiently
    advances_issued = dict(
        db.query(WorkerAdvance.worker_id, func.sum(WorkerAdvance.amount_paisa))
        .filter(WorkerAdvance.company_id == current_user.company_id, WorkerAdvance.entry_type == "ISSUED")
        .group_by(WorkerAdvance.worker_id)
        .all()
    )
    advances_recovered = dict(
        db.query(WorkerAdvance.worker_id, func.sum(WorkerAdvance.amount_paisa))
        .filter(WorkerAdvance.company_id == current_user.company_id, WorkerAdvance.entry_type == "RECOVERED")
        .group_by(WorkerAdvance.worker_id)
        .all()
    )

    results = []
    for w in workers:
        issued = advances_issued.get(w.id, 0) or 0
        recovered = advances_recovered.get(w.id, 0) or 0
        outstanding = max(0, int(issued - recovered))

        # Monthly record
        m_rec = monthly_records.get(w.id)
        current_m = CurrentMonthHours(
            month_year=eval_month,
            total_working_hours=m_rec.total_working_hours if m_rec else Decimal('0.0'),
            overtime_hours=m_rec.overtime_hours if m_rec else Decimal('0.0'),
            gross_pay_paisa=m_rec.gross_pay_paisa if m_rec else 0,
            advance_deduction_paisa=m_rec.advance_deduction_paisa if m_rec else 0,
            net_paid_paisa=m_rec.net_paid_paisa if m_rec else 0,
            status=m_rec.status if m_rec else "NONE"
        )
        redact = current_user.role not in ("admin", "manager", "editor")
        results.append(_worker_to_response(w, outstanding, current_m, redact_compensation=redact))

    return results


@router.post("/workers", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def create_worker(
    payload: WorkerCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Create a new worker profile. Enforces company-scoped unique worker_code.
    Rejects viewers (403 Forbidden).
    """
    # Check duplicate worker code in tenant company
    existing = db.query(Worker).filter(
        Worker.company_id == current_user.company_id,
        func.lower(Worker.worker_code) == payload.worker_code.strip().lower()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker with code '{payload.worker_code}' already exists in your company."
        )

    pay_type_clean = payload.pay_type.upper().strip()
    if pay_type_clean not in ("SALARY", "WAGE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pay_type must be either 'SALARY' or 'WAGE'."
        )

    worker = Worker(
        company_id=current_user.company_id,
        worker_code=payload.worker_code.strip().upper(),
        name=payload.name.strip(),
        join_date=payload.join_date or date.today(),
        pay_type=pay_type_clean,
        basic_rate_paisa=payload.basic_rate_paisa,
        phone=payload.phone.strip() if payload.phone else None,
        is_active=payload.is_active,
        temporary_address=payload.temporary_address.strip() if payload.temporary_address else None,
        permanent_address=payload.permanent_address.strip() if payload.permanent_address else None,
        photo_url=payload.photo_url.strip() if payload.photo_url else None,
        standard_monthly_hours_override=payload.standard_monthly_hours_override,
        overtime_rate_paisa_override=payload.overtime_rate_paisa_override
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    return _worker_to_response(worker, 0, None)


@router.patch("/workers/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: int,
    payload: WorkerUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Update worker profile, including status activation/deactivation, addresses, and compensation overrides.
    Rejects viewers (403 Forbidden).
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    if payload.name is not None:
        worker.name = payload.name.strip()
    if payload.join_date is not None:
        worker.join_date = payload.join_date
    if payload.pay_type is not None:
        pt = payload.pay_type.upper().strip()
        if pt in ("SALARY", "WAGE"):
            worker.pay_type = pt
    if payload.basic_rate_paisa is not None:
        worker.basic_rate_paisa = payload.basic_rate_paisa
    if payload.phone is not None:
        worker.phone = payload.phone.strip() if payload.phone else None
    if payload.temporary_address is not None:
        worker.temporary_address = payload.temporary_address.strip() if payload.temporary_address else None
    if payload.permanent_address is not None:
        worker.permanent_address = payload.permanent_address.strip() if payload.permanent_address else None
    if payload.photo_url is not None:
        worker.photo_url = payload.photo_url.strip() if payload.photo_url else None
    if payload.standard_monthly_hours_override is not None:
        worker.standard_monthly_hours_override = payload.standard_monthly_hours_override
    if payload.overtime_rate_paisa_override is not None:
        worker.overtime_rate_paisa_override = payload.overtime_rate_paisa_override

    # Lifecycle transition logic
    if payload.is_active is not None:
        if not payload.is_active and worker.is_active:
            worker.is_active = False
            worker.inactive_date = payload.inactive_date or date.today()
            worker.inactive_reason = (
                payload.inactive_reason.strip() if payload.inactive_reason else (worker.inactive_reason or "Deactivated")
            )
        elif payload.is_active and not worker.is_active:
            worker.is_active = True
            worker.inactive_date = None
            worker.inactive_reason = None
    else:
        if payload.inactive_reason is not None:
            worker.inactive_reason = payload.inactive_reason.strip() if payload.inactive_reason else None
        if payload.inactive_date is not None:
            worker.inactive_date = payload.inactive_date

    db.commit()
    db.refresh(worker)

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)
    return _worker_to_response(worker, outstanding, None)


@router.patch("/workers/{worker_id}/status", response_model=WorkerResponse)
def update_worker_status(
    worker_id: int,
    payload: WorkerStatusUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Dedicated activation/deactivation lifecycle endpoint with explicit reason and effective date.
    Rejects viewers (403 Forbidden).
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    if not payload.is_active and worker.is_active:
        worker.is_active = False
        worker.inactive_date = payload.inactive_date or date.today()
        worker.inactive_reason = (
            payload.inactive_reason.strip() if payload.inactive_reason else (worker.inactive_reason or "Deactivated")
        )
    elif payload.is_active and not worker.is_active:
        worker.is_active = True
        worker.inactive_date = None
        worker.inactive_reason = None

    db.commit()
    db.refresh(worker)

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)
    return _worker_to_response(worker, outstanding, None)


@router.post("/advances", response_model=AdvanceResponse, status_code=status.HTTP_201_CREATED)
def record_advance(
    payload: AdvanceCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Record worker advance issued (ISSUED) or cash repayment (RECOVERED).
    Rejects viewers (403 Forbidden).
    Enforces worker row lock and parent advance principal verification.
    """
    worker = db.query(Worker).filter(
        Worker.id == payload.worker_id,
        Worker.company_id == current_user.company_id
    ).with_for_update().first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    entry_type_clean = payload.entry_type.upper().strip()
    if entry_type_clean not in ("ISSUED", "RECOVERED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entry_type must be 'ISSUED' or 'RECOVERED'."
        )

    # Inactive worker guardrail: Inactive workers cannot receive new advances, but CAN repay existing ones!
    if not worker.is_active and entry_type_clean == "ISSUED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot issue advance to an inactive worker. Worker must be reactivated first."
        )

    if entry_type_clean == "ISSUED":
        advance = WorkerAdvance(
            company_id=current_user.company_id,
            worker_id=worker.id,
            amount_paisa=payload.amount_paisa,
            entry_type="ISSUED",
            date=payload.date or date.today(),
            notes=payload.notes.strip() if payload.notes else None,
            actor_id=current_user.id,
            installment_amount_paisa=payload.installment_amount_paisa
        )
        db.add(advance)
        db.commit()
        db.refresh(advance)

        res = AdvanceResponse.model_validate(advance)
        res.remaining_principal_paisa = payload.amount_paisa
        return res

    # entry_type == "RECOVERED"
    recon = _reconcile_worker_advances(db, current_user.company_id, worker.id, for_update=True)

    if not recon["is_ledger_consistent"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot record repayment: Worker #{worker.id} has an inconsistent advance ledger (discrepancy: {recon['discrepancy_paisa']} paisa). Manual audit required."
        )

    if payload.parent_advance_id:
        target_adv_id = payload.parent_advance_id
        parent_rem = recon["per_advance_remaining"].get(target_adv_id)
        if parent_rem is None:
            exists = any(a.id == target_adv_id for a in recon["issued_advances"])
            if not exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent advance #{target_adv_id} not found for this worker."
                )
            parent_rem = 0

        if payload.amount_paisa > parent_rem:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Repayment amount ({payload.amount_paisa} paisa) exceeds reconciled remaining balance ({parent_rem} paisa) of Advance #{target_adv_id}."
            )

        advance = WorkerAdvance(
            company_id=current_user.company_id,
            worker_id=worker.id,
            amount_paisa=payload.amount_paisa,
            entry_type="RECOVERED",
            date=payload.date or date.today(),
            notes=payload.notes.strip() if payload.notes else None,
            actor_id=current_user.id,
            parent_advance_id=target_adv_id
        )
        db.add(advance)
        db.commit()
        db.refresh(advance)

        res = AdvanceResponse.model_validate(advance)
        res.remaining_principal_paisa = parent_rem - payload.amount_paisa
        return res

    # Unlinked cash repayment: Split across open advances in FIFO order (C2)
    total_debt = recon["total_outstanding_paisa"]
    if total_debt <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Worker has no outstanding advance balance to repay."
        )

    if payload.amount_paisa > total_debt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Repayment amount ({payload.amount_paisa} paisa) exceeds total reconciled outstanding balance ({total_debt} paisa)."
        )

    remaining_to_allocate = payload.amount_paisa
    created_recoveries: list[WorkerAdvance] = []

    for adv_model in recon["issued_advances"]:
        if remaining_to_allocate <= 0:
            break
        adv_rem = recon["per_advance_remaining"].get(adv_model.id, 0)
        if adv_rem <= 0:
            continue

        alloc_amt = min(adv_rem, remaining_to_allocate)
        if alloc_amt > 0:
            rec_entry = WorkerAdvance(
                company_id=current_user.company_id,
                worker_id=worker.id,
                amount_paisa=alloc_amt,
                entry_type="RECOVERED",
                date=payload.date or date.today(),
                notes=payload.notes.strip() if payload.notes else f"Cash repayment against Advance #{adv_model.id}",
                actor_id=current_user.id,
                parent_advance_id=adv_model.id
            )
            db.add(rec_entry)
            created_recoveries.append(rec_entry)
            remaining_to_allocate -= alloc_amt

    if remaining_to_allocate != 0 or sum(r.amount_paisa for r in created_recoveries) != payload.amount_paisa:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to split cash repayment across advances atomically."
        )

    db.commit()
    for r in created_recoveries:
        db.refresh(r)

    primary_entry = created_recoveries[0]
    res = AdvanceResponse.model_validate(primary_entry)
    res.amount_paisa = payload.amount_paisa
    res.remaining_principal_paisa = total_debt - payload.amount_paisa
    res.allocations = [AdvanceResponse.model_validate(r) for r in created_recoveries]
    return res


@router.get("/workers/{worker_id}/history", response_model=WorkerHistoryResponse)
def get_worker_history(
    worker_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Returns complete chronological ledger for a worker:
    - Full profile with real-time outstanding advance balance
    - Advance history (ISSUED vs RECOVERED)
    - Monthly working hours & payroll records
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)

    advances = (
        db.query(WorkerAdvance)
        .filter(WorkerAdvance.company_id == current_user.company_id, WorkerAdvance.worker_id == worker.id)
        .order_by(WorkerAdvance.date.desc(), WorkerAdvance.id.desc())
        .all()
    )

    monthly_records = (
        db.query(WorkerMonthlyRecord)
        .filter(WorkerMonthlyRecord.company_id == current_user.company_id, WorkerMonthlyRecord.worker_id == worker.id)
        .order_by(WorkerMonthlyRecord.month_year.desc())
        .all()
    )

    recon = _reconcile_worker_advances(db, current_user.company_id, worker.id)
    per_adv_rem = recon["per_advance_remaining"]

    adv_responses = []
    for a in advances:
        resp = AdvanceResponse.model_validate(a)
        if a.entry_type == "ISSUED":
            resp.remaining_principal_paisa = per_adv_rem.get(a.id, 0)
        adv_responses.append(resp)

    worker_resp = _worker_to_response(worker, recon["total_outstanding_paisa"], None)

    return WorkerHistoryResponse(
        worker=worker_resp,
        advances=adv_responses,
        monthly_records=[MonthlyRecordResponse.model_validate(m) for m in monthly_records]
    )


@router.post("/monthly-payroll", response_model=MonthlyRecordResponse)
def process_monthly_payroll(
    payload: MonthlyPayrollRequest,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Process, calculate, and finalize monthly payroll for a worker:
    - Calculates gross pay for SALARY (basic + OT) or WAGE (TWH * rate + OT * Decimal('1.5') * rate)
    - Computes and applies advance deduction up to outstanding advance balance
    - If mark_as_paid=True, updates status to PAID and logs an automatic RECOVERED advance entry
    """
    worker = db.query(Worker).filter(
        Worker.id == payload.worker_id,
        Worker.company_id == current_user.company_id
    ).with_for_update().first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    # Inactive worker guardrail
    if not worker.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process payroll for an inactive worker. Worker must be reactivated first."
        )

    # 1. Immutability guard: Check if record is already finalized as PAID
    existing_record = db.query(WorkerMonthlyRecord).filter(
        WorkerMonthlyRecord.company_id == current_user.company_id,
        WorkerMonthlyRecord.worker_id == worker.id,
        WorkerMonthlyRecord.month_year == payload.month_year
    ).first()
    if existing_record and existing_record.status == "PAID":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot recalculate or modify finalized payroll for period '{payload.month_year}'. Paid records are immutable."
        )

    twh = Decimal(str(payload.total_working_hours)) if payload.total_working_hours is not None else Decimal('0.0')
    ot = Decimal(str(payload.overtime_hours)) if payload.overtime_hours is not None else Decimal('0.0')

    # 2. Fetch company HR settings
    settings = db.query(CompanyHRSettings).filter(
        CompanyHRSettings.company_id == current_user.company_id
    ).first()

    std_hours_default = Decimal("208.00")
    ot_mult_default = Decimal("1.50")
    ded_ceiling_default = 50

    company_std_hours = Decimal(str(settings.standard_monthly_hours)) if settings else std_hours_default
    company_ot_mult = Decimal(str(settings.overtime_multiplier)) if settings else ot_mult_default
    company_ceiling_pct = settings.max_advance_deduction_pct if (settings and settings.max_advance_deduction_pct is not None) else ded_ceiling_default

    eff_std_hours = Decimal(str(worker.standard_monthly_hours_override)) if worker.standard_monthly_hours_override is not None else company_std_hours

    # 3. Regular Pay computation
    if worker.pay_type == "SALARY":
        regular_pay = worker.basic_rate_paisa
    else:  # WAGE
        regular_pay = int((twh * Decimal(worker.basic_rate_paisa)).to_integral_value(rounding=ROUND_HALF_UP))

    # 4. Overtime Pay computation (Worker override takes precedence)
    if worker.overtime_rate_paisa_override and worker.overtime_rate_paisa_override > 0:
        ot_rate_snapshot = worker.overtime_rate_paisa_override
        ot_pay = int((ot * Decimal(worker.overtime_rate_paisa_override)).to_integral_value(rounding=ROUND_HALF_UP))
    else:
        ot_rate_snapshot = None
        if worker.pay_type == "SALARY":
            hourly_rate = Decimal(worker.basic_rate_paisa) / eff_std_hours
            ot_pay = int((ot * hourly_rate * company_ot_mult).to_integral_value(rounding=ROUND_HALF_UP))
        else:  # WAGE
            ot_pay = int((ot * Decimal(worker.basic_rate_paisa) * company_ot_mult).to_integral_value(rounding=ROUND_HALF_UP))

    # 5. Gross pay computation
    if payload.gross_pay_paisa is not None:
        gross_pay = payload.gross_pay_paisa
    else:
        gross_pay = regular_pay + ot_pay

    # 6. Advance deduction computation with ordinary deduction ceiling and reconciled FIFO installments (C1)
    ceiling_paisa = int((Decimal(gross_pay) * (Decimal(company_ceiling_pct) / Decimal("100"))).to_integral_value(rounding=ROUND_HALF_UP))
    available_cap = min(ceiling_paisa, gross_pay)

    recon = _reconcile_worker_advances(db, current_user.company_id, worker.id, for_update=True)
    total_debt = recon["total_outstanding_paisa"] if recon["is_ledger_consistent"] else 0

    if total_debt <= 0:
        payroll_capacity = 0
    elif payload.advance_deduction_paisa is not None:
        payroll_capacity = min(payload.advance_deduction_paisa, available_cap, total_debt)
    else:
        payroll_capacity = min(available_cap, total_debt)

    allocations = []
    remaining_capacity = payroll_capacity

    for adv in recon["issued_advances"]:
        if remaining_capacity <= 0:
            break
        rem_principal = recon["per_advance_remaining"].get(adv.id, 0)
        if rem_principal <= 0:
            continue

        if adv.installment_amount_paisa and adv.installment_amount_paisa > 0:
            installment_target = adv.installment_amount_paisa
        else:
            # Legacy advance without configured installment: recover up to remaining capacity
            installment_target = rem_principal

        deduct_for_adv = min(installment_target, rem_principal, remaining_capacity)
        if deduct_for_adv > 0:
            allocations.append((adv, deduct_for_adv))
            remaining_capacity -= deduct_for_adv

    advance_ded = sum(amt for _, amt in allocations)
    net_paid = max(0, gross_pay - advance_ded)

    # 7. Find or create Monthly Record with snapshots
    record = existing_record
    payment_status = "PAID" if payload.mark_as_paid else ("PENDING" if not record else record.status)
    payment_dt = payload.paid_date or (date.today() if payload.mark_as_paid else None)
    payment_meth = payload.payment_method or "CASH"

    if not record:
        record = WorkerMonthlyRecord(
            company_id=current_user.company_id,
            worker_id=worker.id,
            month_year=payload.month_year,
            total_working_hours=twh,
            overtime_hours=ot,
            gross_pay_paisa=gross_pay,
            advance_deduction_paisa=advance_ded,
            net_paid_paisa=net_paid,
            status=payment_status,
            paid_date=payment_dt,
            payment_method=payment_meth,
            basic_rate_paisa_snapshot=worker.basic_rate_paisa,
            standard_hours_snapshot=eff_std_hours,
            overtime_multiplier_snapshot=company_ot_mult,
            overtime_rate_paisa_snapshot=ot_rate_snapshot,
            regular_pay_paisa=regular_pay,
            overtime_pay_paisa=ot_pay,
            ceiling_pct_snapshot=company_ceiling_pct
        )
        db.add(record)
    else:
        record.total_working_hours = twh
        record.overtime_hours = ot
        record.gross_pay_paisa = gross_pay
        record.advance_deduction_paisa = advance_ded
        record.net_paid_paisa = net_paid
        record.basic_rate_paisa_snapshot = worker.basic_rate_paisa
        record.standard_hours_snapshot = eff_std_hours
        record.overtime_multiplier_snapshot = company_ot_mult
        record.overtime_rate_paisa_snapshot = ot_rate_snapshot
        record.regular_pay_paisa = regular_pay
        record.overtime_pay_paisa = ot_pay
        record.ceiling_pct_snapshot = company_ceiling_pct
        if payload.mark_as_paid:
            record.status = "PAID"
            record.paid_date = payment_dt
            record.payment_method = payment_meth

    db.flush()  # Flush so record.id is guaranteed for child foreign keys

    # 8. If marking as PAID and advances were deducted, record linked child RECOVERED entries
    if payload.mark_as_paid and advance_ded > 0:
        for adv, amt in allocations:
            recovery_entry = WorkerAdvance(
                company_id=current_user.company_id,
                worker_id=worker.id,
                amount_paisa=amt,
                entry_type="RECOVERED",
                date=payment_dt or date.today(),
                notes=f"Auto-deducted from {payload.month_year} payroll against Advance #{adv.id}",
                actor_id=current_user.id,
                parent_advance_id=adv.id,
                monthly_record_id=record.id
            )
            db.add(recovery_entry)

    db.commit()
    db.refresh(record)

    return MonthlyRecordResponse.model_validate(record)


@router.get("/settings", response_model=HRSettingsResponse)
def get_hr_settings(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Retrieve company-wide HR calculation settings (standard monthly hours, overtime multiplier, deduction ceiling).
    Strictly require_admin.
    """
    settings = db.query(CompanyHRSettings).filter(
        CompanyHRSettings.company_id == current_user.company_id
    ).first()
    if not settings:
        return HRSettingsResponse(
            id=None,
            company_id=current_user.company_id,
            standard_monthly_hours=Decimal("208.00"),
            overtime_multiplier=Decimal("1.50"),
            max_advance_deduction_pct=50,
            updated_at=None,
            updated_by_id=None
        )
    return settings


@router.put("/settings", response_model=HRSettingsResponse)
def update_hr_settings(
    payload: HRSettingsUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update company-wide HR calculation settings.
    Strictly require_admin.
    Validates standard hours (0 < hours <= 744), overtime multiplier (1.0 <= mult <= 5.0), and ceiling (1 <= pct <= 50).
    """
    settings = db.query(CompanyHRSettings).filter(
        CompanyHRSettings.company_id == current_user.company_id
    ).first()

    now = datetime.now(timezone.utc)
    if not settings:
        settings = CompanyHRSettings(
            company_id=current_user.company_id,
            standard_monthly_hours=payload.standard_monthly_hours,
            overtime_multiplier=payload.overtime_multiplier,
            max_advance_deduction_pct=payload.max_advance_deduction_pct or 50,
            updated_at=now,
            updated_by_id=current_user.id
        )
        db.add(settings)
    else:
        settings.standard_monthly_hours = payload.standard_monthly_hours
        settings.overtime_multiplier = payload.overtime_multiplier
        settings.max_advance_deduction_pct = payload.max_advance_deduction_pct or 50
        settings.updated_at = now
        settings.updated_by_id = current_user.id

    db.commit()
    db.refresh(settings)
    return settings


# ============================================================================
# SUBPHASE 4B.1: WORKER PHOTOGRAPH ENDPOINTS
# ============================================================================

@router.post("/workers/{worker_id}/photo", response_model=WorkerResponse)
async def upload_worker_photo(
    worker_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Upload and attach a worker photograph (JPEG, PNG, WEBP <= 2MB).
    Scoped to tenant company and requires editor or admin role.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    # Validate MIME type
    if file.content_type not in ALLOWED_PHOTO_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image format '{file.content_type}'. Allowed formats: JPEG, PNG, WEBP."
        )

    # Validate file extension
    raw_filename = file.filename or ""
    ext = os.path.splitext(raw_filename)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed extensions: .jpg, .jpeg, .png, .webp"
        )

    # Prevent dangerous multi-extension
    stem = os.path.splitext(raw_filename)[0]
    if any(stem.lower().endswith(bad) for bad in [".exe", ".php", ".sh", ".bat", ".cmd", ".py", ".pl", ".dll"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dangerous multi-extension filename detected."
        )

    content = await file.read()
    if len(content) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Photograph exceeds maximum size of 2 MB ({len(content) / (1024 * 1024):.2f} MB)."
        )

    # Validate header magic bytes
    is_valid_magic = (
        content.startswith(b"\xff\xd8\xff") or  # JPEG
        content.startswith(b"\x89PNG\r\n\x1a\n") or  # PNG
        (len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")  # WEBP
    )
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image payload: file content does not match image header signatures."
        )

    unique_name = f"wphoto_{worker.company_id}_{worker.id}_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(UPLOAD_PHOTO_DIR, unique_name)

    # Delete previous local photo if exists
    if worker.photo_url and "/api/v1/hr/workers/" in worker.photo_url:
        old_pattern = f"wphoto_{worker.company_id}_{worker.id}_"
        for existing in os.listdir(UPLOAD_PHOTO_DIR):
            if existing.startswith(old_pattern):
                try:
                    os.remove(os.path.join(UPLOAD_PHOTO_DIR, existing))
                except OSError:
                    pass

    with open(file_path, "wb") as f:
        f.write(content)

    worker.photo_url = f"/api/v1/hr/workers/{worker.id}/photo"
    db.commit()
    db.refresh(worker)

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)
    return _worker_to_response(worker, outstanding, None)


@router.get("/workers/{worker_id}/photo")
def get_worker_photo(
    worker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream worker photograph with tenant scoping and path traversal protection.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    prefix = f"wphoto_{worker.company_id}_{worker.id}_"
    matched_file = None
    for fname in os.listdir(UPLOAD_PHOTO_DIR):
        if fname.startswith(prefix):
            matched_file = fname
            break

    if not matched_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker photograph not found."
        )

    safe_path = _safe_resolve_path(UPLOAD_PHOTO_DIR, matched_file)
    ext = os.path.splitext(matched_file)[1].lower()
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(
        path=safe_path,
        media_type=media_map.get(ext, "image/jpeg"),
        filename=matched_file,
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.delete("/workers/{worker_id}/photo", response_model=WorkerResponse)
def delete_worker_photo(
    worker_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Remove worker photograph. Requires editor or admin role.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    prefix = f"wphoto_{worker.company_id}_{worker.id}_"
    for fname in os.listdir(UPLOAD_PHOTO_DIR):
        if fname.startswith(prefix):
            try:
                os.remove(os.path.join(UPLOAD_PHOTO_DIR, fname))
            except OSError:
                pass

    worker.photo_url = None
    db.commit()
    db.refresh(worker)

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)
    return _worker_to_response(worker, outstanding, None)


# ============================================================================
# SUBPHASE 4B.2: CONFIDENTIAL CITIZENSHIP DOCUMENT ENDPOINTS (ADMIN ONLY)
# ============================================================================

@router.post("/workers/{worker_id}/citizenship", response_model=CitizenshipDocResponse)
async def upload_citizenship_document(
    worker_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Upload and attach a sensitive citizenship document (PDF, JPEG, PNG, WEBP <= 5MB).
    STRICTLY restricted to Role.ADMIN. Files are isolated outside public webroot.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    if file.content_type not in ALLOWED_DOC_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document format '{file.content_type}'. Allowed formats: PDF, JPEG, PNG, WEBP."
        )

    raw_filename = file.filename or "citizenship_document.pdf"
    ext = os.path.splitext(raw_filename)[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed extensions: .pdf, .jpg, .jpeg, .png, .webp"
        )

    stem = os.path.splitext(raw_filename)[0]
    if any(stem.lower().endswith(bad) for bad in [".exe", ".php", ".sh", ".bat", ".cmd", ".py", ".pl", ".dll"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dangerous multi-extension filename detected."
        )

    content = await file.read()
    if len(content) > MAX_DOC_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document exceeds maximum size of 5 MB ({len(content) / (1024 * 1024):.2f} MB)."
        )

    # Magic byte verification
    is_valid_magic = (
        content.startswith(b"%PDF") or
        content.startswith(b"\xff\xd8\xff") or
        content.startswith(b"\x89PNG\r\n\x1a\n") or
        (len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
    )
    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document payload: file content does not match expected document/image headers."
        )

    # Secure company subfolder
    comp_docs_dir = os.path.join(SECURE_DOCS_DIR, f"company_{current_user.company_id}", "citizenship")
    os.makedirs(comp_docs_dir, exist_ok=True)

    # Delete previous document if exists
    if worker.citizenship_doc_path:
        old_path = os.path.join(comp_docs_dir, worker.citizenship_doc_path)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    safe_original_name = _sanitize_filename(file.filename or "citizenship_document")
    unique_doc_name = f"cit_{worker.company_id}_{worker.id}_{uuid.uuid4().hex[:16]}{ext}"
    final_path = os.path.join(comp_docs_dir, unique_doc_name)

    with open(final_path, "wb") as f:
        f.write(content)

    worker.citizenship_doc_path = unique_doc_name
    worker.citizenship_doc_name = safe_original_name
    worker.citizenship_uploaded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(worker)

    return CitizenshipDocResponse(
        has_citizenship_doc=True,
        citizenship_doc_name=worker.citizenship_doc_name,
        uploaded_at=worker.citizenship_uploaded_at
    )


@router.get("/workers/{worker_id}/citizenship")
def download_citizenship_document(
    worker_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Stream sensitive citizenship document with tenant scoping and path traversal defense.
    STRICTLY restricted to Role.ADMIN. Emits non-cacheable private headers.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    if not worker.citizenship_doc_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No citizenship document registered for this worker."
        )

    comp_docs_dir = os.path.join(SECURE_DOCS_DIR, f"company_{current_user.company_id}", "citizenship")
    file_path = _safe_resolve_path(comp_docs_dir, worker.citizenship_doc_path)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizenship document file not found on secure storage."
        )

    ext = os.path.splitext(worker.citizenship_doc_path)[1].lower()
    media_map = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }

    display_name = worker.citizenship_doc_name or f"citizenship_{worker.worker_code}{ext}"

    return FileResponse(
        path=file_path,
        media_type=media_map.get(ext, "application/octet-stream"),
        filename=display_name,
        headers={
            "Cache-Control": "private, no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f'inline; filename="{display_name}"'
        }
    )


@router.delete("/workers/{worker_id}/citizenship", status_code=status.HTTP_204_NO_CONTENT)
def delete_citizenship_document(
    worker_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Permanently delete sensitive citizenship document from secure storage.
    STRICTLY restricted to Role.ADMIN.
    """
    worker = db.query(Worker).filter(
        Worker.id == worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    if worker.citizenship_doc_path:
        comp_docs_dir = os.path.join(SECURE_DOCS_DIR, f"company_{current_user.company_id}", "citizenship")
        file_path = _safe_resolve_path(comp_docs_dir, worker.citizenship_doc_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    worker.citizenship_doc_path = None
    worker.citizenship_doc_name = None
    worker.citizenship_uploaded_at = None
    db.commit()

    return None

