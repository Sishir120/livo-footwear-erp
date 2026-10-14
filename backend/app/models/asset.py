from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, Date, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class FixedAsset(Base):
    """
    Fixed Assets Register per client requirement REQ-18 and Decision E.
    Tracks machinery, moulds, vehicles, tools, and furniture with acquisition dates and integer paisa valuation.
    """
    __tablename__ = "fixed_assets"
    __table_args__ = (
        CheckConstraint("purchase_cost_paisa >= 0", name="chk_fixed_asset_cost_non_negative"),
        CheckConstraint("quantity > 0", name="chk_fixed_asset_quantity_positive"),
        UniqueConstraint("company_id", "asset_code", name="uq_company_asset_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    asset_code = Column(String(50), nullable=False, index=True)
    asset_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # MACHINERY, MOULD, VEHICLE, TOOLS, FURNITURE, OTHER
    purchase_date_ad = Column(Date, nullable=False)
    purchase_date_bs = Column(String(10), nullable=False)
    purchase_cost_paisa = Column(BigInteger, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    location = Column(String(255), nullable=True)
    remarks = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
    actor = relationship("User", foreign_keys=[actor_id])
