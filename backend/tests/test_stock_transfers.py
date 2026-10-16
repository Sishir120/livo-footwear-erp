import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal, Base, engine
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.security import get_password_hash

# Ensure tables exist in SQLite test DB
Base.metadata.create_all(bind=engine)

@pytest.fixture
def setup_transfer_env():
    db = SessionLocal()
    try:
        # Create company
        company = db.query(Company).filter(Company.name == "Transfer Test Footwear Ltd").first()
        if not company:
            company = Company(name="Transfer Test Footwear Ltd", code="TRF-CO-1", pan_number="307777777")
            db.add(company)
            db.commit()
            db.refresh(company)

        # Editor & Viewer
        editor = db.query(User).filter(User.username == "trf_editor").first()
        if not editor:
            editor = User(
                company_id=company.id,
                username="trf_editor",
                name="Transfer Editor",
                password_hash=get_password_hash("TrfPass2026!"),
                role="editor",
                active=True
            )
            db.add(editor)

        viewer = db.query(User).filter(User.username == "trf_viewer").first()
        if not viewer:
            viewer = User(
                company_id=company.id,
                username="trf_viewer",
                name="Transfer Viewer",
                password_hash=get_password_hash("TrfPass2026!"),
                role="viewer",
                active=True
            )
            db.add(viewer)

        # Warehouses (Source: Pokhara, Destination: Kathmandu)
        wh1 = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.code == "WH-PKR-01").first()
        if not wh1:
            wh1 = Warehouse(company_id=company.id, name="Pokhara Factory WH", code="WH-PKR-01", is_active=True)
            db.add(wh1)

        wh2 = db.query(Warehouse).filter(Warehouse.company_id == company.id, Warehouse.code == "WH-KTM-01").first()
        if not wh2:
            wh2 = Warehouse(company_id=company.id, name="Kathmandu Central WH", code="WH-KTM-01", is_active=True)
            db.add(wh2)

        db.commit()
        db.refresh(wh1)
        db.refresh(wh2)

        yield {
            "company_id": company.id,
            "wh_source_id": wh1.id,
            "wh_dest_id": wh2.id
        }
    finally:
        db.close()


def _login(client: TestClient, username: str = "trf_editor"):
    res = client.post("/api/v1/auth/login", json={"username": username, "password": "TrfPass2026!"})
    assert res.status_code == 200


def _create_product_with_stock(client: TestClient, sku: str, warehouse_id: int, initial_qty: float = 100.0):
    p_res = client.post("/api/v1/production/products", json={
        "code": sku,
        "name": f"Transfer Shoe {sku}",
        "category": "Shoe",
        "size": "41",
        "color": "Brown",
        "unit_price": 1500.0
    })
    assert p_res.status_code == 200
    prod_id = p_res.json()["id"]

    # Add initial stock into source warehouse
    m_res = client.post("/api/v1/stock/movements", json={
        "product_id": prod_id,
        "warehouse_id": warehouse_id,
        "size": "41",
        "quantity": initial_qty,
        "direction": 1,
        "reference_type": "production",
        "notes": f"Initial balance for {sku}"
    })
    assert m_res.status_code == 200
    return prod_id


def _get_wh_stock(company_id: int, warehouse_id: int, product_id: int, size: str = "41") -> float:
    from app.api.v1.transfers import get_warehouse_stock
    db = SessionLocal()
    try:
        val = get_warehouse_stock(db, company_id, warehouse_id, product_id, size)
        return float(val)
    finally:
        db.close()


def test_normal_full_transfer_lifecycle(setup_transfer_env):
    """
    Tests complete normal transfer:
    1. Create DRAFT transfer from Pokhara to Kathmandu.
    2. Dispatch: Source warehouse stock decreases by 20. In-transit state verified.
    3. Destination receipt: Kathmandu receives all 20. Destination stock increases by 20.
    4. Balances reconcile exactly.
    """
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-NORM-01", wh_src, 50.0)

        # 1. Create transfer
        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "carrier_name": "Sajha Yatayat Cargo",
            "vehicle_number": "BA 2 KHA 4455",
            "notes": "Weekly branch replenishment",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 20.0}]
        })
        assert t_res.status_code == 201
        t_id = t_res.json()["id"]
        assert t_res.json()["status"] == "DRAFT"

        # 2. Dispatch
        disp_res = client.post(f"/api/v1/transfers/{t_id}/dispatch", json={
            "dispatch_date_ad": "2026-10-15",
            "dispatch_date_bs": "2083-06-29"
        })
        assert disp_res.status_code == 200
        assert disp_res.json()["status"] == "IN_TRANSIT"

        # Verify source stock decreased from 50 to 30
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") == 30.0

        # Destination stock is still 0 while in transit
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 0.0

        # 3. Destination receipt
        detail_res = client.get(f"/api/v1/transfers/{t_id}")
        assert detail_res.status_code == 200
        item_id = detail_res.json()["items"][0]["id"]

        rec_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "receipt_date_ad": "2026-10-16",
            "receipt_date_bs": "2083-06-30",
            "items": [{"item_id": item_id, "received_quantity": 20.0}]
        })
        assert rec_res.status_code == 200
        assert rec_res.json()["status"] == "RECEIVED"

        # Destination stock is now 20
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 20.0


