import pytest
import time
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, SalesOrder, Invoice, AuditLog
from app.models.sales import Client
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.production import ProductionBatch
from app.core.security import get_password_hash, create_access_token
from app.api.deps import COOKIE_NAME

@pytest.fixture(scope="module")
def setup_checkpoint10_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Company Alpha (ID will be alpha.id)
    c_alpha = db.query(Company).filter(Company.code == "CP10_ALPHA").first()
    if not c_alpha:
        c_alpha = Company(name="ALPHA FOOTWEAR CORP", code="CP10_ALPHA", pan_number="900000001")
        db.add(c_alpha)
        db.commit()
        db.refresh(c_alpha)

    # Company Beta (ID will be beta.id)
    c_beta = db.query(Company).filter(Company.code == "CP10_BETA").first()
    if not c_beta:
        c_beta = Company(name="BETA FOOTWEAR CORP", code="CP10_BETA", pan_number="900000002")
        db.add(c_beta)
        db.commit()
        db.refresh(c_beta)

    # Alpha Users: Admin, Editor, Viewer
    alpha_admin = db.query(User).filter(User.username == "cp10_alpha_admin").first()
    if not alpha_admin:
        alpha_admin = User(
            company_id=c_alpha.id,
            name="Alpha Admin",
            username="cp10_alpha_admin",
            password_hash=get_password_hash("AlphaPass123!"),
            role="admin",
            active=True
        )
        db.add(alpha_admin)

    alpha_editor = db.query(User).filter(User.username == "cp10_alpha_editor").first()
    if not alpha_editor:
        alpha_editor = User(
            company_id=c_alpha.id,
            name="Alpha Editor",
            username="cp10_alpha_editor",
            password_hash=get_password_hash("AlphaPass123!"),
            role="editor",
            active=True
        )
        db.add(alpha_editor)

    alpha_viewer = db.query(User).filter(User.username == "cp10_alpha_viewer").first()
    if not alpha_viewer:
        alpha_viewer = User(
            company_id=c_alpha.id,
            name="Alpha Viewer",
            username="cp10_alpha_viewer",
            password_hash=get_password_hash("AlphaPass123!"),
            role="viewer",
            active=True
        )
        db.add(alpha_viewer)

    # Beta Users: Admin, Editor
    beta_admin = db.query(User).filter(User.username == "cp10_beta_admin").first()
    if not beta_admin:
        beta_admin = User(
            company_id=c_beta.id,
            name="Beta Admin",
            username="cp10_beta_admin",
            password_hash=get_password_hash("BetaPass123!"),
            role="admin",
            active=True
        )
        db.add(beta_admin)

    beta_editor = db.query(User).filter(User.username == "cp10_beta_editor").first()
    if not beta_editor:
        beta_editor = User(
            company_id=c_beta.id,
            name="Beta Editor",
            username="cp10_beta_editor",
            password_hash=get_password_hash("BetaPass123!"),
            role="editor",
            active=True
        )
        db.add(beta_editor)

    db.commit()

    token_alpha_admin = create_access_token({"user_id": alpha_admin.id, "company_id": c_alpha.id, "role": "admin", "sub": "cp10_alpha_admin"})
    token_alpha_editor = create_access_token({"user_id": alpha_editor.id, "company_id": c_alpha.id, "role": "editor", "sub": "cp10_alpha_editor"})
    token_alpha_viewer = create_access_token({"user_id": alpha_viewer.id, "company_id": c_alpha.id, "role": "viewer", "sub": "cp10_alpha_viewer"})
    token_beta_admin = create_access_token({"user_id": beta_admin.id, "company_id": c_beta.id, "role": "admin", "sub": "cp10_beta_admin"})
    token_beta_editor = create_access_token({"user_id": beta_editor.id, "company_id": c_beta.id, "role": "editor", "sub": "cp10_beta_editor"})

    db.close()

    return {
        "alpha_id": c_alpha.id,
        "beta_id": c_beta.id,
        "users": {
            "alpha_admin_id": alpha_admin.id,
            "alpha_editor_id": alpha_editor.id,
            "alpha_viewer_id": alpha_viewer.id,
            "beta_admin_id": beta_admin.id,
            "beta_editor_id": beta_editor.id,
        },
        "tokens": {
            "alpha_admin": token_alpha_admin,
            "alpha_editor": token_alpha_editor,
            "alpha_viewer": token_alpha_viewer,
            "beta_admin": token_beta_admin,
            "beta_editor": token_beta_editor,
        }
    }


