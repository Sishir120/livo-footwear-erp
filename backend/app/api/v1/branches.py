from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.branch import Branch
from app.models.stock import Warehouse
from app.models.stock_transfer import StockTransfer
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    WarehouseAssignRequest,
    WarehouseDetailResponse
)

router = APIRouter(prefix="/branches", tags=["Branch Management"])


def _branch_to_response(branch: Branch) -> dict:
    wh_list = [
        WarehouseDetailResponse(
            id=w.id,
            name=w.name,
            code=w.code,
            location=w.location,
            is_active=w.is_active
        )
        for w in (branch.warehouses or [])
    ]
    return {
        "id": branch.id,
        "company_id": branch.company_id,
        "code": branch.code,
        "name": branch.name,
        "type": branch.type,
        "address": branch.address,
        "phone": branch.phone,
        "email": branch.email,
        "is_active": branch.is_active,
        "warehouses_count": len(wh_list),
        "warehouses": wh_list,
        "created_at": branch.created_at.isoformat() if branch.created_at else None
    }


@router.get("", response_model=List[BranchResponse])
def list_branches(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all branches / operating divisions for the authenticated tenant company.
    Strictly isolated by current_user.company_id.
    """
    query = db.query(Branch).filter(Branch.company_id == current_user.company_id)
    if is_active is not None:
        query = query.filter(Branch.is_active == is_active)
    branches = query.order_by(Branch.name.asc()).all()
    return [_branch_to_response(b) for b in branches]


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
def create_branch(
    data: BranchCreate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Creates a new internal branch/operating location for the authenticated company.
    Enforces uniqueness of branch code within current company.
    """
    existing = db.query(Branch).filter(
        Branch.company_id == current_user.company_id,
        func.upper(Branch.code) == data.code.strip().upper()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch code '{data.code}' already exists for this company."
        )

    branch = Branch(
        company_id=current_user.company_id,
        code=data.code.strip().upper(),
        name=data.name.strip(),
        type=data.type.value if hasattr(data.type, "value") else str(data.type),
        address=data.address.strip() if data.address else None,
        phone=data.phone.strip() if data.phone else None,
        email=data.email.strip() if data.email else None,
        is_active=True
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return _branch_to_response(branch)


@router.get("/{branch_id}", response_model=BranchResponse)
def get_branch_detail(
    branch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches details of a specific branch including linked warehouses."""
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return _branch_to_response(branch)


@router.put("/{branch_id}", response_model=BranchResponse)
def update_branch(
    branch_id: int,
    data: BranchUpdate,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Updates branch metadata."""
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if data.name is not None:
        branch.name = data.name.strip()
    if data.type is not None:
        branch.type = data.type.value if hasattr(data.type, "value") else str(data.type)
    if data.address is not None:
        branch.address = data.address.strip() if data.address else None
    if data.phone is not None:
        branch.phone = data.phone.strip() if data.phone else None
    if data.email is not None:
        branch.email = data.email.strip() if data.email else None
    if data.is_active is not None:
        if not data.is_active:
            # Check for in-transit transfers involving attached warehouses
            wh_ids = [w.id for w in branch.warehouses]
            if wh_ids:
                pending_trf = db.query(StockTransfer).filter(
                    StockTransfer.company_id == current_user.company_id,
                    StockTransfer.status == "IN_TRANSIT",
                    (StockTransfer.source_warehouse_id.in_(wh_ids) | StockTransfer.destination_warehouse_id.in_(wh_ids))
                ).first()
                if pending_trf:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Cannot deactivate branch '{branch.name}'. It has active IN_TRANSIT stock transfer "
                            f"{pending_trf.transfer_number} attached to its warehouses."
                        )
                    )
        branch.is_active = data.is_active

    branch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(branch)
    return _branch_to_response(branch)


@router.patch("/{branch_id}/toggle-active", response_model=BranchResponse)
def toggle_branch_active(
    branch_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """Toggles active/inactive status of a branch with integrity checks."""
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    new_status = not branch.is_active
    if not new_status:
        # Check for in-transit stock transfers
        wh_ids = [w.id for w in branch.warehouses]
        if wh_ids:
            pending_trf = db.query(StockTransfer).filter(
                StockTransfer.company_id == current_user.company_id,
                StockTransfer.status == "IN_TRANSIT",
                (StockTransfer.source_warehouse_id.in_(wh_ids) | StockTransfer.destination_warehouse_id.in_(wh_ids))
            ).first()
            if pending_trf:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot deactivate branch '{branch.name}'. It has active IN_TRANSIT stock transfer "
                        f"{pending_trf.transfer_number} attached to its warehouses."
                    )
                )

    branch.is_active = new_status
    branch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(branch)
    return _branch_to_response(branch)


@router.post("/{branch_id}/warehouses", response_model=BranchResponse)
def assign_warehouse_to_branch(
    branch_id: int,
    payload: WarehouseAssignRequest,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Assigns an existing warehouse to a branch.
    Strictly verifies that both branch and warehouse belong to current_user.company_id.
    """
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign warehouse to inactive branch '{branch.name}'."
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == payload.warehouse_id,
        Warehouse.company_id == current_user.company_id
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found in current company")

    warehouse.branch_id = branch.id
    db.commit()
    db.refresh(branch)
    return _branch_to_response(branch)


@router.delete("/{branch_id}/warehouses/{warehouse_id}", response_model=BranchResponse)
def unlink_warehouse_from_branch(
    branch_id: int,
    warehouse_id: int,
    current_user: User = Depends(require_editor),
    db: Session = Depends(get_db)
):
    """
    Unlinks a warehouse from a branch (resets branch_id to NULL).
    Preserves warehouse and its stock movements.
    """
    branch = db.query(Branch).filter(
        Branch.id == branch_id,
        Branch.company_id == current_user.company_id
    ).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.company_id == current_user.company_id,
        Warehouse.branch_id == branch.id
    ).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not linked to this branch")

    warehouse.branch_id = None
    db.commit()
    db.refresh(branch)
    return _branch_to_response(branch)
