from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class AccountGroup(Base):
    __tablename__ = "account_groups"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    group_type = Column(String(50), nullable=False)  # Asset, Liability, Income, Expense
    parent_id = Column(Integer, ForeignKey("account_groups.id"), nullable=True)

class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("account_groups.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    opening_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    group = relationship("AccountGroup")

class JournalVoucher(Base):
    __tablename__ = "journal_vouchers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    voucher_number = Column(String(50), nullable=False, index=True)
    voucher_type = Column(String(50), nullable=False)  # Sales, Purchase, Payment, Receipt, Journal
    date_ad = Column(String(10), nullable=False, index=True)
    date_bs = Column(String(10), nullable=False)
    narration = Column(Text, nullable=True)
    ref_type = Column(String(50), nullable=True)
    ref_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    entries = relationship("JournalEntry", back_populates="voucher", cascade="all, delete-orphan")

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    voucher_id = Column(Integer, ForeignKey("journal_vouchers.id"), nullable=False, index=True)
    ledger_id = Column(Integer, ForeignKey("ledger_accounts.id"), nullable=False, index=True)
    debit_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)

    voucher = relationship("JournalVoucher", back_populates="entries")
    ledger = relationship("LedgerAccount")
