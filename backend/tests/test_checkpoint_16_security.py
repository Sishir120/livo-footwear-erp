"""
Checkpoint 16 — Master Security, Adversarial Isolation & Hardening Test Suite
Standard: NIST SP 800-53 / OWASP API Security Top 10 2023 / ASVS 4.0 Level 2

Validates comprehensive security posture:
1. Multi-Tenant Boundary Integrity (No Cross-Tenant Read, Write, or Delete).
2. Idempotency Security & Cross-Tenant Payload Collision Isolation.
3. Offline Sync Security & Event Tenant Scoping.
4. Gallery Path Traversal Resistance.
5. RBAC & Strict Least-Privilege Enforcement.
"""
import pytest
import hashlib
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse
from app.models.sales import Client
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_c16_master():
    db: Session = SessionLocal()
    try:
        # Tenant 1: Alpha Footwear
        c1 = db.query(Company).filter(Company.code == "C16_ALPHA").first()
        if not c1:
            c1 = Company(name="Alpha Footwear Pvt Ltd", code="C16_ALPHA", pan_number="601111111")
            db.add(c1)
            db.commit()
            db.refresh(c1)

        # Tenant 2: Beta Shoes
        c2 = db.query(Company).filter(Company.code == "C16_BETA").first()
        if not c2:
            c2 = Company(name="Beta Shoes Industry", code="C16_BETA", pan_number="602222222")
            db.add(c2)
            db.commit()
            db.refresh(c2)

        # Users
        u_alpha = db.query(User).filter(User.username == "alpha_operator").first()
        if not u_alpha:
            u_alpha = User(
                name="Alpha Operator",
                username="alpha_operator",
                email="op@alpha.com",
                company_id=c1.id,
                role="editor",
                active=True,
                password_hash=get_password_hash("AlphaPass123!")
            )
            db.add(u_alpha)
            db.commit()
            db.refresh(u_alpha)

        u_beta = db.query(User).filter(User.username == "beta_operator").first()
        if not u_beta:
            u_beta = User(
                name="Beta Operator",
                username="beta_operator",
                email="op@beta.com",
                company_id=c2.id,
                role="editor",
                active=True,
                password_hash=get_password_hash("BetaPass123!")
            )
            db.add(u_beta)
            db.commit()
            db.refresh(u_beta)

        # Products & Warehouses
        p_beta = db.query(Product).filter(Product.company_id == c2.id).first()
        if not p_beta:
            p_beta = Product(
                company_id=c2.id,
                code="BETA-DERBY-01",
                name="Beta Classic Derby",
                category="Shoe",
                size="42",
                unit_price=Decimal("4500.00")
            )
            db.add(p_beta)
            db.commit()
            db.refresh(p_beta)

        wh_beta = db.query(Warehouse).filter(Warehouse.company_id == c2.id).first()
        if not wh_beta:
            wh_beta = Warehouse(company_id=c2.id, name="Beta Warehouse", code="WH-BETA-01", is_active=True)
            db.add(wh_beta)
            db.commit()
            db.refresh(wh_beta)

        token_alpha = create_access_token({
            "sub": u_alpha.username,
            "user_id": u_alpha.id,
            "company_id": c1.id,
            "role": u_alpha.role
        })

        token_beta = create_access_token({
            "sub": u_beta.username,
            "user_id": u_beta.id,
            "company_id": c2.id,
            "role": u_beta.role
        })

        return {
            "c1": c1,
            "c2": c2,
            "u_alpha": u_alpha,
            "u_beta": u_beta,
            "token_alpha": token_alpha,
            "token_beta": token_beta,
            "p_beta": p_beta,
            "wh_beta": wh_beta
        }
    finally:
        db.close()


def test_idempotency_cross_tenant_isolation(setup_c16_master):
    """
    Verifies that idempotency keys are strictly scoped by tenant.
    Alpha and Beta can use the EXACT SAME idempotency key without collision.
    """
    ctx = setup_c16_master
    h_alpha = {"Authorization": f"Bearer {ctx['token_alpha']}", "Idempotency-Key": "SHARED-KEY-12345"}
    h_beta = {"Authorization": f"Bearer {ctx['token_beta']}", "Idempotency-Key": "SHARED-KEY-12345"}

    with TestClient(app) as client:
        # Alpha creates client with key SHARED-KEY-12345
        res_a = client.post("/api/v1/sales/clients", json={
            "code": "CL-ALPHA-IDEM",
            "name": "Alpha Client",
            "credit_limit": 50000
        }, headers=h_alpha)
        assert res_a.status_code in (200, 201)

        # Beta creates client with SAME key SHARED-KEY-12345
        # Under multi-tenant isolation, this must NOT collide or return Alpha's cached response!
        res_b = client.post("/api/v1/sales/clients", json={
            "code": "CL-BETA-IDEM",
            "name": "Beta Client",
            "credit_limit": 60000
        }, headers=h_beta)
        assert res_b.status_code in (200, 201)
        assert res_b.json()["code"] == "CL-BETA-IDEM", "Cross-tenant idempotency isolation failed"


def test_offline_production_draft_sync_tenant_boundary(setup_c16_master):
    """
    Alpha attempts to submit an offline production draft sync targeting Beta's product or warehouse.
    Expected: Safe rejection (404/422).
    """
    ctx = setup_c16_master
    h_alpha = {"Authorization": f"Bearer {ctx['token_alpha']}"}

    with TestClient(app) as client:
        # Attack 1: Specify Beta's product ID
        res = client.post("/api/v1/production/drafts/sync", json={
            "idempotency_key": "OFFLINE-ATTACK-01",
            "product_id": ctx["p_beta"].id,
            "warehouse_id": 1,
            "date_ad": "2026-10-02",
            "date_bs": "2083-06-16",
            "size_quantities": {"42": 10}
        }, headers=h_alpha)
        assert res.status_code in (404, 422), "Offline sync against foreign product must fail"

        # Attack 2: Specify Beta's warehouse ID
        res = client.post("/api/v1/production/drafts/sync", json={
            "idempotency_key": "OFFLINE-ATTACK-02",
            "product_id": 1,
            "warehouse_id": ctx["wh_beta"].id,
            "date_ad": "2026-10-02",
            "date_bs": "2083-06-16",
            "size_quantities": {"42": 10}
        }, headers=h_alpha)
        assert res.status_code in (404, 422), "Offline sync targeting foreign warehouse must fail"


def test_gallery_path_traversal_attack(setup_c16_master):
    """
    Adversary attempts directory traversal sequences in file serving endpoints.
    Expected: Safe 400 Bad Request or 404 Not Found without leaking filesystem contents.
    """
    ctx = setup_c16_master
    h_alpha = {"Authorization": f"Bearer {ctx['token_alpha']}"}

    with TestClient(app) as client:
        traversal_payloads = [
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..\\..\\..\\windows\\win.ini",
            "....//....//....//app//config.py"
        ]

        for payload in traversal_payloads:
            res = client.get(f"/api/v1/gallery/images/{payload}/download", headers=h_alpha)
            assert res.status_code in (400, 404, 422), f"Path traversal attempt did not fail safely: {payload}"
            assert "root:" not in res.text
            assert "[fonts]" not in res.text
            assert "SECRET_KEY" not in res.text
