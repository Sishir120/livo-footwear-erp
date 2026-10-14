import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase, RawMaterialMovement
from app.models.worker import Worker, WorkerAdvance
from app.core.security import get_password_hash
from app.api.deps import COOKIE_NAME
from app.api.v1.hr import _reconcile_worker_advances


@pytest.fixture(scope="module")
def setup_adversarial_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()

    db: Session = SessionLocal()

    comp_a = db.query(Company).filter(Company.code == "ADV_A").first()
    if not comp_a:
        comp_a = Company(name="Adversarial Corp A", code="ADV_A", pan_number="111111111")
        db.add(comp_a)
        db.commit()
        db.refresh(comp_a)

    comp_b = db.query(Company).filter(Company.code == "ADV_B").first()
    if not comp_b:
        comp_b = Company(name="Adversarial Corp B", code="ADV_B", pan_number="222222222")
        db.add(comp_b)
        db.commit()
        db.refresh(comp_b)

    user_a = db.query(User).filter(User.username == "adv_editor_a").first()
    if not user_a:
        user_a = User(
            name="Adv Editor A",
            username="adv_editor_a",
            company_id=comp_a.id,
            role="editor",
            active=True,
            password_hash=get_password_hash("EditorPass123!")
        )
        db.add(user_a)

    user_b = db.query(User).filter(User.username == "adv_editor_b").first()
    if not user_b:
        user_b = User(
            name="Adv Editor B",
            username="adv_editor_b",
            company_id=comp_b.id,
            role="editor",
            active=True,
            password_hash=get_password_hash("EditorPass123!")
        )
        db.add(user_b)

    db.commit()
    db.close()

    return {
        "comp_a_id": comp_a.id,
        "comp_b_id": comp_b.id,
        "user_a_creds": ("adv_editor_a", "EditorPass123!"),
        "user_b_creds": ("adv_editor_b", "EditorPass123!"),
    }


def _login(client: TestClient, username: str, password: str) -> dict:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    token = res.cookies.get(COOKIE_NAME)
    assert token
    return {COOKIE_NAME: token}


def test_reproduce_double_receive_purchase_order(setup_adversarial_env):
    """
    Test reproducing Finding 1: Repeated receipt of the same purchase order.
    A purchase order that is already RECEIVED should reject subsequent receipt calls with 409 Conflict.
    """
    client = TestClient(app)
    cookies_a = _login(client, *setup_adversarial_env["user_a_creds"])

    # 1. Create Supplier and Raw Material in Company A
    sup = client.post("/api/v1/purchase/suppliers", json={"code": "SUP-ADV-1", "name": "Adv Supplier"}, cookies=cookies_a).json()
    mat = client.post("/api/v1/purchase/raw-materials", json={"code": "MAT-ADV-1", "name": "Adv Leather", "unit": "kg"}, cookies=cookies_a).json()

    # 2. Create Purchase Order in ORDERED status
    po = client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": mat["id"],
        "quantity": 100.0,
        "unit_price": 500.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "ORDERED"
    }, cookies=cookies_a).json()
    po_id = po["id"]

    # 3. Receive Goods (First receipt -> Valid)
    recv1 = client.post(f"/api/v1/purchase/purchases/{po_id}/receive", json={
        "receipt_date_ad": "2026-10-02",
        "receipt_date_bs": "2083-06-16",
        "received_quantity": 100.0
    }, cookies=cookies_a)
    assert recv1.status_code == 200
    assert recv1.json()["status"] == "RECEIVED"

    # 4. Attempt duplicate receipt on already RECEIVED PO -> Must be rejected with 409 Conflict
    recv2 = client.post(f"/api/v1/purchase/purchases/{po_id}/receive", json={
        "receipt_date_ad": "2026-10-03",
        "receipt_date_bs": "2083-06-17",
        "received_quantity": 100.0
    }, cookies=cookies_a)

    # In vulnerable state, this returns 200 and doubles stock. In secure state, returns 409 Conflict.
    assert recv2.status_code == 409, f"Expected 409 Conflict on double receipt, got {recv2.status_code}: {recv2.text}"


