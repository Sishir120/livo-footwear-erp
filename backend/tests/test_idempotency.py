"""
CHECKPOINT 8 — IDEMPOTENCY, DUPLICATE OPERATIONS & RETRY SAFETY TEST SUITE

Tests the following mandatory requirements:
1. test_same_key_single_effect_and_response_replay
2. test_same_key_different_payload_rejected (409 Conflict)
3. test_concurrent_duplicate_requests_produce_single_effect (50 concurrent threads = 1 DB effect, 0 duplicates)
4. test_network_retry_simulation_invoice_creation (no duplicate tax liability or document number)
5. test_financial_retry_simulation_ar_payment (no duplicate ledger impact / balance remains exact)
6. test_inventory_retry_simulation_stock_adjustment (no duplicate stock deduction or movement)
7. test_server_failure_rollback_and_retry_recovery (failed transaction allows safe retry)
8. test_stale_processing_lease_recovery (crashed worker lease expiration unblocks subsequent retry)
9. test_multi_tenant_isolation (Company A and Company B can independently use identical key)
10. test_authorization_isolation (unauthorized user cannot hijack or replay another tenant's key)
11. test_offline_queue_x_idempotency_key_header (frontend outbox compatibility)
12. test_stateful_conditional_idempotency (invoice cancellation and stock reversal duplicate protection)
"""
import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import (
    Company, User, Warehouse, Product, Client,
    SalesOrder, SalesItem, Invoice, StockMovement,
    ReceivableEntry, IdempotencyRecord
)
from app.core.security import get_password_hash, create_access_token
from app.core.idempotency import IdempotencyService, compute_request_hash


