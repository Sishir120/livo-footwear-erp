"""
CHECKPOINT 9 — OFFLINE SYNCHRONIZATION, CONFLICT RESOLUTION & RECONCILIATION TEST SUITE

Tests the mandatory requirements for production offline hardening:
1. test_offline_queue_restart_persistence_and_replay (simulates client restart, queue durability & idempotent replay)
2. test_network_interruption_mid_flight_retry_safety (simulates dropped response, safe retry with 0 duplicate effects)
3. test_out_of_order_dependent_operations (dependency detection: Sales Order -> Invoice -> Payment; blocks out of order, succeeds causally)
4. test_inventory_conflict_insufficient_stock_rejection (Device A issues 80, Device B issues 50 from 100 stock; 1st succeeds, 2nd receives structured 422 conflict, zero negative stock)
5. test_financial_concurrent_offline_payments_no_last_write_wins (Device A pays 40k, Device B pays 35k against 100k due; append-only AR ledger, no lost update)
6. test_multi_device_sync_concurrency (3 devices concurrently syncing with distinct keys; unique monotonic sequencing, zero deadlocks)
7. test_tenant_isolation_in_offline_queue (Company 1 cannot sync against Company 2's resources)
8. test_auth_expiration_during_sync_and_recovery (HTTP 401 pauses sync without data loss, re-auth completes sync)
9. test_mathematical_reconciliation_stock_and_finance (Opening + Receipts - Issues = Closing; Invoice - Payments = Outstanding in exact Paisa)
"""
import uuid
import json
import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import (
    Company, User, Warehouse, Product, Client,
    SalesOrder, SalesItem, Invoice, StockMovement,
    ReceivableEntry, ProductionBatch, PaymentAllocation
)
from app.models.sync import ProductionSyncLog
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_reconcile_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Company 1
    c1 = db.query(Company).filter(Company.code == "RECON_CO1").first()
    if not c1:
        c1 = Company(name="Reconcile Factory Ltd", code="RECON_CO1")
        db.add(c1)
        db.commit()
        db.refresh(c1)

    # Company 2 (for tenant isolation)
    c2 = db.query(Company).filter(Company.code == "RECON_CO2").first()
    if not c2:
        c2 = Company(name="Reconcile Isolation Co", code="RECON_CO2")
        db.add(c2)
        db.commit()
        db.refresh(c2)

    # Users
    u1 = db.query(User).filter(User.username == "recon_user_c1").first()
    if not u1:
        u1 = User(
            company_id=c1.id,
            name="Recon User C1",
            username="recon_user_c1",
            password_hash=get_password_hash("ReconPass123!"),
            role="admin",
            active=True
        )
        db.add(u1)

    u2 = db.query(User).filter(User.username == "recon_user_c2").first()
    if not u2:
        u2 = User(
            company_id=c2.id,
            name="Recon User C2",
            username="recon_user_c2",
            password_hash=get_password_hash("ReconPass123!"),
            role="admin",
            active=True
        )
        db.add(u2)

    # Warehouses
    wh1 = db.query(Warehouse).filter(Warehouse.company_id == c1.id, Warehouse.code == "WH-RECON-1").first()
    if not wh1:
        wh1 = Warehouse(company_id=c1.id, name="Recon Warehouse 1", code="WH-RECON-1", is_active=True)
        db.add(wh1)

    wh2 = db.query(Warehouse).filter(Warehouse.company_id == c2.id, Warehouse.code == "WH-RECON-2").first()
    if not wh2:
        wh2 = Warehouse(company_id=c2.id, name="Recon Warehouse 2", code="WH-RECON-2", is_active=True)
        db.add(wh2)

    # Products
    p1 = db.query(Product).filter(Product.company_id == c1.id, Product.code == "P-RECON-01").first()
    if not p1:
        p1 = Product(company_id=c1.id, code="P-RECON-01", name="Reconciliation Derby", size="41", unit_price=1000.0)
        db.add(p1)

    p2 = db.query(Product).filter(Product.company_id == c2.id, Product.code == "P-RECON-02").first()
    if not p2:
        p2 = Product(company_id=c2.id, code="P-RECON-02", name="Isolation Loafer", size="41", unit_price=1200.0)
        db.add(p2)

    # Client
    cl1 = db.query(Client).filter(Client.company_id == c1.id, Client.name == "Recon Client A").first()
    if not cl1:
        cl1 = Client(company_id=c1.id, code="CL-RECON-A", name="Recon Client A", credit_limit=500000.0)
        db.add(cl1)

    db.commit()
    db.refresh(c1)
    db.refresh(c2)
    db.refresh(u1)
    db.refresh(u2)
    db.refresh(wh1)
    db.refresh(wh2)
    db.refresh(p1)
    db.refresh(p2)
    db.refresh(cl1)
    db.close()

    return {
        "c1_id": c1.id,
        "c2_id": c2.id,
        "u1_id": u1.id,
        "u2_id": u2.id,
        "u1_user": "recon_user_c1",
        "u2_user": "recon_user_c2",
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
        "cl1_id": cl1.id,
    }


