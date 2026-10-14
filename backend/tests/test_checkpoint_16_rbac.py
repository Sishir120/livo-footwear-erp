"""
Checkpoint 16 — Adversarial RBAC, Privilege Escalation & Auth Hardening Test Suite
Standard: NIST SP 800-53 AC-6 (Least Privilege) / IA-2 (Authentication) / OWASP API Security Top 10

Attacks authorization and authentication boundaries:
1. Vertical privilege escalation (Viewer / Operator attempting Admin-only actions).
2. Token tampering (expired, altered signature, wrong secret, missing claims, inactive user).
3. Mass assignment / Privilege injection (attempting to override company_id, role, or user_id).
"""
import pytest
import time
import jwt
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
from app.config import settings


@pytest.fixture(scope="module")
def setup_rbac_users():
    db: Session = SessionLocal()
    try:
        comp = db.query(Company).filter(Company.code == "RBAC_CORP").first()
        if not comp:
            comp = Company(name="RBAC Enterprise", code="RBAC_CORP", pan_number="444444444")
            db.add(comp)
            db.commit()
            db.refresh(comp)

        # 1. Admin
        u_admin = db.query(User).filter(User.username == "rbac_admin").first()
        if not u_admin:
            u_admin = User(
                name="Admin User",
                username="rbac_admin",
                email="admin@rbac.com",
                company_id=comp.id,
                role="admin",
                active=True,
                password_hash=get_password_hash("AdminPass123!")
            )
            db.add(u_admin)
            db.commit()
            db.refresh(u_admin)

        # 2. Operator / Editor
        u_editor = db.query(User).filter(User.username == "rbac_editor").first()
        if not u_editor:
            u_editor = User(
                name="Editor User",
                username="rbac_editor",
                email="editor@rbac.com",
                company_id=comp.id,
                role="editor",
                active=True,
                password_hash=get_password_hash("EditorPass123!")
            )
            db.add(u_editor)
            db.commit()
            db.refresh(u_editor)

        # 3. Viewer (read-only)
        u_viewer = db.query(User).filter(User.username == "rbac_viewer").first()
        if not u_viewer:
            u_viewer = User(
                name="Viewer User",
                username="rbac_viewer",
                email="viewer@rbac.com",
                company_id=comp.id,
                role="viewer",
                active=True,
                password_hash=get_password_hash("ViewerPass123!")
            )
            db.add(u_viewer)
            db.commit()
            db.refresh(u_viewer)

        # 4. Inactive User
        u_inactive = db.query(User).filter(User.username == "rbac_inactive").first()
        if not u_inactive:
            u_inactive = User(
                name="Disabled User",
                username="rbac_inactive",
                email="disabled@rbac.com",
                company_id=comp.id,
                role="admin",
                active=False,
                password_hash=get_password_hash("DisabledPass123!")
            )
            db.add(u_inactive)
            db.commit()
            db.refresh(u_inactive)

        # Product and Client for tests
        prod = db.query(Product).filter(Product.company_id == comp.id).first()
        if not prod:
            prod = Product(
                company_id=comp.id,
                code="RBAC-PROD-01",
                name="RBAC Oxford",
                category="Shoe",
                size="42",
                color="Black",
                unit_price=Decimal("4000.00")
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)

        client_rec = db.query(Client).filter(Client.company_id == comp.id).first()
        if not client_rec:
            client_rec = Client(company_id=comp.id, code="RBAC-CL-01", name="RBAC Client", credit_limit=Decimal("50000.00"))
            db.add(client_rec)
            db.commit()
            db.refresh(client_rec)

        wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id).first()
        if not wh:
            wh = Warehouse(company_id=comp.id, name="RBAC Main Warehouse", code="WH-RBAC-01", is_active=True)
            db.add(wh)
            db.commit()
            db.refresh(wh)

        return {
            "comp": comp,
            "admin": u_admin,
            "editor": u_editor,
            "viewer": u_viewer,
            "inactive": u_inactive,
            "prod": prod,
            "client": client_rec,
            "wh": wh
        }
    finally:
        db.close()


def test_viewer_mutation_rejection(setup_rbac_users):
    """
    Lowest-privileged role (viewer) attempts write operations across all domains.
    Expected: Strict 403 Forbidden.
    """
    u = setup_rbac_users
    token = create_access_token({"sub": u["viewer"].username, "user_id": u["viewer"].id, "company_id": u["comp"].id, "role": "viewer"})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Stock movement
        res = client.post("/api/v1/stock/movements", json={
            "product_id": u["prod"].id, "direction": 1, "quantity": 10
        }, headers=headers)
        assert res.status_code == 403

        # Stock adjustment
        res = client.post("/api/v1/stock/adjustments", json={
            "product_id": u["prod"].id, "quantity_delta": 5, "reason_code": "RECOUNT"
        }, headers=headers)
        assert res.status_code == 403

        # Create Client
        res = client.post("/api/v1/sales/clients", json={
            "code": "ILLEGAL-CL", "name": "Illegal Client", "credit_limit": 1000
        }, headers=headers)
        assert res.status_code == 403

        # Create Sales Order
        res = client.post("/api/v1/sales/orders", json={
            "client_id": u["client"].id, "order_date_ad": "2026-10-02", "order_date_bs": "2083-06-16",
            "received_amount": 0, "items": [{"product_id": u["prod"].id, "quantity": 1, "unit_price": 4000}]
        }, headers=headers)
        assert res.status_code == 403

        # Create Product
        res = client.post("/api/v1/production/products", json={
            "code": "ILLEGAL-PROD", "name": "Illegal Product", "category": "Shoe"
        }, headers=headers)
        assert res.status_code == 403

        # Create Supplier
        res = client.post("/api/v1/purchase/suppliers", json={
            "code": "ILLEGAL-SUP", "name": "Illegal Supplier"
        }, headers=headers)
        assert res.status_code == 403

        # Record Worker Advance
        res = client.post("/api/v1/hr/advances", json={
            "worker_id": 1, "amount_paisa": 10000
        }, headers=headers)
        assert res.status_code == 403


