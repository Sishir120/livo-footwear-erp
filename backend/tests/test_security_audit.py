import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, SalesOrder, Invoice
from app.core.security import get_password_hash, create_access_token
from app.api.deps import COOKIE_NAME
from app.db.repository import TenantRepository

@pytest.fixture(scope="module")
def setup_audit_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Tenant 1: LIVO GROUP OF INDUSTRIES
    c1 = db.query(Company).filter(Company.code == "LIVO_AUDIT").first()
    if not c1:
        c1 = Company(name="LIVO AUDIT FACTORY", code="LIVO_AUDIT")
        db.add(c1)
        db.commit()
        db.refresh(c1)

    # Tenant 2: COMPETITOR FOOTWEAR
    c2 = db.query(Company).filter(Company.code == "COMP_AUDIT").first()
    if not c2:
        c2 = Company(name="COMPETITOR AUDIT FACTORY", code="COMP_AUDIT")
        db.add(c2)
        db.commit()
        db.refresh(c2)

    # Users in Tenant 1
    t1_editor = db.query(User).filter(User.username == "t1_editor").first()
    if not t1_editor:
        t1_editor = User(
            company_id=c1.id,
            name="Tenant 1 Editor",
            username="t1_editor",
            password_hash=get_password_hash("AuditPass123!"),
            role="editor",
            active=True
        )
        db.add(t1_editor)

    t1_viewer = db.query(User).filter(User.username == "t1_viewer").first()
    if not t1_viewer:
        t1_viewer = User(
            company_id=c1.id,
            name="Tenant 1 Viewer",
            username="t1_viewer",
            password_hash=get_password_hash("AuditPass123!"),
            role="viewer",
            active=True
        )
        db.add(t1_viewer)

    # User in Tenant 2
    t2_editor = db.query(User).filter(User.username == "t2_editor").first()
    if not t2_editor:
        t2_editor = User(
            company_id=c2.id,
            name="Tenant 2 Editor",
            username="t2_editor",
            password_hash=get_password_hash("AuditPass123!"),
            role="editor",
            active=True
        )
        db.add(t2_editor)

    db.commit()

    token_t1_editor = create_access_token({"user_id": t1_editor.id, "company_id": c1.id, "role": "editor"})
    token_t1_viewer = create_access_token({"user_id": t1_viewer.id, "company_id": c1.id, "role": "viewer"})
    token_t2_editor = create_access_token({"user_id": t2_editor.id, "company_id": c2.id, "role": "editor"})

    db.close()

    return {
        "c1_id": c1.id,
        "c2_id": c2.id,
        "tokens": {
            "t1_editor": token_t1_editor,
            "t1_viewer": token_t1_viewer,
            "t2_editor": token_t2_editor,
        }
    }


# ==============================================================================
# 1. RBAC & BOUNDARY TESTING
# ==============================================================================

def test_viewer_strictly_rejected_from_mutating_endpoints(setup_audit_env):
    """
    Verifies that 'viewer' role is strictly rejected (403 Forbidden) from all
    mutating operations across Purchase, Production, Sales, Invoices, and Backup.
    """
    token_viewer = setup_audit_env["tokens"]["t1_viewer"]

    with TestClient(app, cookies={COOKIE_NAME: token_viewer}) as client:
        # Purchase mutating endpoints
        res1 = client.post("/api/v1/purchase/suppliers", json={"code": "SUP-V", "name": "Viewer Sup"})
        assert res1.status_code == 403, f"Expected 403, got {res1.status_code}: {res1.text}"

        res2 = client.post("/api/v1/purchase/raw-materials", json={"code": "RM-V", "name": "Viewer RM"})
        assert res2.status_code == 403

        res3 = client.post("/api/v1/purchase/purchases", json={
            "supplier_id": 1, "raw_material_id": 1, "quantity": 10.0, "unit_price": 100.0,
            "purchase_date_ad": "2026-01-01", "purchase_date_bs": "2082-09-17"
        })
        assert res3.status_code == 403

        # Production mutating endpoints
        res4 = client.post("/api/v1/production/products", json={"code": "P-V", "name": "Viewer Product"})
        assert res4.status_code == 403

        res5 = client.post("/api/v1/production/batches", json={
            "batch_number": "BATCH-V", "product_id": 1, "target_quantity": 50.0, "produced_quantity": 50.0,
            "date_ad": "2026-01-01", "date_bs": "2082-09-17"
        })
        assert res5.status_code == 403

        # Sales mutating endpoints
        res6 = client.post("/api/v1/sales/clients", json={"code": "CLI-V", "name": "Viewer Client"})
        assert res6.status_code == 403

        res7 = client.post("/api/v1/sales/orders", json={
            "order_number": "ORD-V", "client_id": 1, "order_date_ad": "2026-01-01", "order_date_bs": "2082-09-17",
            "items": [{"product_id": 1, "quantity": 1.0, "unit_price": 500.0}]
        })
        assert res7.status_code == 403

        res8 = client.post("/api/v1/sales/payments", json={
            "sales_order_id": 1, "client_id": 1, "amount": 100.0, "payment_date_ad": "2026-01-01", "payment_date_bs": "2082-09-17"
        })
        assert res8.status_code == 403

        # Invoice mutating endpoints
        res9 = client.post("/api/v1/invoices", json={"sales_order_id": 1})
        assert res9.status_code == 403

        res10 = client.post("/api/v1/invoices/1/cancel")
        assert res10.status_code == 403

        # Backup trigger endpoint
        res11 = client.post("/api/v1/backup/run")
        assert res11.status_code == 403