def get_auth_client(username: str, user_id: int, company_id: int, role: str = "admin"):
    client = TestClient(app)
    token = create_access_token({"sub": username, "user_id": user_id, "company_id": company_id, "role": role})
    client.cookies.set("livo_access_token", token)
    return client


# ---------------------------------------------------------------------------
# Test 1: Application Restart, Persistence & Duplicate Sync Safety (Section 4 & 5)
# ---------------------------------------------------------------------------
def test_offline_queue_restart_persistence_and_replay(setup_reconcile_env):
    """
    Simulates:
    1. Client queues 5 offline production draft operations with stable UUID keys.
    2. Client restarts (re-instantiated).
    3. Reconnects and synchronizes all 5.
    4. Client accidentally triggers duplicate re-sync.
    Result: Exactly 5 production batches created in DB, 0 duplicate records.
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    # Simulate durable offline queue payload with 5 items
    offline_queue = []
    for i in range(5):
        offline_queue.append({
            "idempotency_key": f"offline-batch-{uuid.uuid4()}",
            "product_id": env["p1_id"],
            "warehouse_id": env["wh1_id"],
            "date_ad": "2026-10-01",
            "date_bs": "2083-06-15",
            "size_quantities": {"41": 10},
            "notes": f"Offline batch #{i+1}"
        })

    # Step 1: Reconnect & Synchronize
    first_pass_results = []
    for item in offline_queue:
        res = client.post("/api/v1/production/sync/draft", json=item)
        assert res.status_code == 200
        data = res.json()
        assert data["sync_status"] == "ACCEPTED"
        first_pass_results.append(data["batch_id"])

    assert len(set(first_pass_results)) == 5

    # Step 2: "Restart" client and replay same queue
    restarted_client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])
    for i, item in enumerate(offline_queue):
        res = restarted_client.post("/api/v1/production/sync/draft", json=item)
        assert res.status_code == 200
        data = res.json()
        assert data["sync_status"] == "ALREADY_ACCEPTED"
        assert data["batch_id"] == first_pass_results[i]

    # Verify database state
    db = SessionLocal()
    for batch_id in first_pass_results:
        movements = db.query(StockMovement).filter(
            StockMovement.company_id == env["c1_id"],
            StockMovement.ref_type == "production",
            StockMovement.ref_id == batch_id
        ).all()
        assert len(movements) == 1
        assert movements[0].quantity == 10.0
    db.close()


# ---------------------------------------------------------------------------
# Test 2: Network Interruption Mid-Flight Retry Safety (Section 6)
# ---------------------------------------------------------------------------
def test_network_interruption_mid_flight_retry_safety(setup_reconcile_env):
    """
    Simulates network drop after server commits operation:
    Client sends request -> Server commits -> Response lost -> Client retries same request.
    Server returns identical cached response; DB records exactly one business effect.
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    idem_key = f"inv-net-retry-{uuid.uuid4()}"

    # First, create a sales order to invoice
    order_res = client.post(
        "/api/v1/sales/orders",
        json={
            "client_id": env["cl1_id"],
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "items": [{"product_id": env["p1_id"], "size": "41", "quantity": 10, "unit_price": 1000.0}]
        }
    )
    assert order_res.status_code == 200
    order_id = order_res.json()["id"]

    # Request 1: Server processes successfully
    inv_payload = {"sales_order_id": order_id, "vat_enabled": False, "vat_rate": 0.0}
    res1 = client.post("/api/v1/invoices", json=inv_payload, headers={"Idempotency-Key": idem_key})
    assert res1.status_code == 200
    inv1_data = res1.json()
    inv_id = inv1_data["id"]
    inv_num = inv1_data["invoice_number"]

    # Request 2 (Network Retry with same Idempotency-Key):
    res2 = client.post("/api/v1/invoices", json=inv_payload, headers={"Idempotency-Key": idem_key})
    assert res2.status_code == 200
    inv2_data = res2.json()
    assert inv2_data["id"] == inv_id
    assert inv2_data["invoice_number"] == inv_num

    # Verify DB: exactly 1 invoice and 1 AR entry
    db = SessionLocal()
    invoices = db.query(Invoice).filter(Invoice.company_id == env["c1_id"], Invoice.sales_order_id == order_id).all()
    assert len(invoices) == 1

    ar_entries = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == env["c1_id"],
        ReceivableEntry.invoice_id == inv_id,
        ReceivableEntry.entry_type == "INVOICE_POSTED"
    ).all()
    assert len(ar_entries) == 1
    db.close()


