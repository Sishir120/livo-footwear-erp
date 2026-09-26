from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.logging import logger

async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=exc
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please contact system administrator or click Send Diagnostics.",
            "error_type": exc.__class__.__name__
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(
        f"HTTP Exception {exc.status_code} on {request.method} {request.url.path}: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )
