import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.idempotency import IdempotencyRecord


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused with a different request payload or endpoint."""
    def __init__(self, key: str, message: str = "Idempotency key conflict: Request payload or endpoint does not match the original request."):
        self.key = key
        self.message = message
        super().__init__(self.message)


class IdempotencyProcessingError(Exception):
    """Raised when an operation with this idempotency key is already in flight."""
    def __init__(self, key: str, message: str = "Operation in progress for this idempotency key. Please retry shortly."):
        self.key = key
        self.message = message
        super().__init__(self.message)


def compute_request_hash(
    method: str,
    path: str,
    body: Optional[bytes | str] = None,
    query_string: Optional[str] = ""
) -> str:
    """
    Computes a deterministic, collision-resistant SHA-256 fingerprint for HTTP requests.
    Normalizes JSON payloads by parsing and serializing with sorted keys and minimal separators.
    For non-JSON or raw binary, computes SHA-256 over raw bytes.
    """
    normalized_body = ""
    if body:
        if isinstance(body, bytes):
            try:
                body_str = body.decode("utf-8")
            except UnicodeDecodeError:
                body_str = None
        else:
            body_str = str(body)

        if body_str:
            try:
                parsed = json.loads(body_str)
                # Canonical JSON: sorted keys, compact separators
                normalized_body = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
            except Exception:
                normalized_body = body_str.strip()
        elif isinstance(body, bytes):
            normalized_body = hashlib.sha256(body).hexdigest()

    canonical = f"{method.upper()}:{path}:{query_string or ''}:{normalized_body}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class IdempotencyService:
    """
    Core service coordinating database-backed idempotency records, leases,
    fingerprint verification, and state transitions.
    """

    @staticmethod
    def get_record(db: Session, company_id: int, idempotency_key: str) -> Optional[IdempotencyRecord]:
        return db.query(IdempotencyRecord).filter(
            IdempotencyRecord.company_id == company_id,
            IdempotencyRecord.idempotency_key == idempotency_key
        ).first()

    @staticmethod
    def initiate_or_retrieve(
        db: Session,
        company_id: int,
        user_id: Optional[int],
        idempotency_key: str,
        method: str,
        path: str,
        request_hash: str,
        lease_seconds: int = 60
    ) -> Tuple[IdempotencyRecord, bool]:
        """
        Atomically initiates or retrieves an idempotency record for (company_id, idempotency_key).
        Returns:
            (record, should_execute: bool)
            - should_execute is True if the caller must execute the underlying business logic.
            - should_execute is False if the operation is already COMPLETED and the cached response should be replayed.
        Raises:
            IdempotencyConflictError: If the key was already used with a different request fingerprint.
            IdempotencyProcessingError: If another concurrent request is actively executing under a valid lease.
        """
        now = datetime.now(timezone.utc)
        record = IdempotencyService.get_record(db, company_id, idempotency_key)

        if record:
            # 1. Scope and Tenant validation
            if record.company_id != company_id:
                raise IdempotencyConflictError(idempotency_key, "Idempotency key tenant mismatch.")

            # 2. Canonical payload & endpoint fingerprint verification
            if record.request_hash != request_hash:
                raise IdempotencyConflictError(
                    idempotency_key,
                    f"Idempotency key '{idempotency_key}' was previously used for a different request payload or endpoint."
                )

            # 3. Completed state: Replay cached result
            if record.status == "COMPLETED":
                return record, False

            # 4. Processing state: Check for stale lease recovery
            if record.status == "PROCESSING":
                is_stale = record.locked_until is None or ensure_utc(record.locked_until) < now
                if is_stale:
                    # Lease expired (e.g. server crash or worker timeout) -> Recover lease and retry
                    record.locked_until = now + timedelta(seconds=lease_seconds)
                    record.recovery_count += 1
                    record.updated_at = now
                    db.commit()
                    db.refresh(record)
                    return record, True
                else:
                    # Actively in flight
                    raise IdempotencyProcessingError(
                        idempotency_key,
                        f"An identical request with idempotency key '{idempotency_key}' is currently processing."
                    )

            # 5. Failed state: Previous attempt rolled back cleanly -> allow retry
            if record.status == "FAILED":
                record.status = "PROCESSING"
                record.locked_until = now + timedelta(seconds=lease_seconds)
                record.updated_at = now
                record.error_message = None
                db.commit()
                db.refresh(record)
                return record, True

        # 6. Record does not exist: Create new PROCESSING entry
        new_record = IdempotencyRecord(
            company_id=company_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_method=method.upper(),
            request_path=path,
            request_hash=request_hash,
            status="PROCESSING",
            locked_until=now + timedelta(seconds=lease_seconds),
            created_at=now,
            updated_at=now
        )
        db.add(new_record)
        try:
            db.commit()
            db.refresh(new_record)
            return new_record, True
        except IntegrityError:
            db.rollback()
            # Concurrency race: Another thread inserted simultaneously. Re-fetch and evaluate.
            return IdempotencyService.initiate_or_retrieve(
                db, company_id, user_id, idempotency_key, method, path, request_hash, lease_seconds
            )

    @staticmethod
    def record_success(
        db: Session,
        company_id: int,
        idempotency_key: str,
        status_code: int,
        response_body: str,
        response_headers: Optional[Dict[str, str]] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None
    ) -> None:
        """Marks the idempotency record as COMPLETED and persists the exact HTTP response for replay."""
        record = IdempotencyService.get_record(db, company_id, idempotency_key)
        if record:
            record.status = "COMPLETED"
            record.response_status_code = status_code
            record.response_body = response_body
            if response_headers:
                record.response_headers = json.dumps(response_headers)
            if resource_id:
                record.resource_id = str(resource_id)
            if resource_type:
                record.resource_type = resource_type
            record.completed_at = datetime.now(timezone.utc)
            record.updated_at = datetime.now(timezone.utc)
            record.locked_until = None
            db.commit()

    @staticmethod
    def record_failure(
        db: Session,
        company_id: int,
        idempotency_key: str,
        error_message: Optional[str] = None,
        status_code: int = 500
    ) -> None:
        """Marks the idempotency record as FAILED so that clients can safely retry."""
        record = IdempotencyService.get_record(db, company_id, idempotency_key)
        if record:
            record.status = "FAILED"
            record.response_status_code = status_code
            record.error_message = error_message
            record.updated_at = datetime.now(timezone.utc)
            record.locked_until = None
            db.commit()