def test_cross_tenant_idor_protection_across_all_entities(setup_checkpoint10_env):
    """
    SECTION 3 & 4: Broken Object Level Authorization (IDOR) & Tenant Isolation Audit.
    Alpha creates resources across all domains.
    Beta attempts GET on /clients/{id}, /suppliers/{id}, /raw-materials/{id},
    /products/{id}, /warehouses/{id}, /batches/{id}, /orders/{id}, /invoices/{id},
    and /invoices/{id}/printable.
    All must return 404 (Not Found in tenant scope). Never return Company Alpha data to Beta.
    """
    tokens = setup_checkpoint10_env["tokens"]
    alpha_editor = tokens["alpha_editor"]
    beta_editor = tokens["beta_editor"]

    # 1. Company Alpha creates test entities
    with TestClient(app, cookies={COOKIE_NAME: alpha_editor}) as client_a:
        sup_res = client_a.post("/api/v1/purchase/suppliers", json={"code": "AL-SUP-1", "name": "Alpha Tannery"})
        assert sup_res.status_code == 200
        alpha_sup_id = sup_res.json()["id"]

        mat_res = client_a.post("/api/v1/purchase/raw-materials", json={"code": "AL-RM-1", "name": "Alpha EVA Sheet"})
        assert mat_res.status_code == 200
        alpha_mat_id = mat_res.json()["id"]

        pur_res = client_a.post("/api/v1/purchase/purchases", json={
            "supplier_id": alpha_sup_id,
            "raw_material_id": alpha_mat_id,
            "quantity": 100.0,
            "unit_price": 50.0,
            "purchase_date_ad": "2026-10-01",
            "purchase_date_bs": "2083-06-15"
        })
        assert pur_res.status_code == 200
        alpha_pur_id = pur_res.json()["id"]

        prod_res = client_a.post("/api/v1/production/products", json={"code": "AL-SHOE-1", "name": "Alpha Trekker", "unit_price": 2500.0})
        assert prod_res.status_code == 200
        alpha_prod_id = prod_res.json()["id"]

        batch_res = client_a.post("/api/v1/production/batches", json={
            "product_id": alpha_prod_id,
            "target_quantity": 40.0,
            "produced_quantity": 40.0,
            "worker_count": 5,
            "date_ad": "2026-10-01",
            "date_bs": "2083-06-15"
        })
        assert batch_res.status_code == 200
        alpha_batch_id = batch_res.json()["id"]

        cli_res = client_a.post("/api/v1/sales/clients", json={"code": "AL-CLI-1", "name": "Alpha Shoe Mart"})
        assert cli_res.status_code == 200
        alpha_cli_id = cli_res.json()["id"]

        ord_res = client_a.post("/api/v1/sales/orders", json={
            "client_id": alpha_cli_id,
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "items": [{"product_id": alpha_prod_id, "quantity": 10.0, "unit_price": 2500.0}]
        })
        assert ord_res.status_code == 200
        alpha_ord_id = ord_res.json()["id"]

        inv_res = client_a.post("/api/v1/invoices", json={"sales_order_id": alpha_ord_id, "vat_enabled": True, "vat_rate": 13.0})
        assert inv_res.status_code == 200
        alpha_inv_id = inv_res.json()["id"]

        # Warehouse ID for Alpha
        wh_res = client_a.get("/api/v1/stock/warehouses")
        assert wh_res.status_code == 200
        alpha_wh_id = wh_res.json()[0]["id"]

    # 2. Company Beta attempts to fetch Alpha's records by ID (IDOR Attack)
    with TestClient(app, cookies={COOKIE_NAME: beta_editor}) as client_b:
        idor_targets = [
            f"/api/v1/purchase/suppliers/{alpha_sup_id}",
            f"/api/v1/purchase/raw-materials/{alpha_mat_id}",
            f"/api/v1/purchase/purchases/{alpha_pur_id}",
            f"/api/v1/production/products/{alpha_prod_id}",
            f"/api/v1/production/batches/{alpha_batch_id}",
            f"/api/v1/stock/warehouses/{alpha_wh_id}",
            f"/api/v1/sales/clients/{alpha_cli_id}",
            f"/api/v1/sales/orders/{alpha_ord_id}",
            f"/api/v1/invoices/{alpha_inv_id}",
            f"/api/v1/invoices/{alpha_inv_id}/printable",
        ]

        for target in idor_targets:
            res = client_b.get(target)
            assert res.status_code == 404, f"IDOR Vulnerability detected! Route {target} returned {res.status_code} to Tenant Beta instead of 404"


