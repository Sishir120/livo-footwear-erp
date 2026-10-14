from decimal import Decimal
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.db.session import SessionLocal
from app.models import Company, User, Worker, WorkerAdvance, WorkerMonthlyRecord, CompanyHRSettings
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_wp4b4_2_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db = SessionLocal()

    # 1. Company 1
    comp1 = db.query(Company).filter(Company.code == "WP4B2_CO1").first()
    if not comp1:
        comp1 = Company(name="WP 4B2 Factory One", code="WP4B2_CO1")
        db.add(comp1)
        db.commit()
        db.refresh(comp1)

    # 2. Company 2
    comp2 = db.query(Company).filter(Company.code == "WP4B2_CO2").first()
    if not comp2:
        comp2 = Company(name="WP 4B2 Factory Two", code="WP4B2_CO2")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # 3. Settings for Company 1 (208 hours, 1.5x, 50% ceiling)
    s1 = db.query(CompanyHRSettings).filter(CompanyHRSettings.company_id == comp1.id).first()
    if not s1:
        s1 = CompanyHRSettings(company_id=comp1.id, standard_monthly_hours=Decimal("208.00"), overtime_multiplier=Decimal("1.50"), max_advance_deduction_pct=50)
        db.add(s1)
    else:
        s1.standard_monthly_hours = Decimal("208.00")
        s1.overtime_multiplier = Decimal("1.50")
        s1.max_advance_deduction_pct = 50

    # 4. Users in Company 1
    admin1 = db.query(User).filter(User.username == "wp4b2_admin1").first()
    if not admin1:
        admin1 = User(
            company_id=comp1.id,
            name="HR Admin 4B2",
            username="wp4b2_admin1",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin1)

    editor1 = db.query(User).filter(User.username == "wp4b2_editor1").first()
    if not editor1:
        editor1 = User(
            company_id=comp1.id,
            name="HR Editor 4B2",
            username="wp4b2_editor1",
            password_hash=get_password_hash("EditorPass123!"),
            role="editor",
            active=True
        )
        db.add(editor1)

    # 5. Users in Company 2
    admin2 = db.query(User).filter(User.username == "wp4b2_admin2").first()
    if not admin2:
        admin2 = User(
            company_id=comp2.id,
            name="HR Admin Two 4B2",
            username="wp4b2_admin2",
            password_hash=get_password_hash("Admin2Pass123!"),
            role="admin",
            active=True
        )
        db.add(admin2)

    db.commit()

    # Clean records for test companies
    db.query(WorkerAdvance).filter(WorkerAdvance.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.commit()
    db.close()

    return {
        "company1_id": comp1.id,
        "company2_id": comp2.id,
        "admin1": ("wp4b2_admin1", "AdminPass123!"),
        "editor1": ("wp4b2_editor1", "EditorPass123!"),
        "admin2": ("wp4b2_admin2", "Admin2Pass123!"),
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


def test_1_fifo_recovery_with_multiple_advances(setup_wp4b4_2_env):
    """Multiple advances are recovered in deterministic FIFO order (earlier date/id first)."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    # Create worker
    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-FIFO-01",
        "name": "FIFO Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 5000000  # NPR 50,000 monthly
    }, cookies=cookies).json()
    w_id = w["id"]

    # Issue Advance A on 2026-09-01: 600,000 paisa (NPR 6,000), installment 300,000
    adv_a = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 600000,
        "entry_type": "ISSUED",
        "date": "2026-09-01",
        "installment_amount_paisa": 300000,
        "notes": "Advance A"
    }, cookies=cookies).json()

    # Issue Advance B on 2026-09-15: 400,000 paisa (NPR 4,000), installment 200,000
    adv_b = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 400000,
        "entry_type": "ISSUED",
        "date": "2026-09-15",
        "installment_amount_paisa": 200000,
        "notes": "Advance B"
    }, cookies=cookies).json()

    # Payroll for 2026-09: capacity is ample (50% of 5,000,000 = 2,500,000).
    # FIFO: Advance A installment = 300,000. Advance B installment = 200,000. Total deduction = 500,000.
    pay_res = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-09",
        "mark_as_paid": True
    }, cookies=cookies)
    assert pay_res.status_code == 200
    data = pay_res.json()
    assert data["advance_deduction_paisa"] == 500000
    assert data["net_paid_paisa"] == 4500000

    # Verify 2 linked recovery entries created in DB
    db = SessionLocal()
    rec_a = db.query(WorkerAdvance).filter(WorkerAdvance.parent_advance_id == adv_a["id"], WorkerAdvance.entry_type == "RECOVERED").first()
    rec_b = db.query(WorkerAdvance).filter(WorkerAdvance.parent_advance_id == adv_b["id"], WorkerAdvance.entry_type == "RECOVERED").first()
    assert rec_a is not None and rec_a.amount_paisa == 300000
    assert rec_b is not None and rec_b.amount_paisa == 200000
    assert rec_a.monthly_record_id == data["id"]
    assert rec_b.monthly_record_id == data["id"]
    db.close()


def test_2_fixed_installment_enforcement(setup_wp4b4_2_env):
    """Configured fixed installment limits deduction even when capacity is large."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-INST-01",
        "name": "Installment Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 4000000
    }, cookies=cookies).json()

    # Issue advance 1,000,000 paisa with fixed installment 250,000 paisa
    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 1000000,
        "entry_type": "ISSUED",
        "installment_amount_paisa": 250000
    }, cookies=cookies).json()

    # Available capacity is 2,000,000 paisa (50% of 4M). But installment is strictly 250,000.
    pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w["id"],
        "month_year": "2026-10",
        "mark_as_paid": True
    }, cookies=cookies).json()

    assert pay["advance_deduction_paisa"] == 250000
    assert pay["net_paid_paisa"] == 3750000


