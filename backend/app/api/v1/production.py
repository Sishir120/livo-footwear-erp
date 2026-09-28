from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.models.purchase import RawMaterial, Purchase
from app.models.bom import BillOfMaterials
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

class BOMItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    raw_material_id: int = Field(..., gt=0)
    quantity_required: float = Field(..., gt=0)

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

# Helper: check raw material available balance
def check_raw_material_stock(db: Session, company_id: int, raw_material_id: int, required_qty: float, material_name: str) -> float:
    total_purchased = db.query(
        func.coalesce(func.sum(Purchase.quantity), 0.0)
    ).filter(
        Purchase.company_id == company_id,
        Purchase.raw_material_id == raw_material_id
    ).scalar()

    total_used = db.query(
        func.coalesce(func.sum(ProductionMaterialUsage.quantity_used), 0.0)
    ).filter(
        ProductionMaterialUsage.company_id == company_id,
        ProductionMaterialUsage.raw_material_id == raw_material_id
    ).scalar()

    available = float(total_purchased) - float(total_used)
    if available < required_qty:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient Raw Material: {material_name} (Required: {required_qty:.2f}, Available: {available:.2f})"
        )
    return available

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

# Bill of Materials (BOM)
@router.get("/bom")
def list_boms(
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(BillOfMaterials).filter(BillOfMaterials.company_id == current_user.company_id)
    if product_id:
        query = query.filter(BillOfMaterials.product_id == product_id)
    return query.all()

@router.post("/bom")
def create_bom_item(
    data: BOMItemCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    product_repo = TenantRepository(Product, db, current_user.company_id)
    if not product_repo.get_by_id(data.product_id):
        raise HTTPException(status_code=404, detail="Product not found in current company")

    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    if not material_repo.get_by_id(data.raw_material_id):
        raise HTTPException(status_code=404, detail="Raw Material not found in current company")

    existing = db.query(BillOfMaterials).filter(
        BillOfMaterials.company_id == current_user.company_id,
        BillOfMaterials.product_id == data.product_id,
        BillOfMaterials.raw_material_id == data.raw_material_id
    ).first()

    if existing:
        existing.quantity_required = data.quantity_required
        db.commit()
        return existing

    bom = BillOfMaterials(
        company_id=current_user.company_id,
        product_id=data.product_id,
        raw_material_id=data.raw_material_id,
        quantity_required=data.quantity_required
    )
    db.add(bom)
    db.commit()
    return bom

@router.delete("/bom/{bom_id}")
def delete_bom_item(
    bom_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    bom = db.query(BillOfMaterials).filter(
        BillOfMaterials.id == bom_id,
        BillOfMaterials.company_id == current_user.company_id
    ).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM item not found")
    db.delete(bom)
    db.commit()
    return {"status": "deleted", "id": bom_id}

# Production Batches
@router.get("/batches")
def list_batches(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(ProductionBatch, db, current_user.company_id)
    return repo.get_all()

@router.post("/batches")
def create_production_batch(data: ProductionBatchCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    # Defensive check: ensure product belongs strictly to caller's company (Tenant Isolation / IDOR prevention)
    product_repo = TenantRepository(Product, db, current_user.company_id)
    product = product_repo.get_by_id(data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in current company")

    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)

    # Determine BOM vs manual usage
    boms = db.query(BillOfMaterials).filter(
        BillOfMaterials.company_id == current_user.company_id,
        BillOfMaterials.product_id == data.product_id
    ).all()

    usages_to_deduct = []

    if boms:
        # 1. Proportional BOM Deduction
        for bom in boms:
            mat = material_repo.get_by_id(bom.raw_material_id)
            if not mat:
                raise HTTPException(status_code=404, detail=f"BOM raw material {bom.raw_material_id} not found in company")
            qty_needed = float(bom.quantity_required) * float(data.produced_quantity)
            check_raw_material_stock(db, current_user.company_id, bom.raw_material_id, qty_needed, mat.name)
            usages_to_deduct.append((bom.raw_material_id, qty_needed))
    elif data.material_usages:
        # 2. Explicit manual material usage provided
        for mat in data.material_usages:
            raw_mat = material_repo.get_by_id(mat.raw_material_id)
            if not raw_mat:
                raise HTTPException(status_code=404, detail=f"Raw material {mat.raw_material_id} not found in current company")
            check_raw_material_stock(db, current_user.company_id, mat.raw_material_id, mat.quantity_used, raw_mat.name)
            usages_to_deduct.append((mat.raw_material_id, mat.quantity_used))

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

    # 2. Record material usage deductions
    for raw_mat_id, qty_used in usages_to_deduct:
        usage_repo.create(
            batch_id=batch.id,
            raw_material_id=raw_mat_id,
            quantity_used=qty_used
        )

    # 3. Write finished product stock movement (+1 IN) per RULES.md §1
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
