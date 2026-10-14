from decimal import Decimal
import pytest
from datetime import date
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models import Company, User, Worker, WorkerAdvance, WorkerMonthlyRecord, CompanyHRSettings
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME


@pytest.fixture(scope="module")
def setup_c1_c2_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db = SessionLocal()

    # Company 1
    comp1 = db.query(Company).filter(Company.code == "C1C2_CO1").first()
    if not comp1:
        comp1 = Company(name="C1C2 Factory One", code="C1C2_CO1")
        db.add(comp1)
        db.commit()
        db.refresh(comp1)

    # Company 2 (for tenant isolation)
    comp2 = db.query(Company).filter(Company.code == "C1C2_CO2").first()
    if not comp2:
        comp2 = Company(name="C1C2 Factory Two", code="C1C2_CO2")
        db.add(comp2)
        db.commit()
        db.refresh(comp2)

    # Settings for Company 1
    s1 = db.query(CompanyHRSettings).filter(CompanyHRSettings.company_id == comp1.id).first()
    if not s1:
        s1 = CompanyHRSettings(company_id=comp1.id, standard_monthly_hours=Decimal("208.00"), overtime_multiplier=Decimal("1.50"), max_advance_deduction_pct=50)
        db.add(s1)
    else:
        s1.standard_monthly_hours = Decimal("208.00")
        s1.overtime_multiplier = Decimal("1.50")
        s1.max_advance_deduction_pct = 50

    # Users in Company 1
    admin1 = db.query(User).filter(User.username == "c1c2_admin1").first()
    if not admin1:
        admin1 = User(
            company_id=comp1.id,
            name="C1C2 Admin One",
            username="c1c2_admin1",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin1)

    # Users in Company 2
    admin2 = db.query(User).filter(User.username == "c1c2_admin2").first()
    if not admin2:
        admin2 = User(
            company_id=comp2.id,
            name="C1C2 Admin Two",
            username="c1c2_admin2",
            password_hash=get_password_hash("Admin2Pass123!"),
            role="admin",
            active=True
        )
        db.add(admin2)

    db.commit()

    # Clean records
    db.query(WorkerAdvance).filter(WorkerAdvance.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(WorkerMonthlyRecord).filter(WorkerMonthlyRecord.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.query(Worker).filter(Worker.company_id.in_([comp1.id, comp2.id])).delete(synchronize_session=False)
    db.commit()
    db.close()

    return {
        "company1_id": comp1.id,
        "company2_id": comp2.id,
        "admin1": ("c1c2_admin1", "AdminPass123!"),
        "admin2": ("c1c2_admin2", "Admin2Pass123!"),
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    token = resp.cookies.get(COOKIE_NAME)
    assert token, "Cookie not set on login response"
    return {COOKIE_NAME: token}


# =========================================================================
# C1: RECONCILIATION OF LEGACY UNLINKED RECOVERIES
# =========================================================================

def test_c1_single_advance_with_legacy_unlinked_partial_recovery(setup_c1_c2_env):
    """
    Scenario: Worker took an advance of 1,000,000 paisa.
    A legacy unlinked recovery of 400,000 paisa exists (parent_advance_id = None).
    Reconciled remaining balance must be 600,000 paisa, NOT 1,000,000.
    Payroll capacity and deduction must be capped at 600,000 paisa.
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])
    co_id = setup_c1_c2_env["company1_id"]

    # 1. Create worker
    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C1-01",
        "name": "Legacy Worker 1",
        "pay_type": "SALARY",
        "basic_rate_paisa": 5000000  # NPR 50,000
    }, cookies=cookies).json()
    w_id = w["id"]

    # 2. Directly insert an issued advance and a legacy unlinked recovery in DB
    db = SessionLocal()
    admin_user = db.query(User).filter(User.username == setup_c1_c2_env["admin1"][0]).first()
    adv = WorkerAdvance(
        company_id=co_id,
        worker_id=w_id,
        amount_paisa=1000000,
        entry_type="ISSUED",
        date=date(2026, 7, 1),
        notes="Pre-019 advance",
        actor_id=admin_user.id
    )
    db.add(adv)
    db.flush()

    legacy_rec = WorkerAdvance(
        company_id=co_id,
        worker_id=w_id,
        amount_paisa=400000,
        entry_type="RECOVERED",
        date=date(2026, 7, 31),
        notes="Pre-019 unlinked recovery",
        actor_id=admin_user.id,
        parent_advance_id=None,
        monthly_record_id=None
    )
    db.add(legacy_rec)
    db.commit()
    db.close()

    # 3. Verify history endpoint reports reconciled remaining principal = 600,000
    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 600000
    issued_item = next(a for a in hist["advances"] if a["entry_type"] == "ISSUED")
    assert issued_item["remaining_principal_paisa"] == 600000

    # 4. Process payroll for 2026-08: Even though 50% capacity is 2,500,000 paisa,
    # deduction must strictly cap at 600,000 paisa (not 1,000,000 paisa!)
    pay = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-08",
        "mark_as_paid": True
    }, cookies=cookies).json()

    assert pay["advance_deduction_paisa"] == 600000
    assert pay["net_paid_paisa"] == 4400000

    # 5. Worker debt is now fully settled (0 paisa)
    hist2 = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist2["worker"]["outstanding_advance_paisa"] == 0
    issued_item2 = next(a for a in hist2["advances"] if a["entry_type"] == "ISSUED")
    assert issued_item2["remaining_principal_paisa"] == 0


def test_c1_multiple_advances_multiple_legacy_unlinked_recoveries(setup_c1_c2_env):
    """
    Scenario:
    Advance 1: 500,000 (2026-06-01)
    Advance 2: 700,000 (2026-07-01)
    Legacy recovery 1: 300,000 (2026-06-15, unlinked)
    Legacy recovery 2: 400,000 (2026-07-15, unlinked)
    Total issued = 1,200,000. Total legacy recovered = 700,000.
    Reconciled FIFO allocation:
    - Advance 1: 500,000 - 300,000 - 200,000 = 0 paisa remaining.
    - Advance 2: 700,000 - 200,000 = 500,000 paisa remaining.
    Sum of per-advance remaining = 0 + 500,000 = 500,000 paisa == aggregate outstanding!
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])
    co_id = setup_c1_c2_env["company1_id"]

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C1-02",
        "name": "Legacy Multi Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 4000000
    }, cookies=cookies).json()
    w_id = w["id"]

    db = SessionLocal()
    admin_user = db.query(User).filter(User.username == setup_c1_c2_env["admin1"][0]).first()
    a1 = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=500000, entry_type="ISSUED", date=date(2026, 6, 1), actor_id=admin_user.id)
    a2 = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=700000, entry_type="ISSUED", date=date(2026, 7, 1), actor_id=admin_user.id)
    r1 = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=300000, entry_type="RECOVERED", date=date(2026, 6, 15), actor_id=admin_user.id, parent_advance_id=None)
    r2 = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=400000, entry_type="RECOVERED", date=date(2026, 7, 15), actor_id=admin_user.id, parent_advance_id=None)
    db.add_all([a1, a2, r1, r2])
    db.commit()
    db.close()

    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 500000
    issued_map = {a["id"]: a["remaining_principal_paisa"] for a in hist["advances"] if a["entry_type"] == "ISSUED"}
    assert issued_map[a1.id] == 0
    assert issued_map[a2.id] == 500000
    assert sum(issued_map.values()) == hist["worker"]["outstanding_advance_paisa"]


