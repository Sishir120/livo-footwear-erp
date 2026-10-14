from decimal import Decimal
import json
import hashlib
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from app.core.sequence import generate_document_number, allocate_next_sequence
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, StockMovement, Warehouse
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.models.purchase import RawMaterial, Purchase, RawMaterialMovement
from app.models.bom import BillOfMaterials
from app.models.sync import ProductionSyncLog
from app.core.locks import get_idempotency_mutex, acquire_idempotency_advisory_lock, acquire_raw_material_mutation_lock
from app.core.nepali_date import parse_ad_date
from app.db.repository import TenantRepository

router = APIRouter(prefix="/production", tags=["Production & Products"])

class ProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    category: Optional[str] = Field("Shoe", max_length=50)
    size: Optional[str] = Field("40", max_length=20)
    color: Optional[str] = Field("Black", max_length=50)
    unit_price: Decimal = Field(Decimal('0.0'), ge=Decimal('0.0'))

class MaterialUsageItem(BaseModel):
    raw_material_id: int = Field(..., gt=0)
    quantity_used: Decimal = Field(..., gt=0)

class BOMItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    raw_material_id: int = Field(..., gt=0)
    quantity_required: Decimal = Field(..., gt=0)

class ProductionBatchCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    target_quantity: Decimal = Field(..., gt=0)
    produced_quantity: Decimal = Field(..., gt=0)  # [M-01 FIX] Must be > 0; zero-pair batches are semantically invalid
    worker_count: int = Field(1, ge=1)
    date_ad: str = Field(..., max_length=20)
    date_bs: str = Field(..., max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=50)
    material_usages: List[MaterialUsageItem] = []

# Helper: check raw material available balance from append-only movement ledger
def check_raw_material_stock(db: Session, company_id: int, raw_material_id: int, required_qty: Decimal, material_name: str) -> float:
    ledger_balance = db.query(
        func.coalesce(func.sum(RawMaterialMovement.quantity * RawMaterialMovement.direction), 0.0)
    ).filter(
        RawMaterialMovement.company_id == company_id,
        RawMaterialMovement.raw_material_id == raw_material_id
    ).scalar()

    available = Decimal(str(round(float(ledger_balance), 4)))
    if available < required_qty:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient Raw Material: {material_name} (INSUFFICIENT_RAW_MATERIAL, Required: {required_qty:.2f}, Available: {available:.2f})"
        )
    return float(available)

