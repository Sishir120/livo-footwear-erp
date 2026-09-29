import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, StockMovement
from app.core.security import get_password_hash

@pytest.fixture(scope="module")
def setup_db():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "LIVO").first()
    if not comp:
        comp = Company(name="LIVO GROUP OF INDUSTRIES", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Warehouse
    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id, Warehouse.code == "WH-MAIN").first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="Main Finished Warehouse", code="WH-MAIN", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    # Admin user
    admin = db.query(User).filter(User.username == "stock_admin").first()
    if not admin:
        admin = User(
            company_id=comp.id,
            name="Stock Admin",
            username="stock_admin",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin)

    # Editor user
    editor = db.query(User).filter(User.username == "stock_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="Stock Editor",
            username="stock_editor",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    # Viewer user
    viewer = db.query(User).filter(User.username == "stock_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="Stock Viewer",
            username="stock_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    db.commit()
    db.close()
    return comp.id


def test_batch_creation_generates_positive_stock_movements(setup_db):
    company_id = setup_db
    with TestClient(app) as client:
        # Login as editor
        res = client.post("/api/v1/auth/login", json={"username": "stock_editor", "password": "EditorPass123!"})
        assert res.status_code == 200

        # Create a product
        p_res = client.post("/api/v1/production/products", json={
            "code": "TEST-OXF-42",
            "name": "Test Oxford Shoe",
            "category": "Shoe",
            "size": "42",
            "color": "Black",
            "unit_price": 1200.0
        })
        assert p_res.status_code == 200
        prod = p_res.json()
        prod_id = prod["id"]

        # Create production batch
        b_res = client.post("/api/v1/production/batches", json={
            "batch_number": "BATCH-TEST-001",
            "product_id": prod_id,
            "target_quantity": 40.0,
            "produced_quantity": 40.0,
            "worker_count": 5,
            "date_ad": "2026-09-29",
            "date_bs": "2083-06-13"
        })
        assert b_res.status_code == 200

        # Verify stock movements created
        m_res = client.get(f"/api/v1/stock/ledger?product_id={prod_id}")
        assert m_res.status_code == 200
        data = m_res.json()
        assert data["total"] >= 1
        latest = data["items"][0]
        assert latest["movement_type"] == "PRODUCTION_IN"
        assert latest["direction"] == 1
        assert latest["quantity"] == 40.0
        assert latest["size"] == "42"
        assert latest["source_doc_ref"] == "BATCH-TEST-001"
        assert latest["running_balance"] == 40.0


def test_sales_dispatch_generates_negative_stock_movements(setup_db):
    company_id = setup_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "stock_editor", "password": "EditorPass123!"})

        # Create product & produce stock
        p_res = client.post("/api/v1/production/products", json={
            "code": "TEST-SLP-40",
            "name": "Test Factory Slipper",
            "category": "Slipper",
            "size": "40",
            "color": "Blue",
            "unit_price": 450.0
        })
        prod_id = p_res.json()["id"]

        client.post("/api/v1/production/batches", json={
            "batch_number": "BATCH-SLP-01",
            "product_id": prod_id,
            "target_quantity": 60.0,
            "produced_quantity": 60.0,
            "worker_count": 4,
            "date_ad": "2026-09-29",
            "date_bs": "2083-06-13"
        })

        # Create client
        c_res = client.post("/api/v1/sales/clients", json={
            "code": "CLI-PATAN-01",
            "name": "Patan Footwear Wholesale",
            "address": "Patan, Lalitpur"
        })
        assert c_res.status_code == 200
        client_id = c_res.json()["id"]

        # Create delivered sales order
        so_res = client.post("/api/v1/sales/orders", json={
            "order_number": "SO-TEST-001",
            "client_id": client_id,
            "order_date_ad": "2026-09-29",
            "order_date_bs": "2083-06-13",
            "delivered": True,
            "items": [
                {
                    "product_id": prod_id,
                    "quantity": 15.0,
                    "unit_price": 450.0
                }
            ],
            "received_amount": 6750.0
        })
        assert so_res.status_code == 200

        # Verify ledger has negative movement
        l_res = client.get(f"/api/v1/stock/ledger?product_id={prod_id}")
        assert l_res.status_code == 200
        items = l_res.json()["items"]
        assert len(items) >= 2
        sales_mov = items[0]
        assert sales_mov["movement_type"] == "SALES_OUT"
        assert sales_mov["direction"] == -1
        assert sales_mov["quantity"] == 15.0
        assert sales_mov["qty_out"] == 15.0
        assert sales_mov["running_balance"] == 45.0  # 60 - 15 = 45


