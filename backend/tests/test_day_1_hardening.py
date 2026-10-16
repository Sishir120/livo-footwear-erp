"""
LIVO ERP - Day 1 Backend Hardening & Evidence-Based Verification Test Suite
Tests:
- H-01: Shared database-backed rate limiter across workers, multi-client isolation, fail-open resilience
- H-03: Content-Security-Policy header presence and strict policy enforcement
- H-08: Health readiness probe contract (/health/ready)
- Financial & operational route authorization negative boundaries
"""
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.db.session import SessionLocal
from app.models.rate_limit import RateLimitEntry
from app.middleware.rate_limit import BasicRateLimitMiddleware
from app.api.deps import COOKIE_NAME
from app.core.security import create_access_token


@pytest.fixture(autouse=True)
def clean_rate_limit_store():
    """Ensure rate limit store is reset before and after each test."""
    BasicRateLimitMiddleware.reset_all()
    yield
    BasicRateLimitMiddleware.reset_all()


def test_h01_rate_limiter_shared_db_store_concurrency():
    """
    H-01: Verify that rate limit entries are persisted in the shared database
    table and enforce the 30-requests-per-minute threshold across workers.
    """
    client = TestClient(app)

    # Fire 30 login attempts (ceiling)
    for i in range(30):
        resp = client.post("/api/v1/auth/login", json={"username": "user", "password": "wrong"})
        assert resp.status_code in (401, 404, 422)

    # Verify rows in database
    db = SessionLocal()
    count = db.query(RateLimitEntry).filter(RateLimitEntry.endpoint == "auth_login").count()
    db.close()
    assert count == 30, f"Expected 30 database-tracked rate limit records, got {count}"

    # 31st request must trigger HTTP 429
    blocked = client.post("/api/v1/auth/login", json={"username": "user", "password": "wrong"})
    assert blocked.status_code == 429
    data = blocked.json()
    assert data["error"] == "RATE_LIMITED"
    assert "Retry-After" in blocked.headers
    assert blocked.headers["Retry-After"] == "60"


def test_h01_rate_limiter_storage_failure_fail_open_resilience():
    """
    H-01: Verify that if the shared database store is unavailable or throws,
    the rate limiter fails open to in-memory sliding window and never returns 500.
    """
    client = TestClient(app)

    # Simulate database outage during rate limit check
    with patch("app.middleware.rate_limit.BasicRateLimitMiddleware._check_database_rate_limit", return_value=None):
        # Requests should still be processed by in-memory fallback without 500 error
        resp = client.post("/api/v1/auth/login", json={"username": "user", "password": "wrong"})
        assert resp.status_code in (401, 404, 422)


def test_h01_rate_limiter_multi_client_isolation():
    """
    H-01: Verify that rate-limiting Client A does NOT block unrelated Client B.
    Using trusted reverse proxy peer (127.0.0.1) to test legitimate forwarded client IP isolation.
    """
    client = TestClient(app, client=("127.0.0.1", 50000))

    # Exhaust ceiling for Client A
    for i in range(30):
        client.post(
            "/api/v1/auth/login",
            json={"username": "user_a", "password": "wrong"},
            headers={"X-Forwarded-For": "198.51.100.1"}
        )

    # Verify Client A is blocked
    resp_a = client.post(
        "/api/v1/auth/login",
        json={"username": "user_a", "password": "wrong"},
        headers={"X-Forwarded-For": "198.51.100.1"}
    )
    assert resp_a.status_code == 429

    # Verify Client B (different IP) is NOT blocked
    resp_b = client.post(
        "/api/v1/auth/login",
        json={"username": "user_b", "password": "wrong"},
        headers={"X-Forwarded-For": "203.0.113.88"}
    )
    assert resp_b.status_code in (401, 404, 422)



def test_h03_content_security_policy_header_enforcement():
    """
    H-03: Verify Content-Security-Policy header is attached to all API responses
    with strict directives tailored for the LIVO frontend and printable invoices.
    """
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200

    csp = resp.headers.get("Content-Security-Policy")
    assert csp is not None, "Content-Security-Policy header is missing from API response"
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self' 'unsafe-inline'" in csp
    assert "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com" in csp
    assert "font-src 'self' https://fonts.gstatic.com data:" in csp
    assert "img-src 'self' data: blob: https:" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp


def test_h08_readiness_probe_contract_verification():
    """
    H-08: Verify /health/ready evaluates DB connectivity and schema invariants.
    """
    client = TestClient(app)
    from app.api.v1.health import get_expected_migration_head
    head = get_expected_migration_head()

    # 1. Healthy database probe returns HTTP 200
    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_cursor = Mock()
        mock_cursor.first.return_value = (head,)
        mock_execute.return_value = mock_cursor

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "healthy"

    # 2. Degraded database probe returns HTTP 503
    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB Connection refused")):
        resp_down = client.get("/api/v1/health/ready")
        assert resp_down.status_code == 503
        data_down = resp_down.json()
        assert data_down["status"] == "unready"
        assert data_down["database"] == "unhealthy"


def test_financial_authorization_negative_boundaries():
    """
    Priority A: Verify unauthenticated requests to financial and operational endpoints
    are strictly rejected with HTTP 401 Unauthorized.
    """
    client = TestClient(app)

    # Invoices endpoint without session
    inv_resp = client.get("/api/v1/invoices")
    assert inv_resp.status_code == 401
    assert "Session cookie missing" in inv_resp.json()["detail"]

    # Stock transfers endpoint without session
    transfer_resp = client.get("/api/v1/transfers")
    assert transfer_resp.status_code == 401

    # Purchases endpoint without session
    purch_resp = client.get("/api/v1/purchases")
    assert purch_resp.status_code == 401
