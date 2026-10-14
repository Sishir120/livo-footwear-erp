import io
import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import engine, SessionLocal
from app.models import Company, User, Worker, WorkerAdvance, WorkerMonthlyRecord
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_phase_4b_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db = SessionLocal()

    # 1. Company 1
    comp1 = db.query(Company).filter(Company.code == "HR4B_CO1").first()
    if not comp1:
        comp1 = Company(name="Phase 4B Main Factory", code="HR4B_CO1")
        db.add(comp1)
        db.commit()
        db.refresh(comp1)

    # 2. Company 2 (for cross-tenant validation)
    comp2 = db.query(Company).filter(Company.code == "HR4B_CO2").first()
    if not comp2:
        comp2 = Company(name="Phase 4B Other Factory", code="HR4B_CO2")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # 3. Users in Company 1
    admin1 = db.query(User).filter(User.username == "hr4b_admin1").first()
    if not admin1:
        admin1 = User(
            company_id=comp1.id,
            name="HR Super Admin",
            username="hr4b_admin1",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin1)

    editor1 = db.query(User).filter(User.username == "hr4b_editor1").first()
    if not editor1:
        editor1 = User(
            company_id=comp1.id,
            name="HR Supervisor",
            username="hr4b_editor1",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor1)

    viewer1 = db.query(User).filter(User.username == "hr4b_viewer1").first()
    if not viewer1:
        viewer1 = User(
            company_id=comp1.id,
            name="HR Auditor",
            username="hr4b_viewer1",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer1)

    # 4. Admin in Company 2
    admin2 = db.query(User).filter(User.username == "hr4b_admin2").first()
    if not admin2:
        admin2 = User(
            company_id=comp2.id,
            name="Other Admin",
            username="hr4b_admin2",
            password_hash=get_password_hash("Admin2Pass123!"),
            role="admin",
            active=True
        )
        db.add(admin2)

    db.commit()

    # Clean existing workers for these companies
    db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(WorkerAdvance).filter(WorkerAdvance.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.commit()

    db.close()

    return {
        "company1_id": comp1.id,
        "company2_id": comp2.id,
        "admin1": ("hr4b_admin1", "AdminPass123!"),
        "editor1": ("hr4b_editor1", "EditorPass123!"),
        "viewer1": ("hr4b_viewer1", "ViewerPass123!"),
        "admin2": ("hr4b_admin2", "Admin2Pass123!")
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


# ============================================================================
# SUBPHASE 4B.1 TESTS: WORKER IDENTITY, ADDRESSES, PHOTO
# ============================================================================

def test_worker_addresses_create_read_update(setup_phase_4b_env):
    """Test temporary and permanent addresses persist, update, and serialize correctly."""
    client = TestClient(app)
    cookies = _login(client, *setup_phase_4b_env["editor1"])

    # 1. Create worker with addresses
    create_payload = {
        "worker_code": "WKR-ADDR-01",
        "name": "Bikash Tamang",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3200000,
        "phone": "9841000001",
        "temporary_address": "Kathmandu-16, Balaju",
        "permanent_address": "Sindhupalchok, Melamchi-4",
        "is_active": True
    }
    resp = client.post("/api/v1/hr/workers", json=create_payload, cookies=cookies)
    assert resp.status_code == 201
    w = resp.json()
    assert w["worker_code"] == "WKR-ADDR-01"
    assert w["temporary_address"] == "Kathmandu-16, Balaju"
    assert w["permanent_address"] == "Sindhupalchok, Melamchi-4"
    assert w["has_citizenship_doc"] is False
    assert w["citizenship_doc_name"] is None
    worker_id = w["id"]

    # 2. Read worker via list
    resp_list = client.get("/api/v1/hr/workers?search=WKR-ADDR-01", cookies=cookies)
    assert resp_list.status_code == 200
    listed_w = resp_list.json()[0]
    assert listed_w["temporary_address"] == "Kathmandu-16, Balaju"
    assert listed_w["permanent_address"] == "Sindhupalchok, Melamchi-4"

    # 3. Update addresses
    update_payload = {
        "temporary_address": "Lalitpur-3, Pulchowk",
        "permanent_address": "Sindhupalchok, Helambu-1"
    }
    resp_update = client.patch(f"/api/v1/hr/workers/{worker_id}", json=update_payload, cookies=cookies)
    assert resp_update.status_code == 200
    updated_w = resp_update.json()
    assert updated_w["temporary_address"] == "Lalitpur-3, Pulchowk"
    assert updated_w["permanent_address"] == "Sindhupalchok, Helambu-1"


def test_worker_photo_upload_validation_and_streaming(setup_phase_4b_env):
    """Test photo upload validates format, size, magic bytes, and streams with tenant scoping."""
    client = TestClient(app)
    editor_cookies = _login(client, *setup_phase_4b_env["editor1"])
    admin2_cookies = _login(client, *setup_phase_4b_env["admin2"])

    # Create worker
    resp = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-PHOTO-01",
        "name": "Sunil Maharjan",
        "pay_type": "WAGE",
        "basic_rate_paisa": 16000
    }, cookies=editor_cookies)
    assert resp.status_code == 201
    worker_id = resp.json()["id"]

    # 1. Reject invalid MIME type
    text_file = ("test.txt", io.BytesIO(b"Hello world"), "text/plain")
    resp_bad_mime = client.post(
        f"/api/v1/hr/workers/{worker_id}/photo",
        files={"file": text_file},
        cookies=editor_cookies
    )
    assert resp_bad_mime.status_code == 400
    assert "Unsupported image format" in resp_bad_mime.json()["detail"]

    # 2. Reject disguised file (invalid magic bytes)
    fake_jpeg = ("fake.jpg", io.BytesIO(b"Not a real jpeg file"), "image/jpeg")
    resp_fake = client.post(
        f"/api/v1/hr/workers/{worker_id}/photo",
        files={"file": fake_jpeg},
        cookies=editor_cookies
    )
    assert resp_fake.status_code == 400
    assert "image header signatures" in resp_fake.json()["detail"]

    # 3. Reject oversized photo (> 2MB)
    huge_data = b"\xff\xd8\xff\xe0" + b"\x00" * (2 * 1024 * 1024 + 100)
    huge_jpeg = ("huge.jpg", io.BytesIO(huge_data), "image/jpeg")
    resp_huge = client.post(
        f"/api/v1/hr/workers/{worker_id}/photo",
        files={"file": huge_jpeg},
        cookies=editor_cookies
    )
    assert resp_huge.status_code == 400
    assert "exceeds maximum size" in resp_huge.json()["detail"]

    # 4. Successful upload of valid JPEG (magic bytes \xff\xd8\xff)
    valid_jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 200
    valid_file = ("profile.jpg", io.BytesIO(valid_jpeg_bytes), "image/jpeg")
    resp_ok = client.post(
        f"/api/v1/hr/workers/{worker_id}/photo",
        files={"file": valid_file},
        cookies=editor_cookies
    )
    assert resp_ok.status_code == 200
    w_updated = resp_ok.json()
    assert w_updated["photo_url"] == f"/api/v1/hr/workers/{worker_id}/photo"

    # 5. Stream photo
    resp_stream = client.get(f"/api/v1/hr/workers/{worker_id}/photo", cookies=editor_cookies)
    assert resp_stream.status_code == 200
    assert resp_stream.headers["content-type"] == "image/jpeg"

    # 6. Cross-tenant stream attempt: company 2 user cannot access company 1 worker photo
    resp_cross = client.get(f"/api/v1/hr/workers/{worker_id}/photo", cookies=admin2_cookies)
    assert resp_cross.status_code == 404

    # 7. Delete photo
    resp_del = client.delete(f"/api/v1/hr/workers/{worker_id}/photo", cookies=editor_cookies)
    assert resp_del.status_code == 200
    assert resp_del.json()["photo_url"] is None

    # Stream after deletion should return 404
    resp_stream_after = client.get(f"/api/v1/hr/workers/{worker_id}/photo", cookies=editor_cookies)
    assert resp_stream_after.status_code == 404