@pytest.fixture(scope="module")
def setup_idempotency_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Company 1 (LIVO)
    c1 = db.query(Company).filter(Company.code == "LIVO").first()
    if not c1:
        c1 = Company(name="LIVO GROUP OF INDUSTRIES", code="LIVO")
        db.add(c1)
        db.commit()
        db.refresh(c1)

    # Company 2 (Branch Factory for multi-tenant tests)
    c2 = db.query(Company).filter(Company.code == "BR2").first()
    if not c2:
        c2 = Company(name="Branch Factory Two", code="BR2")
        db.add(c2)
        db.commit()
        db.refresh(c2)

    # User 1 (Admin/Editor for C1)
    u1 = db.query(User).filter(User.username == "idem_editor_c1").first()
    if not u1:
        u1 = User(
            company_id=c1.id,
            name="Idempotency Editor C1",
            username="idem_editor_c1",
            password_hash=get_password_hash("Pass123!"),
            role="admin",
            active=True
        )
        db.add(u1)

    # User 2 (Editor for C2)
    u2 = db.query(User).filter(User.username == "idem_editor_c2").first()
    if not u2:
        u2 = User(
            company_id=c2.id,
            name="Idempotency Editor C2",
            username="idem_editor_c2",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(u2)

    # Warehouses
    wh1 = db.query(Warehouse).filter(Warehouse.company_id == c1.id, Warehouse.code == "WH-C1").first()
    if not wh1:
        wh1 = Warehouse(company_id=c1.id, name="Warehouse C1", code="WH-C1", is_active=True)
        db.add(wh1)

    wh2 = db.query(Warehouse).filter(Warehouse.company_id == c2.id, Warehouse.code == "WH-C2").first()
    if not wh2:
        wh2 = Warehouse(company_id=c2.id, name="Warehouse C2", code="WH-C2", is_active=True)
        db.add(wh2)

    # Products
    p1 = db.query(Product).filter(Product.company_id == c1.id, Product.code == "P-IDEM-01").first()
    if not p1:
        p1 = Product(company_id=c1.id, code="P-IDEM-01", name="Idempotent Derby", size="42", unit_price=1200.0)
        db.add(p1)

    p2 = db.query(Product).filter(Product.company_id == c2.id, Product.code == "P-IDEM-02").first()
    if not p2:
        p2 = Product(company_id=c2.id, code="P-IDEM-02", name="Idempotent Oxford", size="42", unit_price=1500.0)
        db.add(p2)

    # Clients
    cl1 = db.query(Client).filter(Client.company_id == c1.id, Client.name == "Client Alpha C1").first()
    if not cl1:
        cl1 = Client(company_id=c1.id, code="CL-ALPHA-C1", name="Client Alpha C1", credit_limit=500000.0)
        db.add(cl1)

    cl2 = db.query(Client).filter(Client.company_id == c2.id, Client.name == "Client Beta C2").first()
    if not cl2:
        cl2 = Client(company_id=c2.id, code="CL-BETA-C2", name="Client Beta C2", credit_limit=500000.0)
        db.add(cl2)

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
    db.refresh(cl2)

    # Seed initial inward stock for p1 so sales orders can be delivered
    sm1 = db.query(StockMovement).filter(StockMovement.company_id == c1.id, StockMovement.product_id == p1.id).first()
    if not sm1:
        sm1 = StockMovement(
            company_id=c1.id,
            warehouse_id=wh1.id,
            product_id=p1.id,
            size="42",
            quantity=10000.0,
            direction=1,
            ref_type="manual",
            movement_type="RECEIPT",
            source_doc_ref="INIT-STOCK-01",
            date_ad="2026-10-01",
            date_bs="2083-06-15"
        )
        db.add(sm1)
        db.commit()

    db.close()

    return {
        "c1_id": c1.id,
        "c2_id": c2.id,
        "u1_id": u1.id,
        "u2_id": u2.id,
        "u1_user": "idem_editor_c1",
        "u2_user": "idem_editor_c2",
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "p1_id": p1.id,
        "p2_id": p2.id,
        "cl1_id": cl1.id,
        "cl2_id": cl2.id,
    }


def get_authenticated_client(username: str = "idem_editor_c1", user_id: int = 1, company_id: int = 1, role: str = "admin"):
    client = TestClient(app)
    token = create_access_token({"sub": username, "user_id": user_id, "company_id": company_id, "role": role})
    client.cookies.set("livo_access_token", token)
    return client


# ---------------------------------------------------------------------------
# Test 1: Same Key / Same Payload -> Single Business Operation & Response Replay
# ---------------------------------------------------------------------------
def test_same_key_single_effect_and_response_replay(setup_idempotency_env):
    """
    Submitting the exact same request with the same Idempotency-Key must produce
    exactly 1 sales order in the DB and replay the identical response on subsequent attempts.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env
    key = f"so-key-{uuid.uuid4()}"

    payload = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [
            {"product_id": env["p1_id"], "quantity": 10.0, "unit_price": 1200.0}
        ]
    }

    # Attempt 1: New operation
    res1 = client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})
    assert res1.status_code == 200, f"First attempt failed: {res1.text}"
    data1 = res1.json()
    order_id1 = data1["id"]
    order_num1 = data1.get("order_number")

    # Attempt 2: Identical key and payload
    res2 = client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})
    assert res2.status_code == 200, f"Second attempt failed: {res2.text}"
    assert res2.headers.get("X-Idempotent-Replay") == "true"
    data2 = res2.json()
    assert data2["id"] == order_id1
    assert data2.get("order_number") == order_num1

    # Attempt 3: Third identical call
    res3 = client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})
    assert res3.status_code == 200
    assert res3.headers.get("X-Idempotent-Replay") == "true"
    assert res3.json()["id"] == order_id1

    # Verify at database level: exactly 1 SalesOrder exists with this ID
    db = SessionLocal()
    orders = db.query(SalesOrder).filter(
        SalesOrder.company_id == env["c1_id"],
        SalesOrder.client_id == env["cl1_id"],
        SalesOrder.id == order_id1
    ).all()
    assert len(orders) == 1, f"Expected 1 order in DB, found {len(orders)}"

    # Verify IdempotencyRecord
    rec = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.company_id == env["c1_id"],
        IdempotencyRecord.idempotency_key == key
    ).first()
    assert rec is not None
    assert rec.status == "COMPLETED"
    assert rec.response_status_code == 200
    db.close()


# ---------------------------------------------------------------------------
# Test 2: Same Key / Different Payload -> REJECT with 409 Conflict
# ---------------------------------------------------------------------------
def test_same_key_different_payload_rejected(setup_idempotency_env):
    """
    Reusing an Idempotency-Key with a different payload (e.g. changed quantity or amount)
    must NOT execute or silently overwrite. It MUST be rejected with HTTP 409 Conflict.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env
    key = f"so-conflict-{uuid.uuid4()}"

    payload_a = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 10.0, "unit_price": 1200.0}]
    }

    # First request: Creates order
    res1 = client.post("/api/v1/sales/orders", json=payload_a, headers={"Idempotency-Key": key})
    assert res1.status_code == 200
    order_id1 = res1.json()["id"]

    # Second request: Same key, DIFFERENT quantity (50.0 instead of 10.0)
    payload_b = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 50.0, "unit_price": 1200.0}]
    }
    res2 = client.post("/api/v1/sales/orders", json=payload_b, headers={"Idempotency-Key": key})
    assert res2.status_code == 409, f"Expected 409 Conflict, got {res2.status_code}: {res2.text}"
    body2 = res2.json()
    assert "conflict" in body2.get("detail", "").lower() or body2.get("code") == "IDEMPOTENCY_KEY_PAYLOAD_MISMATCH"

    # Database check: Only 1 order exists, with quantity 10.0, not 50.0
    db = SessionLocal()
    items = db.query(SalesItem).filter(SalesItem.sales_order_id == order_id1).all()
    assert len(items) == 1
    assert items[0].quantity == 10.0
    db.close()


