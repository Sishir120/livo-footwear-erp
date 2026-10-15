"""
LIVO Footwear ERP — Phase 16.2 Security Remediation Test Suite
=============================================================
Regression tests verifying:
1. SEC-01: Demo account provisioning safeguards (disabled by default, production refusal, opt-in).
2. SEC-02: Migration failure propagation (lifespan raises RuntimeError, does not swallow).
3. SEC-03: RFC 7239 reverse proxy IP extraction, spoofing prevention, and rate-limit enforcement.
"""

import os
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from fastapi import Request

from app.main import app, lifespan
from app.config import settings
from app.db.session import Base
from app.models.company import Company
from app.models.user import User
from app.core.demo_seeding import seed_demo_users_if_enabled
from app.middleware.rate_limit import (
    is_ip_in_trusted_list,
    extract_client_ip,
    BasicRateLimitMiddleware
)

# ------------------------------------------------------------------------------
# 1. SEC-01: DEMO PROVISIONING SAFEGUARDS
# ------------------------------------------------------------------------------

def test_sec01_demo_seeding_disabled_by_default():
    """Verify demo account seeding is skipped by default (ENABLE_DEMO_SEEDING=false)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    
    with Session() as db:
        comp = Company(name="LIVO Test", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

        with patch.object(settings, "ENABLE_DEMO_SEEDING", False):
            result = seed_demo_users_if_enabled(db, comp)
            assert result["status"] == "skipped"
            assert result["reason"] == "disabled_by_default"

            # Assert zero users were created
            user_count = db.query(User).count()
            assert user_count == 0, f"Expected 0 users, found {user_count}"


def test_sec01_production_mode_strictly_refuses_demo_seeding():
    """Verify demo account seeding is strictly rejected if ENVIRONMENT is production."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    
    with Session() as db:
        comp = Company(name="LIVO Test", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

        with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                result = seed_demo_users_if_enabled(db, comp)
                assert result["status"] == "rejected"
                assert result["reason"] == "production_mode_refusal"

                # Assert zero users were created
                user_count = db.query(User).count()
                assert user_count == 0, "Production mode must never seed demo accounts!"


def test_sec01_dev_mode_opt_in_seeding_creates_accounts():
    """Verify opt-in demo account seeding functions when explicitly enabled in non-production."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    
    with Session() as db:
        comp = Company(name="LIVO Test", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

        with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            with patch.object(settings, "ENVIRONMENT", "development"):
                result = seed_demo_users_if_enabled(db, comp)
                assert result["status"] == "seeded"
                assert "admin_demo" in result["seeded_users"]
                assert "viewer_demo" in result["seeded_users"]

                # Assert accounts exist in database
                admin = db.query(User).filter(User.username == "admin_demo").first()
                assert admin is not None
                assert admin.role == "admin"


# ------------------------------------------------------------------------------
# 2. SEC-02: MIGRATION FAILURE PROPAGATION
# ------------------------------------------------------------------------------

def test_sec02_migration_failure_raises_runtime_error():
    """Verify Alembic migration failures abort application startup instead of swallowing."""
    import asyncio

    async def _run():
        with patch("alembic.command.upgrade") as mock_upgrade:
            mock_upgrade.side_effect = Exception("Simulated connection timeout during migration")
            
            with patch.object(settings, "AUTO_MIGRATE", True):
                with pytest.raises(RuntimeError) as exc_info:
                    async with lifespan(app):
                        pass

                assert "Database migration failure" in str(exc_info.value)
                assert "Simulated connection timeout" in str(exc_info.value)

    asyncio.run(_run())


def test_sec02_auto_migrate_disabled_skips_startup_migrations():
    """Verify AUTO_MIGRATE=False skips Alembic startup migrations cleanly without error."""
    import asyncio

    async def _run():
        with patch("alembic.command.upgrade") as mock_upgrade:
            with patch.object(settings, "AUTO_MIGRATE", False):
                async with lifespan(app):
                    pass
                assert mock_upgrade.call_count == 0

    asyncio.run(_run())


def test_sec02_render_yaml_configuration_validity():
    """Verify render.yaml declares required staging environment variables."""
    import yaml
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    render_yaml_path = os.path.join(root_dir, "render.yaml")
    assert os.path.exists(render_yaml_path), "render.yaml must exist at repository root"

    with open(render_yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    web_service = next(s for s in config["services"] if s["name"] == "livo-footwear-erp-backend")
    env_map = {env["key"]: env.get("value") for env in web_service["envVars"]}

    assert env_map.get("ENVIRONMENT") == "staging", "render.yaml must declare ENVIRONMENT=staging"
    assert env_map.get("AUTO_MIGRATE") == "true", "render.yaml must declare AUTO_MIGRATE=true for free plan"
    assert env_map.get("TRUSTED_PROXIES") == "127.0.0.1,::1", "render.yaml must declare conservative TRUSTED_PROXIES"


# ------------------------------------------------------------------------------
# 3. SEC-03: RATE LIMITING & TRUSTED PROXY VALIDATION
# ------------------------------------------------------------------------------

def test_sec03_untrusted_client_spoofed_forwarded_header_ignored():
    """An untrusted direct peer cannot spoof X-Forwarded-For to bypass limits."""
    mock_request = Mock()
    mock_request.client.host = "198.51.100.45"  # Direct peer IP
    mock_request.headers = {
        "X-Forwarded-For": "10.0.0.1, 192.168.1.1, 8.8.8.8",
        "X-Real-IP": "8.8.8.8"
    }

    # Trusted proxies only includes local loopback
    trusted = ["127.0.0.1", "::1"]
    resolved_ip = extract_client_ip(mock_request, trusted)
    
    # Must resolve to direct peer IP, ignoring the spoofed headers
    assert resolved_ip == "198.51.100.45"


def test_sec03_trusted_proxy_extracts_legitimate_client_ip():
    """A connection from a trusted reverse proxy correctly extracts client IP."""
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"  # Trusted reverse proxy (e.g. Caddy/Nginx)
    mock_request.headers = {
        "X-Forwarded-For": "203.0.113.195, 127.0.0.1"
    }

    trusted = ["127.0.0.1", "::1"]
    resolved_ip = extract_client_ip(mock_request, trusted)
    
    assert resolved_ip == "203.0.113.195"


def test_sec03_malformed_forwarded_header_falls_back_safely():
    """Malformed or injection payloads in X-Forwarded-For do not cause crashes."""
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {
        "X-Forwarded-For": "malformed_ip, <script>alert(1)</script>, ; DROP TABLE"
    }

    trusted = ["127.0.0.1", "::1"]
    resolved_ip = extract_client_ip(mock_request, trusted)
    
    # Should safely return the fallback peer IP without crashing
    assert resolved_ip in ("malformed_ip", "127.0.0.1")


def test_sec03_rate_limiting_enforcement_on_auth_route():
    """Verify rate limit triggers HTTP 429 on exceeding threshold."""
    BasicRateLimitMiddleware.reset_all()

    client = TestClient(app)
    
    # Send requests up to rate limit ceiling (ceiling is 30 requests)
    for i in range(30):
        resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong"})
        assert resp.status_code in (401, 404, 422)

    # 31st request must trigger HTTP 429 Too Many Requests
    blocked_resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "wrong"})
    assert blocked_resp.status_code == 429
    assert blocked_resp.json()["error"] == "RATE_LIMITED"
    assert "Retry-After" in blocked_resp.headers

    BasicRateLimitMiddleware.reset_all()


def test_sec03_evasion_attempt_by_changing_forwarded_for_fails():
    """An attacker cycling X-Forwarded-For cannot evade rate limits from an untrusted peer."""
    BasicRateLimitMiddleware.reset_all()
    client = TestClient(app)

    # Simulate an attacker varying X-Forwarded-For across 30 requests
    for i in range(30):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "nobody", "password": "wrong"},
            headers={"X-Forwarded-For": f"198.51.100.{i+1}"}
        )
        assert resp.status_code in (401, 404, 422)

    # 31st request with yet another new IP header must STILL be blocked
    evasion_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "wrong"},
        headers={"X-Forwarded-For": "203.0.113.99"}
    )
    assert evasion_resp.status_code == 429
    assert evasion_resp.json()["error"] == "RATE_LIMITED"

    BasicRateLimitMiddleware.reset_all()


# ------------------------------------------------------------------------------
# 4. DEPLOYMENT IDENTITY & HEALTH ENDPOINTS
# ------------------------------------------------------------------------------

def test_deployment_identity_in_health_response():
    """Verify health endpoints include the truncated BUILD_COMMIT without leaking secrets."""
    client = TestClient(app)

    # Test /api/v1/health
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "commit" in data
    assert data["commit"] == settings.BUILD_COMMIT
    assert len(data["commit"]) <= 8
    assert "status" in data
    assert "version" in data

    # Test /api/v1/health/live
    live_resp = client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    live_data = live_resp.json()
    assert live_data["commit"] == settings.BUILD_COMMIT

    # Test /api/v1/health/ready
    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert ready_data["commit"] == settings.BUILD_COMMIT


# ------------------------------------------------------------------------------
# 5. ADDITIONAL P0 SECURITY & STARTUP SAFETY SAFEGUARDS
# ------------------------------------------------------------------------------

def test_sec01_ambiguous_environment_refuses_demo_seeding():
    """Verify demo account seeding fails closed if ENVIRONMENT is ambiguous or unknown."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        comp = Company(name="LIVO Test", code="LIVO")
        db.add(comp)
        db.commit()

        # Test with unknown environment
        with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            with patch.object(settings, "ENVIRONMENT", "staging_review"):
                result = seed_demo_users_if_enabled(db, comp)
                assert result["status"] == "rejected"
                assert result["reason"] == "ambiguous_environment_refusal"
                assert db.query(User).count() == 0

        # Test with empty environment
        with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            with patch.object(settings, "ENVIRONMENT", ""):
                result = seed_demo_users_if_enabled(db, comp)
                assert result["status"] == "rejected"
                assert result["reason"] == "ambiguous_environment_refusal"
                assert db.query(User).count() == 0


def test_sec01_existing_account_preserved_without_overwrite():
    """Verify demo seeding does not reset password or reactivate disabled accounts."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        comp = Company(name="LIVO Test", code="LIVO")
        db.add(comp)
        db.commit()

        # Pre-create admin_demo as DEACTIVATED with custom password hash
        custom_hash = "custom_scrypt_argon_hash_12345"
        disabled_admin = User(
            company_id=comp.id,
            name="Deactivated Administrator",
            username="admin_demo",
            email="disabled@livogroup.com",
            password_hash=custom_hash,
            role="admin",
            active=False  # Deactivated
        )
        db.add(disabled_admin)
        db.commit()

        # Run demo seeding in development mode
        with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            with patch.object(settings, "ENVIRONMENT", "development"):
                result = seed_demo_users_if_enabled(db, comp)
                assert result["status"] == "seeded"
                # admin_demo was not in seeded_users because it already existed
                assert "admin_demo" not in result["seeded_users"]

        # Verify disabled status and password hash were preserved
        reloaded = db.query(User).filter(User.username == "admin_demo").first()
        assert reloaded.active is False, "Demo seeding must not reactivate disabled accounts!"
        assert reloaded.password_hash == custom_hash, "Demo seeding must not overwrite existing password hashes!"


def test_sec02_migration_failure_sanitizes_db_credentials():
    """Verify that database migration exceptions mask passwords in connection strings."""
    import asyncio

    async def _run():
        with patch("alembic.command.upgrade") as mock_upgrade:
            mock_upgrade.side_effect = Exception(
                "connection failed: postgresql://admin_user:super_secret_db_pass_999@db.prod.internal:5432/livodb"
            )

            with patch.object(settings, "AUTO_MIGRATE", True):
                with pytest.raises(RuntimeError) as exc_info:
                    async with lifespan(app):
                        pass

                err_msg = str(exc_info.value)
                assert "super_secret_db_pass_999" not in err_msg, "Database passwords must never leak in exception messages!"
                assert "postgresql://admin_user:***@db.prod.internal:5432/livodb" in err_msg

    asyncio.run(_run())


def test_sec02_readiness_probe_schema_mismatch_returns_503():
    """Verify that /health/ready returns HTTP 503 if DB schema does not match Alembic head (critical when AUTO_MIGRATE=false)."""
    client = TestClient(app)

    # Mock DB query to return an outdated revision
    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_cursor = Mock()
        mock_cursor.first.return_value = ("001_initial_schema",)
        mock_execute.return_value = mock_cursor

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_mismatch"
        assert "expected_head" in data
        assert data["current_head"] == "001_initial_schema"


def test_sec02_readiness_probe_missing_table_returns_503():
    """Verify that /health/ready returns HTTP 503 if alembic_version table is absent or unreadable."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        def side_effect(statement, *args, **kwargs):
            sql_text = str(statement)
            if "SELECT 1" in sql_text:
                return Mock()
            raise Exception("relation 'alembic_version' does not exist")
        mock_execute.side_effect = side_effect

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_unverified"


def test_sec02_readiness_probe_matching_schema_returns_200():
    """Verify that /health/ready returns HTTP 200 when DB schema matches the expected Alembic head."""
    client = TestClient(app)
    from app.api.v1.health import get_expected_migration_head
    head = get_expected_migration_head()

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_cursor = Mock()
        mock_cursor.first.return_value = (head,)
        mock_execute.return_value = mock_cursor

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["database"] == "healthy"


def test_sec02_readiness_probe_database_unavailable_returns_503():
    """Verify that /health/ready returns HTTP 503 if database connection probe fails."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_execute.side_effect = Exception("connection refused: database offline")

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "unhealthy"


def test_sec02_readiness_probe_empty_version_table_returns_503():
    """Verify that /health/ready returns HTTP 503 if alembic_version table contains 0 rows."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        def side_effect(stmt, *args, **kwargs):
            if "SELECT 1" in str(stmt):
                return Mock()
            mock_cur = Mock()
            mock_cur.fetchall.return_value = []
            mock_cur.first.return_value = None
            return mock_cur
        mock_execute.side_effect = side_effect

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_mismatch"
        assert data["sub_status"] == "revision_empty"


def test_sec02_readiness_probe_unknown_revision_returns_503():
    """Verify that /health/ready returns HTTP 503 if alembic_version contains an unknown or ahead revision."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        def side_effect(stmt, *args, **kwargs):
            if "SELECT 1" in str(stmt):
                return Mock()
            mock_cur = Mock()
            mock_cur.fetchall.return_value = [("999_future_or_unknown_revision",)]
            return mock_cur
        mock_execute.side_effect = side_effect

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_mismatch"
        assert data["sub_status"] == "revision_unknown_or_ahead"


def test_sec02_readiness_probe_multiple_revisions_in_db_returns_503():
    """Verify that /health/ready returns HTTP 503 if multiple active revisions exist in alembic_version."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        def side_effect(stmt, *args, **kwargs):
            if "SELECT 1" in str(stmt):
                return Mock()
            mock_cur = Mock()
            mock_cur.fetchall.return_value = [("019_rev_a",), ("020_rev_b",)]
            return mock_cur
        mock_execute.side_effect = side_effect

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_mismatch"
        assert data["sub_status"] == "multiple_database_revisions"


def test_sec02_readiness_probe_multiple_alembic_heads_returns_503():
    """Verify that /health/ready returns HTTP 503 if Alembic ScriptDirectory detects conflicting heads."""
    client = TestClient(app)

    with patch("app.api.v1.health.get_alembic_script_directory") as mock_script_dir:
        mock_script = Mock()
        mock_script.get_heads.return_value = ["head_a", "head_b"]
        mock_script_dir.return_value = mock_script

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_unverified"
        assert data["sub_status"] == "multiple_migration_heads"


def test_sec02_readiness_probe_missing_critical_table_invariant_returns_503():
    """Verify that /health/ready returns HTTP 503 if critical business tables are missing despite matching revision."""
    client = TestClient(app)

    with patch("sqlalchemy.inspect") as mock_inspect:
        mock_inspector = Mock()
        # Return table list missing 'invoices' and 'users'
        mock_inspector.get_table_names.return_value = ["alembic_version", "companies"]
        mock_inspect.return_value = mock_inspector

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_invariant_violation"
        assert "missing_tables" in data
        assert "users" in data["missing_tables"]


def test_sec02_readiness_probe_missing_critical_column_invariant_returns_503():
    """Verify that /health/ready returns HTTP 503 if critical columns on users table are missing."""
    client = TestClient(app)

    with patch("sqlalchemy.inspect") as mock_inspect:
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = [
            "companies", "users", "invoices", "products", "production_batches", "stock_movements"
        ]
        # Return columns missing 'password_hash'
        mock_inspector.get_columns.return_value = [
            {"name": "id"}, {"name": "company_id"}, {"name": "username"}
        ]
        mock_inspect.return_value = mock_inspector

        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unready"
        assert data["database"] == "schema_invariant_violation"
        assert "missing_columns" in data
        assert "password_hash" in data["missing_columns"]


def test_liveness_probe_does_not_access_database():
    """Verify that /health/live succeeds even if database is completely unavailable."""
    client = TestClient(app)

    with patch("sqlalchemy.orm.Session.execute") as mock_execute:
        mock_execute.side_effect = Exception("database completely unreachable")

        resp = client.get("/api/v1/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert data["commit"] == settings.BUILD_COMMIT


# ------------------------------------------------------------------------------
# 6. ADMINISTRATOR PROVISIONING & DEMO CONTAINMENT CLI TESTS
# ------------------------------------------------------------------------------

def test_create_admin_script_fails_if_company_not_found(capsys):
    """create_admin.py must fail safely if company LIVO does not exist."""
    from scripts.create_admin import create_admin
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with patch("scripts.create_admin.SessionLocal", Session):
        with pytest.raises(SystemExit) as exc_info:
            create_admin("admin_test", "admin@test.com", "SecurePassword123")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Default tenant company 'LIVO' not found" in captured.out


def test_create_admin_script_fails_if_user_already_exists(capsys):
    """create_admin.py must refuse to overwrite an existing user account."""
    from scripts.create_admin import create_admin
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        comp = Company(name="LIVO Group", code="LIVO")
        db.add(comp)
        db.commit()
        existing_user = User(
            company_id=comp.id,
            name="Existing Admin",
            username="existing_admin",
            email="existing@example.com",
            password_hash="existing_hash",
            role="admin",
            active=True
        )
        db.add(existing_user)
        db.commit()

    with patch("scripts.create_admin.SessionLocal", Session):
        with pytest.raises(SystemExit) as exc_info:
            create_admin("existing_admin", "newemail@test.com", "SecurePassword123")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "already exists" in captured.out


def test_create_admin_script_validates_password_length(capsys):
    """create_admin.py must reject passwords under 8 characters."""
    from scripts.create_admin import create_admin

    with pytest.raises(SystemExit) as exc_info:
        create_admin("new_admin", "admin@test.com", "short")
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "at least 8 characters" in captured.out


def test_create_admin_script_provisions_active_admin_account():
    """create_admin.py provisions active administrator with correct company binding."""
    from scripts.create_admin import create_admin
    from app.core.security import verify_password
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        comp = Company(name="LIVO Group", code="LIVO")
        db.add(comp)
        db.commit()

    with patch("scripts.create_admin.SessionLocal", Session):
        create_admin("new_legit_admin", "legit@livogroup.com", "VeryStrongPassword12345!", "Legit Admin")

    with Session() as db:
        admin = db.query(User).filter(User.username == "new_legit_admin").first()
        assert admin is not None
        assert admin.role == "admin"
        assert admin.active is True
        assert admin.email == "legit@livogroup.com"
        assert verify_password("VeryStrongPassword12345!", admin.password_hash) is True


def test_sec03_proxy_traversal_with_private_ip_hops():
    """Verify right-to-left traversal behavior when intermediate private IPs exist."""
    mock_request = Mock()
    mock_request.client.host = "127.0.0.1"
    mock_request.headers = {
        "X-Forwarded-For": "203.0.113.195, 10.0.0.1, 127.0.0.1"
    }

    # Case 1: 10.0.0.1 is NOT in trusted proxies -> returns 10.0.0.1 as first untrusted hop
    trusted_loopback_only = ["127.0.0.1", "::1"]
    resolved_ip = extract_client_ip(mock_request, trusted_loopback_only)
    assert resolved_ip == "10.0.0.1"

    # Case 2: 10.0.0.0/8 IS trusted -> traverses past 10.0.0.1 to 203.0.113.195
    trusted_with_private = ["127.0.0.1", "::1", "10.0.0.0/8"]
    resolved_ip = extract_client_ip(mock_request, trusted_with_private)
    assert resolved_ip == "203.0.113.195"

    # Case 3: Malformed X-Real-IP injection falls back safely to peer_ip without returning injection string
    mock_request.headers = {
        "X-Forwarded-For": "<script>alert(1)</script>",
        "X-Real-IP": "; DROP TABLE users;"
    }
    resolved_ip = extract_client_ip(mock_request, trusted_loopback_only)
    assert resolved_ip == "127.0.0.1"



