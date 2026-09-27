from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.db.repository import TenantRepository

router = APIRouter(prefix="/purchase", tags=["Purchase & Materials"])

# Schemas
class SupplierCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    contact_person: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)

class RawMaterialCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    unit: str = Field("kg", max_length=20)
    min_stock_alert: float = Field(0.0, ge=0.0)

class PurchaseCreate(BaseModel):
    supplier_id: int = Field(..., gt=0)
    raw_material_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    purchase_date_ad: str = Field(..., max_length=20)
    purchase_date_bs: str = Field(..., max_length=20)
    payment_status: str = Field("unpaid", max_length=20)
    notes: Optional[str] = Field(None, max_length=500)

# Suppliers
@router.get("/suppliers")
def list_suppliers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(Supplier, db, current_user.company_id)
    return repo.get_all()

@router.post("/suppliers")
def create_supplier(data: SupplierCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(Supplier, db, current_user.company_id)
    supplier = repo.create(**data.model_dump())
    db.commit()
    return supplier

# Raw Materials
@router.get("/raw-materials")
def list_raw_materials(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(RawMaterial, db, current_user.company_id)
    return repo.get_all()

@router.post("/raw-materials")
def create_raw_material(data: RawMaterialCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(RawMaterial, db, current_user.company_id)
    material = repo.create(**data.model_dump())
    db.commit()
    return material

# Purchases
@router.get("/purchases")
def list_purchases(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Purchase).filter(Purchase.company_id == current_user.company_id)
    if date_from:
        query = query.filter(Purchase.purchase_date_ad >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date_ad <= date_to)
    return query.all()


@router.post("/purchases")
def create_purchase(data: PurchaseCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    # Defensive check: ensure supplier and raw_material belong strictly to caller's company (Tenant Isolation / IDOR prevention)
    supplier_repo = TenantRepository(Supplier, db, current_user.company_id)
    if not supplier_repo.get_by_id(data.supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found in current company")

    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    if not material_repo.get_by_id(data.raw_material_id):
        raise HTTPException(status_code=404, detail="Raw material not found in current company")

    repo = TenantRepository(Purchase, db, current_user.company_id)
    total_amount = data.quantity * data.unit_price
    purchase = repo.create(
        total_amount=total_amount,
        **data.model_dump()
    )
    db.commit()
    return purchase