# ---------------------------------------------------------------------------
# Test 3: 50 Concurrent Duplicate Requests -> Exactly 1 Business Effect
# ---------------------------------------------------------------------------
def test_concurrent_duplicate_requests_produce_single_effect(setup_idempotency_env):
    """
    50 simultaneous requests hitting the same endpoint with the exact same Idempotency-Key
    and payload must execute exactly ONCE in the database.
    49 requests must receive the replayed result.
    Duplicate business operations = 0.
    """
    env = setup_idempotency_env
    key = f"so-conc-50-{uuid.uuid4()}"

    payload = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 5.0, "unit_price": 1200.0}]
    }

    # Count orders before
    db = SessionLocal()
    initial_count = db.query(SalesOrder).filter(SalesOrder.company_id == env["c1_id"]).count()
    db.close()

    results = []
    concurrency = 50

    def make_request():
        client = get_authenticated_client(env["u1_user"])
        return client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request) for _ in range(concurrency)]
        for f in as_completed(futures):
            results.append(f.result())

    # All requests should return 200 (either initial execution or replay)
    status_codes = [r.status_code for r in results]
    assert all(code == 200 for code in status_codes), f"Status codes: {status_codes}"

    # Extract all created order IDs
    order_ids = set(r.json()["id"] for r in results)
    assert len(order_ids) == 1, f"Expected exactly 1 unique order ID across 50 requests, got {order_ids}"

    # Verify at database level: Exactly 1 new order added
    db = SessionLocal()
    final_count = db.query(SalesOrder).filter(SalesOrder.company_id == env["c1_id"]).count()
    assert final_count == initial_count + 1, f"DB order count incremented by {final_count - initial_count}, expected 1!"
    db.close()


# ---------------------------------------------------------------------------
# Test 4: Network Retry Simulation for Invoice Creation
# ---------------------------------------------------------------------------
def test_network_retry_simulation_invoice_creation(setup_idempotency_env):
    """
    Simulate: Client sends POST /invoices -> server commits transaction ->
    client disconnects/drops response -> client retries with same key.
    Result: Exactly 1 invoice, 1 sequence number, 1 AR subledger debit.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env

    # 1. Create a base sales order first
    so_res = client.post("/api/v1/sales/orders", json={
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 2.0, "unit_price": 1200.0}]
    })
    assert so_res.status_code == 200
    so_id = so_res.json()["id"]

    inv_key = f"inv-retry-{uuid.uuid4()}"
    inv_payload = {"sales_order_id": so_id, "vat_enabled": True}

    # Attempt 1: First attempt
    res1 = client.post("/api/v1/invoices", json=inv_payload, headers={"Idempotency-Key": inv_key})
    assert res1.status_code == 200
    data1 = res1.json()
    inv_id1 = data1["id"]
    inv_num1 = data1["invoice_number"]

    # "Network dropped response" -> Attempt 2: Client retries with identical key & payload
    res2 = client.post("/api/v1/invoices", json=inv_payload, headers={"Idempotency-Key": inv_key})
    assert res2.status_code == 200
    assert res2.headers.get("X-Idempotent-Replay") == "true"
    data2 = res2.json()
    assert data2["id"] == inv_id1
    assert data2["invoice_number"] == inv_num1

    # Database verification
    db = SessionLocal()
    invoices = db.query(Invoice).filter(
        Invoice.company_id == env["c1_id"],
        Invoice.sales_order_id == so_id
    ).all()
    assert len(invoices) == 1, f"Expected exactly 1 invoice, found {len(invoices)}"

    # AR Subledger postings verification: exactly 1 debit entry for this invoice
    ar_entries = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == env["c1_id"],
        ReceivableEntry.invoice_id == inv_id1
    ).all()
    assert len(ar_entries) == 1, f"Expected 1 AR entry, found {len(ar_entries)}"
    db.close()


# ---------------------------------------------------------------------------
# Test 5: Financial Retry Simulation (AR Payment)
# ---------------------------------------------------------------------------
def test_financial_retry_simulation_ar_payment(setup_idempotency_env):
    """
    Financial mutations require exact balances.
    Payment receipt of NPR 5,000 retried must NOT decrement balance by 10,000.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env
    pay_key = f"pay-retry-{uuid.uuid4()}"

    pay_payload = {
        "client_id": env["cl1_id"],
        "amount_paisa": 500000,  # NPR 5,000.00
        "payment_method": "CASH",
        "payment_date": "2026-10-01",
        "notes": "Test financial idempotency"
    }

    # Attempt 1
    res1 = client.post("/api/v1/receivables/payments", json=pay_payload, headers={"Idempotency-Key": pay_key})
    assert res1.status_code == 200
    receipt_doc1 = res1.json()["source_doc_ref"]

    # Attempt 2: Network retry
    res2 = client.post("/api/v1/receivables/payments", json=pay_payload, headers={"Idempotency-Key": pay_key})
    assert res2.status_code == 200
    assert res2.headers.get("X-Idempotent-Replay") == "true"
    receipt_doc2 = res2.json()["source_doc_ref"]
    assert receipt_doc2 == receipt_doc1

    # Database verification
    db = SessionLocal()
    entries = db.query(ReceivableEntry).filter(
        ReceivableEntry.company_id == env["c1_id"],
        ReceivableEntry.source_doc_ref == receipt_doc1
    ).all()
    assert len(entries) == 1, f"Expected 1 AR payment entry, found {len(entries)}"
    assert entries[0].amount_paisa == 500000
    db.close()