def test_unauthenticated_requests_rejected_from_business_routes():
    """
    Verifies that unauthenticated requests (401 Unauthorized) cannot access
    any business routes.
    """
    with TestClient(app) as client:
        routes_to_test = [
            "/api/v1/purchase/suppliers",
            "/api/v1/purchase/raw-materials",
            "/api/v1/purchase/purchases",
            "/api/v1/production/products",
            "/api/v1/production/batches",
            "/api/v1/stock/movements",
            "/api/v1/stock/balance",
            "/api/v1/sales/clients",
            "/api/v1/sales/orders",
            "/api/v1/invoices",
            "/api/v1/reports/daily",
            "/api/v1/reports/stock",
            "/api/v1/backup/status",
        ]
        for route in routes_to_test:
            res = client.get(route)
            assert res.status_code == 401, f"Expected 401 for {route}, got {res.status_code}"


# ==============================================================================
# 2. TENANT ISOLATION & IDOR DEFENSE
# ==============================================================================

def test_tenant_isolation_and_idor_prevention(setup_audit_env):
    """
    Verifies that Tenant 2 cannot access, query, or mutate Tenant 1 records.
    """
    t1_token = setup_audit_env["tokens"]["t1_editor"]
    t2_token = setup_audit_env["tokens"]["t2_editor"]

    # Step A: T1 Editor creates a client, product, and sales order
    with TestClient(app, cookies={COOKIE_NAME: t1_token}) as client1:
        p_res = client1.post("/api/v1/production/products", json={"code": "T1-BOOT-101", "name": "Tenant 1 Leather Boot", "unit_price": 1200.0})
        assert p_res.status_code == 200
        t1_product_id = p_res.json()["id"]

        c_res = client1.post("/api/v1/sales/clients", json={"code": "T1-CLI-99", "name": "Tenant 1 Sole Retailer"})
        assert c_res.status_code == 200
        t1_client_id = c_res.json()["id"]

        o_res = client1.post("/api/v1/sales/orders", json={
            "order_number": "T1-ORD-9001",
            "client_id": t1_client_id,
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "items": [{"product_id": t1_product_id, "quantity": 10.0, "unit_price": 1200.0}]
        })
        assert o_res.status_code == 200
        t1_order_id = o_res.json()["id"]

        inv_res = client1.post("/api/v1/invoices", json={"sales_order_id": t1_order_id, "vat_enabled": True, "vat_rate": 13.0})
        assert inv_res.status_code == 200
        t1_invoice_id = inv_res.json()["id"]

    # Step B: T2 Editor attempts to read or mutate T1's entities
    with TestClient(app, cookies={COOKIE_NAME: t2_token}) as client2:
        # T2 should NOT see T1's products
        products_res = client2.get("/api/v1/production/products")
        assert products_res.status_code == 200
        t2_products = products_res.json()
        assert not any(p["id"] == t1_product_id for p in t2_products), "IDOR leak: Tenant 2 saw Tenant 1 product"

        # T2 should NOT see T1's clients
        clients_res = client2.get("/api/v1/sales/clients")
        assert clients_res.status_code == 200
        t2_clients = clients_res.json()
        assert not any(c["id"] == t1_client_id for c in t2_clients), "IDOR leak: Tenant 2 saw Tenant 1 client"

        # T2 should NOT see T1's invoices
        invoices_res = client2.get("/api/v1/invoices")
        assert invoices_res.status_code == 200
        t2_invoices = invoices_res.json()
        assert not any(i["id"] == t1_invoice_id for i in t2_invoices), "IDOR leak: Tenant 2 saw Tenant 1 invoice"

        # T2 cannot cancel T1's invoice (cross-tenant IDOR attack)
        cancel_res = client2.post(f"/api/v1/invoices/{t1_invoice_id}/cancel")
        assert cancel_res.status_code == 404, "Tenant 2 should receive 404 when attempting to mutate Tenant 1 invoice"

        # T2 cannot create an invoice against T1's sales order
        hijack_inv_res = client2.post("/api/v1/invoices", json={"sales_order_id": t1_order_id})
        assert hijack_inv_res.status_code == 404, "Tenant 2 should receive 404 when referencing Tenant 1 sales order"