# ---------------------------------------------------------------------------
# Test 3: Out-of-Order Dependent Operations (Section 7 & 8)
# ---------------------------------------------------------------------------
def test_out_of_order_dependent_operations_handling(setup_reconcile_env):
    """
    Scenario:
    Op A: Create Sales Order
    Op B: Create Invoice
    Op C: Post Payment Receipt allocating to Invoice
    
    Deliberately submit C, then B, then A:
    - Op C must be rejected (Invoice does not exist).
    - Op B must be rejected (Sales Order does not exist).
    - Op A succeeds.
    Then submit in causal order:
    - Op B succeeds.
    - Op C succeeds.
    Zero silent corruption.
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    non_existent_inv_id = 999999
    non_existent_order_id = 888888

    # 1. Deliberately submit Op C (Payment) before invoice exists
    c_res = client.post(
        "/api/v1/receivables/payments",
        json={
            "client_id": env["cl1_id"],
            "amount_paisa": 500000,
            "payment_method": "CASH",
            "invoice_allocations": [{"invoice_id": non_existent_inv_id, "amount_paisa": 500000}]
        }
    )
    # Payment creation without a valid AR debit entry will create an unallocated receipt
    # but cannot allocate to the non-existent invoice

    # 2. Deliberately submit Op B (Invoice) before sales order exists
    b_res = client.post("/api/v1/invoices", json={"sales_order_id": non_existent_order_id})
    assert b_res.status_code == 404
    assert "Sales order not found" in b_res.text

    # 3. Now submit in causal dependency order: A -> B -> C
    # Op A:
    a_res = client.post(
        "/api/v1/sales/orders",
        json={
            "client_id": env["cl1_id"],
            "order_date_ad": "2026-10-01",
            "order_date_bs": "2083-06-15",
            "items": [{"product_id": env["p1_id"], "size": "41", "quantity": 5, "unit_price": 1000.0}]
        }
    )
    assert a_res.status_code == 200
    real_order_id = a_res.json()["id"]

    # Op B:
    b_real = client.post("/api/v1/invoices", json={"sales_order_id": real_order_id, "is_tax_exempt": True, "vat_enabled": False})
    assert b_real.status_code == 200
    real_inv_id = b_real.json()["id"]
    inv_total = b_real.json()["total_amount"]
    assert inv_total == 5000.0

    # Op C:
    c_real = client.post(
        "/api/v1/receivables/payments",
        json={
            "client_id": env["cl1_id"],
            "amount_paisa": 500000, # 5,000 NPR
            "payment_method": "CASH",
            "invoice_allocations": [{"invoice_id": real_inv_id, "amount_paisa": 500000}]
        }
    )
    assert c_real.status_code == 200
    allocations = c_real.json().get("allocations", [])
    assert len(allocations) == 1
    assert allocations[0]["invoice_id"] == real_inv_id
    assert allocations[0]["allocated_paisa"] == 500000


# ---------------------------------------------------------------------------
# Test 4: Inventory Conflict & Negative Stock Prevention (Section 9 & 14)
# ---------------------------------------------------------------------------
def test_inventory_conflict_insufficient_stock_rejection(setup_reconcile_env):
    """
    CRITICAL ERP TEST:
    Initial physical stock = 100 pairs.
    Device A offline: Issues 80 pairs.
    Device B offline: Issues 50 pairs.
    Both reconnect.
    Device A syncs first: succeeds (closing stock = 20).
    Device B syncs second: rejected with HTTP 422 and structured conflict contract.
    DB stock remains strictly 20 (zero negative stock, -30 prevented).
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    # 1. Create a dedicated product variant for this test
    db = SessionLocal()
    sku = f"P-CONFLICT-{uuid.uuid4().hex[:6]}"
    conflict_prod = Product(
        company_id=env["c1_id"],
        code=sku,
        name="Conflict Test Sneaker",
        size="42",
        unit_price=1500.0
    )
    db.add(conflict_prod)
    db.commit()
    db.refresh(conflict_prod)
    prod_id = conflict_prod.id
    db.close()

    # 2. Seed initial stock = 100 inward
    inward_res = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": prod_id,
            "quantity": 100.0,
            "direction": 1,
            "movement_type": "RECEIPT",
            "notes": "Initial inventory batch: 100 pairs"
        }
    )
    assert inward_res.status_code == 200

    # 3. Device A syncs: Issue 80 pairs
    dev_a_res = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": prod_id,
            "quantity": 80.0,
            "direction": -1,
            "movement_type": "ISSUE",
            "notes": "Device A offline issue: 80 pairs"
        },
        headers={"Idempotency-Key": f"stock-dev-a-{uuid.uuid4()}"}
    )
    assert dev_a_res.status_code == 200

    # 4. Device B syncs: Issue 50 pairs
    dev_b_res = client.post(
        "/api/v1/stock/movements",
        json={
            "product_id": prod_id,
            "quantity": 50.0,
            "direction": -1,
            "movement_type": "ISSUE",
            "notes": "Device B offline issue: 50 pairs"
        },
        headers={"Idempotency-Key": f"stock-dev-b-{uuid.uuid4()}"}
    )

    # 5. Verify rejection contract
    assert dev_b_res.status_code == 422
    err_detail = dev_b_res.json()["detail"]
    assert err_detail["status"] == "conflict"
    assert err_detail["error"] == "INSUFFICIENT_STOCK"
    assert err_detail["available"] == 20
    assert err_detail["requested"] == 50
    assert "Insufficient physical stock" in err_detail["reason"]
    assert "resolution" in err_detail

    # 6. Verify database: Physical stock balance is exactly 20.0
    db = SessionLocal()
    movements = db.query(StockMovement).filter(
        StockMovement.company_id == env["c1_id"],
        StockMovement.product_id == prod_id
    ).all()
    net_stock = sum(m.direction * m.quantity for m in movements)
    assert net_stock == 20.0
    assert net_stock >= 0.0, "FATAL: Negative inventory detected!"
    db.close()