def test_c1_mixture_of_legacy_unlinked_and_new_linked_recoveries(setup_c1_c2_env):
    """
    Scenario:
    Advance 1: 1,000,000 paisa.
    Legacy unlinked recovery: 300,000 paisa.
    New linked recovery on Advance 1: 200,000 paisa.
    Advance 1 remaining principal must be: 1,000,000 - 200,000 (linked) - 300,000 (legacy) = 500,000 paisa.
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])
    co_id = setup_c1_c2_env["company1_id"]

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C1-03",
        "name": "Mixed Recovery Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=cookies).json()
    w_id = w["id"]

    db = SessionLocal()
    admin_user = db.query(User).filter(User.username == setup_c1_c2_env["admin1"][0]).first()
    adv = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=1000000, entry_type="ISSUED", date=date(2026, 5, 1), actor_id=admin_user.id)
    db.add(adv)
    db.flush()

    leg_rec = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=300000, entry_type="RECOVERED", date=date(2026, 5, 15), actor_id=admin_user.id, parent_advance_id=None)
    linked_rec = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=200000, entry_type="RECOVERED", date=date(2026, 6, 1), actor_id=admin_user.id, parent_advance_id=adv.id)
    db.add_all([leg_rec, linked_rec])
    db.commit()
    db.close()

    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 500000
    adv_item = next(a for a in hist["advances"] if a["entry_type"] == "ISSUED")
    assert adv_item["remaining_principal_paisa"] == 500000


def test_c1_inconsistent_over_recovered_ledger_rejected(setup_c1_c2_env):
    """
    Scenario: An inconsistent historical ledger exists where recoveries exceed issued advances.
    System must refuse additional recovery attempts (HTTP 422) rather than silently clamping to 0.
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])
    co_id = setup_c1_c2_env["company1_id"]

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C1-OVER",
        "name": "Over Recovered Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2000000
    }, cookies=cookies).json()
    w_id = w["id"]

    db = SessionLocal()
    admin_user = db.query(User).filter(User.username == setup_c1_c2_env["admin1"][0]).first()
    # Issued 200,000, but recovered 300,000
    a = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=200000, entry_type="ISSUED", date=date(2026, 1, 1), actor_id=admin_user.id)
    r = WorkerAdvance(company_id=co_id, worker_id=w_id, amount_paisa=300000, entry_type="RECOVERED", date=date(2026, 1, 15), actor_id=admin_user.id, parent_advance_id=None)
    db.add_all([a, r])
    db.commit()
    db.close()

    # Repayment attempt must be rejected with 422
    res_rep = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 50000,
        "entry_type": "RECOVERED"
    }, cookies=cookies)
    assert res_rep.status_code == 422
    assert "inconsistent advance ledger" in res_rep.json()["detail"]