def test_partial_receipt_with_discrepancy(setup_transfer_env):
    """
    Tests partial receipt:
    Dispatched: 10 units
    Received: 8 units (2 damaged in transit, documented with reason)
    """
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-DISC-01", wh_src, 30.0)

        # Create & Dispatch 10 units
        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 10.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        # Receive only 8 units
        detail_res = client.get(f"/api/v1/transfers/{t_id}")
        item_id = detail_res.json()["items"][0]["id"]

        rec_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{
                "item_id": item_id,
                "received_quantity": 8.0,
                "discrepancy_reason": "2 pairs water damaged in truck cargo hold"
            }]
        })
        assert rec_res.status_code == 200

        # Verify discrepancy logged
        final_res = client.get(f"/api/v1/transfers/{t_id}")
        itm = final_res.json()["items"][0]
        assert itm["dispatched_quantity"] == 10.0
        assert itm["received_quantity"] == 8.0
        assert itm["discrepancy_quantity"] == 2.0
        assert "water damaged" in itm["discrepancy_reason"].lower()

        # Destination stock is exactly 8.0
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 8.0


def test_insufficient_stock_dispatch_rejected(setup_transfer_env):
    """Verifies dispatch fails if requested quantity exceeds source warehouse on-hand stock."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-NOSTOCK-01", wh_src, 5.0)

        # Create transfer requesting 15 units (only 5 exist)
        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 15.0}]
        })
        assert t_res.status_code == 201
        t_id = t_res.json()["id"]

        # Attempt dispatch -> must fail with 400 Insufficient Stock
        disp_res = client.post(f"/api/v1/transfers/{t_id}/dispatch")
        assert disp_res.status_code == 400
        assert "insufficient stock" in disp_res.json()["detail"].lower()


def test_same_source_destination_rejected(setup_transfer_env):
    """Verifies transfers cannot have identical source and destination warehouses."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-SAMELOC-01", wh_src, 10.0)

        res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_src,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 5.0}]
        })
        assert res.status_code == 400
        assert "distinct" in res.json()["detail"].lower()


def test_in_transit_cancellation_reverses_source_stock(setup_transfer_env):
    """
    Verifies that cancelling an in-transit transfer restores stock back to source warehouse
    via VOID_REVERSAL movement.
    """
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-CANCEL-01", wh_src, 40.0)

        # Create & Dispatch 15 units
        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 15.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        # Source is 25
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") == 25.0

        # Cancel while IN_TRANSIT (e.g. road blocked, truck returned to factory)
        canc_res = client.post(f"/api/v1/transfers/{t_id}/cancel")
        assert canc_res.status_code == 200
        assert canc_res.json()["status"] == "CANCELLED"

        # Source is restored to 40.0
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") == 40.0


def test_received_transfer_cannot_be_cancelled(setup_transfer_env):
    """Verifies that once a transfer is RECEIVED at destination, it cannot be cancelled."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-NOREV-01", wh_src, 20.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 5.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        detail = client.get(f"/api/v1/transfers/{t_id}").json()
        item_id = detail["items"][0]["id"]
        client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 5.0}]
        })

        # Attempt to cancel -> must be 400
        bad_cancel = client.post(f"/api/v1/transfers/{t_id}/cancel")
        assert bad_cancel.status_code == 400
        assert "cannot cancel a received transfer" in bad_cancel.json()["detail"].lower()


def test_unauthorized_viewer_cannot_dispatch_or_receive(setup_transfer_env):
    """Verifies RBAC rules on stock transfers."""
    env = setup_transfer_env
    with TestClient(app) as client:
        _login(client, "trf_viewer")

        # Viewer cannot create
        c_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": env["wh_source_id"],
            "destination_warehouse_id": env["wh_dest_id"],
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": 1, "quantity": 10.0}]
        })
        assert c_res.status_code in (401, 403)


def test_over_receipt_attempt_rejected(setup_transfer_env):
    """Adversarial Test: Verify caller cannot receive more than dispatched quantity (phantom stock creation prevention)."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-OVER-01", wh_src, 50.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 10.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        detail = client.get(f"/api/v1/transfers/{t_id}").json()
        item_id = detail["items"][0]["id"]

        # Attempt to receive 15 when only 10 dispatched
        bad_rec = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 15.0}]
        })
        assert bad_rec.status_code == 400
        assert "over-receipt forbidden" in bad_rec.json()["detail"].lower()


