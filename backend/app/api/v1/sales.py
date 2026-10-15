from decimal import Decimal
from datetime import datetime, date, timezone
from typing import List, Optional
from contextlib import ExitStack
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor
from app.core.sequence import generate_document_number
from app.core.nepali_date import ad_to_bs_str
from app.core.currency import quantize_npr
from app.core.locks import (
    get_stock_mutex,
    acquire_stock_advisory_lock,
    acquire_client_credit_lock,
    acquire_stock_mutation_lock,
    get_client_credit_mutex,
)
from app.models.user import User
from app.models.sales import Client, SalesOrder, SalesItem, Payment, SalesExpense
from app.models.stock import Product, StockMovement, Warehouse
from app.models.stock_snapshot import StockSnapshot
from app.models.receivable import ReceivableEntry
from app.db.repository import TenantRepository

router = APIRouter(prefix="/sales", tags=["Sales & Invoicing"])

VALID_EXPENSE_CATEGORIES = {
    "DELIVERY_FREIGHT",
    "PACKING_MATERIALS",
    "SALES_COMMISSION",
    "LOADING_UNLOADING",
    "PROMOTIONAL_SAMPLE",
    "OTHER",
}
VALID_PAYMENT_METHODS = {"CASH", "BANK"}


class ClientCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    contact_person: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    credit_limit: Decimal = Field(Decimal('0.0'), ge=Decimal('0.0'))


class SalesItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=Decimal('0.0'))


class SalesOrderCreate(BaseModel):
    client_id: int = Field(..., gt=0)
    order_date_ad: str = Field(..., max_length=20)
    order_date_bs: str = Field(..., max_length=20)
    received_amount: Decimal = Field(Decimal('0.0'), ge=Decimal('0.0'))
    items: List[SalesItemCreate] = Field(..., min_length=1)
    delivered: Optional[bool] = None
    dispatch_now: Optional[bool] = False
    status: Optional[str] = None
    supervisor_override: bool = False


class DispatchRequest(BaseModel):
    dispatch_date_ad: Optional[str] = None
    dispatch_date_bs: Optional[str] = None
    carrier_name: Optional[str] = Field(None, max_length=128)
    vehicle_number: Optional[str] = Field(None, max_length=64)
    dispatch_notes: Optional[str] = Field(None, max_length=255)


class PaymentCreate(BaseModel):
    sales_order_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    payment_date_ad: str = Field(..., max_length=20)
    payment_date_bs: str = Field(..., max_length=20)
    payment_method: str = Field("cash", max_length=30)
    notes: Optional[str] = Field(None, max_length=500)


class SalesExpenseCreate(BaseModel):
    expense_date_ad: str = Field(..., max_length=10)
    expense_date_bs: str = Field(..., max_length=10)
    particular: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., max_length=32)
    amount_paisa: int = Field(..., gt=0)
    sales_order_id: Optional[int] = None
    payment_method: str = Field("CASH", max_length=32)
    remarks: Optional[str] = Field(None, max_length=255)


def _format_order(ord: SalesOrder, items: list = None) -> dict:
    taxable_paisa = sum(int(round(float(it.total_price) * 100)) for it in items) if items else int(round(float(ord.total_amount) * 100))
    vat_paisa = int(round(taxable_paisa * 0.13))
    return {
        "id": ord.id,
        "order_number": ord.order_number,
        "client_id": ord.client_id,
        "order_date_ad": ord.order_date_ad,
        "order_date_bs": ord.order_date_bs,
        "dispatch_date_ad": ord.dispatch_date_ad.isoformat() if ord.dispatch_date_ad else None,
        "dispatch_date_bs": ord.dispatch_date_bs,
        "status": ord.status,
        "total_amount": ord.total_amount,
        "received_amount": ord.received_amount,
        "receivable_amount": ord.receivable_amount,
        "delivered": ord.delivered,
        "dispatched_at": ord.dispatched_at.isoformat() if ord.dispatched_at else None,
        "dispatched_by_id": ord.dispatched_by_id,
        "dispatch_notes": ord.dispatch_notes,
        "carrier_name": ord.carrier_name,
        "vehicle_number": ord.vehicle_number,
        "taxable_amount_paisa": taxable_paisa,
        "vat_rate": 13.0,
        "vat_amount_paisa": vat_paisa,
        "total_amount_paisa": int(round(float(ord.total_amount) * 100)),
        "items": items or []
    }