def test_3_partial_recovery_when_capacity_is_insufficient(setup_wp4b4_2_env):
    """When ordinary deduction ceiling is smaller than installment, recovery is capped at ceiling."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    # Worker with salary NPR 10,000 (1,000,000 paisa). 50% ceiling = 500,000 paisa.
    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-CAP-01",
        "name": "Low Salary Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 1000000
    }, cookies=cookies).json()

    # Installment is 800,000 paisa (exceeds the 500,000 paisa ceiling)
    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 2000000,
        "entry_type": "ISSUED",
        "installment_amount_paisa": 800000
    }, cookies=cookies).json()

    pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w["id"],
        "month_year": "2026-10",
        "mark_as_paid": True
    }, cookies=cookies).json()

    # Must be capped exactly at 500,000 paisa (ceiling)
    assert pay["advance_deduction_paisa"] == 500000
    assert pay["net_paid_paisa"] == 500000


def test_4_installment_roll_forward_across_months(setup_wp4b4_2_env):
    """Unpaid principal rolls forward into subsequent payrolls until exhausted."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-ROLL-01",
        "name": "Roll Forward Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=cookies).json()

    # Advance 700,000 paisa with installment 300,000 paisa
    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 700000,
        "entry_type": "ISSUED",
        "installment_amount_paisa": 300000
    }, cookies=cookies).json()

    # Month 1: recovers 300,000 (remaining: 400,000)
    p1 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-08", "mark_as_paid": True}, cookies=cookies).json()
    assert p1["advance_deduction_paisa"] == 300000

    # Month 2: recovers 300,000 (remaining: 100,000)
    p2 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-09", "mark_as_paid": True}, cookies=cookies).json()
    assert p2["advance_deduction_paisa"] == 300000

    # Month 3: installment is 300,000, but remaining principal is only 100,000 -> recovers 100,000
    p3 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "mark_as_paid": True}, cookies=cookies).json()
    assert p3["advance_deduction_paisa"] == 100000

    # Month 4: advance is fully paid -> 0 deduction
    p4 = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-11", "mark_as_paid": True}, cookies=cookies).json()
    assert p4["advance_deduction_paisa"] == 0


def test_5_legacy_advance_without_configured_installment(setup_wp4b4_2_env):
    """Legacy advances without configured installment are recoverable up to available capacity."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-LEG-01",
        "name": "Legacy Advance Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2000000
    }, cookies=cookies).json()

    # Issue advance with NO installment_amount_paisa (None)
    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 500000,
        "entry_type": "ISSUED",
        "installment_amount_paisa": None
    }, cookies=cookies).json()

    # Payroll capacity is 1,000,000. Advance principal is 500,000 -> recovers full 500,000.
    pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w["id"],
        "month_year": "2026-10",
        "mark_as_paid": True
    }, cookies=cookies).json()
    assert pay["advance_deduction_paisa"] == 500000
    assert pay["net_paid_paisa"] == 1500000


def test_6_inactive_worker_repayment_allowed_but_issuance_blocked(setup_wp4b4_2_env):
    """Inactive workers can repay existing debt, but cannot receive new advances or process payroll."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    # Active worker takes advance
    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-INACT-REP",
        "name": "Repaying Inactive Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2500000
    }, cookies=cookies).json()

    adv = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 600000,
        "entry_type": "ISSUED"
    }, cookies=cookies).json()

    # Deactivate worker
    client.patch(f"/api/v1/hr/workers/{w['id']}/status", json={"is_active": False, "inactive_reason": "Resigned"}, cookies=cookies)

    # 1. New advance issuance BLOCKED (400)
    res_iss = client.post("/api/v1/hr/advances", json={"worker_id": w["id"], "amount_paisa": 100000, "entry_type": "ISSUED"}, cookies=cookies)
    assert res_iss.status_code == 400

    # 2. Payroll processing BLOCKED (400)
    res_pay = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10"}, cookies=cookies)
    assert res_pay.status_code == 400

    # 3. Cash repayment PERMITTED (201)
    res_rep = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 400000,
        "entry_type": "RECOVERED",
        "parent_advance_id": adv["id"],
        "notes": "Cash settlement after resignation"
    }, cookies=cookies)
    assert res_rep.status_code == 201
    assert res_rep.json()["remaining_principal_paisa"] == 200000

    # 4. Excessive repayment rejected (422)
    res_over = client.post("/api/v1/hr/advances", json={
        "worker_id": w["id"],
        "amount_paisa": 300000,  # exceeds remaining 200,000
        "entry_type": "RECOVERED",
        "parent_advance_id": adv["id"]
    }, cookies=cookies)
    assert res_over.status_code == 422


