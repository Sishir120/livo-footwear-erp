"""
Checkpoint 16 — Adversarial IDOR / BOLA Regression Test Suite
Standard: OWASP API Security Top 10 2023 (API1: BOLA) / NIST SP 800-53 AC-3

Attacks every endpoint accepting an object identifier by substituting foreign entity IDs
owned by Company B into requests authenticated as Company A.
All GET, PUT, PATCH, POST actions, and DELETE endpoints MUST safely reject foreign IDs (404/422).
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse
from app.models.sales import Client, SalesOrder
from app.models.invoice import Invoice
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.production import ProductionBatch
from app.models.worker import Worker
from app.models.gallery import ProductImage
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_idor_entities():
    db: Session = SessionLocal()
    try:
        # Tenants
        comp_a = db.query(Company).filter(Company.code == "IDOR_A").first()
        if not comp_a:
            comp_a = Company(name="IDOR Tenant A", code="IDOR_A", pan_number="333333331")
            db.add(comp_a)
            db.commit()
            db.refresh(comp_a)

        comp_b = db.query(Company).filter(Company.code == "IDOR_B").first()
        if not comp_b:
            comp_b = Company(name="IDOR Tenant B", code="IDOR_B", pan_number="333333332")
            db.add(comp_b)
            db.commit()
            db.refresh(comp_b)

        # User A (attacker)
        user_a = db.query(User).filter(User.username == "idor_user_a").first()
        if not user_a:
            user_a = User(
                name="IDOR Attacker User",
                username="idor_user_a",
                email="attacker@idora.com",
                company_id=comp_a.id,
                role="admin",
                password_hash=get_password_hash("AttackerPass123!")
            )
            db.add(user_a)
            db.commit()
            db.refresh(user_a)

        # Company B victim entities
        wh_b = db.query(Warehouse).filter(Warehouse.company_id == comp_b.id).first()
        if not wh_b:
            wh_b = Warehouse(company_id=comp_b.id, name="Victim Warehouse", code="WH-VIC-01", is_active=True)
            db.add(wh_b)
            db.commit()
            db.refresh(wh_b)

        prod_b = db.query(Product).filter(Product.company_id == comp_b.id, Product.code == "PROD-VIC-01").first()
        if not prod_b:
            prod_b = Product(
                company_id=comp_b.id,
                code="PROD-VIC-01",
                name="Victim Shoe",
                category="Shoe",
                size="42",
                color="Black",
                unit_price=Decimal("5000.00")
            )
            db.add(prod_b)
            db.commit()
            db.refresh(prod_b)

        client_b = db.query(Client).filter(Client.company_id == comp_b.id, Client.code == "CL-VIC-01").first()
        if not client_b:
            client_b = Client(company_id=comp_b.id, code="CL-VIC-01", name="Victim Client", credit_limit=Decimal("100000.00"))
            db.add(client_b)
            db.commit()
            db.refresh(client_b)

        order_b = db.query(SalesOrder).filter(SalesOrder.company_id == comp_b.id, SalesOrder.order_number == "SO-VIC-01").first()
        if not order_b:
            order_b = SalesOrder(
                company_id=comp_b.id,
                order_number="SO-VIC-01",
                client_id=client_b.id,
                order_date_ad="2026-10-02",
                order_date_bs="2083-06-16",
                total_amount=Decimal("10000.00"),
                received_amount=Decimal("0.00"),
                receivable_amount=Decimal("10000.00"),
                status="confirmed"
            )
            db.add(order_b)
            db.commit()
            db.refresh(order_b)

        inv_b = db.query(Invoice).filter(Invoice.company_id == comp_b.id, Invoice.invoice_number == "INV-VIC-01").first()
        if not inv_b:
            inv_b = Invoice(
                company_id=comp_b.id,
                sales_order_id=order_b.id,
                invoice_number="INV-VIC-01",
                sequence_number=101,
                date_ad="2026-10-02",
                date_bs="2083-06-16",
                subtotal=Decimal("10000.00"),
                total_amount=Decimal("10000.00"),
                receivable_amount=Decimal("10000.00")
            )
            db.add(inv_b)
            db.commit()
            db.refresh(inv_b)

        sup_b = db.query(Supplier).filter(Supplier.company_id == comp_b.id, Supplier.code == "SUP-VIC-01").first()
        if not sup_b:
            sup_b = Supplier(company_id=comp_b.id, code="SUP-VIC-01", name="Victim Leather Supplier")
            db.add(sup_b)
            db.commit()
            db.refresh(sup_b)

        rm_b = db.query(RawMaterial).filter(RawMaterial.company_id == comp_b.id, RawMaterial.code == "RM-VIC-01").first()
        if not rm_b:
            rm_b = RawMaterial(company_id=comp_b.id, code="RM-VIC-01", name="Victim Leather Hide", unit="kg")
            db.add(rm_b)
            db.commit()
            db.refresh(rm_b)

        purch_b = db.query(Purchase).filter(Purchase.company_id == comp_b.id).first()
        if not purch_b:
            purch_b = Purchase(
                company_id=comp_b.id,
                supplier_id=sup_b.id,
                raw_material_id=rm_b.id,
                quantity=Decimal("100.0"),
                unit_price=Decimal("150.0"),
                total_amount=Decimal("15000.0"),
                purchase_date_ad="2026-10-02",
                purchase_date_bs="2083-06-16"
            )
            db.add(purch_b)
            db.commit()
            db.refresh(purch_b)

        worker_b = db.query(Worker).filter(Worker.company_id == comp_b.id, Worker.worker_code == "WRK-VIC-01").first()
        if not worker_b:
            worker_b = Worker(
                company_id=comp_b.id,
                worker_code="WRK-VIC-01",
                name="Victim Craftsman",
                pay_type="SALARY",
                basic_rate_paisa=4000000
            )
            db.add(worker_b)
            db.commit()
            db.refresh(worker_b)

        batch_b = db.query(ProductionBatch).filter(ProductionBatch.company_id == comp_b.id).first()
        if not batch_b:
            batch_b = ProductionBatch(
                company_id=comp_b.id,
                batch_number="BATCH-VIC-01",
                product_id=prod_b.id,
                target_quantity=Decimal("50.0"),
                produced_quantity=Decimal("0.0"),
                status="PLANNED",
                date_ad="2026-10-02",
                date_bs="2083-06-16"
            )
            db.add(batch_b)
            db.commit()
            db.refresh(batch_b)

        img_b = db.query(ProductImage).filter(ProductImage.company_id == comp_b.id).first()
        if not img_b:
            img_b = ProductImage(
                company_id=comp_b.id,
                product_id=prod_b.id,
                image_url="/api/v1/gallery/images/9991/download",
                file_name="victim_shoe_img.jpg",
                mime_type="image/jpeg",
                file_size_bytes=2048,
                is_primary=True
            )
            db.add(img_b)
            db.commit()
            db.refresh(img_b)

        token_a = create_access_token({
            "sub": user_a.username,
            "user_id": user_a.id,
            "company_id": comp_a.id,
            "role": user_a.role
        })

        return {
            "token_a": token_a,
            "victim_ids": {
                "wh": wh_b.id,
                "prod": prod_b.id,
                "client": client_b.id,
                "order": order_b.id,
                "inv": inv_b.id,
                "sup": sup_b.id,
                "rm": rm_b.id,
                "purch": purch_b.id,
                "worker": worker_b.id,
                "batch": batch_b.id,
                "img": img_b.id
            }
        }
    finally:
        db.close()


def test_idor_get_substitutions(setup_idor_entities):
    """
    Substitutes victim object IDs into User A's GET requests.
    Expected: Safe 404 Not Found for every single object type.
    """
    token = setup_idor_entities["token_a"]
    v = setup_idor_entities["victim_ids"]
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Product BOLA
        res = client.get(f"/api/v1/production/products/{v['prod']}", headers=headers)
        assert res.status_code == 404

        # Client BOLA
        res = client.get(f"/api/v1/sales/clients/{v['client']}", headers=headers)
        assert res.status_code == 404

        # Warehouse BOLA
        res = client.get(f"/api/v1/stock/warehouses/{v['wh']}", headers=headers)
        assert res.status_code == 404

        # Sales Order BOLA
        res = client.get(f"/api/v1/sales/orders/{v['order']}", headers=headers)
        assert res.status_code == 404

        # Invoice BOLA
        res = client.get(f"/api/v1/invoices/{v['inv']}", headers=headers)
        assert res.status_code == 404

        # Printable Invoice BOLA
        res = client.get(f"/api/v1/invoices/{v['inv']}/printable", headers=headers)
        assert res.status_code == 404

        # Supplier BOLA
        res = client.get(f"/api/v1/purchase/suppliers/{v['sup']}", headers=headers)
        assert res.status_code == 404

        # Raw Material BOLA
        res = client.get(f"/api/v1/purchase/raw-materials/{v['rm']}", headers=headers)
        assert res.status_code == 404

        # Purchase BOLA
        res = client.get(f"/api/v1/purchase/purchases/{v['purch']}", headers=headers)
        assert res.status_code == 404

        # Worker History BOLA
        res = client.get(f"/api/v1/hr/workers/{v['worker']}/history", headers=headers)
        assert res.status_code == 404

        # Production Order BOLA
        res = client.get(f"/api/v1/production/{v['batch']}", headers=headers)
        assert res.status_code == 404

        # Gallery Image Download BOLA
        res = client.get(f"/api/v1/gallery/images/{v['img']}/download", headers=headers)
        assert res.status_code == 404


def test_idor_patch_and_delete_substitutions(setup_idor_entities):
    """
    Substitutes victim object IDs into User A's PATCH, POST, and DELETE requests.
    Expected: Safe 404 Not Found for mutations against foreign objects.
    """
    token = setup_idor_entities["token_a"]
    v = setup_idor_entities["victim_ids"]
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Patch foreign worker
        res = client.patch(f"/api/v1/hr/workers/{v['worker']}", json={"basic_rate_paisa": 1000}, headers=headers)
        assert res.status_code == 404

        # Delete foreign gallery image
        res = client.delete(f"/api/v1/gallery/{v['img']}", headers=headers)
        assert res.status_code == 404

        # Void or status transition on foreign invoice
        res = client.patch(f"/api/v1/invoices/{v['inv']}/status", json={"status": "PAID"}, headers=headers)
        assert res.status_code in (404, 405)

        # Complete foreign production batch
        res = client.post(f"/api/v1/production/{v['batch']}/complete", headers=headers)
        assert res.status_code in (404, 422)
