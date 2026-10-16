import time
import ipaddress
import logging
import threading
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
    Hybrid distributed rate limiter for public auth endpoints (SEC-03 hardened / H-01).
    
    Architecture:
    1. Primary Store: Shared PostgreSQL/database table `rate_limit_entries` for atomic,
       cross-worker and cross-instance rate tracking under multi-worker Uvicorn deployments.
    2. Fail-Open Resilient Store: If database connection fails or times out, seamlessly falls back
       to in-process sliding window memory store with metrics tracking to avoid locking out users.
    3. Identity Scoping: Scoped by client IP derived from right-to-left trusted proxy traversal.
    """
    _instances = []
    _table_initialized = False
    _last_prune_time = 0.0
    _memory_lock = threading.Lock()

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        BasicRateLimitMiddleware._instances.append(self)
        self._ensure_table_exists()

    @classmethod
    def _ensure_table_exists(cls):
        if not cls._table_initialized:
            try:
                from app.db.session import engine
                from app.models.rate_limit import RateLimitEntry
                RateLimitEntry.__table__.create(engine, checkfirst=True)
                cls._table_initialized = True
            except Exception as e:
                logger.warning("Could not auto-verify rate_limit_entries table: %s", e)

    @classmethod
    def reset_all(cls):
        with cls._memory_lock:
            for inst in cls._instances:
                inst.requests.clear()
        try:
            from app.db.session import SessionLocal
            from app.models.rate_limit import RateLimitEntry
            db = SessionLocal()
            db.query(RateLimitEntry).delete()
            db.commit()
            db.close()
        except Exception:
            pass

    def _check_database_rate_limit(self, key: str, endpoint: str, now: float, cutoff: float) -> Optional[bool]:
        """
        Queries and updates shared database rate limit log.
        Uses write-then-count pattern to guarantee atomic enforcement across concurrent workers:
        1. Insert attempt into rate_limit_entries with current timestamp.
        2. Query count of attempts within (now - window_seconds).
        3. If count > max_requests, return True (rate limited).
        4. Prunes stale logs on a time-throttled interval (at most once every 5 minutes).
        Returns True if rate limited, False if allowed, or None on database failure.
        """
        for attempt in range(3):
            db = None
            try:
                from app.db.session import SessionLocal
                from app.models.rate_limit import RateLimitEntry
                db = SessionLocal()

                # 1. Record attempt first to close the check-then-act race window across workers
                db.add(RateLimitEntry(key=key, endpoint=endpoint, timestamp=now))
                db.commit()

                # 2. Count attempts in the active sliding window (including the one just recorded)
                count = db.query(RateLimitEntry).filter(
                    RateLimitEntry.key == key,
                    RateLimitEntry.endpoint == endpoint,
                    RateLimitEntry.timestamp > cutoff
                ).count()

                # 3. Throttled background pruning: purge entries older than 5 windows at most once every 5 minutes
                if now - BasicRateLimitMiddleware._last_prune_time > 300.0:
                    BasicRateLimitMiddleware._last_prune_time = now
                    purge_cutoff = now - (self.window_seconds * 5)
                    try:
                        db.query(RateLimitEntry).filter(RateLimitEntry.timestamp < purge_cutoff).delete()
                        db.commit()
                    except Exception as prune_err:
                        logger.debug("Non-critical rate limit prune skipped: %s", prune_err)

                if count > self.max_requests:
                    return True

                return False
            except Exception as e:
                if db:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                if attempt < 2 and "locked" in str(e).lower():
                    time.sleep(0.05 * (attempt + 1))
                    continue
                logger.warning("Shared rate limit database check failed (%s); falling back to in-memory sliding window.", e)
                return None
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass

    async def dispatch(self, request: Request, call_next):
        # Rate limit authentication/login endpoints
        if request.url.path.endswith("/auth/login"):
            client_ip = extract_client_ip(request)
            key = f"ip:{client_ip}"
            endpoint = "auth_login"
            now = time.time()
            cutoff = now - self.window_seconds

            is_limited = self._check_database_rate_limit(key, endpoint, now, cutoff)

            # If DB failed (returned None), fall back to in-memory sliding window
            if is_limited is None:
                with BasicRateLimitMiddleware._memory_lock:
                    self.requests[client_ip] = [
                        t for t in self.requests[client_ip] if now - t < self.window_seconds
                    ]
                    self.requests[client_ip].append(now)
                    if len(self.requests[client_ip]) > self.max_requests:
                        is_limited = True
                    else:
                        is_limited = False


            if is_limited:
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

        return await call_next(request)


