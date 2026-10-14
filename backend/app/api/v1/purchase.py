from decimal import Decimal
import math
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase, RawMaterialMovement
from app.db.repository import TenantRepository
from app.core.sequence import allocate_next_sequence
from app.core.locks import acquire_raw_material_mutation_lock, acquire_purchase_lock, get_purchase_mutex
from app.core.nepali_date import parse_ad_date
import uuid

router = APIRouter(prefix="/purchase", tags=["Purchase & Materials"])
purchases_router = APIRouter(prefix="/purchases", tags=["Purchase Orders & Movements"])

def generate_unique_grn_number(db: Session, company_id: int) -> str:
    for _ in range(100):
        seq = allocate_next_sequence(db, company_id, "GRN")
        candidate = f"GRN-{seq:04d}"
        if not db.query(Purchase.id).filter(Purchase.grn_number == candidate).first():
            return candidate
        # Collision fallback for multi-tenant or repeat tests
        scoped_candidate = f"GRN-C{company_id}-{seq:04d}"
        if not db.query(Purchase.id).filter(Purchase.grn_number == scoped_candidate).first():
            return scoped_candidate
    return f"GRN-{uuid.uuid4().hex[:8].upper()}"

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
    reorder_level: float = Field(0.0, ge=0.0)
    min_stock_alert: Decimal = Field(Decimal('0.0'), ge=Decimal('0.0'))

class PurchaseCreate(BaseModel):
    supplier_id: int = Field(..., gt=0)
    raw_material_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    purchase_date_ad: str = Field(..., max_length=20)
    purchase_date_bs: str = Field(..., max_length=20)
    order_date_ad: Optional[str] = Field(None, max_length=20)
    order_date_bs: Optional[str] = Field(None, max_length=20)
    receipt_date_ad: Optional[str] = Field(None, max_length=20)
    receipt_date_bs: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field("RECEIVED", max_length=20)  # ORDERED, RECEIVED
    payment_status: str = Field("unpaid", max_length=20)
    notes: Optional[str] = Field(None, max_length=500)
    carrying_in_paisa: Optional[int] = Field(0, ge=0)
    import_duty_paisa: Optional[int] = Field(0, ge=0)
    china_carrying_paisa: Optional[int] = Field(0, ge=0)
    insurance_paisa: Optional[int] = Field(0, ge=0)

class GoodsReceiptCreate(BaseModel):
    receipt_date_ad: str = Field(..., max_length=20)
    receipt_date_bs: str = Field(..., max_length=20)
    received_quantity: Decimal = Field(..., gt=0)
    carrying_in_paisa: int = Field(0, ge=0)
    import_duty_paisa: int = Field(0, ge=0)
    china_carrying_paisa: int = Field(0, ge=0)
    insurance_paisa: int = Field(0, ge=0)
    notes: Optional[str] = Field(None, max_length=500)

class MaterialAdjustmentCreate(BaseModel):
    adjustment_type: str = Field("ADJUSTMENT", max_length=32)
    quantity: Decimal = Field(..., gt=0)
    direction: int = Field(..., description="1 for inward (+), -1 for outward (-)")
    movement_date_ad: str = Field(..., max_length=20)
    movement_date_bs: str = Field(..., max_length=20)
    notes: Optional[str] = Field(None, max_length=255)

# --- Suppliers Endpoints ---
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

