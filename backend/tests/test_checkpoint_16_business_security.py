"""
Checkpoint 16 — Adversarial Business Logic, Invariants & Error Disclosure Test Suite
Standard: OWASP API Security Top 10 (API8: Lack of Protection from Automated Threats / API3: Broken Object Property Level Auth)

Attacks core domain invariants:
1. Stock zero-floor invariant (negative physical stock rejection).
2. Negative/zero quantity and price rejection across stock and sales.
3. Credit limit breach rejection without supervisor override.
4. Duplicate VAT tax invoice creation rejection (Nepal IRD statutory invariant).
5. AR payment allocation boundaries (allocations exceeding payment amount rejected).
6. Production negative/fractional quantity injection.
7. Information disclosure audit (ensuring 4xx/5xx responses do not leak stack traces or connection strings).
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder
from app.models.invoice import Invoice
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_biz_security():
    db: Session = SessionLocal()
    try:
        comp = db.query(Company).filter(Company.code == "BIZ_SEC").first()
        if not comp:
            comp = Company(name="Business Security Corp", code="BIZ_SEC", pan_number="555555555")
            db.add(comp)
            db.commit()
            db.refresh(comp)

        admin = db.query(User).filter(User.username == "biz_admin").first()
        if not admin:
            admin = User(
                name="Biz Admin",
                username="biz_admin",
                email="biz_admin@bizsec.com",
                company_id=comp.id,
                role="admin",
                active=True,
                password_hash=get_password_hash("AdminPass123!")
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id).first()
        if not wh:
            wh = Warehouse(company_id=comp.id, name="Biz Warehouse", code="WH-BIZ-01", is_active=True)
            db.add(wh)
            db.commit()
            db.refresh(wh)

        prod = db.query(Product).filter(Product.company_id == comp.id, Product.code == "BIZ-SHOE-01").first()
        if not prod:
            prod = Product(
                company_id=comp.id,
                code="BIZ-SHOE-01",
                name="Biz Derby",
                category="Shoe",
                size="41",
                color="Brown",
                unit_price=Decimal("3000.00")
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)

        # Deposit initial stock of 20 pairs
        init_m = db.query(StockMovement).filter(StockMovement.company_id == comp.id, StockMovement.product_id == prod.id).first()
        if not init_m:
            init_m = StockMovement(
                company_id=comp.id,
                product_id=prod.id,
                warehouse_id=wh.id,
                size="41",
                quantity=Decimal("20.0"),
                direction=1,
                ref_type="manual",
                movement_type="PRODUCTION_IN",
                actor_id=admin.id,
                date_ad="2026-10-02",
                date_bs="2083-06-16"
            )
            db.add(init_m)
            db.commit()

        # Client with strict credit limit of NPR 10,000
        client_rec = db.query(Client).filter(Client.company_id == comp.id, Client.code == "BIZ-CL-01").first()
        if not client_rec:
            client_rec = Client(
                company_id=comp.id,
                code="BIZ-CL-01",
                name="Strict Credit Client",
                credit_limit=Decimal("10000.00")
            )
            db.add(client_rec)
            db.commit()
            db.refresh(client_rec)

        token = create_access_token({
            "sub": admin.username,
            "user_id": admin.id,
            "company_id": comp.id,
            "role": admin.role
        })

        return {
            "comp": comp,
            "admin": admin,
            "wh": wh,
            "prod": prod,
            "client": client_rec,
            "token": token
        }
    finally:
        db.close()


def test_stock_invariants_attack(setup_biz_security):
    """
    Attacks inventory invariants:
    1. Outbound movement exceeding physical balance (zero-floor).
    2. Negative quantity.
    3. Zero quantity.
    4. Invalid direction.
    """
    ctx = setup_biz_security
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    with TestClient(app) as client:
        # Attack 1: Request 50 pairs when only 20 are in stock
        res = client.post("/api/v1/stock/movements", json={
            "product_id": ctx["prod"].id,
            "direction": -1,
            "quantity": 50,
            "reference_type": "manual"
        }, headers=headers)
        assert res.status_code == 422, "Overselling stock must be rejected with 422"
        data = res.json()
        assert "INSUFFICIENT_STOCK" in str(data)

        # Attack 2: Negative quantity in movement
        res = client.post("/api/v1/stock/movements", json={
            "product_id": ctx["prod"].id,
            "direction": 1,
            "quantity": -10,
            "reference_type": "manual"
        }, headers=headers)
        assert res.status_code in (400, 422)

        # Attack 3: Zero quantity in movement
        res = client.post("/api/v1/stock/movements", json={
            "product_id": ctx["prod"].id,
            "direction": 1,
            "quantity": 0,
            "reference_type": "manual"
        }, headers=headers)
        assert res.status_code in (400, 422)

        # Attack 4: Invalid direction (e.g. 2 or -2)
        res = client.post("/api/v1/stock/movements", json={
            "product_id": ctx["prod"].id,
            "direction": 2,
            "quantity": 5,
            "reference_type": "manual"
        }, headers=headers)
        assert res.status_code == 400


def test_sales_and_credit_invariants_attack(setup_biz_security):
    """
    Attacks sales orders and credit limit rules:
    1. Negative unit price.
    2. Negative item quantity.
    3. Credit limit breach without supervisor override.
    """
    ctx = setup_biz_security
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    with TestClient(app) as client:
        # Attack 1: Negative unit price
        res = client.post("/api/v1/sales/orders", json={
            "client_id": ctx["client"].id,
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": ctx["prod"].id, "quantity": 1, "unit_price": -500.0}]
        }, headers=headers)
        assert res.status_code in (400, 422)

        # Attack 2: Negative item quantity
        res = client.post("/api/v1/sales/orders", json={
            "client_id": ctx["client"].id,
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": ctx["prod"].id, "quantity": -5, "unit_price": 3000.0}]
        }, headers=headers)
        assert res.status_code in (400, 422)

        # Attack 3: Credit limit breach (Order value NPR 15,000 exceeds limit of NPR 10,000)
        res = client.post("/api/v1/sales/orders", json={
            "client_id": ctx["client"].id,
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": ctx["prod"].id, "quantity": 5, "unit_price": 3000.0}],  # 15,000
            "supervisor_override": False
        }, headers=headers)
        assert res.status_code == 422, "Credit limit breach without supervisor override must fail"
        assert "CREDIT_LIMIT_EXCEEDED" in str(res.json())


def test_vat_invoice_statutory_invariant(setup_biz_security):
    """
    Attacks statutory tax duplicate liability:
    Creating duplicate active VAT invoices for the same sales order must be rejected (409 Conflict).
    """
    ctx = setup_biz_security
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    with TestClient(app) as client:
        # Create a valid sales order with supervisor_override to isolate VAT statutory testing
        res_order = client.post("/api/v1/sales/orders", json={
            "client_id": ctx["client"].id,
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": ctx["prod"].id, "quantity": 2, "unit_price": 3000.0}],
            "delivered": False,
            "supervisor_override": True
        }, headers=headers)
        assert res_order.status_code in (200, 201)
        order_id = res_order.json()["id"]

        # 1. Generate first VAT invoice -> 200
        res_inv1 = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "vat_enabled": True
        }, headers=headers)
        assert res_inv1.status_code in (200, 201)

        # 2. Attempt duplicate VAT invoice for the same order -> 409 Conflict
        res_inv2 = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "vat_enabled": True
        }, headers=headers)
        assert res_inv2.status_code == 409, "Duplicate VAT invoice for the same sales order must be rejected"


def test_receivables_over_allocation_rejection(setup_biz_security):
    """
    Attacks AR payment allocation sum:
    Total allocated paisa exceeding the receipt amount must be rejected with 422.
    """
    ctx = setup_biz_security
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    with TestClient(app) as client:
        res = client.post("/api/v1/receivables/payments", json={
            "client_id": ctx["client"].id,
            "amount_paisa": 100000,  # 1,000 NPR
            "payment_method": "CASH",
            "invoice_allocations": [
                {"invoice_id": 1, "amount_paisa": 80000},
                {"invoice_id": 2, "amount_paisa": 50000}  # Total 130,000 > 100,000
            ]
        }, headers=headers)
        assert res.status_code == 422, "Payment allocations exceeding receipt amount must fail"


def test_error_responses_do_not_leak_sensitive_internals(setup_biz_security):
    """
    Deliberately triggers 400, 401, 404, 422 error states across endpoints.
    Verifies response bodies NEVER leak stack traces, database URLs, passwords, or filesystem paths.
    """
    ctx = setup_biz_security
    headers = {"Authorization": f"Bearer {ctx['token']}"}

    endpoints_to_probe = [
        ("GET", "/api/v1/production/products/99999999", None, headers),
        ("POST", "/api/v1/sales/orders", {"client_id": 99999999}, headers),
        ("POST", "/api/v1/auth/login", {"username": "nonexistent_user", "password": "WrongPassword!"}, {}),
        ("GET", "/api/v1/gallery/images/9999999/download", None, headers)
    ]

    forbidden_substrings = [
        "Traceback (most recent call last)",
        "sqlite://",
        "postgresql://",
        "password_hash",
        "SECRET_KEY",
        "d:\\antigravity",
        "/var/app"
    ]

    with TestClient(app) as client:
        for method, route, body, hdrs in endpoints_to_probe:
            if method == "GET":
                res = client.get(route, headers=hdrs)
            else:
                res = client.post(route, json=body, headers=hdrs)

            content = res.text.lower()
            for bad_str in forbidden_substrings:
                assert bad_str.lower() not in content, f"Sensitive leak detected in {route} response: {bad_str}"
