import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, StockMovement, SalesOrder, SalesExpense
from app.core.security import get_password_hash


@pytest.fixture(scope="module")
def setup_phase3_db():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "LIVO_PH3").first()
    if not comp:
        comp = Company(name="LIVO PHASE 3 ENTERPRISE", code="LIVO_PH3")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id, Warehouse.code == "WH-PH3").first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="Phase 3 Warehouse", code="WH-PH3", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    admin = db.query(User).filter(User.username == "ph3_admin").first()
    if not admin:
        admin = User(
            company_id=comp.id,
            name="Phase 3 Admin",
            username="ph3_admin",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin)

    editor = db.query(User).filter(User.username == "ph3_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="Phase 3 Editor",
            username="ph3_editor",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    viewer = db.query(User).filter(User.username == "ph3_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="Phase 3 Viewer",
            username="ph3_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    db.commit()
    comp_id = comp.id
    db.close()
    return comp_id


def test_order_creation_as_confirmed_does_not_mutate_physical_stock(setup_phase3_db):
    """
    Track 4 Test 1:
    Confirm that booking an order with status CONFIRMED creates ZERO physical stock movements
    and reserves stock under ATP calculation.
    """
    with TestClient(app) as client:
        # 1. Login as editor
        login_res = client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})
        assert login_res.status_code == 200

        # 2. Create product
        prod_res = client.post("/api/v1/production/products", json={
            "code": "PH3-DERBY-41",
            "name": "Phase 3 Classic Derby",
            "category": "Derby",
            "size": "41",
            "color": "Brown",
            "unit_price": 2500.0
        })
        assert prod_res.status_code == 200
        product_id = prod_res.json()["id"]

        # 3. Create client
        c_res = client.post("/api/v1/sales/clients", json={
            "code": "CLI-PH3-01",
            "name": "Kathmandu Retailers",
            "phone": "9841234567"
        })
        assert c_res.status_code == 200
        client_id = c_res.json()["id"]

        # 4. Add initial physical inventory (50 pairs)
        in_res = client.post("/api/v1/stock/movements", json={
            "product_id": product_id,
            "quantity": 50.0,
            "direction": 1,
            "reference_type": "production",
            "notes": "Initial batch"
        })
        assert in_res.status_code == 200

        # 5. Measure stock movement count before booking
        m_before = client.get(f"/api/v1/stock/movements?product_id={product_id}").json()
        count_before = len(m_before)

        # 6. Book wholesale order (CONFIRMED status, zero dispatch)
        so_res = client.post("/api/v1/sales/orders", json={
            "client_id": client_id,
            "order_date_ad": "2026-10-11",
            "order_date_bs": "2083-06-25",
            "status": "CONFIRMED",
            "dispatch_now": False,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 20.0,
                    "unit_price": 2500.0
                }
            ],
            "received_amount": 0.0
        })
        assert so_res.status_code in (200, 201)
        order_data = so_res.json()
        assert order_data["status"] == "CONFIRMED"
        assert order_data["delivered"] is False

        # 7. Invariant: StockMovement table row count is unchanged
        m_after = client.get(f"/api/v1/stock/movements?product_id={product_id}").json()
        assert len(m_after) == count_before, "Booking order must create zero physical stock movements!"

        # 8. Check ATP calculation: Physical=50, Reserved=20, ATP=30
        bal_res = client.get(f"/api/v1/stock/balance?product_id={product_id}")
        assert bal_res.status_code == 200
        bal_data = bal_res.json()[0]
        assert float(bal_data["physical_stock"]) == 50.0
        assert float(bal_data["reserved_stock"]) == 20.0
        assert float(bal_data["available_to_promise"]) == 30.0