def test_adjustment_rbac_and_zero_floor(setup_db):
    company_id = setup_db
    with TestClient(app) as client:
        # 1. Viewer is strictly 403 Forbidden
        client.post("/api/v1/auth/login", json={"username": "stock_viewer", "password": "ViewerPass123!"})
        v_adj = client.post("/api/v1/stock/adjustments", json={
            "product_id": 1,
            "warehouse_id": 1,
            "size": "42",
            "quantity_delta": 5.0,
            "reason_code": "RECOUNT_CORRECTION"
        })
        assert v_adj.status_code == 403

        # 2. Editor login
        client.post("/api/v1/auth/login", json={"username": "stock_editor", "password": "EditorPass123!"})

        # Create a new product with 20 stock
        p_res = client.post("/api/v1/production/products", json={
            "code": "TEST-ADJ-38",
            "name": "Test Adjustment Sandal",
            "category": "Sandal",
            "size": "38",
            "color": "Tan",
            "unit_price": 700.0
        })
        prod_id = p_res.json()["id"]

        # Positive adjustment (+20) allowed for editor
        pos_res = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "38",
            "quantity_delta": 20.0,
            "reason_code": "RECOUNT_CORRECTION",
            "reason_text": "Initial physical audit recount"
        })
        assert pos_res.status_code == 200
        assert pos_res.json()["direction"] == 1
        assert pos_res.json()["quantity"] == 20.0

        # Downward recount adjustment allowed for editor
        recount_down = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "38",
            "quantity_delta": -4.0,
            "reason_code": "RECOUNT_CORRECTION",
            "reason_text": "Over-count correction"
        })
        assert recount_down.status_code == 200
        assert recount_down.json()["direction"] == -1
        assert recount_down.json()["quantity"] == 4.0

        # Downward DAMAGED adjustment without supervisor token rejected for editor
        dmg_unauth = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "38",
            "quantity_delta": -2.0,
            "reason_code": "DAMAGED",
            "reason_text": "Water damaged in monsoon"
        })
        assert dmg_unauth.status_code == 403

        # Downward DAMAGED adjustment WITH supervisor token accepted for editor
        dmg_auth = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "38",
            "quantity_delta": -2.0,
            "reason_code": "DAMAGED",
            "reason_text": "Water damaged in monsoon",
            "supervisor_token": "SUPERVISOR_AUTH_2026"
        })
        assert dmg_auth.status_code == 200
        assert dmg_auth.json()["movement_type"] == "ADJUSTMENT_OUT"

        # Zero floor rejection: attempting to reduce more than available (current is 20 - 4 - 2 = 14)
        zero_floor = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "38",
            "quantity_delta": -50.0,
            "reason_code": "RECOUNT_CORRECTION"
        })
        assert zero_floor.status_code == 422
        assert "negative" in zero_floor.json()["detail"].lower()


def test_reversal_restores_exact_balance_and_prevents_duplicates(setup_db):
    company_id = setup_db
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "stock_editor", "password": "EditorPass123!"})

        # Product
        p_res = client.post("/api/v1/production/products", json={
            "code": "TEST-REV-41",
            "name": "Test Reversal Boot",
            "category": "Boot",
            "size": "41",
            "color": "Brown",
            "unit_price": 2500.0
        })
        prod_id = p_res.json()["id"]

        # Initial stock: +30
        client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "41",
            "quantity_delta": 30.0,
            "reason_code": "RECOUNT_CORRECTION"
        })

        # Add +10 movement to be reversed
        m10_res = client.post("/api/v1/stock/adjustments", json={
            "product_id": prod_id,
            "warehouse_id": 1,
            "size": "41",
            "quantity_delta": 10.0,
            "reason_code": "RECOUNT_CORRECTION",
            "reason_text": "Accidental double entry"
        })
        mov_to_reverse = m10_res.json()
        mov_id = mov_to_reverse["id"]

        # Balance before reversal is 40
        bal_res = client.get(f"/api/v1/stock/ledger?product_id={prod_id}")
        assert bal_res.json()["items"][0]["running_balance"] == 40.0

        # Reverse movement
        rev_res = client.post(f"/api/v1/stock/reversals/{mov_id}")
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert rev_data["movement_type"] == "VOID_REVERSAL"
        assert rev_data["direction"] == -1
        assert rev_data["quantity"] == 10.0
        assert rev_data["reversal_of_id"] == mov_id

        # Verify balance restored to exactly 30.0
        bal_after = client.get(f"/api/v1/stock/ledger?product_id={prod_id}")
        assert bal_after.json()["items"][0]["running_balance"] == 30.0

        # Duplicate reversal rejected with 400
        dup_rev = client.post(f"/api/v1/stock/reversals/{mov_id}")
        assert dup_rev.status_code == 400

        # Cannot reverse a void reversal itself
        rev_of_rev = client.post(f"/api/v1/stock/reversals/{rev_data['id']}")
        assert rev_of_rev.status_code == 400
