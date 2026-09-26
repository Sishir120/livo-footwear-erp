from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.db.repository import TenantRepository

router = APIRouter(prefix="/stock", tags=["Stock Ledger"])

@router.get("/movements")
def list_stock_movements(
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = TenantRepository(StockMovement, db, current_user.company_id)
    if product_id:
        return repo.filter(StockMovement.product_id == product_id)
    return repo.get_all()

@router.get("/balance")
def get_stock_balance(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns current stock balance per product derived from SUM(direction * quantity)
    in the stock_movements ledger as mandated by RULES.md §1.
    """
    product_repo = TenantRepository(Product, db, current_user.company_id)
    products = product_repo.get_all()
    
    if category:
        products = [p for p in products if p.category and p.category.lower() == category.lower()]

    balance_results = []
    for prod in products:
        qty = db.query(
            func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
        ).filter(
            StockMovement.company_id == current_user.company_id,
            StockMovement.product_id == prod.id
        ).scalar()

        balance_results.append({
            "product_id": prod.id,
            "code": prod.code,
            "name": prod.name,
            "category": prod.category,
            "size": prod.size,
            "color": prod.color,
            "unit_price": prod.unit_price,
            "current_stock_pairs": float(qty),
            "pending_stock": float(qty) if float(qty) > 0 else 0.0
        })

    return balance_results
