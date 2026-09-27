from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.models.stock import Product, StockMovement
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

@router.post("/orders")
def create_sales_order(data: SalesOrderCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    # Defensive check: ensure client belongs strictly to caller's company (Tenant Isolation / IDOR prevention)
    client_repo = TenantRepository(Client, db, current_user.company_id)
    if not client_repo.get_by_id(data.client_id):
        raise HTTPException(status_code=404, detail="Client not found in current company")

    # Defensive check: ensure each product belongs strictly to caller's company
    product_repo = TenantRepository(Product, db, current_user.company_id)
    for item in data.items:
        if not product_repo.get_by_id(item.product_id):
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found in current company")

    order_repo = TenantRepository(SalesOrder, db, current_user.company_id)
    item_repo = TenantRepository(SalesItem, db, current_user.company_id)
    movement_repo = TenantRepository(StockMovement, db, current_user.company_id)

    # 1. Calculate order total
    total_amount = sum(item.quantity * item.unit_price for item in data.items)
    receivable_amount = total_amount - data.received_amount

    # 2. Create order record
    order = order_repo.create(
        order_number=data.order_number,
        client_id=data.client_id,
        order_date_ad=data.order_date_ad,
        order_date_bs=data.order_date_bs,
        status="delivered" if data.delivered else "pending",
        total_amount=total_amount,
        received_amount=data.received_amount,
        receivable_amount=receivable_amount,
        delivered=data.delivered
    )

    # 3. Create item line entries & stock movements (-1 OUT)
    for item in data.items:
        line_total = item.quantity * item.unit_price
        item_repo.create(
            sales_order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=line_total
        )

        if data.delivered:
            movement_repo.create(
                product_id=item.product_id,
                quantity=item.quantity,
                direction=-1,
                ref_type="sale",
                ref_id=order.id,
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

    payment = payment_repo.create(**data.model_dump())
    
    # Update order received & receivable balance
    order.received_amount += data.amount
    order.receivable_amount = max(0.0, order.total_amount - order.received_amount)
    
    db.commit()
    return payment
