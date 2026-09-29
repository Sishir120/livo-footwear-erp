import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, Client, SalesOrder, SalesItem, Invoice
from app.models.receivable import ReceivableEntry, PaymentAllocation
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_ar_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create Company
    comp = db.query(Company).filter(Company.code == "AR_TEST_CO").first()
    if not comp:
        comp = Company(name="AR Test Footwear Ltd", code="AR_TEST_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Warehouse
    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id).first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="AR Main Depot", code="WH-AR", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    # Editor user
    editor = db.query(User).filter(User.username == "ar_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="AR Editor",
            username="ar_editor",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    # Viewer user
    viewer = db.query(User).filter(User.username == "ar_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="AR Viewer",
            username="ar_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    # Product
    prod = db.query(Product).filter(Product.company_id == comp.id, Product.code == "AR-P01").first()
    if not prod:
        prod = Product(
            company_id=comp.id,
            code="AR-P01",
            name="AR Sneaker 40",
            category="Footwear",
            size="40",
            color="Black",
            unit_price=1200.0
        )
        db.add(prod)

    # Client
    client = db.query(Client).filter(Client.company_id == comp.id, Client.code == "CLI-AR-01").first()
    if not client:
        client = Client(
            company_id=comp.id,
            code="CLI-AR-01",
            name="Himalayan Footwear Distributors",
            contact_person="Ramesh Shrestha",
            phone="9841000000",
            credit_limit=50000.0
        )
        db.add(client)

    db.commit()
    db.refresh(comp)
    db.refresh(editor)
    db.refresh(viewer)
    db.refresh(prod)
    db.refresh(client)
    db.close()

    return {
        "company_id": comp.id,
        "editor_username": "ar_editor",
        "viewer_username": "ar_viewer",
        "client_id": client.id,
        "product_id": prod.id
    }


def login_user(client: TestClient, username: str, password: str = "EditorPass123!"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.json().get("access_token")
    if token:
        client.cookies.set(COOKIE_NAME, token)
    for k, v in resp.cookies.items():
        client.cookies.set(k, v)
    return client


def test_invoice_issuance_writes_matching_ar_entry(setup_ar_env):
    """Verify that posting a sales invoice writes a corresponding INVOICE_POSTED entry in receivable_entries."""
    client = TestClient(app)
    login_user(client, setup_ar_env["editor_username"], "EditorPass123!")

    # 1. Create a sales order
    order_payload = {
        "order_number": f"ORD-AR-{int(datetime.now().timestamp())}",
        "client_id": setup_ar_env["client_id"],
        "order_date_ad": "2026-09-28",
        "order_date_bs": "2083-06-12",
        "received_amount": 0.0,
        "delivered": False,
        "items": [
            {
                "product_id": setup_ar_env["product_id"],
                "quantity": 5.0,
                "unit_price": 1200.0
            }
        ]
    }
    ord_resp = client.post("/api/v1/sales/orders", json=order_payload)
    assert ord_resp.status_code == 200
    order_data = ord_resp.json()
    order_id = order_data["id"]

    # 2. Issue tax invoice
    inv_payload = {
        "sales_order_id": order_id,
        "vat_enabled": True,
        "vat_rate": 13.0
    }
    inv_resp = client.post("/api/v1/invoices", json=inv_payload)
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()
    invoice_id = inv_data["id"]
    invoice_num = inv_data["invoice_number"]
    total_amount = inv_data["total_amount"]
    expected_paisa = int(round(total_amount * 100))

    # 3. Verify receivable_entries contains matching record
    db = SessionLocal()
    entry = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == setup_ar_env["company_id"],
        ReceivableEntry.invoice_id == invoice_id,
        ReceivableEntry.entry_type == "INVOICE_POSTED"
    ).first()

    assert entry is not None
    assert entry.direction == 1
    assert entry.amount_paisa == expected_paisa
    assert entry.source_doc_ref == invoice_num
    assert entry.client_id == setup_ar_env["client_id"]
    assert entry.due_date is not None
    db.close()


def test_partial_payments_decrement_outstanding_balance(setup_ar_env):
    """Verify that posting a partial payment decrements party balance and preserves allocation links."""
    client = TestClient(app)
    login_user(client, setup_ar_env["editor_username"], "EditorPass123!")

    # Find the invoice created in previous test
    db = SessionLocal()
    inv_entry = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == setup_ar_env["company_id"],
        ReceivableEntry.client_id == setup_ar_env["client_id"],
        ReceivableEntry.entry_type == "INVOICE_POSTED"
    ).order_by(ReceivableEntry.id.desc()).first()
    assert inv_entry is not None
    invoice_id = inv_entry.invoice_id
    total_paisa = inv_entry.amount_paisa
    db.close()

    # Pay 40% of the invoice as partial payment
    partial_payment_paisa = int(total_paisa * 0.4)
    payment_payload = {
        "client_id": setup_ar_env["client_id"],
        "amount_paisa": partial_payment_paisa,
        "payment_method": "BANK",
        "reference": "CHQ-990812",
        "notes": "Partial settlement cheque",
        "invoice_allocations": [
            {
                "invoice_id": invoice_id,
                "amount_paisa": partial_payment_paisa
            }
        ]
    }

    pay_resp = client.post("/api/v1/receivables/payments", json=payment_payload)
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["amount_paisa"] == partial_payment_paisa
    assert len(pay_data["allocations"]) == 1
    assert pay_data["allocations"][0]["invoice_id"] == invoice_id
    assert pay_data["allocations"][0]["allocated_paisa"] == partial_payment_paisa

    # Check statement reflects remaining balance
    stmt_resp = client.get(f"/api/v1/receivables/statement/{setup_ar_env['client_id']}")
    assert stmt_resp.status_code == 200
    stmt = stmt_resp.json()
    assert stmt["summary"]["total_credit_paisa"] >= partial_payment_paisa
    assert stmt["summary"]["net_balance_paisa"] == stmt["summary"]["total_debit_paisa"] - stmt["summary"]["total_credit_paisa"]


def test_disputed_invoices_flagged_without_altering_balance_math(setup_ar_env):
    """Verify that flagging an entry as disputed does not alter running ledger balance math."""
    client = TestClient(app)
    login_user(client, setup_ar_env["editor_username"], "EditorPass123!")

    # Fetch latest invoice entry
    db = SessionLocal()
    entry = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == setup_ar_env["company_id"],
        ReceivableEntry.client_id == setup_ar_env["client_id"],
        ReceivableEntry.entry_type == "INVOICE_POSTED"
    ).first()
    assert entry is not None
    entry_id = entry.id
    db.close()

    # Get statement balance before dispute
    stmt1 = client.get(f"/api/v1/receivables/statement/{setup_ar_env['client_id']}").json()
    balance_before = stmt1["summary"]["net_balance_paisa"]

    # Toggle dispute to True
    disp_resp = client.post(
        f"/api/v1/receivables/dispute/{entry_id}",
        json={"is_disputed": True, "dispute_notes": "Rate mismatch on line 1 under review"}
    )
    assert disp_resp.status_code == 200
    disp_data = disp_resp.json()
    assert disp_data["is_disputed"] is True
    assert disp_data["dispute_notes"] == "Rate mismatch on line 1 under review"

    # Verify statement balance is still identical
    stmt2 = client.get(f"/api/v1/receivables/statement/{setup_ar_env['client_id']}").json()
    assert stmt2["summary"]["net_balance_paisa"] == balance_before


