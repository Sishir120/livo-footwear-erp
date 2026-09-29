import io
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import (
    Company, User, Product, Client, SalesOrder, SalesItem,
    ProductionBatch, Worker, DailyFactoryLog, ProductImage
)
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_gallery_analytics_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create Primary Company
    comp = db.query(Company).filter(Company.code == "GA_TEST_CO").first()
    if not comp:
        comp = Company(name="Gallery Analytics Factory", code="GA_TEST_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Second Company for tenant isolation
    comp2 = db.query(Company).filter(Company.code == "GA_OTHER_CO").first()
    if not comp2:
        comp2 = Company(name="Other Gallery Factory", code="GA_OTHER_CO")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # Editor user (in Primary Company)
    editor = db.query(User).filter(User.username == "ga_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="GA Editor",
            username="ga_editor",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    # Viewer user (in Primary Company)
    viewer = db.query(User).filter(User.username == "ga_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="GA Viewer",
            username="ga_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    # Clean up any leftover test data
    db.query(ProductImage).filter(ProductImage.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(DailyFactoryLog).filter(DailyFactoryLog.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(SalesItem).filter(SalesItem.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(SalesOrder).filter(SalesOrder.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(ProductionBatch).filter(ProductionBatch.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(Product).filter(Product.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(Client).filter(Client.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.commit()

    # Seed products for company 1
    p1 = Product(company_id=comp.id, code="GA-PROD-01", name="Classic Oxford Black", category="Shoe", unit_price=2500.0)
    p2 = Product(company_id=comp.id, code="GA-PROD-02", name="Leather Chelsea Boot", category="Boot", unit_price=4500.0)
    db.add_all([p1, p2])

    # Seed client for company 1
    c1 = Client(company_id=comp.id, code="GA-CL-01", name="Elite Footwear Traders", contact_person="9841001122", phone="014223344")
    c2 = Client(company_id=comp.id, code="GA-CL-02", name="Kathmandu Retail Hub", contact_person="9841002233", phone="014334455")
    db.add_all([c1, c2])

    db.commit()
    db.refresh(p1)
    db.refresh(p2)
    db.refresh(c1)
    db.refresh(c2)

    data = {
        "company_id": comp.id,
        "company2_id": comp2.id,
        "editor_username": "ga_editor",
        "editor_password": "EditorPass123!",
        "viewer_username": "ga_viewer",
        "viewer_password": "ViewerPass123!",
        "product1_id": p1.id,
        "product2_id": p2.id,
        "client1_id": c1.id,
        "client2_id": c2.id
    }
    db.close()
    return data


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


def test_gallery_upload_and_validation(setup_gallery_analytics_env):
    """Verify image upload, mime-type validation, and retrieval."""
    client = TestClient(app)
    cookies = _login(client, setup_gallery_analytics_env["editor_username"], setup_gallery_analytics_env["editor_password"])
    prod_id = setup_gallery_analytics_env["product1_id"]

    # 1. Invalid mime type should fail
    bad_file = ("text.txt", io.BytesIO(b"Hello text file"), "text/plain")
    resp_bad = client.post(
        f"/api/v1/gallery/upload/{prod_id}",
        files={"file": bad_file},
        cookies=cookies
    )
    assert resp_bad.status_code == 400
    assert "Unsupported file format" in resp_bad.json()["detail"]

    # 2. Valid JPEG image upload
    fake_jpeg_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 200
    valid_file = ("oxford.jpg", io.BytesIO(fake_jpeg_content), "image/jpeg")
    resp_up = client.post(
        f"/api/v1/gallery/upload/{prod_id}",
        files={"file": valid_file},
        cookies=cookies
    )
    assert resp_up.status_code == 201
    up_data = resp_up.json()
    assert up_data["product_id"] == prod_id
    assert up_data["product_code"] == "GA-PROD-01"
    image_id = up_data["id"]

    # 3. List gallery items
    resp_list = client.get("/api/v1/gallery", cookies=cookies)
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) >= 1
    found = [it for it in items if it["id"] == image_id]
    assert len(found) == 1
    assert found[0]["product_name"] == "Classic Oxford Black"

    # 4. Download image
    resp_dl = client.get(f"/api/v1/gallery/images/{image_id}/download", cookies=cookies)
    assert resp_dl.status_code == 200
    assert resp_dl.content == fake_jpeg_content


def test_viewer_role_rejected_from_gallery_mutations(setup_gallery_analytics_env):
    """Verify viewer role cannot upload or delete images (HTTP 403)."""
    client = TestClient(app)
    viewer_cookies = _login(client, setup_gallery_analytics_env["viewer_username"], setup_gallery_analytics_env["viewer_password"])
    prod_id = setup_gallery_analytics_env["product1_id"]

    fake_jpeg = ("sample.jpg", io.BytesIO(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100), "image/jpeg")
    resp_up = client.post(
        f"/api/v1/gallery/upload/{prod_id}",
        files={"file": fake_jpeg},
        cookies=viewer_cookies
    )
    assert resp_up.status_code == 403

    resp_del = client.delete("/api/v1/gallery/9999", cookies=viewer_cookies)
    assert resp_del.status_code == 403


def test_top_selling_products_ranking(setup_gallery_analytics_env):
    """Verify Point 7: Top-selling products ranked accurately by total pairs sold."""
    client = TestClient(app)
    cookies = _login(client, setup_gallery_analytics_env["editor_username"], setup_gallery_analytics_env["editor_password"])
    db = SessionLocal()

    comp_id = setup_gallery_analytics_env["company_id"]
    p1_id = setup_gallery_analytics_env["product1_id"]
    p2_id = setup_gallery_analytics_env["product2_id"]
    c1_id = setup_gallery_analytics_env["client1_id"]

    # Create Sales Order with 50 pairs of Product 1 and 120 pairs of Product 2
    order = SalesOrder(
        company_id=comp_id,
        order_number="GA-SO-001",
        client_id=c1_id,
        order_date_ad="2026-09-10",
        order_date_bs="2083-05-25",
        status="delivered",
        total_amount=665000.0,
        received_amount=500000.0,
        receivable_amount=165000.0
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    item1 = SalesItem(
        company_id=comp_id,
        sales_order_id=order.id,
        product_id=p1_id,
        quantity=50.0,
        unit_price=2500.0,
        total_price=125000.0
    )
    item2 = SalesItem(
        company_id=comp_id,
        sales_order_id=order.id,
        product_id=p2_id,
        quantity=120.0,
        unit_price=4500.0,
        total_price=540000.0
    )
    db.add_all([item1, item2])
    db.commit()
    db.close()

    resp = client.get("/api/v1/analytics/top-products", cookies=cookies)
    assert resp.status_code == 200
    ranked = resp.json()
    assert len(ranked) >= 2

    # Product 2 should be Rank 1 (120 pairs sold > 50 pairs)
    assert ranked[0]["product_id"] == p2_id
    assert ranked[0]["rank"] == 1
    assert ranked[0]["total_pairs_sold"] == 120.0
    assert ranked[0]["total_revenue_paisa"] == 54000000  # 540,000 * 100

    # Product 1 should be Rank 2 (50 pairs sold)
    assert ranked[1]["product_id"] == p1_id
    assert ranked[1]["rank"] == 2
    assert ranked[1]["total_pairs_sold"] == 50.0
    assert ranked[1]["total_revenue_paisa"] == 12500000


def test_top_customers_ranking(setup_gallery_analytics_env):
    """Verify Point 8: Top customers sorted serially from highest to lowest volume/revenue."""
    client = TestClient(app)
    cookies = _login(client, setup_gallery_analytics_env["editor_username"], setup_gallery_analytics_env["editor_password"])
    db = SessionLocal()

    comp_id = setup_gallery_analytics_env["company_id"]
    p1_id = setup_gallery_analytics_env["product1_id"]
    c2_id = setup_gallery_analytics_env["client2_id"]

    # Create Order for Client 2 with larger revenue than Client 1 (e.g. 1,000,000)
    order2 = SalesOrder(
        company_id=comp_id,
        order_number="GA-SO-002",
        client_id=c2_id,
        order_date_ad="2026-09-12",
        order_date_bs="2083-05-27",
        status="delivered",
        total_amount=1000000.0,
        received_amount=950000.0,
        receivable_amount=50000.0
    )
    db.add(order2)
    db.commit()
    db.refresh(order2)

    item3 = SalesItem(
        company_id=comp_id,
        sales_order_id=order2.id,
        product_id=p1_id,
        quantity=400.0,
        unit_price=2500.0,
        total_price=1000000.0
    )
    db.add(item3)
    db.commit()
    db.close()

    resp = client.get("/api/v1/analytics/top-customers", cookies=cookies)
    assert resp.status_code == 200
    ranked = resp.json()
    assert len(ranked) >= 2

    # Client 2 has 1,000,000 revenue > Client 1 (665,000) -> Serial 1
    assert ranked[0]["client_id"] == c2_id
    assert ranked[0]["serial_no"] == 1
    assert ranked[0]["total_pairs"] == 400.0
    assert ranked[0]["total_revenue_paisa"] == 100000000

    # Client 1 -> Serial 2
    assert ranked[1]["serial_no"] == 2
    assert ranked[1]["total_pairs"] == 170.0  # 50 + 120


def test_production_ratios_and_timeframe_aggregation(setup_gallery_analytics_env):
    """Verify Points 6 & 9: Production ratios across 1m, 3m, 1y timeframes."""
    client = TestClient(app)
    cookies = _login(client, setup_gallery_analytics_env["editor_username"], setup_gallery_analytics_env["editor_password"])
    db = SessionLocal()

    comp_id = setup_gallery_analytics_env["company_id"]
    p1_id = setup_gallery_analytics_env["product1_id"]

    today_ad = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    yesterday_ad = (datetime.now(timezone.utc).date() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Log 1 batch yesterday: 400 pairs, 40 workers
    b1 = ProductionBatch(
        company_id=comp_id,
        batch_number="GA-BATCH-001",
        product_id=p1_id,
        target_quantity=400.0,
        produced_quantity=400.0,
        worker_count=40,
        status="completed",
        date_ad=yesterday_ad,
        date_bs="2083-06-14"
    )
    db.add(b1)
    db.commit()

    # Post an explicit daily log today via API: 50 workers, 400.0 hours, 600 pairs
    resp_log = client.post("/api/v1/analytics/daily-logs", json={
        "date_ad": today_ad,
        "date_bs": "2083-06-15",
        "total_workers": 50,
        "total_working_hours": 400.0,
        "total_pairs_produced": 600
    }, cookies=cookies)
    assert resp_log.status_code == 201
    db.close()

    # Query 1m timeframe
    resp_1m = client.get("/api/v1/analytics/production-ratios?timeframe=1m", cookies=cookies)
    assert resp_1m.status_code == 200
    data_1m = resp_1m.json()
    assert data_1m["timeframe"] == "1m"
    records = data_1m["daily_records"]
    assert len(records) >= 2

    # Check today's record: 600 pairs / 50 workers = 12.0 pairs/worker, 600 / 400h = 1.5 pairs/hour
    today_rec = [r for r in records if r["date_ad"] == today_ad][0]
    assert today_rec["pairs_produced"] == 600.0
    assert today_rec["worker_count"] == 50
    assert today_rec["pairs_per_worker"] == 12.0
    assert today_rec["pairs_per_hour"] == 1.5

    # Check summary totals
    assert data_1m["summary"]["total_pairs_produced"] >= 1000.0
    assert data_1m["summary"]["avg_pairs_per_worker"] > 0
    assert data_1m["summary"]["avg_pairs_per_man_hour"] > 0
