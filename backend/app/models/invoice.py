from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class Invoice(Base):
    __tablename__ = "invoices"
    # DB-level guard against concurrent invoice number collision (RULES.md §3)
    # No two invoices for the same company may share a sequence_number.
    __table_args__ = (
        UniqueConstraint("company_id", "sequence_number", name="uq_invoice_company_sequence"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)  # e.g., INV-2026-00001
    sequence_number = Column(Integer, nullable=False, index=True)      # Sequential per company
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    subtotal = Column(Float, nullable=False)
    vat_enabled = Column(Boolean, default=False, nullable=False)        # VAT flag off by default per RULES.md §0
    vat_rate = Column(Float, default=0.0, nullable=False)              # e.g., 13.0
    vat_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, nullable=False)
    received_amount = Column(Float, nullable=False, default=0.0)
    receivable_amount = Column(Float, nullable=False, default=0.0)
    is_void = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sales_order = relationship("SalesOrder")


class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True, index=True)
    current_sequence = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company")

