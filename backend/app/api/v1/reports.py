from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch
from app.models.sales import SalesOrder, SalesItem
from app.db.repository import TenantRepository

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/daily")
def get_daily_report(
    date_ad: str = Query(..., description="Date AD YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Daily Report: Production, sales, and stock movement summary for a given day.
    Highest-priority feature requested by client (TASKS.md §1.5).
    """
    company_id = current_user.company_id

    # 1. Production batches on date_ad
    production_batches = db.query(ProductionBatch).filter(
        ProductionBatch.company_id == company_id,
        ProductionBatch.date_ad == date_ad
    ).all()

    total_pairs_produced = sum(b.produced_quantity for b in production_batches)
    total_workers_active = sum(b.worker_count for b in production_batches)

    # 2. Sales orders on date_ad
    sales_orders = db.query(SalesOrder).filter(
        SalesOrder.company_id == company_id,
        SalesOrder.order_date_ad == date_ad
    ).all()

    total_sales_amount = sum(o.total_amount for o in sales_orders)
    total_received_amount = sum(o.received_amount for o in sales_orders)
    total_receivable_amount = sum(o.receivable_amount for o in sales_orders)

    # 3. Stock movements summary on date_ad
    stock_in = db.query(
        func.coalesce(func.sum(StockMovement.quantity), 0.0)
    ).filter(
        StockMovement.company_id == company_id,
        StockMovement.date_ad == date_ad,
        StockMovement.direction == 1
    ).scalar()

    stock_out = db.query(
        func.coalesce(func.sum(StockMovement.quantity), 0.0)
    ).filter(
        StockMovement.company_id == company_id,
        StockMovement.date_ad == date_ad,
        StockMovement.direction == -1
    ).scalar()

    return {
        "date_ad": date_ad,
        "production": {
            "batch_count": len(production_batches),
            "total_pairs_produced": float(total_pairs_produced),
            "worker_count": total_workers_active,
            "batches": production_batches
        },
        "sales": {
            "order_count": len(sales_orders),
            "total_sales_amount": float(total_sales_amount),
            "total_received_amount": float(total_received_amount),
            "total_receivable_amount": float(total_receivable_amount),
            "orders": sales_orders
        },
        "stock_movement_summary": {
            "total_stock_in_pairs": float(stock_in),
            "total_stock_out_pairs": float(stock_out),
            "net_change_pairs": float(stock_in - stock_out)
        }
    }

@router.get("/stock")
def get_stock_report(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stock Report: Current stock by item/code, category, size, color, pending stock.
    Highest-priority feature requested by client (TASKS.md §1.5).
    """
    company_id = current_user.company_id
    product_repo = TenantRepository(Product, db, company_id)
    products = product_repo.get_all()

    if category:
        products = [p for p in products if p.category and p.category.lower() == category.lower()]

    items_report = []
    total_stock_pairs = 0.0
    total_stock_value = 0.0

    for p in products:
        current_qty = db.query(
            func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
        ).filter(
            StockMovement.company_id == company_id,
            StockMovement.product_id == p.id
        ).scalar()

        qty = float(current_qty)
        val = qty * p.unit_price
        total_stock_pairs += qty
        total_stock_value += val

        items_report.append({
            "product_id": p.id,
            "code": p.code,
            "name": p.name,
            "category": p.category,
            "size": p.size,
            "color": p.color,
            "unit_price": p.unit_price,
            "current_stock_pairs": qty,
            "estimated_value": val,
            "status": "In Stock" if qty > 10 else ("Low Stock" if qty > 0 else "Out of Stock")
        })

    return {
        "summary": {
            "total_products_count": len(products),
            "total_stock_pairs": total_stock_pairs,
            "total_stock_value": total_stock_value
        },
        "items": items_report
    }
