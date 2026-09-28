import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User
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

    user = db.query(User).filter(User.username == "bom_tester").first()
    if not user:
        user = User(
            company_id=comp.id,
            name="BOM Tester",
            username="bom_tester",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(user)
        db.commit()

    token = create_access_token({"user_id": user.id, "company_id": comp.id, "role": "editor"})
    db.close()

    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client

def test_bom_automatic_deduction_and_insufficient_rejection(client):
    # 1. Create Supplier & Raw Material
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": "SUP-BOM-01",
        "name": "BOM Leather Tannery",
        "phone": "9811223344"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": "RM-BOM-LEATHER",
        "name": "Calf Leather Premium",
        "unit": "sqft",
        "min_stock_alert": 10.0
    }).json()
    mat_id = mat["id"]

    # 2. Purchase 100 sqft of leather
    client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 100.0,
        "unit_price": 300.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15"
    })

    # 3. Create Footwear Product
    prod = client.post("/api/v1/production/products", json={
        "code": "BOM-SHOE-01",
        "name": "Premium Leather Oxford 42",
        "category": "Shoe",
        "size": "42",
        "color": "Tan",
        "unit_price": 4500.0
    }).json()
    prod_id = prod["id"]

    # 4. Configure BOM: 1.5 sqft per pair
    bom_res = client.post("/api/v1/production/bom", json={
        "product_id": prod_id,
        "raw_material_id": mat_id,
        "quantity_required": 1.5
    })
    assert bom_res.status_code == 200

    # 5. Attempt batch of 100 pairs (requires 150 sqft > 100 available)
    # MUST FAIL with HTTP 422 Insufficient Raw Material
    fail_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-FAIL-01",
        "product_id": prod_id,
        "target_quantity": 100.0,
        "produced_quantity": 100.0,
        "worker_count": 5,
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15"
    })
    assert fail_res.status_code == 422
    assert "Insufficient Raw Material" in fail_res.json()["detail"]
    assert "Calf Leather Premium" in fail_res.json()["detail"]

    # 6. Create valid batch of 40 pairs (requires 60 sqft <= 100 available)
    # MUST SUCCEED with HTTP 200
    ok_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-OK-01",
        "product_id": prod_id,
        "target_quantity": 40.0,
        "produced_quantity": 40.0,
        "worker_count": 4,
        "date_ad": "2026-10-01",
        "date_bs": "2083-06-15"
    })
    assert ok_res.status_code == 200

    # 7. Now remaining stock is 100 - 60 = 40 sqft.
    # Attempting batch of 30 pairs (requires 45 sqft > 40 available) MUST FAIL with 422
    fail2_res = client.post("/api/v1/production/batches", json={
        "batch_number": "BATCH-FAIL-02",
        "product_id": prod_id,
        "target_quantity": 30.0,
        "produced_quantity": 30.0,
        "worker_count": 3,
        "date_ad": "2026-10-02",
        "date_bs": "2083-06-16"
    })
    assert fail2_res.status_code == 422
    assert "Insufficient Raw Material" in fail2_res.json()["detail"]
