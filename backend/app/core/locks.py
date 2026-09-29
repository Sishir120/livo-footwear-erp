"""
PostgreSQL Distributed Advisory Locks & In-Process Fallback for Stock Movements & Credit Limits.
Eliminates multi-worker mutex blindspots across Uvicorn workers and autoscaled containers.
"""
import hashlib
import threading
from collections import defaultdict
from typing import Any
from sqlalchemy import text, event
from sqlalchemy.orm import Session

_product_locks = defaultdict(threading.RLock)
_idempotency_locks = defaultdict(threading.RLock)
_mutation_locks = defaultdict(threading.RLock)
_credit_locks = defaultdict(threading.RLock)
_meta_lock = threading.RLock()

def hash_args_to_bigint(*args: Any) -> int:
    """
    Computes a deterministic signed 64-bit integer from arbitrary arguments.
    Mapped to signed 64-bit integer range [-2^63, 2^63 - 1] for PostgreSQL pg_advisory_xact_lock.
    """
    raw_str = ":".join(str(a) for a in args)
    raw_hash = int(hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:15], 16)
    return raw_hash - (1 << 63) if raw_hash >= (1 << 63) else raw_hash

def _register_thread_lock_release(db: Session, lock: threading.RLock):
    """Binds an in-process thread lock to the SQLAlchemy session lifecycle, releasing on commit/rollback/close."""
    if not hasattr(db, "info"):
        return
    if "_held_thread_locks" not in db.info:
        db.info["_held_thread_locks"] = []

        @event.listens_for(db, "after_transaction_end")
        def _release_on_tx_end(session, transaction):
            held = session.info.get("_held_thread_locks", [])
            while held:
                l = held.pop()
                try:
                    l.release()
                except RuntimeError:
                    pass

    db.info["_held_thread_locks"].append(lock)

def get_stock_mutex(company_id: int, product_id: int) -> threading.RLock:
    """Returns an in-process mutex dedicated to a specific product variant (retained for backward compatibility)."""
    with _meta_lock:
        return _product_locks[(company_id, product_id)]

def get_advisory_lock_key(company_id: int, product_id: int) -> int:
    """Legacy 64-bit signed bigint lock key from company_id and product_id."""
    raw_key = ((company_id & 0xFFFFFFFF) << 32) | (product_id & 0xFFFFFFFF)
    return raw_key - (1 << 64) if raw_key >= (1 << 63) else raw_key

def acquire_stock_advisory_lock(db: Session, company_id: int, product_id: int) -> int:
    """Acquires a transaction-scoped PostgreSQL Advisory Lock for (company_id, product_id)."""
    lock_key = get_advisory_lock_key(company_id, product_id)
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_key})
    except Exception:
        pass
    return lock_key

def get_stock_mutation_mutex(company_id: int, warehouse_id: int, product_id: int, size: str) -> threading.RLock:
    """Returns an in-process mutex dedicated to (company_id, warehouse_id, product_id, size)."""
    with _meta_lock:
        return _mutation_locks[(company_id, warehouse_id, product_id, str(size))]

def acquire_stock_mutation_lock(db: Session, company_id: int, warehouse_id: int, product_id: int, size: str) -> int:
    """
    Acquires a transaction-scoped PostgreSQL Advisory Lock for stock mutation on (company, warehouse, product, size).
    Computes deterministic signed 64-bit bigint hash:
      lock_id = hash_args_to_bigint("stock", company_id, warehouse_id, product_id, size)
    Falls back to an in-process keyed threading lock on SQLite test runners, auto-released on tx end.
    """
    lock_id = hash_args_to_bigint("stock", company_id, warehouse_id, product_id, size)
    bind = None
    try:
        bind = db.get_bind()
    except Exception:
        pass

    if bind and bind.dialect.name == "postgresql":
        try:
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
        except Exception:
            pass
    else:
        # SQLite / in-process fallback
        mutex = get_stock_mutation_mutex(company_id, warehouse_id, product_id, size)
        mutex.acquire()
        _register_thread_lock_release(db, mutex)

    return lock_id

def get_client_credit_mutex(company_id: int, client_id: int) -> threading.RLock:
    """Returns an in-process mutex dedicated to (company_id, client_id) credit limits."""
    with _meta_lock:
        return _credit_locks[(company_id, client_id)]

def acquire_client_credit_lock(db: Session, company_id: int, client_id: int) -> int:
    """
    Acquires a transaction-scoped PostgreSQL Advisory Lock on client credit evaluation:
      lock_id = hash_args_to_bigint("credit", company_id, client_id)
    Falls back to an in-process keyed threading lock on SQLite test runners, auto-released on tx end.
    """
    lock_id = hash_args_to_bigint("credit", company_id, client_id)
    bind = None
    try:
        bind = db.get_bind()
    except Exception:
        pass

    if bind and bind.dialect.name == "postgresql":
        try:
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
        except Exception:
            pass
    else:
        # SQLite / in-process fallback
        mutex = get_client_credit_mutex(company_id, client_id)
        mutex.acquire()
        _register_thread_lock_release(db, mutex)

    return lock_id

def get_idempotency_mutex(company_id: int, idempotency_key: str) -> threading.RLock:
    """Returns an in-process mutex dedicated to an idempotency key."""
    with _meta_lock:
        return _idempotency_locks[(company_id, idempotency_key)]

def get_idempotency_lock_key(company_id: int, idempotency_key: str) -> int:
    """Derive a deterministic signed 64-bit integer from (company_id, idempotency_key)."""
    return hash_args_to_bigint(company_id, idempotency_key)

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
