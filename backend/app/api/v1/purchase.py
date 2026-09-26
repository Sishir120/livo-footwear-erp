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
    code: str
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class RawMaterialCreate(BaseModel):
    code: str
    name: str
    unit: str = "kg"
    min_stock_alert: float = 0.0

class PurchaseCreate(BaseModel):
    supplier_id: int
    raw_material_id: int
    quantity: float
    unit_price: float
    purchase_date_ad: str
    purchase_date_bs: str
    payment_status: str = "unpaid"
    notes: Optional[str] = None

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
    repo = TenantRepository(Purchase, db, current_user.company_id)
    total_amount = data.quantity * data.unit_price
    purchase = repo.create(
        total_amount=total_amount,
        **data.model_dump()
    )
    db.commit()
    return purchase
