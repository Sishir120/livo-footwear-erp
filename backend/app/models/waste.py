from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class WasteRecord(Base):
    """
    Waste & scrap floor tracking per client requirement REQ-19 and Decision D.
    Strictly informational audit record that does NOT execute automated warehouse stock deductions,
    preventing duplicate deductions against BOM consumption until explicitly confirmed by client.
    """
    __tablename__ = "waste_records"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_waste_record_quantity_positive"),
        CheckConstraint("waste_type IN ('RAW_MATERIAL_SCRAP', 'FINISHED_PAIR_REJECT')", name="chk_waste_record_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    waste_date_ad = Column(Date, nullable=False)
    waste_date_bs = Column(String(10), nullable=False)
    waste_type = Column(String(32), nullable=False)  # RAW_MATERIAL_SCRAP, FINISHED_PAIR_REJECT
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=True, index=True)
    quantity = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(20), nullable=False)  # kg, pcs, litre, pair
    reason = Column(String(255), nullable=True)
    disposal_method = Column(String(64), nullable=True, default="DISCARDED")  # DISCARDED, RECYCLED, STORED, RESOLD
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
    raw_material = relationship("RawMaterial")
    product = relationship("Product")
    batch = relationship("ProductionBatch")
    actor = relationship("User", foreign_keys=[actor_id])