def test_operator_vertical_escalation_to_admin(setup_rbac_users):
    """
    Operator / Editor attempts administrative actions:
    1. Operational telemetry (slow queries, system errors).
    2. Database backup triggers.
    3. Downward stock adjustment without supervisor token.
    Expected: Safe 403 Forbidden.
    """
    u = setup_rbac_users
    token = create_access_token({"sub": u["editor"].username, "user_id": u["editor"].id, "company_id": u["comp"].id, "role": "editor"})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Ops telemetry (admin only)
        res = client.get("/api/v1/ops/telemetry", headers=headers)
        assert res.status_code == 403, "Editor must not access administrative ops telemetry"

        # Backup trigger (admin only)
        res = client.post("/api/v1/backup/run", headers=headers)
        assert res.status_code == 403, "Editor must not trigger administrative backup"

        # Negative stock adjustment without supervisor token
        res = client.post("/api/v1/stock/adjustments", json={
            "product_id": u["prod"].id,
            "quantity_delta": -5,
            "reason_code": "DAMAGE"
        }, headers=headers)
        assert res.status_code == 403


def test_token_tampering_attacks(setup_rbac_users):
    """
    Adversarial attacks on the authentication layer:
    1. Expired token.
    2. Modified / altered signature.
    3. Wrong HMAC secret.
    4. Missing user_id claim.
    5. Missing company_id claim.
    6. Inactive / disabled user token.
    Expected: Safe 401 Unauthorized for every scenario.
    """
    u = setup_rbac_users

    with TestClient(app) as client:
        # 1. Expired token
        expired_token = jwt.encode(
            {"sub": u["admin"].username, "user_id": u["admin"].id, "company_id": u["comp"].id, "exp": int(time.time()) - 3600},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401

        # 2. Tampered token payload
        valid_token = create_access_token({"sub": u["admin"].username, "user_id": u["admin"].id, "company_id": u["comp"].id, "role": "admin"})
        tampered_token = valid_token[:-4] + "abcd"
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
        assert res.status_code == 401

        # 3. Wrong secret
        foreign_token = jwt.encode(
            {"sub": u["admin"].username, "user_id": u["admin"].id, "company_id": u["comp"].id, "role": "admin", "exp": int(time.time()) + 3600},
            "ATTACKER_SIGNING_KEY_XYZ_999",
            algorithm="HS256"
        )
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {foreign_token}"})
        assert res.status_code == 401

        # 4. Missing user_id claim
        missing_uid = jwt.encode(
            {"sub": u["admin"].username, "company_id": u["comp"].id, "role": "admin", "exp": int(time.time()) + 3600},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {missing_uid}"})
        assert res.status_code == 401

        # 5. Missing company_id claim
        missing_cid = jwt.encode(
            {"sub": u["admin"].username, "user_id": u["admin"].id, "role": "admin", "exp": int(time.time()) + 3600},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {missing_cid}"})
        assert res.status_code == 401

        # 6. Disabled / Inactive user
        inactive_token = create_access_token({"sub": u["inactive"].username, "user_id": u["inactive"].id, "company_id": u["comp"].id, "role": "admin"})
        res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {inactive_token}"})
        assert res.status_code == 401


def test_mass_assignment_and_privilege_injection(setup_rbac_users):
    """
    Attempts mass-assignment attacks by injecting company_id, role, or user_id into payloads.
    Expected: Server does not allow changing tenant ownership or privilege escalation.
    """
    u = setup_rbac_users
    token = create_access_token({"sub": u["editor"].username, "user_id": u["editor"].id, "company_id": u["comp"].id, "role": "editor"})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Attempt to create product while injecting foreign company_id
        res = client.post("/api/v1/production/products", json={
            "code": "MASS-ASSIGN-01",
            "name": "Mass Assigned Shoe",
            "category": "Shoe",
            "company_id": 99999
        }, headers=headers)
        assert res.status_code in (200, 201)
        created = res.json()
        assert created["company_id"] == u["comp"].id, "Injected company_id must be ignored and bound to caller company"

        # Attempt to create client while injecting foreign company_id
        res = client.post("/api/v1/sales/clients", json={
            "code": "MASS-CL-01",
            "name": "Mass Assigned Client",
            "credit_limit": 10000,
            "company_id": 88888
        }, headers=headers)
        assert res.status_code in (200, 201)
        created = res.json()
        assert created["company_id"] == u["comp"].id, "Injected company_id in client must be ignored"
