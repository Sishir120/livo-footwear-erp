from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class DocumentSequence(Base):
    """
    Centralized transactional sequence generator for all business documents.
    Provides collision-resistant counters per company and document type.
    """
    __tablename__ = "document_sequences"

    __table_args__ = (
        UniqueConstraint("company_id", "document_type", name="uq_company_doc_type_sequence"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # e.g., "SALES_ORDER", "PRODUCTION", "RECEIPT", "ADJUSTMENT"
    current_sequence = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