# ============================================================================
# SUBPHASE 4B.2 TESTS: SECURE CITIZENSHIP DOCUMENT MANAGEMENT
# ============================================================================

def test_citizenship_document_admin_only_and_rbac(setup_phase_4b_env):
    """Test citizenship upload, download, and deletion strictly require Role.ADMIN."""
    client = TestClient(app)
    admin_cookies = _login(client, *setup_phase_4b_env["admin1"])
    editor_cookies = _login(client, *setup_phase_4b_env["editor1"])
    viewer_cookies = _login(client, *setup_phase_4b_env["viewer1"])
    admin2_cookies = _login(client, *setup_phase_4b_env["admin2"])

    # Create worker
    resp = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-CIT-01",
        "name": "Manish Shrestha",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3800000
    }, cookies=admin_cookies)
    assert resp.status_code == 201
    worker_id = resp.json()["id"]

    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    pdf_file = ("citizenship_front.pdf", io.BytesIO(valid_pdf_content), "application/pdf")

    # 1. Non-admin (Editor) cannot upload (403 Forbidden)
    resp_ed_up = client.post(
        f"/api/v1/hr/workers/{worker_id}/citizenship",
        files={"file": ("citizenship.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
        cookies=editor_cookies
    )
    assert resp_ed_up.status_code == 403
    assert "admin" in resp_ed_up.json()["detail"].lower()

    # 2. Non-admin (Viewer) cannot upload (403 Forbidden)
    resp_vi_up = client.post(
        f"/api/v1/hr/workers/{worker_id}/citizenship",
        files={"file": ("citizenship.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
        cookies=viewer_cookies
    )
    assert resp_vi_up.status_code == 403

    # 3. Admin successfully uploads
    resp_adm_up = client.post(
        f"/api/v1/hr/workers/{worker_id}/citizenship",
        files={"file": ("citizenship_front.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
        cookies=admin_cookies
    )
    assert resp_adm_up.status_code == 200
    cit_meta = resp_adm_up.json()
    assert cit_meta["has_citizenship_doc"] is True
    assert cit_meta["citizenship_doc_name"] == "citizenship_front.pdf"

    # Worker response must show has_citizenship_doc=True but NEVER leak raw storage path
    resp_w = client.get(f"/api/v1/hr/workers?search=WKR-CIT-01", cookies=admin_cookies)
    assert resp_w.status_code == 200
    w_data = resp_w.json()[0]
    assert w_data["has_citizenship_doc"] is True
    assert w_data["citizenship_doc_name"] == "citizenship_front.pdf"
    assert "storage/secure_hr" not in str(w_data)

    # 4. Non-admin cannot download (403)
    resp_ed_dl = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=editor_cookies)
    assert resp_ed_dl.status_code == 403

    resp_vi_dl = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=viewer_cookies)
    assert resp_vi_dl.status_code == 403

    # 5. Cross-tenant admin cannot download or upload (404 Not Found)
    resp_cross_dl = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=admin2_cookies)
    assert resp_cross_dl.status_code == 404

    # 6. Admin downloads successfully with private cache headers
    resp_adm_dl = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=admin_cookies)
    assert resp_adm_dl.status_code == 200
    assert resp_adm_dl.content == valid_pdf_content
    assert "no-store" in resp_adm_dl.headers["cache-control"]
    assert resp_adm_dl.headers.get("x-content-type-options") == "nosniff"

    # 7. Non-admin cannot delete (403)
    resp_ed_del = client.delete(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=editor_cookies)
    assert resp_ed_del.status_code == 403

    # 8. Admin deletes document (204)
    resp_adm_del = client.delete(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=admin_cookies)
    assert resp_adm_del.status_code == 204

    # Subsequent download yields 404
    resp_adm_dl2 = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=admin_cookies)
    assert resp_adm_dl2.status_code == 404


def test_citizenship_document_magic_byte_validation(setup_phase_4b_env):
    """Test fake document extension with invalid header signature is rejected."""
    client = TestClient(app)
    admin_cookies = _login(client, *setup_phase_4b_env["admin1"])

    resp = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-CIT-SEC",
        "name": "Security Test Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=admin_cookies)
    assert resp.status_code == 201
    worker_id = resp.json()["id"]

    # Spoofed PDF file
    spoofed_file = ("script.pdf", io.BytesIO(b"<?php phpinfo(); ?>"), "application/pdf")
    resp_spoof = client.post(
        f"/api/v1/hr/workers/{worker_id}/citizenship",
        files={"file": spoofed_file},
        cookies=admin_cookies
    )
    assert resp_spoof.status_code == 400
    assert "header" in resp_spoof.json()["detail"].lower()


# ============================================================================
# SUBPHASE 4B.3 TESTS: WORKER ACTIVATION / DEACTIVATION & GUARDRAILS
# ============================================================================

def test_worker_deactivation_lifecycle_and_transaction_guardrails(setup_phase_4b_env):
    """
    Test deactivation sets inactive_date, blocks new advances and payroll,
    while preserving historical records and balances. Reactivation restores eligibility.
    """
    client = TestClient(app)
    editor_cookies = _login(client, *setup_phase_4b_env["editor1"])

    # 1. Create worker
    resp_w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-LIFECYCLE-01",
        "name": "Pooja Gurung",
        "pay_type": "SALARY",
        "basic_rate_paisa": 4500000,
        "is_active": True
    }, cookies=editor_cookies)
    assert resp_w.status_code == 201
    worker_id = resp_w.json()["id"]

    # 2. Issue an initial advance while active
    resp_adv = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 600000,
        "entry_type": "ISSUED",
        "notes": "Festival advance"
    }, cookies=editor_cookies)
    assert resp_adv.status_code == 201

    # 3. Deactivate worker via status endpoint
    deact_payload = {
        "is_active": False,
        "inactive_reason": "Resigned to pursue higher education",
        "inactive_date": "2026-10-15"
    }
    resp_deact = client.patch(f"/api/v1/hr/workers/{worker_id}/status", json=deact_payload, cookies=editor_cookies)
    assert resp_deact.status_code == 200
    deact_data = resp_deact.json()
    assert deact_data["is_active"] is False
    assert deact_data["inactive_date"] == "2026-10-15"
    assert deact_data["inactive_reason"] == "Resigned to pursue higher education"
    # Outstanding advance balance remains fully intact (600,000 paisa)
    assert deact_data["outstanding_advance_paisa"] == 600000

    # 4. Inactive worker transaction guardrail: Advance issuance MUST BE REJECTED
    resp_block_adv = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 100000,
        "entry_type": "ISSUED",
        "notes": "Attempt on inactive worker"
    }, cookies=editor_cookies)
    assert resp_block_adv.status_code == 400
    assert "inactive" in resp_block_adv.json()["detail"].lower()

    # 5. Inactive worker transaction guardrail: Payroll processing MUST BE REJECTED
    resp_block_pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": worker_id,
        "month_year": "2026-10",
        "total_working_hours": 160.0
    }, cookies=editor_cookies)
    assert resp_block_pay.status_code == 400
    assert "inactive" in resp_block_pay.json()["detail"].lower()

    # 6. Historical records remain fully readable and intact
    resp_hist = client.get(f"/api/v1/hr/workers/{worker_id}/history", cookies=editor_cookies)
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert hist["worker"]["is_active"] is False
    assert hist["worker"]["outstanding_advance_paisa"] == 600000
    assert len(hist["advances"]) == 1

    # 7. Reactivate worker
    react_payload = {
        "is_active": True
    }
    resp_react = client.patch(f"/api/v1/hr/workers/{worker_id}/status", json=react_payload, cookies=editor_cookies)
    assert resp_react.status_code == 200
    react_data = resp_react.json()
    assert react_data["is_active"] is True
    assert react_data["inactive_date"] is None
    assert react_data["outstanding_advance_paisa"] == 600000  # Balance still preserved

    # 8. Now advances and payroll work again
    resp_adv_ok = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 100000,
        "entry_type": "ISSUED",
        "notes": "Post-reactivation advance"
    }, cookies=editor_cookies)
    assert resp_adv_ok.status_code == 201
