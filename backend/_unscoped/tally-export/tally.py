from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.sales import SalesOrder, Client, Payment
from app.models.purchase import Purchase, Supplier, RawMaterial
from app.models.production import ProductionBatch
from app.models.invoice import Invoice
from app.models.stock import Product, StockMovement
from app.models.accounting import AccountGroup, LedgerAccount, JournalVoucher, JournalEntry
from app.db.repository import TenantRepository

router = APIRouter(prefix="/tally", tags=["Tally Prime Financial Engine"])

class JournalEntryItem(BaseModel):
    ledger_id: int
    debit_amount: float = 0.0
    credit_amount: float = 0.0

class JournalVoucherCreate(BaseModel):
    voucher_number: str
    voucher_type: str = "Journal"  # Sales, Purchase, Payment, Receipt, Journal
    date_ad: str
    date_bs: str
    narration: Optional[str] = None
    entries: List[JournalEntryItem]

@router.get("/daybook")
def get_tally_daybook(
    date_ad: str = Query(..., description="Date AD YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tally Prime Day Book: Consolidates all Sales Vouchers, Purchase Vouchers,
    Payment Receipts, and Production Batches for a specific day.
    """
    company_id = current_user.company_id
    vouchers = []

    # 1. Sales Orders / Invoices
    sales = db.query(SalesOrder).filter(
        SalesOrder.company_id == company_id,
        SalesOrder.order_date_ad == date_ad
    ).all()

    for s in sales:
        client = db.query(Client).filter(Client.id == s.client_id).first()
        vouchers.append({
            "id": f"sales-{s.id}",
            "voucher_type": "Sales Voucher",
            "voucher_number": s.order_number,
            "particulars": f"Sales Account / {client.name if client else 'Customer'}",
            "debit_amount": s.total_amount,
            "credit_amount": 0.0,
            "narration": f"Sales Order for {s.total_amount:,.2f}"
        })

    # 2. Raw Material Purchases
    purchases = db.query(Purchase).filter(
        Purchase.company_id == company_id,
        Purchase.purchase_date_ad == date_ad
    ).all()

    for p in purchases:
        supplier = db.query(Supplier).filter(Supplier.id == p.supplier_id).first()
        mat = db.query(RawMaterial).filter(RawMaterial.id == p.raw_material_id).first()
        vouchers.append({
            "id": f"purchase-{p.id}",
            "voucher_type": "Purchase Voucher",
            "voucher_number": f"PUR-{p.id:04d}",
            "particulars": f"Purchase Account / {supplier.name if supplier else 'Supplier'}",
            "debit_amount": 0.0,
            "credit_amount": p.total_amount,
            "narration": f"Purchased {p.quantity} {mat.unit if mat else ''} of {mat.name if mat else ''}"
        })

    # 3. Payments / Receipts
    payments = db.query(Payment).filter(
        Payment.company_id == company_id,
        Payment.payment_date_ad == date_ad
    ).all()

    for pay in payments:
        client = db.query(Client).filter(Client.id == pay.client_id).first()
        vouchers.append({
            "id": f"payment-{pay.id}",
            "voucher_type": "Receipt Voucher",
            "voucher_number": f"REC-{pay.id:04d}",
            "particulars": f"Cash/Bank Account ← {client.name if client else 'Client'}",
            "debit_amount": pay.amount,
            "credit_amount": 0.0,
            "narration": f"Payment received via {pay.payment_method}"
        })

    total_debit = sum(v["debit_amount"] for v in vouchers)
    total_credit = sum(v["credit_amount"] for v in vouchers)

    return {
        "date_ad": date_ad,
        "voucher_count": len(vouchers),
        "total_debit": total_debit,
        "total_credit": total_credit,
        "vouchers": vouchers
    }

@router.get("/trial-balance")
def get_tally_trial_balance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tally Prime Trial Balance: Computes total assets, liabilities, income, and expenses.
    """
    company_id = current_user.company_id

    total_sales = db.query(func.coalesce(func.sum(SalesOrder.total_amount), 0.0)).filter(
        SalesOrder.company_id == company_id
    ).scalar()

    total_purchases = db.query(func.coalesce(func.sum(Purchase.total_amount), 0.0)).filter(
        Purchase.company_id == company_id
    ).scalar()

    total_cash_received = db.query(func.coalesce(func.sum(SalesOrder.received_amount), 0.0)).filter(
        SalesOrder.company_id == company_id
    ).scalar()

    total_receivables = db.query(func.coalesce(func.sum(SalesOrder.receivable_amount), 0.0)).filter(
        SalesOrder.company_id == company_id
    ).scalar()

    # Derived stock inventory value
    products = db.query(Product).filter(Product.company_id == company_id).all()
    inventory_value = 0.0
    for prod in products:
        qty = db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)).filter(
            StockMovement.company_id == company_id,
            StockMovement.product_id == prod.id
        ).scalar()
        inventory_value += (float(qty) * prod.unit_price)

    groups = [
        {"group": "Sales Accounts (Income)", "debit": 0.0, "credit": float(total_sales)},
        {"group": "Purchase Accounts (Expense)", "debit": float(total_purchases), "credit": 0.0},
        {"group": "Cash / Bank Accounts (Asset)", "debit": float(total_cash_received), "credit": 0.0},
        {"group": "Sundry Debtors / Receivables (Asset)", "debit": float(total_receivables), "credit": 0.0},
        {"group": "Stock-in-Hand (Asset)", "debit": float(inventory_value), "credit": 0.0},
    ]

    total_debits = sum(g["debit"] for g in groups)
    total_credits = sum(g["credit"] for g in groups)

    return {
        "groups": groups,
        "total_debit": total_debits,
        "total_credit": total_credits,
        "is_balanced": abs(total_debits - total_credits) < 0.01
    }

