from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base


class BranchType(str, Enum):
    HEAD_OFFICE = "HEAD_OFFICE"
    FACTORY = "FACTORY"
    RETAIL_OUTLET = "RETAIL_OUTLET"
    REGIONAL_HUB = "REGIONAL_HUB"


class Branch(Base):
    """
    Branch / Operating Location Model:
    Represents an internal operating division, factory, regional showroom, or distribution hub
    belonging to the parent Legal Entity (Company).
    """
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_company_branch_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)  # e.g., "BR-KTM-01", "BR-BRG-01"
    name = Column(String(100), nullable=False)
    type = Column(String(30), default=BranchType.RETAIL_OUTLET.value, nullable=False)
    address = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    company = relationship("Company")
    warehouses = relationship("Warehouse", back_populates="branch")