def test_viewer_role_receives_403_on_payment_posting(setup_ar_env):
    """Verify that user with viewer role is strictly blocked (HTTP 403) from posting payments."""
    client = TestClient(app)
    login_user(client, setup_ar_env["viewer_username"], "ViewerPass123!")

    payment_payload = {
        "client_id": setup_ar_env["client_id"],
        "amount_paisa": 100000,
        "payment_method": "CASH",
        "reference": "CASH-FAIL"
    }
    resp = client.post("/api/v1/receivables/payments", json=payment_payload)
    assert resp.status_code == 403


def test_aging_buckets_split_correctly_based_on_as_of_date(setup_ar_env):
    """Verify that aging report splits debts into statutory buckets (current, 31-60, 61-90, 90+) based on as_of_date."""
    client = TestClient(app)
    login_user(client, setup_ar_env["editor_username"], "EditorPass123!")

    db = SessionLocal()
    # Create a fresh client for pure bucket testing
    aging_client = Client(
        company_id=setup_ar_env["company_id"],
        code=f"CLI-AGING-{int(datetime.now().timestamp())}",
        name="Aging Matrix Test Client",
        credit_limit=200000.0
    )
    db.add(aging_client)
    db.commit()
    db.refresh(aging_client)

    eval_date = datetime(2026, 9, 30, tzinfo=timezone.utc)

    # 1. Current entry: due 2026-09-25 (5 days overdue -> current bucket <= 30)
    e_current = ReceivableEntry(
        company_id=setup_ar_env["company_id"],
        client_id=aging_client.id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=10000,
        source_doc_ref="INV-CURR",
        actor_id=1,
        occurred_at=eval_date - timedelta(days=20),
        due_date=eval_date - timedelta(days=5)
    )
    # 2. 31-60 days overdue: due 45 days ago
    e_31_60 = ReceivableEntry(
        company_id=setup_ar_env["company_id"],
        client_id=aging_client.id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=20000,
        source_doc_ref="INV-31-60",
        actor_id=1,
        occurred_at=eval_date - timedelta(days=75),
        due_date=eval_date - timedelta(days=45)
    )
    # 3. 61-90 days overdue: due 75 days ago
    e_61_90 = ReceivableEntry(
        company_id=setup_ar_env["company_id"],
        client_id=aging_client.id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=30000,
        source_doc_ref="INV-61-90",
        actor_id=1,
        occurred_at=eval_date - timedelta(days=105),
        due_date=eval_date - timedelta(days=75)
    )
    # 4. Over 90 days overdue: due 120 days ago
    e_over_90 = ReceivableEntry(
        company_id=setup_ar_env["company_id"],
        client_id=aging_client.id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=40000,
        source_doc_ref="INV-OVER-90",
        actor_id=1,
        occurred_at=eval_date - timedelta(days=150),
        due_date=eval_date - timedelta(days=120)
    )

    db.add_all([e_current, e_31_60, e_61_90, e_over_90])
    db.commit()
    db.close()

    # Fetch aging report as of 2026-09-30
    resp = client.get("/api/v1/receivables/aging?as_of_date=2026-09-30")
    assert resp.status_code == 200
    data = resp.json()

    # Find aging_client row
    party = next((p for p in data["items"] if p["client_id"] == aging_client.id), None)
    assert party is not None
    assert party["current_paisa"] == 10000
    assert party["days_31_60_paisa"] == 20000
    assert party["days_61_90_paisa"] == 30000
    assert party["over_90_paisa"] == 40000
    assert party["total_due_paisa"] == 100000


