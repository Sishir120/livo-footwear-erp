"""test_production_batch_color_and_gallery.py

Targeted test suite for Phase 4A:
1. Online batch creation persists custom batch color.
2. Offline draft synchronization persists custom batch color.
3. Legacy offline draft payload (omitting color) succeeds backward-compatibly.
4. Custom batch color does NOT create product / SKU records.
5. Gallery upload with valid batch association links batch and returns batch metadata.
6. Gallery upload without batch association preserves fallback to product catalog color.
7. Gallery upload with cross-tenant batch returns HTTP 404.
8. Gallery upload with product-batch mismatch returns HTTP 422.
9. Gallery listing and image download enforce strict tenant isolation.
10. Idempotent offline sync replay does not duplicate batch or stock records.
"""

import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, ProductionBatch, StockMovement
from app.models.gallery import ProductImage
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_phase4a_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Company 1 (Primary)
    comp1 = db.query(Company).filter(Company.code == "P4A_CO1").first()
    if not comp1:
        comp1 = Company(name="Phase 4A Primary Co", code="P4A_CO1")
        db.add(comp1)
        db.commit()
        db.refresh(comp1)

    # Company 2 (Cross-tenant)
    comp2 = db.query(Company).filter(Company.code == "P4A_CO2").first()
    if not comp2:
        comp2 = Company(name="Phase 4A Secondary Co", code="P4A_CO2")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # Warehouse for Company 1
    wh1 = db.query(Warehouse).filter(Warehouse.company_id == comp1.id).first()
    if not wh1:
        wh1 = Warehouse(company_id=comp1.id, name="P4A Main Warehouse", code="WH-P4A-1", is_active=True)
        db.add(wh1)
        db.commit()
        db.refresh(wh1)

    # Warehouse for Company 2
    wh2 = db.query(Warehouse).filter(Warehouse.company_id == comp2.id).first()
    if not wh2:
        wh2 = Warehouse(company_id=comp2.id, name="P4A Other Warehouse", code="WH-P4A-2", is_active=True)
        db.add(wh2)
        db.commit()
        db.refresh(wh2)

    # User for Company 1 (Editor)
    user1 = db.query(User).filter(User.username == "p4a_editor1").first()
    if not user1:
        user1 = User(
            company_id=comp1.id,
            name="P4A Editor 1",
            username="p4a_editor1",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(user1)

    # User for Company 2 (Editor)
    user2 = db.query(User).filter(User.username == "p4a_editor2").first()
    if not user2:
        user2 = User(
            company_id=comp2.id,
            name="P4A Editor 2",
            username="p4a_editor2",
            password_hash=get_password_hash("Pass123!"),
            role="editor",
            active=True
        )
        db.add(user2)

    # Products for Company 1
    p1 = db.query(Product).filter(Product.company_id == comp1.id, Product.code == "P4A-PROD-01").first()
    if not p1:
        p1 = Product(company_id=comp1.id, code="P4A-PROD-01", name="Trail Runner", category="Shoe", color="Navy", size="41", unit_price=2200.0)
        db.add(p1)

    p2 = db.query(Product).filter(Product.company_id == comp1.id, Product.code == "P4A-PROD-02").first()
    if not p2:
        p2 = Product(company_id=comp1.id, code="P4A-PROD-02", name="Alpine Trekker", category="Boot", color="Black", size="42", unit_price=3500.0)
        db.add(p2)

    # Product for Company 2
    p3 = db.query(Product).filter(Product.company_id == comp2.id, Product.code == "P4A-PROD-03").first()
    if not p3:
        p3 = Product(company_id=comp2.id, code="P4A-PROD-03", name="City Loafer", category="Shoe", color="Tan", size="40", unit_price=1900.0)
        db.add(p3)

    db.commit()
    db.refresh(comp1)
    db.refresh(comp2)
    db.refresh(wh1)
    db.refresh(wh2)
    db.refresh(user1)
    db.refresh(user2)
    db.refresh(p1)
    db.refresh(p2)
    db.refresh(p3)

    # Create a batch in Company 2 for cross-tenant testing
    batch_comp2 = db.query(ProductionBatch).filter(ProductionBatch.company_id == comp2.id, ProductionBatch.batch_number == "BATCH-P4A-CO2-001").first()
    if not batch_comp2:
        batch_comp2 = ProductionBatch(
            company_id=comp2.id,
            product_id=p3.id,
            batch_number="BATCH-P4A-CO2-001",
            date_ad="2026-10-12",
            date_bs="2083-06-26",
            target_quantity=50,
            produced_quantity=50,
            worker_count=1,
            color="Burgundy",
            status="completed"
        )
        db.add(batch_comp2)
        db.commit()
        db.refresh(batch_comp2)

    data = {
        "comp1_id": comp1.id,
        "comp2_id": comp2.id,
        "wh1_id": wh1.id,
        "wh2_id": wh2.id,
        "user1": "p4a_editor1",
        "user2": "p4a_editor2",
        "prod1_id": p1.id,
        "prod2_id": p2.id,
        "prod3_id": p3.id,
        "batch_comp2_id": batch_comp2.id
    }
    db.close()
    return data


def _login(client: TestClient, username: str, password: str = "Pass123!"):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not found in login response"
    return {COOKIE_NAME: token}


def _make_dummy_jpeg():
    # Valid JPEG magic bytes header
    return io.BytesIO(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 256)


def test_online_batch_creation_persists_custom_color(setup_phase4a_env):
    """1. POST /api/v1/production/batches persists custom batch color."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    payload = {
        "product_id": prod_id,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "target_quantity": 80,
        "produced_quantity": 80,
        "worker_count": 4,
        "color": "Crimson Red"
    }

    resp = client.post("/api/v1/production/batches", json=payload, cookies=cookies)
    assert resp.status_code in (200, 201), f"Batch creation failed: {resp.text}"
    data = resp.json()
    batch_id = data["id"]
    batch_no = data["batch_number"]
    assert data.get("color") == "Crimson Red"

    # Verify directly in database using primary key id
    db = SessionLocal()
    b = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    assert b is not None
    assert b.color == "Crimson Red"
    db.close()


def test_offline_draft_sync_persists_custom_color(setup_phase4a_env):
    """2. POST /api/v1/production/sync/draft persists custom color."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    idem_key = f"prod:draft:{uuid.uuid4()}"
    draft_payload = {
        "idempotency_key": idem_key,
        "created_at_device": "2026-10-12T09:00:00Z",
        "product_id": prod_id,
        "warehouse_id": setup_phase4a_env["wh1_id"],
        "line": "Line 2",
        "shift": "Shift 2",
        "worker_count": 6,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "color": "Desert Khaki",
        "size_quantities": {"41": 35, "42": 45},
        "notes": "Custom color test run"
    }

    resp = client.post("/api/v1/production/sync/draft", json=draft_payload, cookies=cookies)
    assert resp.status_code == 200, f"Draft sync failed: {resp.text}"
    res_data = resp.json()
    assert res_data.get("sync_status") == "ACCEPTED"
    batch_id = res_data["batch_id"]

    # Verify in DB
    db = SessionLocal()
    b = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    assert b is not None
    assert b.color == "Desert Khaki"
    assert b.produced_quantity == 80
    db.close()


def test_legacy_offline_payload_without_color_succeeds(setup_phase4a_env):
    """3. POST /api/v1/production/sync/draft succeeds backward-compatibly when color is omitted."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    idem_key = f"prod:draft:{uuid.uuid4()}"
    legacy_payload = {
        "idempotency_key": idem_key,
        "created_at_device": "2026-10-12T09:05:00Z",
        "product_id": prod_id,
        "warehouse_id": setup_phase4a_env["wh1_id"],
        "line": "Line 1",
        "shift": "Shift 1",
        "worker_count": 4,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "size_quantities": {"41": 20}
        # Notice: 'color' is omitted entirely!
    }

    resp = client.post("/api/v1/production/sync/draft", json=legacy_payload, cookies=cookies)
    assert resp.status_code == 200, f"Legacy draft sync failed: {resp.text}"
    res_data = resp.json()
    assert res_data.get("sync_status") == "ACCEPTED"
    batch_id = res_data["batch_id"]

    db = SessionLocal()
    b = db.query(ProductionBatch).filter(ProductionBatch.id == batch_id).first()
    assert b is not None
    assert b.color is None
    db.close()


def test_custom_color_does_not_create_new_sku_or_product(setup_phase4a_env):
    """4. Custom batch colors do NOT create new Product/SKU catalog records."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    db = SessionLocal()
    initial_product_count = db.query(Product).filter(Product.company_id == setup_phase4a_env["comp1_id"]).count()
    db.close()

    idem_key = f"prod:draft:{uuid.uuid4()}"
    draft_payload = {
        "idempotency_key": idem_key,
        "created_at_device": "2026-10-12T09:10:00Z",
        "product_id": prod_id,
        "warehouse_id": setup_phase4a_env["wh1_id"],
        "line": "Line 3",
        "shift": "Shift 1",
        "worker_count": 3,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "color": "Neon Orange Flare",
        "size_quantities": {"41": 15}
    }

    resp = client.post("/api/v1/production/sync/draft", json=draft_payload, cookies=cookies)
    assert resp.status_code == 200

    db = SessionLocal()
    after_product_count = db.query(Product).filter(Product.company_id == setup_phase4a_env["comp1_id"]).count()
    assert after_product_count == initial_product_count, "Product catalog count altered by custom batch color!"

    # Also assert no product exists with color "Neon Orange Flare"
    novel_prod = db.query(Product).filter(Product.color == "Neon Orange Flare").first()
    assert novel_prod is None, "Rogue Product SKU was generated for custom batch color!"
    db.close()


def test_gallery_upload_with_valid_batch_association(setup_phase4a_env):
    """5. Upload image with valid batch association links batch and returns batch metadata."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    # First, create a batch for prod_id with color "Forest Green"
    batch_payload = {
        "product_id": prod_id,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "target_quantity": 40,
        "produced_quantity": 40,
        "worker_count": 2,
        "color": "Forest Green"
    }
    b_resp = client.post("/api/v1/production/batches", json=batch_payload, cookies=cookies)
    assert b_resp.status_code in (200, 201)
    batch_data = b_resp.json()
    batch_id = batch_data["id"]
    batch_no = batch_data["batch_number"]

    # Now upload gallery photo with production_batch_id
    img_stream = _make_dummy_jpeg()
    file_tuple = ("forest_runner.jpg", img_stream, "image/jpeg")

    up_resp = client.post(
        f"/api/v1/gallery/upload/{prod_id}?production_batch_id={batch_id}",
        files={"file": file_tuple},
        cookies=cookies
    )
    assert up_resp.status_code == 201, f"Upload failed: {up_resp.text}"
    img_data = up_resp.json()

    assert img_data["product_id"] == prod_id
    assert img_data["production_batch_id"] == batch_id
    assert img_data["batch_number"] == batch_no
    assert img_data["batch_color"] == "Forest Green"
    assert img_data["batch_date_bs"] == "2083-06-26"

    # Also verify GET /api/v1/gallery lists this item with batch metadata
    list_resp = client.get(f"/api/v1/gallery?product_id={prod_id}&production_batch_id={batch_id}", cookies=cookies)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    matched = next((it for it in items if it["id"] == img_data["id"]), None)
    assert matched is not None
    assert matched["batch_number"] == batch_no
    assert matched["batch_color"] == "Forest Green"


def test_gallery_upload_without_batch_association_preserves_historical_fallback(setup_phase4a_env):
    """6. Upload image without batch association preserves fallback to product catalog color."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]  # Product 1 has catalog color "Navy"

    img_stream = _make_dummy_jpeg()
    file_tuple = ("catalog_runner.jpg", img_stream, "image/jpeg")

    up_resp = client.post(
        f"/api/v1/gallery/upload/{prod_id}",
        files={"file": file_tuple},
        cookies=cookies
    )
    assert up_resp.status_code == 201, f"Upload failed: {up_resp.text}"
    img_data = up_resp.json()

    assert img_data["product_id"] == prod_id
    assert img_data["production_batch_id"] is None
    assert img_data["batch_number"] is None
    # Falls back to product catalog color
    assert img_data["batch_color"] == "Navy"
    assert img_data["batch_date_bs"] is None


def test_gallery_upload_cross_tenant_batch_returns_404(setup_phase4a_env):
    """7. Linking an inaccessible cross-tenant batch returns HTTP 404 (IDOR protection)."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])  # Company 1
    prod_id = setup_phase4a_env["prod1_id"]                # Product in Company 1
    foreign_batch_id = setup_phase4a_env["batch_comp2_id"] # Batch in Company 2

    img_stream = _make_dummy_jpeg()
    file_tuple = ("idor_attempt.jpg", img_stream, "image/jpeg")

    up_resp = client.post(
        f"/api/v1/gallery/upload/{prod_id}?production_batch_id={foreign_batch_id}",
        files={"file": file_tuple},
        cookies=cookies
    )
    assert up_resp.status_code == 404, f"Expected 404 for cross-tenant batch, got {up_resp.status_code}: {up_resp.text}"
    assert "not found" in up_resp.json()["detail"].lower()


def test_gallery_upload_product_mismatch_returns_422(setup_phase4a_env):
    """8. Linking a batch that belongs to Product X when uploading for Product Y returns HTTP 422."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod1_id = setup_phase4a_env["prod1_id"]
    prod2_id = setup_phase4a_env["prod2_id"]

    # Create batch explicitly linked to prod1_id
    batch_payload = {
        "product_id": prod1_id,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "target_quantity": 25,
        "produced_quantity": 25,
        "worker_count": 2,
        "color": "Teal"
    }
    b_resp = client.post("/api/v1/production/batches", json=batch_payload, cookies=cookies)
    assert b_resp.status_code in (200, 201)
    prod1_batch_id = b_resp.json()["id"]

    # Attempt to upload image for prod2_id with batch of prod1_id
    img_stream = _make_dummy_jpeg()
    file_tuple = ("mismatch.jpg", img_stream, "image/jpeg")

    up_resp = client.post(
        f"/api/v1/gallery/upload/{prod2_id}?production_batch_id={prod1_batch_id}",
        files={"file": file_tuple},
        cookies=cookies
    )
    assert up_resp.status_code == 422, f"Expected 422 for mismatched product-batch, got {up_resp.status_code}: {up_resp.text}"
    assert f"belongs to product #{prod1_id}" in up_resp.json()["detail"]


def test_gallery_list_and_download_tenant_isolation(setup_phase4a_env):
    """9. Audit gallery listing and download for strict multi-tenant isolation."""
    client = TestClient(app)
    cookies1 = _login(client, setup_phase4a_env["user1"])
    cookies2 = _login(client, setup_phase4a_env["user2"])

    # Upload an image in Company 2
    prod3_id = setup_phase4a_env["prod3_id"]
    img_stream = _make_dummy_jpeg()
    file_tuple = ("comp2_image.jpg", img_stream, "image/jpeg")

    up_resp2 = client.post(
        f"/api/v1/gallery/upload/{prod3_id}",
        files={"file": file_tuple},
        cookies=cookies2
    )
    assert up_resp2.status_code == 201
    comp2_img_id = up_resp2.json()["id"]

    # 1. Company 1 listing should NOT contain comp2_img_id
    list1 = client.get("/api/v1/gallery", cookies=cookies1)
    assert list1.status_code == 200
    ids_in_co1 = [item["id"] for item in list1.json()]
    assert comp2_img_id not in ids_in_co1, "Cross-tenant image leaked in gallery listing!"

    # 2. Company 1 attempting to download Company 2 image must return 404
    dl_attempt = client.get(f"/api/v1/gallery/images/{comp2_img_id}/download", cookies=cookies1)
    assert dl_attempt.status_code == 404, f"Expected 404 for cross-tenant download, got {dl_attempt.status_code}"


def test_idempotent_offline_sync_replay_does_not_duplicate_batch(setup_phase4a_env):
    """10. Offline draft replay with duplicate idempotency_key is idempotent and creates no duplicate records."""
    client = TestClient(app)
    cookies = _login(client, setup_phase4a_env["user1"])
    prod_id = setup_phase4a_env["prod1_id"]

    idem_key = f"prod:draft:{uuid.uuid4()}"
    draft_payload = {
        "idempotency_key": idem_key,
        "created_at_device": "2026-10-12T09:20:00Z",
        "product_id": prod_id,
        "warehouse_id": setup_phase4a_env["wh1_id"],
        "line": "Line 1",
        "shift": "Shift 1",
        "worker_count": 5,
        "date_ad": "2026-10-12",
        "date_bs": "2083-06-26",
        "color": "Slate Gray",
        "size_quantities": {"41": 50},
        "notes": "Idempotency replay test"
    }

    # Initial send
    resp1 = client.post("/api/v1/production/sync/draft", json=draft_payload, cookies=cookies)
    assert resp1.status_code == 200
    data1 = resp1.json()
    batch_no1 = data1["batch_number"]

    # Replay send (identical key)
    resp2 = client.post("/api/v1/production/sync/draft", json=draft_payload, cookies=cookies)
    assert resp2.status_code == 200
    data2 = resp2.json()
    batch_no2 = data2["batch_number"]

    assert batch_no1 == batch_no2, "Idempotent replay returned a different batch number!"

    # Verify database has only one batch with this batch number for this tenant
    db = SessionLocal()
    batches = db.query(ProductionBatch).filter(
        ProductionBatch.company_id == setup_phase4a_env["comp1_id"],
        ProductionBatch.batch_number == batch_no1
    ).all()
    assert len(batches) == 1, f"Found {len(batches)} batches for batch number {batch_no1} in company!"
    db.close()
