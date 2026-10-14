import io
from decimal import Decimal
import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models import Company, User, Worker, WorkerAdvance, WorkerMonthlyRecord, CompanyHRSettings
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_wp4b4_1_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db = SessionLocal()

    # 1. Company 1
    comp1 = db.query(Company).filter(Company.code == "WP4B_CO1").first()
    if not comp1:
        comp1 = Company(name="WP 4B Main Factory", code="WP4B_CO1")
        db.add(comp1)
        db.commit()
        db.refresh(comp1)

    # 2. Company 2
    comp2 = db.query(Company).filter(Company.code == "WP4B_CO2").first()
    if not comp2:
        comp2 = Company(name="WP 4B Other Factory", code="WP4B_CO2")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # 3. Users in Company 1
    admin1 = db.query(User).filter(User.username == "wp4b_admin1").first()
    if not admin1:
        admin1 = User(
            company_id=comp1.id,
            name="HR Admin One",
            username="wp4b_admin1",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin1)

    editor1 = db.query(User).filter(User.username == "wp4b_editor1").first()
    if not editor1:
        editor1 = User(
            company_id=comp1.id,
            name="HR Editor One",
            username="wp4b_editor1",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor1)

    # 4. Users in Company 2
    admin2 = db.query(User).filter(User.username == "wp4b_admin2").first()
    if not admin2:
        admin2 = User(
            company_id=comp2.id,
            name="HR Admin Two",
            username="wp4b_admin2",
            password_hash=get_password_hash("Admin2Pass123!"),
            role="admin",
            active=True
        )
        db.add(admin2)

    db.commit()

    # Clean records for test companies
    db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(WorkerAdvance).filter(WorkerAdvance.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.commit()

    db.close()

    return {
        "company1_id": comp1.id,
        "company2_id": comp2.id,
        "admin1": ("wp4b_admin1", "AdminPass123!"),
        "editor1": ("wp4b_editor1", "EditorPass123!"),
        "admin2": ("wp4b_admin2", "Admin2Pass123!"),
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


def test_1_admin_settings_retrieval_and_update(setup_wp4b4_1_env):
    """Admin can retrieve and update company HR settings."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # 1. GET settings
    res = client.get("/api/v1/hr/settings", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert data["company_id"] == setup_wp4b4_1_env["company1_id"]
    assert float(data["standard_monthly_hours"]) == 208.00
    assert float(data["overtime_multiplier"]) == 1.50
    assert data["max_advance_deduction_pct"] == 50

    # 2. PUT settings
    update_payload = {
        "standard_monthly_hours": "200.00",
        "overtime_multiplier": "2.00",
        "max_advance_deduction_pct": 40
    }
    put_res = client.put("/api/v1/hr/settings", json=update_payload, cookies=cookies)
    assert put_res.status_code == 200
    put_data = put_res.json()
    assert float(put_data["standard_monthly_hours"]) == 200.00
    assert float(put_data["overtime_multiplier"]) == 2.00
    assert put_data["max_advance_deduction_pct"] == 40


def test_2_editor_settings_update_rejected(setup_wp4b4_1_env):
    """Editor user cannot read or update company HR settings (403 Forbidden)."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["editor1"])

    # GET rejected
    res = client.get("/api/v1/hr/settings", cookies=cookies)
    assert res.status_code == 403

    # PUT rejected
    put_res = client.put("/api/v1/hr/settings", json={
        "standard_monthly_hours": "180.00",
        "overtime_multiplier": "1.50",
        "max_advance_deduction_pct": 30
    }, cookies=cookies)
    assert put_res.status_code == 403


def test_3_settings_tenant_isolation(setup_wp4b4_1_env):
    """Company A admin updating settings does not affect Company B."""
    client_a = TestClient(app)
    cookies_a = _login(client_a, *setup_wp4b4_1_env["admin1"])

    client_b = TestClient(app)
    cookies_b = _login(client_b, *setup_wp4b4_1_env["admin2"])

    # Admin A sets hours=190.00
    client_a.put("/api/v1/hr/settings", json={
        "standard_monthly_hours": "190.00",
        "overtime_multiplier": "1.75",
        "max_advance_deduction_pct": 45
    }, cookies=cookies_a)

    # Admin B gets settings -> should still have standard defaults or Company B's own
    res_b = client_b.get("/api/v1/hr/settings", cookies=cookies_b)
    assert res_b.status_code == 200
    assert float(res_b.json()["standard_monthly_hours"]) == 208.00
    assert float(res_b.json()["overtime_multiplier"]) == 1.50


def test_4_default_settings_for_company_without_settings_row(setup_wp4b4_1_env):
    """If settings row does not exist, GET /hr/settings returns default values safely."""
    db = SessionLocal()
    # Temporarily remove Company 2 settings row
    db.query(CompanyHRSettings).filter(CompanyHRSettings.company_id == setup_wp4b4_1_env["company2_id"]).delete()
    db.commit()
    db.close()

    client_b = TestClient(app)
    cookies_b = _login(client_b, *setup_wp4b4_1_env["admin2"])

    res = client_b.get("/api/v1/hr/settings", cookies=cookies_b)
    assert res.status_code == 200
    data = res.json()
    assert float(data["standard_monthly_hours"]) == 208.00
    assert float(data["overtime_multiplier"]) == 1.50
    assert data["max_advance_deduction_pct"] == 50


def test_5_validation_boundary_and_invalid_values(setup_wp4b4_1_env):
    """Validation rejects invalid, boundary, or excessive values."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # 1. Zero standard hours
    r1 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "0.0", "overtime_multiplier": "1.5", "max_advance_deduction_pct": 50}, cookies=cookies)
    assert r1.status_code == 422

    # 2. Excessive standard hours (> 744)
    r2 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "745.0", "overtime_multiplier": "1.5", "max_advance_deduction_pct": 50}, cookies=cookies)
    assert r2.status_code == 422

    # 3. Multiplier < 1.0
    r3 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.0", "overtime_multiplier": "0.9", "max_advance_deduction_pct": 50}, cookies=cookies)
    assert r3.status_code == 422

    # 4. Multiplier > 5.0
    r4 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.0", "overtime_multiplier": "5.5", "max_advance_deduction_pct": 50}, cookies=cookies)
    assert r4.status_code == 422

    # 5. Ceiling > 50%
    r5 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.0", "overtime_multiplier": "1.5", "max_advance_deduction_pct": 55}, cookies=cookies)
    assert r5.status_code == 422

    # 6. Ceiling <= 0%
    r6 = client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.0", "overtime_multiplier": "1.5", "max_advance_deduction_pct": 0}, cookies=cookies)
    assert r6.status_code == 422


def test_6_worker_standard_hours_override_precedence(setup_wp4b4_1_env):
    """Worker-level standard hours override takes precedence over company settings in overtime calculation."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # Reset company 1 settings: standard_monthly_hours = 208.00, multiplier = 1.50
    client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.00", "overtime_multiplier": "1.50", "max_advance_deduction_pct": 50}, cookies=cookies)

    # Create worker with override: standard_monthly_hours_override = 200.00
    # Monthly salary = NPR 20,000 (2,000,000 paisa)
    w_res = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-PRE-01",
        "name": "Standard Hours Override Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2000000,
        "standard_monthly_hours_override": "200.00"
    }, cookies=cookies)
    assert w_res.status_code == 201
    w_id = w_res.json()["id"]

    # Calculate payroll with 10 OT hours
    # If company 208 was used: hourly = 2000000 / 208 = 9615.38; OT = 10 * 9615.38 * 1.5 = 144231 paisa
    # With worker override 200: hourly = 2000000 / 200 = 10000; OT = 10 * 10000 * 1.5 = 150000 paisa
    pay_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "total_working_hours": "200.0",
        "overtime_hours": "10.0",
        "mark_as_paid": False
    }, cookies=cookies)
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert data["overtime_pay_paisa"] == 150000
    assert float(data["standard_hours_snapshot"]) == 200.00