# Clients
@router.get("/clients")
def list_clients(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = TenantRepository(Client, db, current_user.company_id)
    return repo.get_all(limit=limit, offset=offset)


@router.post("/clients")
def create_client(data: ClientCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(Client, db, current_user.company_id)
    client = repo.create(**data.model_dump())
    db.commit()
    return client


@router.get("/clients/{client_id}")
def get_client(client_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single client strictly scoped to current tenant company."""
    repo = TenantRepository(Client, db, current_user.company_id)
    client = repo.get_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# Orders
@router.get("/orders")
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns bounded paginated list of sales orders with optional status filter.
    Eliminates N+1 query anti-pattern by batch-fetching all line items in a single query.
    """
    query = db.query(SalesOrder).filter(SalesOrder.company_id == current_user.company_id)
    if status_filter:
        s_upper = status_filter.upper()
        if s_upper == "CONFIRMED":
            query = query.filter((SalesOrder.status.in_(["CONFIRMED", "pending"])) | (SalesOrder.delivered == False))
        elif s_upper == "DISPATCHED":
            query = query.filter((SalesOrder.status.in_(["DISPATCHED", "delivered"])) & (SalesOrder.delivered == True))
        else:
            query = query.filter(func.lower(SalesOrder.status) == status_filter.lower())

    orders = query.order_by(SalesOrder.id.desc()).offset(offset).limit(limit).all()
    if not orders:
        return []

    order_ids = [ord.id for ord in orders]
    all_items = db.query(SalesItem).filter(
        SalesItem.sales_order_id.in_(order_ids),
        SalesItem.company_id == current_user.company_id
    ).all()

    items_by_order = {}
    for item in all_items:
        items_by_order.setdefault(item.sales_order_id, []).append(item)

    return [_format_order(ord, items_by_order.get(ord.id, [])) for ord in orders]


@router.get("/orders/{order_id}")
def get_order(order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetches a single sales order strictly scoped to current tenant company."""
    repo = TenantRepository(SalesOrder, db, current_user.company_id)
    ord = repo.get_by_id(order_id)
    if not ord:
        raise HTTPException(status_code=404, detail="Sales order not found")
    items = db.query(SalesItem).filter(
        SalesItem.sales_order_id == ord.id,
        SalesItem.company_id == current_user.company_id
    ).all()
    return _format_order(ord, items)


@router.post("/orders")
def create_sales_order(data: SalesOrderCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    # Defensive check: ensure client belongs strictly to caller's company (Tenant Isolation / IDOR prevention)
    client_repo = TenantRepository(Client, db, current_user.company_id)
    if not client_repo.get_by_id(data.client_id):
        raise HTTPException(status_code=404, detail="Client not found in current company")

    order_repo = TenantRepository(SalesOrder, db, current_user.company_id)
    item_repo = TenantRepository(SalesItem, db, current_user.company_id)
    movement_repo = TenantRepository(StockMovement, db, current_user.company_id)

    # Pre-fetch products to obtain SKUs and sizes
    prod_map = {}
    for item in data.items:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.company_id == current_user.company_id
        ).with_for_update().first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found in current company")
        prod_map[item.product_id] = product

    # Determine whether to dispatch immediately or book as CONFIRMED (Phase 3 decoupling)
    should_dispatch = False
    if data.dispatch_now is True:
        should_dispatch = True
    elif data.status and data.status.upper() in ("DISPATCHED", "DELIVERED"):
        should_dispatch = True
    elif data.delivered is True and not data.status and not getattr(data, "dispatch_now", False):
        should_dispatch = True

    # Determine whether to enforce ATP check on booking
    enforce_atp = False
    if not should_dispatch:
        if data.status and data.status.upper() == "CONFIRMED":
            enforce_atp = True
        elif data.delivered is None and not data.status:
            enforce_atp = True

    # Distributed PostgreSQL transaction-scoped advisory locks
    acquire_client_credit_lock(db, current_user.company_id, data.client_id)
    if should_dispatch:
        targets = sorted(list(set((1, item.product_id, str(prod_map[item.product_id].size or "")) for item in data.items)))
        for wh_id, pid, sz in targets:
            acquire_stock_mutation_lock(db, current_user.company_id, wh_id, pid, sz)
            acquire_stock_advisory_lock(db, current_user.company_id, pid)

    # In-process mutexes for thread-level synchronization across concurrent requests
    credit_mutex = get_client_credit_mutex(current_user.company_id, data.client_id)
    stock_mutexes = [get_stock_mutex(current_user.company_id, pid) for pid in sorted(list(set(item.product_id for item in data.items)))] if should_dispatch else []

    with ExitStack() as stack:
        stack.enter_context(credit_mutex)
        for lock in stock_mutexes:
            stack.enter_context(lock)

        # 1. Strict Decimal Precision Currency Calculation
        total_amount_dec = quantize_npr(sum(
            quantize_npr(Decimal(str(item.quantity)) * quantize_npr(item.unit_price))
            for item in data.items
        ))
        received_dec = quantize_npr(data.received_amount)
        receivable_dec = quantize_npr(total_amount_dec - received_dec)

        total_amount = Decimal(total_amount_dec)
        received_amount = Decimal(received_dec)
        receivable_amount = Decimal(receivable_dec)

        # 2. Credit Dispatch Safeguard: check customer credit limit
        client = client_repo.get_by_id(data.client_id)
        if client and client.credit_limit and client.credit_limit > 0:
            ar_outstanding_paisa = db.query(
                func.coalesce(func.sum(ReceivableEntry.direction * ReceivableEntry.amount_paisa), 0)
            ).filter(
                ReceivableEntry.company_id == current_user.company_id,
                ReceivableEntry.client_id == data.client_id
            ).scalar() or 0

            if ar_outstanding_paisa == 0:
                legacy_receivable = db.query(
                    func.coalesce(func.sum(SalesOrder.receivable_amount), Decimal('0.0'))
                ).filter(
                    SalesOrder.company_id == current_user.company_id,
                    SalesOrder.client_id == data.client_id
                ).scalar() or Decimal('0.0')
                ar_outstanding_paisa = int(round(legacy_receivable * 100))

            credit_limit_paisa = int(round(client.credit_limit * 100))
            order_total_paisa = int(round(total_amount * 100))

            if (ar_outstanding_paisa + order_total_paisa) > credit_limit_paisa:
                if not getattr(data, "supervisor_override", False):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "CREDIT_LIMIT_EXCEEDED",
                            "current_outstanding_paisa": ar_outstanding_paisa,
                            "credit_limit_paisa": credit_limit_paisa,
                            "order_value_paisa": order_total_paisa,
                            "message": "Credit limit exceeded - supervisor override required",
                            "Credit limit exceeded - supervisor override required": True
                        }
                    )

        # 3. Stock Verification: Immediate Dispatch checks Physical Stock, Booking checks Available-to-Promise (ATP)
        for item in data.items:
            product = prod_map[item.product_id]

            # Calculate on-hand physical stock
            latest_snap = db.query(StockSnapshot).filter(
                StockSnapshot.company_id == current_user.company_id,
                StockSnapshot.product_id == item.product_id
            ).order_by(StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).first()

            if latest_snap:
                subsequent = db.query(
                    func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), Decimal('0.0'))
                ).filter(
                    StockMovement.company_id == current_user.company_id,
                    StockMovement.product_id == item.product_id,
                    StockMovement.id > latest_snap.last_movement_id
                ).scalar()
                current_physical = Decimal(latest_snap.balance) + Decimal(subsequent)
            else:
                current_physical = Decimal(
                    db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), Decimal('0.0')))
                    .filter(
                        StockMovement.product_id == item.product_id,
                        StockMovement.company_id == current_user.company_id
                    )
                    .scalar() or Decimal('0.0')
                )

            if should_dispatch:
                # Direct dispatch boundary check: Physical On-Hand must satisfy requested
                if current_physical - Decimal(str(item.quantity)) < Decimal('0.0'):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "INSUFFICIENT_STOCK",
                            "sku": product.code,
                            "size": product.size or "",
                            "available": int(current_physical),
                            "requested": int(item.quantity),
                            "message": f"Insufficient physical stock for this size variant (Available: {int(current_physical)}, Requested: {int(item.quantity)})",
                            "Insufficient physical stock": True
                        }
                    )
            elif enforce_atp:
                # Booking boundary check: ATP = Physical Stock - Committed Undispatched Orders
                reserved_qty = Decimal(
                    db.query(func.coalesce(func.sum(SalesItem.quantity), Decimal('0.0')))
                    .join(SalesOrder, SalesOrder.id == SalesItem.sales_order_id)
                    .filter(
                        SalesOrder.company_id == current_user.company_id,
                        SalesItem.product_id == item.product_id,
                        SalesOrder.status.in_(["CONFIRMED", "pending"]),
                        SalesOrder.delivered == False
                    )
                    .scalar() or Decimal('0.0')
                )
                atp = current_physical - reserved_qty
                if Decimal(str(item.quantity)) > atp and not getattr(data, "supervisor_override", False):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "error": "INSUFFICIENT_STOCK",
                            "code": "INSUFFICIENT_ATP",
                            "sku": product.code,
                            "size": product.size or "",
                            "available": int(max(Decimal('0.0'), atp)),
                            "requested": int(item.quantity),
                            "physical_stock": int(current_physical),
                            "reserved_stock": int(reserved_qty),
                            "available_to_promise": int(max(Decimal('0.0'), atp)),
                            "message": f"Insufficient Available-to-Promise stock (ATP: {int(max(Decimal('0.0'), atp))}, Physical: {int(current_physical)}, Reserved: {int(reserved_qty)}, Requested: {int(item.quantity)}). Supervisor override required.",
                            "Insufficient physical stock": True
                        }
                    )

        # 4. Resolve Order Status
        if should_dispatch:
            if data.status and data.status.upper() in ("DISPATCHED", "DELIVERED"):
                order_status = data.status.upper()
            elif data.dispatch_now:
                order_status = "DISPATCHED"
            else:
                order_status = "delivered"
        elif data.status:
            order_status = data.status.upper()
        elif data.delivered is False:
            order_status = "pending"
        else:
            order_status = "CONFIRMED"

        dispatch_date_ad_val = None
        if should_dispatch and data.order_date_ad:
            try:
                dispatch_date_ad_val = datetime.strptime(data.order_date_ad, "%Y-%m-%d").date()
            except ValueError:
                dispatch_date_ad_val = date.today()

        # 5. Create order record
        order = order_repo.create(
            order_number=generate_document_number(db, current_user.company_id, "SALES_ORDER", "SO"),
            client_id=data.client_id,
            order_date_ad=data.order_date_ad,
            order_date_bs=data.order_date_bs,
            dispatch_date_ad=dispatch_date_ad_val,
            dispatch_date_bs=data.order_date_bs if should_dispatch else None,
            status=order_status,
            total_amount=total_amount,
            received_amount=received_amount,
            receivable_amount=receivable_amount,
            delivered=should_dispatch,
            dispatched_at=datetime.now(timezone.utc) if should_dispatch else None,
            dispatched_by_id=current_user.id if should_dispatch else None,
        )

        # 6. Create item line entries & stock movements (-1 OUT only if dispatched)
        for item in data.items:
            line_total_dec = quantize_npr(Decimal(str(item.quantity)) * quantize_npr(item.unit_price))
            item_repo.create(
                sales_order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=Decimal(quantize_npr(item.unit_price)),
                total_price=Decimal(line_total_dec)
            )

            if should_dispatch:
                target_wh = db.query(Warehouse).filter(
                    Warehouse.company_id == current_user.company_id,
                    Warehouse.is_active == True
                ).order_by(Warehouse.id.asc()).first()
                target_wh_id = target_wh.id if target_wh else 1

                prod = prod_map.get(item.product_id)
                m_type = "SALES_DISPATCH" if data.dispatch_now else "SALES_OUT"
                movement_repo.create(
                    product_id=item.product_id,
                    warehouse_id=target_wh_id,
                    size=prod.size if prod else None,
                    quantity=item.quantity,
                    direction=-1,
                    ref_type="sale",
                    ref_id=order.id,
                    movement_type=m_type,
                    source_doc_ref=order.order_number,
                    actor_id=current_user.id,
                    date_ad=data.order_date_ad,
                    date_bs=data.order_date_bs,
                    notes=f"Sales Order {order.order_number}"
                )

        db.commit()
        db.refresh(order)
        return order


# Deferred Dispatch
@router.post("/orders/{order_id}/dispatch")
def dispatch_sales_order(
    order_id: int,
    payload: Optional[DispatchRequest] = None,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Submits an explicit physical warehouse dispatch action for a CONFIRMED sales order.
    Validates status, acquires deterministic advisory locks for all required sizes,
    verifies physical inventory, appends immutable StockMovement rows (-1), and updates order status to DISPATCHED.
    """
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id,
        SalesOrder.company_id == current_user.company_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if order.status in ("DISPATCHED", "delivered") or order.delivered is True:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order has already been dispatched")

    if order.status == "CANCELLED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot dispatch a cancelled order")

    items = db.query(SalesItem).filter(
        SalesItem.sales_order_id == order.id,
        SalesItem.company_id == current_user.company_id
    ).all()

    if not items:
        raise HTTPException(status_code=400, detail="Cannot dispatch an order with no line items")

    prod_map = {}
    for item in items:
        prod = db.query(Product).filter(
            Product.id == item.product_id,
            Product.company_id == current_user.company_id
        ).with_for_update().first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product #{item.product_id} not found")
        prod_map[item.product_id] = prod

    # Acquire deterministic transaction locks in sorted order
    targets = sorted(list(set((1, item.product_id, str(prod_map[item.product_id].size or "")) for item in items)))
    for wh_id, pid, sz in targets:
        acquire_stock_mutation_lock(db, current_user.company_id, wh_id, pid, sz)
        acquire_stock_advisory_lock(db, current_user.company_id, pid)

    stock_mutexes = [get_stock_mutex(current_user.company_id, pid) for pid in sorted(list(set(item.product_id for item in items)))]

    with ExitStack() as stack:
        for lock in stock_mutexes:
            stack.enter_context(lock)

        # Physical stock verification under lock
        for item in items:
            product = prod_map[item.product_id]

            latest_snap = db.query(StockSnapshot).filter(
                StockSnapshot.company_id == current_user.company_id,
                StockSnapshot.product_id == item.product_id
            ).order_by(StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).first()

            if latest_snap:
                subsequent = db.query(
                    func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), Decimal('0.0'))
                ).filter(
                    StockMovement.company_id == current_user.company_id,
                    StockMovement.product_id == item.product_id,
                    StockMovement.id > latest_snap.last_movement_id
                ).scalar()
                current_physical = Decimal(latest_snap.balance) + Decimal(subsequent)
            else:
                current_physical = Decimal(
                    db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), Decimal('0.0')))
                    .filter(
                        StockMovement.product_id == item.product_id,
                        StockMovement.company_id == current_user.company_id
                    )
                    .scalar() or Decimal('0.0')
                )

            if current_physical - Decimal(str(item.quantity)) < Decimal('0.0'):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "error": "INSUFFICIENT_STOCK",
                        "sku": product.code,
                        "size": product.size or "",
                        "available": int(current_physical),
                        "requested": int(item.quantity),
                        "message": f"Insufficient physical stock to dispatch SKU {product.code} (Available: {int(current_physical)}, Requested: {int(item.quantity)})",
                        "Insufficient physical stock": True
                    }
                )

        target_wh = db.query(Warehouse).filter(
            Warehouse.company_id == current_user.company_id,
            Warehouse.is_active == True
        ).order_by(Warehouse.id.asc()).first()
        target_wh_id = target_wh.id if target_wh else 1

        d_ad_str = (payload.dispatch_date_ad if payload and payload.dispatch_date_ad else None) or datetime.now().strftime("%Y-%m-%d")

        try:
            d_ad_date = datetime.strptime(d_ad_str, "%Y-%m-%d").date()
        except ValueError:
            d_ad_date = date.today()
            d_ad_str = d_ad_date.strftime("%Y-%m-%d")

        d_bs_str = (payload.dispatch_date_bs if payload and payload.dispatch_date_bs else None) or ad_to_bs_str(d_ad_date)

        movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
        for item in items:
            prod = prod_map.get(item.product_id)
            movement_repo.create(
                product_id=item.product_id,
                warehouse_id=target_wh_id,
                size=prod.size if prod else None,
                quantity=item.quantity,
                direction=-1,
                ref_type="sale",
                ref_id=order.id,
                movement_type="SALES_DISPATCH",
                source_doc_ref=order.order_number,
                actor_id=current_user.id,
                date_ad=d_ad_str,
                date_bs=d_bs_str,
                notes=f"Sales Dispatch for Order {order.order_number}" + (f" - Carrier: {payload.carrier_name}" if (payload and payload.carrier_name) else "")
            )

        order.status = "DISPATCHED"
        order.delivered = True
        order.dispatched_at = datetime.now(timezone.utc)
        order.dispatched_by_id = current_user.id
        order.dispatch_date_ad = d_ad_date
        order.dispatch_date_bs = d_bs_str
        if payload:
            order.carrier_name = payload.carrier_name
            order.vehicle_number = payload.vehicle_number
            order.dispatch_notes = payload.dispatch_notes

        db.commit()
        db.refresh(order)
        return _format_order(order, items)


