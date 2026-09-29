from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # Boot, Slipper, Shoe, Sandal
    size = Column(String(50), nullable=True)      # e.g., 39, 40, 41, 42
    color = Column(String(50), nullable=True)     # Black, Brown, Red, Navy
    unit_price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Note: NO stock_qty field here! Stock is derived strictly from StockMovement ledger per RULES.md §1

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    company = relationship("Company")

class StockMovement(Base):
    """
    Append-only stock ledger per RULES.md §1.
    direction: +1 for IN (production/return/purchase/adjustment), -1 for OUT (sales/loss/damage/adjustment)
    ref_type: 'production', 'sale', 'adjustment', 'return', 'void_reversal'
    movement_type: 'PRODUCTION_IN', 'SALES_OUT', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT', 'TRANSFER_IN', 'TRANSFER_OUT', 'VOID_REVERSAL'
    """
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False, default=1, server_default="1")
    size = Column(String(20), nullable=True)
    quantity = Column(Float, nullable=False)
    direction = Column(Integer, nullable=False)  # +1 or -1
    ref_type = Column(String(50), nullable=False)
    ref_id = Column(Integer, nullable=True)
    movement_type = Column(String(50), nullable=False, default="PRODUCTION_IN", server_default="PRODUCTION_IN")
    source_doc_ref = Column(String(64), nullable=True)
    reversal_of_id = Column(Integer, ForeignKey("stock_movements.id"), nullable=True)
    reason_code = Column(String(32), nullable=True)
    reason_text = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1, server_default="1")
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_stock_ledger_lookup", "company_id", "product_id", "size", "created_at"),
    )

    product = relationship("Product")
    warehouse = relationship("Warehouse")
    actor = relationship("User", foreign_keys=[actor_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    reversed_movement = relationship("StockMovement", remote_side=[id], foreign_keys=[reversal_of_id])

    def __init__(self, **kwargs):
        if "movement_type" not in kwargs or not kwargs["movement_type"]:
            ref = str(kwargs.get("ref_type", "")).lower()
            dir_val = kwargs.get("direction", 1)
            if ref == "production":
                kwargs["movement_type"] = "PRODUCTION_IN"
            elif ref == "sale":
                kwargs["movement_type"] = "SALES_OUT"
            elif ref == "adjustment":
                kwargs["movement_type"] = "ADJUSTMENT_IN" if dir_val == 1 else "ADJUSTMENT_OUT"
            elif ref == "void_reversal":
                kwargs["movement_type"] = "VOID_REVERSAL"
            elif ref == "transfer":
                kwargs["movement_type"] = "TRANSFER_IN" if dir_val == 1 else "TRANSFER_OUT"
            else:
                kwargs["movement_type"] = "PRODUCTION_IN" if dir_val == 1 else "SALES_OUT"
        super().__init__(**kwargs)