# =========================================================================
# C2: CASH REPAYMENT SPLITTING ACROSS MULTIPLE ADVANCES
# =========================================================================

def test_c2_split_repayment_across_two_advances(setup_c1_c2_env):
    """
    Scenario:
    Advance A: 300,000 paisa (remaining 300,000).
    Advance B: 500,000 paisa (remaining 500,000).
    Repayment: 450,000 paisa submitted without parent_advance_id.
    Result:
    - Splits into Allocation 1: 300,000 linked to Advance A (fully paid, remaining: 0).
    - Allocation 2: 150,000 linked to Advance B (remaining: 350,000).
    - Response contains allocations list summing to 450,000.
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C2-01",
        "name": "Split Two Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3000000
    }, cookies=cookies).json()
    w_id = w["id"]

    adv_a = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 300000, "entry_type": "ISSUED", "date": "2026-08-01"}, cookies=cookies).json()
    adv_b = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 500000, "entry_type": "ISSUED", "date": "2026-08-15"}, cookies=cookies).json()

    # Repay 450,000 paisa unlinked
    res = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 450000,
        "entry_type": "RECOVERED"
    }, cookies=cookies)
    assert res.status_code == 201
    data = res.json()

    assert data["amount_paisa"] == 450000
    assert data["remaining_principal_paisa"] == 350000  # Total remaining: 800,000 - 450,000 = 350,000
    assert "allocations" in data and len(data["allocations"]) == 2

    alloc_map = {a["parent_advance_id"]: a["amount_paisa"] for a in data["allocations"]}
    assert alloc_map[adv_a["id"]] == 300000
    assert alloc_map[adv_b["id"]] == 150000

    # Verify per-advance remaining balances via history
    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    issued_map = {a["id"]: a["remaining_principal_paisa"] for a in hist["advances"] if a["entry_type"] == "ISSUED"}
    assert issued_map[adv_a["id"]] == 0
    assert issued_map[adv_b["id"]] == 350000
    assert hist["worker"]["outstanding_advance_paisa"] == 350000


def test_c2_split_repayment_across_three_advances(setup_c1_c2_env):
    """
    Scenario:
    Adv 1: 100,000. Adv 2: 200,000. Adv 3: 300,000. (Total = 600,000)
    Repayment: 450,000.
    Allocates:
    - Adv 1: 100,000 (rem: 0)
    - Adv 2: 200,000 (rem: 0)
    - Adv 3: 150,000 (rem: 150,000)
    """
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-C2-02",
        "name": "Split Three Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 2500000
    }, cookies=cookies).json()
    w_id = w["id"]

    a1 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 100000, "entry_type": "ISSUED", "date": "2026-09-01"}, cookies=cookies).json()
    a2 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 200000, "entry_type": "ISSUED", "date": "2026-09-02"}, cookies=cookies).json()
    a3 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 300000, "entry_type": "ISSUED", "date": "2026-09-03"}, cookies=cookies).json()

    res = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 450000, "entry_type": "RECOVERED"}, cookies=cookies)
    assert res.status_code == 201
    data = res.json()
    assert len(data["allocations"]) == 3

    alloc_map = {a["parent_advance_id"]: a["amount_paisa"] for a in data["allocations"]}
    assert alloc_map[a1["id"]] == 100000
    assert alloc_map[a2["id"]] == 200000
    assert alloc_map[a3["id"]] == 150000

    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 150000


def test_c2_exact_full_settlement_repayment(setup_c1_c2_env):
    """Repayment exactly equal to total debt clears all advances to 0."""
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-C2-EXACT", "name": "Exact Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies).json()
    w_id = w["id"]

    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 250000, "entry_type": "ISSUED"}, cookies=cookies)
    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 350000, "entry_type": "ISSUED"}, cookies=cookies)

    res = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 600000, "entry_type": "RECOVERED"}, cookies=cookies)
    assert res.status_code == 201
    assert res.json()["remaining_principal_paisa"] == 0

    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 0


def test_c2_repayment_exceeding_total_debt_rejected_without_partial_writes(setup_c1_c2_env):
    """Repayment greater than total debt is rejected with 422 and creates zero records."""
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-C2-EXCEED", "name": "Exceed Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies).json()
    w_id = w["id"]

    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 200000, "entry_type": "ISSUED"}, cookies=cookies)

    # Attempt to repay 300,000 on a 200,000 debt
    res = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 300000, "entry_type": "RECOVERED"}, cookies=cookies)
    assert res.status_code == 422
    assert "exceeds total reconciled outstanding balance" in res.json()["detail"]

    # Verify no recoveries created
    db = SessionLocal()
    rec_count = db.query(WorkerAdvance).filter(WorkerAdvance.worker_id == w_id, WorkerAdvance.entry_type == "RECOVERED").count()
    assert rec_count == 0
    db.close()


def test_c2_explicit_targeted_repayment_cannot_exceed_parent_balance(setup_c1_c2_env):
    """When parent_advance_id is supplied, repayment cannot exceed that specific advance's balance."""
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-C2-TARGET", "name": "Target Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies).json()
    w_id = w["id"]

    a1 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 200000, "entry_type": "ISSUED"}, cookies=cookies).json()
    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 500000, "entry_type": "ISSUED"}, cookies=cookies)

    # Attempt to repay 300,000 specifically targeted to a1 (which only owes 200,000)
    res = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 300000,
        "entry_type": "RECOVERED",
        "parent_advance_id": a1["id"]
    }, cookies=cookies)
    assert res.status_code == 422
    assert "exceeds reconciled remaining balance" in res.json()["detail"]


