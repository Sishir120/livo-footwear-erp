import json
import logging
import asyncio
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import JSONResponse
from fastapi import status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.core.locks import get_idempotency_mutex, acquire_idempotency_advisory_lock
from app.core.idempotency import (
    IdempotencyService,
    compute_request_hash,
    IdempotencyConflictError,
    IdempotencyProcessingError
)

logger = logging.getLogger("livo.idempotency")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Production-grade HTTP Idempotency Middleware.
    Enforces exactly-once execution for mutating requests (POST, PUT, PATCH, DELETE)
    carrying an Idempotency-Key or X-Idempotency-Key header.
    
    Guarantees:
    1. Scoped multi-tenant uniqueness (company_id, idempotency_key).
    2. Tamper-evident fingerprinting (same key with different payload rejected with 409 Conflict).
    3. Distributed PostgreSQL advisory lock and in-process mutex serialization.
    4. Safe replay of cached responses without re-executing business logic.
    5. Automatic recovery of stale processing leases after server crash or timeout.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only inspect mutating HTTP methods
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        # Dedicated offline sync endpoints have their own protocol
        if request.url.path.endswith("/sync/draft"):
            return await call_next(request)

        # 1. Extract Idempotency Key from headers
        idempotency_key = (
            request.headers.get("Idempotency-Key") or
            request.headers.get("X-Idempotency-Key") or
            request.headers.get("idempotency-key")
        )

        # Read and cache body so both middleware and route handlers can inspect it
        body_bytes = await request.body()

        # If not in headers, inspect JSON body for an idempotency_key field (for non-sync routes)
        if not idempotency_key and body_bytes:
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    parsed_json = json.loads(body_bytes.decode("utf-8"))
                    if isinstance(parsed_json, dict) and "idempotency_key" in parsed_json:
                        idempotency_key = str(parsed_json["idempotency_key"]).strip()
                except Exception:
                    pass

        # If no idempotency key is associated with this mutation, pass through normally
        if not idempotency_key:
            return await call_next(request)

        # Validate key length and format
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 128:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": "Idempotency-Key must be non-empty and at most 128 characters.", "code": "INVALID_IDEMPOTENCY_KEY"}
            )

        # 2. Extract Tenant Context & Authentication
        token = request.cookies.get("livo_access_token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            # Let unauthenticated requests fall through to route dependencies (returns 401/403)
            return await call_next(request)

        payload = decode_access_token(token)
        if not payload:
            return await call_next(request)

        company_id = payload.get("company_id")
        user_id = payload.get("user_id")

        if not company_id:
            return await call_next(request)

        # 3. Compute canonical request hash
        request_hash = compute_request_hash(
            method=request.method,
            path=request.url.path,
            body=body_bytes,
            query_string=str(request.url.query)
        )

        # 4. Concurrency lock & initiate/retrieve record
        mutex = get_idempotency_mutex(company_id, idempotency_key)

        should_execute = False
        record = None

        with mutex:
            setup_db: Session = SessionLocal()
            try:
                acquire_idempotency_advisory_lock(setup_db, company_id, idempotency_key)

                record, should_execute = IdempotencyService.initiate_or_retrieve(
                    db=setup_db,
                    company_id=company_id,
                    user_id=user_id,
                    idempotency_key=idempotency_key,
                    method=request.method,
                    path=request.url.path,
                    request_hash=request_hash,
                    lease_seconds=60
                )
            except IdempotencyConflictError as exc:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"detail": exc.message, "code": "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH"}
                )
            except IdempotencyProcessingError:
                # Concurrent request in-flight: Will wait/poll below
                pass
            finally:
                setup_db.close()

        # If operation is actively processing by another thread/request, poll for completion
        if not should_execute and (record is None or record.status == "PROCESSING"):
            poll_start = datetime.now(timezone.utc)
            while (datetime.now(timezone.utc) - poll_start).total_seconds() < 5.0:
                await asyncio.sleep(0.05)
                poll_db: Session = SessionLocal()
                try:
                    record = IdempotencyService.get_record(poll_db, company_id, idempotency_key)
                    if record:
                        if record.request_hash != request_hash:
                            return JSONResponse(
                                status_code=status.HTTP_409_CONFLICT,
                                content={"detail": "Idempotency key payload mismatch.", "code": "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH"}
                            )
                        if record.status == "COMPLETED":
                            should_execute = False
                            break
                        if record.status == "FAILED":
                            # Prior attempt failed, try to acquire execution
                            with mutex:
                                record, should_execute = IdempotencyService.initiate_or_retrieve(
                                    db=poll_db,
                                    company_id=company_id,
                                    user_id=user_id,
                                    idempotency_key=idempotency_key,
                                    method=request.method,
                                    path=request.url.path,
                                    request_hash=request_hash,
                                    lease_seconds=60
                                )
                            break
                finally:
                    poll_db.close()

            if record and record.status == "PROCESSING":
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"detail": "Operation currently processing with this idempotency key. Please retry shortly.", "code": "IDEMPOTENCY_IN_PROGRESS"}
                )

        # Case A: Operation completed -> Replay cached response
        if not should_execute and record and record.status == "COMPLETED":
            logger.info(f"Replaying cached response for idempotency key '{idempotency_key}' (company {company_id})")
            headers = {}
            if record.response_headers:
                try:
                    headers = json.loads(record.response_headers)
                except Exception:
                    headers = {}

            headers["X-Idempotent-Replay"] = "true"
            headers["X-Idempotency-Key"] = idempotency_key

            return Response(
                content=record.response_body.encode("utf-8") if record.response_body else b"",
                status_code=record.response_status_code or 200,
                headers=headers,
                media_type="application/json"
            )

        # Case B: Execute the request without holding in-process mutex
        try:
            response = await call_next(request)
        except Exception as exc:
            # Execution raised unhandled exception -> Mark FAILED and re-raise
            with mutex:
                fail_db: Session = SessionLocal()
                try:
                    IdempotencyService.record_failure(
                        db=fail_db,
                        company_id=company_id,
                        idempotency_key=idempotency_key,
                        error_message=str(exc),
                        status_code=500
                    )
                except Exception:
                    pass
                finally:
                    fail_db.close()
            raise exc

        # Consume the response streaming body iterator to capture payload
        response_body_chunks = [chunk async for chunk in response.body_iterator]
        full_body_bytes = b"".join(response_body_chunks)
        body_str = full_body_bytes.decode("utf-8", errors="replace")

        with mutex:
            record_db: Session = SessionLocal()
            try:
                if response.status_code < 500:
                    # Successful or client validation error -> Mark COMPLETED
                    headers_dict = dict(response.headers)
                    filtered_headers = {
                        k: v for k, v in headers_dict.items()
                        if k.lower() not in ("content-length", "transfer-encoding")
                    }
                    IdempotencyService.record_success(
                        db=record_db,
                        company_id=company_id,
                        idempotency_key=idempotency_key,
                        status_code=response.status_code,
                        response_body=body_str,
                        response_headers=filtered_headers
                    )
                else:
                    # Server error 5xx -> Mark FAILED to allow retry
                    IdempotencyService.record_failure(
                        db=record_db,
                        company_id=company_id,
                        idempotency_key=idempotency_key,
                        error_message=f"Server returned HTTP {response.status_code}",
                        status_code=response.status_code
                    )
            except Exception as save_err:
                logger.error(f"Failed to persist idempotency completion for key {idempotency_key}: {save_err}")
            finally:
                record_db.close()

        # Reconstruct response for the caller
        out_headers = dict(response.headers)
        out_headers["X-Idempotency-Key"] = idempotency_key

        return Response(
            content=full_body_bytes,
            status_code=response.status_code,
            headers=out_headers,
            media_type=response.media_type
        )

