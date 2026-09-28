import time
import uuid
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable accessible across async request lifecycle
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
company_id_var: ContextVar[Optional[int]] = ContextVar("company_id", default=None)

logger = logging.getLogger("livo.access")
logger.setLevel(logging.INFO)

# Ensure handler exists
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

def get_request_id() -> str:
    return request_id_var.get("")

def set_company_id(cid: int):
    company_id_var.set(cid)

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Observability & Correlation Tracing Middleware.
    Inspects incoming X-Request-ID or generates req_<uuid4[:12]>.
    Attaches X-Request-ID to response and emits structured JSON access logs.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = f"req_{uuid.uuid4().hex[:12]}"

        token_req = request_id_var.set(req_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "request_id": req_id,
                "company_id": company_id_var.get(None),
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": 500,
                "latency_ms": latency_ms,
                "error": str(exc),
            }
            logger.error(json.dumps(log_record))
            request_id_var.reset(token_req)
            raise exc

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # Skip noisy polling endpoints like /health in structured log spam if 200
        if request.url.path != "/api/v1/health" or response.status_code >= 400:
            status_level = "INFO" if response.status_code < 400 else "WARN" if response.status_code < 500 else "ERROR"
            log_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": status_level,
                "request_id": req_id,
                "company_id": company_id_var.get(None),
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
            }
            if response.status_code >= 500:
                logger.error(json.dumps(log_record))
            elif response.status_code >= 400:
                logger.warning(json.dumps(log_record))
            else:
                logger.info(json.dumps(log_record))

        request_id_var.reset(token_req)
        return response