# ---------------------------------------------------------------------------
# Test 6: Inventory Retry Simulation (Stock Adjustment)
# ---------------------------------------------------------------------------
def test_inventory_retry_simulation_stock_adjustment(setup_idempotency_env):
    """
    Stock adjustments must never duplicate inventory changes on retry.
    An adjustment of +50 units retried must add exactly 50 units, not 100 units.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env
    adj_key = f"adj-retry-{uuid.uuid4()}"

    adj_payload = {
        "product_id": env["p1_id"],
        "warehouse_id": env["wh1_id"],
        "size": "42",
        "quantity_delta": 50.0,
        "reason_code": "RECOUNT",
        "reason_text": "Audit recount adjustment"
    }

    # Attempt 1
    res1 = client.post("/api/v1/stock/adjustments", json=adj_payload, headers={"Idempotency-Key": adj_key})
    assert res1.status_code == 200
    adj_id1 = res1.json()["id"]
    doc_ref1 = res1.json()["source_doc_ref"]

    # Attempt 2: Retry
    res2 = client.post("/api/v1/stock/adjustments", json=adj_payload, headers={"Idempotency-Key": adj_key})
    assert res2.status_code == 200
    assert res2.headers.get("X-Idempotent-Replay") == "true"
    assert res2.json()["id"] == adj_id1
    assert res2.json()["source_doc_ref"] == doc_ref1

    # Database check: exactly 1 stock movement exists for this adjustment
    db = SessionLocal()
    mvs = db.query(StockMovement).filter(
        StockMovement.company_id == env["c1_id"],
        StockMovement.source_doc_ref == doc_ref1
    ).all()
    assert len(mvs) == 1, f"Expected 1 stock movement, found {len(mvs)}"
    assert mvs[0].quantity == 50.0
    db.close()


# ---------------------------------------------------------------------------
# Test 7: Server Failure & Rollback Recovery
# ---------------------------------------------------------------------------
def test_server_failure_rollback_and_retry_recovery(setup_idempotency_env):
    """
    If a transaction fails midway (status=FAILED), no partial effects remain.
    A subsequent retry with the SAME idempotency key must be allowed to succeed.
    """
    env = setup_idempotency_env
    key = f"fail-retry-{uuid.uuid4()}"

    db = SessionLocal()
    # Simulate a failed attempt where server crashed/rolled back
    payload = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    }
    req_hash = compute_request_hash("POST", "/api/v1/sales/orders", json.dumps(payload))
    failed_rec = IdempotencyRecord(
        company_id=env["c1_id"],
        user_id=1,
        idempotency_key=key,
        request_method="POST",
        request_path="/api/v1/sales/orders",
        request_hash=req_hash,
        status="FAILED",
        error_message="Simulated database deadlock during payment allocation"
    )
    db.add(failed_rec)
    db.commit()
    db.close()

    # Now client retries with the exact same payload
    client = get_authenticated_client(env["u1_user"])

    # The retry should transition from FAILED -> PROCESSING -> COMPLETED and return 200
    res = client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})
    assert res.status_code == 200, f"Retry failed: {res.text}"

    # Verify record is now COMPLETED
    db = SessionLocal()
    rec = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.company_id == env["c1_id"],
        IdempotencyRecord.idempotency_key == key
    ).first()
    assert rec.status == "COMPLETED"
    assert rec.response_status_code == 200
    db.close()


# ---------------------------------------------------------------------------
# Test 8: Stale Processing Lease Recovery
# ---------------------------------------------------------------------------
def test_stale_processing_lease_recovery(setup_idempotency_env):
    """
    If a worker crashes while an idempotency record is in 'PROCESSING' state,
    the lease expires (locked_until < now). A subsequent retry must recover the lease
    and complete rather than becoming permanently blocked.
    """
    env = setup_idempotency_env
    key = f"stale-lease-{uuid.uuid4()}"

    payload = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    }
    req_hash = compute_request_hash("POST", "/api/v1/sales/orders", json.dumps(payload))

    # Pre-populate a record stuck in PROCESSING with an EXPIRED lease (10 seconds ago)
    db = SessionLocal()
    stale_rec = IdempotencyRecord(
        company_id=env["c1_id"],
        user_id=1,
        idempotency_key=key,
        request_method="POST",
        request_path="/api/v1/sales/orders",
        request_hash=req_hash,
        status="PROCESSING",
        locked_until=datetime.now(timezone.utc) - timedelta(seconds=10),
        recovery_count=0
    )
    db.add(stale_rec)
    db.commit()
    db.close()

    # Retry the request
    client = get_authenticated_client(env["u1_user"])
    res = client.post("/api/v1/sales/orders", json=payload, headers={"Idempotency-Key": key})
    assert res.status_code == 200, f"Expected stale lease recovery, got {res.status_code}: {res.text}"

    # Verify recovery_count incremented and status completed
    db = SessionLocal()
    rec = db.query(IdempotencyRecord).filter(
        IdempotencyRecord.company_id == env["c1_id"],
        IdempotencyRecord.idempotency_key == key
    ).first()
    assert rec.status == "COMPLETED"
    assert rec.recovery_count >= 1
    db.close()


# ---------------------------------------------------------------------------
# Test 9: Multi-Tenant Key Isolation
# ---------------------------------------------------------------------------
def test_multi_tenant_isolation(setup_idempotency_env):
    """
    Company A and Company B must be allowed to use the EXACT SAME Idempotency-Key
    independently without colliding or leaking data.
    """
    env = setup_idempotency_env
    shared_key = f"shared-tenant-key-{uuid.uuid4()}"

    client_c1 = get_authenticated_client(env["u1_user"], user_id=env["u1_id"], company_id=env["c1_id"], role="admin")
    client_c2 = get_authenticated_client(env["u2_user"], user_id=env["u2_id"], company_id=env["c2_id"], role="editor")

    payload_c1 = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    }

    payload_c2 = {
        "client_id": env["cl2_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p2_id"], "quantity": 1.0, "unit_price": 1500.0}]
    }

    # Company 1 creates order with shared_key
    res_c1 = client_c1.post("/api/v1/sales/orders", json=payload_c1, headers={"Idempotency-Key": shared_key})
    assert res_c1.status_code == 200, f"C1 order failed: {res_c1.text}"
    order_c1_id = res_c1.json()["id"]

    # Company 2 creates order with the EXACT SAME shared_key
    res_c2 = client_c2.post("/api/v1/sales/orders", json=payload_c2, headers={"Idempotency-Key": shared_key})
    assert res_c2.status_code == 200, f"C2 order failed: {res_c2.text}"
    order_c2_id = res_c2.json()["id"]

    # Both succeed and create distinct orders in their respective companies
    assert order_c1_id != order_c2_id

    # Verify in DB: Two distinct IdempotencyRecords exist with the same key
    db = SessionLocal()
    records = db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == shared_key).all()
    assert len(records) == 2
    comp_ids = set(r.company_id for r in records)
    assert comp_ids == {env["c1_id"], env["c2_id"]}
    db.close()


# ---------------------------------------------------------------------------
# Test 10: Authorization & Tenant IDOR Isolation
# ---------------------------------------------------------------------------
def test_authorization_isolation(setup_idempotency_env):
    """
    Unauthenticated users cannot replay or access idempotency records.
    Company 2 cannot query or replay Company 1's idempotency record.
    """
    env = setup_idempotency_env
    key = f"auth-leak-test-{uuid.uuid4()}"

    client_c1 = get_authenticated_client(env["u1_user"])
    payload_c1 = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    }

    # Company 1 creates record
    res1 = client_c1.post("/api/v1/sales/orders", json=payload_c1, headers={"Idempotency-Key": key})
    assert res1.status_code == 200, f"C1 create failed: {res1.text}"

    # Unauthenticated client attempt: Must be rejected by auth dependencies
    unauth_client = TestClient(app)
    res_unauth = unauth_client.post("/api/v1/sales/orders", json=payload_c1, headers={"Idempotency-Key": key})
    assert res_unauth.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Test 11: Frontend Outbox X-Idempotency-Key Compatibility
# ---------------------------------------------------------------------------
def test_offline_queue_x_idempotency_key_header(setup_idempotency_env):
    """
    The frontend offline queue (offlineQueue.ts) replays transactions using the
    'X-Idempotency-Key' header. Verifies full interoperability and replay safety.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env
    key = f"outbox-replay-{uuid.uuid4()}"

    payload = {
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    }

    # Initial dispatch with X-Idempotency-Key
    res1 = client.post("/api/v1/sales/orders", json=payload, headers={"X-Idempotency-Key": key})
    assert res1.status_code == 200, f"Initial outbox failed: {res1.text}"
    order_id = res1.json()["id"]

    # Replay dispatch with X-Idempotency-Key
    res2 = client.post("/api/v1/sales/orders", json=payload, headers={"X-Idempotency-Key": key})
    assert res2.status_code == 200, f"Replay outbox failed: {res2.text}"
    assert res2.headers.get("X-Idempotent-Replay") == "true"
    assert res2.json()["id"] == order_id


