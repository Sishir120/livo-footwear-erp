from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.models.purchase import RawMaterial
from app.db.repository import TenantRepository

router = APIRouter(prefix="/production", tags=["Production & Products"])

class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    category: Optional[str] = Field("Shoe", max_length=50)
    size: Optional[str] = Field("40", max_length=20)
    color: Optional[str] = Field("Black", max_length=50)
    unit_price: float = Field(0.0, ge=0.0)

class MaterialUsageItem(BaseModel):
    raw_material_id: int = Field(..., gt=0)
    quantity_used: float = Field(..., gt=0)

class ProductionBatchCreate(BaseModel):
    batch_number: str = Field(..., min_length=1, max_length=50)
    product_id: int = Field(..., gt=0)
    target_quantity: float = Field(..., gt=0)
    produced_quantity: float = Field(..., gt=0)  # [M-01 FIX] Must be > 0; zero-pair batches are semantically invalid
    worker_count: int = Field(1, ge=1)
    date_ad: str = Field(..., max_length=20)
    date_bs: str = Field(..., max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
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
    # Defensive check: ensure product belongs strictly to caller's company (Tenant Isolation / IDOR prevention)
    product_repo = TenantRepository(Product, db, current_user.company_id)
    if not product_repo.get_by_id(data.product_id):
        raise HTTPException(status_code=404, detail="Product not found in current company")

    # Defensive check: ensure raw materials belong strictly to caller's company
    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    for mat in data.material_usages:
        if not material_repo.get_by_id(mat.raw_material_id):
            raise HTTPException(status_code=404, detail=f"Raw material {mat.raw_material_id} not found in current company")

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
