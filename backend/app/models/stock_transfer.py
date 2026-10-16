from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class StockTransfer(Base):
    __tablename__ = "stock_transfers"
    __table_args__ = (
        UniqueConstraint("company_id", "transfer_number", name="uq_company_transfer_number"),
        Index("ix_transfers_source_wh", "company_id", "source_warehouse_id"),
        Index("ix_transfers_dest_wh", "company_id", "destination_warehouse_id"),
        Index("ix_transfers_status", "company_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    transfer_number = Column(String(50), nullable=False, index=True)  # e.g., TRF-01-00001
    source_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    destination_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, index=True)
    status = Column(String(32), default="DRAFT", nullable=False)  # DRAFT, IN_TRANSIT, RECEIVED, CANCELLED

    transfer_date_ad = Column(String(10), nullable=False)
    transfer_date_bs = Column(String(10), nullable=False)
    dispatch_date_ad = Column(String(10), nullable=True)
    dispatch_date_bs = Column(String(10), nullable=True)
    receipt_date_ad = Column(String(10), nullable=True)
    receipt_date_bs = Column(String(10), nullable=True)

    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dispatched_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    carrier_name = Column(String(128), nullable=True)
    vehicle_number = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    source_warehouse = relationship("Warehouse", foreign_keys=[source_warehouse_id])
    destination_warehouse = relationship("Warehouse", foreign_keys=[destination_warehouse_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    dispatched_by = relationship("User", foreign_keys=[dispatched_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])
    items = relationship("StockTransferItem", back_populates="transfer", cascade="all, delete-orphan")


class StockTransferItem(Base):
    __tablename__ = "stock_transfer_items"
    __table_args__ = (
        Index("ix_transfer_items_lookup", "company_id", "transfer_id", "product_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    transfer_id = Column(Integer, ForeignKey("stock_transfers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    size = Column(String(20), nullable=True)

    requested_quantity = Column(Numeric, nullable=False)
    dispatched_quantity = Column(Numeric, default=0.0, nullable=False)
    received_quantity = Column(Numeric, default=0.0, nullable=False)
    discrepancy_quantity = Column(Numeric, default=0.0, nullable=False)  # dispatched - received
    discrepancy_reason = Column(String(255), nullable=True)

    transfer = relationship("StockTransfer", back_populates="items")
    product = relationship("Product")