@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single supplier strictly scoped to current tenant company."""
    repo = TenantRepository(Supplier, db, current_user.company_id)
    supplier = repo.get_by_id(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

# --- Raw Materials Endpoints ---
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

@router.get("/raw-materials/{material_id}")
def get_raw_material(material_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single raw material strictly scoped to current tenant company."""
    repo = TenantRepository(RawMaterial, db, current_user.company_id)
    mat = repo.get_by_id(material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Raw material not found")
    return mat

# --- Shared Implementation Handlers for Purchases & Movements ---
def handle_list_purchases(
    date_from: Optional[str],
    date_to: Optional[str],
    current_user: User,
    db: Session
):
    query = db.query(Purchase).filter(Purchase.company_id == current_user.company_id)
    if date_from:
        query = query.filter(Purchase.purchase_date_ad >= date_from)
    if date_to:
        query = query.filter(Purchase.purchase_date_ad <= date_to)
    return query.order_by(Purchase.id.desc()).all()

def handle_get_purchase(purchase_id: int, current_user: User, db: Session):
    repo = TenantRepository(Purchase, db, current_user.company_id)
    purchase = repo.get_by_id(purchase_id)
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return purchase

def handle_create_purchase(data: PurchaseCreate, current_user: User, db: Session):
    supplier_repo = TenantRepository(Supplier, db, current_user.company_id)
    if not supplier_repo.get_by_id(data.supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found in current company")

    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    mat = material_repo.get_by_id(data.raw_material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Raw material not found in current company")

    repo = TenantRepository(Purchase, db, current_user.company_id)
    total_amount = data.quantity * data.unit_price

    carrying_in_paisa = int(data.carrying_in_paisa or 0)
    import_duty_paisa = int(data.import_duty_paisa or 0)
    china_carrying_paisa = int(data.china_carrying_paisa or 0)
    insurance_paisa = int(data.insurance_paisa or 0)

    # Integer-paisa landed cost precision
    qty_float = float(data.quantity)
    invoice_base_paisa = int(round(qty_float * float(data.unit_price) * 100))
    total_landed_cost_paisa = invoice_base_paisa + carrying_in_paisa + import_duty_paisa + china_carrying_paisa + insurance_paisa
    effective_unit_rate_paisa = int(math.floor(total_landed_cost_paisa / qty_float)) if qty_float > 0 else 0

    order_ad = parse_ad_date(data.order_date_ad) if data.order_date_ad else parse_ad_date(data.purchase_date_ad)
    order_bs = data.order_date_bs or data.purchase_date_bs

    status_val = (data.status or "RECEIVED").upper()

    if status_val == "ORDERED":
        purchase = repo.create(
            supplier_id=data.supplier_id,
            raw_material_id=data.raw_material_id,
            quantity=data.quantity,
            unit_price=data.unit_price,
            total_amount=total_amount,
            purchase_date_ad=data.purchase_date_ad,
            purchase_date_bs=data.purchase_date_bs,
            order_date_ad=order_ad,
            order_date_bs=order_bs,
            receipt_date_ad=None,
            receipt_date_bs=None,
            status="ORDERED",
            payment_status=data.payment_status,
            notes=data.notes,
            carrying_in_paisa=carrying_in_paisa,
            import_duty_paisa=import_duty_paisa,
            china_carrying_paisa=china_carrying_paisa,
            insurance_paisa=insurance_paisa,
            total_landed_cost_paisa=total_landed_cost_paisa,
            effective_unit_rate_paisa=effective_unit_rate_paisa,
            received_quantity=0.0,
            grn_number=None,
            received_by_id=None
        )
        db.commit()
        return purchase

    # Otherwise status is RECEIVED: acquire advisory lock, allocate GRN, append RawMaterialMovement, update current_stock
    acquire_raw_material_mutation_lock(db, current_user.company_id, data.raw_material_id)

    receipt_ad = parse_ad_date(data.receipt_date_ad) if data.receipt_date_ad else parse_ad_date(data.purchase_date_ad)
    receipt_bs = data.receipt_date_bs or data.purchase_date_bs
    grn_num = generate_unique_grn_number(db, current_user.company_id)

    purchase = repo.create(
        supplier_id=data.supplier_id,
        raw_material_id=data.raw_material_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        total_amount=total_amount,
        purchase_date_ad=data.purchase_date_ad,
        purchase_date_bs=data.purchase_date_bs,
        order_date_ad=order_ad,
        order_date_bs=order_bs,
        receipt_date_ad=receipt_ad,
        receipt_date_bs=receipt_bs,
        status="RECEIVED",
        payment_status=data.payment_status,
        notes=data.notes,
        carrying_in_paisa=carrying_in_paisa,
        import_duty_paisa=import_duty_paisa,
        china_carrying_paisa=china_carrying_paisa,
        insurance_paisa=insurance_paisa,
        total_landed_cost_paisa=total_landed_cost_paisa,
        effective_unit_rate_paisa=effective_unit_rate_paisa,
        received_quantity=qty_float,
        grn_number=grn_num,
        received_by_id=current_user.id
    )

    movement = RawMaterialMovement(
        company_id=current_user.company_id,
        raw_material_id=data.raw_material_id,
        movement_date=receipt_ad,
        movement_date_bs=receipt_bs,
        direction=1,
        quantity=qty_float,
        unit_cost_paisa=effective_unit_rate_paisa,
        movement_type="PURCHASE_RECEIPT",
        reference_voucher=grn_num,
        notes=data.notes or f"Purchase receipt {grn_num}",
        actor_id=current_user.id
    )
    db.add(movement)
    mat.current_stock += qty_float
    db.commit()
    return purchase

def handle_receive_purchase(purchase_id: int, data: GoodsReceiptCreate, current_user: User, db: Session):
    mutex = get_purchase_mutex(current_user.company_id, purchase_id)
    with mutex:
        acquire_purchase_lock(db, current_user.company_id, purchase_id)
        db.rollback()

        purchase = db.query(Purchase).filter(
            Purchase.id == purchase_id,
            Purchase.company_id == current_user.company_id
        ).with_for_update().first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        acquire_raw_material_mutation_lock(db, current_user.company_id, purchase.raw_material_id)
        db.refresh(purchase)

        if purchase.status == "RECEIVED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Purchase order #{purchase.id} has already been received (GRN: {purchase.grn_number or 'N/A'})."
            )

        material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
        mat = material_repo.get_by_id(purchase.raw_material_id)
        if not mat:
            raise HTTPException(status_code=404, detail="Raw material not found in current company")

        qty = float(data.received_quantity)
        if qty <= 0:
            raise HTTPException(status_code=422, detail="Received quantity must be greater than zero")

        carrying_in_paisa = int(data.carrying_in_paisa or 0)
        import_duty_paisa = int(data.import_duty_paisa or 0)
        china_carrying_paisa = int(data.china_carrying_paisa or 0)
        insurance_paisa = int(data.insurance_paisa or 0)

        unit_price = float(purchase.unit_price)
        invoice_base_paisa = int(round(qty * unit_price * 100))
        total_landed_cost_paisa = invoice_base_paisa + carrying_in_paisa + import_duty_paisa + china_carrying_paisa + insurance_paisa
        effective_unit_rate_paisa = int(math.floor(total_landed_cost_paisa / qty)) if qty > 0 else 0

        receipt_ad = parse_ad_date(data.receipt_date_ad)
        receipt_bs = data.receipt_date_bs

        grn_num = purchase.grn_number
        if not grn_num:
            grn_num = generate_unique_grn_number(db, current_user.company_id)

        purchase.status = "RECEIVED"
        purchase.received_quantity = qty
        purchase.receipt_date_ad = receipt_ad
        purchase.receipt_date_bs = receipt_bs
        purchase.carrying_in_paisa = carrying_in_paisa
        purchase.import_duty_paisa = import_duty_paisa
        purchase.china_carrying_paisa = china_carrying_paisa
        purchase.insurance_paisa = insurance_paisa
        purchase.total_landed_cost_paisa = total_landed_cost_paisa
        purchase.effective_unit_rate_paisa = effective_unit_rate_paisa
        purchase.grn_number = grn_num
        purchase.received_by_id = current_user.id
        if data.notes:
            purchase.notes = (purchase.notes or "") + f" | GRN Notes: {data.notes}"

        movement = RawMaterialMovement(
            company_id=current_user.company_id,
            raw_material_id=purchase.raw_material_id,
            movement_date=receipt_ad,
            movement_date_bs=receipt_bs,
            direction=1,
            quantity=qty,
            unit_cost_paisa=effective_unit_rate_paisa,
            movement_type="PURCHASE_RECEIPT",
            reference_voucher=grn_num,
            notes=data.notes or f"Goods receipt for PO #{purchase.id}",
            actor_id=current_user.id
        )
        db.add(movement)
        mat.current_stock += qty
        db.commit()
        return purchase

def handle_get_material_card(material_id: int, current_user: User, db: Session):
    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    mat = material_repo.get_by_id(material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Raw material not found in current company")

    movements = db.query(RawMaterialMovement).filter(
        RawMaterialMovement.company_id == current_user.company_id,
        RawMaterialMovement.raw_material_id == material_id
    ).order_by(RawMaterialMovement.movement_date.asc(), RawMaterialMovement.id.asc()).all()

    running = 0.0
    records = []
    for m in movements:
        running += m.quantity * m.direction
        records.append({
            "id": m.id,
            "movement_date": str(m.movement_date),
            "movement_date_bs": m.movement_date_bs,
            "direction": m.direction,
            "quantity": m.quantity,
            "unit_cost_paisa": m.unit_cost_paisa,
            "unit_cost_npr": round(m.unit_cost_paisa / 100.0, 2),
            "movement_type": m.movement_type,
            "reference_voucher": m.reference_voucher,
            "notes": m.notes,
            "running_balance": round(running, 4),
            "created_at": m.created_at.isoformat() if m.created_at else None
        })

    return {
        "material": {
            "id": mat.id,
            "code": mat.code,
            "name": mat.name,
            "unit": mat.unit,
            "reorder_level": mat.reorder_level,
            "current_stock": mat.current_stock
        },
        "current_balance": round(running, 4),
        "movements": records
    }

def handle_adjust_material(material_id: int, data: MaterialAdjustmentCreate, current_user: User, db: Session):
    if data.direction not in (1, -1):
        raise HTTPException(status_code=422, detail="Direction must be +1 (Inward) or -1 (Outward)")
    qty = float(data.quantity)
    if qty <= 0:
        raise HTTPException(status_code=422, detail="Adjustment quantity must be greater than zero")

    material_repo = TenantRepository(RawMaterial, db, current_user.company_id)
    mat = material_repo.get_by_id(material_id)
    if not mat:
        raise HTTPException(status_code=404, detail="Raw material not found in current company")

    acquire_raw_material_mutation_lock(db, current_user.company_id, material_id)

    current_balance = db.query(
        func.coalesce(func.sum(RawMaterialMovement.quantity * RawMaterialMovement.direction), 0.0)
    ).filter(
        RawMaterialMovement.company_id == current_user.company_id,
        RawMaterialMovement.raw_material_id == material_id
    ).scalar()
    current_balance = float(current_balance)

    if data.direction == -1 and current_balance < qty:
        raise HTTPException(
            status_code=422,
            detail=f"INSUFFICIENT_RAW_MATERIAL: Outward adjustment of {qty:.2f} breaches zero stock floor. Available balance: {current_balance:.2f}"
        )

    adj_seq = allocate_next_sequence(db, current_user.company_id, "ADJ")
    adj_voucher = f"ADJ-{adj_seq:04d}"

    mov_date = parse_ad_date(data.movement_date_ad)
    mov_date_bs = data.movement_date_bs

    movement = RawMaterialMovement(
        company_id=current_user.company_id,
        raw_material_id=material_id,
        movement_date=mov_date,
        movement_date_bs=mov_date_bs,
        direction=data.direction,
        quantity=qty,
        unit_cost_paisa=0,
        movement_type="ADJUSTMENT",
        reference_voucher=adj_voucher,
        notes=f"{data.adjustment_type}: {data.notes or ''}".strip(),
        actor_id=current_user.id
    )
    db.add(movement)
    mat.current_stock += data.direction * qty
    db.commit()

    new_balance = round(current_balance + data.direction * qty, 4)
    return {
        "status": "success",
        "voucher": adj_voucher,
        "direction": data.direction,
        "quantity": qty,
        "new_balance": new_balance
    }

# --- Routes on /api/v1/purchase ---
@router.get("/purchases")
def router_list_purchases(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return handle_list_purchases(date_from, date_to, current_user, db)

@router.get("/purchases/{purchase_id}")
def router_get_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_get_purchase(purchase_id, current_user, db)

@router.post("/purchases")
def router_create_purchase(data: PurchaseCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_create_purchase(data, current_user, db)

@router.post("/purchases/{purchase_id}/receive")
def router_receive_purchase(purchase_id: int, data: GoodsReceiptCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_receive_purchase(purchase_id, data, current_user, db)

@router.get("/materials/{material_id}/card")
@router.get("/raw-materials/{material_id}/card")
def router_get_material_card(material_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_get_material_card(material_id, current_user, db)

@router.post("/materials/{material_id}/adjust")
@router.post("/raw-materials/{material_id}/adjust")
def router_adjust_material(material_id: int, data: MaterialAdjustmentCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_adjust_material(material_id, data, current_user, db)

# --- Routes on /api/v1/purchases ---
@purchases_router.get("")
@purchases_router.get("/")
def direct_list_purchases(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return handle_list_purchases(date_from, date_to, current_user, db)

@purchases_router.get("/{purchase_id}")
def direct_get_purchase(purchase_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_get_purchase(purchase_id, current_user, db)

@purchases_router.post("")
@purchases_router.post("/")
def direct_create_purchase(data: PurchaseCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_create_purchase(data, current_user, db)

@purchases_router.post("/{purchase_id}/receive")
def direct_receive_purchase(purchase_id: int, data: GoodsReceiptCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_receive_purchase(purchase_id, data, current_user, db)

@purchases_router.get("/materials/{material_id}/card")
@purchases_router.get("/raw-materials/{material_id}/card")
def direct_get_material_card(material_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_get_material_card(material_id, current_user, db)

@purchases_router.post("/materials/{material_id}/adjust")
@purchases_router.post("/raw-materials/{material_id}/adjust")
def direct_adjust_material(material_id: int, data: MaterialAdjustmentCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    return handle_adjust_material(material_id, data, current_user, db)
