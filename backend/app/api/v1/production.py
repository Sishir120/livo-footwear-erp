from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.db.repository import TenantRepository

router = APIRouter(prefix="/production", tags=["Production & Products"])

class ProductCreate(BaseModel):
    code: str
    name: str
    category: Optional[str] = "Shoe"
    size: Optional[str] = "40"
    color: Optional[str] = "Black"
    unit_price: float = 0.0

class MaterialUsageItem(BaseModel):
    raw_material_id: int
    quantity_used: float

class ProductionBatchCreate(BaseModel):
    batch_number: str
    product_id: int
    target_quantity: float
    produced_quantity: float
    worker_count: int = 1
    date_ad: str
    date_bs: str
    notes: Optional[str] = None
    material_usages: List[MaterialUsageItem] = []

# Products
@router.get("/products")
def list_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(Product, db, current_user.company_id)
    return repo.get_all()

@router.post("/products")
def create_product(data: ProductCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(Product, db, current_user.company_id)
    product = repo.create(**data.model_dump())
    db.commit()
    return product

# Production Batches
@router.get("/batches")
def list_batches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(ProductionBatch, db, current_user.company_id)
    return repo.get_all()

@router.post("/batches")
def create_production_batch(data: ProductionBatchCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    batch_repo = TenantRepository(ProductionBatch, db, current_user.company_id)
    movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
    usage_repo = TenantRepository(ProductionMaterialUsage, db, current_user.company_id)

    # 1. Create batch record
    batch = batch_repo.create(
        batch_number=data.batch_number,
        product_id=data.product_id,
        target_quantity=data.target_quantity,
        produced_quantity=data.produced_quantity,
        worker_count=data.worker_count,
        status="completed",
        date_ad=data.date_ad,
        date_bs=data.date_bs,
        notes=data.notes
    )

    # 2. Record material usage if any
    for mat in data.material_usages:
        usage_repo.create(
            batch_id=batch.id,
            raw_material_id=mat.raw_material_id,
            quantity_used=mat.quantity_used
        )

    # 3. Write stock movement (+1 IN) per RULES.md §1
    movement_repo.create(
        product_id=data.product_id,
        quantity=data.produced_quantity,
        direction=1,
        ref_type="production",
        ref_id=batch.id,
        date_ad=data.date_ad,
        date_bs=data.date_bs,
        notes=f"Production Batch {data.batch_number}"
    )

    db.commit()
    return batch
