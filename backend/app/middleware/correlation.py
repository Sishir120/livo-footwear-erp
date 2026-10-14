import time
import uuid
import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables accessible across async request lifecycle
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
company_id_var: ContextVar[Optional[int]] = ContextVar("company_id", default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar("user_id", default=None)

logger = logging.getLogger("livo.access")
logger.setLevel(logging.INFO)

if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

SAFE_ID_REGEX = re.compile(r"^[A-Za-z0-9_\-\.]{1,64}$")

def sanitize_id(raw_id: Optional[str]) -> str:
    """Validates and sanitizes inbound request/correlation IDs to prevent log injection."""
    if not raw_id:
        return str(uuid.uuid4())
    cleaned = raw_id.strip()
    if SAFE_ID_REGEX.match(cleaned):
        return cleaned
    return str(uuid.uuid4())

def get_correlation_id() -> str:
    """Returns the current request's correlation ID."""
    return correlation_id_var.get("")

def get_request_id() -> str:
    """Returns the current request's request ID."""
    return request_id_var.get("")

def set_company_id(cid: int):
    company_id_var.set(cid)

def set_user_id(uid: int):
    user_id_var.set(uid)

def sanitize_sensitive_data(obj: Any) -> Any:
    """
    Privacy Boundary Rule: Strictly masks passwords, authorization tokens,
    PAN numbers, and customer names from application log streams.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("password", "token", "secret", "pan", "auth", "pan_number", "cookie")):
                sanitized[k] = "[REDACTED]"
            elif k_lower in ("name", "customer_name", "client_name"):
                sanitized[k] = "[REDACTED_PII]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_sensitive_data(item) for item in obj]
    return obj

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Observability & Correlation Tracing Middleware.
    Validates and sanitizes incoming X-Correlation-ID / X-Request-ID (max 64 safe chars).
    Attaches X-Correlation-ID and X-Request-ID to outgoing response headers.
    Emits structured JSON access logs with privacy boundary masking.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        raw_corr = request.headers.get("X-Correlation-ID")
        raw_req = request.headers.get("X-Request-ID")
        
        corr_id = sanitize_id(raw_corr)
        req_id = sanitize_id(raw_req) if raw_req else corr_id

        token_corr = correlation_id_var.set(corr_id)
        token_req = request_id_var.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "service": "livo-footwear-erp",
                "correlation_id": corr_id,
                "request_id": req_id,
                "company_id": company_id_var.get(None),
                "user_id": user_id_var.get(None),
                "route": request.url.path,
                "method": request.method,
                "status_code": 500,
                "duration_ms": latency_ms,
                "event": "http_request_exception",
                "error_code": "INTERNAL_ERROR",
                "error": str(exc),
            }
            logger.error(json.dumps(sanitize_sensitive_data(log_record)))
            correlation_id_var.reset(token_corr)
            request_id_var.reset(token_req)
            raise exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-Request-ID"] = req_id

        # Skip noisy polling endpoints like /health in structured log spam if 200
        is_health = request.url.path.startswith("/api/v1/health") and response.status_code == 200
        if not is_health:
            status_level = "INFO" if response.status_code < 400 else "WARNING" if response.status_code < 500 else "ERROR"
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": status_level,
                "service": "livo-footwear-erp",
                "correlation_id": corr_id,
                "request_id": req_id,
                "company_id": company_id_var.get(None),
                "user_id": user_id_var.get(None),
                "route": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": latency_ms,
                "event": "http_request_complete"
            }
            sanitized = sanitize_sensitive_data(log_record)
            if response.status_code >= 500:
                logger.error(json.dumps(sanitized))
            elif response.status_code >= 400:
                logger.warning(json.dumps(sanitized))
            else:
                logger.info(json.dumps(sanitized))

        correlation_id_var.reset(token_corr)
        request_id_var.reset(token_req)
        return response