# Products
@router.get("/products")
def list_products(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns bounded paginated list of products strictly scoped to current tenant."""
    repo = TenantRepository(Product, db, current_user.company_id)
    return repo.get_all(limit=limit, offset=offset)

@router.post("/products")
def create_product(data: ProductCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(Product, db, current_user.company_id)
    product = repo.create(**data.model_dump())
    db.commit()
    return product

@router.get("/products/{product_id}")
def get_product(product_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single product strictly scoped to current tenant company."""
    repo = TenantRepository(Product, db, current_user.company_id)
    product = repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
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

@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single production batch strictly scoped to current tenant company."""
    repo = TenantRepository(ProductionBatch, db, current_user.company_id)
    batch = repo.get_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Production batch not found")
    return batch

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
            qty_needed = Decimal(bom.quantity_required) * Decimal(data.produced_quantity)
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
        batch_number=generate_document_number(db, current_user.company_id, "PRODUCTION", "PROD"),
        product_id=data.product_id,
        target_quantity=data.target_quantity,
        produced_quantity=data.produced_quantity,
        worker_count=data.worker_count,
        status="completed",
        date_ad=data.date_ad,
        date_bs=data.date_bs,
        notes=data.notes,
        color=data.color
    )

    # 2. Record material usage deductions and append RawMaterialMovement ledger entries
    for raw_mat_id, qty_used in usages_to_deduct:
        acquire_raw_material_mutation_lock(db, current_user.company_id, raw_mat_id)
        usage_repo.create(
            batch_id=batch.id,
            raw_material_id=raw_mat_id,
            quantity_used=qty_used
        )
        movement = RawMaterialMovement(
            company_id=current_user.company_id,
            raw_material_id=raw_mat_id,
            movement_date=parse_ad_date(data.date_ad),
            movement_date_bs=data.date_bs,
            direction=-1,
            quantity=float(qty_used),
            unit_cost_paisa=0,
            movement_type="BOM_ISSUE",
            reference_voucher=batch.batch_number,
            notes=f"Production Batch {batch.batch_number} BOM issue",
            actor_id=current_user.id
        )
        db.add(movement)
        mat = material_repo.get_by_id(raw_mat_id)
        if mat:
            mat.current_stock -= float(qty_used)

    # 3. Write finished product stock movement (+1 IN) per RULES.md §1
    target_wh = db.query(Warehouse).filter(
        Warehouse.company_id == current_user.company_id,
        Warehouse.is_active == True
    ).order_by(Warehouse.id.asc()).first()
    target_wh_id = target_wh.id if target_wh else 1

    movement_repo.create(
        product_id=data.product_id,
        warehouse_id=target_wh_id,
        size=product.size,
        quantity=data.produced_quantity,
        direction=1,
        ref_type="production",
        ref_id=batch.id,
        movement_type="PRODUCTION_IN",
        source_doc_ref=batch.batch_number,
        actor_id=current_user.id,
        date_ad=data.date_ad,
        date_bs=data.date_bs,
        notes=f"Production Batch {batch.batch_number}"
    )

    db.commit()
    return batch


class ProductionDraftSyncRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    created_at_device: Optional[str] = None
    product_id: int = Field(..., gt=0)
    warehouse_id: int = Field(1, gt=0)
    line: Optional[str] = Field("Line 1", max_length=50)
    shift: Optional[str] = Field("Shift 1", max_length=50)
    worker_count: int = Field(1, ge=1)
    date_ad: str = Field(..., max_length=20)
    date_bs: str = Field(..., max_length=20)
    size_quantities: Dict[str, Any] = Field(..., description="Mapping of continental size to quantity pairs")
    notes: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=50)


@router.post("/sync/draft")
def sync_production_draft(
    payload: ProductionDraftSyncRequest,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Idempotent server-side reconciliation endpoint for offline production batch drafts.
    Adheres to advisory-locked serialization, integer pair validation, and stock card movements.
    """
    # 1. Acquire transaction-scoped PostgreSQL advisory lock & in-process thread mutex
    acquire_idempotency_advisory_lock(db, current_user.company_id, payload.idempotency_key)
    mutex = get_idempotency_mutex(current_user.company_id, payload.idempotency_key)

    with mutex:
        # Canonical hash of incoming JSON payload
        canonical_str = json.dumps(payload.model_dump(), sort_keys=True)
        payload_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        # 2. Check if this idempotency key was already recorded
        existing_log = db.query(ProductionSyncLog).filter(
            ProductionSyncLog.company_id == current_user.company_id,
            ProductionSyncLog.idempotency_key == payload.idempotency_key
        ).first()

        if existing_log:
            if existing_log.payload_hash != payload_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key conflict: draft payload differs from previously submitted request for key '{payload.idempotency_key}'."
                )

            if existing_log.status == "ACCEPTED":
                batch = db.query(ProductionBatch).filter(
                    ProductionBatch.id == existing_log.batch_id,
                    ProductionBatch.company_id == current_user.company_id
                ).first()
                return {
                    "batch_id": existing_log.batch_id,
                    "batch_number": batch.batch_number if batch else None,
                    "sync_status": "ALREADY_ACCEPTED"
                }
            elif existing_log.status == "REJECTED":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Draft previously rejected: {existing_log.error_message}"
                )

        # 3. Model & Tenant Validation: Product must exist in current company
        product_repo = TenantRepository(Product, db, current_user.company_id)
        product = product_repo.get_by_id(payload.product_id)
        if not product:
            rejected_log = ProductionSyncLog(
                company_id=current_user.company_id,
                idempotency_key=payload.idempotency_key,
                batch_id=None,
                actor_id=current_user.id,
                payload_hash=payload_hash,
                status="REJECTED",
                error_code="MODEL_INACTIVE",
                error_message="Product not found in current company"
            )
            db.add(rejected_log)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Product not found in current company"
            )

        # 3b. Verify warehouse ownership strictly within current tenant company (Tenant Isolation / IDOR)
        target_wh = db.query(Warehouse).filter(
            Warehouse.id == payload.warehouse_id,
            Warehouse.company_id == current_user.company_id
        ).first()
        if not target_wh:
            rejected_log = ProductionSyncLog(
                company_id=current_user.company_id,
                idempotency_key=payload.idempotency_key,
                batch_id=None,
                actor_id=current_user.id,
                payload_hash=payload_hash,
                status="REJECTED",
                error_code="INVALID_WAREHOUSE",
                error_message="Warehouse not found in current company"
            )
            db.add(rejected_log)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found in current company"
            )

        # 4. Strict Non-Negative Whole Integer Size Quantities Validation
        if not payload.size_quantities or not isinstance(payload.size_quantities, dict):
            rejected_log = ProductionSyncLog(
                company_id=current_user.company_id,
                idempotency_key=payload.idempotency_key,
                batch_id=None,
                actor_id=current_user.id,
                payload_hash=payload_hash,
                status="REJECTED",
                error_code="INVALID_QUANTITY",
                error_message="Size quantities dictionary cannot be empty"
            )
            db.add(rejected_log)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Size quantities dictionary cannot be empty"
            )

        total_pairs = 0
        validated_sizes: Dict[str, int] = {}
        for sz, qty in payload.size_quantities.items():
            try:
                val = Decimal(qty)
                if val < 0 or not (val % 1 == 0):
                    raise ValueError()
                int_val = int(val)
                validated_sizes[str(sz)] = int_val
                total_pairs += int_val
            except (ValueError, TypeError):
                rejected_log = ProductionSyncLog(
                    company_id=current_user.company_id,
                    idempotency_key=payload.idempotency_key,
                    batch_id=None,
                    actor_id=current_user.id,
                    payload_hash=payload_hash,
                    status="REJECTED",
                    error_code="INVALID_QUANTITY",
                    error_message=f"Size quantity for size {sz} must be a non-negative whole integer"
                )
                db.add(rejected_log)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Size quantity for size {sz} must be a non-negative whole integer"
                )

        if total_pairs <= 0:
            rejected_log = ProductionSyncLog(
                company_id=current_user.company_id,
                idempotency_key=payload.idempotency_key,
                batch_id=None,
                actor_id=current_user.id,
                payload_hash=payload_hash,
                status="REJECTED",
                error_code="INVALID_QUANTITY",
                error_message="Total produced pairs must be greater than zero"
            )
            db.add(rejected_log)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Total produced pairs must be greater than zero"
            )

        # 5. Monotonic Batch Number Generation
        batch_seq = allocate_next_sequence(db, current_user.company_id, "BATCH")
        batch_num = f"BATCH-{batch_seq:04d}"

        # 6. Insert ProductionBatch
        notes_str = payload.notes or f"Offline sync run: {payload.line or 'Main'} / {payload.shift or 'Shift 1'}"
        batch = ProductionBatch(
            company_id=current_user.company_id,
            batch_number=batch_num,
            product_id=payload.product_id,
            target_quantity=Decimal(total_pairs),
            produced_quantity=Decimal(total_pairs),
            worker_count=payload.worker_count,
            status="completed",
            date_ad=payload.date_ad,
            date_bs=payload.date_bs,
            notes=notes_str,
            color=payload.color
        )
        db.add(batch)
        db.flush()

        # 7. BOM Deductions if present
        boms = db.query(BillOfMaterials).filter(
            BillOfMaterials.company_id == current_user.company_id,
            BillOfMaterials.product_id == payload.product_id
        ).all()
        for bom in boms:
            qty_needed = Decimal(bom.quantity_required) * Decimal(total_pairs)
            mat = db.query(RawMaterial).filter(
                RawMaterial.company_id == current_user.company_id,
                RawMaterial.id == bom.raw_material_id
            ).first()
            if mat:
                check_raw_material_stock(db, current_user.company_id, bom.raw_material_id, qty_needed, mat.name)
            acquire_raw_material_mutation_lock(db, current_user.company_id, bom.raw_material_id)
            db.add(ProductionMaterialUsage(
                company_id=current_user.company_id,
                batch_id=batch.id,
                raw_material_id=bom.raw_material_id,
                quantity_used=qty_needed
            ))
            db.add(RawMaterialMovement(
                company_id=current_user.company_id,
                raw_material_id=bom.raw_material_id,
                movement_date=parse_ad_date(payload.date_ad),
                movement_date_bs=payload.date_bs,
                direction=-1,
                quantity=float(qty_needed),
                unit_cost_paisa=0,
                movement_type="BOM_ISSUE",
                reference_voucher=batch.batch_number,
                notes=f"Production Batch {batch.batch_number} BOM issue",
                actor_id=current_user.id
            ))
            if mat:
                mat.current_stock -= float(qty_needed)

        # 8. Append StockMovement (+1 INWARD per size)
        movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
        for sz, qty in validated_sizes.items():
            if qty > 0:
                variant = db.query(Product).filter(
                    Product.company_id == current_user.company_id,
                    Product.name == product.name,
                    Product.size == sz
                ).first() or product

                movement_repo.create(
                    product_id=variant.id,
                    warehouse_id=payload.warehouse_id,
                    size=sz,
                    quantity=Decimal(qty),
                    direction=1,
                    ref_type="production",
                    ref_id=batch.id,
                    movement_type="PRODUCTION_IN",
                    source_doc_ref=batch_num,
                    actor_id=current_user.id,
                    date_ad=payload.date_ad,
                    date_bs=payload.date_bs,
                    notes=f"Production batch {batch_num} - Size {sz}"
                )

        # 9. Record ACCEPTED in production_sync_logs
        sync_log = ProductionSyncLog(
            company_id=current_user.company_id,
            idempotency_key=payload.idempotency_key,
            batch_id=batch.id,
            actor_id=current_user.id,
            payload_hash=payload_hash,
            status="ACCEPTED",
            error_code=None,
            error_message=None
        )
        db.add(sync_log)
        db.commit()

        return {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "sync_status": "ACCEPTED"
        }
