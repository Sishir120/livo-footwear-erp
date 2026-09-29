from datetime import date, datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.worker import Worker, WorkerAdvance, WorkerMonthlyRecord
from app.schemas.worker import (
    WorkerCreate,
    WorkerUpdate,
    WorkerResponse,
    CurrentMonthHours,
    AdvanceCreate,
    AdvanceResponse,
    MonthlyPayrollRequest,
    MonthlyRecordResponse,
    WorkerHistoryResponse,
)

router = APIRouter(prefix="/hr", tags=["HR Management & Payroll Ledger"])


def _calculate_outstanding_advance(db: Session, company_id: int, worker_id: int) -> int:
    """Returns exact integer paisa outstanding advance balance: sum(ISSUED) - sum(RECOVERED)."""
    issued = db.query(func.coalesce(func.sum(WorkerAdvance.amount_paisa), 0)).filter(
        WorkerAdvance.company_id == company_id,
        WorkerAdvance.worker_id == worker_id,
        WorkerAdvance.entry_type == "ISSUED"
    ).scalar() or 0

    recovered = db.query(func.coalesce(func.sum(WorkerAdvance.amount_paisa), 0)).filter(
        WorkerAdvance.company_id == company_id,
        WorkerAdvance.worker_id == worker_id,
        WorkerAdvance.entry_type == "RECOVERED"
    ).scalar() or 0

    return max(0, int(issued - recovered))


@router.get("/workers", response_model=List[WorkerResponse])
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
            total_working_hours=m_rec.total_working_hours if m_rec else 0.0,
            overtime_hours=m_rec.overtime_hours if m_rec else 0.0,
            gross_pay_paisa=m_rec.gross_pay_paisa if m_rec else 0,
            advance_deduction_paisa=m_rec.advance_deduction_paisa if m_rec else 0,
            net_paid_paisa=m_rec.net_paid_paisa if m_rec else 0,
            status=m_rec.status if m_rec else "NONE"
        )

        results.append(
            WorkerResponse(
                id=w.id,
                company_id=w.company_id,
                worker_code=w.worker_code,
                name=w.name,
                join_date=w.join_date,
                pay_type=w.pay_type,
                basic_rate_paisa=w.basic_rate_paisa,
                phone=w.phone,
                is_active=w.is_active,
                created_at=w.created_at,
                outstanding_advance_paisa=outstanding,
                current_month=current_m
            )
        )

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
        is_active=payload.is_active
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)

    return WorkerResponse(
        id=worker.id,
        company_id=worker.company_id,
        worker_code=worker.worker_code,
        name=worker.name,
        join_date=worker.join_date,
        pay_type=worker.pay_type,
        basic_rate_paisa=worker.basic_rate_paisa,
        phone=worker.phone,
        is_active=worker.is_active,
        created_at=worker.created_at,
        outstanding_advance_paisa=0,
        current_month=None
    )