def test_reproduce_hr_single_advance_over_recovery_reconciliation(setup_adversarial_env):
    """
    Test reproducing Finding 2: Single advance with linked recovery exceeding its principal.
    Reconciliation engine should flag is_ledger_consistent = False.
    """
    db: Session = SessionLocal()
    comp_id = setup_adversarial_env["comp_a_id"]

    import uuid
    uid = uuid.uuid4().hex[:6].upper()
    wkr = Worker(
        company_id=comp_id,
        worker_code=f"WKR-OVER-ADV-{uid}",
        name="Over Adv Worker",
        pay_type="SALARY",
        basic_rate_paisa=5000000,
        is_active=True
    )
    db.add(wkr)
    db.commit()
    db.refresh(wkr)

    # Advance 1: 500,000 paisa
    adv1 = WorkerAdvance(company_id=comp_id, worker_id=wkr.id, amount_paisa=500000, entry_type="ISSUED", date=date(2026, 1, 1), actor_id=1)
    # Advance 2: 500,000 paisa
    adv2 = WorkerAdvance(company_id=comp_id, worker_id=wkr.id, amount_paisa=500000, entry_type="ISSUED", date=date(2026, 2, 1), actor_id=1)
    db.add_all([adv1, adv2])
    db.flush()

    # Corrupted / over-recovery on Advance 1: 600,000 paisa linked directly to adv1
    rec1 = WorkerAdvance(company_id=comp_id, worker_id=wkr.id, amount_paisa=600000, entry_type="RECOVERED", date=date(2026, 1, 15), actor_id=1, parent_advance_id=adv1.id)
    db.add(rec1)
    db.commit()

    recon = _reconcile_worker_advances(db, comp_id, wkr.id)
    db.close()

    # Total issued = 1,000,000. Total recovered = 600,000.
    # Raw debt = 400,000.
    # But Advance 1 was over-recovered by 100,000!
    # is_ledger_consistent must be False because Advance 1 is over-recovered.
    assert recon["is_ledger_consistent"] is False, "Expected is_ledger_consistent to be False when an individual advance is over-recovered"


def test_unauthenticated_metrics_access():
    """
    Test checking Finding 3: Metrics endpoint exposure.
    Verify whether /metrics returns telemetry without authentication.
    """
    client = TestClient(app)
    res = client.get("/api/v1/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers.get("content-type", "")


def test_cross_tenant_idor_boundary(setup_adversarial_env):
    """
    Adversarial BOLA/IDOR test:
    User in Company B attempts to access Company A's Supplier, Purchase, Product, and Worker.
    Must return 404 Not Found (tenant-isolated).
    """
    client = TestClient(app)
    cookies_a = _login(client, *setup_adversarial_env["user_a_creds"])
    cookies_b = _login(client, *setup_adversarial_env["user_b_creds"])

    import uuid
    tag = uuid.uuid4().hex[:6].upper()

    # Company A creates resources
    sup_a = client.post("/api/v1/purchase/suppliers", json={"code": f"SUP-IDOR-{tag}", "name": "Company A Supplier"}, cookies=cookies_a).json()
    wkr_a = client.post("/api/v1/hr/workers", json={"worker_code": f"WKR-IDOR-{tag}", "name": "Worker A", "pay_type": "SALARY", "basic_rate_paisa": 3000000}, cookies=cookies_a).json()

    # Company B tries to read Company A's supplier
    res_sup = client.get(f"/api/v1/purchase/suppliers/{sup_a['id']}", cookies=cookies_b)
    assert res_sup.status_code == 404, f"Expected 404 for cross-tenant supplier, got {res_sup.status_code}"

    # Company B tries to read Company A's worker history
    res_wkr = client.get(f"/api/v1/hr/workers/{wkr_a['id']}/history", cookies=cookies_b)
    assert res_wkr.status_code == 404, f"Expected 404 for cross-tenant worker, got {res_wkr.status_code}"

    # Company B tries to issue advance to Company A's worker
    res_adv = client.post("/api/v1/hr/advances", json={"worker_id": wkr_a["id"], "amount_paisa": 100000, "entry_type": "ISSUED"}, cookies=cookies_b)
    assert res_adv.status_code == 404, f"Expected 404 for cross-tenant advance issuance, got {res_adv.status_code}"


def test_cash_repayment_between_draft_preview_and_finalization(setup_adversarial_env):
    """
    Adversarial timing test:
    1. Worker has advance of 100,000 paisa.
    2. Draft payroll is computed (mark_as_paid=False) with 50,000 paisa deduction.
    3. Worker makes full cash repayment of 100,000 paisa before finalization.
    4. Payroll is finalized (mark_as_paid=True).
    Expected: Final payroll recalculates live debt, realizes debt is 0, deducts 0 paisa,
    and creates ZERO recovery records!
    """
    client = TestClient(app)
    cookies_a = _login(client, *setup_adversarial_env["user_a_creds"])

    import uuid
    w_tag = uuid.uuid4().hex[:6].upper()

    w = client.post("/api/v1/hr/workers", json={
        "worker_code": f"WKR-TIMING-{w_tag}",
        "name": "Timing Worker",
        "pay_type": "SALARY",
        "basic_rate_paisa": 4000000  # NPR 40,000
    }, cookies=cookies_a).json()
    w_id = w["id"]

    # Issue advance: 100,000 paisa
    client.post("/api/v1/hr/advances", json={"worker_id": w_id, "amount_paisa": 100000, "entry_type": "ISSUED"}, cookies=cookies_a)

    # 1. Draft payroll preview for 2026-10 (mark_as_paid=False)
    draft = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "mark_as_paid": False
    }, cookies=cookies_a).json()
    assert draft["status"] == "PENDING"
    assert draft["advance_deduction_paisa"] == 100000

    # 2. Worker repays full advance via cash before payroll finalization!
    repay = client.post("/api/v1/hr/advances", json={
        "worker_id": w_id,
        "amount_paisa": 100000,
        "entry_type": "RECOVERED"
    }, cookies=cookies_a)
    assert repay.status_code == 201

    # 3. Finalize payroll for 2026-10 (mark_as_paid=True)
    final = client.post("/api/v1/hr/monthly-payroll", json={
        "worker_id": w_id,
        "month_year": "2026-10",
        "mark_as_paid": True
    }, cookies=cookies_a).json()

    assert final["status"] == "PAID"
    # Live debt was 0, so deduction MUST be 0!
    assert final["advance_deduction_paisa"] == 0
    assert final["net_paid_paisa"] == 4000000

    # Verify worker history has NO extra recovery records
    hist = client.get(f"/api/v1/hr/workers/{w_id}/history", cookies=cookies_a).json()
    assert hist["worker"]["outstanding_advance_paisa"] == 0
    recoveries = [a for a in hist["advances"] if a["entry_type"] == "RECOVERED"]
    # Only the 1 cash repayment, ZERO payroll recoveries
    assert len(recoveries) == 1
    assert recoveries[0]["monthly_record_id"] is None


