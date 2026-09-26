import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User
from app.core.security import get_password_hash

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    comp = db.query(Company).filter(Company.code == "LIVO").first()
    if not comp:
        comp = Company(name="LIVO GROUP OF INDUSTRIES", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)
        
    ed = db.query(User).filter(User.username == "erp_editor").first()
    if not ed:
        ed = User(
            company_id=comp.id,
            name="ERP Editor",
            username="erp_editor",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(ed)
        db.commit()

    db.close()
    
    with TestClient(app) as test_client:
        # Login to get cookie
        res = test_client.post("/api/v1/auth/login", json={"username": "erp_editor", "password": "Pass123!"})
        assert res.status_code == 200
        yield test_client

def test_full_erp_workflow(client):
    # 1. Create Supplier & Raw Material & Purchase
    sup_res = client.post("/api/v1/purchase/suppliers", json={
        "code": "SUP-01", "name": "Polymer Leather Co", "phone": "9800000000"
    })
    assert sup_res.status_code == 200
    sup_id = sup_res.json()["id"]

    mat_res = client.post("/api/v1/purchase/raw-materials", json={
        "code": "RM-LEATHER", "name": "Synthetic Leather Black", "unit": "meters", "min_stock_alert": 50.0
    })
    assert mat_res.status_code == 200
    mat_id = mat_res.json()["id"]

    pur_res = client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup_id, "raw_material_id": mat_id, "quantity": 200.0,
        "unit_price": 450.0, "purchase_date_ad": "2026-10-01", "purchase_date_bs": "2083-06-15"
    })
    assert pur_res.status_code == 200

    # 2. Create Product & Production Batch
    prod_res = client.post("/api/v1/production/products", json={
        "code": "BOOT-BLK-42", "name": "LIVO Executive Boot Black 42",
        "category": "Boot", "size": "42", "color": "Black", "unit_price": 3200.0
    })
    assert prod_res.status_code == 200
    product_id = prod_res.json()["id"]

    batch_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-2026-999",
        "product_id": product_id,
        "target_quantity": 50.0,
        "produced_quantity": 50.0,
        "worker_count": 8,
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15",
        "material_usages": [{"raw_material_id": mat_id, "quantity_used": 25.0}]
    })
    assert batch_res.status_code == 200

    # 3. Verify Stock Balance (+50)
    stock_res = client.get("/api/v1/stock/balance")
    assert stock_res.status_code == 200
    stock_items = stock_res.json()
    product_stock = next(item for item in stock_items if item["product_id"] == product_id)
    assert product_stock["current_stock_pairs"] >= 50.0

    # 4. Create Client & Sales Order (-10)
    cli_res = client.post("/api/v1/sales/clients", json={
        "code": "CLI-KT01", "name": "Kathmandu Shoe Center", "phone": "9841000000"
    })
    assert cli_res.status_code == 200
    client_id = cli_res.json()["id"]

    order_res = client.post("/api/v1/sales/orders", json={
        "order_number": "SO-2026-999",
        "client_id": client_id,
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "received_amount": 10000.0,
        "items": [{"product_id": product_id, "quantity": 10.0, "unit_price": 3200.0}]
    })
    assert order_res.status_code == 200
    order_id = order_res.json()["id"]

    # Verify Stock Balance after sale
    stock_res2 = client.get("/api/v1/stock/balance")
    assert stock_res2.status_code == 200

    # 5. Generate Invoice
    inv_res = client.post("/api/v1/invoices", json={
        "sales_order_id": order_id,
        "vat_enabled": False
    })
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]
    assert inv_res.json()["invoice_number"].startswith("INV-01-")
    assert inv_res.json()["sequence_number"] >= 1

    # Test printable invoice HTML
    print_res = client.get(f"/api/v1/invoices/{inv_id}/printable")
    assert print_res.status_code == 200
    assert "TAX INVOICE" in print_res.text
    assert "LIVO GROUP OF INDUSTRIES" in print_res.text

    # 6. Verify Daily Report & Stock Report
    daily_res = client.get("/api/v1/reports/daily?date_ad=2026-10-01")
    assert daily_res.status_code == 200
    daily_data = daily_res.json()
    assert daily_data["production"]["total_pairs_produced"] >= 50.0
    assert daily_data["sales"]["total_sales_amount"] >= 32000.0

    stock_rep_res = client.get("/api/v1/reports/stock")
    assert stock_rep_res.status_code == 200
    assert stock_rep_res.json()["summary"]["total_stock_pairs"] >= 40.0