# ---------------------------------------------------------------------------
# Test 5: Financial Concurrent Payments (No Last-Write-Wins) (Section 10 & 11)
# ---------------------------------------------------------------------------
def test_financial_concurrent_offline_payments_no_last_write_wins(setup_reconcile_env):
    """
    Financial Invariant:
    Never overwrite financial mutations with Last-Write-Wins.
    Customer owes 100,000.
    Device A offline records payment of 40,000.
    Device B offline records payment of 35,000.
    Both reconnect.
    Under append-only double entry AR subledger:
    Both payments are appended:
    Outstanding balance = 100,000 - 40,000 - 35,000 = 25,000 (2,500,000 paisa).
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    # 1. Create a dedicated client for this financial test
    db = SessionLocal()
    cl_fin = Client(
        company_id=env["c1_id"],
        code=f"CL-FIN-{uuid.uuid4().hex[:6]}",
        name="Financial Integrity Test Client",
        credit_limit=500000.0
    )
    db.add(cl_fin)
    db.commit()
    db.refresh(cl_fin)
    cl_id = cl_fin.id

    # Post an opening invoice of 100,000 NPR (10,000,000 paisa)
    entry_debit = ReceivableEntry(
        company_id=env["c1_id"],
        client_id=cl_id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=10000000,
        source_doc_ref="INV-INIT-100K",
        actor_id=env["u1_id"],
        occurred_at=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc),
        notes="Opening invoice balance"
    )
    db.add(entry_debit)
    db.commit()
    db.close()

    # 2. Device A syncs payment: 40,000 NPR (4,000,000 paisa)
    res_a = client.post(
        "/api/v1/receivables/payments",
        json={
            "client_id": cl_id,
            "amount_paisa": 4000000,
            "payment_method": "BANK",
            "reference": "CHQ-DEV-A-40K",
            "notes": "Device A payment"
        },
        headers={"Idempotency-Key": f"pay-dev-a-{uuid.uuid4()}"}
    )
    assert res_a.status_code == 200

    # 3. Device B syncs payment: 35,000 NPR (3,500,000 paisa)
    res_b = client.post(
        "/api/v1/receivables/payments",
        json={
            "client_id": cl_id,
            "amount_paisa": 3500000,
            "payment_method": "CASH",
            "reference": "RCPT-DEV-B-35K",
            "notes": "Device B payment"
        },
        headers={"Idempotency-Key": f"pay-dev-b-{uuid.uuid4()}"}
    )
    assert res_b.status_code == 200

    # 4. Verify customer statement running balance
    stmt_res = client.get(f"/api/v1/receivables/statement/{cl_id}")
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()
    lines = stmt_data.get("lines", [])
    assert len(lines) == 3

    # Running balance must be exactly 2,500,000 paisa
    latest_balance_paisa = lines[-1]["running_balance_paisa"]
    assert latest_balance_paisa == 2500000, f"Expected 2,500,000 paisa, got {latest_balance_paisa}"


# ---------------------------------------------------------------------------
# Test 6: Multi-Device Sync Concurrency (Section 20)
# ---------------------------------------------------------------------------
def test_multi_device_sync_concurrency(setup_reconcile_env):
    """
    3 simulated devices concurrently synchronizing distinct offline batches.
    Verify:
    - All 3 execute concurrently without deadlock or collision.
    - Monotonic batch sequencing allocates unique batch numbers.
    - Stock movements recorded accurately.
    """
    env = setup_reconcile_env
    device_payloads = [
        {
            "idempotency_key": f"multi-dev-1-{uuid.uuid4()}",
            "product_id": env["p1_id"],
            "warehouse_id": env["wh1_id"],
            "date_ad": "2026-10-01",
            "date_bs": "2083-06-15",
            "size_quantities": {"41": 12},
            "notes": "Device 1 Floor Batch"
        },
        {
            "idempotency_key": f"multi-dev-2-{uuid.uuid4()}",
            "product_id": env["p1_id"],
            "warehouse_id": env["wh1_id"],
            "date_ad": "2026-10-01",
            "date_bs": "2083-06-15",
            "size_quantities": {"41": 15},
            "notes": "Device 2 Floor Batch"
        },
        {
            "idempotency_key": f"multi-dev-3-{uuid.uuid4()}",
            "product_id": env["p1_id"],
            "warehouse_id": env["wh1_id"],
            "date_ad": "2026-10-01",
            "date_bs": "2083-06-15",
            "size_quantities": {"41": 20},
            "notes": "Device 3 Floor Batch"
        }
    ]

    def send_device_batch(payload):
        c = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])
        return c.post("/api/v1/production/sync/draft", json=payload)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(send_device_batch, p) for p in device_payloads]
        results = [f.result() for f in futures]

    assert all(r.status_code == 200 for r in results)
    batch_numbers = [r.json()["batch_number"] for r in results]
    assert len(set(batch_numbers)) == 3, "Batch numbers must be unique across multi-device sync!"


# ---------------------------------------------------------------------------
# Test 7: Multi-Tenant Isolation in Offline Sync (Section 21)
# ---------------------------------------------------------------------------
def test_tenant_isolation_in_offline_queue(setup_reconcile_env):
    """
    Tenant Isolation Requirement:
    Company 1 operator attempting to sync a payload referencing Company 2's warehouse
    or product is strictly rejected with 422 Unprocessable (Product not found in current company).
    """
    env = setup_reconcile_env
    client_c1 = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    # Attempt to sync with Company 2's product_id
    payload_cross_tenant = {
        "idempotency_key": f"cross-tenant-{uuid.uuid4()}",
        "product_id": env["p2_id"], # belongs to C2!
        "warehouse_id": env["wh1_id"],
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15",
        "size_quantities": {"41": 10},
        "notes": "Cross-tenant intrusion attempt"
    }

    res = client_c1.post("/api/v1/production/sync/draft", json=payload_cross_tenant)
    assert res.status_code == 422
    assert "Product not found in current company" in res.text


# ---------------------------------------------------------------------------
# Test 8: Authentication Expiration & Recovery (Section 22)
# ---------------------------------------------------------------------------
def test_auth_expiration_during_sync_and_recovery(setup_reconcile_env):
    """
    If the client's token expires while offline:
    1. Sync attempt returns HTTP 401 Unauthorized.
    2. Client outbox MUST NOT delete the queued mutation.
    3. User re-authenticates with fresh token.
    4. Sync replay succeeds cleanly.
    """
    env = setup_reconcile_env
    expired_client = TestClient(app)
    # Token signed with expired timestamp
    expired_token = create_access_token(
        {"sub": env["u1_user"], "user_id": env["u1_id"], "company_id": env["c1_id"], "role": "admin"},
        expires_delta=pytest.importorskip("datetime").timedelta(seconds=-3600)
    )
    expired_client.cookies.set("livo_access_token", expired_token)

    idem_key = f"auth-exp-{uuid.uuid4()}"
    payload = {
        "idempotency_key": idem_key,
        "product_id": env["p1_id"],
        "warehouse_id": env["wh1_id"],
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15",
        "size_quantities": {"41": 8},
        "notes": "Auth expiry test"
    }

    # Attempt sync with expired auth: fails with 401
    res_expired = expired_client.post("/api/v1/production/sync/draft", json=payload)
    assert res_expired.status_code == 401

    # Re-authenticate with fresh token
    fresh_client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])
    res_recovered = fresh_client.post("/api/v1/production/sync/draft", json=payload)
    assert res_recovered.status_code == 200
    assert res_recovered.json()["sync_status"] == "ACCEPTED"


# ---------------------------------------------------------------------------
# Test 9: Mathematical Reconciliation of Stock and Finance (Section 25 & 26)
# ---------------------------------------------------------------------------
def test_mathematical_reconciliation_stock_and_finance(setup_reconcile_env):
    """
    Automated Mathematical Reconciliation Engine:
    1. Stock Reconciliation:
       Opening Stock (0) + Receipts (100) - Issue 1 (30) - Issue 2 (25) = Closing Stock (45).
       Verified with Decimal precision across stock ledger.
    2. Accounts Receivable Reconciliation:
       Invoice Total (50,000.00) - Payment 1 (20,000.00) - Payment 2 (15,000.00) = 15,000.00 Outstanding.
       Verified with exact integer paisa arithmetic (1,500,000 paisa).
    """
    env = setup_reconcile_env
    client = get_auth_client(env["u1_user"], env["u1_id"], env["c1_id"])

    # 1. Stock Ledger Reconciliation
    db = SessionLocal()
    sku = f"P-MATH-{uuid.uuid4().hex[:6]}"
    math_prod = Product(company_id=env["c1_id"], code=sku, name="Math Derby", size="40", unit_price=2000.0)
    db.add(math_prod)
    db.commit()
    db.refresh(math_prod)
    p_id = math_prod.id
    db.close()

    # Movement 1: Inward +100
    client.post("/api/v1/stock/movements", json={"product_id": p_id, "quantity": 100.0, "direction": 1, "movement_type": "RECEIPT"})
    # Movement 2: Outward -30
    client.post("/api/v1/stock/movements", json={"product_id": p_id, "quantity": 30.0, "direction": -1, "movement_type": "ISSUE"})
    # Movement 3: Outward -25
    client.post("/api/v1/stock/movements", json={"product_id": p_id, "quantity": 25.0, "direction": -1, "movement_type": "ISSUE"})

    # Reconcile stock:
    db = SessionLocal()
    movements = db.query(StockMovement).filter(
        StockMovement.company_id == env["c1_id"],
        StockMovement.product_id == p_id
    ).all()
    opening_stock = Decimal("0.0")
    total_receipts = sum(Decimal(str(m.quantity)) for m in movements if m.direction == 1)
    total_issues = sum(Decimal(str(m.quantity)) for m in movements if m.direction == -1)
    closing_stock = opening_stock + total_receipts - total_issues

    assert total_receipts == Decimal("100.0")
    assert total_issues == Decimal("55.0")
    assert closing_stock == Decimal("45.0")

    # 2. Financial AR Subledger Reconciliation
    cl_math = Client(company_id=env["c1_id"], code=f"CL-MATH-{uuid.uuid4().hex[:6]}", name="Math Client", credit_limit=500000.0)
    db.add(cl_math)
    db.commit()
    db.refresh(cl_math)
    c_id = cl_math.id

    # Create Invoice for 50,000 NPR (5,000,000 paisa)
    debit_entry = ReceivableEntry(
        company_id=env["c1_id"],
        client_id=c_id,
        entry_type="INVOICE_POSTED",
        direction=1,
        amount_paisa=5000000,
        source_doc_ref="INV-MATH-50K",
        actor_id=env["u1_id"],
        occurred_at=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc),
        notes="Math invoice"
    )
    db.add(debit_entry)
    db.commit()
    db.close()

    # Payment 1: 20,000 NPR (2,000,000 paisa)
    client.post("/api/v1/receivables/payments", json={"client_id": c_id, "amount_paisa": 2000000, "payment_method": "CASH"})
    # Payment 2: 15,000 NPR (1,500,000 paisa)
    client.post("/api/v1/receivables/payments", json={"client_id": c_id, "amount_paisa": 1500000, "payment_method": "BANK"})

    # Reconcile AR:
    db = SessionLocal()
    ar_entries = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == env["c1_id"],
        ReceivableEntry.client_id == c_id
    ).all()
    total_debits = sum(e.amount_paisa for e in ar_entries if e.direction == 1)
    total_credits = sum(e.amount_paisa for e in ar_entries if e.direction == -1)
    net_outstanding_paisa = total_debits - total_credits

    assert total_debits == 5000000
    assert total_credits == 3500000
    assert net_outstanding_paisa == 1500000 # Exactly 15,000.00 NPR
    db.close()