def test_input_validation_negative_and_zero_rejections(setup_adversarial_env):
    """
    Adversarial input validation tests:
    Negative prices, negative quantities, zero amounts.
    """
    client = TestClient(app)
    cookies_a = _login(client, *setup_adversarial_env["user_a_creds"])

    # Negative worker salary
    res_w = client.post("/api/v1/hr/workers", json={
        "worker_code": "WKR-NEG",
        "name": "Negative Salary",
        "pay_type": "SALARY",
        "basic_rate_paisa": -50000
    }, cookies=cookies_a)
    assert res_w.status_code == 422

    # Zero advance amount
    res_adv = client.post("/api/v1/hr/advances", json={
        "worker_id": 1,
        "amount_paisa": 0,
        "entry_type": "ISSUED"
    }, cookies=cookies_a)
    assert res_adv.status_code == 422


def test_concurrent_purchase_receipt_race(setup_adversarial_env):
    """
    Deterministic concurrency test:
    Verify that concurrent receipt requests for the same purchase order cannot both succeed.
    - Exactly 1 request succeeds (HTTP 200).
    - All other concurrent requests fail with HTTP 409 Conflict.
    - Stock movements has exactly 1 entry.
    - Raw material stock increases by exactly the received quantity (zero duplicate inflation).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    client = TestClient(app)
    cookies_a = _login(client, *setup_adversarial_env["user_a_creds"])

    import uuid
    race_tag = uuid.uuid4().hex[:6].upper()

    sup = client.post("/api/v1/purchase/suppliers", json={
        "code": f"SUP-CRACE-{race_tag}",
        "name": "Concurrent Race Supplier"
    }, cookies=cookies_a).json()

    rm = client.post("/api/v1/purchase/raw-materials", json={
        "code": f"RM-CRACE-{race_tag}",
        "name": "Race Synthetic Foam",
        "unit": "kg"
    }, cookies=cookies_a).json()
    rm_id = rm["id"]

    po = client.post("/api/v1/purchase/purchases", json={
        "supplier_id": sup["id"],
        "raw_material_id": rm_id,
        "quantity": 100.0,
        "unit_price": 500.0,
        "purchase_date_ad": "2026-10-01",
        "purchase_date_bs": "2083-06-15",
        "status": "ORDERED"
    }, cookies=cookies_a).json()
    po_id = po["id"]

    results = []
    def attempt_receive(worker_idx: int):
        with TestClient(app, cookies=cookies_a) as tclient:
            res = tclient.post(f"/api/v1/purchases/{po_id}/receive", json={
                "received_quantity": 100.0,
                "carrying_in_paisa": 1000,
                "import_duty_paisa": 0,
                "china_carrying_paisa": 0,
                "insurance_paisa": 0,
                "receipt_date_ad": "2026-10-02",
                "receipt_date_bs": "2083-06-16",
                "notes": f"Concurrent receive worker {worker_idx}"
            })
            return res.status_code, res.text

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_receive, i) for i in range(5)]
        for f in as_completed(futures):
            results.append(f.result())

    status_codes = [sc for sc, _ in results]
    success_200 = sum(1 for sc in status_codes if sc == 200)
    conflict_409 = sum(1 for sc in status_codes if sc == 409)

    assert success_200 == 1, f"Expected exactly 1 receipt to succeed, got {success_200}. Statuses: {status_codes}"
    assert conflict_409 == 4, f"Expected 4 rejections with 409 Conflict, got {conflict_409}. Statuses: {status_codes}"

    # Verify material card and movement count
    card = client.get(f"/api/v1/purchase/materials/{rm_id}/card", cookies=cookies_a).json()
    assert card["material"]["current_stock"] == 100.0, f"Stock inflated! Expected 100.0, got {card['material']['current_stock']}"
    assert card["current_balance"] == 100.0, f"Balance mismatch! Expected 100.0, got {card['current_balance']}"
    assert len(card["movements"]) == 1, f"Duplicate movements created! Expected 1, got {len(card['movements'])}"
