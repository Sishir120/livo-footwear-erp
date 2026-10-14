import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.logging import logger
from app.middleware.correlation import get_correlation_id, get_request_id
from app.core.error_taxonomy import ErrorCode, classify_http_status

async def global_exception_handler(request: Request, exc: Exception):
    corr_id = get_correlation_id() or get_request_id() or "unknown"
    logger.error(
        f"Unhandled Exception [req:{corr_id}] on {request.method} {request.url.path}: {str(exc)}",
        exc_info=exc,
        extra={
            "request_id": corr_id,
            "correlation_id": corr_id,
            "route": request.url.path,
            "method": request.method,
            "status_code": 500,
            "error_code": ErrorCode.INTERNAL_ERROR,
            "event": "unhandled_server_exception"
        }
    )
    headers = {
        "X-Correlation-ID": corr_id,
        "X-Request-ID": corr_id
    }
    return JSONResponse(
        status_code=500,
        content={
            "error": ErrorCode.INTERNAL_ERROR,
            "message": "An unexpected error occurred. Please contact system administrator.",
            "detail": "An unexpected error occurred. Please contact system administrator.",
            "request_id": corr_id
        },
        headers=headers
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    corr_id = get_correlation_id() or get_request_id() or "unknown"
    detail_str = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    error_code = classify_http_status(exc.status_code, detail_str)

    logger.warning(
        f"HTTP Exception {exc.status_code} [{error_code}] [req:{corr_id}] on {request.method} {request.url.path}: {detail_str}",
        extra={
            "request_id": corr_id,
            "correlation_id": corr_id,
            "route": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": error_code,
            "event": "http_client_exception"
        }
    )
    headers = dict(exc.headers or {})
    headers["X-Correlation-ID"] = corr_id
    headers["X-Request-ID"] = corr_id
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": detail_str,
            "detail": exc.detail,
            "request_id": corr_id
        },
        headers=headers
    )

from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    corr_id = get_correlation_id() or get_request_id() or "unknown"
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({
            "error": ErrorCode.VALIDATION_ERROR,
            "message": "Request validation failed.",
            "detail": exc.errors(),
            "request_id": corr_id
        }),
        headers={
            "X-Correlation-ID": corr_id,
            "X-Request-ID": corr_id
        }
    )


