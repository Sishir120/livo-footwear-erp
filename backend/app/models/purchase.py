from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime, ForeignKey, Text, UniqueConstraint, Date, Float, CheckConstraint, func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_supplier_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    pan_number = Column(String(15), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class RawMaterial(Base):
    __tablename__ = "raw_materials"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_raw_material_code"),
        CheckConstraint("unit IN ('kg', 'pcs', 'litre')", name="chk_raw_material_unit"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False, default="kg")  # kg, pcs, litre
    reorder_level = Column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False, server_default="0.0000")
    current_stock = Column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False, server_default="0.0000")
    min_stock_alert = Column(Numeric(12, 4), default=Decimal("0.0000"))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False, index=True)
    quantity = Column(Numeric, nullable=False)
    unit_price = Column(Numeric, nullable=False)
    total_amount = Column(Numeric, nullable=False)
    purchase_date_ad = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    purchase_date_bs = Column(String(10), nullable=False)             # YYYY-MM-DD BS
    order_date_ad = Column(Date, nullable=True)
    order_date_bs = Column(String(10), nullable=True)
    receipt_date_ad = Column(Date, nullable=True)
    receipt_date_bs = Column(String(10), nullable=True)
    status = Column(String(20), default="RECEIVED", nullable=False, server_default="RECEIVED")  # ORDERED, PARTIALLY_RECEIVED, RECEIVED, CANCELLED
    payment_status = Column(String(50), default="unpaid")              # paid, partial, unpaid
    
    # Landed Cost Multi-Column Paisa Allocation
    carrying_in_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    import_duty_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    china_carrying_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    insurance_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    total_landed_cost_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    effective_unit_rate_paisa = Column(BigInteger, default=0, nullable=False, server_default="0")
    
    # Receiving tracking
    received_quantity = Column(Numeric(12, 4), default=Decimal("0.0000"), nullable=False, server_default="0.0000")
    grn_number = Column(String(32), unique=True, nullable=True)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier")
    raw_material = relationship("RawMaterial")
    received_by = relationship("User", foreign_keys=[received_by_id])

class RawMaterialMovement(Base):
    __tablename__ = "raw_material_movements"
    __table_args__ = (
        CheckConstraint("direction IN (1, -1)", name="chk_rm_movement_direction"),
        CheckConstraint("quantity > 0", name="chk_rm_movement_quantity_positive"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False, index=True)
    movement_date = Column(Date, nullable=False)
    movement_date_bs = Column(String(10), nullable=False)
    direction = Column(Integer, nullable=False)  # +1 (Inward/Receipt/Adj In), -1 (Outward/BOM Issue/Scrap/Adj Out)
    quantity = Column(Numeric(12, 4), nullable=False)
    unit_cost_paisa = Column(BigInteger, nullable=False, default=0)
    movement_type = Column(String(32), nullable=False)  # PURCHASE_RECEIPT, BOM_ISSUE, SCRAP_WRITEOFF, ADJUSTMENT
    reference_voucher = Column(String(64), nullable=False)  # PO-2026-0042, BATCH-0118, ADJ-005
    notes = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    raw_material = relationship("RawMaterial")
    actor = relationship("User", foreign_keys=[actor_id])