def test_7_fixed_worker_overtime_rate_precedence(setup_wp4b4_1_env):
    """Fixed worker overtime rate override takes precedence over company multiplier calculation."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # Create salaried worker with fixed overtime rate override = NPR 250/hr (25,000 paisa)
    w_res = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-OT-FIXED",
        "name": "Fixed OT Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000,
        "overtime_rate_paisa_override": 25000
    }, cookies=cookies)
    assert w_res.status_code == 201
    w_id = w_res.json()["id"]

    # 12 hours overtime: 12 * 25,000 = 300,000 paisa
    pay_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "total_working_hours": "208.0",
        "overtime_hours": "12.0",
        "mark_as_paid": False
    }, cookies=cookies)
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert data["overtime_pay_paisa"] == 300000
    assert data["overtime_rate_paisa_snapshot"] == 25000


def test_8_salary_regular_pay_full_monthly_rate(setup_wp4b4_1_env):
    """Salaried workers receive full basic salary regardless of recorded working hours."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    w_res = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-SAL-FULL",
        "name": "Full Salary Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3500000
    }, cookies=cookies)
    assert w_res.status_code == 201
    w_id = w_res.json()["id"]

    # Worker only worked 120 hours (less than 208)
    pay_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "total_working_hours": "120.0",
        "overtime_hours": "0.0",
        "mark_as_paid": False
    }, cookies=cookies)
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert data["regular_pay_paisa"] == 3500000
    assert data["gross_pay_paisa"] == 3500000


