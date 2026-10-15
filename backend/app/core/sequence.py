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

import threading
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.sequence import DocumentSequence

# ---------------------------------------------------------------------------
# Python-level mutex registry for SQLite environments (test only)
# On PostgreSQL, DB-level SELECT FOR UPDATE provides the serialization.
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


def allocate_next_sequence(db: Session, company_id: int, document_type: str) -> int:
    """
    Atomically allocates the next sequence number for (company_id, document_type).

    PostgreSQL: Uses SELECT ... FOR UPDATE on the DocumentSequence row.
    SQLite: Uses a Python threading.Lock (safe for unit tests, not for multi-process).

    Returns: The next integer sequence number (always monotonically increasing per scope).
    """
    lock = _get_sqlite_lock(company_id, document_type) if _is_sqlite(db) else None
    if lock:
        lock.acquire()
    try:
        # First ensure the row exists
        seq_record = db.query(DocumentSequence).filter(
            DocumentSequence.company_id == company_id,
            DocumentSequence.document_type == document_type
        ).first()

        if not seq_record:
            # Try to create if missing
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
                pass  # Someone else created it, we can safely proceed to atomic update

        # Atomic UPDATE with RETURNING
        from sqlalchemy import update
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
            # Fallback for concurrent transaction race
            seq_record = db.query(DocumentSequence).filter(
                DocumentSequence.company_id == company_id,
                DocumentSequence.document_type == document_type
            ).with_for_update().first()
            if seq_record:
                seq_record.current_sequence += 1
                db.flush()
                return seq_record.current_sequence
            raise RuntimeError(f"Failed to allocate sequence for {document_type}")
            
        db.flush()
        return result
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
