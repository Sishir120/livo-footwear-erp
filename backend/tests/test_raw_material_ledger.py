import uuid
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User
from app.models.purchase import Supplier, RawMaterial, Purchase, RawMaterialMovement
from app.core.security import get_password_hash, create_access_token

@pytest.fixture(scope="module")
def setup_env():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    uid = uuid.uuid4().hex[:6]
    comp = Company(name=f"Landed Ledger Corp {uid}", code=f"LLC_{uid}".upper())
    db.add(comp)
    db.commit()
    db.refresh(comp)

    editor_user = User(
        company_id=comp.id,
        name="Procurement Manager",
        username=f"proc_editor_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="editor",
        active=True
    )
    viewer_user = User(
        company_id=comp.id,
        name="Auditor Viewer",
        username=f"proc_viewer_{uid}",
        password_hash=get_password_hash("Secret123!"),
        role="viewer",
        active=True
    )
    db.add_all([editor_user, viewer_user])
    db.commit()
    db.refresh(editor_user)
    db.refresh(viewer_user)

    editor_token = create_access_token({"user_id": editor_user.id, "company_id": comp.id, "role": "editor"})
    viewer_token = create_access_token({"user_id": viewer_user.id, "company_id": comp.id, "role": "viewer"})
    db.close()

    return {
        "company_id": comp.id,
        "editor_token": editor_token,
        "viewer_token": viewer_token
    }

@pytest.fixture
def client(setup_env):
    with TestClient(app) as tc:
        tc.headers["Authorization"] = f"Bearer {setup_env['editor_token']}"
        yield tc

@pytest.fixture
def viewer_client(setup_env):
    with TestClient(app) as tc:
        tc.headers["Authorization"] = f"Bearer {setup_env['viewer_token']}"
        yield tc


def test_po_creation_does_not_mutate_stock_until_received(client):
    """
    Directive 3: A Purchase Order in ORDERED status creates no stock movement.
    Stock movements are appended strictly when GRN / receive is posted.
    """
    uid = uuid.uuid4().hex[:5]
    # 1. Create Supplier & Raw Material
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-PO-{uid}",
        "name": f"Supplier PO {uid}",
        "phone": "9800000000"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-PO-{uid}",
        "name": f"Rubber Sheet {uid}",
        "unit": "kg",
        "reorder_level": 10.0
    }).json()
    mat_id = mat["id"]

    # 2. Check initial stock card is zero
    card_res = client.get(f"/api/v1/purchases/materials/{mat_id}/card")
    assert card_res.status_code == 200
    card = card_res.json()
    assert card["current_balance"] == 0.0
    assert len(card["movements"]) == 0

    # 3. Create PO with status="ORDERED"
    po_res = client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 50.0,
        "unit_price": 200.0,
        "purchase_date_ad": "2026-10-11",
        "purchase_date_bs": "2083-06-25",
        "status": "ORDERED",
        "notes": "Draft PO for rubber sheets"
    })
    assert po_res.status_code == 200
    po = po_res.json()
    assert po["status"] == "ORDERED"
    assert po["received_quantity"] == 0.0

    # 4. Confirm physical stock has NOT changed
    card_after_po = client.get(f"/api/v1/purchases/materials/{mat_id}/card").json()
    assert card_after_po["current_balance"] == 0.0
    assert len(card_after_po["movements"]) == 0

    # 5. Receive the goods via /receive
    rec_res = client.post(f"/api/v1/purchases/{po['id']}/receive", json={
        "receipt_date_ad": "2026-10-12",
        "receipt_date_bs": "2083-06-26",
        "received_quantity": 50.0,
        "carrying_in_paisa": 100000,
        "import_duty_paisa": 50000,
        "china_carrying_paisa": 0,
        "insurance_paisa": 25000,
        "notes": "Full shipment arrived at warehouse gate"
    })
    assert rec_res.status_code == 200
    updated_po = rec_res.json()
    assert updated_po["status"] == "RECEIVED"
    assert updated_po["received_quantity"] == 50.0
    assert updated_po["grn_number"] is not None

    # 6. Verify movement ledger now reflects +50.0
    card_received = client.get(f"/api/v1/purchases/materials/{mat_id}/card").json()
    assert card_received["current_balance"] == 50.0
    assert len(card_received["movements"]) == 1
    m = card_received["movements"][0]
    assert m["direction"] == 1
    assert m["quantity"] == 50.0
    assert m["movement_type"] == "PURCHASE_RECEIPT"