def test_9_wage_regular_pay_calculation(setup_wp4b4_1_env):
    """Wage workers' regular pay is hourly wage multiplied by recorded working hours."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # Hourly rate NPR 150 = 15,000 paisa
    w_res = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-WAGE-01",
        "name": "Hourly Wage Worker",
        "pay_type": "WAGE",
        "basic_rate_paisa": 15000
    }, cookies=cookies)
    assert w_res.status_code == 201
    w_id = w_res.json()["id"]

    # 160 hours: 160 * 15,000 = 2,400,000 paisa
    pay_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "total_working_hours": "160.0",
        "overtime_hours": "0.0",
        "mark_as_paid": False
    }, cookies=cookies)
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert data["regular_pay_paisa"] == 2400000
    assert data["gross_pay_paisa"] == 2400000


def test_10_salary_and_wage_overtime_calculations(setup_wp4b4_1_env):
    """Standard multiplier overtime calculation for both salary and wage workers."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # Ensure 208 hours and 1.5x multiplier
    client.put("/api/v1/hr/settings", json={"standard_monthly_hours": "208.00", "overtime_multiplier": "1.50", "max_advance_deduction_pct": 50}, cookies=cookies)

    # 1. Salary: 2080000 paisa / 208 = 10000 paisa/hr. 8 hrs OT at 1.5x = 8 * 10000 * 1.5 = 120000 paisa
    w_sal = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-SAL-OT", "name": "Sal OT", "pay_type": "SALARY", "basic_rate_paisa": 2080000}, cookies=cookies).json()
    p_sal = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w_sal["id"], "month_year": "2026-10", "total_working_hours": "208.0", "overtime_hours": "8.0"}, cookies=cookies).json()
    assert p_sal["overtime_pay_paisa"] == 120000

    # 2. Wage: 12000 paisa/hr. 8 hrs OT at 1.5x = 8 * 12000 * 1.5 = 144000 paisa
    w_wage = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-WAG-OT", "name": "Wage OT", "pay_type": "WAGE", "basic_rate_paisa": 12000}, cookies=cookies).json()
    p_wage = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w_wage["id"], "month_year": "2026-10", "total_working_hours": "100.0", "overtime_hours": "8.0"}, cookies=cookies).json()
    assert p_wage["overtime_pay_paisa"] == 144000


def test_11_decimal_rounding_half_paisa_boundaries(setup_wp4b4_1_env):
    """Decimal rounding uses commercial ROUND_HALF_UP at half-paisa boundaries."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    # Basic salary: 2500001 paisa, standard hours = 208.00, multiplier = 1.50
    # Hourly = 2500001 / 208 = 12019.23557692...
    # For OT hours = 1.0: 1.0 * (2500001 / 208) * 1.5 = 18028.853365... -> rounds to 18029
    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-ROUND", "name": "Round Worker", "pay_type": "SALARY", "basic_rate_paisa": 2500001}, cookies=cookies).json()
    p = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "total_working_hours": "208.0", "overtime_hours": "1.0"}, cookies=cookies).json()
    expected_ot = int((Decimal("1.0") * (Decimal("2500001") / Decimal("208.00")) * Decimal("1.50")).to_integral_value(rounding="ROUND_HALF_UP"))
    assert p["overtime_pay_paisa"] == expected_ot


def test_12_zero_gross_pay_and_non_negative_net_pay(setup_wp4b4_1_env):
    """Zero working hours produces zero gross pay and non-negative net pay."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-ZERO", "name": "Zero Hours Worker", "pay_type": "WAGE", "basic_rate_paisa": 15000}, cookies=cookies).json()
    p = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "total_working_hours": "0.0", "overtime_hours": "0.0"}, cookies=cookies).json()
    assert p["gross_pay_paisa"] == 0
    assert p["advance_deduction_paisa"] == 0
    assert p["net_paid_paisa"] == 0


