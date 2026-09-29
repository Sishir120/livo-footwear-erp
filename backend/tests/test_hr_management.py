import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Worker, WorkerAdvance, WorkerMonthlyRecord
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_hr_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create Primary Company
    comp = db.query(Company).filter(Company.code == "HR_TEST_CO").first()
    if not comp:
        comp = Company(name="HR Test Footwear Industries Ltd", code="HR_TEST_CO")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    # Second Company for tenant isolation verification
    comp2 = db.query(Company).filter(Company.code == "HR_OTHER_CO").first()
    if not comp2:
        comp2 = Company(name="Other Footwear Factory", code="HR_OTHER_CO")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # Editor user (in Primary Company)
    editor = db.query(User).filter(User.username == "hr_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="HR Manager",
            username="hr_editor",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor)

    # Viewer user (in Primary Company)
    viewer = db.query(User).filter(User.username == "hr_viewer").first()
    if not viewer:
        viewer = User(
            company_id=comp.id,
            name="HR Auditor",
            username="hr_viewer",
            password_hash=get_password_hash("ViewerPass123!"),
            role="viewer",
            active=True
        )
        db.add(viewer)

    # Clean up any leftover test data from previous runs
    db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(WorkerAdvance).filter(WorkerAdvance.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp.id, comp2.id])).delete(synchronize_session=False)
    db.commit()

    db.refresh(comp)
    db.refresh(comp2)
    db.refresh(editor)
    db.refresh(viewer)
    db.close()

    return {
        "company_id": comp.id,
        "company2_id": comp2.id,
        "editor_username": "hr_editor",
        "editor_password": "EditorPass123!",
        "viewer_username": "hr_viewer",
        "viewer_password": "ViewerPass123!"
    }


def _login_and_get_cookie(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


def test_worker_creation_salary_and_wage(setup_hr_env):
    """Verify creating salaried staff and wage workers with correct pay types."""
    client = TestClient(app)
    cookies = _login_and_get_cookie(client, setup_hr_env["editor_username"], setup_hr_env["editor_password"])

    # 1. Create Salaried Worker
    resp1 = client.post("/api/v1/hr/workers", json={
        "worker_code": "EMP-001",
        "name": "Ram Bahadur Shrestha",
        "join_date": "2026-01-15",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3500000,  # NPR 35,000.00
        "phone": "9841234567",
        "is_active": True
    }, cookies=cookies)
    assert resp1.status_code == 201
    w1 = resp1.json()
    assert w1["worker_code"] == "EMP-001"
    assert w1["pay_type"] == "SALARY"
    assert w1["basic_rate_paisa"] == 3500000
    assert w1["is_active"] is True

    # 2. Create Wage Worker
    resp2 = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-002",
        "name": "Gita Thapa",
        "join_date": "2026-03-01",
        "pay_type": "WAGE",
        "basic_rate_paisa": 15000,  # NPR 150.00 / hour
        "phone": "9851098765",
        "is_active": True
    }, cookies=cookies)
    assert resp2.status_code == 201
    w2 = resp2.json()
    assert w2["worker_code"] == "WKR-002"
    assert w2["pay_type"] == "WAGE"
    assert w2["basic_rate_paisa"] == 15000


def test_worker_code_uniqueness_within_company(setup_hr_env):
    """Verify duplicate worker_code within the same tenant company is rejected with 400 Bad Request."""
    client = TestClient(app)
    cookies = _login_and_get_cookie(client, setup_hr_env["editor_username"], setup_hr_env["editor_password"])

    resp = client.post("/api/v1/hr/workers", json={
        "worker_code": "EMP-001",  # Already created
        "name": "Duplicate Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=cookies)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_advance_calculation_issued_and_recovered(setup_hr_env):
    """Verify advance ledger arithmetic: Outstanding = sum(ISSUED) - sum(RECOVERED)."""
    client = TestClient(app)
    cookies = _login_and_get_cookie(client, setup_hr_env["editor_username"], setup_hr_env["editor_password"])

    # Create worker
    resp_w = client.post("/api/v1/hr/workers", json={
        "worker_code": "EMP-ADV-01",
        "name": "Hari Maya Rai",
        "pay_type": "SALARY",
        "basic_rate_paisa": 4000000
    }, cookies=cookies)
    assert resp_w.status_code == 201
    worker_id = resp_w.json()["id"]

    # 1. Issue first advance of NPR 5,000.00 (500,000 paisa)
    resp_adv1 = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 500000,
        "entry_type": "ISSUED",
        "notes": "Festival advance Dashain"
    }, cookies=cookies)
    assert resp_adv1.status_code == 201

    # 2. Issue second advance of NPR 2,000.00 (200,000 paisa)
    resp_adv2 = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 200000,
        "entry_type": "ISSUED",
        "notes": "Emergency medical"
    }, cookies=cookies)
    assert resp_adv2.status_code == 201

    # Check outstanding via list workers: should be 700,000 paisa (NPR 7,000)
    resp_list1 = client.get(f"/api/v1/hr/workers?search=EMP-ADV-01", cookies=cookies)
    assert resp_list1.status_code == 200
    assert resp_list1.json()[0]["outstanding_advance_paisa"] == 700000

    # 3. Record partial repayment of NPR 3,000.00 (300,000 paisa)
    resp_rec = client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 300000,
        "entry_type": "RECOVERED",
        "notes": "Cash partial repayment"
    }, cookies=cookies)
    assert resp_rec.status_code == 201

    # Check outstanding: 700,000 - 300,000 = 400,000 paisa (NPR 4,000)
    resp_list2 = client.get(f"/api/v1/hr/workers?search=EMP-ADV-01", cookies=cookies)
    assert resp_list2.status_code == 200
    assert resp_list2.json()[0]["outstanding_advance_paisa"] == 400000


