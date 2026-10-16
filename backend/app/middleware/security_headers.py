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

        # Prevent browser and proxy caching of sensitive API responses (OWASP API Top 10)
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        if "Pragma" not in response.headers:
            response.headers["Pragma"] = "no-cache"

        # Content-Security-Policy (H-03):
        # Strict origin bounding while accommodating Next.js hydration, Google Fonts (Fira Code/Inter in globals.css),
        # data:/blob: assets for QR codes, and inline styles for printable invoice rendering.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob: https:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "script-src 'self' 'unsafe-inline'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        if not settings.LIVO_DEV_MODE:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

