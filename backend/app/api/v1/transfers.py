from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.sequence import allocate_next_sequence
from app.core.locks import acquire_stock_mutation_lock, acquire_stock_transfer_lock, reset_service_read_snapshot_under_lock
from app.core.nepali_date import today_bs, parse_ad_date

router = APIRouter(prefix="/transfers", tags=["Stock Transfers"])


# --- Schemas ---

class StockTransferItemCreate(BaseModel):
    product_id: int = Field(..., gt=0)
    size: Optional[str] = Field(None, max_length=20)
    quantity: Decimal = Field(..., gt=0)


class StockTransferCreate(BaseModel):
    source_warehouse_id: int = Field(..., gt=0)
    destination_warehouse_id: int = Field(..., gt=0)
    transfer_date_ad: str = Field(..., max_length=20)
    transfer_date_bs: str = Field(..., max_length=20)
    carrier_name: Optional[str] = Field(None, max_length=128)
    vehicle_number: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=500)
    items: List[StockTransferItemCreate] = Field(..., min_length=1)


class StockTransferDispatch(BaseModel):
    dispatch_date_ad: Optional[str] = Field(None, max_length=20)
    dispatch_date_bs: Optional[str] = Field(None, max_length=20)
    carrier_name: Optional[str] = Field(None, max_length=128)
    vehicle_number: Optional[str] = Field(None, max_length=64)
    notes: Optional[str] = Field(None, max_length=500)


class ReceiveItemPayload(BaseModel):
    item_id: int = Field(..., gt=0)
    received_quantity: Decimal = Field(..., ge=0)
    discrepancy_reason: Optional[str] = Field(None, max_length=255)


class StockTransferReceive(BaseModel):
    receipt_date_ad: Optional[str] = Field(None, max_length=20)
    receipt_date_bs: Optional[str] = Field(None, max_length=20)
    items: List[ReceiveItemPayload] = Field(..., min_length=1)
    is_final: bool = Field(True, description="Whether this receipt finalizes the shipment and closes any remaining unreceived quantity as discrepancy.")
    notes: Optional[str] = Field(None, max_length=500)


# --- Helpers ---

def get_warehouse_stock(db: Session, company_id: int, warehouse_id: int, product_id: int, size: Optional[str]) -> Decimal:
    """Computes exact on-hand stock for a specific warehouse and product variant."""
    query = db.query(func.coalesce(func.sum(StockMovement.quantity * StockMovement.direction), 0)).filter(
        StockMovement.company_id == company_id,
        StockMovement.warehouse_id == warehouse_id,
        StockMovement.product_id == product_id
    )
    if size:
        query = query.filter(StockMovement.size == size)
    val = query.scalar() or 0
    return Decimal(str(val))


# --- Endpoints ---

