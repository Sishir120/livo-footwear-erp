from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class ProductionSyncLog(Base):
    __tablename__ = "production_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("production_batches.id"), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)  # 'ACCEPTED', 'REJECTED', 'CONFLICT'
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company")
    batch = relationship("ProductionBatch")
    actor = relationship("User")

    __table_args__ = (
        Index("ix_sync_company_key", "company_id", "idempotency_key"),
    )
