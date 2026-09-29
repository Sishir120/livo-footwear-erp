from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_snapshot import StockSnapshot
from app.db.repository import TenantRepository
from app.config import settings

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

class StockAdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: Optional[int] = 1
    size: Optional[str] = None
    quantity_delta: float
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
    supervisor_token: Optional[str] = None

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

from app.core.locks import get_stock_mutex, acquire_stock_advisory_lock, acquire_stock_mutation_lock

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
                    detail={
                        "error": "INSUFFICIENT_STOCK",
                        "sku": product.code,
                        "size": product.size or "",
                        "available": avail_str,
                        "requested": req_str,
                        "message": f"Insufficient physical stock for this size variant (Available: {avail_str}, Requested: {req_str})",
                        "Insufficient physical stock": True
                    }
                )

            # 4. Append the -1 movement and commit the transaction, releasing the lock.
            movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
            movement = movement_repo.create(
                product_id=payload.product_id,
                warehouse_id=1,
                size=product.size,
                direction=payload.direction,
                quantity=payload.quantity,
                ref_type=payload.reference_type or "manual",
                ref_id=payload.reference_id,
                movement_type="SALES_OUT" if payload.reference_type == "sale" else "ADJUSTMENT_OUT",
                actor_id=current_user.id,
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
        warehouse_id=1,
        size=product.size,
        direction=payload.direction,
        quantity=payload.quantity,
        ref_type=payload.reference_type or "manual",
        ref_id=payload.reference_id,
        movement_type="PRODUCTION_IN" if payload.reference_type == "production" else "ADJUSTMENT_IN",
        actor_id=current_user.id,
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


def get_available_stock_variant(
    db: Session,
    company_id: int,
    product_id: int,
    warehouse_id: Optional[int] = None,
    size: Optional[str] = None
) -> float:
    """
    Computes exact on-hand stock for a product variant (product_id, size, warehouse_id).
    Strict append-only summation: SUM(direction * quantity).
    """
    query = db.query(
        func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
    ).filter(
        StockMovement.company_id == company_id,
        StockMovement.product_id == product_id
    )
    if warehouse_id is not None:
        query = query.filter(StockMovement.warehouse_id == warehouse_id)
    if size is not None:
        query = query.filter(StockMovement.size == size)
    return float(query.scalar() or 0.0)


@router.get("/warehouses")
def list_warehouses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns active warehouses for current tenant."""
    warehouses = db.query(Warehouse).filter(
        Warehouse.company_id == current_user.company_id,
        Warehouse.is_active == True
    ).all()
    if not warehouses:
        wh = Warehouse(
            company_id=current_user.company_id,
            name="Main Finished Warehouse",
            code="WH-MAIN",
            location="Factory Premises, Birgunj",
            is_active=True
        )
        db.add(wh)
        db.commit()
        db.refresh(wh)
        warehouses = [wh]
    return [
        {
            "id": w.id,
            "name": w.name,
            "code": w.code,
            "location": w.location
        }
        for w in warehouses
    ]


@router.get("/ledger")
def get_stock_ledger(
    product_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    size: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns audit-compliant immutable stock movement ledger records.
    Running balances are computed across movements partitioned by product variant & warehouse.
    """
    subq = db.query(
        StockMovement.id.label("m_id"),
        StockMovement.company_id,
        StockMovement.product_id,
        StockMovement.warehouse_id,
        StockMovement.size,
        StockMovement.quantity,
        StockMovement.direction,
        StockMovement.ref_type,
        StockMovement.ref_id,
        StockMovement.movement_type,
        StockMovement.source_doc_ref,
        StockMovement.reversal_of_id,
        StockMovement.reason_code,
        StockMovement.reason_text,
        StockMovement.actor_id,
        StockMovement.approved_by_id,
        StockMovement.date_ad,
        StockMovement.date_bs,
        StockMovement.notes,
        StockMovement.created_at,
        func.sum(StockMovement.direction * StockMovement.quantity).over(
            partition_by=[StockMovement.product_id, StockMovement.warehouse_id, StockMovement.size],
            order_by=[StockMovement.created_at.asc(), StockMovement.id.asc()]
        ).label("running_balance")
    ).filter(
        StockMovement.company_id == current_user.company_id
    )

    if product_id:
        subq = subq.filter(StockMovement.product_id == product_id)
    if warehouse_id:
        subq = subq.filter(StockMovement.warehouse_id == warehouse_id)
    if size:
        subq = subq.filter(StockMovement.size == size)

    subquery = subq.subquery()
    query = db.query(subquery)

    if movement_type:
        query = query.filter(subquery.c.movement_type == movement_type)
    if date_from:
        query = query.filter(subquery.c.date_ad >= date_from)
    if date_to:
        query = query.filter(subquery.c.date_ad <= date_to)

    total_count = query.count()
    rows = query.order_by(subquery.c.created_at.desc(), subquery.c.m_id.desc()).offset(offset).limit(limit).all()

    # Preload product, warehouse, and user details in batch
    p_ids = list({r.product_id for r in rows})
    w_ids = list({r.warehouse_id for r in rows if r.warehouse_id})
    u_ids = list({r.actor_id for r in rows if r.actor_id} | {r.approved_by_id for r in rows if r.approved_by_id})

    prods = {p.id: p for p in db.query(Product).filter(Product.id.in_(p_ids)).all()} if p_ids else {}
    warehouses = {w.id: w for w in db.query(Warehouse).filter(Warehouse.id.in_(w_ids)).all()} if w_ids else {}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(u_ids)).all()} if u_ids else {}

    items = []
    for r in rows:
        prod = prods.get(r.product_id)
        wh = warehouses.get(r.warehouse_id)
        actor = users.get(r.actor_id)
        approver = users.get(r.approved_by_id)

        items.append({
            "id": r.m_id,
            "product_id": r.product_id,
            "product_code": prod.code if prod else "",
            "product_name": prod.name if prod else "",
            "category": prod.category if prod else "",
            "warehouse_id": r.warehouse_id,
            "warehouse_name": wh.name if wh else "Main Finished Warehouse",
            "size": r.size or (prod.size if prod else ""),
            "quantity": float(r.quantity),
            "direction": r.direction,
            "qty_in": float(r.quantity) if r.direction == 1 else 0.0,
            "qty_out": float(r.quantity) if r.direction == -1 else 0.0,
            "running_balance": float(r.running_balance or 0.0),
            "movement_type": r.movement_type,
            "source_doc_ref": r.source_doc_ref or "",
            "ref_type": r.ref_type,
            "ref_id": r.ref_id,
            "reversal_of_id": r.reversal_of_id,
            "reason_code": r.reason_code or "",
            "reason_text": r.reason_text or "",
            "actor_id": r.actor_id,
            "actor_name": actor.name if actor else (actor.username if actor else "System"),
            "approved_by_id": r.approved_by_id,
            "approved_by_name": approver.name if approver else None,
            "date_ad": r.date_ad,
            "date_bs": r.date_bs,
            "notes": r.notes or "",
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "total": total_count,
        "items": items,
        "limit": limit,
        "offset": offset
    }


@router.post("/adjustments")
def create_stock_adjustment(
    payload: StockAdjustmentCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Atomic Stock Adjustment service enforcing:
    1. Zero-floor invariant (Current Balance + delta >= 0).
    2. RBAC: Negative adjustments require admin role or valid supervisor token, unless reason is RECOUNT/RECOUNT_CORRECTION.
    3. Append-only ledger movement record.
    """
    if payload.quantity_delta == 0:
        raise HTTPException(status_code=400, detail="Adjustment quantity delta cannot be zero")

    product = db.query(Product).filter(
        Product.id == payload.product_id,
        Product.company_id == current_user.company_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in current company")

    target_size = payload.size or product.size
    target_warehouse_id = payload.warehouse_id or 1

    # Check RBAC for downward adjustment
    if payload.quantity_delta < 0:
        is_recount = (payload.reason_code or "").upper() in ("RECOUNT", "RECOUNT_CORRECTION")
        if not is_recount and current_user.role != "admin":
            supervisor_valid = False
            if payload.supervisor_token:
                import secrets
                configured_token = getattr(settings, "SUPERVISOR_AUTH_TOKEN", "SUPERVISOR_AUTH_2026")
                if secrets.compare_digest(payload.supervisor_token, configured_token):
                    supervisor_valid = True
                else:
                    from app.core.security import verify_password
                    admin_users = db.query(User).filter(User.company_id == current_user.company_id, User.role == "admin").all()
                    for au in admin_users:
                        if verify_password(payload.supervisor_token, au.password_hash):
                            supervisor_valid = True
                            break
            if not supervisor_valid:
                raise HTTPException(
                    status_code=403,
                    detail="Downward stock adjustments for loss/damage require an administrator or valid supervisor authorization token."
                )

    acquire_stock_advisory_lock(db, current_user.company_id, payload.product_id)
    mutex = get_stock_mutex(current_user.company_id, payload.product_id)
    with mutex:
        current_balance = get_available_stock_variant(
            db, current_user.company_id, payload.product_id, target_warehouse_id, target_size
        )

        projected_balance = current_balance + payload.quantity_delta
        if projected_balance < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Adjustment rejected: would cause negative stock balance. Current: {current_balance}, Requested delta: {payload.quantity_delta}, Projected: {projected_balance}"
            )

        direction = 1 if payload.quantity_delta > 0 else -1
        qty = abs(payload.quantity_delta)
        m_type = "ADJUSTMENT_IN" if direction == 1 else "ADJUSTMENT_OUT"
        doc_ref = f"ADJ-{datetime.now().strftime('%y%m%d%H%M%S')}"

        movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
        movement = movement_repo.create(
            product_id=payload.product_id,
            warehouse_id=target_warehouse_id,
            size=target_size,
            quantity=qty,
            direction=direction,
            ref_type="adjustment",
            ref_id=None,
            movement_type=m_type,
            source_doc_ref=doc_ref,
            reason_code=payload.reason_code,
            reason_text=payload.reason_text,
            actor_id=current_user.id,
            approved_by_id=current_user.id if current_user.role == "admin" else None,
            date_ad=datetime.now().strftime("%Y-%m-%d"),
            date_bs="",
            notes=payload.reason_text or f"Stock adjustment: {payload.reason_code or 'MANUAL'}"
        )
        db.commit()
        db.refresh(movement)
        return movement


@router.post("/reversals/{movement_id}")
def reverse_stock_movement(
    movement_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Atomic Reversal of a prior stock movement.
    Creates an inverse VOID_REVERSAL movement with reversal_of_id linked to the original movement.
    Enforces that:
    1. Movement exists and belongs to caller's company.
    2. Movement has not already been reversed.
    3. Movement is not itself a VOID_REVERSAL.
    4. If reversing an inward movement (which removes stock), does not violate the zero floor.
    """
    target = db.query(StockMovement).filter(
        StockMovement.id == movement_id,
        StockMovement.company_id == current_user.company_id
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Stock movement not found in current company")

    if target.movement_type == "VOID_REVERSAL":
        raise HTTPException(status_code=400, detail="Cannot reverse a void reversal movement")

    already_reversed = db.query(StockMovement).filter(
        StockMovement.reversal_of_id == target.id,
        StockMovement.company_id == current_user.company_id
    ).first()
    if already_reversed:
        raise HTTPException(status_code=400, detail=f"Movement #{movement_id} has already been reversed by #{already_reversed.id}")

    acquire_stock_advisory_lock(db, current_user.company_id, target.product_id)
    mutex = get_stock_mutex(current_user.company_id, target.product_id)
    with mutex:
        inv_direction = -target.direction
        if inv_direction == -1:
            current_balance = get_available_stock_variant(
                db, current_user.company_id, target.product_id, target.warehouse_id, target.size
            )
            if current_balance - target.quantity < 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Reversal rejected: would result in negative stock balance. Current: {current_balance}, Reversal deduction: {target.quantity}"
                )

        movement_repo = TenantRepository(StockMovement, db, current_user.company_id)
        reversal = movement_repo.create(
            product_id=target.product_id,
            warehouse_id=target.warehouse_id,
            size=target.size,
            quantity=target.quantity,
            direction=inv_direction,
            ref_type="void_reversal",
            ref_id=target.ref_id,
            movement_type="VOID_REVERSAL",
            source_doc_ref=f"REV-{target.id}",
            reversal_of_id=target.id,
            reason_code="VOID_REVERSAL",
            reason_text=f"Void Reversal of movement #{target.id} ({target.source_doc_ref or target.movement_type})",
            actor_id=current_user.id,
            approved_by_id=current_user.id if current_user.role == "admin" else None,
            date_ad=datetime.now().strftime("%Y-%m-%d"),
            date_bs=target.date_bs,
            notes=f"Reversal of movement #{target.id}"
        )
        db.commit()
        db.refresh(reversal)
        return reversal


@router.get("/curve/{product_id}")
def get_product_stock_curve(
    product_id: int,
    warehouse_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns Paris Points (32-43) live stock curve for the given product's model family.
    """
    base_prod = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == current_user.company_id
    ).first()
    if not base_prod:
        raise HTTPException(status_code=404, detail="Product not found")

    sibling_products = db.query(Product).filter(
        Product.company_id == current_user.company_id,
        Product.name == base_prod.name
    ).all()

    curve = {sz: 0.0 for sz in range(32, 44)}
    for sp in sibling_products:
        sz_int = None
        try:
            sz_int = int(sp.size)
        except (ValueError, TypeError):
            pass
        if sz_int and 32 <= sz_int <= 43:
            bal = get_available_stock_variant(db, current_user.company_id, sp.id, warehouse_id, sp.size)
            curve[sz_int] = max(0.0, bal)

    return {
        "product_id": base_prod.id,
        "product_name": base_prod.name,
        "product_code": base_prod.code,
        "category": base_prod.category,
        "curve": curve
    }