def test_landed_cost_calculation_and_capitalization(client):
    """
    Directive 2: Landed Cost Capitalization.
    Total Landed Cost = Base + Carrying + Customs + China Freight + Insurance (in integer paisa).
    Effective Unit Cost = floor(Total Landed Cost / Received Quantity).
    """
    uid = uuid.uuid4().hex[:5]
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-IMP-{uid}",
        "name": f"China Poly Chemical {uid}"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-EVA-{uid}",
        "name": f"EVA Pellets Virgin Grade {uid}",
        "unit": "kg"
    }).json()

    # Base price: 100 kg @ NPR 450.00 = NPR 45,000.00 = 4,500,000 paisa
    # Local Carrying: NPR 2,500.00 = 250,000 paisa
    # Import Duty: NPR 4,500.00 = 450,000 paisa
    # China Freight: NPR 3,000.00 = 300,000 paisa
    # Insurance: NPR 1,500.00 = 150,000 paisa
    # Total Landed = 4,500,000 + 250,000 + 450,000 + 300,000 + 150,000 = 5,650,000 paisa
    # Effective Unit Rate = 5,650,000 // 100 = 56,500 paisa (NPR 565.00/kg)

    po = client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat["id"],
        "quantity": 100.0,
        "unit_price": 450.0,
        "purchase_date_ad": "2026-10-11",
        "purchase_date_bs": "2083-06-25",
        "status": "ORDERED"
    }).json()

    rec_res = client.post(f"/api/v1/purchases/{po['id']}/receive", json={
        "receipt_date_ad": "2026-10-11",
        "receipt_date_bs": "2083-06-25",
        "received_quantity": 100.0,
        "carrying_in_paisa": 250000,
        "import_duty_paisa": 450000,
        "china_carrying_paisa": 300000,
        "insurance_paisa": 150000,
        "notes": "Customs clearance Birgunj dry port"
    })
    assert rec_res.status_code == 200
    rec = rec_res.json()

    assert rec["total_landed_cost_paisa"] == 5650000
    assert rec["effective_unit_rate_paisa"] == 56500

    # Stock card check for capitalized unit cost
    card = client.get(f"/api/v1/purchases/materials/{mat['id']}/card").json()
    mov = card["movements"][0]
    assert mov["unit_cost_paisa"] == 56500
    assert mov["unit_cost_npr"] == 565.0


def test_raw_material_movement_append_and_balance_reconciliation(client):
    """
    Directive 1: Physical stock on hand = sum(quantity * direction) from immutable ledger entries.
    """
    uid = uuid.uuid4().hex[:5]
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-REC-{uid}",
        "name": f"Supplier Reconcile {uid}"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-REC-{uid}",
        "name": f"Adhesive Glue {uid}",
        "unit": "litre"
    }).json()
    mat_id = mat["id"]

    # 1. First inward receipt: +30
    client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 30.0,
        "unit_price": 500.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "RECEIVED"
    })

    # 2. Second inward receipt: +70
    client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 70.0,
        "unit_price": 500.0,
        "purchase_date_ad": "2026-10-02",
        "purchase_date_bs": "2083-06-16",
        "status": "RECEIVED"
    })

    # 3. Third movement: manual outward adjustment (-20)
    client.post(f"/api/v1/purchases/materials/{mat_id}/adjust", json={
        "adjustment_type": "SAMPLE",
        "quantity": 20.0,
        "direction": -1,
        "movement_date_ad": "2026-10-03",
        "movement_date_bs": "2083-06-17",
        "notes": "Sent 20 litres to lab for quality assurance"
    })

    card = client.get(f"/api/v1/purchases/materials/{mat_id}/card").json()
    assert card["current_balance"] == 80.0
    assert len(card["movements"]) == 3
    assert card["movements"][0]["running_balance"] == 30.0
    assert card["movements"][1]["running_balance"] == 100.0
    assert card["movements"][2]["running_balance"] == 80.0


def test_zero_floor_protection_on_raw_material_adjustment(client):
    """
    Zero-floor invariant: Rejects any negative adjustment that would cause current stock to drop below zero.
    """
    uid = uuid.uuid4().hex[:5]
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-FLR-{uid}",
        "name": f"Supplier Floor {uid}"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-FLR-{uid}",
        "name": f"Leather Thread {uid}",
        "unit": "pcs"
    }).json()
    mat_id = mat["id"]

    # Inward 15 pcs
    client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 15.0,
        "unit_price": 100.0,
        "purchase_date_ad": "2026-10-05",
        "purchase_date_bs": "2083-06-19",
        "status": "RECEIVED"
    })

    # Attempt to deduct 20 pcs (breaches zero floor)
    adj_fail = client.post(f"/api/v1/purchases/materials/{mat_id}/adjust", json={
        "adjustment_type": "DAMAGE",
        "quantity": 20.0,
        "direction": -1,
        "movement_date_ad": "2026-10-06",
        "movement_date_bs": "2083-06-20",
        "notes": "Attempted over-deduction"
    })
    assert adj_fail.status_code == 422
    assert "INSUFFICIENT_RAW_MATERIAL" in adj_fail.json()["detail"]

    # Confirm stock remains strictly 15.0
    card = client.get(f"/api/v1/purchases/materials/{mat_id}/card").json()
    assert card["current_balance"] == 15.0