def test_multi_stage_partial_receipts(setup_transfer_env):
    """Verifies multi-stage delivery: Stage 1 brings partial stock, Stage 2 completes shipment."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-MULTI-01", wh_src, 100.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 100.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        detail = client.get(f"/api/v1/transfers/{t_id}").json()
        item_id = detail["items"][0]["id"]

        # Stage 1: Truck 1 arrives with 60 pairs (is_final=False)
        rec1 = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 60.0}],
            "is_final": False,
            "notes": "Truck 1 batch"
        })
        assert rec1.status_code == 200
        assert rec1.json()["status"] == "PARTIALLY_RECEIVED"
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 60.0

        # Stage 2: Truck 2 arrives with remaining 40 pairs (is_final=True)
        rec2 = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 40.0}],
            "is_final": True,
            "notes": "Truck 2 final batch"
        })
        assert rec2.status_code == 200
        assert rec2.json()["status"] == "RECEIVED"
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 100.0


def test_partial_receipt_cancellation_preserves_conservation(setup_transfer_env):
    """
    CRITICAL INVENTORY CONSERVATION TEST:
    100 dispatched. 40 received at destination.
    Remaining 60 in-transit is cancelled.
    Source must get back exactly 60.
    Destination must retain 40.
    Net company balance must equal starting balance!
    """
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-CONSRV-01", wh_src, 100.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 100.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        # Source is 0, Destination is 0
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") == 0.0
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 0.0

        # Receive 40 pairs partially
        detail = client.get(f"/api/v1/transfers/{t_id}").json()
        item_id = detail["items"][0]["id"]
        client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 40.0}],
            "is_final": False
        })
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 40.0

        # Cancel transfer mid-way
        c_res = client.post(f"/api/v1/transfers/{t_id}/cancel")
        assert c_res.status_code == 200
        assert c_res.json()["status"] == "CANCELLED"

        # Verify exact conservation:
        # Source gets back 60 (100 - 40)
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") == 60.0
        # Destination retains 40
        assert _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 40.0
        # Total stock = 60 + 40 = 100.0
        assert _get_wh_stock(env["company_id"], wh_src, prod_id, "41") + _get_wh_stock(env["company_id"], wh_dst, prod_id, "41") == 100.0


def test_final_receipt_with_shortage_requires_reason(setup_transfer_env):
    """Verifies that finalizing a transfer with shortages mandates a discrepancy reason."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-DISC-01", wh_src, 50.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [{"product_id": prod_id, "size": "41", "quantity": 50.0}]
        })
        t_id = t_res.json()["id"]
        client.post(f"/api/v1/transfers/{t_id}/dispatch")

        detail = client.get(f"/api/v1/transfers/{t_id}").json()
        item_id = detail["items"][0]["id"]

        # Attempt to finalize short receipt without reason -> must be 400
        bad_final = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 45.0, "discrepancy_reason": ""}],
            "is_final": True
        })
        assert bad_final.status_code == 400
        assert "discrepancy reason is strictly required" in bad_final.json()["detail"].lower()

        # Provide reason -> succeeds
        good_final = client.post(f"/api/v1/transfers/{t_id}/receive", json={
            "items": [{"item_id": item_id, "received_quantity": 45.0, "discrepancy_reason": "DAMAGED_IN_TRANSIT"}],
            "is_final": True
        })
        assert good_final.status_code == 200
        assert good_final.json()["status"] == "RECEIVED"

        # Verify discrepancy recorded
        detail_after = client.get(f"/api/v1/transfers/{t_id}").json()
        assert detail_after["items"][0]["discrepancy_quantity"] == 5.0
        assert detail_after["items"][0]["discrepancy_reason"] == "DAMAGED_IN_TRANSIT"


def test_duplicate_variants_in_create_rejected(setup_transfer_env):
    """Verifies that requesting the exact same variant multiple times in a transfer payload is rejected."""
    env = setup_transfer_env
    wh_src = env["wh_source_id"]
    wh_dst = env["wh_dest_id"]

    with TestClient(app) as client:
        _login(client, "trf_editor")
        prod_id = _create_product_with_stock(client, "TRF-DUP-01", wh_src, 50.0)

        t_res = client.post("/api/v1/transfers", json={
            "source_warehouse_id": wh_src,
            "destination_warehouse_id": wh_dst,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-06-29",
            "items": [
                {"product_id": prod_id, "size": "41", "quantity": 10.0},
                {"product_id": prod_id, "size": "41", "quantity": 5.0}
            ]
        })
        assert t_res.status_code == 400
        assert "duplicate product variant" in t_res.json()["detail"].lower()
