from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class DailyFactoryLog(Base):
    """
    Daily aggregated production and factory worker metric roll-up.
    Tracks worker count, working shift hours, pairs produced, and productivity ratios.
    """
    __tablename__ = "daily_factory_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    total_workers = Column(Integer, nullable=False, default=0)
    total_working_hours = Column(Float, nullable=False, default=0.0)
    total_pairs_produced = Column(Integer, nullable=False, default=0)
    pairs_per_worker_ratio = Column(Float, nullable=False, default=0.0)
    pairs_per_man_hour_ratio = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("company_id", "date_ad", name="uq_company_daily_log_date"),
    )