def test_credit_dispatch_safeguard(setup_ar_env):
    """Verify that sales order exceeding customer credit limit is blocked with 422 unless overridden."""
    client = TestClient(app)
    login_user(client, setup_ar_env["editor_username"], "EditorPass123!")

    db = SessionLocal()
    # Client with 10,000 NPR credit limit (1,000,000 paisa)
    tight_client = Client(
        company_id=setup_ar_env["company_id"],
        code=f"CLI-TIGHT-{int(datetime.now().timestamp())}",
        name="Tight Credit Client",
        credit_limit=10000.0
    )
    db.add(tight_client)
    db.commit()
    db.refresh(tight_client)
    db.close()

    # Order total: 10 pairs @ 1200 = 12,000 NPR (> 10,000 NPR credit limit)
    over_payload = {
        "order_number": f"ORD-OVER-{int(datetime.now().timestamp())}",
        "client_id": tight_client.id,
        "order_date_ad": "2026-09-28",
        "order_date_bs": "2083-06-12",
        "received_amount": 0.0,
        "delivered": False,
        "items": [
            {
                "product_id": setup_ar_env["product_id"],
                "quantity": 10.0,
                "unit_price": 1200.0
            }
        ],
        "supervisor_override": False
    }

    # Should be rejected with 422
    resp = client.post("/api/v1/sales/orders", json=over_payload)
    assert resp.status_code == 422
    assert "Credit limit exceeded - supervisor override required" in resp.json()["detail"]

    # When supervisor_override is True, order succeeds
    over_payload["supervisor_override"] = True
    over_payload["order_number"] = f"ORD-OVER-OK-{int(datetime.now().timestamp())}"
    resp_ok = client.post("/api/v1/sales/orders", json=over_payload)
    assert resp_ok.status_code == 200
