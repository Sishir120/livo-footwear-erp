from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, Boolean, Index, func
from sqlalchemy.orm import relationship
from app.db.session import Base

class ReceivableEntry(Base):
    """
    Append-only Accounts Receivable ledger.
    direction: +1 for Debit (Receivable Increase e.g. Invoice, Opening Balance),
               -1 for Credit (Receivable Decrease e.g. Payment, Credit Note, Write Off)
    amount_paisa: Exact integer paisa (1 NPR = 100 paisa)
    """
    __tablename__ = "receivable_entries"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    entry_type = Column(String(32), nullable=False, index=True)
    # INVOICE_POSTED, PAYMENT_CASH, PAYMENT_BANK, CREDIT_NOTE, VOID_REVERSAL, OPENING_BALANCE, WRITE_OFF
    direction = Column(Integer, nullable=False)  # +1 or -1
    amount_paisa = Column(BigInteger, nullable=False)
    source_doc_ref = Column(String(64), nullable=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc), index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    is_disputed = Column(Boolean, default=False, nullable=False)
    dispute_notes = Column(String(255), nullable=True)
    notes = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_ar_party_date", "company_id", "client_id", "occurred_at"),
    )

    company = relationship("Company")
    client = relationship("Client")
    invoice = relationship("Invoice")
    actor = relationship("User")


class PaymentAllocation(Base):
    """
    Settlement link mapping a payment receipt entry to an invoice entry.
    Enforces exact allocation in integer paisa.
    """
    __tablename__ = "payment_allocations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    payment_entry_id = Column(Integer, ForeignKey("receivable_entries.id"), nullable=False, index=True)
    invoice_entry_id = Column(Integer, ForeignKey("receivable_entries.id"), nullable=False, index=True)
    allocated_paisa = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
    payment_entry = relationship("ReceivableEntry", foreign_keys=[payment_entry_id])
    invoice_entry = relationship("ReceivableEntry", foreign_keys=[invoice_entry_id])
