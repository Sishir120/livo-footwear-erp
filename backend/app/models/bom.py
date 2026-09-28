from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class BillOfMaterials(Base):
    """
    Bill of Materials (BOM) definition for footwear models.
    Defines proportional raw material consumption (leather, soles, laces, adhesives) per pair.
    """
    __tablename__ = "bill_of_materials"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    raw_material_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=False, index=True)
    quantity_required = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "product_id", "raw_material_id", name="uq_bom_product_material"),
    )

    company = relationship("Company")
    product = relationship("Product")
    raw_material = relationship("RawMaterial")