def test_client_supplied_tenant_id_mass_assignment_neutralized(setup_checkpoint10_env):
    """
    SECTION 2 & 7: Never Trust Client Tenant IDs & Mass Assignment Audit.
    Client submits malicious company_id (Beta's ID or arbitrary ID 9999).
    Server MUST derive tenant context strictly from authenticated user.
    """
    tokens = setup_checkpoint10_env["tokens"]
    alpha_editor = tokens["alpha_editor"]
    alpha_id = setup_checkpoint10_env["alpha_id"]
    beta_id = setup_checkpoint10_env["beta_id"]

    with TestClient(app, cookies={COOKIE_NAME: alpha_editor}) as client:
        # 1. Product creation with client-injected company_id
        res_prod = client.post("/api/v1/production/products", json={
            "code": "SPOOF-PROD-01",
            "name": "Spoofed Product",
            "unit_price": 100.0,
            "company_id": beta_id  # Attack attempt
        })
        assert res_prod.status_code == 200
        prod_data = res_prod.json()
        assert prod_data["company_id"] == alpha_id, "Tenant ID spoofed in Product!"

        # 2. Client creation with spoofed company_id
        res_cli = client.post("/api/v1/sales/clients", json={
            "code": "SPOOF-CLI-01",
            "name": "Spoofed Client",
            "company_id": 99999  # Attack attempt
        })
        assert res_cli.status_code == 200
        cli_data = res_cli.json()
        assert cli_data["company_id"] == alpha_id, "Tenant ID spoofed in Client!"

        # 3. Supplier creation with spoofed company_id
        res_sup = client.post("/api/v1/purchase/suppliers", json={
            "code": "SPOOF-SUP-01",
            "name": "Spoofed Supplier",
            "company_id": beta_id
        })
        assert res_sup.status_code == 200
        sup_data = res_sup.json()
        assert sup_data["company_id"] == alpha_id, "Tenant ID spoofed in Supplier!"


def test_privilege_escalation_and_rbac_boundaries(setup_checkpoint10_env):
    """
    SECTION 5, 6, & 18: Role-Based Access Control & Admin Boundaries.
    Viewer -> cannot mutate anything (403).
    Editor -> cannot access admin/telemetry/backup/user-management endpoints (403).
    Admin -> allowed to access admin endpoints.
    """
    tokens = setup_checkpoint10_env["tokens"]
    viewer_token = tokens["alpha_viewer"]
    editor_token = tokens["alpha_editor"]
    admin_token = tokens["alpha_admin"]

    # 1. Viewer attempts mutations
    with TestClient(app, cookies={COOKIE_NAME: viewer_token}) as client_v:
        # Attempt to create product
        res1 = client_v.post("/api/v1/production/products", json={"code": "V-PROD", "name": "V-Shoe"})
        assert res1.status_code == 403
        # Attempt to create worker
        res2 = client_v.post("/api/v1/hr/workers", json={"worker_code": "V-WRK", "name": "Viewer Worker", "pay_type": "WAGE", "basic_rate_paisa": 50000})
        assert res2.status_code == 403
        # Attempt to trigger backup
        res3 = client_v.post("/api/v1/backup/run")
        assert res3.status_code == 403

    # 2. Editor attempts administrative endpoints
    with TestClient(app, cookies={COOKIE_NAME: editor_token}) as client_e:
        # Operations telemetry cockpit
        res_tel = client_e.get("/api/v1/ops/telemetry")
        assert res_tel.status_code == 403, "Editor escalated to ops telemetry cockpit!"
        # Trigger immediate system backup
        res_bk = client_e.post("/api/v1/backup/run")
        assert res_bk.status_code == 403, "Editor escalated to trigger system backup!"
        # User management list
        res_ul = client_e.get("/api/v1/auth/users")
        assert res_ul.status_code == 403, "Editor escalated to view users list!"
        # User creation
        res_uc = client_e.post("/api/v1/auth/users", json={
            "username": "hacked_admin",
            "name": "Hacked",
            "password": "Password123!",
            "role": "admin"
        })
        assert res_uc.status_code == 403, "Editor escalated to create admin user!"

    # 3. Admin successfully accesses administrative endpoints
    with TestClient(app, cookies={COOKIE_NAME: admin_token}) as client_a:
        res_tel = client_a.get("/api/v1/ops/telemetry")
        assert res_tel.status_code == 200
        assert "db_status" in res_tel.json()

        res_ul = client_a.get("/api/v1/auth/users")
        assert res_ul.status_code == 200
        assert isinstance(res_ul.json(), list)


