from datetime import datetime, timezone, timedelta, date as dt_date
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.stock import Product
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.production import ProductionBatch
from app.models.worker import Worker
from app.models.analytics import DailyFactoryLog
from app.schemas.analytics import (
    TopProductItem,
    TopCustomerItem,
    DailyRecordItem,
    ProductionRatioSummary,
    ProductionRatioResponse,
    DailyLogCreate,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Leaderboards"])


def _approx_ad_to_bs(ad_date_str: str) -> str:
    """
    Fallback converter from AD (YYYY-MM-DD) to approximate BS date.
    Nepali BS year is approximately AD + 56 years, 8 months.
    """
    try:
        parts = ad_date_str.split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        bs_year = y + 56
        bs_month = m + 8
        if bs_month > 12:
            bs_year += 1
            bs_month -= 12
        return f"{bs_year:04d}-{bs_month:02d}-{d:02d}"
    except Exception:
        return "2083-06-15"


@router.get("/top-products", response_model=List[TopProductItem])
def get_top_products(
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Point 7: Top-selling products ranked at the top of the product catalog.
    Computes total volume (pairs sold), exact integer paisa revenue, and order frequency.
    """
    # 1. Query aggregated sales per product
    sales_subquery = db.query(
        SalesItem.product_id,
        func.sum(SalesItem.quantity).label("total_pairs_sold"),
        func.sum(SalesItem.total_price).label("total_revenue"),
        func.count(func.distinct(SalesItem.sales_order_id)).label("order_count")
    ).join(
        SalesOrder, SalesItem.sales_order_id == SalesOrder.id
    ).filter(
        SalesItem.company_id == current_user.company_id,
        SalesOrder.company_id == current_user.company_id,
        SalesOrder.status != "cancelled"
    ).group_by(
        SalesItem.product_id
    ).subquery()

    # 2. Join with Products table
    query = db.query(
        Product.id.label("product_id"),
        Product.code,
        Product.name,
        Product.category,
        func.coalesce(sales_subquery.c.total_pairs_sold, 0.0).label("pairs_sold"),
        func.coalesce(sales_subquery.c.total_revenue, 0.0).label("revenue"),
        func.coalesce(sales_subquery.c.order_count, 0).label("orders")
    ).outerjoin(
        sales_subquery, Product.id == sales_subquery.c.product_id
    ).filter(
        Product.company_id == current_user.company_id
    ).order_by(
        desc("pairs_sold"),
        desc("revenue")
    ).limit(limit)

    results = query.all()

    ranked_items = []
    for rank_idx, row in enumerate(results, start=1):
        revenue_paisa = int(round(float(row.revenue) * 100))
        ranked_items.append(
            TopProductItem(
                rank=rank_idx,
                product_id=row.product_id,
                code=row.code,
                name=row.name,
                category=row.category,
                total_pairs_sold=float(row.pairs_sold),
                total_revenue_paisa=revenue_paisa,
                order_count=int(row.orders)
            )
        )
    return ranked_items


@router.get("/top-customers", response_model=List[TopCustomerItem])
def get_top_customers(
    limit: int = Query(50, ge=1, le=100, description="Max customers to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Point 8: Top customer rankings sorted serially from highest to lowest volume/revenue.
    Computes total orders, pairs bought, invoiced revenue (paisa), and payment reliability.
    """
    # 1. Distinct orders subquery
    orders_sub = db.query(
        SalesOrder.client_id,
        func.count(SalesOrder.id).label("order_count"),
        func.coalesce(func.sum(SalesOrder.total_amount), 0.0).label("total_revenue"),
        func.coalesce(func.sum(SalesOrder.received_amount), 0.0).label("total_received"),
        func.coalesce(func.sum(SalesOrder.receivable_amount), 0.0).label("total_receivable")
    ).filter(
        SalesOrder.company_id == current_user.company_id,
        SalesOrder.status != "cancelled"
    ).group_by(
        SalesOrder.client_id
    ).subquery()

    # 2. Distinct pairs subquery
    pairs_sub = db.query(
        SalesOrder.client_id,
        func.coalesce(func.sum(SalesItem.quantity), 0.0).label("total_pairs")
    ).join(
        SalesOrder, SalesItem.sales_order_id == SalesOrder.id
    ).filter(
        SalesItem.company_id == current_user.company_id,
        SalesOrder.company_id == current_user.company_id,
        SalesOrder.status != "cancelled"
    ).group_by(
        SalesOrder.client_id
    ).subquery()

    query = db.query(
        Client.id.label("client_id"),
        Client.code.label("client_code"),
        Client.name,
        Client.contact_person,
        func.coalesce(orders_sub.c.order_count, 0).label("order_count"),
        func.coalesce(pairs_sub.c.total_pairs, 0.0).label("total_pairs"),
        func.coalesce(orders_sub.c.total_revenue, 0.0).label("total_revenue"),
        func.coalesce(orders_sub.c.total_received, 0.0).label("total_received"),
        func.coalesce(orders_sub.c.total_receivable, 0.0).label("total_receivable")
    ).outerjoin(
        orders_sub, Client.id == orders_sub.c.client_id
    ).outerjoin(
        pairs_sub, Client.id == pairs_sub.c.client_id
    ).filter(
        Client.company_id == current_user.company_id
    ).order_by(
        desc("total_revenue"),
        desc("total_pairs"),
        desc("order_count")
    ).limit(limit)

    results = query.all()

    ranked_customers = []
    for serial_idx, row in enumerate(results, start=1):
        rev_paisa = int(round(float(row.total_revenue) * 100))
        rec_paisa = int(round(float(row.total_received) * 100))
        due_paisa = int(round(float(row.total_receivable) * 100))

        reliability = 100.0
        if rev_paisa > 0:
            reliability = round(min(100.0, (rec_paisa / rev_paisa) * 100.0), 2)

        ranked_customers.append(
            TopCustomerItem(
                serial_no=serial_idx,
                client_id=row.client_id,
                client_code=row.client_code,
                name=row.name,
                pan_number=row.contact_person or "",
                total_orders=int(row.order_count),
                total_pairs=float(row.total_pairs),
                total_revenue_paisa=rev_paisa,
                total_received_paisa=rec_paisa,
                outstanding_receivable_paisa=due_paisa,
                reliability_score=reliability
            )
        )
    return ranked_customers


@router.get("/production-ratios", response_model=ProductionRatioResponse)
def get_production_ratios(
    timeframe: Literal["1m", "3m", "1y"] = Query("1m", description="Timeframe: 1m (30 days), 3m (90 days), 1y (365 days)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Points 6 & 9: Daily worker and production logs tracking worker count, working hours, and output pairs,
    with interactive ratio graphs across 1-month, 3-month, and 1-year timeframes.
    """
    days = 30 if timeframe == "1m" else (90 if timeframe == "3m" else 365)
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days)
    start_str = start_date.strftime("%Y-%m-%d")

    # 1. Fetch any explicit DailyFactoryLog entries
    daily_logs = db.query(DailyFactoryLog).filter(
        DailyFactoryLog.company_id == current_user.company_id,
        DailyFactoryLog.date_ad >= start_str
    ).all()
    logs_by_date = {log.date_ad: log for log in daily_logs}

    # 2. Fetch Production Batches within date range
    batches = db.query(ProductionBatch).filter(
        ProductionBatch.company_id == current_user.company_id,
        ProductionBatch.date_ad >= start_str,
        ProductionBatch.status != "cancelled"
    ).all()

    # Get active workers count as fallback baseline
    active_workers_count = db.query(func.count(Worker.id)).filter(
        Worker.company_id == current_user.company_id,
        Worker.is_active == True
    ).scalar() or 20  # default 20 if no workers registered yet

    # Group batches by date
    batches_by_date = {}
    for b in batches:
        d = b.date_ad
        if d not in batches_by_date:
            batches_by_date[d] = {
                "produced": 0.0,
                "workers": 0,
                "date_bs": b.date_bs
            }
        batches_by_date[d]["produced"] += float(b.produced_quantity)
        batches_by_date[d]["workers"] = max(batches_by_date[d]["workers"], b.worker_count or 1)

    # 3. Combine distinct dates
    all_dates = sorted(set(list(logs_by_date.keys()) + list(batches_by_date.keys())))

    daily_records: List[DailyRecordItem] = []
    total_pairs_all = 0.0
    total_workers_sum = 0
    total_hours_sum = 0.0

    for d_str in all_dates:
        log_entry = logs_by_date.get(d_str)
        batch_entry = batches_by_date.get(d_str)

        if log_entry:
            pairs = float(log_entry.total_pairs_produced)
            workers = log_entry.total_workers
            hours = float(log_entry.total_working_hours)
            bs = log_entry.date_bs
        elif batch_entry:
            pairs = float(batch_entry["produced"])
            workers = batch_entry["workers"] if batch_entry["workers"] > 0 else active_workers_count
            hours = float(workers * 8.0)
            bs = batch_entry["date_bs"]
        else:
            continue

        if not bs:
            bs = _approx_ad_to_bs(d_str)

        pairs_per_w = round(pairs / workers, 2) if workers > 0 else 0.0
        pairs_per_h = round(pairs / hours, 2) if hours > 0 else 0.0

        daily_records.append(
            DailyRecordItem(
                date_ad=d_str,
                date_bs=bs,
                worker_count=workers,
                total_working_hours=hours,
                pairs_produced=pairs,
                pairs_per_worker=pairs_per_w,
                pairs_per_hour=pairs_per_h
            )
        )

        total_pairs_all += pairs
        total_workers_sum += workers
        total_hours_sum += hours

    # Summary
    num_days = len(daily_records)
    avg_workers = round(total_workers_sum / num_days, 1) if num_days > 0 else 0.0
    avg_pairs_worker = round(total_pairs_all / total_workers_sum, 2) if total_workers_sum > 0 else 0.0
    avg_pairs_hour = round(total_pairs_all / total_hours_sum, 2) if total_hours_sum > 0 else 0.0

    summary = ProductionRatioSummary(
        avg_daily_workers=avg_workers,
        total_pairs_produced=round(total_pairs_all, 1),
        avg_pairs_per_worker=avg_pairs_worker,
        avg_pairs_per_man_hour=avg_pairs_hour
    )

    return ProductionRatioResponse(
        timeframe=timeframe,
        summary=summary,
        daily_records=daily_records
    )


@router.post("/daily-logs", status_code=status.HTTP_201_CREATED)
def record_daily_factory_log(
    payload: DailyLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_editor)
):
    """
    Log or update daily worker count and shift hours for a specific date.
    Enforces editor permissions.
    """
    bs_date = payload.date_bs or _approx_ad_to_bs(payload.date_ad)

    # Check if entry exists for this company and date
    existing = db.query(DailyFactoryLog).filter(
        DailyFactoryLog.company_id == current_user.company_id,
        DailyFactoryLog.date_ad == payload.date_ad
    ).first()

    # Calculate pairs from production batches if not provided
    pairs = payload.total_pairs_produced
    if pairs is None:
        batch_sum = db.query(func.coalesce(func.sum(ProductionBatch.produced_quantity), 0.0)).filter(
            ProductionBatch.company_id == current_user.company_id,
            ProductionBatch.date_ad == payload.date_ad,
            ProductionBatch.status != "cancelled"
        ).scalar() or 0.0
        pairs = int(round(batch_sum))

    pairs_worker = round(pairs / payload.total_workers, 2) if payload.total_workers > 0 else 0.0
    pairs_hour = round(pairs / payload.total_working_hours, 2) if payload.total_working_hours > 0 else 0.0

    if existing:
        existing.date_bs = bs_date
        existing.total_workers = payload.total_workers
        existing.total_working_hours = payload.total_working_hours
        existing.total_pairs_produced = pairs
        existing.pairs_per_worker_ratio = pairs_worker
        existing.pairs_per_man_hour_ratio = pairs_hour
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}
    else:
        new_log = DailyFactoryLog(
            company_id=current_user.company_id,
            date_ad=payload.date_ad,
            date_bs=bs_date,
            total_workers=payload.total_workers,
            total_working_hours=payload.total_working_hours,
            total_pairs_produced=pairs,
            pairs_per_worker_ratio=pairs_worker,
            pairs_per_man_hour_ratio=pairs_hour
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return {"status": "created", "id": new_log.id}