def test_production_bom_deduction_appends_raw_movement(client):
    """
    Integration with Production: Completing a batch appends BOM_ISSUE RawMaterialMovement
    and enforces physical raw material availability.
    """
    uid = uuid.uuid4().hex[:5]
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-BOMD-{uid}",
        "name": f"BOM Supplier {uid}"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-SOLET-{uid}",
        "name": f"Sole Rubber Compound {uid}",
        "unit": "kg"
    }).json()
    mat_id = mat["id"]

    # 1. Receive 100 kg
    client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 100.0,
        "unit_price": 300.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "RECEIVED"
    })

    # 2. Create Product
    prod = client.post("/api/v1/production/products", json={
        "code": f"PROD-BOM-{uid}",
        "name": f"Running Trainer {uid}",
        "category": "Shoe",
        "size": "42",
        "color": "Grey",
        "unit_price": 3500.0
    }).json()
    prod_id = prod["id"]

    # 3. Configure BOM: 2.0 kg per pair
    bom_res = client.post("/api/v1/production/bom", json={
        "product_id": prod_id,
        "raw_material_id": mat_id,
        "quantity_required": 2.0
    })
    assert bom_res.status_code == 200

    # 4. Produce 10 pairs (requires 20 kg <= 100 available)
    batch_res = client.post("/api/v1/production/batches", json={
        "product_id": prod_id,
        "target_quantity": 10.0,
        "produced_quantity": 10.0,
        "worker_count": 2,
        "date_ad": "2026-10-02",
        "date_bs": "2083-06-16",
        "notes": "Batch 10 pairs"
    })
    assert batch_res.status_code == 200
    batch = batch_res.json()

    # 5. Verify ledger balance = 80 kg and BOM_ISSUE row exists
    card = client.get(f"/api/v1/purchases/materials/{mat_id}/card").json()
    assert card["current_balance"] == 80.0
    assert len(card["movements"]) == 2

    bom_issue_mov = card["movements"][1]
    assert bom_issue_mov["direction"] == -1
    assert bom_issue_mov["quantity"] == 20.0
    assert bom_issue_mov["movement_type"] == "BOM_ISSUE"
    assert bom_issue_mov["reference_voucher"] == batch["batch_number"]

    # 6. Attempt producing 50 pairs (requires 100 kg > 80 available) -> Must reject with 422
    fail_batch = client.post("/api/v1/production/batches", json={
        "product_id": prod_id,
        "target_quantity": 50.0,
        "produced_quantity": 50.0,
        "worker_count": 5,
        "date_ad": "2026-10-03",
        "date_bs": "2083-06-17",
        "notes": "Excess batch"
    })
    assert fail_batch.status_code == 422
    assert "Insufficient Raw Material" in fail_batch.json()["detail"]


def test_viewer_role_blocked_from_grn_and_adjustments(client, viewer_client):
    """
    RBAC Gate: Viewer role must receive HTTP 403 when attempting mutations:
    - Creating POs
    - Receiving goods (GRN)
    - Manual stock adjustments
    Viewer can read stock cards with HTTP 200.
    """
    uid = uuid.uuid4().hex[:5]
    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-RBAC-{uid}",
        "name": f"Supplier RBAC {uid}"
    }).json()

    mat = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-RBAC-{uid}",
        "name": f"Shoe Laces {uid}",
        "unit": "pcs"
    }).json()
    mat_id = mat["id"]

    po = client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 10.0,
        "unit_price": 50.0,
        "purchase_date_ad": "2026-10-10",
        "purchase_date_bs": "2083-06-24",
        "status": "ORDERED"
    }).json()

    # 1. Viewer blocked from creating PO
    v_po = viewer_client.post("/api/v1/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat_id,
        "quantity": 5.0,
        "unit_price": 50.0,
        "purchase_date_ad": "2026-10-10",
        "purchase_date_bs": "2083-06-24"
    })
    assert v_po.status_code == 403

    # 2. Viewer blocked from receiving goods
    v_rec = viewer_client.post(f"/api/v1/purchases/{po['id']}/receive", json={
        "receipt_date_ad": "2026-10-10",
        "receipt_date_bs": "2083-06-24",
        "received_quantity": 10.0
    })
    assert v_rec.status_code == 403

    # 3. Viewer blocked from stock adjustments
    v_adj = viewer_client.post(f"/api/v1/purchases/materials/{mat_id}/adjust", json={
        "adjustment_type": "RECOUNT",
        "quantity": 2.0,
        "direction": 1,
        "movement_date_ad": "2026-10-10",
        "movement_date_bs": "2083-06-24"
    })
    assert v_adj.status_code == 403

    # 4. Viewer can read stock card
    v_card = viewer_client.get(f"/api/v1/purchases/materials/{mat_id}/card")
    assert v_card.status_code == 200
    assert v_card.json()["material"]["id"] == mat_id
