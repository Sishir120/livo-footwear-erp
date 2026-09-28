from datetime import date, datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class StockSnapshot(Base):
    """
    Materialized stock ledger balance snapshot for O(1) query scaling.
    Stock at any time = Latest Snapshot Balance + SUM(movements where id > last_movement_id).
    """
    __tablename__ = "stock_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    balance = Column(Integer, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    last_movement_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "product_id", "snapshot_date", name="uq_stock_snapshot"),
    )

    company = relationship("Company")
    product = relationship("Product")
