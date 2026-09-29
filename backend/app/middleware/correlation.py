import time
import uuid
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable accessible across async request lifecycle
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
company_id_var: ContextVar[Optional[int]] = ContextVar("company_id", default=None)

logger = logging.getLogger("livo.access")
logger.setLevel(logging.INFO)

# Ensure handler exists
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

def get_correlation_id() -> str:
    """Returns the current request's correlation ID."""
    return correlation_id_var.get("")

def get_request_id() -> str:
    return request_id_var.get("")

def set_company_id(cid: int):
    company_id_var.set(cid)

def sanitize_sensitive_data(obj: Any) -> Any:
    """
    Privacy Boundary Rule: Strictly masks or omits passwords, authorization tokens,
    PAN numbers, and customer names from application log streams.
    """
    if isinstance(obj, dict):
        sanitized = {}
        for k, v in obj.items():
            k_lower = k.lower()
            if any(s in k_lower for s in ("password", "token", "secret", "pan", "auth", "pan_number")):
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
    Inspects incoming X-Correlation-ID or X-Request-ID, or generates uuid4.
    Attaches X-Correlation-ID and X-Request-ID to outgoing response headers
    and emits structured JSON access logs with privacy boundary masking.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        if not corr_id:
            corr_id = str(uuid.uuid4())

        token_corr = correlation_id_var.set(corr_id)
        token_req = request_id_var.set(corr_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "correlation_id": corr_id,
                "request_id": corr_id,
                "company_id": company_id_var.get(None),
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": 500,
                "latency_ms": latency_ms,
                "error": str(exc),
            }
            logger.error(json.dumps(sanitize_sensitive_data(log_record)))
            correlation_id_var.reset(token_corr)
            request_id_var.reset(token_req)
            raise exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = corr_id
        response.headers["X-Request-ID"] = corr_id

        # Skip noisy polling endpoints like /health in structured log spam if 200
        if request.url.path != "/api/v1/health" or response.status_code >= 400:
            status_level = "INFO" if response.status_code < 400 else "WARN" if response.status_code < 500 else "ERROR"
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": status_level,
                "correlation_id": corr_id,
                "request_id": corr_id,
                "company_id": company_id_var.get(None),
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
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
