from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.models.stock import Product, StockMovement
from app.models.receivable import ReceivableEntry
from app.db.repository import TenantRepository

router = APIRouter(prefix="/sales", tags=["Sales & Invoicing"])

class ClientCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    contact_person: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=255)
    credit_limit: float = Field(0.0, ge=0.0)

class SalesItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0.0)

class SalesOrderCreate(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=50)
    client_id: int = Field(..., gt=0)
    order_date_ad: str = Field(..., max_length=20)
    order_date_bs: str = Field(..., max_length=20)
    received_amount: float = Field(0.0, ge=0.0)
    items: List[SalesItemCreate] = Field(..., min_length=1)
    delivered: bool = True
    supervisor_override: bool = False

class PaymentCreate(BaseModel):
    sales_order_id: int = Field(..., gt=0)
    client_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    payment_date_ad: str = Field(..., max_length=20)
    payment_date_bs: str = Field(..., max_length=20)
    payment_method: str = Field("cash", max_length=30)
    notes: Optional[str] = Field(None, max_length=500)

# Clients
@router.get("/clients")
def list_clients(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(Client, db, current_user.company_id)
    return repo.get_all()

@router.post("/clients")
def create_client(data: ClientCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    repo = TenantRepository(Client, db, current_user.company_id)
    client = repo.create(**data.model_dump())
    db.commit()
    return client

# Orders
@router.get("/orders")
def list_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(SalesOrder, db, current_user.company_id)
    orders = repo.get_all()
    # Attach items and payments
    result = []
    for ord in orders:
        items = db.query(SalesItem).filter(SalesItem.sales_order_id == ord.id, SalesItem.company_id == current_user.company_id).all()
        result.append({
            "id": ord.id,
            "order_number": ord.order_number,
            "client_id": ord.client_id,
            "order_date_ad": ord.order_date_ad,
            "order_date_bs": ord.order_date_bs,
            "status": ord.status,
            "total_amount": ord.total_amount,
            "received_amount": ord.received_amount,
            "receivable_amount": ord.receivable_amount,
            "items": items
        })
    return result

from decimal import Decimal
from contextlib import ExitStack
from sqlalchemy import func
from app.models.stock_snapshot import StockSnapshot
from app.core.currency import quantize_npr
from app.core.locks import (
    get_stock_mutex,
    acquire_stock_advisory_lock,
    acquire_client_credit_lock,
    acquire_stock_mutation_lock,
    get_client_credit_mutex,
)

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

    # Distributed PostgreSQL transaction-scoped advisory locks
    acquire_client_credit_lock(db, current_user.company_id, data.client_id)
    if data.delivered:
        targets = sorted(list(set((1, item.product_id, str(prod_map[item.product_id].size or "")) for item in data.items)))
        for wh_id, pid, sz in targets:
            acquire_stock_mutation_lock(db, current_user.company_id, wh_id, pid, sz)
            acquire_stock_advisory_lock(db, current_user.company_id, pid)

    # In-process mutexes for thread-level synchronization across concurrent requests
    credit_mutex = get_client_credit_mutex(current_user.company_id, data.client_id)
    stock_mutexes = [get_stock_mutex(current_user.company_id, pid) for pid in sorted(list(set(item.product_id for item in data.items)))] if data.delivered else []

    with ExitStack() as stack:
        stack.enter_context(credit_mutex)
        for lock in stock_mutexes:
            stack.enter_context(lock)


        # 1. Physical Stock Boundary Check
        for item in data.items:
            product = prod_map[item.product_id]

            if data.delivered:
                # Calculate current available balance within the lock boundary
                latest_snap = db.query(StockSnapshot).filter(
                    StockSnapshot.company_id == current_user.company_id,
                    StockSnapshot.product_id == item.product_id
                ).order_by(StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).first()

                if latest_snap:
                    subsequent = db.query(
                        func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
                    ).filter(
                        StockMovement.company_id == current_user.company_id,
                        StockMovement.product_id == item.product_id,
                        StockMovement.id > latest_snap.last_movement_id
                    ).scalar()
                    current_balance = float(latest_snap.balance) + float(subsequent)
                else:
                    current_balance = float(
                        db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0))
                        .filter(
                            StockMovement.product_id == item.product_id,
                            StockMovement.company_id == current_user.company_id
                        )
                        .scalar()
                    )

                if current_balance - float(item.quantity) < 0:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "error": "INSUFFICIENT_STOCK",
                            "sku": product.code,
                            "size": product.size or "",
                            "available": int(current_balance),
                            "requested": int(item.quantity),
                            "message": f"Insufficient physical stock for this size variant (Available: {int(current_balance)}, Requested: {int(item.quantity)})",
                            "Insufficient physical stock": True
                        }
                    )

        # 2. Strict Decimal Precision Currency Calculation
        total_amount_dec = quantize_npr(sum(
            quantize_npr(Decimal(str(item.quantity)) * quantize_npr(item.unit_price))
            for item in data.items
        ))
        received_dec = quantize_npr(data.received_amount)
        receivable_dec = quantize_npr(total_amount_dec - received_dec)

        total_amount = float(total_amount_dec)
        received_amount = float(received_dec)
        receivable_amount = float(receivable_dec)

        # 3. Credit Dispatch Safeguard: check customer credit limit
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
                    func.coalesce(func.sum(SalesOrder.receivable_amount), 0.0)
                ).filter(
                    SalesOrder.company_id == current_user.company_id,
                    SalesOrder.client_id == data.client_id
                ).scalar() or 0.0
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

        # 4. Create order record
        order = order_repo.create(
            order_number=data.order_number,
            client_id=data.client_id,
            order_date_ad=data.order_date_ad,
            order_date_bs=data.order_date_bs,
            status="delivered" if data.delivered else "pending",
            total_amount=total_amount,
            received_amount=received_amount,
            receivable_amount=receivable_amount,
            delivered=data.delivered
        )

        # 4. Create item line entries & stock movements (-1 OUT)
        for item in data.items:
            line_total_dec = quantize_npr(Decimal(str(item.quantity)) * quantize_npr(item.unit_price))
            item_repo.create(
                sales_order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=float(quantize_npr(item.unit_price)),
                total_price=float(line_total_dec)
            )

            if data.delivered:
                prod = prod_map.get(item.product_id)
                movement_repo.create(
                    product_id=item.product_id,
                    warehouse_id=1,
                    size=prod.size if prod else None,
                    quantity=item.quantity,
                    direction=-1,
                    ref_type="sale",
                    ref_id=order.id,
                    movement_type="SALES_OUT",
                    source_doc_ref=data.order_number,
                    actor_id=current_user.id,
                    date_ad=data.order_date_ad,
                    date_bs=data.order_date_bs,
                    notes=f"Sales Order {data.order_number}"
                )

        db.commit()
        return order

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
        amount=float(payment_amt_dec),
        payment_date_ad=data.payment_date_ad,
        payment_date_bs=data.payment_date_bs,
        payment_method=data.payment_method,
        notes=data.notes
    )

    # Update order received & receivable balance with exact Decimal quantization
    new_received_dec = quantize_npr(Decimal(str(order.received_amount)) + payment_amt_dec)
    order_total_dec = quantize_npr(order.total_amount)
    new_receivable_dec = quantize_npr(max(Decimal("0.00"), order_total_dec - new_received_dec))

    order.received_amount = float(new_received_dec)
    order.receivable_amount = float(new_receivable_dec)

    db.commit()
    return payment