def test_dispatch_action_appends_stock_movements_and_updates_status(setup_phase3_db):
    """
    Track 4 Test 2:
    Confirm that explicit dispatch action appends StockMovement rows (direction = -1),
    deducts physical inventory, and updates status to DISPATCHED.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})

        # Fetch product and client from previous test
        orders = client.get("/api/v1/sales/orders?status=CONFIRMED").json()
        assert len(orders) > 0
        order = orders[0]
        order_id = order["id"]
        product_id = order["items"][0]["product_id"]

        m_before = len(client.get(f"/api/v1/stock/movements?product_id={product_id}").json())

        # Submit explicit dispatch action
        dispatch_res = client.post(f"/api/v1/sales/orders/{order_id}/dispatch", json={
            "dispatch_date_ad": "2026-10-12",
            "dispatch_date_bs": "2083-06-26",
            "carrier_name": "Lumbini Express Logistics",
            "vehicle_number": "BA 2 KHA 9876",
            "dispatch_notes": "Driver: Ram Bahadur, 10 Cartons"
        })
        assert dispatch_res.status_code == 200
        dispatched_data = dispatch_res.json()
        assert dispatched_data["status"] == "DISPATCHED"
        assert dispatched_data["delivered"] is True
        assert dispatched_data["carrier_name"] == "Lumbini Express Logistics"
        assert dispatched_data["vehicle_number"] == "BA 2 KHA 9876"
        assert dispatched_data["dispatched_at"] is not None

        # Verify physical stock movement appended (-1 direction, SALES_DISPATCH)
        movements = client.get(f"/api/v1/stock/movements?product_id={product_id}").json()
        assert len(movements) == m_before + 1
        latest_movement = movements[0] if movements[0]["id"] > movements[-1]["id"] else movements[-1]
        assert latest_movement["direction"] == -1
        assert latest_movement["movement_type"] == "SALES_DISPATCH"
        assert float(latest_movement["quantity"]) == 20.0

        # Verify ATP balances: Physical on-hand = 30, Reserved = 0, ATP = 30
        bal = client.get(f"/api/v1/stock/balance?product_id={product_id}").json()[0]
        assert float(bal["physical_stock"]) == 30.0
        assert float(bal["reserved_stock"]) == 0.0
        assert float(bal["available_to_promise"]) == 30.0


def test_cannot_dispatch_same_order_twice(setup_phase3_db):
    """
    Track 4 Test 3:
    Verifies HTTP 409 Conflict when attempting to dispatch an already dispatched order.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})

        orders = client.get("/api/v1/sales/orders?status=DISPATCHED").json()
        assert len(orders) > 0
        order_id = orders[0]["id"]

        # Attempt duplicate dispatch
        dup_res = client.post(f"/api/v1/sales/orders/{order_id}/dispatch", json={
            "carrier_name": "Duplicate Carrier"
        })
        assert dup_res.status_code == 409, f"Expected 409 Conflict, got {dup_res.status_code}: {dup_res.text}"


