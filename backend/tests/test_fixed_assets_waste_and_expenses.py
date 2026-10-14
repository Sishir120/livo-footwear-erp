import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.purchase import RawMaterial
from app.models.production import ProductionBatch
from app.models.asset import FixedAsset
from app.models.waste import WasteRecord
from app.models.sales import FactoryExpense
from app.core.security import get_password_hash, create_access_token
from app.db.session import Base, engine

Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_setup(db_session: Session):
    import uuid
    uid = uuid.uuid4().hex[:6]

    # Company 1
    comp1 = Company(name=f"Himalayan Footwear {uid}", code=f"HFI_{uid}")
    db_session.add(comp1)
    db_session.flush()

    # Company 2 (for tenant isolation)
    comp2 = Company(name=f"Everest Leather {uid}", code=f"ELW_{uid}")
    db_session.add(comp2)
    db_session.flush()

    # Users
    admin_user = User(
        company_id=comp1.id,
        name="Admin Test",
        username=f"admin_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="admin",
        active=True
    )
    editor_user = User(
        company_id=comp1.id,
        name="Editor Test",
        username=f"editor_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="editor",
        active=True
    )
    viewer_user = User(
        company_id=comp1.id,
        name="Viewer Test",
        username=f"viewer_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="viewer",
        active=True
    )
    other_tenant_user = User(
        company_id=comp2.id,
        name="Other Admin",
        username=f"other_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="admin",
        active=True
    )
    db_session.add_all([admin_user, editor_user, viewer_user, other_tenant_user])
    db_session.flush()

    # Products & Raw Materials for Comp1
    prod = Product(
        company_id=comp1.id,
        code="HFI-BOOT-01",
        name="Trekking Boot",
        category="Boot",
        size="41",
        unit_price=Decimal("3500.00")
    )
    rm = RawMaterial(
        company_id=comp1.id,
        code="RM-EVA-01",
        name="EVA Sole Sheet",
        unit="kg",
        current_stock=100.0,
        reorder_level=20.0
    )
    db_session.add_all([prod, rm])
    db_session.flush()

    batch = ProductionBatch(
        company_id=comp1.id,
        batch_number="BATCH-2083-001",
        product_id=prod.id,
        target_quantity=50,
        produced_quantity=50,
        worker_count=5,
        status="completed",
        date_ad="2026-10-12",
        date_bs="2083-06-26",
        color="Black"
    )
    db_session.add(batch)
    db_session.commit()

    return {
        "comp1_id": comp1.id,
        "comp2_id": comp2.id,
        "admin_token": create_access_token({"sub": admin_user.username, "user_id": admin_user.id, "company_id": comp1.id, "role": "admin"}),
        "editor_token": create_access_token({"sub": editor_user.username, "user_id": editor_user.id, "company_id": comp1.id, "role": "editor"}),
        "viewer_token": create_access_token({"sub": viewer_user.username, "user_id": viewer_user.id, "company_id": comp1.id, "role": "viewer"}),
        "other_token": create_access_token({"sub": other_tenant_user.username, "user_id": other_tenant_user.id, "company_id": comp2.id, "role": "admin"}),
        "product_id": prod.id,
        "raw_material_id": rm.id,
        "batch_id": batch.id
    }