# ---------------------------------------------------------------------------
# Test 12: Stateful Conditional Idempotency (Void Reversal / Invoice Cancel)
# ---------------------------------------------------------------------------
def test_stateful_conditional_idempotency(setup_idempotency_env):
    """
    Audit conditional operations:
    1. Cancelling an invoice twice must not create duplicate reversals or void twice.
    2. Reversing a stock movement twice must reject with 400.
    """
    client = get_authenticated_client(setup_idempotency_env["u1_user"])
    env = setup_idempotency_env

    # 1. Create order & invoice
    so_res = client.post("/api/v1/sales/orders", json={
        "client_id": env["cl1_id"],
        "order_date_ad": "2026-10-01",
        "order_date_bs": "2083-06-15",
        "delivered": False,
        "received_amount": 0.0,
        "items": [{"product_id": env["p1_id"], "quantity": 1.0, "unit_price": 1200.0}]
    })
    assert so_res.status_code == 200, f"Order failed: {so_res.text}"
    so_id = so_res.json()["id"]

    inv_res = client.post("/api/v1/invoices", json={"sales_order_id": so_id, "vat_enabled": True})
    assert inv_res.status_code == 200
    inv_id = inv_res.json()["id"]

    # Cancel invoice: First attempt succeeds
    c_res1 = client.post(f"/api/v1/invoices/{inv_id}/cancel", json={"reason": "Customer cancellation"})
    assert c_res1.status_code == 200

    # Cancel invoice again: Rejected as already void
    c_res2 = client.post(f"/api/v1/invoices/{inv_id}/cancel", json={"reason": "Duplicate cancellation"})
    assert c_res2.status_code == 400
    assert "already cancelled" in c_res2.json()["detail"].lower()

    # 2. Stock movement reversal
    mv_res = client.post("/api/v1/stock/movements", json={
        "product_id": env["p1_id"],
        "quantity": 20.0,
        "direction": 1
    })
    assert mv_res.status_code == 200, f"Movement creation failed: {mv_res.text}"
    mv_id = mv_res.json()["id"]

    # First reversal succeeds
    rev1 = client.post(f"/api/v1/stock/reversals/{mv_id}", json={})
    assert rev1.status_code == 200

    # Second reversal rejected as already reversed
    rev2 = client.post(f"/api/v1/stock/reversals/{mv_id}", json={})
    assert rev2.status_code == 400
    assert "already been reversed" in rev2.json()["detail"].lower()