def test_c2_same_date_advances_use_deterministic_id_ordering(setup_c1_c2_env):
    """Advances sharing the same date are allocated in strictly ascending ID order."""
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-C2-DATE", "name": "Same Date Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies).json()
    w_id = w["id"]

    today_str = str(date.today())
    a1 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 150000, "entry_type": "ISSUED", "date": today_str}, cookies=cookies).json()
    a2 = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 250000, "entry_type": "ISSUED", "date": today_str}, cookies=cookies).json()
    assert a1["id"] < a2["id"]

    res = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 200000, "entry_type": "RECOVERED"}, cookies=cookies).json()
    assert len(res["allocations"]) == 2
    assert res["allocations"][0]["parent_advance_id"] == a1["id"]
    assert res["allocations"][0]["amount_paisa"] == 150000
    assert res["allocations"][1]["parent_advance_id"] == a2["id"]
    assert res["allocations"][1]["amount_paisa"] == 50000


def test_c2_inactive_worker_can_split_repayment(setup_c1_c2_env):
    """Inactive workers can make multi-advance split repayments to settle debt."""
    client = TestClient(app)
    cookies = _login(client, *setup_c1_c2_env["admin1"])

    w = client.post("/api/v1/hr/workers", json={"worker_code": "WKR-C2-INACT", "name": "Inactive Split Worker", "pay_type": "SALARY", "basic_rate_paisa": 2000000}, cookies=cookies).json()
    w_id = w["id"]

    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 100000, "entry_type": "ISSUED"}, cookies=cookies)
    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 200000, "entry_type": "ISSUED"}, cookies=cookies)

    # Deactivate worker
    client.patch(f"/api/v1/hr/workers/{w_id}/status", json={"is_active": False, "inactive_reason": "Resigned"}, cookies=cookies)

    # Repay 250,000 across the two advances
    res = client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 250000, "entry_type": "RECOVERED"}, cookies=cookies)
    assert res.status_code == 201
    assert len(res.json()["allocations"]) == 2
    assert res.json()["remaining_principal_paisa"] == 50000