def test_insufficient_physical_stock_blocks_dispatch(setup_phase3_db):
    """
    Track 4 Test 4:
    Verifies HTTP 422 INSUFFICIENT_STOCK if stock was depleted between booking and dispatch.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})

        # 1. Create a new product with 10 pairs
        prod_res = client.post("/api/v1/production/products", json={
            "code": "PH3-DEPLETE-40",
            "name": "Depleting Stock Model",
            "category": "Boot",
            "size": "40",
            "unit_price": 3000.0
        })
        pid = prod_res.json()["id"]

        clients = client.get("/api/v1/sales/clients").json()
        cid = clients[0]["id"]

        client.post("/api/v1/stock/movements", json={
            "product_id": pid,
            "quantity": 10.0,
            "direction": 1
        })

        # 2. Book order for 10 pairs (CONFIRMED)
        order_res = client.post("/api/v1/sales/orders", json={
            "client_id": cid,
            "order_date_ad": "2026-10-11",
            "order_date_bs": "2083-06-25",
            "status": "CONFIRMED",
            "dispatch_now": False,
            "items": [{"product_id": pid, "quantity": 10.0, "unit_price": 3000.0}]
        })
        assert order_res.status_code in (200, 201)
        order_id = order_res.json()["id"]

        # 3. Simulate external stock depletion (e.g., damaged stock adjustment of 10 pairs OUT)
        deplete_res = client.post("/api/v1/stock/movements", json={
            "product_id": pid,
            "quantity": 10.0,
            "direction": -1,
            "notes": "Damaged goods discarded"
        })
        assert deplete_res.status_code == 200

        # Physical stock is now 0 pairs
        # 4. Attempt to dispatch the 10-pair booked order -> must fail with HTTP 422
        dispatch_fail = client.post(f"/api/v1/sales/orders/{order_id}/dispatch", json={
            "carrier_name": "Truck 1"
        })
        assert dispatch_fail.status_code == 422
        err_detail = dispatch_fail.json()["detail"]
        assert "INSUFFICIENT_STOCK" in str(err_detail)


def test_sales_expense_integer_paisa_creation_and_aggregation(setup_phase3_db):
    """
    Track 4 Test 5:
    Verifies integer-paisa sales expense subledger creation, validation, filtering, and aggregation.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})

        # 1. Invalid category rejected
        bad_cat = client.post("/api/v1/sales/expenses", json={
            "expense_date_ad": "2026-10-11",
            "expense_date_bs": "2083-06-25",
            "particular": "Personal Lunch",
            "category": "INVALID_CATEGORY",
            "amount_paisa": 10000,
            "payment_method": "CASH"
        })
        assert bad_cat.status_code in (400, 422)

        # 2. Non-positive amount rejected
        bad_amt = client.post("/api/v1/sales/expenses", json={
            "expense_date_ad": "2026-10-11",
            "expense_date_bs": "2083-06-25",
            "particular": "Zero Expense",
            "category": "DELIVERY_FREIGHT",
            "amount_paisa": 0,
            "payment_method": "CASH"
        })
        assert bad_amt.status_code in (400, 422)

        # 3. Create valid expenses
        exp1 = client.post("/api/v1/sales/expenses", json={
            "expense_date_ad": "2026-10-11",
            "expense_date_bs": "2083-06-25",
            "particular": "Freight for Butwal shipment",
            "category": "DELIVERY_FREIGHT",
            "amount_paisa": 550000,  # 5,500.00 NPR
            "payment_method": "BANK",
            "remarks": "Paid via Nabil Bank"
        })
        assert exp1.status_code == 200
        exp1_id = exp1.json()["id"]

        exp2 = client.post("/api/v1/sales/expenses", json={
            "expense_date_ad": "2026-10-11",
            "expense_date_bs": "2083-06-25",
            "particular": "Carton boxes and tape",
            "category": "PACKING_MATERIALS",
            "amount_paisa": 120000,  # 1,200.00 NPR
            "payment_method": "CASH",
            "remarks": "Local store cash purchase"
        })
        assert exp2.status_code == 200

        # 4. List and verify aggregation
        all_exp = client.get("/api/v1/sales/expenses").json()
        assert all_exp["count"] >= 2
        assert all_exp["total_amount_paisa"] >= 670000
        assert all_exp["total_amount_npr"] >= 6700.0

        # 5. Filter by category
        freight_only = client.get("/api/v1/sales/expenses?category=DELIVERY_FREIGHT").json()
        assert any(e["id"] == exp1_id for e in freight_only["items"])
        assert not any(e["category"] != "DELIVERY_FREIGHT" for e in freight_only["items"])

        # 6. Delete expense
        del_res = client.delete(f"/api/v1/sales/expenses/{exp1_id}")
        assert del_res.status_code == 200


def test_viewer_role_blocked_from_dispatch_and_expenses(setup_phase3_db):
    """
    Track 4 Test 6:
    Confirm HTTP 403 Forbidden for viewer role on all mutating dispatch and expense endpoints.
    """
    with TestClient(app) as client:
        # Login as viewer
        client.post("/api/v1/auth/login", json={"username": "ph3_viewer", "password": "ViewerPass123!"})

        # 1. Attempt dispatch -> 403
        disp = client.post("/api/v1/sales/orders/1/dispatch", json={"carrier_name": "Test"})
        assert disp.status_code == 403

        # 2. Attempt record expense -> 403
        exp = client.post("/api/v1/sales/expenses", json={
            "expense_date_ad": "2026-10-11",
            "expense_date_bs": "2083-06-25",
            "particular": "Unauthorized expense",
            "category": "DELIVERY_FREIGHT",
            "amount_paisa": 100000,
            "payment_method": "CASH"
        })
        assert exp.status_code == 403

        # 3. Attempt delete expense -> 403
        del_exp = client.delete("/api/v1/sales/expenses/1")
        assert del_exp.status_code == 403

        # 4. View expenses -> Allowed (200)
        view_exp = client.get("/api/v1/sales/expenses")
        assert view_exp.status_code == 200


