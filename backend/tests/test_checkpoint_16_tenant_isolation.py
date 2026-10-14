"""
Checkpoint 16 — Adversarial Multi-Tenant Isolation Test Suite
Standard: NIST SP 800-53 AC-3 / AC-4 / OWASP API Security Top 10 2023 (API1: BOLA)

Executes cross-tenant adversarial attacks between Company A and Company B across
all domain boundaries: READ, WRITE, and DELETE operations.
Every cross-tenant access MUST result in safe failure (404 Not Found / 403 Forbidden).
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.invoice import Invoice
from app.models.purchase import Supplier, RawMaterial
from app.models.production import ProductionBatch
from app.models.receivable import ReceivableEntry
from app.models.worker import Worker
from app.models.gallery import ProductImage
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_tenants():
    db: Session = SessionLocal()
    try:
        # Create Company A
        comp_a = db.query(Company).filter(Company.code == "COMP_A_C16").first()
        if not comp_a:
            comp_a = Company(name="Company A Footwear", code="COMP_A_C16", pan_number="111111111")
            db.add(comp_a)
            db.commit()
            db.refresh(comp_a)

        # Create Company B
        comp_b = db.query(Company).filter(Company.code == "COMP_B_C16").first()
        if not comp_b:
            comp_b = Company(name="Company B Leather", code="COMP_B_C16", pan_number="222222222")
            db.add(comp_b)
            db.commit()
            db.refresh(comp_b)

        # Users for Company A
        user_a = db.query(User).filter(User.username == "user_a_c16").first()
        if not user_a:
            user_a = User(
                name="User A Admin",
                username="user_a_c16",
                email="user_a@comp-a.com",
                company_id=comp_a.id,
                role="admin",
                password_hash=get_password_hash("PasswordA123!")
            )
            db.add(user_a)
            db.commit()
            db.refresh(user_a)

        # Users for Company B
        user_b = db.query(User).filter(User.username == "user_b_c16").first()
        if not user_b:
            user_b = User(
                name="User B Admin",
                username="user_b_c16",
                email="user_b@comp-b.com",
                company_id=comp_b.id,
                role="admin",
                password_hash=get_password_hash("PasswordB123!")
            )
            db.add(user_b)
            db.commit()
            db.refresh(user_b)

        # Populate Company B distinguishable resources
        wh_b = db.query(Warehouse).filter(Warehouse.company_id == comp_b.id).first()
        if not wh_b:
            wh_b = Warehouse(company_id=comp_b.id, name="B Main Warehouse", code="WH-B-01", is_active=True)
            db.add(wh_b)
            db.commit()
            db.refresh(wh_b)

        prod_b = db.query(Product).filter(Product.company_id == comp_b.id, Product.code == "PROD-B-101").first()
        if not prod_b:
            prod_b = Product(
                company_id=comp_b.id,
                code="PROD-B-101",
                name="Company B Boot",
                category="Boot",
                size="42",
                color="Black",
                unit_price=Decimal("4500.00")
            )
            db.add(prod_b)
            db.commit()
            db.refresh(prod_b)

        client_b = db.query(Client).filter(Client.company_id == comp_b.id, Client.code == "CL-B-01").first()
        if not client_b:
            client_b = Client(
                company_id=comp_b.id,
                code="CL-B-01",
                name="Company B Exclusive Client",
                credit_limit=Decimal("50000.00")
            )
            db.add(client_b)
            db.commit()
            db.refresh(client_b)

        sup_b = db.query(Supplier).filter(Supplier.company_id == comp_b.id, Supplier.code == "SUP-B-01").first()
        if not sup_b:
            sup_b = Supplier(company_id=comp_b.id, code="SUP-B-01", name="Supplier B Sole Co")
            db.add(sup_b)
            db.commit()
            db.refresh(sup_b)

        rm_b = db.query(RawMaterial).filter(RawMaterial.company_id == comp_b.id, RawMaterial.code == "RM-B-01").first()
        if not rm_b:
            rm_b = RawMaterial(company_id=comp_b.id, code="RM-B-01", name="Rubber Sole Material", unit="kg")
            db.add(rm_b)
            db.commit()
            db.refresh(rm_b)

        order_b = db.query(SalesOrder).filter(SalesOrder.company_id == comp_b.id, SalesOrder.order_number == "SO-B-999").first()
        if not order_b:
            order_b = SalesOrder(
                company_id=comp_b.id,
                order_number="SO-B-999",
                client_id=client_b.id,
                order_date_ad="2026-10-02",
                order_date_bs="2083-06-16",
                total_amount=Decimal("9000.00"),
                received_amount=Decimal("0.00"),
                receivable_amount=Decimal("9000.00"),
                status="confirmed"
            )
            db.add(order_b)
            db.commit()
            db.refresh(order_b)

        inv_b = db.query(Invoice).filter(Invoice.company_id == comp_b.id, Invoice.invoice_number == "INV-B-999").first()
        if not inv_b:
            inv_b = Invoice(
                company_id=comp_b.id,
                sales_order_id=order_b.id,
                invoice_number="INV-B-999",
                sequence_number=999,
                date_ad="2026-10-02",
                date_bs="2083-06-16",
                subtotal=Decimal("9000.00"),
                total_amount=Decimal("9000.00"),
                receivable_amount=Decimal("9000.00")
            )
            db.add(inv_b)
            db.commit()
            db.refresh(inv_b)

        worker_b = db.query(Worker).filter(Worker.company_id == comp_b.id, Worker.worker_code == "WRK-B-01").first()
        if not worker_b:
            worker_b = Worker(
                company_id=comp_b.id,
                worker_code="WRK-B-01",
                name="B-Worker",
                pay_type="SALARY",
                basic_rate_paisa=3000000
            )
            db.add(worker_b)
            db.commit()
            db.refresh(worker_b)

        img_b = db.query(ProductImage).filter(ProductImage.company_id == comp_b.id).first()
        if not img_b:
            img_b = ProductImage(
                company_id=comp_b.id,
                product_id=prod_b.id,
                image_url="/api/v1/gallery/images/9999/download",
                file_name="compb_secure_image.jpg",
                mime_type="image/jpeg",
                file_size_bytes=1024,
                is_primary=True
            )
            db.add(img_b)
            db.commit()
            db.refresh(img_b)

        # Company A resources
        wh_a = db.query(Warehouse).filter(Warehouse.company_id == comp_a.id).first()
        if not wh_a:
            wh_a = Warehouse(company_id=comp_a.id, name="A Main Warehouse", code="WH-A-01", is_active=True)
            db.add(wh_a)
            db.commit()
            db.refresh(wh_a)

        prod_a = db.query(Product).filter(Product.company_id == comp_a.id, Product.code == "PROD-A-101").first()
        if not prod_a:
            prod_a = Product(
                company_id=comp_a.id,
                code="PROD-A-101",
                name="Company A Loafer",
                category="Shoe",
                size="41",
                color="Brown",
                unit_price=Decimal("3500.00")
            )
            db.add(prod_a)
            db.commit()
            db.refresh(prod_a)

        client_a = db.query(Client).filter(Client.company_id == comp_a.id, Client.code == "CL-A-01").first()
        if not client_a:
            client_a = Client(
                company_id=comp_a.id,
                code="CL-A-01",
                name="Company A Client Corp",
                credit_limit=Decimal("100000.00")
            )
            db.add(client_a)
            db.commit()
            db.refresh(client_a)

        token_a = create_access_token({"sub": user_a.username, "user_id": user_a.id, "company_id": comp_a.id, "role": user_a.role})
        token_b = create_access_token({"sub": user_b.username, "user_id": user_b.id, "company_id": comp_b.id, "role": user_b.role})

        return {
            "comp_a": comp_a,
            "comp_b": comp_b,
            "user_a": user_a,
            "user_b": user_b,
            "token_a": token_a,
            "token_b": token_b,
            "b_ids": {
                "wh": wh_b.id,
                "prod": prod_b.id,
                "client": client_b.id,
                "sup": sup_b.id,
                "rm": rm_b.id,
                "order": order_b.id,
                "inv": inv_b.id,
                "worker": worker_b.id,
                "img": img_b.id
            },
            "a_ids": {
                "wh": wh_a.id,
                "prod": prod_a.id,
                "client": client_a.id
            }
        }
    finally:
        db.close()


def test_cross_company_read_isolation(setup_tenants):
    """
    User A attempts to read Company B entities via direct ID and collection endpoints.
    Expected: Collection endpoints omit B entities; direct ID lookups return 404.
    """
    token_a = setup_tenants["token_a"]
    b_ids = setup_tenants["b_ids"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with TestClient(app) as client:
        # 1. Product direct lookup & listing
        res = client.get(f"/api/v1/production/products/{b_ids['prod']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B product"

        res = client.get("/api/v1/production/products", headers=headers)
        assert res.status_code == 200
        prods = res.json()
        assert not any(p["id"] == b_ids["prod"] for p in prods), "Company B product leaked in collection"

        # 2. Client direct lookup & listing
        res = client.get(f"/api/v1/sales/clients/{b_ids['client']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B client"

        res = client.get("/api/v1/sales/clients", headers=headers)
        assert res.status_code == 200
        clients = res.json()
        assert not any(c["id"] == b_ids["client"] for c in clients), "Company B client leaked in collection"

        # 3. Warehouse direct lookup & listing
        res = client.get(f"/api/v1/stock/warehouses/{b_ids['wh']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B warehouse"

        res = client.get("/api/v1/stock/warehouses", headers=headers)
        assert res.status_code == 200
        warehouses = res.json()
        assert not any(w["id"] == b_ids["wh"] for w in warehouses), "Company B warehouse leaked in collection"

        # 4. Sales order direct lookup
        res = client.get(f"/api/v1/sales/orders/{b_ids['order']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B sales order"

        # 5. Invoice direct lookup and printable view
        res = client.get(f"/api/v1/invoices/{b_ids['inv']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B invoice"

        res = client.get(f"/api/v1/invoices/{b_ids['inv']}/printable", headers=headers)
        assert res.status_code == 404, "User A must not render Company B printable invoice"

        # 6. Supplier & Raw Material lookups
        res = client.get(f"/api/v1/purchase/suppliers/{b_ids['sup']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B supplier"

        res = client.get(f"/api/v1/purchase/raw-materials/{b_ids['rm']}", headers=headers)
        assert res.status_code == 404, "User A must not read Company B raw material"

        # 7. HR Worker direct lookup
        res = client.get(f"/api/v1/hr/workers/{b_ids['worker']}/history", headers=headers)
        assert res.status_code == 404, "User A must not read Company B worker history"

        res = client.patch(f"/api/v1/hr/workers/{b_ids['worker']}", json={"name": "Attacker Name"}, headers=headers)
        assert res.status_code == 404, "User A must not patch Company B worker"

        # 8. Gallery image direct download
        res = client.get(f"/api/v1/gallery/images/{b_ids['img']}/download", headers=headers)
        assert res.status_code == 404, "User A must not read Company B gallery image"


def test_cross_company_write_attacks(setup_tenants):
    """
    User A attempts to mutate resources using Company B foreign keys or endpoints.
    Expected: Every cross-tenant mutation is rejected (404/422).
    """
    token_a = setup_tenants["token_a"]
    b_ids = setup_tenants["b_ids"]
    a_ids = setup_tenants["a_ids"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with TestClient(app) as client:
        # Attack 1: Create sales order referencing Company B client
        res = client.post("/api/v1/sales/orders", json={
            "client_id": b_ids["client"],
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": a_ids["prod"], "quantity": 10, "unit_price": 3500.0}]
        }, headers=headers)
        assert res.status_code in (404, 422), "Cross-tenant client injection in sales order must fail"

        # Attack 2: Create sales order referencing Company B product
        res = client.post("/api/v1/sales/orders", json={
            "client_id": a_ids["client"],
            "order_date_ad": "2026-10-02",
            "order_date_bs": "2083-06-16",
            "received_amount": 0,
            "items": [{"product_id": b_ids["prod"], "quantity": 10, "unit_price": 4500.0}]
        }, headers=headers)
        assert res.status_code in (404, 422), "Cross-tenant product injection in sales order must fail"

        # Attack 3: Generate invoice referencing Company B sales order
        res = client.post("/api/v1/invoices", json={
            "sales_order_id": b_ids["order"],
            "vat_enabled": False
        }, headers=headers)
        assert res.status_code == 404, "Cross-tenant invoice generation must fail"

        # Attack 4: Stock movement referencing Company B product
        res = client.post("/api/v1/stock/movements", json={
            "product_id": b_ids["prod"],
            "direction": 1,
            "quantity": 50,
            "reference_type": "manual"
        }, headers=headers)
        assert res.status_code == 404, "Stock movement against foreign product must fail"

        # Attack 5: Stock adjustment targeting Company B warehouse
        res = client.post("/api/v1/stock/adjustments", json={
            "product_id": a_ids["prod"],
            "warehouse_id": b_ids["wh"],
            "quantity_delta": 10,
            "reason_code": "RECOUNT"
        }, headers=headers)
        assert res.status_code == 404, "Stock adjustment targeting foreign warehouse must fail"

        # Attack 6: Purchase referencing Company B supplier
        res = client.post("/api/v1/purchase/purchases", json={
            "supplier_id": b_ids["sup"],
            "raw_material_id": a_ids.get("rm", 1),
            "quantity": 100,
            "unit_price": 50.0,
            "purchase_date_ad": "2026-10-02",
            "purchase_date_bs": "2083-06-16"
        }, headers=headers)
        assert res.status_code == 404, "Purchase targeting foreign supplier must fail"

        # Attack 7: HR advance for Company B worker
        res = client.post("/api/v1/hr/advances", json={
            "worker_id": b_ids["worker"],
            "amount_paisa": 500000,
            "notes": "Unauthorized cross-tenant advance"
        }, headers=headers)
        assert res.status_code == 404, "HR advance for foreign worker must fail"

        # Attack 8: AR payment targeting Company B client
        res = client.post("/api/v1/receivables/payments", json={
            "client_id": b_ids["client"],
            "amount_paisa": 500000,
            "payment_method": "CASH"
        }, headers=headers)
        assert res.status_code == 404, "AR payment for foreign client must fail"

        # Attack 9: AR payment allocation targeting Company B invoice
        res = client.post("/api/v1/receivables/payments", json={
            "client_id": a_ids["client"],
            "amount_paisa": 500000,
            "payment_method": "CASH",
            "invoice_allocations": [{"invoice_id": b_ids["inv"], "amount_paisa": 500000}]
        }, headers=headers)
        assert res.status_code in (404, 422), "AR payment allocation to foreign invoice must fail"


def test_cross_company_delete_attacks(setup_tenants):
    """
    User A attempts to delete Company B resources.
    Expected: Safe 404 failure.
    """
    token_a = setup_tenants["token_a"]
    b_ids = setup_tenants["b_ids"]
    headers = {"Authorization": f"Bearer {token_a}"}

    with TestClient(app) as client:
        # Delete foreign gallery image
        res = client.delete(f"/api/v1/gallery/{b_ids['img']}", headers=headers)
        assert res.status_code == 404, "Deleting foreign company image must fail with 404"
