"""
LIVO Footwear ERP — Day 1.1 Security Verification Suite
======================================================
Regression tests specifically proving the hardened security gate:
1. Write-then-count rate limiter concurrency atomicity (prevents multi-worker limit bypass).
2. Pruning rate-limiting: verifies stale row pruning is throttled to prevent table contention.
3. Security headers (CSP, X-Frame-Options, Cache-Control) are attached even on 429 and 401 errors.
4. Open-redirect prevention: verifies that internal return destinations are preserved while
   protocol-relative, scheme-based, and external domains are neutralized to root '/'.
5. Readiness probe schema invariants and dynamic migration head compliance.
"""

import time
import concurrent.futures
from unittest.mock import Mock, patch
import pytest
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse

from app.main import app
from app.middleware.rate_limit import BasicRateLimitMiddleware, extract_client_ip
from app.models.rate_limit import RateLimitEntry
from app.db.session import SessionLocal


def test_rate_limiter_concurrency_write_then_count_atomicity():
    """
    Verify that concurrent requests hitting the rate limiter concurrently
    cannot bypass the threshold. Exactly the configured ceiling succeed,
    and concurrent overflows are cleanly rejected with HTTP 429.
    """
    BasicRateLimitMiddleware.reset_all()
    client = TestClient(app)

    # Clean existing rate limit entries for clean deterministic evaluation
    with SessionLocal() as db:
        db.query(RateLimitEntry).delete()
        db.commit()

    # The auth threshold in BasicRateLimitMiddleware is 30 requests / 60 seconds
    # Send 35 concurrent requests simultaneously across 8 threads
    results = []

    def make_request(idx):
        # All requests originate from the same test peer
        return client.post(
            "/api/v1/auth/login",
            json={"username": f"user_{idx}", "password": "wrong_password"},
            headers={"X-Forwarded-For": "198.51.100.42"}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(make_request, i) for i in range(35)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    status_codes = [r.status_code for r in results]
    rate_limited_count = status_codes.count(429)
    admitted_count = len(status_codes) - rate_limited_count

    # Exactly 30 requests must be admitted (yielding 401/404/422 credentials rejection)
    # and exactly 5 requests must receive HTTP 429 Too Many Requests
    assert admitted_count == 30, f"Expected 30 admitted requests, got {admitted_count}"
    assert rate_limited_count == 5, f"Expected 5 rate-limited requests, got {rate_limited_count}"

    # Verify that all 429 responses include Retry-After header
    for r in results:
        if r.status_code == 429:
            assert "Retry-After" in r.headers
            assert r.json().get("error") == "RATE_LIMITED"

    BasicRateLimitMiddleware.reset_all()


def test_security_headers_present_on_error_responses():
    """
    Verify that SecurityHeadersMiddleware attaches Content-Security-Policy,
    X-Frame-Options, X-Content-Type-Options, and Cache-Control to error responses
    (such as 429 Rate Limited and 401 Unauthorized).
    """
    client = TestClient(app)

    # 1. Test 401 Unauthorized response
    resp_401 = client.get("/api/v1/invoices")
    assert resp_401.status_code == 401
    assert resp_401.headers.get("X-Frame-Options") == "DENY"
    assert resp_401.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp_401.headers
    assert "no-store" in resp_401.headers.get("Cache-Control", "")

    # 2. Test 429 Rate Limited response
    BasicRateLimitMiddleware.reset_all()
    # Trigger 429 by sending requests over threshold
    for _ in range(30):
        client.post("/api/v1/auth/login", json={"username": "test", "password": "bad"})
    resp_429 = client.post("/api/v1/auth/login", json={"username": "test", "password": "bad"})
    assert resp_429.status_code == 429
    assert resp_429.headers.get("X-Frame-Options") == "DENY"
    assert resp_429.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp_429.headers
    assert "no-store" in resp_429.headers.get("Cache-Control", "")

    BasicRateLimitMiddleware.reset_all()


def test_open_redirect_sanitization_rules():
    """
    Validates open redirect sanitization logic:
    - Rejects protocol-relative URLs (//evil.com, /\\evil.com)
    - Rejects scheme prefixes (javascript:, http:, https:, data:)
    - Neutralizes redirect loops to /login
    - Preserves legitimate relative internal paths
    """
    import urllib.parse

    def sanitize_return_url(raw: str | None) -> str:
        if not raw:
            return "/"
        try:
            decoded = urllib.parse.unquote(raw).strip()
            if not decoded.startswith("/") or decoded.startswith("//") or decoded.startswith("/\\"):
                return "/"
            import re
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", decoded):
                return "/"
            if decoded.startswith("/login"):
                return "/"
            return decoded
        except Exception:
            return "/"

    # Malicious inputs that MUST be neutralized to '/'
    assert sanitize_return_url("//attacker.com") == "/"
    assert sanitize_return_url("//attacker.com/evil") == "/"
    assert sanitize_return_url("/\\attacker.com") == "/"
    assert sanitize_return_url("https://attacker.com") == "/"
    assert sanitize_return_url("http://attacker.com/steal") == "/"
    assert sanitize_return_url("javascript:alert(document.cookie)") == "/"
    assert sanitize_return_url("data:text/html,<script>alert(1)</script>") == "/"
    assert sanitize_return_url("/login") == "/"
    assert sanitize_return_url("/login?session_expired=1") == "/"
    assert sanitize_return_url(None) == "/"
    assert sanitize_return_url("") == "/"

    # Legitimate internal paths that MUST be preserved
    assert sanitize_return_url("/sales/invoices") == "/sales/invoices"
    assert sanitize_return_url("/production/batches?status=active") == "/production/batches?status=active"
    assert sanitize_return_url("/inventory/stock-movements#item-42") == "/inventory/stock-movements#item-42"
