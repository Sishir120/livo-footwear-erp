"""
Concurrency Mutex & Race Condition Prevention Tests
Verifies that concurrent dispatch requests against limited stock cannot oversell.
Enforces pessimistic locking and the HTTP 422 negative stock barrier.
"""
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, StockMovement, Client
from app.core.security import get_password_hash, create_access_token
from app.api.deps import COOKIE_NAME

@pytest.fixture(scope="module")
def setup_race_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "RACE_CO").first()
    if not comp:
        comp = Company(name="Race Test Company", code="RACE_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    user = db.query(User).filter(User.username == "race_editor").first()
    if not user:
        user = User(
            company_id=comp.id,
            name="Race Editor",
            username="race_editor",
            password_hash=get_password_hash("RacePass123!"),
            role="editor",
            active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(
        data={"user_id": user.id, "company_id": comp.id, "role": user.role, "sub": user.username}
    )

    db.close()
    return {"company_id": comp.id, "user_id": user.id, "token": token}


def test_concurrent_stock_dispatch_race(setup_race_env):
    """
    Step 1 Concurrency Verification:
    - Product variant seeded with exactly 20 pairs.
    - 10 concurrent dispatch requests of 5 pairs each (Total requested: 50 pairs).
    - Exactly 4 requests must succeed (HTTP 200/201).
    - Exactly 6 requests must fail with HTTP 422 Insufficient physical stock.
    - Final derived inventory must equal exactly 0 (never negative).
    """
    token = setup_race_env["token"]
    company_id = setup_race_env["company_id"]

    db = SessionLocal()
    # Create isolated product for this test
    product = Product(
        company_id=company_id,
        code="RACE-SNK-42",
        name="Race Test Sneaker 42",
        category="Sneaker",
        size="42",
        color="White",
        unit_price=2500.0
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id

    # Seed with exactly 20 pairs (direction = 1)
    seed_movement = StockMovement(
        company_id=company_id,
        product_id=product_id,
        direction=1,
        quantity=20.0,
        ref_type="production_seed",
        ref_id=1,
        notes="Seeded exactly 20 pairs for race test",
        date_ad="2026-10-01",
        date_bs=""
    )
    db.add(seed_movement)
    db.commit()
    db.close()

    def send_dispatch_request(worker_idx: int):
        with TestClient(app, cookies={COOKIE_NAME: token}) as client:
            res = client.post(
                "/api/v1/stock/movements",
                json={
                    "product_id": product_id,
                    "quantity": 5.0,
                    "direction": -1,
                    "reference_type": "dispatch_race",
                    "reference_id": worker_idx,
                    "notes": f"Concurrent dispatch worker {worker_idx}"
                }
            )
            return res.status_code, res.text

    # Fire 10 concurrent requests of 5 pairs each
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_dispatch_request, i) for i in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    status_codes = [status for status, _ in results]
    success_count = sum(1 for sc in status_codes if sc in (200, 201))
    failure_422_count = sum(1 for sc in status_codes if sc == 422)

    # Assert exactly 4 succeed, exactly 6 fail with 422
    assert success_count == 4, f"Expected exactly 4 successes, got {success_count}. Statuses: {status_codes}"
    assert failure_422_count == 6, f"Expected exactly 6 422 failures, got {failure_422_count}. Statuses: {status_codes}"

    # Verify final derived stock balance is exactly 0
    with TestClient(app, cookies={COOKIE_NAME: token}) as client:
        balance_res = client.get("/api/v1/stock/balance")
        assert balance_res.status_code == 200
        items = balance_res.json()
        target_item = next((it for it in items if it["product_id"] == product_id), None)
        assert target_item is not None
        assert target_item["current_stock_pairs"] == 0.0, f"Expected 0.0 stock, found {target_item['current_stock_pairs']}"


def test_concurrent_sales_orders_dispatch_race(setup_race_env):
    """
    Step 1 Concurrency Verification for Sales Orders:
    - Product variant seeded with exactly 20 pairs.
    - 10 concurrent sales orders of 5 pairs each with delivered=True.
    - Exactly 4 requests must succeed (HTTP 200), exactly 6 must fail with HTTP 422.
    - Final stock balance must equal exactly 0.
    """
    token = setup_race_env["token"]
    company_id = setup_race_env["company_id"]

    db = SessionLocal()
    client_obj = Client(
        company_id=company_id,
        code="RACE-CLI-01",
        name="Race Wholesale Dealer",
        phone="9800000001"
    )
    db.add(client_obj)
    db.commit()
    db.refresh(client_obj)
    client_id = client_obj.id

    product = Product(
        company_id=company_id,
        code="RACE-BOOT-43",
        name="Race Test Boot 43",
        category="Boot",
        size="43",
        color="Brown",
        unit_price=3500.0
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    product_id = product.id

    # Seed with exactly 20 pairs
    seed_movement = StockMovement(
        company_id=company_id,
        product_id=product_id,
        direction=1,
        quantity=20.0,
        ref_type="production_seed",
        ref_id=2,
        notes="Seeded exactly 20 pairs for sales race test",
        date_ad="2026-10-01",
        date_bs=""
    )
    db.add(seed_movement)
    db.commit()
    db.close()

    def send_order_request(worker_idx: int):
        with TestClient(app, cookies={COOKIE_NAME: token}) as client:
            res = client.post(
                "/api/v1/sales/orders",
                json={
                    "order_number": f"SO-RACE-{worker_idx:03d}",
                    "client_id": client_id,
                    "order_date_ad": "2026-10-01",
                    "order_date_bs": "2083-06-15",
                    "items": [{"product_id": product_id, "quantity": 5.0, "unit_price": 3500.0}],
                    "delivered": True
                }
            )
            return res.status_code, res.text

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_order_request, i) for i in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    status_codes = [status for status, _ in results]
    success_count = sum(1 for sc in status_codes if sc in (200, 201))
    failure_422_count = sum(1 for sc in status_codes if sc == 422)

    assert success_count == 4, f"Expected 4 successful orders, got {success_count}. Statuses: {status_codes}"
    assert failure_422_count == 6, f"Expected 6 422 rejections, got {failure_422_count}. Statuses: {status_codes}"

    with TestClient(app, cookies={COOKIE_NAME: token}) as client:
        balance_res = client.get("/api/v1/stock/balance")
        assert balance_res.status_code == 200
        items = balance_res.json()
        target_item = next((it for it in items if it["product_id"] == product_id), None)
        assert target_item is not None
        assert target_item["current_stock_pairs"] == 0.0