@router.get("/profit-loss")
def get_tally_profit_loss(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tally Prime Profit & Loss Statement (P&L): Revenue - Cost of Goods Sold = Net Profit.
    """
    company_id = current_user.company_id

    gross_sales = float(db.query(func.coalesce(func.sum(SalesOrder.total_amount), 0.0)).filter(
        SalesOrder.company_id == company_id
    ).scalar())

    material_cost = float(db.query(func.coalesce(func.sum(Purchase.total_amount), 0.0)).filter(
        Purchase.company_id == company_id
    ).scalar())

    gross_profit = gross_sales - material_cost
    profit_margin_pct = (gross_profit / gross_sales * 100) if gross_sales > 0 else 0.0

    return {
        "trading_account": {
            "gross_sales_revenue": gross_sales,
            "raw_material_purchases": material_cost,
            "gross_profit": gross_profit,
            "gross_profit_margin_pct": round(profit_margin_pct, 2)
        },
        "net_profit": gross_profit
    }

@router.get("/outstanding")
def get_tally_outstanding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tally Prime Outstanding Aging Report: Sundry Debtors (Clients) Receivable Balances.
    """
    company_id = current_user.company_id
    clients = db.query(Client).filter(Client.id == company_id).all() if False else db.query(Client).filter(Client.company_id == company_id).all()

    receivables_list = []
    total_outstanding = 0.0

    for c in clients:
        due = db.query(func.coalesce(func.sum(SalesOrder.receivable_amount), 0.0)).filter(
            SalesOrder.company_id == company_id,
            SalesOrder.client_id == c.id
        ).scalar()
        due_val = float(due)
        total_outstanding += due_val

        receivables_list.append({
            "client_id": c.id,
            "code": c.code,
            "name": c.name,
            "contact": c.phone or "N/A",
            "credit_limit": c.credit_limit,
            "outstanding_receivable": due_val,
            "status": "Overdue" if due_val > c.credit_limit and c.credit_limit > 0 else "Normal"
        })

    return {
        "total_outstanding_receivables": total_outstanding,
        "clients": receivables_list
    }
