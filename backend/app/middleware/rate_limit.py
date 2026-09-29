import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

class BasicRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory sliding window rate limiter for public auth endpoints.
    Sized appropriately for a 3-user internal tool per RULES.md §4.
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
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            elif request.headers.get("X-Real-IP"):
                client_ip = request.headers.get("X-Real-IP").strip()
            else:
                client_ip = request.client.host if request.client else "127.0.0.1"
            now = time.time()
            
            # Clean up old timestamps
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < self.window_seconds
            ]
            
            if len(self.requests[client_ip]) >= self.max_requests:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many login attempts. Please wait a minute before retrying."}
                )
                
            self.requests[client_ip].append(now)

        return await call_next(request)