@router.get("")
def list_transfers(
    status_filter: Optional[str] = Query(None, alias="status"),
    source_warehouse_id: Optional[int] = Query(None),
    destination_warehouse_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists stock transfers strictly scoped to current tenant company."""
    query = db.query(StockTransfer).filter(StockTransfer.company_id == current_user.company_id)
    if status_filter:
        query = query.filter(StockTransfer.status == status_filter.upper())
    if source_warehouse_id:
        query = query.filter(StockTransfer.source_warehouse_id == source_warehouse_id)
    if destination_warehouse_id:
        query = query.filter(StockTransfer.destination_warehouse_id == destination_warehouse_id)

    total_count = query.count()
    items = query.order_by(StockTransfer.id.desc()).offset(offset).limit(limit).all()

    results = []
    for t in items:
        results.append({
            "id": t.id,
            "transfer_number": t.transfer_number,
            "source_warehouse_id": t.source_warehouse_id,
            "source_warehouse_name": t.source_warehouse.name if t.source_warehouse else None,
            "source_branch_name": t.source_warehouse.branch.name if (t.source_warehouse and t.source_warehouse.branch) else None,
            "destination_warehouse_id": t.destination_warehouse_id,
            "destination_warehouse_name": t.destination_warehouse.name if t.destination_warehouse else None,
            "destination_branch_name": t.destination_warehouse.branch.name if (t.destination_warehouse and t.destination_warehouse.branch) else None,
            "is_inter_branch": (
                t.source_warehouse.branch_id != t.destination_warehouse.branch_id
                if (t.source_warehouse and t.destination_warehouse and t.source_warehouse.branch_id and t.destination_warehouse.branch_id)
                else False
            ),
            "status": t.status,
            "transfer_date_ad": t.transfer_date_ad,
            "transfer_date_bs": t.transfer_date_bs,
            "dispatch_date_ad": t.dispatch_date_ad,
            "receipt_date_ad": t.receipt_date_ad,
            "carrier_name": t.carrier_name,
            "vehicle_number": t.vehicle_number,
            "items_count": len(t.items),
            "created_at": t.created_at.isoformat() if t.created_at else None
        })

    return {
        "items": results,
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_transfer(
    data: StockTransferCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Creates a new stock transfer in DRAFT state."""
    if data.source_warehouse_id == data.destination_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination warehouses must be distinct."
        )

    # Validate warehouses belong to company
    wh_source = db.query(Warehouse).filter(
        Warehouse.id == data.source_warehouse_id,
        Warehouse.company_id == current_user.company_id,
        Warehouse.is_active == True
    ).first()
    if not wh_source:
        raise HTTPException(status_code=404, detail="Source warehouse not found or inactive.")

    wh_dest = db.query(Warehouse).filter(
        Warehouse.id == data.destination_warehouse_id,
        Warehouse.company_id == current_user.company_id,
        Warehouse.is_active == True
    ).first()
    if not wh_dest:
        raise HTTPException(status_code=404, detail="Destination warehouse not found or inactive.")

    # Validate products and ensure no duplicate variants in request
    seen_variants = set()
    for itm in data.items:
        key = (itm.product_id, str(itm.size or "").strip())
        if key in seen_variants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate product variant in transfer items: Product #{itm.product_id}, Size: {itm.size or 'N/A'}"
            )
        seen_variants.add(key)

        prod = db.query(Product).filter(
            Product.id == itm.product_id,
            Product.company_id == current_user.company_id
        ).first()
        if not prod:
            raise HTTPException(status_code=404, detail=f"Product #{itm.product_id} not found.")

    seq = allocate_next_sequence(db, current_user.company_id, "TRF")
    transfer_num = f"TRF-{current_user.company_id:02d}-{seq:05d}"

    transfer = StockTransfer(
        company_id=current_user.company_id,
        transfer_number=transfer_num,
        source_warehouse_id=data.source_warehouse_id,
        destination_warehouse_id=data.destination_warehouse_id,
        status="DRAFT",
        transfer_date_ad=data.transfer_date_ad,
        transfer_date_bs=data.transfer_date_bs,
        created_by_id=current_user.id,
        carrier_name=data.carrier_name,
        vehicle_number=data.vehicle_number,
        notes=data.notes
    )
    db.add(transfer)
    db.flush()

    for itm in data.items:
        t_item = StockTransferItem(
            company_id=current_user.company_id,
            transfer_id=transfer.id,
            product_id=itm.product_id,
            size=itm.size,
            requested_quantity=itm.quantity,
            dispatched_quantity=0.0,
            received_quantity=0.0,
            discrepancy_quantity=0.0
        )
        db.add(t_item)

    db.commit()
    db.refresh(transfer)
    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "source_warehouse_id": transfer.source_warehouse_id,
        "destination_warehouse_id": transfer.destination_warehouse_id,
        "message": f"Transfer {transfer.transfer_number} created in DRAFT state"
    }


