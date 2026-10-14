import os
import re
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime, timezone
from typing import Any, Dict

def redact_sensitive_data(val: Any) -> Any:
    """
    Recursively redacts passwords, tokens, API keys, secret credentials, PANs, and cookies.
    """
    if isinstance(val, dict):
        clean = {}
        for k, v in val.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in (
                "password", "token", "secret", "authorization", "auth",
                "cookie", "pan", "pan_number", "access_key", "secret_key"
            )):
                clean[k] = "[REDACTED]"
            elif k_lower in ("client_name", "customer_name"):
                clean[k] = "[REDACTED_PII]"
            else:
                clean[k] = redact_sensitive_data(v)
        return clean
    elif isinstance(val, list):
        return [redact_sensitive_data(item) for item in val]
    elif isinstance(val, str):
        # Redact JWTs or bearer tokens in arbitrary strings
        if "bearer " in val.lower() or "eyjhbgcioi" in val.lower():
            return re.sub(r'Bearer\s+[A-Za-z0-9\-\._~+/]+=*', 'Bearer [REDACTED]', val, flags=re.IGNORECASE)
        # Redact password patterns
        if "password=" in val.lower():
            return re.sub(r'password=[^\s&]+', 'password=[REDACTED]', val, flags=re.IGNORECASE)
        return val
    return val

class StructuredJSONFormatter(logging.Formatter):
    """
    Formats application and access logs as standardized production JSON.
    Guarantees standard fields:
    timestamp, level, service, environment, request_id, correlation_id,
    user_id, company_id, route, method, status_code, duration_ms, event, error_code.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Import context vars lazily to avoid circular imports
        try:
            from app.middleware.correlation import get_request_id, get_correlation_id, company_id_var
            req_id = get_request_id() or getattr(record, "request_id", None) or "none"
            corr_id = get_correlation_id() or getattr(record, "correlation_id", None) or "none"
            comp_id = company_id_var.get(None) if hasattr(company_id_var, "get") else None
        except Exception:
            req_id = getattr(record, "request_id", "none")
            corr_id = getattr(record, "correlation_id", "none")
            comp_id = getattr(record, "company_id", None)

        env = os.getenv("ENVIRONMENT", "production" if os.getenv("LIVO_DEV_MODE") == "false" else "development")

        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "livo-footwear-erp",
            "environment": env,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": req_id,
            "correlation_id": corr_id,
            "company_id": comp_id or getattr(record, "company_id", None),
            "user_id": getattr(record, "user_id", None),
            "route": getattr(record, "route", None),
            "method": getattr(record, "method", None),
            "status_code": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "error_code": getattr(record, "error_code", None),
        }

        # Clean None values from top-level fields for conciseness
        cleaned_payload = {k: v for k, v in log_payload.items() if v is not None}

        # Include sanitized message if distinct from event
        if record.getMessage() != log_payload.get("event"):
            cleaned_payload["message"] = record.getMessage()

        # Capture server-side exception trace if present
        if record.exc_info:
            cleaned_payload["exception"] = self.formatException(record.exc_info)

        # Redact any accidental credentials or tokens
        sanitized = redact_sensitive_data(cleaned_payload)
        return json.dumps(sanitized)

def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "livo_erp.log")

    logger = logging.getLogger("livo_erp")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = StructuredJSONFormatter()

    # Rotating file handler (10 MB max, 5 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()
