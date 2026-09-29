from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, BigInteger, String, Float, Date, DateTime, ForeignKey, Boolean, Index, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Worker(Base):
    """
    Factory worker profile. Supports both salaried staff and hourly/piece wage workers.
    Scoped by company_id for multi-tenant isolation.
    """
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    worker_code = Column(String(32), nullable=False, index=True)  # e.g., EMP-101, WKR-042
    name = Column(String(128), nullable=False)
    join_date = Column(Date, nullable=False, default=date.today)
    pay_type = Column(String(16), nullable=False)  # 'SALARY' or 'WAGE'
    basic_rate_paisa = Column(BigInteger, nullable=False)  # Monthly salary or hourly wage rate in integer paisa
    phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "worker_code", name="uq_company_worker_code"),
        Index("ix_worker_company_status", "company_id", "is_active"),
    )

    company = relationship("Company")
    advances = relationship("WorkerAdvance", back_populates="worker", cascade="all, delete-orphan")
    monthly_records = relationship("WorkerMonthlyRecord", back_populates="worker", cascade="all, delete-orphan")


class WorkerAdvance(Base):
    """
    Advance payment ledger for workers.
    entry_type: 'ISSUED' (+ advance taken by worker) or 'RECOVERED' (- advance repaid or deducted from salary)
    """
    __tablename__ = "worker_advances"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    amount_paisa = Column(BigInteger, nullable=False)
    entry_type = Column(String(16), nullable=False)  # 'ISSUED' vs 'RECOVERED'
    date = Column(Date, nullable=False, default=date.today)
    notes = Column(String(255), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_advances_worker_date", "company_id", "worker_id", "date"),
    )

    company = relationship("Company")
    worker = relationship("Worker", back_populates="advances")
    actor = relationship("User")


class WorkerMonthlyRecord(Base):
    """
    Monthly hours, overtime, and finalized payroll record per worker.
    month_year: YYYY-MM (e.g. 2026-09 or 2083-06)
    """
    __tablename__ = "worker_monthly_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    month_year = Column(String(10), nullable=False, index=True)  # YYYY-MM
    total_working_hours = Column(Float, default=0.0, nullable=False)
    overtime_hours = Column(Float, default=0.0, nullable=False)
    gross_pay_paisa = Column(BigInteger, default=0, nullable=False)
    advance_deduction_paisa = Column(BigInteger, default=0, nullable=False)
    net_paid_paisa = Column(BigInteger, default=0, nullable=False)
    paid_date = Column(Date, nullable=True)
    payment_method = Column(String(32), nullable=True)  # 'CASH', 'BANK'
    status = Column(String(16), default="PENDING", nullable=False)  # 'PENDING', 'PAID'
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("company_id", "worker_id", "month_year", name="uq_worker_monthly_company_month"),
        Index("ix_monthly_worker_status", "company_id", "month_year", "status"),
    )

    company = relationship("Company")
    worker = relationship("Worker", back_populates="monthly_records")
