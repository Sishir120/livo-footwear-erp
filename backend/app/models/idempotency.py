from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class IdempotencyRecord(Base):
    """
    Server-side persistence model for HTTP mutation idempotency keys.
    Guarantees exactly-once business effects for sales orders, invoices, payments,
    stock movements, production batches, HR payroll, and offline reconciliations.
    
    Scoped strictly by (company_id, idempotency_key) to preserve multi-tenant isolation.
    """
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    idempotency_key = Column(String(128), nullable=False, index=True)
    request_method = Column(String(16), nullable=False)
    request_path = Column(String(256), nullable=False)
    request_hash = Column(String(64), nullable=False)  # SHA-256 canonical fingerprint
    status = Column(String(32), nullable=False, default="PROCESSING")  # 'PROCESSING', 'COMPLETED', 'FAILED'
    response_status_code = Column(Integer, nullable=True)
    response_headers = Column(Text, nullable=True)     # JSON-encoded response headers to replay
    response_body = Column(Text, nullable=True)        # Cached response body payload
    resource_id = Column(String(64), nullable=True)     # Primary created resource ID if applicable
    resource_type = Column(String(64), nullable=True)   # Primary resource table/type
    error_message = Column(Text, nullable=True)        # Details on failure
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Lease expiration for stale processing
    recovery_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("company_id", "idempotency_key", name="uq_idempotency_company_key"),
        Index("ix_idempotency_company_key", "company_id", "idempotency_key"),
        Index("ix_idempotency_status_locked", "status", "locked_until"),
    )