# Payments
@router.post("/payments")
def record_payment(data: PaymentCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    order_repo = TenantRepository(SalesOrder, db, current_user.company_id)
    client_repo = TenantRepository(Client, db, current_user.company_id)
    payment_repo = TenantRepository(Payment, db, current_user.company_id)

    order = order_repo.get_by_id(data.sales_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    if not client_repo.get_by_id(data.client_id):
        raise HTTPException(status_code=404, detail="Client not found in current company")

    if order.client_id != data.client_id:
        raise HTTPException(status_code=400, detail="Client ID does not match sales order client")

    payment_amt_dec = quantize_npr(data.amount)
    payment = payment_repo.create(
        sales_order_id=data.sales_order_id,
        client_id=data.client_id,
        amount=Decimal(payment_amt_dec),
        payment_date_ad=data.payment_date_ad,
        payment_date_bs=data.payment_date_bs,
        payment_method=data.payment_method,
        notes=data.notes
    )

    # Update order received & receivable balance with exact Decimal quantization
    new_received_dec = quantize_npr(Decimal(str(order.received_amount)) + payment_amt_dec)
    order_total_dec = quantize_npr(order.total_amount)
    new_receivable_dec = quantize_npr(max(Decimal("0.00"), order_total_dec - new_received_dec))

    order.received_amount = Decimal(new_received_dec)
    order.receivable_amount = Decimal(new_receivable_dec)

    db.commit()
    return payment


# Sales Expenses Subledger
@router.post("/expenses")
def create_sales_expense(
    data: SalesExpenseCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Records an immutable integer-paisa sales expense in the subledger.
    """
    if data.category not in VALID_EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid expense category '{data.category}'. Allowed: {sorted(list(VALID_EXPENSE_CATEGORIES))}"
        )

    pm = data.payment_method.upper()
    if pm not in VALID_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment method '{data.payment_method}'. Allowed: {sorted(list(VALID_PAYMENT_METHODS))}"
        )

    if data.amount_paisa <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Amount in paisa must be greater than zero"
        )

    if data.sales_order_id is not None:
        order = db.query(SalesOrder).filter(
            SalesOrder.id == data.sales_order_id,
            SalesOrder.company_id == current_user.company_id
        ).first()
        if not order:
            raise HTTPException(status_code=404, detail="Referenced sales order not found in current company")

    try:
        exp_date_ad = datetime.strptime(data.expense_date_ad, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expense_date_ad format. Expected YYYY-MM-DD")

    expense = SalesExpense(
        company_id=current_user.company_id,
        expense_date_ad=exp_date_ad,
        expense_date_bs=data.expense_date_bs,
        particular=data.particular,
        category=data.category,
        amount_paisa=data.amount_paisa,
        sales_order_id=data.sales_order_id,
        payment_method=pm,
        remarks=data.remarks,
        actor_id=current_user.id
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/expenses")
def list_sales_expenses(
    category: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sales_order_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns paginated sales expenses with category/date filtering and total sum aggregation.
    """
    query = db.query(SalesExpense).filter(SalesExpense.company_id == current_user.company_id)

    if category:
        query = query.filter(SalesExpense.category == category.upper())

    if sales_order_id:
        query = query.filter(SalesExpense.sales_order_id == sales_order_id)

    if start_date:
        try:
            s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(SalesExpense.expense_date_ad >= s_date)
        except ValueError:
            pass

    if end_date:
        try:
            e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(SalesExpense.expense_date_ad <= e_date)
        except ValueError:
            pass

    total_amount_paisa = query.with_entities(
        func.coalesce(func.sum(SalesExpense.amount_paisa), 0)
    ).scalar() or 0

    items = query.order_by(SalesExpense.expense_date_ad.desc(), SalesExpense.id.desc()).offset(offset).limit(limit).all()

    return {
        "items": items,
        "total_amount_paisa": int(total_amount_paisa),
        "total_amount_npr": float(round(Decimal(total_amount_paisa) / Decimal(100), 2)),
        "count": len(items)
    }


@router.delete("/expenses/{expense_id}")
def delete_sales_expense(
    expense_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Deletes a sales expense entry (restricted to editor/admin role).
    """
    expense = db.query(SalesExpense).filter(
        SalesExpense.id == expense_id,
        SalesExpense.company_id == current_user.company_id
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Sales expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Sales expense deleted successfully", "id": expense_id}
