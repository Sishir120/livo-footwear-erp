from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.stock_snapshot import StockSnapshot
from app.db.repository import TenantRepository

router = APIRouter(prefix="/stock", tags=["Stock Ledger"])

class SnapshotCreate(BaseModel):
    snapshot_date: Optional[str] = None  # YYYY-MM-DD, defaults to today

class StockMovementCreate(BaseModel):
    product_id: int
    quantity: float
    direction: int = Field(..., description="1 for inward, -1 for outbound")
    reference_type: Optional[str] = "manual"
    reference_id: Optional[int] = None
    notes: Optional[str] = None

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

from app.core.locks import get_stock_mutex, acquire_stock_advisory_lock

@router.post("/movements")
def create_stock_movement(
    payload: StockMovementCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Appends a stock ledger movement with explicit pessimistic row-level locking
    and atomic negative stock verification boundary check.
    """
    if payload.direction not in (-1, 1):
        raise HTTPException(status_code=400, detail="Direction must be 1 (inward) or -1 (outbound)")
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    # Before appending any outbound stock movement (direction = -1):
    if payload.direction == -1:
        # Acquire PostgreSQL distributed transaction-scoped advisory lock: (company_id << 32) | product_id
        acquire_stock_advisory_lock(db, current_user.company_id, payload.product_id)
        mutex = get_stock_mutex(current_user.company_id, payload.product_id)
        with mutex:
            # 1. Acquire an explicit pessimistic row lock on the target product variant inside current transaction:
            product = db.query(Product).filter(
                Product.id == payload.product_id,
                Product.company_id == current_user.company_id
            ).with_for_update().first()

            if not product:
                raise HTTPException(status_code=404, detail="Product not found in current company")

            # 2. Compute the current available balance inside this serialized transaction boundary:
            latest_snap = db.query(StockSnapshot).filter(
                StockSnapshot.company_id == current_user.company_id,
                StockSnapshot.product_id == payload.product_id
            ).order_by(StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).first()

            if latest_snap:
                subsequent = db.query(
                    func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
                ).filter(
                    StockMovement.company_id == current_user.company_id,
                    StockMovement.product_id == payload.product_id,
                    StockMovement.id > latest_snap.last_movement_id
                ).scalar()
                current_balance = float(latest_snap.balance) + float(subsequent)
            else:
                current_balance = float(
                    db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0))
                    .filter(
                        StockMovement.product_id == payload.product_id,
                        StockMovement.company_id == current_user.company_id
                    )
                    .scalar()
                )

            # 3. If current_balance - payload.quantity < 0:
            if current_balance - payload.quantity < 0:
                avail_str = int(current_balance) if current_balance.is_integer() else current_balance
                req_str = int(payload.quantity) if payload.quantity.is_integer() else payload.quantity
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient physical stock for this size variant (Available: {avail_str}, Requested: {req_str})"
                )

            # 4. Append the -1 movement and commit the transaction, releasing the lock.
            movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
            movement = movement_repo.create(
                product_id=payload.product_id,
                direction=payload.direction,
                quantity=payload.quantity,
                ref_type=payload.reference_type or "manual",
                ref_id=payload.reference_id,
                notes=payload.notes,
                date_ad=datetime.now().strftime("%Y-%m-%d"),
                date_bs=""
            )
            db.commit()
            db.refresh(movement)
            return movement

    # Inward movement (+1)
    product = db.query(Product).filter(
        Product.id == payload.product_id,
        Product.company_id == current_user.company_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in current company")

    movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
    movement = movement_repo.create(
        product_id=payload.product_id,
        direction=payload.direction,
        quantity=payload.quantity,
        ref_type=payload.reference_type or "manual",
        ref_id=payload.reference_id,
        notes=payload.notes,
        date_ad=datetime.now().strftime("%Y-%m-%d"),
        date_bs=""
    )
    db.commit()
    db.refresh(movement)
    return movement

@router.get("/snapshots")
def list_stock_snapshots(
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(StockSnapshot).filter(StockSnapshot.company_id == current_user.company_id)
    if product_id:
        query = query.filter(StockSnapshot.product_id == product_id)
    return query.order_by(StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).all()

@router.post("/snapshots")
def create_stock_snapshots(
    payload: Optional[SnapshotCreate] = None,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Materializes current stock balance for all products into stock_snapshots.
    Enables O(1) query scaling: Stock = Snapshot Balance + SUM(movements after last_movement_id).
    """
    target_date = date.today()
    if payload and payload.snapshot_date:
        try:
            target_date = datetime.strptime(payload.snapshot_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid snapshot_date format (expected YYYY-MM-DD)")

    product_repo = TenantRepository(Product, db, current_user.company_id)
    products = product_repo.get_all()
    if not products:
        return {"created_snapshots": 0, "snapshots": []}

    product_ids = [p.id for p in products]

    # Calculate full current balance and find max movement id for each product
    agg_rows = db.query(
        StockMovement.product_id,
        func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0).label("balance"),
        func.coalesce(func.max(StockMovement.id), 0).label("last_movement_id")
    ).filter(
        StockMovement.company_id == current_user.company_id,
        StockMovement.product_id.in_(product_ids)
    ).group_by(StockMovement.product_id).all()

    agg_map = {row.product_id: (int(row.balance), int(row.last_movement_id)) for row in agg_rows}

    created = []
    for prod in products:
        bal, last_id = agg_map.get(prod.id, (0, 0))
        # Upsert or create snapshot for (company_id, product_id, snapshot_date)
        existing = db.query(StockSnapshot).filter(
            StockSnapshot.company_id == current_user.company_id,
            StockSnapshot.product_id == prod.id,
            StockSnapshot.snapshot_date == target_date
        ).first()

        if existing:
            existing.balance = bal
            existing.last_movement_id = last_id
            created.append(existing)
        else:
            snap = StockSnapshot(
                company_id=current_user.company_id,
                product_id=prod.id,
                balance=bal,
                snapshot_date=target_date,
                last_movement_id=last_id
            )
            db.add(snap)
            created.append(snap)

    db.commit()
    return {
        "created_snapshots": len(created),
        "snapshot_date": str(target_date),
        "snapshots": [
            {
                "id": s.id,
                "product_id": s.product_id,
                "balance": s.balance,
                "last_movement_id": s.last_movement_id,
                "snapshot_date": str(s.snapshot_date)
            }
            for s in created
        ]
    }

@router.get("/balance")
def get_stock_balance(
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns current stock balance per product.
    O(1) Snapshot Math:
    Stock = Latest Snapshot Balance + SUM_{i > last_movement_id} (direction * quantity)
    Falls back to pure movement summation if no snapshot exists.
    """
    product_repo = TenantRepository(Product, db, current_user.company_id)
    products = product_repo.get_all()

    if category:
        products = [p for p in products if p.category and p.category.lower() == category.lower()]

    if not products:
        return []

    product_ids = [p.id for p in products]

    # Fetch latest snapshot per product
    all_snaps = db.query(StockSnapshot).filter(
        StockSnapshot.company_id == current_user.company_id,
        StockSnapshot.product_id.in_(product_ids)
    ).order_by(StockSnapshot.product_id, StockSnapshot.snapshot_date.desc(), StockSnapshot.id.desc()).all()

    snapshot_map = {}
    for snap in all_snaps:
        if snap.product_id not in snapshot_map:
            snapshot_map[snap.product_id] = snap

    balance_map = {}

    # Products with snapshots: base balance + movements where id > last_movement_id
    if snapshot_map:
        conditions = [
            (StockMovement.product_id == p_id) & (StockMovement.id > snap.last_movement_id)
            for p_id, snap in snapshot_map.items()
        ]
        subsequent_rows = db.query(
            StockMovement.product_id,
            func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0).label("delta")
        ).filter(
            StockMovement.company_id == current_user.company_id,
            or_(*conditions)
        ).group_by(StockMovement.product_id).all()

        delta_map = {row.product_id: float(row.delta) for row in subsequent_rows}
        for p_id, snap in snapshot_map.items():
            balance_map[p_id] = float(snap.balance) + delta_map.get(p_id, 0.0)

    # Products without snapshots: full movement summation fallback
    products_without_snapshot = [p_id for p_id in product_ids if p_id not in snapshot_map]
    if products_without_snapshot:
        pure_rows = db.query(
            StockMovement.product_id,
            func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0).label("balance")
        ).filter(
            StockMovement.company_id == current_user.company_id,
            StockMovement.product_id.in_(products_without_snapshot)
        ).group_by(StockMovement.product_id).all()
        for row in pure_rows:
            balance_map[row.product_id] = float(row.balance)

    balance_results = []
    for prod in products:
        qty = balance_map.get(prod.id, 0.0)
        balance_results.append({
            "product_id": prod.id,
            "code": prod.code,
            "name": prod.name,
            "category": prod.category,
            "size": prod.size,
            "color": prod.color,
            "unit_price": prod.unit_price,
            "current_stock_pairs": qty,
            "pending_stock": qty if qty > 0 else 0.0
        })

    return balance_results

