from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
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

class StockMovement(Base):
    """
    Append-only stock ledger per RULES.md §1.
    direction: +1 for IN (production/return/purchase), -1 for OUT (sales/loss/damage)
    ref_type: 'production', 'sale', 'adjustment', 'return'
    """
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    direction = Column(Integer, nullable=False)  # +1 or -1
    ref_type = Column(String(50), nullable=False)
    ref_id = Column(Integer, nullable=True)
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product")