def test_invoice_creation_enforces_exact_13_percent_vat(setup_phase3_db):
    """
    Statutory 13% Nepal VAT Test 1:
    Create an order of 10 pairs @ NPR 1,000 (Taxable = NPR 10,000 = 1,000,000 paisa).
    Assert vat_amount_paisa == 130000 (NPR 1,300.00).
    Assert total_amount_paisa == 1130000 (NPR 11,300.00).
    Assert vat_rate == 13.0.
    """
    with TestClient(app) as client:
        login_res = client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})
        assert login_res.status_code == 200

        # Create product: NPR 1,000 / pair
        p_res = client.post("/api/v1/production/products", json={
            "code": "VAT-PROD-1000",
            "name": "Standard VAT Footwear Model",
            "category": "Boot",
            "size": "42",
            "color": "Black",
            "unit_price": 1000.0
        })
        assert p_res.status_code == 200
        prod_id = p_res.json()["id"]

        # Add physical stock (50 pairs) so Available-to-Promise (ATP) check passes
        stock_res = client.post("/api/v1/stock/movements", json={
            "product_id": prod_id,
            "quantity": 50.0,
            "direction": 1,
            "reference_type": "production",
            "notes": "Initial stock for VAT test"
        })
        assert stock_res.status_code == 200

        # Create client
        c_res = client.post("/api/v1/sales/clients", json={
            "code": "CLI-VAT-01",
            "name": "Nepal Footwear Distributor",
            "phone": "9841000000"
        })
        assert c_res.status_code == 200
        client_id = c_res.json()["id"]

        # Create order: 10 pairs @ 1,000 = 10,000 NPR
        order_res = client.post("/api/v1/sales/orders", json={
            "client_id": client_id,
            "order_date_ad": "2026-10-12",
            "order_date_bs": "2083-06-26",
            "status": "CONFIRMED",
            "dispatch_now": False,
            "items": [{"product_id": prod_id, "quantity": 10, "unit_price": 1000.0}]
        })
        assert order_res.status_code in (200, 201)
        order_id = order_res.json()["id"]

        # Generate invoice
        inv_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id
        })
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert inv["vat_amount_paisa"] == 130000
        assert inv["total_amount_paisa"] == 1130000
        assert float(inv["vat_rate"]) == 13.0
        assert float(inv["vat_amount"]) == 1300.0
        assert float(inv["total_amount"]) == 11300.0


def test_rejection_of_tampered_zero_vat_payload(setup_phase3_db):
    """
    Statutory 13% Nepal VAT Test 2:
    Attempt sending tampered vat_amount = 0 (or vat_enabled = False) on a taxable footwear order.
    Confirm the server strictly recalculates to statutory 13% Nepal VAT.
    """
    with TestClient(app) as client:
        login_res = client.post("/api/v1/auth/login", json={"username": "ph3_editor", "password": "EditorPass123!"})
        assert login_res.status_code == 200

        # Create product: NPR 1,000 / pair
        p_res = client.post("/api/v1/production/products", json={
            "code": "VAT-PROD-ZERO-TAMPER",
            "name": "Tamper Test Footwear",
            "category": "Sneaker",
            "size": "40",
            "color": "White",
            "unit_price": 1000.0
        })
        assert p_res.status_code == 200
        prod_id = p_res.json()["id"]

        # Add physical stock (50 pairs) so Available-to-Promise (ATP) check passes
        stock_res = client.post("/api/v1/stock/movements", json={
            "product_id": prod_id,
            "quantity": 50.0,
            "direction": 1,
            "reference_type": "production",
            "notes": "Initial stock for tamper test"
        })
        assert stock_res.status_code == 200

        # Create client
        c_res = client.post("/api/v1/sales/clients", json={
            "code": "CLI-VAT-TAMPER",
            "name": "Tamper Test Client",
            "phone": "9841111111"
        })
        assert c_res.status_code == 200
        client_id = c_res.json()["id"]

        # Create order: 10 pairs @ 1,000 = 10,000 NPR
        order_res = client.post("/api/v1/sales/orders", json={
            "client_id": client_id,
            "order_date_ad": "2026-10-12",
            "order_date_bs": "2083-06-26",
            "status": "CONFIRMED",
            "dispatch_now": False,
            "items": [{"product_id": prod_id, "quantity": 10, "unit_price": 1000.0}]
        })
        assert order_res.status_code in (200, 201)
        order_id = order_res.json()["id"]

        # Attempt to tamper by requesting vat_amount = 0 and vat_enabled = False
        tampered_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "vat_enabled": False,
            "vat_rate": 0.0,
            "vat_amount": 0.0
        })
        assert tampered_res.status_code in (200, 201)
        inv = tampered_res.json()

        # Confirm the server recalculated to statutory standard 13% VAT
        assert inv["vat_amount_paisa"] == 130000
        assert inv["total_amount_paisa"] == 1130000
        assert float(inv["vat_rate"]) == 13.0
        assert float(inv["vat_amount"]) == 1300.0
        assert float(inv["total_amount"]) == 11300.0

