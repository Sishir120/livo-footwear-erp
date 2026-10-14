from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.waste import WasteRecord
from app.models.purchase import RawMaterial
from app.models.stock import Product
from app.models.production import ProductionBatch
from app.core.nepali_date import parse_ad_date

router = APIRouter(prefix="/waste", tags=["Waste & Scrap Management"])

class WasteRecordCreate(BaseModel):
    waste_date_ad: str = Field(..., max_length=20)
    waste_date_bs: str = Field(..., max_length=20)
    waste_type: str = Field(..., description="RAW_MATERIAL_SCRAP or FINISHED_PAIR_REJECT")
    raw_material_id: Optional[int] = Field(None, gt=0)
    product_id: Optional[int] = Field(None, gt=0)
    batch_id: Optional[int] = Field(None, gt=0)
    quantity: float = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=20)  # kg, pcs, litre, pair
    reason: Optional[str] = Field(None, max_length=255)
    disposal_method: Optional[str] = Field("DISCARDED", max_length=64)


@router.get("")
def list_waste_records(
    waste_type: Optional[str] = Query(None),
    batch_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns waste & scrap records strictly scoped to current tenant company.
    Provides informational scrap tracking without mutating warehouse stock.
    """
    query = db.query(WasteRecord).filter(WasteRecord.company_id == current_user.company_id)
    if waste_type and waste_type.upper() in {"RAW_MATERIAL_SCRAP", "FINISHED_PAIR_REJECT"}:
        query = query.filter(WasteRecord.waste_type == waste_type.upper())
    if batch_id:
        query = query.filter(WasteRecord.batch_id == batch_id)

    items = query.order_by(WasteRecord.waste_date_ad.desc(), WasteRecord.id.desc()).offset(offset).limit(limit).all()

    # Summarize scrap quantities
    total_raw_kg = sum(w.quantity for w in items if w.waste_type == "RAW_MATERIAL_SCRAP" and w.unit == "kg")
    total_reject_pairs = sum(w.quantity for w in items if w.waste_type == "FINISHED_PAIR_REJECT")

    # Enrich with foreign names
    results = []
    for w in items:
        mat_name = None
        prod_name = None
        batch_no = None
        if w.raw_material_id:
            m = db.query(RawMaterial.name).filter(RawMaterial.id == w.raw_material_id).first()
            if m: mat_name = m[0]
        if w.product_id:
            p = db.query(Product.name).filter(Product.id == w.product_id).first()
            if p: prod_name = p[0]
        if w.batch_id:
            b = db.query(ProductionBatch.batch_number).filter(ProductionBatch.id == w.batch_id).first()
            if b: batch_no = b[0]

        results.append({
            "id": w.id,
            "company_id": w.company_id,
            "waste_date_ad": str(w.waste_date_ad),
            "waste_date_bs": w.waste_date_bs,
            "waste_type": w.waste_type,
            "raw_material_id": w.raw_material_id,
            "raw_material_name": mat_name,
            "product_id": w.product_id,
            "product_name": prod_name,
            "batch_id": w.batch_id,
            "batch_number": batch_no,
            "quantity": w.quantity,
            "unit": w.unit,
            "reason": w.reason,
            "disposal_method": w.disposal_method,
            "created_at": w.created_at.isoformat() if w.created_at else None
        })

    return {
        "items": results,
        "total_records": len(results),
        "total_raw_scrap_kg": round(total_raw_kg, 2),
        "total_reject_pairs": round(total_reject_pairs, 1)
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_waste_record(
    data: WasteRecordCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Records factory floor scrap or rejected pairs.
    Strictly audit-logging; does not automatically deduct warehouse inventory
    to prevent double-deduction against BOM batch issuance.
    """
    wt = data.waste_type.strip().upper()
    if wt not in {"RAW_MATERIAL_SCRAP", "FINISHED_PAIR_REJECT"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="waste_type must be either 'RAW_MATERIAL_SCRAP' or 'FINISHED_PAIR_REJECT'"
        )

    # Validate linked entities if supplied
    if data.raw_material_id:
        rm = db.query(RawMaterial).filter(
            RawMaterial.id == data.raw_material_id,
            RawMaterial.company_id == current_user.company_id
        ).first()
        if not rm:
            raise HTTPException(status_code=404, detail="Raw material not found in current company")

    if data.product_id:
        pr = db.query(Product).filter(
            Product.id == data.product_id,
            Product.company_id == current_user.company_id
        ).first()
        if not pr:
            raise HTTPException(status_code=404, detail="Product not found in current company")

    if data.batch_id:
        pb = db.query(ProductionBatch).filter(
            ProductionBatch.id == data.batch_id,
            ProductionBatch.company_id == current_user.company_id
        ).first()
        if not pb:
            raise HTTPException(status_code=404, detail="Production batch not found in current company")

    try:
        w_date_ad = parse_ad_date(data.waste_date_ad)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid waste_date_ad: {e}")

    record = WasteRecord(
        company_id=current_user.company_id,
        waste_date_ad=w_date_ad,
        waste_date_bs=data.waste_date_bs.strip(),
        waste_type=wt,
        raw_material_id=data.raw_material_id,
        product_id=data.product_id,
        batch_id=data.batch_id,
        quantity=float(data.quantity),
        unit=data.unit.strip().lower(),
        reason=data.reason.strip() if data.reason else None,
        disposal_method=data.disposal_method.strip().upper() if data.disposal_method else "DISCARDED",
        actor_id=current_user.id
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}")
def delete_waste_record(
    record_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Deletes a waste record.
    """
    record = db.query(WasteRecord).filter(
        WasteRecord.id == record_id,
        WasteRecord.company_id == current_user.company_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Waste record not found")

    db.delete(record)
    db.commit()
    return {"message": "Waste record deleted successfully", "id": record_id}