@router.get("/{transfer_id}")
def get_transfer_detail(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches full details of a stock transfer including items and ledger status."""
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id,
        StockTransfer.company_id == current_user.company_id
    ).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Stock transfer not found")

    items_detail = []
    for itm in transfer.items:
        items_detail.append({
            "id": itm.id,
            "product_id": itm.product_id,
            "product_code": itm.product.code if itm.product else None,
            "product_name": itm.product.name if itm.product else None,
            "size": itm.size,
            "requested_quantity": float(itm.requested_quantity),
            "dispatched_quantity": float(itm.dispatched_quantity),
            "received_quantity": float(itm.received_quantity),
            "discrepancy_quantity": float(itm.discrepancy_quantity),
            "discrepancy_reason": itm.discrepancy_reason
        })

    return {
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "source_warehouse_id": transfer.source_warehouse_id,
        "source_warehouse_name": transfer.source_warehouse.name if transfer.source_warehouse else None,
        "source_branch_id": transfer.source_warehouse.branch_id if transfer.source_warehouse else None,
        "source_branch_name": transfer.source_warehouse.branch.name if (transfer.source_warehouse and transfer.source_warehouse.branch) else None,
        "destination_warehouse_id": transfer.destination_warehouse_id,
        "destination_warehouse_name": transfer.destination_warehouse.name if transfer.destination_warehouse else None,
        "destination_branch_id": transfer.destination_warehouse.branch_id if transfer.destination_warehouse else None,
        "destination_branch_name": transfer.destination_warehouse.branch.name if (transfer.destination_warehouse and transfer.destination_warehouse.branch) else None,
        "is_inter_branch": (
            transfer.source_warehouse.branch_id != transfer.destination_warehouse.branch_id
            if (transfer.source_warehouse and transfer.destination_warehouse and transfer.source_warehouse.branch_id and transfer.destination_warehouse.branch_id)
            else False
        ),
        "status": transfer.status,
        "transfer_date_ad": transfer.transfer_date_ad,
        "transfer_date_bs": transfer.transfer_date_bs,
        "dispatch_date_ad": transfer.dispatch_date_ad,
        "dispatch_date_bs": transfer.dispatch_date_bs,
        "receipt_date_ad": transfer.receipt_date_ad,
        "receipt_date_bs": transfer.receipt_date_bs,
        "carrier_name": transfer.carrier_name,
        "vehicle_number": transfer.vehicle_number,
        "notes": transfer.notes,
        "created_by": transfer.created_by.name if transfer.created_by else None,
        "dispatched_by": transfer.dispatched_by.name if transfer.dispatched_by else None,
        "received_by": transfer.received_by.name if transfer.received_by else None,
        "items": items_detail,
        "created_at": transfer.created_at.isoformat() if transfer.created_at else None
    }


@router.post("/{transfer_id}/dispatch")
def dispatch_transfer(
    transfer_id: int,
    payload: Optional[StockTransferDispatch] = None,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Confirms dispatch of items from source warehouse.
    Takes stock mutation lock and transfer row lock, validates available source stock,
    deducts source inventory via TRANSFER_OUT, and transitions transfer into IN_TRANSIT status.
    """
    acquire_stock_transfer_lock(db, current_user.company_id, transfer_id)
    reset_service_read_snapshot_under_lock(db)
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id,
        StockTransfer.company_id == current_user.company_id
    ).with_for_update().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Stock transfer not found")

    if transfer.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot dispatch transfer in '{transfer.status}' status. Only DRAFT transfers can be dispatched."
        )

    # Acquire lock for source warehouse stock mutation for each item
    for itm in transfer.items:
        acquire_stock_mutation_lock(db, current_user.company_id, transfer.source_warehouse_id, itm.product_id, str(itm.size or ""))

    # Check on-hand stock for all items
    for itm in transfer.items:
        current_stock = get_warehouse_stock(
            db,
            current_user.company_id,
            transfer.source_warehouse_id,
            itm.product_id,
            itm.size
        )
        if current_stock < itm.requested_quantity:
            prod_name = itm.product.name if itm.product else f"#{itm.product_id}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient stock in source warehouse for '{prod_name}' (Size: {itm.size or 'N/A'}). "
                    f"Requested: {itm.requested_quantity}, Available: {current_stock}"
                )
            )

    d_date_ad = payload.dispatch_date_ad if payload and payload.dispatch_date_ad else transfer.transfer_date_ad
    d_date_bs = payload.dispatch_date_bs if payload and payload.dispatch_date_bs else transfer.transfer_date_bs

    if payload:
        if payload.carrier_name:
            transfer.carrier_name = payload.carrier_name
        if payload.vehicle_number:
            transfer.vehicle_number = payload.vehicle_number
        if payload.notes:
            transfer.notes = f"{transfer.notes or ''} | {payload.notes}".strip(" |")

    # Deduct stock from source warehouse
    for itm in transfer.items:
        movement = StockMovement(
            company_id=current_user.company_id,
            product_id=itm.product_id,
            warehouse_id=transfer.source_warehouse_id,
            size=itm.size,
            quantity=itm.requested_quantity,
            direction=-1,
            movement_type="TRANSFER_OUT",
            ref_type="transfer",
            ref_id=transfer.id,
            source_doc_ref=transfer.transfer_number,
            actor_id=current_user.id,
            date_ad=d_date_ad,
            date_bs=d_date_bs,
            notes=f"Dispatched via Transfer {transfer.transfer_number} to Warehouse #{transfer.destination_warehouse_id}"
        )
        db.add(movement)
        itm.dispatched_quantity = itm.requested_quantity

    transfer.status = "IN_TRANSIT"
    transfer.dispatch_date_ad = d_date_ad
    transfer.dispatch_date_bs = d_date_bs
    transfer.dispatched_by_id = current_user.id

    db.commit()
    db.refresh(transfer)
    return {
        "message": f"Transfer {transfer.transfer_number} successfully dispatched and is now IN_TRANSIT",
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "dispatched_by_id": transfer.dispatched_by_id
    }


