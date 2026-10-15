import time
import ipaddress
import logging
from collections import defaultdict
from typing import List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.config import settings

logger = logging.getLogger("livo_erp.rate_limit")

def is_ip_in_trusted_list(ip_str: str, trusted_list: List[str]) -> bool:
    """Checks if an IP string is present in or covered by trusted proxies/CIDRs."""
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
        for trusted in trusted_list:
            trusted = trusted.strip()
            if not trusted:
                continue
            if "/" in trusted:
                if ip in ipaddress.ip_network(trusted, strict=False):
                    return True
            else:
                if ip == ipaddress.ip_address(trusted):
                    return True
    except ValueError:
        return False
    return False

def extract_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """
    Extracts the client IP using X-Forwarded-For right-to-left traversal and trusted proxy verification (SEC-03 / OWASP reverse-proxy guidelines).
    - If the direct peer connection (request.client.host) is NOT in trusted_proxies,
      forwarded headers are considered untrusted/spoofed and strictly ignored.
    - If the direct peer IS a trusted proxy, X-Forwarded-For is traversed from right-to-left
      to locate the first untrusted upstream IP.
    """
    peer_ip = request.client.host if request.client and request.client.host else "127.0.0.1"
    
    if trusted_proxies is None:
        trusted_proxies = settings.TRUSTED_PROXIES

    if not is_ip_in_trusted_list(peer_ip, trusted_proxies):
        # Peer is NOT a trusted proxy: ignore all forwarded headers to prevent spoofing
        return peer_ip

    # Peer is a trusted proxy: inspect forwarded headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        for candidate in reversed(parts):
            try:
                ip_obj = ipaddress.ip_address(candidate)
                if not is_ip_in_trusted_list(str(ip_obj), trusted_proxies):
                    return str(ip_obj)
            except ValueError:
                # Malformed IP in header: skip safely
                continue

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        real_ip = real_ip.strip()
        try:
            ip_obj = ipaddress.ip_address(real_ip)
            if not is_ip_in_trusted_list(str(ip_obj), trusted_proxies):
                return str(ip_obj)
        except ValueError:
            pass

    return peer_ip

class BasicRateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory sliding window rate limiter for public auth endpoints (SEC-03 hardened).
    
    NOTE: In-memory sliding window operates per Python process/instance.
    For multi-instance / horizontally scaled production deployments, a distributed
    store (e.g. Redis / PostgreSQL advisory count) is a release prerequisite.
    """
    _instances = []

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        BasicRateLimitMiddleware._instances.append(self)

    @classmethod
    def reset_all(cls):
        for inst in cls._instances:
            inst.requests.clear()

    async def dispatch(self, request: Request, call_next):
        # Rate limit only authentication/login endpoints
        if request.url.path.endswith("/auth/login"):
            client_ip = extract_client_ip(request)
            now = time.time()
            
            # Clean up old timestamps
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < self.window_seconds
            ]
            
            if len(self.requests[client_ip]) >= self.max_requests:
                from app.core.metrics import metrics
                from app.core.error_taxonomy import ErrorCode
                from app.middleware.correlation import get_request_id, get_correlation_id
                
                metrics.inc("rate_limited_requests_total", labels={"route": "auth_login"})
                req_id = get_request_id() or get_correlation_id() or "unknown"
                msg = "Too many login attempts. Please wait a minute before retrying."
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": ErrorCode.RATE_LIMITED,
                        "message": msg,
                        "detail": msg,
                        "request_id": req_id
                    },
                    headers={
                        "Retry-After": str(self.window_seconds),
                        "X-Request-ID": req_id,
                        "X-Correlation-ID": req_id
                    }
                )
                
            self.requests[client_ip].append(now)

        return await call_next(request)

