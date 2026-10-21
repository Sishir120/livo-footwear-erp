"""
LIVO Footwear ERP — Sequence Allocator
Provides collision-resistant document number generation for all business entities.

Strategy:
  - PostgreSQL (production): Uses SELECT ... FOR UPDATE row-level locking on
    the DocumentSequence table. This serializes all concurrent writes at the
    DB level with zero application-level locks or retries needed.

  - SQLite (testing): SELECT FOR UPDATE is a no-op in SQLite, so we add a
    Python-level threading.Lock keyed by (company_id, document_type) to
    provide equivalent serialization during unit tests.

Gap policy: Gaps are ACCEPTABLE (e.g., after rollbacks). Duplicates are NEVER acceptable.
"""

import re
import time
import logging
import threading
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.sequence import DocumentSequence

logger = logging.getLogger("livo_erp.sequence")


class SequenceAllocationError(HTTPException):
    """
    Raised when document sequence allocation fails.
    Ensures fail-closed behavior: never fabricates or duplicates document numbers.
    """
    def __init__(
        self,
        detail: str = "Failed to allocate document sequence number. Please retry.",
        status_code: int = 503,
        document_type: Optional[str] = None,
        company_id: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        self.document_type = document_type
        self.company_id = company_id
        self.original_error = original_error
        super().__init__(status_code=status_code, detail=detail)


def is_transient_retryable_sequence_error(exc: Exception) -> bool:
    """
    Evaluates whether a database exception encountered during sequence allocation
    is demonstrably transient and safe to retry under a savepoint.

    Safe to retry under savepoint (transient lock conflicts):
    - 40P01: deadlock_detected (transient lock conflict resolved on rollback)
    - 55P03: lock_not_available (transient lock timeout resolved after backoff)

    Unsafe to retry under savepoint (fail-closed immediately):
    - 40001: serialization_failure (snapshot is pinned; in-transaction savepoint
      retry cannot advance snapshot under REPEATABLE READ / SERIALIZABLE;
      requires whole-transaction retry at service boundary)
    - Connection drops / network down
    - IntegrityError (FK violations, constraint corruptions)
    - Syntax / Schema errors
    """
    orig = getattr(exc, "orig", None)
    pgcode = getattr(orig, "pgcode", None) or ""
    if pgcode in ("40P01", "55P03"):
        return True

    msg = str(exc).lower()
    if "deadlock detected" in msg or "canceling statement due to lock timeout" in msg or "could not obtain lock" in msg:
        return True

    return False


# ---------------------------------------------------------------------------
# Python-level mutex registry for SQLite environments (test only)
# On PostgreSQL, DB-level row updates / FOR UPDATE provide the serialization.
# ---------------------------------------------------------------------------
_sqlite_locks: dict[tuple, threading.Lock] = {}
_registry_lock = threading.Lock()


def _get_sqlite_lock(company_id: int, document_type: str) -> threading.Lock:
    key = (company_id, document_type)
    with _registry_lock:
        if key not in _sqlite_locks:
            _sqlite_locks[key] = threading.Lock()
        return _sqlite_locks[key]


def _is_sqlite(db: Session) -> bool:
    url = db.bind.url if db.bind else None
    if url is None:
        try:
            url = db.get_bind().url
        except Exception:
            return False
    return str(url).startswith("sqlite")


def allocate_next_sequence(
    db: Session,
    company_id: int,
    document_type: str,
    max_retries: int = 3
) -> int:
    """
    Atomically allocates the next sequence number for (company_id, document_type).

    PostgreSQL: Uses atomic UPDATE ... RETURNING on the DocumentSequence row.
    SQLite: Uses a Python threading.Lock (safe for unit tests, not for multi-process).

    Returns: The next integer sequence number (monotonically increasing per scope).
    Fails closed: Raises SequenceAllocationError on contention exhaustion or failure.
    Never falls back to un-locked table max ID queries.
    """
    lock = _get_sqlite_lock(company_id, document_type) if _is_sqlite(db) else None
    if lock:
        lock.acquire()
    try:
        last_error = None
        for attempt in range(max_retries):
            try:
                with db.begin_nested():
                    # 1. Ensure seed row exists
                    seq_record = db.query(DocumentSequence).filter(
                        DocumentSequence.company_id == company_id,
                        DocumentSequence.document_type == document_type
                    ).first()

                    if not seq_record:
                        try:
                            with db.begin_nested():
                                new_seq = DocumentSequence(
                                    company_id=company_id,
                                    document_type=document_type,
                                    current_sequence=0
                                )
                                db.add(new_seq)
                                db.flush()
                        except IntegrityError:
                            pass  # Concurrently created by racing worker

                    # 2. Atomic UPDATE with RETURNING
                    stmt = (
                        update(DocumentSequence)
                        .where(
                            DocumentSequence.company_id == company_id,
                            DocumentSequence.document_type == document_type
                        )
                        .values(current_sequence=DocumentSequence.current_sequence + 1)
                        .returning(DocumentSequence.current_sequence)
                    )
                    result = db.execute(stmt).scalar()

                    if result is None:
                        # Fallback for concurrent transaction race: explicit row lock
                        seq_record = db.query(DocumentSequence).filter(
                            DocumentSequence.company_id == company_id,
                            DocumentSequence.document_type == document_type
                        ).with_for_update().first()
                        if seq_record:
                            seq_record.current_sequence += 1
                            db.flush()
                            return seq_record.current_sequence
                        raise SequenceAllocationError(
                            detail=f"Document sequence record for '{document_type}' not found after creation.",
                            document_type=document_type,
                            company_id=company_id
                        )

                    db.flush()
                    return result

            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1 and is_transient_retryable_sequence_error(exc):
                    time.sleep(0.01 * (2 ** attempt))
                    continue
                # Non-transient error or exhausted retries: break immediately
                break

        sanitized = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", str(last_error))
        logger.error(
            "Failed to allocate document sequence for company %s, type %s: %s",
            company_id, document_type, sanitized
        )
        raise SequenceAllocationError(
            detail=f"Failed to allocate document sequence for '{document_type}': {sanitized}",
            status_code=503,
            document_type=document_type,
            company_id=company_id,
            original_error=last_error
        ) from last_error
    finally:
        if lock:
            lock.release()


def generate_document_number(
    db: Session,
    company_id: int,
    document_type: str,
    prefix: str = None
) -> str:
    """
    Generates a formatted, collision-resistant document number.

    Format: {PREFIX}-{YYYY}-{00001}
    Example: SO-2026-00001, PROD-2026-00042, ADJ-2026-00007

    The sequence counter is scoped per (company_id, document_type),
    ensuring Company A and Company B have independent counters, and
    SALES_ORDER and PRODUCTION are also independent.
    """
    year_str = datetime.now().strftime("%Y")
    seq_num = allocate_next_sequence(db, company_id, document_type)
    formatted_seq = f"{seq_num:05d}"

    if prefix:
        return f"{prefix}-{year_str}-{formatted_seq}"
    else:
        return f"{year_str}-{formatted_seq}"