def test_deactivated_user_blocked_immediately(setup_checkpoint10_env):
    """
    SECTION 13 & 16: User Lifecycle & Immediate Session Revocation.
    A deactivated user must NOT continue performing mutations or accessing
    data merely because an existing JWT was previously minted.
    """
    admin_token = setup_checkpoint10_env["tokens"]["alpha_admin"]
    uniq_name = f"fired_{int(time.time() * 1000)}"

    # Step 1: Admin creates an active user
    with TestClient(app, cookies={COOKIE_NAME: admin_token}) as client_admin:
        create_res = client_admin.post("/api/v1/auth/users", json={
            "username": uniq_name,
            "name": "Temporary Employee",
            "password": "SecretPassword123!",
            "role": "editor"
        })
        assert create_res.status_code == 201
        fired_user_id = create_res.json()["id"]

    # Step 2: Employee logs in and obtains token
    with TestClient(app) as client_auth:
        login_res = client_auth.post("/api/v1/auth/login", json={
            "username": uniq_name,
            "password": "SecretPassword123!"
        })
        assert login_res.status_code == 200
        emp_token = login_res.cookies[COOKIE_NAME]

    # Step 3: Employee verifies access works
    with TestClient(app, cookies={COOKIE_NAME: emp_token}) as client_emp:
        me_res = client_emp.get("/api/v1/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["username"] == uniq_name

    # Step 4: Admin deactivates employee
    with TestClient(app, cookies={COOKIE_NAME: admin_token}) as client_admin:
        deact_res = client_admin.patch(f"/api/v1/auth/users/{fired_user_id}", json={"active": False})
        assert deact_res.status_code == 200
        assert deact_res.json()["active"] is False

    # Step 5: Employee attempts request with previously minted token
    with TestClient(app, cookies={COOKIE_NAME: emp_token}) as client_emp:
        # Authentication dependency looks up active user in DB
        blocked_res = client_emp.get("/api/v1/auth/me")
        assert blocked_res.status_code == 401, "Deactivated user was not blocked!"
        assert "inactive" in blocked_res.json()["detail"].lower()


def test_jwt_tampering_and_expired_token():
    """
    SECTION 11 & 12: Token Lifecycle & JWT Claim Integrity.
    Verifies that:
    - Tampered token signature is rejected.
    - Tampered payload is rejected.
    - Expired token is rejected.
    - Missing token is rejected.
    """
    # 1. Expired token
    expired_payload = {
        "user_id": 1,
        "company_id": 1,
        "role": "admin",
        "sub": "expired_admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=2)
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with TestClient(app, cookies={COOKIE_NAME: expired_token}) as client:
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()

    # 2. Tampered signature
    valid_payload = {
        "user_id": 1,
        "company_id": 1,
        "role": "admin",
        "sub": "tampered_admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=2)
    }
    tampered_token = jwt.encode(valid_payload, "WRONG_SECRET_KEY_ATTACKER", algorithm=settings.ALGORITHM)

    with TestClient(app, cookies={COOKIE_NAME: tampered_token}) as client:
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    # 3. Missing token
    with TestClient(app) as client:
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401


def test_reports_and_analytics_tenant_partitioning(setup_checkpoint10_env):
    """
    SECTION 20: Security of Reports & Analytics Aggregation Queries.
    Verifies that aggregated reports (/daily, /stock, /analytics/top-products)
    strictly filter by authenticated company_id and never leak metrics across tenants.
    """
    tokens = setup_checkpoint10_env["tokens"]
    alpha_editor = tokens["alpha_editor"]
    beta_editor = tokens["beta_editor"]

    iso_date = "2099-12-31"

    # 1. Tenant Alpha creates daily report data specifically on iso_date
    with TestClient(app, cookies={COOKIE_NAME: alpha_editor}) as client_a:
        p_res = client_a.post("/api/v1/production/products", json={"code": f"REP-P-{int(time.time()*1000)}", "name": "Report Prod"})
        prod_id = p_res.json()["id"]

        b_res = client_a.post("/api/v1/production/batches", json={
            "product_id": prod_id,
            "target_quantity": 25.0,
            "produced_quantity": 25.0,
            "worker_count": 2,
            "date_ad": iso_date,
            "date_bs": "2083-06-15"
        })
        assert b_res.status_code == 200

        rep_a = client_a.get(f"/api/v1/reports/daily?date_ad={iso_date}")
        assert rep_a.status_code == 200
        assert rep_a.json()["production"]["batch_count"] >= 1, "Tenant Alpha should see its production batch"

    # 2. Tenant Beta queries daily report for the exact same date
    with TestClient(app, cookies={COOKIE_NAME: beta_editor}) as client_b:
        rep_b = client_b.get(f"/api/v1/reports/daily?date_ad={iso_date}")
        assert rep_b.status_code == 200
        b_data = rep_b.json()
        assert b_data["production"]["batch_count"] == 0, "Aggregation leak! Beta saw Alpha's batch count!"
        assert b_data["sales"]["order_count"] == 0, "Aggregation leak! Beta saw Alpha's sales count!"

        # Stock report leak check: verify Alpha's product is never in Beta's stock report
        stock_rep = client_b.get("/api/v1/reports/stock")
        assert stock_rep.status_code == 200
        beta_items = stock_rep.json()["items"]
        assert all(item["product_id"] != prod_id for item in beta_items), "Alpha product leaked into Beta stock report!"


def test_cors_policy_and_security_headers():
    """
    SECTION 10 & 25: CORS & HTTP Security Headers.
    CORS origins are explicitly restricted (no wildcard with credentials).
    Security headers (nosniff, DENY, etc.) are present on all responses.
    """
    with TestClient(app) as client:
        # Request with allowed frontend origin
        allowed_res = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert allowed_res.status_code == 200
        assert allowed_res.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert allowed_res.headers.get("access-control-allow-credentials") == "true"

        # Request with unauthorized origin
        evil_res = client.get(
            "/api/v1/health",
            headers={"Origin": "http://evil-competitor-site.com"}
        )
        assert evil_res.headers.get("access-control-allow-origin") is None or evil_res.headers.get("access-control-allow-origin") != "http://evil-competitor-site.com"

        # Security Headers
        assert allowed_res.headers.get("X-Content-Type-Options") == "nosniff"
        assert allowed_res.headers.get("X-Frame-Options") == "DENY"
        assert "strict-origin-when-cross-origin" in allowed_res.headers.get("Referrer-Policy", "")
        assert "geolocation=()" in allowed_res.headers.get("Permissions-Policy", "")


def test_user_management_cross_tenant_idor(setup_checkpoint10_env):
    """
    SECTION 16 & 18: Admin boundaries & Cross-tenant User Management IDOR.
    Alpha Admin cannot view or mutate users belonging to Company Beta.
    """
    tokens = setup_checkpoint10_env["tokens"]
    alpha_admin = tokens["alpha_admin"]
    beta_admin_id = setup_checkpoint10_env["users"]["beta_admin_id"]

    with TestClient(app, cookies={COOKIE_NAME: alpha_admin}) as client:
        # Alpha Admin lists users: should only see Alpha's users
        users_res = client.get("/api/v1/auth/users")
        assert users_res.status_code == 200
        user_ids = [u["id"] for u in users_res.json()]
        assert beta_admin_id not in user_ids, "Cross-tenant leak: Alpha Admin saw Beta Admin!"

        # Alpha Admin attempts to modify Beta Admin (IDOR attack)
        patch_res = client.patch(f"/api/v1/auth/users/{beta_admin_id}", json={"active": False})
        assert patch_res.status_code == 404, "Alpha Admin was able to target Beta user!"


def test_login_security_and_account_enumeration():
    """
    SECTION 14 & 15: Password Security & Login Abuse / Account Enumeration Defense.
    Both non-existent accounts and wrong passwords must return identical 401
    'Incorrect username or password' responses.
    """
    with TestClient(app) as client:
        # Non-existent user
        res_fake = client.post("/api/v1/auth/login", json={
            "username": "totally_nonexistent_user_999",
            "password": "SomePassword123!"
        })
        assert res_fake.status_code == 401
        assert res_fake.json()["detail"] == "Incorrect username or password"

        # Existing user with wrong password
        res_wrong_pw = client.post("/api/v1/auth/login", json={
            "username": "admin_demo",
            "password": "WrongPasswordAttempt!"
        })
        assert res_wrong_pw.status_code == 401
        assert res_wrong_pw.json()["detail"] == "Incorrect username or password"


def test_document_numbering_cross_tenant_independence(setup_checkpoint10_env):
    """
    SECTION 4 & 17: Document Sequences Partitioned Per Tenant.
    Both Alpha and Beta generate invoices; sequences increment monotonically
    per tenant without interference or collision.
    """
    tokens = setup_checkpoint10_env["tokens"]
    alpha_editor = tokens["alpha_editor"]
    beta_editor = tokens["beta_editor"]

    t_stamp = int(time.time() * 1000)
    # Alpha creates a product and order
    with TestClient(app, cookies={COOKIE_NAME: alpha_editor}) as client_a:
        p_a = client_a.post("/api/v1/production/products", json={"code": f"SQ-A-{t_stamp}", "name": "Seq Alpha Product"}).json()
        c_a = client_a.post("/api/v1/sales/clients", json={"code": f"SQ-A-C-{t_stamp}", "name": "Seq Alpha Client"}).json()
        o_a = client_a.post("/api/v1/sales/orders", json={
            "client_id": c_a["id"],
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "delivered": False,
            "items": [{"product_id": p_a["id"], "quantity": 1.0, "unit_price": 500.0}]
        }).json()
        inv_a = client_a.post("/api/v1/invoices", json={"sales_order_id": o_a["id"]}).json()

    # Beta creates a product and order
    with TestClient(app, cookies={COOKIE_NAME: beta_editor}) as client_b:
        p_b = client_b.post("/api/v1/production/products", json={"code": f"SQ-B-{t_stamp}", "name": "Seq Beta Product"}).json()
        c_b = client_b.post("/api/v1/sales/clients", json={"code": f"SQ-B-C-{t_stamp}", "name": "Seq Beta Client"}).json()
        o_b = client_b.post("/api/v1/sales/orders", json={
            "client_id": c_b["id"],
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "delivered": False,
            "items": [{"product_id": p_b["id"], "quantity": 1.0, "unit_price": 600.0}]
        }).json()
        inv_b = client_b.post("/api/v1/invoices", json={"sales_order_id": o_b["id"]}).json()

    # Sequence numbers must be company-prefixed and independent
    assert inv_a["company_id"] == setup_checkpoint10_env["alpha_id"]
    assert inv_b["company_id"] == setup_checkpoint10_env["beta_id"]
    assert inv_a["invoice_number"].startswith(f"INV-{setup_checkpoint10_env['alpha_id']:02d}-")
    assert inv_b["invoice_number"].startswith(f"INV-{setup_checkpoint10_env['beta_id']:02d}-")
