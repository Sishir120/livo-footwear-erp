"""
Unit and Integration Tests for Operations Telemetry & Observability
Verifies GET /api/v1/ops/telemetry RBAC, metric accuracy, correlation IDs, and privacy masking.
"""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, StockMovement
from app.core.security import get_password_hash, create_access_token
from app.api.deps import COOKIE_NAME
from app.middleware.correlation import sanitize_sensitive_data

@pytest.fixture(scope="module")
def setup_ops_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "OPS_CO").first()
    if not comp:
        comp = Company(name="Ops Test Company", code="OPS_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    admin_user = db.query(User).filter(User.username == "ops_admin").first()
    if not admin_user:
        admin_user = User(
            company_id=comp.id,
            name="Ops Admin",
            username="ops_admin",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

    viewer_user = db.query(User).filter(User.username == "ops_viewer").first()
    if not viewer_user:
        viewer_user = User(
            company_id=comp.id,
            name="Ops Viewer",
            username="ops_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer_user)
        db.commit()
        db.refresh(viewer_user)

    admin_token = create_access_token(
        data={"user_id": admin_user.id, "company_id": comp.id, "role": "admin", "sub": admin_user.username}
    )
    viewer_token = create_access_token(
        data={"user_id": viewer_user.id, "company_id": comp.id, "role": "viewer", "sub": viewer_user.username}
    )

    db.close()
    return {
        "company_id": comp.id,
        "admin_token": admin_token,
        "viewer_token": viewer_token
    }

def test_ops_telemetry_rbac(setup_ops_env):
    """Assert unauthenticated returns 401, viewer returns 403, and admin returns 200."""
    with TestClient(app) as client:
        # Unauthenticated
        res = client.get("/api/v1/ops/telemetry")
        assert res.status_code == 401

        # Viewer role
        client.cookies.set(COOKIE_NAME, setup_ops_env["viewer_token"])
        res_viewer = client.get("/api/v1/ops/telemetry")
        assert res_viewer.status_code == 403

        # Admin role
        client.cookies.set(COOKIE_NAME, setup_ops_env["admin_token"])
        res_admin = client.get("/api/v1/ops/telemetry")
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert "db_status" in data
        assert data["db_status"]["status"] == "healthy"
        assert "latency_ms" in data["db_status"]
        assert "migration_revision" in data
        assert "unsynced_draft_age_seconds" in data
        assert "recent_422_blocks" in data
        assert "broken_core_runs_count" in data
        assert "sync_error_rate_24h" in data
        assert "timestamp" in data

def test_correlation_id_header_propagation(setup_ops_env):
    """Assert X-Correlation-ID is preserved if provided, or generated if omitted."""
    with TestClient(app, cookies={COOKIE_NAME: setup_ops_env["admin_token"]}) as client:
        custom_id = f"corr-{uuid.uuid4().hex[:8]}"
        res = client.get("/api/v1/ops/telemetry", headers={"X-Correlation-ID": custom_id})
        assert res.status_code == 200
        assert res.headers.get("X-Correlation-ID") == custom_id

        # Without header, should auto-generate
        res_auto = client.get("/api/v1/ops/telemetry")
        assert res_auto.status_code == 200
        auto_id = res_auto.headers.get("X-Correlation-ID")
        assert auto_id is not None
        assert len(auto_id) > 10

def test_privacy_boundary_sanitizer():
    """Assert sensitive fields like password, token, PAN, and customer names are redacted."""
    raw_payload = {
        "username": "super_clerk",
        "password": "SecretPassword123!",
        "access_token": "jwt-token-string",
        "pan_number": "987654321",
        "client_name": "Kathmandu Retail House",
        "customer_name": "Shrestha Brothers",
        "nested": {
            "token": "bearer-secret",
            "pan": "123456",
            "safe_field": 42
        }
    }
    sanitized = sanitize_sensitive_data(raw_payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["pan_number"] == "[REDACTED]"
    assert sanitized["client_name"] == "[REDACTED_PII]"
    assert sanitized["customer_name"] == "[REDACTED_PII]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["pan"] == "[REDACTED]"
    assert sanitized["nested"]["safe_field"] == 42
