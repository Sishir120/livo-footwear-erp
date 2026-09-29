"""
Operations Telemetry & Observability API
Provides real-time system metrics, database health, migration state,
and supervisor exception tracking for factory leadership.
"""
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from app.api.deps import get_db, require_admin
from app.models.user import User
from app.models.stock import Product, StockMovement
from app.models.sync import ProductionSyncLog
from app.models.audit import AuditLog

router = APIRouter(prefix="/ops", tags=["Operations Telemetry"])

@router.get("/telemetry")
def get_operations_telemetry(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns live operational telemetry and supervisor cockpit metrics:
    - db_status: database health & query latency in ms.
    - migration_revision: current active Alembic database revision.
    - unsynced_draft_age_seconds: age in seconds of oldest pending offline draft.
    - recent_422_blocks: count of stockout and credit-hold rejections in last 24h.
    - broken_core_runs_count: active footwear models with zero stock in core sizes 39–41.
    - sync_error_rate_24h: ratio of rejected/conflict sync attempts to total syncs in last 24h.
    """
    company_id = current_user.company_id
    now_utc = datetime.now(timezone.utc)
    twenty_four_hours_ago = now_utc - timedelta(hours=24)

    # 1. DB Status & Latency
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar()
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = {"status": "healthy", "latency_ms": db_latency_ms}
    except Exception as e:
        db_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        db_status = {"status": "degraded", "latency_ms": db_latency_ms, "error": str(e)}

    # 2. Active Migration Revision
    migration_revision = "007_production_sync_engine"
    try:
        rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if rev:
            migration_revision = rev
    except Exception:
        pass

    # 3. Unsynced Draft Age
    oldest_pending = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == company_id,
        ProductionSyncLog.status == "PENDING"
    ).order_by(ProductionSyncLog.created_at.asc()).first()

    if oldest_pending and oldest_pending.created_at:
        created = oldest_pending.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        unsynced_draft_age_seconds = max(0, int((now_utc - created).total_seconds()))
    else:
        unsynced_draft_age_seconds = 0

    # 4. Recent 422 Blocks in Last 24 Hours
    stockout_audit_blocks = db.query(AuditLog).filter(
        AuditLog.company_id == company_id,
        AuditLog.timestamp >= twenty_four_hours_ago,
        or_(
            AuditLog.details.like("%INSUFFICIENT_STOCK%"),
            AuditLog.details.like("%Insufficient physical stock%"),
        )
    ).count()

    credit_audit_blocks = db.query(AuditLog).filter(
        AuditLog.company_id == company_id,
        AuditLog.timestamp >= twenty_four_hours_ago,
        or_(
            AuditLog.details.like("%CREDIT_LIMIT%"),
            AuditLog.details.like("%Credit limit exceeded%"),
        )
    ).count()

    sync_blocks = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == company_id,
        ProductionSyncLog.created_at >= twenty_four_hours_ago,
        ProductionSyncLog.status.in_(["REJECTED", "CONFLICT"])
    ).count()

    stockout_blocks_24h = stockout_audit_blocks + sync_blocks
    credit_hold_blocks_24h = credit_audit_blocks
    recent_422_blocks = stockout_blocks_24h + credit_hold_blocks_24h

    # 5. Broken Core Runs (Sizes 39–41)
    active_products = db.query(Product).filter(
        Product.company_id == company_id
    ).all()

    movement_balances = dict(
        db.query(
            StockMovement.product_id,
            func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0.0)
        ).filter(
            StockMovement.company_id == company_id
        ).group_by(StockMovement.product_id).all()
    )

    models_core_stock = defaultdict(lambda: {"39": 0.0, "40": 0.0, "41": 0.0, "has_core_skus": False})
    for p in active_products:
        sz = str(p.size or "").strip()
        base_name = p.name.split("-")[0].strip() if "-" in p.name else p.name
        if sz in ("39", "40", "41"):
            models_core_stock[base_name]["has_core_skus"] = True
            models_core_stock[base_name][sz] += float(movement_balances.get(p.id, 0.0))

    broken_core_runs_count = sum(
        1 for m, data in models_core_stock.items()
        if data["has_core_skus"] and (data["39"] <= 0 or data["40"] <= 0 or data["41"] <= 0)
    )

    # 6. Sync Error Rate in Last 24 Hours
    total_syncs_24h = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == company_id,
        ProductionSyncLog.created_at >= twenty_four_hours_ago
    ).count()

    failed_syncs_24h = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == company_id,
        ProductionSyncLog.created_at >= twenty_four_hours_ago,
        ProductionSyncLog.status.in_(["REJECTED", "CONFLICT"])
    ).count()

    sync_error_rate_24h = round(failed_syncs_24h / total_syncs_24h, 4) if total_syncs_24h > 0 else 0.0

    return {
        "db_status": db_status,
        "migration_revision": migration_revision,
        "unsynced_draft_age_seconds": unsynced_draft_age_seconds,
        "recent_422_blocks": recent_422_blocks,
        "stockout_blocks_24h": stockout_blocks_24h,
        "credit_hold_blocks_24h": credit_hold_blocks_24h,
        "broken_core_runs_count": broken_core_runs_count,
        "sync_error_rate_24h": sync_error_rate_24h,
        "timestamp": now_utc.isoformat()
    }
