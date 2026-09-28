import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, StockMovement, StockSnapshot
from app.core.security import get_password_hash, create_access_token

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

    user = db.query(User).filter(User.username == "snap_tester").first()
    if not user:
        user = User(
            company_id=comp.id,
            name="Snapshot Tester",
            username="snap_tester",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
    token = create_access_token({"user_id": user.id, "company_id": comp.id, "role": "editor"})
    db.close()

    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client

def test_stock_snapshot_materialization_and_math(client):
    # 1. Create a test product
    p_res = client.post("/api/v1/production/products", json={
        "code": "SNAP-PROD-01",
        "name": "Snapshot Test Footwear",
        "category": "Shoe",
        "size": "41",
        "color": "Black",
        "unit_price": 2500.0
    })
    assert p_res.status_code == 200
    prod_id = p_res.json()["id"]

    # 2. Add an initial batch (30 pairs)
    b1_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-SNAP-01",
        "product_id": prod_id,
        "target_quantity": 30.0,
        "produced_quantity": 30.0,
        "worker_count": 2,
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15"
    })
    assert b1_res.status_code == 200

    # 3. Before snapshot: derived stock should be 30 via pure movement summation
    bal_res1 = client.get("/api/v1/stock/balance")
    assert bal_res1.status_code == 200
    prod_bal1 = next(item for item in bal_res1.json() if item["product_id"] == prod_id)
    assert prod_bal1["current_stock_pairs"] == 30.0

    # 4. Create snapshot for today
    snap_res = client.post("/api/v1/stock/snapshots", json={"snapshot_date": str(date.today())})
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert snap_data["created_snapshots"] >= 1

    # Verify snapshot list endpoint
    list_snaps = client.get(f"/api/v1/stock/snapshots?product_id={prod_id}")
    assert list_snaps.status_code == 200
    assert len(list_snaps.json()) >= 1
    latest_snap = list_snaps.json()[0]
    assert latest_snap["balance"] == 30
    assert latest_snap["last_movement_id"] > 0

    # 5. Add subsequent batch (15 pairs) after snapshot
    b2_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-SNAP-02",
        "product_id": prod_id,
        "target_quantity": 15.0,
        "produced_quantity": 15.0,
        "worker_count": 2,
        "date_ad": "2026-10-02",
        "date_bs": "2083-06-16"
    })
    assert b2_res.status_code == 200

    # 6. Verify derived stock = Snapshot (30) + Subsequent Delta (15) = 45.0
    bal_res2 = client.get("/api/v1/stock/balance")
    assert bal_res2.status_code == 200
    prod_bal2 = next(item for item in bal_res2.json() if item["product_id"] == prod_id)
    assert prod_bal2["current_stock_pairs"] == 45.0
