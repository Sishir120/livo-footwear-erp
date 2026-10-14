"""
LIVO Footwear ERP — Centralized Error Taxonomy
Deterministic classification of all client-facing and operational errors.
"""

class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    TENANT_ACCESS_ERROR = "TENANT_ACCESS_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def classify_http_status(status_code: int, detail: str = "") -> str:
    """Classifies an HTTP status code and detail into a standard taxonomy ErrorCode."""
    detail_lower = (detail or "").lower()
    if status_code == 400:
        if "idempotency" in detail_lower or "replayed" in detail_lower:
            return ErrorCode.IDEMPOTENCY_CONFLICT
        return ErrorCode.VALIDATION_ERROR
    elif status_code == 401:
        return ErrorCode.AUTHENTICATION_ERROR
    elif status_code == 403:
        if "tenant" in detail_lower or "company" in detail_lower:
            return ErrorCode.TENANT_ACCESS_ERROR
        return ErrorCode.AUTHORIZATION_ERROR
    elif status_code == 404:
        return ErrorCode.NOT_FOUND
    elif status_code == 409:
        if "idempotency" in detail_lower:
            return ErrorCode.IDEMPOTENCY_CONFLICT
        return ErrorCode.CONFLICT
    elif status_code == 422:
        if "insufficient" in detail_lower or "stock" in detail_lower:
            return ErrorCode.INSUFFICIENT_STOCK
        return ErrorCode.VALIDATION_ERROR
    elif status_code == 429:
        return ErrorCode.RATE_LIMITED
    elif status_code == 503:
        if "timeout" in detail_lower:
            return ErrorCode.DATABASE_TIMEOUT
        return ErrorCode.DATABASE_ERROR
    elif status_code >= 500:
        return ErrorCode.INTERNAL_ERROR
    return ErrorCode.INTERNAL_ERROR
