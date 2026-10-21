from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from app.db.session import Base

class Invoice(Base):
    __tablename__ = "invoices"
    # DB-level guard against concurrent invoice number collision (RULES.md §3)
    # No two invoices for the same company may share a sequence_number.
    __table_args__ = (
        UniqueConstraint("company_id", "sequence_number", name="uq_invoice_company_sequence"),
        UniqueConstraint("company_id", "invoice_number", name="uq_invoice_company_invoice_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)  # e.g., INV-2026-00001
    sequence_number = Column(Integer, nullable=True, index=True)      # Sequential per company (None for drafts)
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    subtotal = Column(Numeric, nullable=False)
    vat_enabled = Column(Boolean, default=True, nullable=False)         # Mandatory statutory VAT enabled by default
    vat_rate = Column(Numeric, default=13.0, nullable=False)             # Statutory standard Nepal IRD VAT rate 13%
    vat_amount = Column(Numeric, default=0.0, nullable=False)
    total_amount = Column(Numeric, nullable=False)
    received_amount = Column(Numeric, nullable=False, default=0.0)
    receivable_amount = Column(Numeric, nullable=False, default=0.0)
    is_void = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sales_order = relationship("SalesOrder")

    @property
    def taxable_amount_paisa(self) -> int:
        if "taxable_amount_paisa" in self.__dict__:
            return self.__dict__["taxable_amount_paisa"]
        amt = self.subtotal if self.subtotal is not None else 0
        return int(round(float(amt) * 100))

    @taxable_amount_paisa.setter
    def taxable_amount_paisa(self, value: int):
        self.__dict__["taxable_amount_paisa"] = int(value)

    @property
    def vat_amount_paisa(self) -> int:
        if "vat_amount_paisa" in self.__dict__:
            return self.__dict__["vat_amount_paisa"]
        amt = self.vat_amount if self.vat_amount is not None else 0
        return int(round(float(amt) * 100))

    @vat_amount_paisa.setter
    def vat_amount_paisa(self, value: int):
        self.__dict__["vat_amount_paisa"] = int(value)

    @property
    def total_amount_paisa(self) -> int:
        if "total_amount_paisa" in self.__dict__:
            return self.__dict__["total_amount_paisa"]
        amt = self.total_amount if self.total_amount is not None else 0
        return int(round(float(amt) * 100))

    @total_amount_paisa.setter
    def total_amount_paisa(self, value: int):
        self.__dict__["total_amount_paisa"] = int(value)


from sqlalchemy import event

@event.listens_for(Invoice, "init")
@event.listens_for(Invoice, "load")
def _populate_invoice_paisa(target, *args, **kwargs):
    sub = target.subtotal if target.subtotal is not None else 0
    vat = target.vat_amount if target.vat_amount is not None else 0
    tot = target.total_amount if target.total_amount is not None else 0
    target.__dict__["taxable_amount_paisa"] = int(round(float(sub) * 100))
    target.__dict__["vat_amount_paisa"] = int(round(float(vat) * 100))
    target.__dict__["total_amount_paisa"] = int(round(float(tot) * 100))



class InvoiceSequence(Base):
    __tablename__ = "invoice_sequences"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True, index=True)
    current_sequence = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    company = relationship("Company")


class CreditNote(Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        UniqueConstraint("company_id", "credit_note_number", name="uq_credit_note_company_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    receivable_entry_id = Column(Integer, ForeignKey("receivable_entries.id"), nullable=True, index=True)
    credit_note_number = Column(String(50), nullable=False, index=True)
    date_ad = Column(String(10), nullable=False)
    date_bs = Column(String(10), nullable=False)
    reason = Column(String(255), nullable=False)
    taxable_amount_paisa = Column(Integer, nullable=False, default=0)
    vat_amount_paisa = Column(Integer, nullable=False, default=0)
    total_amount_paisa = Column(Integer, nullable=False, default=0)
    return_to_stock = Column(Boolean, nullable=False, default=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    invoice = relationship("Invoice")
    items = relationship("CreditNoteItem", back_populates="credit_note", cascade="all, delete-orphan")


class CreditNoteItem(Base):
    __tablename__ = "credit_note_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    credit_note_id = Column(Integer, ForeignKey("credit_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Numeric, nullable=False)
    unit_price_paisa = Column(Integer, nullable=False)
    discount_paisa = Column(Integer, nullable=False, default=0)
    taxable_paisa = Column(Integer, nullable=False, default=0)
    vat_paisa = Column(Integer, nullable=False, default=0)
    total_paisa = Column(Integer, nullable=False, default=0)
    return_to_stock = Column(Boolean, nullable=False, default=False)

    credit_note = relationship("CreditNote", back_populates="items")
    product = relationship("Product")


