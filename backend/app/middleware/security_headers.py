from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Appends OWASP-recommended HTTP security headers to all outgoing API responses:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), camera=(), microphone=()
    - Strict-Transport-Security: HSTS header in production HTTPS environments
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        if not settings.LIVO_DEV_MODE:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
