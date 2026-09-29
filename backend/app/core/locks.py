"""
PostgreSQL Distributed Advisory Locks & In-Process Fallback for Stock Movements.
Eliminates multi-worker mutex blindspots across Uvicorn workers and autoscaled containers.
"""
import threading
from collections import defaultdict
from sqlalchemy import text
from sqlalchemy.orm import Session

_product_locks = defaultdict(threading.Lock)
_meta_lock = threading.Lock()

def get_stock_mutex(company_id: int, product_id: int) -> threading.Lock:
    """Returns an in-process mutex dedicated to a specific product variant (retained for SQLite/unit tests)."""
    with _meta_lock:
        return _product_locks[(company_id, product_id)]

def get_advisory_lock_key(company_id: int, product_id: int) -> int:
    """
    Derive a deterministic 64-bit signed bigint lock key from company_id and product_id.
    Formula: (company_id << 32) | product_id
    Mapped to signed 64-bit integer range [-2^63, 2^63 - 1] for PostgreSQL pg_advisory_xact_lock.
    """
    raw_key = ((company_id & 0xFFFFFFFF) << 32) | (product_id & 0xFFFFFFFF)
    return raw_key - (1 << 64) if raw_key >= (1 << 63) else raw_key

def acquire_stock_advisory_lock(db: Session, company_id: int, product_id: int) -> int:
    """
    Acquires a transaction-scoped PostgreSQL Advisory Lock for (company_id, product_id).
    Inside the transaction block, executes: SELECT pg_advisory_xact_lock(:lock_id)
    Lock automatically releases upon transaction COMMIT or ROLLBACK.
    Safely falls back to no-op if the backend dialect is SQLite (unit tests).
    """
    lock_key = get_advisory_lock_key(company_id, product_id)
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_key})
    except Exception:
        # Fallback or dialect inspection fail-safe
        pass
    return lock_key


import hashlib

_idempotency_locks = defaultdict(threading.Lock)

def get_idempotency_mutex(company_id: int, idempotency_key: str) -> threading.Lock:
    """Returns an in-process mutex dedicated to an idempotency key."""
    with _meta_lock:
        return _idempotency_locks[(company_id, idempotency_key)]

def get_idempotency_lock_key(company_id: int, idempotency_key: str) -> int:
    """Derive a deterministic signed 64-bit integer from (company_id, idempotency_key)."""
    raw_hash = int(hashlib.sha256(f"{company_id}:{idempotency_key}".encode("utf-8")).hexdigest()[:15], 16)
    return raw_hash - (1 << 63) if raw_hash >= (1 << 63) else raw_hash

def acquire_idempotency_advisory_lock(db: Session, company_id: int, idempotency_key: str) -> int:
    """Acquires a transaction-scoped PostgreSQL Advisory Lock on integer hash of idempotency_key."""
    lock_key = get_idempotency_lock_key(company_id, idempotency_key)
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_key})
    except Exception:
        pass
    return lock_key
