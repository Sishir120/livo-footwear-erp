from decimal import Decimal
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor, require_admin
from app.models.user import User
from app.models.asset import FixedAsset
from app.core.nepali_date import parse_ad_date

router = APIRouter(prefix="/fixed-assets", tags=["Fixed Assets Register"])

ALLOWED_CATEGORIES = {"MACHINERY", "MOULD", "VEHICLE", "TOOLS", "FURNITURE", "OTHER"}

class FixedAssetCreate(BaseModel):
    asset_code: str = Field(..., min_length=1, max_length=50)
    asset_name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=50)
    purchase_date_ad: str = Field(..., max_length=20)
    purchase_date_bs: str = Field(..., max_length=20)
    purchase_cost_paisa: Optional[int] = Field(None, ge=0)
    cost_npr: Optional[Decimal] = Field(None, ge=0)
    quantity: int = Field(1, ge=1)
    location: Optional[str] = Field(None, max_length=255)
    remarks: Optional[str] = Field(None, max_length=255)


@router.get("")
def list_fixed_assets(
    category: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns paginated fixed assets with total acquisition valuation in integer paisa and NPR.
    Scoped strictly to the authenticated user's company tenant.
    """
    query = db.query(FixedAsset).filter(FixedAsset.company_id == current_user.company_id)
    if category and category.upper() in ALLOWED_CATEGORIES:
        query = query.filter(FixedAsset.category == category.upper())

    total_cost_paisa = query.with_entities(
        func.coalesce(func.sum(FixedAsset.purchase_cost_paisa * FixedAsset.quantity), 0)
    ).scalar() or 0

    items = query.order_by(FixedAsset.purchase_date_ad.desc(), FixedAsset.id.desc()).offset(offset).limit(limit).all()

    return {
        "items": items,
        "total_valuation_paisa": int(total_cost_paisa),
        "total_valuation_npr": float(round(Decimal(total_cost_paisa) / Decimal(100), 2)),
        "total_count": len(items)
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_fixed_asset(
    data: FixedAssetCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Creates a new capital asset record in the Fixed Assets Register.
    Requires editor or admin role. Prevents duplicate asset codes within the company.
    """
    cat_upper = data.category.strip().upper()
    if cat_upper not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Category '{data.category}' not allowed. Allowed: {sorted(list(ALLOWED_CATEGORIES))}"
        )

    # Check unique asset_code within tenant company
    clean_code = data.asset_code.strip().upper()
    existing = db.query(FixedAsset).filter(
        FixedAsset.company_id == current_user.company_id,
        FixedAsset.asset_code == clean_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Fixed asset with code '{clean_code}' already exists in company."
        )

    # Resolve paisa
    if data.purchase_cost_paisa is not None:
        cost_paisa = data.purchase_cost_paisa
    elif data.cost_npr is not None:
        cost_paisa = int(round(float(data.cost_npr) * 100))
    else:
        cost_paisa = 0

    try:
        p_date_ad = parse_ad_date(data.purchase_date_ad)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid purchase_date_ad: {e}")

    asset = FixedAsset(
        company_id=current_user.company_id,
        asset_code=clean_code,
        asset_name=data.asset_name.strip(),
        category=cat_upper,
        purchase_date_ad=p_date_ad,
        purchase_date_bs=data.purchase_date_bs.strip(),
        purchase_cost_paisa=cost_paisa,
        quantity=data.quantity,
        location=data.location.strip() if data.location else None,
        remarks=data.remarks.strip() if data.remarks else None,
        actor_id=current_user.id
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_fixed_asset(
    asset_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Deletes a fixed asset record. Scoped strictly to tenant company.
    """
    asset = db.query(FixedAsset).filter(
        FixedAsset.id == asset_id,
        FixedAsset.company_id == current_user.company_id
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")

    db.delete(asset)
    db.commit()
    return {"message": "Asset deleted successfully", "id": asset_id}
