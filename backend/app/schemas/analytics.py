from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TopProductItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    product_id: int
    code: str
    name: str
    category: Optional[str] = None
    total_pairs_sold: float
    total_revenue_paisa: int
    order_count: int


class TopCustomerItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serial_no: int
    client_id: int
    client_code: str
    name: str
    pan_number: Optional[str] = None
    total_orders: int
    total_pairs: float
    total_revenue_paisa: int
    total_received_paisa: int
    outstanding_receivable_paisa: int
    reliability_score: float


class DailyRecordItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_ad: str
    date_bs: str
    worker_count: int
    total_working_hours: float
    pairs_produced: float
    pairs_per_worker: float
    pairs_per_hour: float


class ProductionRatioSummary(BaseModel):
    avg_daily_workers: float
    total_pairs_produced: float
    avg_pairs_per_worker: float
    avg_pairs_per_man_hour: float


class ProductionRatioResponse(BaseModel):
    timeframe: str
    summary: ProductionRatioSummary
    daily_records: List[DailyRecordItem]


class DailyLogCreate(BaseModel):
    date_ad: str
    date_bs: Optional[str] = None
    total_workers: int
    total_working_hours: float
    total_pairs_produced: Optional[int] = None