def test_active_inactive_filtering_and_status_toggle(setup_hr_env):
    """Verify active/inactive status toggle and query filters."""
    client = TestClient(app)
    cookies = _login_and_get_cookie(client, setup_hr_env["editor_username"], setup_hr_env["editor_password"])

    # Create worker
    resp_w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-TOGGLE-01",
        "name": "Kiran Tamang",
        "pay_type": "WAGE",
        "basic_rate_paisa": 16000,
        "is_active": True
    }, cookies=cookies)
    assert resp_w.status_code == 201
    worker_id = resp_w.json()["id"]

    # Toggle to Inactive
    resp_patch = client.patch(f"/api/v1/hr/workers/{worker_id}", json={
        "is_active": False
    }, cookies=cookies)
    assert resp_patch.status_code == 200
    assert resp_patch.json()["is_active"] is False

    # Filter active only -> WKR-TOGGLE-01 should NOT be returned
    resp_act = client.get("/api/v1/hr/workers?status=active&search=WKR-TOGGLE-01", cookies=cookies)
    assert len(resp_act.json()) == 0

    # Filter inactive only -> WKR-TOGGLE-01 should be returned
    resp_inact = client.get("/api/v1/hr/workers?status=inactive&search=WKR-TOGGLE-01", cookies=cookies)
    assert len(resp_inact.json()) == 1
    assert resp_inact.json()[0]["worker_code"] == "WKR-TOGGLE-01"

    # Toggle back to Active
    resp_patch2 = client.patch(f"/api/v1/hr/workers/{worker_id}", json={
        "is_active": True
    }, cookies=cookies)
    assert resp_patch2.status_code == 200
    assert resp_patch2.json()["is_active"] is True


def test_monthly_payroll_calculation_and_advance_deduction(setup_hr_env):
    """
    Verify monthly payroll:
    - Salaried worker: basic rate + overtime
    - Automatic deduction of outstanding advance
    - When mark_as_paid=True, creates RECOVERED entry and reduces advance
    """
    client = TestClient(app)
    cookies = _login_and_get_cookie(client, setup_hr_env["editor_username"], setup_hr_env["editor_password"])

    # Create Salaried worker with basic salary NPR 30,000 (3,000,000 paisa)
    resp_w = client.post("/api/v1/hr/workers", json={
        "worker_code": "EMP-PAYROLL-01",
        "name": "Deepak Gurung",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=cookies)
    assert resp_w.status_code == 201
    worker_id = resp_w.json()["id"]

    # Issue advance of NPR 5,000 (500,000 paisa)
    client.post("/api/v1/hr/advances", json={
        "worker_id": worker_id,
        "amount_paisa": 500000,
        "entry_type": "ISSUED",
        "notes": "Advance for rent"
    }, cookies=cookies)

    # Process payroll for 2026-09 with 10 hours overtime
    # Hourly rate = 3000000 / 208 = 14423.07 paisa; 10h * 14423.07 * 1.5 = 216346 paisa
    resp_pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": worker_id,
        "month_year": "2026-09",
        "total_working_hours": 192.0,
        "overtime_hours": 10.0,
        "mark_as_paid": True,
        "payment_method": "BANK"
    }, cookies=cookies)
    assert resp_pay.status_code == 200
    pay_data = resp_pay.json()

    assert pay_data["status"] == "PAID"
    # Gross pay should be basic (3,000,000) + overtime (~216,346)
    assert pay_data["gross_pay_paisa"] >= 3000000
    # Advance deduction should have auto-deducted the full 500,000 paisa
    assert pay_data["advance_deduction_paisa"] == 500000
    # Net paid = gross - 500,000
    assert pay_data["net_paid_paisa"] == pay_data["gross_pay_paisa"] - 500000

    # Verify advance balance is now 0 (recovered)
    history_resp = client.get(f"/api/v1/hr/workers/{worker_id}/history", cookies=cookies)
    assert history_resp.status_code == 200
    h_data = history_resp.json()
    assert h_data["worker"]["outstanding_advance_paisa"] == 0
    assert len(h_data["advances"]) == 2  # 1 ISSUED + 1 auto-created RECOVERED


def test_viewer_role_rejected_from_hr_mutations(setup_hr_env):
    """Verify viewer accounts receive 403 Forbidden on worker creation, advance posting, and payroll."""
    client = TestClient(app)
    viewer_cookies = _login_and_get_cookie(client, setup_hr_env["viewer_username"], setup_hr_env["viewer_password"])

    # 1. Viewer cannot create worker (403)
    resp1 = client.post("/api/v1/hr/workers", json={
        "worker_code": "EMP-HACK-01",
        "name": "Unauthorized Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2000000
    }, cookies=viewer_cookies)
    assert resp1.status_code == 403

    # 2. Viewer cannot record advance (403)
    resp2 = client.post("/api/v1/hr/advances", json={
        "worker_id": 1,
        "amount_paisa": 100000,
        "entry_type": "ISSUED"
    }, cookies=viewer_cookies)
    assert resp2.status_code == 403

    # 3. Viewer cannot process payroll (403)
    resp3 = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": 1,
        "month_year": "2026-09"
    }, cookies=viewer_cookies)
    assert resp3.status_code == 403

    # 4. But viewer CAN read workers list (200 OK)
    resp4 = client.get("/api/v1/hr/workers", cookies=viewer_cookies)
    assert resp4.status_code == 200