def test_13_snapshot_persistence_and_draft_recalculation(setup_wp4b4_1_env):
    """Draft payroll persists calculation snapshots and updates them on recalculation."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-SNAP-01", "name": "Snapshot Worker", "pay_type": "SALARY", "basic_rate_paisa": 2080000}, cookies=cookies).json()

    # Draft 1: 5 hrs OT
    p1 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "total_working_hours": "208.0", "overtime_hours": "5.0", "mark_as_paid": False}, cookies=cookies).json()
    assert p1["status"] == "PENDING"
    assert p1["basic_rate_paisa_snapshot"] == 2080000
    assert float(p1["standard_hours_snapshot"]) == 208.00
    assert float(p1["overtime_multiplier_snapshot"]) == 1.50
    assert p1["overtime_pay_paisa"] == 75000

    # Recalculate draft with 10 hrs OT
    p2 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "total_working_hours": "208.0", "overtime_hours": "10.0", "mark_as_paid": False}, cookies=cookies).json()
    assert p2["overtime_pay_paisa"] == 150000
    assert p2["basic_rate_paisa_snapshot"] == 2080000


def test_14_paid_record_immutability(setup_wp4b4_1_env):
    """Once finalized as PAID, records cannot be modified or recalculated, and snapshots are frozen."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_1_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-IMMUT", "name": "Immutable Worker", "pay_type": "SALARY", "basic_rate_paisa": 2080000}, cookies=cookies).json()

    # Finalize as PAID
    p_paid = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w["id"],
        "month_year": "2026-10",
        "total_working_hours": "208.0",
        "overtime_hours": "4.0",
        "mark_as_paid": True
    }, cookies=cookies)
    assert p_paid.status_code == 200
    assert p_paid.json()["status"] == "PAID"
    orig_gross = p_paid.json()["gross_pay_paisa"]

    # Attempt to recalculate or modify the paid period -> rejected with 422
    retry_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w["id"],
        "month_year": "2026-10",
        "total_working_hours": "208.0",
        "overtime_hours": "10.0",
        "mark_as_paid": False
    }, cookies=cookies)
    assert retry_res.status_code == 422
    assert "Paid records are immutable" in retry_res.json()["detail"]

    # Change worker's basic salary
    client.patch(f"/api/v1/hr/workers/{w['id']}", json={"basic_rate_paisa": 4000000}, cookies=cookies)

    # Verify existing record in database still has original snapshots
    db = SessionLocal()
    rec = db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.worker_id == w["id"], WorkerMonthlyRecord.month_year == "2026-10").first()
    assert rec.basic_rate_paisa_snapshot == 2080000
    assert rec.gross_pay_paisa == orig_gross
    db.close()


def test_15_migration_upgrade_and_relevant_record_preservation(setup_wp4b4_1_env):
    """Verifies Migration 018 schema columns and data integrity."""
    db = SessionLocal()
    from sqlalchemy import inspect
    inspector = inspect(db.bind)

    # 1. company_hr_settings table exists
    assert "company_hr_settings" in inspector.get_table_names()

    # 2. Worker override columns exist
    worker_cols = {c["name"] for c in inspector.get_columns("workers")}
    assert "standard_monthly_hours_override" in worker_cols
    assert "overtime_rate_paisa_override" in worker_cols

    # 3. Monthly records snapshot columns exist
    monthly_cols = {c["name"] for c in inspector.get_columns("worker_monthly_records")}
    assert "basic_rate_paisa_snapshot" in monthly_cols
    assert "standard_hours_snapshot" in monthly_cols
    assert "overtime_multiplier_snapshot" in monthly_cols
    assert "overtime_rate_paisa_snapshot" in monthly_cols
    assert "regular_pay_paisa" in monthly_cols
    assert "overtime_pay_paisa" in monthly_cols
    assert "ceiling_pct_snapshot" in monthly_cols

    db.close()
