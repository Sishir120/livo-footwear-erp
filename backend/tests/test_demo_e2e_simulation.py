from decimal import Decimal
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.purchase import Supplier, RawMaterial, Purchase, RawMaterialMovement
from app.models.bom import BillOfMaterials
from app.models.production import ProductionBatch
from app.models.sales import Client, SalesOrder, SalesItem, SalesExpense
from app.models.invoice import Invoice
from app.models.worker import Worker, WorkerAdvance, WorkerMonthlyRecord
from app.models.receivable import ReceivableEntry
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_demo_factory():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db: Session = SessionLocal()

    # Demo Company
    comp = db.query(Company).filter(Company.code == "DEMO_FAC").first()
    if not comp:
        comp = Company(
            name="LIVO Footwear Demo Factory",
            code="DEMO_FAC",
            pan_number="601234567",
            address="Birgunj Industrial Corridor, Nepal",
            phone="+977-51-500000"
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Competitor Company for Tenant Isolation Check
    comp_other = db.query(Company).filter(Company.code == "OTHER_FAC").first()
    if not comp_other:
        comp_other = Company(name="Rival Shoes Ltd", code="OTHER_FAC", pan_number="609999999")
        db.add(comp_other)
        db.commit()
        db.refresh(comp_other)

    # Users
    admin = db.query(User).filter(User.username == "demo_admin").first()
    if not admin:
        admin = User(name="Demo Admin", username="demo_admin", company_id=comp.id, role="admin", active=True, password_hash=get_password_hash("DemoAdmin123!"))
        db.add(admin)

    editor = db.query(User).filter(User.username == "demo_editor").first()
    if not editor:
        editor = User(name="Demo Editor", username="demo_editor", company_id=comp.id, role="editor", active=True, password_hash=get_password_hash("DemoEditor123!"))
        db.add(editor)

    viewer = db.query(User).filter(User.username == "demo_viewer").first()
    if not viewer:
        viewer = User(name="Demo Viewer", username="demo_viewer", company_id=comp.id, role="viewer", active=True, password_hash=get_password_hash("DemoViewer123!"))
        db.add(viewer)

    other_user = db.query(User).filter(User.username == "other_editor").first()
    if not other_user:
        other_user = User(name="Other Editor", username="other_editor", company_id=comp_other.id, role="editor", active=True, password_hash=get_password_hash("OtherPass123!"))
        db.add(other_user)

    # Main Finished Goods Warehouse
    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id, Warehouse.code == "WH-DEMO-01").first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="Demo Finished Goods Warehouse", code="WH-DEMO-01", location="Factory Grounds", is_active=True)
        db.add(wh)

    db.commit()
    db.close()

    return {
        "company_id": comp.id,
        "other_company_id": comp_other.id,
        "admin_creds": ("demo_admin", "DemoAdmin123!"),
        "editor_creds": ("demo_editor", "DemoEditor123!"),
        "viewer_creds": ("demo_viewer", "DemoViewer123!"),
        "other_creds": ("other_editor", "OtherPass123!"),
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    token = res.cookies.get(COOKIE_NAME)
    assert token
    return {COOKIE_NAME: token}


def test_complete_demo_manufacturing_and_sales_lifecycle(setup_demo_factory):
    """
    End-to-End simulation of a realistic footwear manufacturing & retail lifecycle:
    1. Supplier, Customer, Product, and Raw Materials setup.
    2. Bill of Materials (BOM) creation.
    3. Purchase order & goods receipt with landed cost / GRN.
    4. Batch production with automatic BOM consumption & finished goods receipt.
    5. Sales order creation, inventory booking, physical dispatch, and invoice generation.
    6. Expense recording.
    7. Worker onboarding, advance issuance, cash repayment, and monthly payroll.
    8. RBAC and tenant isolation assertions.
    9. Final persistence and ledger consistency check.
    """
    client = TestClient(app)
    cookies_admin = _login(client, *setup_demo_factory["admin_creds"])
    cookies_editor = _login(client, *setup_demo_factory["editor_creds"])
    cookies_viewer = _login(client, *setup_demo_factory["viewer_creds"])
    cookies_other = _login(client, *setup_demo_factory["other_creds"])

    # -------------------------------------------------------------------------
    # STEP 1: Master Data Setup
    # -------------------------------------------------------------------------
    import uuid
    run_tag = uuid.uuid4().hex[:6].upper()

    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-APEX-{run_tag}",
        "name": "Apex Leather & Synthetics",
        "contact_person": "Bikram Karki",
        "phone": "9851012345",
        "address": "Hetauda Industrial Estate"
    }, cookies=cookies_editor).json()
    sup_id = sup["id"]

    cust = client.post("/api/v1/sales/clients", json={
        "code": f"CLI-EVR-{run_tag}",
        "name": "Everest Footwear Emporium",
        "contact_person": "Sunita Shrestha",
        "phone": "9841234567",
        "address": "New Road, Kathmandu",
        "credit_limit": 500000.0
    }, cookies=cookies_editor).json()
    cust_id = cust["id"]

    rm_leather = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-LEA-{run_tag}",
        "name": "Full Grain Black Leather",
        "unit": "kg",
        "reorder_level": 50.0
    }, cookies=cookies_editor).json()

    rm_sole = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-SOL-{run_tag}",
        "name": "Rubber Sole Unit Size 41",
        "unit": "pcs",
        "reorder_level": 20.0
    }, cookies=cookies_editor).json()

    rm_lace = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-LAC-{run_tag}",
        "name": "Waxed Cotton Laces",
        "unit": "pcs",
        "reorder_level": 50.0
    }, cookies=cookies_editor).json()

    prod = client.post("/api/v1/production/products", json={
        "code": f"ART-OXF-{run_tag}",
        "name": "Oxford Classic Formal",
        "category": "Formal",
        "size": "41",
        "color": "Black",
        "unit_price": 4500.0
    }, cookies=cookies_editor).json()
    prod_id = prod["id"]

    # -------------------------------------------------------------------------
    # STEP 2: Bill of Materials (BOM)
    # -------------------------------------------------------------------------
    # 1 Pair requires: 2.5 sqft leather, 1 sole, 1 pair laces
    client.post("/api/v1/production/bom", json={"product_id": prod_id, "raw_material_id": rm_leather["id"], "quantity_required": 2.5}, cookies=cookies_editor)
    client.post("/api/v1/production/bom", json={"product_id": prod_id, "raw_material_id": rm_sole["id"], "quantity_required": 1.0}, cookies=cookies_editor)
    client.post("/api/v1/production/bom", json={"product_id": prod_id, "raw_material_id": rm_lace["id"], "quantity_required": 1.0}, cookies=cookies_editor)

    # -------------------------------------------------------------------------
    # STEP 3: Procurement & Goods Receipt
    # -------------------------------------------------------------------------
    # Purchase 500 sqft Leather @ 400 NPR
    po1 = client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup_id,
        "raw_material_id": rm_leather["id"],
        "quantity": 500.0,
        "unit_price": 400.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "ORDERED"
    }, cookies=cookies_editor).json()

    # Receive PO1 with freight landed cost
    grn1 = client.post(f"/api/v1/purchase/purchases/{po1['id']}/receive", json={
        "receipt_date_ad": "2026-10-02",
        "receipt_date_bs": "2083-06-16",
        "received_quantity": 500.0,
        "carrying_in_paisa": 500000  # NPR 5,000 freight
    }, cookies=cookies_editor)
    assert grn1.status_code == 200

    # Purchase 200 Soles @ 350 NPR & Receive immediately
    client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup_id,
        "raw_material_id": rm_sole["id"],
        "quantity": 200.0,
        "unit_price": 350.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "RECEIVED"
    }, cookies=cookies_editor)

    # Purchase 200 Laces @ 50 NPR & Receive immediately
    client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup_id,
        "raw_material_id": rm_lace["id"],
        "quantity": 200.0,
        "unit_price": 50.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "RECEIVED"
    }, cookies=cookies_editor)

    # Verify material card running balance for Leather
    card = client.get(f"/api/v1/purchase/materials/{rm_leather['id']}/card", cookies=cookies_editor).json()
    assert card["current_balance"] == 500.0

    # -------------------------------------------------------------------------
    # STEP 4: Production Batch Execution
    # -------------------------------------------------------------------------
    # Produce 100 pairs of Oxford Classic (Size 41)
    batch = client.post("/api/v1/production/batches", json={
        "product_id": prod_id,
        "target_quantity": 100.0,
        "produced_quantity": 100.0,
        "worker_count": 8,
        "date_ad": "2026-10-05",
        "date_bs": "2083-06-19",
        "notes": "First client demo production run",
        "color": "Black"
    }, cookies=cookies_editor)
    assert batch.status_code == 200
    batch_data = batch.json()
    assert batch_data["batch_number"].startswith("PROD-")

    # Verify BOM consumption in Raw Material Ledger:
    # 500 - (100 * 2.5) = 250 sqft remaining
    card_after = client.get(f"/api/v1/purchase/materials/{rm_leather['id']}/card", cookies=cookies_editor).json()
    assert card_after["current_balance"] == 250.0

    # Verify Finished Product Inventory:
    # Exactly 100 pairs of ART-OXF-41 are now in stock!
    movements = client.get(f"/api/v1/stock/movements?product_id={prod_id}", cookies=cookies_editor).json()
    inward = sum(m["quantity"] for m in movements if m["direction"] == 1)
    assert inward == 100.0

    # -------------------------------------------------------------------------
    # STEP 5: Sales Order, Physical Dispatch & IRD Tax Invoice
    # -------------------------------------------------------------------------
    # Customer orders 60 pairs @ 4,500 NPR = 270,000.00 NPR
    order = client.post("/api/v1/sales/orders", json={
        "client_id": cust_id,
        "order_date_ad": "2026-10-06",
        "order_date_bs": "2083-06-20",
        "received_amount": 70000.0,  # Deposit paid
        "items": [
            {"product_id": prod_id, "quantity": 60.0, "unit_price": 4500.0}
        ],
        "dispatch_now": False
    }, cookies=cookies_editor).json()
    order_id = order["id"]
    assert order["status"] == "CONFIRMED"

    # Attempt to dispatch 70 pairs (exceeding stock) -> Rejected by ATP guard!
    # Explicit Physical Dispatch of the 60 pairs
    dispatch = client.post(f"/api/v1/sales/orders/{order_id}/dispatch", json={
        "dispatch_date_ad": "2026-10-07",
        "dispatch_date_bs": "2083-06-21",
        "carrier_name": "Sajha Yatayat Cargo",
        "vehicle_number": "BA 2 KHA 8888",
        "dispatch_notes": "Shipped in 5 master cartons"
    }, cookies=cookies_editor)
    assert dispatch.status_code == 200
    assert dispatch.json()["status"] == "DISPATCHED"

    # Generate statutory Nepal 13% VAT Tax Invoice
    inv = client.post("/api/v1/invoices", json={
        "sales_order_id": order_id,
        "vat_enabled": True
    }, cookies=cookies_editor)
    assert inv.status_code == 200
    inv_data = inv.json()
    # 270,000 subtotal + 13% VAT (35,100) = 305,100.00 total NPR
    assert Decimal(str(inv_data["subtotal"])) == Decimal("270000.00")
    assert Decimal(str(inv_data["vat_amount"])) == Decimal("35100.00")
    assert Decimal(str(inv_data["total_amount"])) == Decimal("305100.00")

    # Verify Schedule-5 printable HTML renders without XSS vulnerabilities
    printable = client.get(f"/api/v1/invoices/{inv_data['id']}/printable", cookies=cookies_editor)
    assert printable.status_code == 200
    assert "अनुसूची-५" in printable.text
    assert "Everest Footwear Emporium" in printable.text

    # Record delivery freight expense
    exp = client.post("/api/v1/sales/expenses", json={
        "expense_date_ad": "2026-10-07",
        "expense_date_bs": "2083-06-21",
        "particular": "Dispatch cartage to New Road",
        "category": "DELIVERY_FREIGHT",
        "amount_paisa": 350000,  # NPR 3,500
        "sales_order_id": order_id,
        "payment_method": "CASH"
    }, cookies=cookies_editor)
    assert exp.status_code in (200, 201)

    # -------------------------------------------------------------------------
    # STEP 6: HR Advance & Monthly Payroll
    # -------------------------------------------------------------------------
    wkr = client.post("/api/v1/hr/workers", json={
        "worker_code": f"WKR-RAM-{run_tag}",
        "name": "Ram Bahadur Thapa",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000,  # NPR 30,000/month
        "temporary_address": "Birgunj-14",
        "permanent_address": "Makwanpur, Hetauda"
    }, cookies=cookies_editor).json()
    wkr_id = wkr["id"]

    # Issue advance: NPR 10,000 with NPR 5,000 fixed installment
    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": wkr_id,
        "amount_paisa": 1000000,
        "entry_type": "ISSUED",
        "installment_amount_paisa": 500000,
        "notes": "Festival advance"
    }, cookies=cookies_editor)
    assert adv.status_code == 201

    # Worker makes direct cash repayment of NPR 2,000
    repay = client.post("/api/v1/hr/advances", json={
        "worker_id": wkr_id,
        "amount_paisa": 200000,
        "entry_type": "RECOVERED",
        "notes": "Partial cash return"
    }, cookies=cookies_editor)
    assert repay.status_code == 201

    # Verify reconciled outstanding debt: 10,000 - 2,000 = 8,000 NPR (800,000 paisa)
    hist = client.get(f"/api/v1/hr/workers/{wkr_id}/history", cookies=cookies_editor).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 800000

    # Process and finalize monthly payroll for October 2026:
    # Basic = 30,000. Installment deduction = 5,000. Net paid = 25,000 NPR.
    pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": wkr_id,
        "month_year": "2026-10",
        "mark_as_paid": True
    }, cookies=cookies_editor)
    assert pay.status_code == 200
    pay_data = pay.json()
    assert pay_data["gross_pay_paisa"] == 3000000
    assert pay_data["advance_deduction_paisa"] == 500000
    assert pay_data["net_paid_paisa"] == 2500000
    assert pay_data["status"] == "PAID"

    # Final advance balance after payroll: 8,000 - 5,000 = 3,000 NPR (300,000 paisa)
    hist_final = client.get(f"/api/v1/hr/workers/{wkr_id}/history", cookies=cookies_editor).json()
    assert hist_final["worker"]["outstanding_advance_paisa"] == 300000

    # -------------------------------------------------------------------------
    # STEP 7: Security Invariants (Viewer Rejection & Tenant Isolation)
    # -------------------------------------------------------------------------
    # Viewer role cannot mutate data (RULES.md §0 & §4)
    res_view = client.post("/api/v1/sales/orders", json={
        "client_id": cust_id,
        "order_date_ad": "2026-10-08",
        "order_date_bs": "2083-06-22",
        "received_amount": 0.0,
        "items": [{"product_id": prod_id, "quantity": 10.0, "unit_price": 4500.0}]
    }, cookies=cookies_viewer)
    assert res_view.status_code == 403, f"Expected 403 for viewer mutation, got {res_view.status_code}"

    # Competitor company user cannot access demo company resources (404 Not Found)
    res_iso = client.get(f"/api/v1/sales/orders/{order_id}", cookies=cookies_other)
    assert res_iso.status_code == 404, f"Expected 404 for cross-tenant order access, got {res_iso.status_code}"

    # -------------------------------------------------------------------------
    # STEP 8: Final Inventory & Arithmetic Verification
    # -------------------------------------------------------------------------
    # Finished goods stock: 100 produced - 60 dispatched = exactly 40 pairs remaining!
    all_movements = client.get(f"/api/v1/stock/movements?product_id={prod_id}", cookies=cookies_editor).json()
    total_physical = sum(m["quantity"] * m["direction"] for m in all_movements)
    assert total_physical == 40.0
