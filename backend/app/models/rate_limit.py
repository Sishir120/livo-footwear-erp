from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Index
from app.db.session import Base

class RateLimitEntry(Base):
    """
    Shared distributed rate limiting log for multi-worker and multi-container environments.
    Stores timestamped access events keyed by client IP or tenant-identity and endpoint.
    """
    __tablename__ = "rate_limit_entries"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), nullable=False, index=True)
    endpoint = Column(String(64), nullable=False, index=True)
    timestamp = Column(Float, nullable=False, index=True)

    __table_args__ = (
        Index("ix_rate_limit_lookup", "key", "endpoint", "timestamp"),
    )