def test_7_database_uniqueness_enforcement_for_same_advance_payroll_pair(setup_wp4b4_2_env):
    """Partial unique index uq_payroll_advance_recovery prevents duplicate recovery rows for same advance and payroll."""
    db = SessionLocal()
    # Find existing linked recovery row
    rec = db.query(WorkerAdvance).filter(WorkerAdvance.monthly_record_id.isnot(None), WorkerAdvance.parent_advance_id.isnot(None)).first()
    assert rec is not None

    # Attempt to insert a duplicate recovery with same (monthly_record_id, parent_advance_id)
    dup = WorkerAdvance(
        company_id=rec.company_id,
        worker_id=rec.worker_id,
        amount_paisa=50000,
        entry_type="RECOVERED",
        date=date.today(),
        actor_id=rec.actor_id,
        parent_advance_id=rec.parent_advance_id,
        monthly_record_id=rec.monthly_record_id
    )
    db.add(dup)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_8_tenant_isolation_advances_and_repayments(setup_wp4b4_2_env):
    """Company A users cannot view, repay, or deduct advances belonging to Company B."""
    client_a = TestClient(app)
    cookies_a = _login(client_a, *setup_wp4b4_2_env["admin1"])

    client_b = TestClient(app)
    cookies_b = _login(client_b, *setup_wp4b4_2_env["admin2"])

    # Company 1 worker & advance
    w1 = client_a.post("/api/v1/hr/workers", json={"worker_code": "WKR-CO1-ISO", "name": "Co1 Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies_a).json()
    adv1 = client_a.post("/api/v1/hr/advances", json={"worker_id": w1["id"], "amount_paisa": 500000, "entry_type": "ISSUED"}, cookies=cookies_a).json()

    # Company 2 admin attempts to repay Company 1's advance -> 404 Not Found
    res = client_b.post("/api/v1/hr/advances", json={"worker_id": w1["id"], "amount_paisa": 100000, "entry_type": "RECOVERED", "parent_advance_id": adv1["id"]}, cookies=cookies_b)
    assert res.status_code == 404

    # Company 2 admin attempts to process payroll for Company 1's worker -> 404 Not Found
    pay_res = client_b.post("/api/v1/hr/monthly-payroll", json={"worker_id": w1["id"], "month_year": "2026-10"}, cookies=cookies_b)
    assert pay_res.status_code == 404


def test_9_exact_net_reconciliation_and_no_negative_net(setup_wp4b4_2_env):
    """Stored net pay strictly reconciles with gross pay minus deductions and is never negative."""
    client = TestClient(app)
    cookies = _login(client, *setup_wp4b4_2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-RECON-01", "name": "Recon Worker", "pay_type": "SALARY", "basic_rate_paisa": 3000000}, cookies=cookies).json()
    client.post("/api/v1/hr/advances", json={"worker_id": w["id"], "amount_paisa": 1000000, "entry_type": "ISSUED", "installment_amount_paisa": 500000}, cookies=cookies)

    pay = client.post("/api/v1/hr/monthly-payroll", json={"worker_id": w["id"], "month_year": "2026-10", "mark_as_paid": True}, cookies=cookies).json()

    gross = pay["gross_pay_paisa"]
    ded = pay["advance_deduction_paisa"]
    net = pay["net_paid_paisa"]

    assert net == gross - ded
    assert net >= 0
    assert ded <= gross


def test_10_migration_019_schema_and_columns(setup_wp4b4_2_env):
    """Verify Migration 019 schema columns and partial index are properly installed."""
    db = SessionLocal()
    from sqlalchemy import inspect
    inspector = inspect(db.bind)

    cols = {c["name"] for c in inspector.get_columns("worker_advances")}
    assert "installment_amount_paisa" in cols
    assert "parent_advance_id" in cols
    assert "monthly_record_id" in cols

    indexes = {i["name"] for i in inspector.get_indexes("worker_advances")}
    assert "uq_payroll_advance_recovery" in indexes
    db.close()