def test_fixed_asset_lifecycle_and_valuation(test_setup, db_session):
    headers = {"Authorization": f"Bearer {test_setup['editor_token']}"}

    # 1. Create Fixed Asset
    payload = {
        "asset_code": "MCH-SOLING-01",
        "asset_name": "Hydraulic Sole Press Machine",
        "category": "MACHINERY",
        "purchase_date_ad": "2026-05-10",
        "purchase_date_bs": "2083-01-27",
        "purchase_cost_paisa": 45000000,  # NPR 450,000.00
        "quantity": 2,
        "location": "Assembly Floor Bay 3",
        "remarks": "Purchased from Taiwan Machinery Corp"
    }
    res = client.post("/api/v1/fixed-assets", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["asset_code"] == "MCH-SOLING-01"
    assert data["purchase_cost_paisa"] == 45000000
    asset_id = data["id"]

    # 2. Duplicate code rejected
    res_dup = client.post("/api/v1/fixed-assets", json=payload, headers=headers)
    assert res_dup.status_code == 409

    # 3. Add second asset using NPR decimal
    payload2 = {
        "asset_code": "MLD-TREK-41",
        "asset_name": "Aluminium Sole Mould Size 41",
        "category": "MOULD",
        "purchase_date_ad": "2026-06-15",
        "purchase_date_bs": "2083-03-01",
        "cost_npr": 35000.50,  # 3,500,050 paisa
        "quantity": 4,
        "location": "Mould Rack A"
    }
    res2 = client.post("/api/v1/fixed-assets", json=payload2, headers=headers)
    assert res2.status_code == 201

    # 4. List assets and verify valuation aggregation
    list_res = client.get("/api/v1/fixed-assets", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_count"] == 2
    # Total valuation: (45000000 * 2) + (3500050 * 4) = 90000000 + 14000200 = 104000200 paisa
    expected_paisa = 104000200
    assert list_data["total_valuation_paisa"] == expected_paisa
    assert list_data["total_valuation_npr"] == float(round(Decimal(expected_paisa) / Decimal(100), 2))

    # 5. Tenant isolation: Other tenant sees 0 assets
    other_headers = {"Authorization": f"Bearer {test_setup['other_token']}"}
    other_list = client.get("/api/v1/fixed-assets", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json()["total_count"] == 0
    assert other_list.json()["total_valuation_paisa"] == 0

    # 6. Viewer blocked from creating
    viewer_headers = {"Authorization": f"Bearer {test_setup['viewer_token']}"}
    view_res = client.post("/api/v1/fixed-assets", json=payload, headers=viewer_headers)
    assert view_res.status_code == 403

    # 7. Delete asset
    del_res = client.delete(f"/api/v1/fixed-assets/{asset_id}", headers=headers)
    assert del_res.status_code == 200


def test_waste_tracking_without_stock_deduction(test_setup, db_session):
    headers = {"Authorization": f"Bearer {test_setup['editor_token']}"}

    # Initial raw material stock balance
    rm = db_session.query(RawMaterial).filter(RawMaterial.id == test_setup["raw_material_id"]).first()
    initial_stock = rm.current_stock

    # 1. Log Raw Material Scrap (Cutting floor scrap)
    waste_payload = {
        "waste_date_ad": "2026-10-12",
        "waste_date_bs": "2083-06-26",
        "waste_type": "RAW_MATERIAL_SCRAP",
        "raw_material_id": test_setup["raw_material_id"],
        "batch_id": test_setup["batch_id"],
        "quantity": 4.5,
        "unit": "kg",
        "reason": "Cutting room trimmings and edge remnants",
        "disposal_method": "RECYCLED"
    }
    res = client.post("/api/v1/waste", json=waste_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["waste_type"] == "RAW_MATERIAL_SCRAP"
    assert data["quantity"] == 4.5
    scrap_id = data["id"]

    # Invariant per Decision D: stock must NOT be deducted automatically
    db_session.refresh(rm)
    assert rm.current_stock == initial_stock, "Scrap logging must NOT mutate inventory balance"

    # 2. Log Finished Pair Reject
    reject_payload = {
        "waste_date_ad": "2026-10-12",
        "waste_date_bs": "2083-06-26",
        "waste_type": "FINISHED_PAIR_REJECT",
        "product_id": test_setup["product_id"],
        "batch_id": test_setup["batch_id"],
        "quantity": 2.0,
        "unit": "pair",
        "reason": "Sole bonding defect discovered during QC",
        "disposal_method": "DISCARDED"
    }
    res_reject = client.post("/api/v1/waste", json=reject_payload, headers=headers)
    assert res_reject.status_code == 201

    # 3. List and verify metrics
    list_res = client.get("/api/v1/waste", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_records"] == 2
    assert list_data["total_raw_scrap_kg"] == 4.5
    assert list_data["total_reject_pairs"] == 2.0

    # 4. Filter by batch
    batch_filter_res = client.get(f"/api/v1/waste?batch_id={test_setup['batch_id']}", headers=headers)
    assert batch_filter_res.status_code == 200
    assert batch_filter_res.json()["total_records"] == 2

    # 5. Invalid waste type rejected
    invalid_payload = dict(waste_payload, waste_type="UNKNOWN_TYPE")
    assert client.post("/api/v1/waste", json=invalid_payload, headers=headers).status_code == 422


def test_factory_expenses_ledger_and_aggregation(test_setup, db_session):
    headers = {"Authorization": f"Bearer {test_setup['editor_token']}"}

    # 1. Create Electricity Bill Expense
    payload1 = {
        "expense_date_ad": "2026-10-01",
        "expense_date_bs": "2083-06-15",
        "particular": "NEA Industrial Feeder Electricity Bill Ashwin",
        "category": "ELECTRICITY_WATER",
        "amount_paisa": 12500000,  # NPR 125,000.00
        "payment_method": "BANK",
        "remarks": "Paid via ConnectIPS"
    }
    res1 = client.post("/api/v1/expenses/factory", json=payload1, headers=headers)
    assert res1.status_code == 201
    assert res1.json()["amount_paisa"] == 12500000
    exp1_id = res1.json()["id"]

    # 2. Create Generator Fuel Expense using NPR decimal
    payload2 = {
        "expense_date_ad": "2026-10-05",
        "expense_date_bs": "2083-06-19",
        "particular": "Diesel 100L for Backup Generator",
        "category": "GENERATOR_FUEL",
        "amount_npr": 17500.00,  # 1,750,000 paisa
        "payment_method": "CASH",
        "remarks": "Purchased from Balaju Fuel Center"
    }
    res2 = client.post("/api/v1/expenses/factory", json=payload2, headers=headers)
    assert res2.status_code == 201
    assert res2.json()["amount_paisa"] == 1750000

    # 3. List and verify aggregation
    list_res = client.get("/api/v1/expenses/factory", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["count"] == 2
    expected_total = 12500000 + 1750000
    assert data["total_amount_paisa"] == expected_total
    assert data["total_amount_npr"] == float(round(Decimal(expected_total) / Decimal(100), 2))

    # 4. Filter by category
    cat_res = client.get("/api/v1/expenses/factory?category=GENERATOR_FUEL", headers=headers)
    assert cat_res.status_code == 200
    assert cat_res.json()["count"] == 1
    assert cat_res.json()["items"][0]["category"] == "GENERATOR_FUEL"

    # 5. Tenant isolation: Other tenant sees 0 expenses
    other_headers = {"Authorization": f"Bearer {test_setup['other_token']}"}
    other_res = client.get("/api/v1/expenses/factory", headers=other_headers)
    assert other_res.status_code == 200
    assert other_res.json()["count"] == 0
    assert other_res.json()["total_amount_paisa"] == 0

    # 6. Delete expense
    del_res = client.delete(f"/api/v1/expenses/factory/{exp1_id}", headers=headers)
    assert del_res.status_code == 200
