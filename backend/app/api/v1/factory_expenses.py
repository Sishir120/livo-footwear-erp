from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.sales import FactoryExpense
from app.core.nepali_date import parse_ad_date

router = APIRouter(prefix="/expenses/factory", tags=["Factory Operating Expenses"])

ALLOWED_EXPENSE_CATEGORIES = {
    "FACTORY_RENT",
    "ELECTRICITY_WATER",
    "GENERATOR_FUEL",
    "MACHINE_MAINTENANCE",
    "OFFICE_SUPPLIES",
    "TEA_REFRESHMENT",
    "FACTORY_LABOR",
    "OTHER"
}

class FactoryExpenseCreate(BaseModel):
    expense_date_ad: str = Field(..., max_length=20)
    expense_date_bs: str = Field(..., max_length=20)
    particular: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=32)
    amount_paisa: Optional[int] = Field(None, gt=0)
    amount_npr: Optional[Decimal] = Field(None, gt=0)
    payment_method: str = Field("CASH", max_length=32)  # CASH, BANK
    remarks: Optional[str] = Field(None, max_length=255)


@router.get("")
def list_factory_expenses(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns factory operating expenses with category and date filtering.
    Calculates total operating expense in integer paisa and NPR.
    """
    query = db.query(FactoryExpense).filter(FactoryExpense.company_id == current_user.company_id)
    if category:
        query = query.filter(FactoryExpense.category == category.upper())

    if start_date:
        try:
            s_date = parse_ad_date(start_date)
            query = query.filter(FactoryExpense.expense_date_ad >= s_date)
        except Exception:
            pass

    if end_date:
        try:
            e_date = parse_ad_date(end_date)
            query = query.filter(FactoryExpense.expense_date_ad <= e_date)
        except Exception:
            pass

    total_amount_paisa = query.with_entities(
        func.coalesce(func.sum(FactoryExpense.amount_paisa), 0)
    ).scalar() or 0

    items = query.order_by(FactoryExpense.expense_date_ad.desc(), FactoryExpense.id.desc()).offset(offset).limit(limit).all()

    return {
        "items": items,
        "total_amount_paisa": int(total_amount_paisa),
        "total_amount_npr": float(round(Decimal(total_amount_paisa) / Decimal(100), 2)),
        "count": len(items)
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_factory_expense(
    data: FactoryExpenseCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Records a general factory operating expense.
    """
    cat_upper = data.category.strip().upper()
    if cat_upper not in ALLOWED_EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category '{data.category}'. Allowed: {sorted(list(ALLOWED_EXPENSE_CATEGORIES))}"
        )

    pm_upper = data.payment_method.strip().upper()
    if pm_upper not in {"CASH", "BANK"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="payment_method must be either 'CASH' or 'BANK'"
        )

    if data.amount_paisa is not None and data.amount_paisa > 0:
        amt_paisa = data.amount_paisa
    elif data.amount_npr is not None and data.amount_npr > 0:
        amt_paisa = int(round(float(data.amount_npr) * 100))
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either amount_paisa or amount_npr must be provided and greater than zero"
        )

    try:
        exp_date_ad = parse_ad_date(data.expense_date_ad)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid expense_date_ad: {e}")

    expense = FactoryExpense(
        company_id=current_user.company_id,
        expense_date_ad=exp_date_ad,
        expense_date_bs=data.expense_date_bs.strip(),
        particular=data.particular.strip(),
        category=cat_upper,
        amount_paisa=amt_paisa,
        payment_method=pm_upper,
        remarks=data.remarks.strip() if data.remarks else None,
        actor_id=current_user.id
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}")
def delete_factory_expense(
    expense_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Deletes a factory expense.
    """
    expense = db.query(FactoryExpense).filter(
        FactoryExpense.id == expense_id,
        FactoryExpense.company_id == current_user.company_id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Factory expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Factory expense deleted successfully", "id": expense_id}