@router.post("/{transfer_id}/receive")
def receive_transfer(
    transfer_id: int,
    payload: StockTransferReceive,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Independent destination receipt verification:
    - Enforces strict over-receipt prevention (rec_qty <= remaining_in_transit).
    - Supports multi-stage receipts (status -> PARTIALLY_RECEIVED) or final receipts (status -> RECEIVED).
    - Logs discrepancies with reasons and creates audit movements for transit losses.
    - Preserves exact stock conservation: Source Reduction = Received + In-Transit + Discrepancy.
    """
    acquire_stock_transfer_lock(db, current_user.company_id, transfer_id)
    reset_service_read_snapshot_under_lock(db)
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id,
        StockTransfer.company_id == current_user.company_id
    ).with_for_update().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Stock transfer not found")

    if transfer.status not in ("IN_TRANSIT", "PARTIALLY_RECEIVED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot receive transfer in '{transfer.status}' status. Only IN_TRANSIT or PARTIALLY_RECEIVED transfers can be received."
        )

    # Query transfer items directly to ensure fresh state under row lock
    items = db.query(StockTransferItem).filter(
        StockTransferItem.transfer_id == transfer.id,
        StockTransferItem.company_id == current_user.company_id
    ).with_for_update().all()

    # Acquire lock for destination warehouse stock mutation for each item
    for itm in items:
        acquire_stock_mutation_lock(db, current_user.company_id, transfer.destination_warehouse_id, itm.product_id, str(itm.size or ""))

    payload_map = {item.item_id: item for item in payload.items}
    r_date_ad = payload.receipt_date_ad or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    r_date_bs = payload.receipt_date_bs or "2083-01-01"

    for itm in items:
        if itm.id not in payload_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing receipt confirmation for transfer item #{itm.id}"
            )
        rec_data = payload_map[itm.id]
        rec_qty = Decimal(str(rec_data.received_quantity))

        remaining_in_transit = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
        if rec_qty > remaining_in_transit:
            prod_name = itm.product.name if itm.product else f"#{itm.product_id}"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Over-receipt forbidden for '{prod_name}' (Size: {itm.size or 'N/A'}). "
                    f"Attempted to receive {rec_qty}, but only {remaining_in_transit} remains in transit."
                )
            )

        if rec_qty > 0:
            movement = StockMovement(
                company_id=current_user.company_id,
                product_id=itm.product_id,
                warehouse_id=transfer.destination_warehouse_id,
                size=itm.size,
                quantity=rec_qty,
                direction=1,
                movement_type="TRANSFER_IN",
                ref_type="transfer",
                ref_id=transfer.id,
                source_doc_ref=transfer.transfer_number,
                actor_id=current_user.id,
                date_ad=r_date_ad,
                date_bs=r_date_bs,
                notes=f"Received via Transfer {transfer.transfer_number} from Warehouse #{transfer.source_warehouse_id}"
            )
            db.add(movement)
            itm.received_quantity = Decimal(str(itm.received_quantity)) + rec_qty

        # Discrepancy handling on final receipt
        if payload.is_final:
            shortage = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
            if shortage > 0:
                reason = rec_data.discrepancy_reason or payload.notes
                if not reason or not reason.strip():
                    prod_name = itm.product.name if itm.product else f"#{itm.product_id}"
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Discrepancy reason is strictly required when finalizing a short receipt for '{prod_name}'. "
                            f"Shortage: {shortage} units."
                        )
                    )
                itm.discrepancy_quantity = shortage
                itm.discrepancy_reason = reason.strip()
                db.add(StockMovement(
                    company_id=current_user.company_id,
                    product_id=itm.product_id,
                    warehouse_id=transfer.source_warehouse_id,
                    size=itm.size,
                    quantity=shortage,
                    direction=0,
                    movement_type="TRANSIT_DISCREPANCY",
                    ref_type="transfer",
                    ref_id=transfer.id,
                    source_doc_ref=f"DISC-{transfer.transfer_number}",
                    actor_id=current_user.id,
                    date_ad=r_date_ad,
                    date_bs=r_date_bs,
                    notes=f"Transit shortage on {transfer.transfer_number}: {itm.discrepancy_reason}"
                ))
            else:
                itm.discrepancy_quantity = Decimal("0.0")

    all_fully_received = all(Decimal(str(itm.received_quantity)) >= Decimal(str(itm.dispatched_quantity)) for itm in items)
    if payload.is_final or all_fully_received:
        transfer.status = "RECEIVED"
    else:
        transfer.status = "PARTIALLY_RECEIVED"

    transfer.receipt_date_ad = r_date_ad
    transfer.receipt_date_bs = r_date_bs
    transfer.received_by_id = current_user.id
    if payload.notes:
        transfer.notes = f"{transfer.notes or ''} | Receipt notes: {payload.notes}".strip(" |")

    db.commit()
    db.refresh(transfer)
    return {
        "message": f"Transfer {transfer.transfer_number} processed (Status: {transfer.status})",
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "received_by_id": transfer.received_by_id
    }


@router.post("/{transfer_id}/cancel")
def cancel_transfer(
    transfer_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Cancels a transfer:
    - If DRAFT: directly marks CANCELLED (no stock was touched).
    - If IN_TRANSIT or PARTIALLY_RECEIVED: reverses only the unreceived in-transit quantity
      back to the source warehouse via VOID_REVERSAL (+1). Already received stock remains at destination!
    - If RECEIVED: rejected (received goods cannot be cancelled; must initiate a return transfer).
    """
    acquire_stock_transfer_lock(db, current_user.company_id, transfer_id)
    reset_service_read_snapshot_under_lock(db)
    transfer = db.query(StockTransfer).filter(
        StockTransfer.id == transfer_id,
        StockTransfer.company_id == current_user.company_id
    ).with_for_update().first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Stock transfer not found")

    if transfer.status == "RECEIVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a received transfer. Initiate a reverse transfer instead."
        )

    if transfer.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer is already cancelled."
        )

    if transfer.status in ("IN_TRANSIT", "PARTIALLY_RECEIVED"):
        for itm in transfer.items:
            acquire_stock_mutation_lock(db, current_user.company_id, transfer.source_warehouse_id, itm.product_id, str(itm.size or ""))

        # Reverse only unreceived in-transit quantity
        for itm in transfer.items:
            remaining_in_transit = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
            if remaining_in_transit > 0:
                movement = StockMovement(
                    company_id=current_user.company_id,
                    product_id=itm.product_id,
                    warehouse_id=transfer.source_warehouse_id,
                    size=itm.size,
                    quantity=remaining_in_transit,
                    direction=1,
                    movement_type="VOID_REVERSAL",
                    ref_type="transfer",
                    ref_id=transfer.id,
                    source_doc_ref=f"VOID-{transfer.transfer_number}",
                    actor_id=current_user.id,
                    date_ad=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    date_bs="2083-01-01",
                    notes=f"Reversal for cancelled transfer {transfer.transfer_number} ({remaining_in_transit} unreceived pairs returned to source)"
                )
                db.add(movement)

    transfer.status = "CANCELLED"
    db.commit()
    db.refresh(transfer)
    return {
        "message": f"Transfer {transfer.transfer_number} marked as CANCELLED",
        "id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status
    }