@router.patch("/workers/{worker_id}", response_model=WorkerResponse)
def update_worker(
    worker_id: int,
    payload: WorkerUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Update worker profile, including toggling active/inactive status.
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
    if payload.is_active is not None:
        worker.is_active = payload.is_active

    db.commit()
    db.refresh(worker)

    outstanding = _calculate_outstanding_advance(db, current_user.company_id, worker.id)

    return WorkerResponse(
        id=worker.id,
        company_id=worker.company_id,
        worker_code=worker.worker_code,
        name=worker.name,
        join_date=worker.join_date,
        pay_type=worker.pay_type,
        basic_rate_paisa=worker.basic_rate_paisa,
        phone=worker.phone,
        is_active=worker.is_active,
        created_at=worker.created_at,
        outstanding_advance_paisa=outstanding,
        current_month=None
    )


@router.post("/advances", response_model=AdvanceResponse, status_code=status.HTTP_201_CREATED)
def record_advance(
    payload: AdvanceCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Record worker advance issued (ISSUED) or cash repayment (RECOVERED).
    Rejects viewers (403 Forbidden).
    """
    worker = db.query(Worker).filter(
        Worker.id == payload.worker_id,
        Worker.company_id == current_user.company_id
    ).first()
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

    advance = WorkerAdvance(
        company_id=current_user.company_id,
        worker_id=worker.id,
        amount_paisa=payload.amount_paisa,
        entry_type=entry_type_clean,
        date=payload.date or date.today(),
        notes=payload.notes.strip() if payload.notes else None,
        actor_id=current_user.id
    )
    db.add(advance)
    db.commit()
    db.refresh(advance)

    return AdvanceResponse.model_validate(advance)


@router.get("/workers/{worker_id}/history", response_model=WorkerHistoryResponse)
def get_worker_history(
    worker_id: int,
    current_user: User = Depends(get_current_user),
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

    worker_resp = WorkerResponse(
        id=worker.id,
        company_id=worker.company_id,
        worker_code=worker.worker_code,
        name=worker.name,
        join_date=worker.join_date,
        pay_type=worker.pay_type,
        basic_rate_paisa=worker.basic_rate_paisa,
        phone=worker.phone,
        is_active=worker.is_active,
        created_at=worker.created_at,
        outstanding_advance_paisa=outstanding,
        current_month=None
    )

    return WorkerHistoryResponse(
        worker=worker_resp,
        advances=[AdvanceResponse.model_validate(a) for a in advances],
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
    - Calculates gross pay for SALARY (basic + OT) or WAGE (TWH * rate + OT * 1.5 * rate)
    - Computes and applies advance deduction up to outstanding advance balance
    - If mark_as_paid=True, updates status to PAID and logs an automatic RECOVERED advance entry
    """
    worker = db.query(Worker).filter(
        Worker.id == payload.worker_id,
        Worker.company_id == current_user.company_id
    ).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found."
        )

    twh = payload.total_working_hours or 0.0
    ot = payload.overtime_hours or 0.0

    # 1. Gross pay computation if not explicitly provided
    if payload.gross_pay_paisa is not None:
        gross_pay = payload.gross_pay_paisa
    else:
        if worker.pay_type == "SALARY":
            # Standard monthly salary base
            base = worker.basic_rate_paisa
            # Overtime rate: (Monthly salary / 208 hours) * 1.5
            hourly_rate = float(worker.basic_rate_paisa) / 208.0
            ot_pay = int(ot * hourly_rate * 1.5)
            gross_pay = base + ot_pay
        else:
            # WAGE worker: regular hours + overtime hours at 1.5x
            reg_pay = int(twh * worker.basic_rate_paisa)
            ot_pay = int(ot * worker.basic_rate_paisa * 1.5)
            gross_pay = reg_pay + ot_pay

    # 2. Advance deduction computation
    outstanding_adv = _calculate_outstanding_advance(db, current_user.company_id, worker.id)

    if payload.advance_deduction_paisa is not None:
        advance_ded = min(payload.advance_deduction_paisa, outstanding_adv, gross_pay)
    else:
        # Default auto-deduction: recover up to outstanding advance or gross pay
        advance_ded = min(outstanding_adv, gross_pay)

    net_paid = max(0, gross_pay - advance_ded)

    # 3. Find or create Monthly Record
    record = db.query(WorkerMonthlyRecord).filter(
        WorkerMonthlyRecord.company_id == current_user.company_id,
        WorkerMonthlyRecord.worker_id == worker.id,
        WorkerMonthlyRecord.month_year == payload.month_year
    ).first()

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
            payment_method=payment_meth
        )
        db.add(record)
    else:
        record.total_working_hours = twh
        record.overtime_hours = ot
        record.gross_pay_paisa = gross_pay
        record.advance_deduction_paisa = advance_ded
        record.net_paid_paisa = net_paid
        if payload.mark_as_paid:
            record.status = "PAID"
            record.paid_date = payment_dt
            record.payment_method = payment_meth

    # 4. If marking as PAID and advance was deducted, record automated RECOVERED advance entry
    if payload.mark_as_paid and advance_ded > 0:
        recovery_entry = WorkerAdvance(
            company_id=current_user.company_id,
            worker_id=worker.id,
            amount_paisa=advance_ded,
            entry_type="RECOVERED",
            date=payment_dt or date.today(),
            notes=f"Auto-deducted from {payload.month_year} payroll",
            actor_id=current_user.id
        )
        db.add(recovery_entry)

    db.commit()
    db.refresh(record)

    return MonthlyRecordResponse.model_validate(record)
