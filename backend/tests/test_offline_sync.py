import pytest
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, ProductionBatch, StockMovement
from app.models.sync import ProductionSyncLog
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_sync_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Company
    comp = db.query(Company).filter(Company.code == "SYNC_TEST_CO").first()
    if not comp:
        comp = Company(name="Sync Test Factory Ltd", code="SYNC_TEST_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Warehouse
    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id).first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="Sync Finished Warehouse", code="WH-SYNC", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    # Editor user
    editor = db.query(User).filter(User.username == "sync_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="Sync Editor",
            username="sync_editor",
            password_hash=get_password_hash("SyncPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    # Viewer user
    viewer = db.query(User).filter(User.username == "sync_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="Sync Viewer",
            username="sync_viewer",
            password_hash=get_password_hash("SyncPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    # Master Product
    prod = db.query(Product).filter(Product.company_id == comp.id, Product.code == "PROD-SYNC-01").first()
    if not prod:
        prod = Product(
            company_id=comp.id,
            code="PROD-SYNC-01",
            name="Offline Trail Boot",
            category="Boot",
            size="40",
            color="Brown",
            unit_price=1800.0
        )
        db.add(prod)

    db.commit()
    db.refresh(comp)
    db.refresh(wh)
    db.refresh(editor)
    db.refresh(viewer)
    db.refresh(prod)
    db.close()

    return {
        "company_id": comp.id,
        "editor_username": "sync_editor",
        "viewer_username": "sync_viewer",
        "product_id": prod.id,
        "warehouse_id": wh.id
    }


def login_client(client: TestClient, username: str, password: str = "SyncPass123!"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json().get("access_token")
    if token:
        client.cookies.set(COOKIE_NAME, token)
    for k, v in resp.cookies.items():
        client.cookies.set(k, v)
    return client


def test_submit_new_draft_creates_batch_and_stock_movements(setup_sync_env):
    """Submitting a fresh production draft records the batch and appends stock movements per size."""
    client = TestClient(app)
    login_client(client, setup_sync_env["editor_username"])

    idem_key = f"prod:draft:{uuid.uuid4()}"
    payload = {
        "idempotency_key": idem_key,
        "created_at_device": "2026-09-29T08:45:00Z",
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "line": "Line 2",
        "shift": "Morning",
        "worker_count": 5,
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {
            "38": 10,
            "39": 20,
            "40": 30
        },
        "notes": "Morning offline assembly run"
    }

    resp = client.post("/api/v1/production/sync/draft", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sync_status"] == "ACCEPTED"
    assert data["batch_id"] is not None
    assert data["batch_number"].startswith("BATCH-")

    # Verify database state
    db = SessionLocal()
    batch = db.query(ProductionBatch).filter(ProductionBatch.id == data["batch_id"]).first()
    assert batch is not None
    assert batch.produced_quantity == 60.0

    # Verify stock movements created
    movements = db.query(StockMovement).filter(
        StockMovement.company_id == setup_sync_env["company_id"],
        StockMovement.ref_type == "production",
        StockMovement.ref_id == batch.id
    ).all()
    assert len(movements) == 3
    total_moved = sum(m.quantity for m in movements)
    assert total_moved == 60.0

    # Verify sync log entry
    log = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == setup_sync_env["company_id"],
        ProductionSyncLog.idempotency_key == idem_key
    ).first()
    assert log is not None
    assert log.status == "ACCEPTED"
    assert log.batch_id == batch.id
    db.close()


def test_replaying_identical_idempotency_key_is_idempotent(setup_sync_env):
    """Replaying the identical idempotency_key returns original batch without duplicating movements."""
    client = TestClient(app)
    login_client(client, setup_sync_env["editor_username"])

    idem_key = f"prod:draft:{uuid.uuid4()}"
    payload = {
        "idempotency_key": idem_key,
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {"40": 25},
        "notes": "Test replay"
    }

    # First attempt: ACCEPTED
    resp1 = client.post("/api/v1/production/sync/draft", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["sync_status"] == "ACCEPTED"
    batch_id = data1["batch_id"]

    db = SessionLocal()
    mv_count_before = db.query(StockMovement).filter(StockMovement.ref_id == batch_id).count()
    db.close()

    # Second attempt: ALREADY_ACCEPTED
    resp2 = client.post("/api/v1/production/sync/draft", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["sync_status"] == "ALREADY_ACCEPTED"
    assert data2["batch_id"] == batch_id

    # Third attempt: ALREADY_ACCEPTED
    resp3 = client.post("/api/v1/production/sync/draft", json=payload)
    assert resp3.status_code == 200
    assert resp3.json()["sync_status"] == "ALREADY_ACCEPTED"

    # Confirm stock movements were NOT duplicated
    db = SessionLocal()
    mv_count_after = db.query(StockMovement).filter(StockMovement.ref_id == batch_id).count()
    assert mv_count_after == mv_count_before
    db.close()


def test_concurrent_idempotent_draft_submissions(setup_sync_env):
    """Concurrent submissions with identical idempotency_key serialize cleanly without 500 error."""
    client = TestClient(app)
    login_client(client, setup_sync_env["editor_username"])
    # Extract token string safely
    token = None
    for cookie in client.cookies.jar:
        if cookie.name == COOKIE_NAME:
            token = cookie.value
            break

    idem_key = f"prod:draft:{uuid.uuid4()}"
    payload = {
        "idempotency_key": idem_key,
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {"41": 15},
        "notes": "Concurrent test"
    }

    def send_draft():
        c = TestClient(app)
        if token:
            c.cookies.set(COOKIE_NAME, token)
        return c.post("/api/v1/production/sync/draft", json=payload)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_draft) for _ in range(5)]
        results = [f.result() for f in futures]

    statuses = [r.status_code for r in results]
    assert all(s == 200 for s in statuses)

    sync_statuses = [r.json()["sync_status"] for r in results]
    # Exactly one ACCEPTED, remainder ALREADY_ACCEPTED
    assert sync_statuses.count("ACCEPTED") == 1
    assert sync_statuses.count("ALREADY_ACCEPTED") == 4

    batch_ids = {r.json()["batch_id"] for r in results}
    assert len(batch_ids) == 1


def test_viewer_role_rejected_from_sync(setup_sync_env):
    """User with viewer role is rejected with HTTP 403 Forbidden."""
    client = TestClient(app)
    login_client(client, setup_sync_env["viewer_username"])

    payload = {
        "idempotency_key": f"prod:draft:{uuid.uuid4()}",
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {"40": 10}
    }

    resp = client.post("/api/v1/production/sync/draft", json=payload)
    assert resp.status_code == 403


def test_non_integer_or_negative_quantities_rejected_and_logged(setup_sync_env):
    """Non-integer, negative, or zero quantities log a REJECTED sync log and return HTTP 422."""
    client = TestClient(app)
    login_client(client, setup_sync_env["editor_username"])

    # 1. Negative quantity
    idem_key_neg = f"prod:draft:{uuid.uuid4()}"
    payload_neg = {
        "idempotency_key": idem_key_neg,
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {"40": -5}
    }
    resp_neg = client.post("/api/v1/production/sync/draft", json=payload_neg)
    assert resp_neg.status_code == 422

    db = SessionLocal()
    log_neg = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == setup_sync_env["company_id"],
        ProductionSyncLog.idempotency_key == idem_key_neg
    ).first()
    assert log_neg is not None
    assert log_neg.status == "REJECTED"
    assert log_neg.error_code == "INVALID_QUANTITY"

    # 2. Fractional float quantity (e.g. 5.5 pairs)
    idem_key_float = f"prod:draft:{uuid.uuid4()}"
    payload_float = {
        "idempotency_key": idem_key_float,
        "product_id": setup_sync_env["product_id"],
        "warehouse_id": setup_sync_env["warehouse_id"],
        "date_ad": "2026-09-29",
        "date_bs": "2083-06-13",
        "size_quantities": {"40": 5.5}
    }
    resp_float = client.post("/api/v1/production/sync/draft", json=payload_float)
    assert resp_float.status_code == 422

    log_float = db.query(ProductionSyncLog).filter(
        ProductionSyncLog.company_id == setup_sync_env["company_id"],
        ProductionSyncLog.idempotency_key == idem_key_float
    ).first()
    assert log_float is not None
    assert log_float.status == "REJECTED"
    db.close()
