from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    batch_number = Column(String(50), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    target_quantity = Column(Float, nullable=False)
    produced_quantity = Column(Float, nullable=False, default=0.0)
    worker_count = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="completed")  # completed, in_progress, cancelled
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("Product")
    material_usages = relationship("ProductionMaterialUsage", back_populates="batch", cascade="all, delete-orphan")

class ProductionMaterialUsage(Base):
    __tablename__ = "production_material_usage"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=False, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False)
    quantity_used = Column(Float, nullable=False)

    batch = relationship("ProductionBatch", back_populates="material_usages")
    raw_material = relationship("RawMaterial")