# ==============================================================================
# 3. INPUT VALIDATION, SQL INJECTION DEFENSE & NEGATIVE FUZZING
# ==============================================================================

def test_sql_injection_defense_in_parameters(setup_audit_env):
    """
    Verifies that SQL injection attempts in string fields, category queries,
    and filter parameters are handled safely via SQLAlchemy parameterized bindings.
    """
    t1_token = setup_audit_env["tokens"]["t1_editor"]
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE products; --",
        "' UNION SELECT * FROM users --",
        "1' OR 1=1 --",
        "<script>alert('xss')</script>"
    ]

    with TestClient(app, cookies={COOKIE_NAME: t1_token}) as client:
        for payload in sql_payloads:
            # Query parameter injection in stock balance filter
            res = client.get(f"/api/v1/stock/balance?category={payload}")
            assert res.status_code == 200, "SQL injection string broke endpoint"
            assert isinstance(res.json(), list)

            # Product creation with SQL payload in name/code
            prod_res = client.post("/api/v1/production/products", json={
                "code": f"CODE-{payload[:10]}",
                "name": f"Product with {payload}",
                "unit_price": 500.0
            })
            assert prod_res.status_code == 200, "Payload crashed product creation"
            assert prod_res.json()["name"] == f"Product with {payload}"


def test_negative_fuzz_testing_payloads(setup_audit_env):
    """
    Tests unexpected payloads, malformed JSON, and string overflows.
    """
    t1_token = setup_audit_env["tokens"]["t1_editor"]

    with TestClient(app, cookies={COOKIE_NAME: t1_token}) as client:
        # String overflow payload (50,000 chars)
        giant_string = "A" * 50000
        res = client.post("/api/v1/production/products", json={
            "code": "OVERFLOW-1",
            "name": giant_string,
            "unit_price": 100.0
        })
        # Should succeed or return clean 4xx/5xx handled response, not unhandled crash
        assert res.status_code in [200, 422, 500]

        # Malformed JSON body
        res_malformed = client.post(
            "/api/v1/invoices",
            content=b"{ invalid json :::",
            headers={"Content-Type": "application/json"}
        )
        assert res_malformed.status_code == 422

        # Invalid data types (string for numeric ID/price)
        res_bad_types = client.post("/api/v1/production/products", json={
            "code": "TEST-BAD",
            "name": "Bad Types",
            "unit_price": "not-a-number"
        })
        assert res_bad_types.status_code == 422


# ==============================================================================
# 4. SESSION & TRANSPORT HARDENING
# ==============================================================================

def test_cookie_flags_security(setup_audit_env):
    """
    Verifies that the session cookie sets HttpOnly, SameSite, and follows security specs.
    """
    with TestClient(app) as client:
        login_res = client.post("/api/v1/auth/login", json={
            "username": "t1_editor",
            "password": "AuditPass123!"
        })
        assert login_res.status_code == 200
        assert COOKIE_NAME in login_res.cookies

        # Inspect raw Set-Cookie header
        set_cookie_header = login_res.headers.get("set-cookie", "")
        assert "httponly" in set_cookie_header.lower(), "Cookie missing HttpOnly flag"
        assert "samesite" in set_cookie_header.lower(), "Cookie missing SameSite flag"


def test_rate_limiter_threshold_protection():
    """
    Verifies that exceeding the rate limiter threshold on /api/v1/auth/login
    triggers an HTTP 429 Too Many Requests response.
    """
    with TestClient(app) as client:
        status_codes = []
        for i in range(35):
            res = client.post("/api/v1/auth/login", json={
                "username": f"brute_force_{i}",
                "password": "wrong"
            })
            status_codes.append(res.status_code)

        # BasicRateLimitMiddleware limits to 30 requests per minute
        assert 429 in status_codes, f"Rate limiter failed to trigger 429: {status_codes}"
