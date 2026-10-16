"""
Day 2 Security Regression Tests — RBAC and Authorization Hardening
Verifies:
1. Unauthenticated requests rejected (401).
2. Admin self-lockout prevention (self-deactivation and self-demotion blocked with 400).
3. Non-admin user management rejection (403).
4. Manager role acceptance and invalid role rejection (422).
5. HR compensation redaction for viewer role on GET /hr/workers.
6. HR worker financial history blocked for viewer role (403), allowed for editor/admin (200).
7. Fixed asset deletion restricted to admin (editor/viewer rejected with 403).
8. BOM item deletion restricted to admin (editor/viewer rejected with 403).
9. Sales expense deletion restricted to admin (editor/viewer rejected with 403).
10. Cross-company tenant isolation on protected resource mutations (404).
"""
import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.worker import Worker
from app.models.asset import FixedAsset
from app.models.bom import BillOfMaterials
from app.models.stock import Product
from app.models.purchase import RawMaterial
from app.models.sales import SalesExpense
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_day_2_fixtures():
    db: Session = SessionLocal()
    try:
        # Tenant Company 1
        comp1 = db.query(Company).filter(Company.code == "DAY2_C1").first()
        if not comp1:
            comp1 = Company(name="Day 2 Corp Primary", code="DAY2_C1", pan_number="555111222")
            db.add(comp1)
            db.commit()
            db.refresh(comp1)

        # Tenant Company 2
        comp2 = db.query(Company).filter(Company.code == "DAY2_C2").first()
        if not comp2:
            comp2 = Company(name="Day 2 Corp Rival", code="DAY2_C2", pan_number="555333444")
            db.add(comp2)
            db.commit()
            db.refresh(comp2)

        # C1 Admin
        u_admin = db.query(User).filter(User.username == "d2_admin").first()
        if not u_admin:
            u_admin = User(
                name="Day2 Admin",
                username="d2_admin",
                email="admin@d2.com",
                company_id=comp1.id,
                role="admin",
                active=True,
                password_hash=get_password_hash("AdminPass123!")
            )
            db.add(u_admin)
            db.commit()
            db.refresh(u_admin)

        # C1 Manager
        u_mgr = db.query(User).filter(User.username == "d2_mgr").first()
        if not u_mgr:
            u_mgr = User(
                name="Day2 Manager",
                username="d2_mgr",
                email="mgr@d2.com",
                company_id=comp1.id,
                role="manager",
                active=True,
                password_hash=get_password_hash("MgrPass123!")
            )
            db.add(u_mgr)
            db.commit()
            db.refresh(u_mgr)

        # C1 Editor
        u_editor = db.query(User).filter(User.username == "d2_editor").first()
        if not u_editor:
            u_editor = User(
                name="Day2 Editor",
                username="d2_editor",
                email="editor@d2.com",
                company_id=comp1.id,
                role="editor",
                active=True,
                password_hash=get_password_hash("EditorPass123!")
            )
            db.add(u_editor)
            db.commit()
            db.refresh(u_editor)

        # C1 Viewer
        u_viewer = db.query(User).filter(User.username == "d2_viewer").first()
        if not u_viewer:
            u_viewer = User(
                name="Day2 Viewer",
                username="d2_viewer",
                email="viewer@d2.com",
                company_id=comp1.id,
                role="viewer",
                active=True,
                password_hash=get_password_hash("ViewerPass123!")
            )
            db.add(u_viewer)
            db.commit()
            db.refresh(u_viewer)

        # C2 Admin
        u_c2_admin = db.query(User).filter(User.username == "d2_c2_admin").first()
        if not u_c2_admin:
            u_c2_admin = User(
                name="Day2 C2 Admin",
                username="d2_c2_admin",
                email="c2admin@d2.com",
                company_id=comp2.id,
                role="admin",
                active=True,
                password_hash=get_password_hash("C2AdminPass123!")
            )
            db.add(u_c2_admin)
            db.commit()
            db.refresh(u_c2_admin)

        # Fixture Worker in C1
        worker = db.query(Worker).filter(Worker.company_id == comp1.id, Worker.worker_code == "W-D2-001").first()
        if not worker:
            worker = Worker(
                company_id=comp1.id,
                worker_code="W-D2-001",
                name="Hari Bahadur",
                pay_type="SALARY",
                basic_rate_paisa=4500000,
                is_active=True
            )
            db.add(worker)
            db.commit()
            db.refresh(worker)

            from app.models.worker import WorkerAdvance
            adv = WorkerAdvance(
                company_id=comp1.id,
                worker_id=worker.id,
                amount_paisa=500000,
                entry_type="ISSUED",
                actor_id=u_admin.id
            )
            db.add(adv)
            db.commit()
            db.refresh(worker)

        # Fixture Fixed Asset in C1
        asset_c1 = db.query(FixedAsset).filter(FixedAsset.company_id == comp1.id, FixedAsset.asset_code == "FA-D2-C1").first()
        if not asset_c1:
            asset_c1 = FixedAsset(
                company_id=comp1.id,
                asset_code="FA-D2-C1",
                asset_name="Hydraulic Sole Press",
                category="MACHINERY",
                purchase_date_ad=date(2026, 3, 1),
                purchase_date_bs="2082-11-17",
                purchase_cost_paisa=120000000,
                quantity=1,
                actor_id=u_admin.id
            )
            db.add(asset_c1)
            db.commit()
            db.refresh(asset_c1)

        # Fixture Fixed Asset in C2
        asset_c2 = db.query(FixedAsset).filter(FixedAsset.company_id == comp2.id, FixedAsset.asset_code == "FA-D2-C2").first()
        if not asset_c2:
            asset_c2 = FixedAsset(
                company_id=comp2.id,
                asset_code="FA-D2-C2",
                asset_name="Rival Sole Press",
                category="MACHINERY",
                purchase_date_ad=date(2026, 3, 1),
                purchase_date_bs="2082-11-17",
                purchase_cost_paisa=80000000,
                quantity=1,
                actor_id=u_c2_admin.id
            )
            db.add(asset_c2)
            db.commit()
            db.refresh(asset_c2)

        # Fixture BOM Item in C1
        prod = db.query(Product).filter(Product.company_id == comp1.id, Product.code == "PROD-D2-01").first()
        if not prod:
            prod = Product(
                company_id=comp1.id,
                code="PROD-D2-01",
                name="Security Boot Leather",
                unit_price=Decimal("3500.00")
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)

        rm = db.query(RawMaterial).filter(RawMaterial.company_id == comp1.id, RawMaterial.code == "RM-D2-01").first()
        if not rm:
            rm = RawMaterial(
                company_id=comp1.id,
                code="RM-D2-01",
                name="Full Grain Leather Sheet",
                unit="kg"
            )
            db.add(rm)
            db.commit()
            db.refresh(rm)

        bom = db.query(BillOfMaterials).filter(BillOfMaterials.company_id == comp1.id, BillOfMaterials.product_id == prod.id).first()
        if not bom:
            bom = BillOfMaterials(
                company_id=comp1.id,
                product_id=prod.id,
                raw_material_id=rm.id,
                quantity_required=Decimal("2.5")
            )
            db.add(bom)
            db.commit()
            db.refresh(bom)

        # Fixture Sales Expense in C1
        expense = db.query(SalesExpense).filter(SalesExpense.company_id == comp1.id, SalesExpense.particular == "D2 Sales Lunch").first()
        if not expense:
            expense = SalesExpense(
                company_id=comp1.id,
                particular="D2 Sales Lunch",
                category="DELIVERY_FREIGHT",
                amount_paisa=350000,
                expense_date_ad=date(2026, 3, 15),
                expense_date_bs="2082-12-01",
                payment_method="CASH",
                actor_id=u_admin.id
            )
            db.add(expense)
            db.commit()
            db.refresh(expense)

        yield {
            "comp1": comp1,
            "comp2": comp2,
            "u_admin": u_admin,
            "u_mgr": u_mgr,
            "u_editor": u_editor,
            "u_viewer": u_viewer,
            "u_c2_admin": u_c2_admin,
            "worker": worker,
            "asset_c1": asset_c1,
            "asset_c2": asset_c2,
            "bom": bom,
            "expense": expense,
        }
    finally:
        db.close()


def make_auth(user: User) -> dict:
    token = create_access_token({
        "user_id": user.id,
        "company_id": user.company_id,
        "role": user.role
    })
    return {"Authorization": f"Bearer {token}"}


class TestDay2RBACAndAuthorizationHardening:
    """Rigorous tests covering Day 2 authorization forensics, matrix enforcement, and regressions."""

    def test_unauthenticated_request_rejected(self):
        client = TestClient(app)
        res = client.get("/api/v1/auth/users")
        assert res.status_code == 401

    def test_admin_self_deactivation_prevented(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)
        headers = make_auth(f["u_admin"])

        payload = {"active": False}
        res = client.patch(f"/api/v1/auth/users/{f['u_admin'].id}", json=payload, headers=headers)
        assert res.status_code == 400
        assert "Administrators cannot deactivate their own account" in res.json()["detail"]

    def test_admin_self_demotion_prevented(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)
        headers = make_auth(f["u_admin"])

        payload = {"role": "viewer"}
        res = client.patch(f"/api/v1/auth/users/{f['u_admin'].id}", json=payload, headers=headers)
        assert res.status_code == 400
        assert "Administrators cannot demote their own account" in res.json()["detail"]

    def test_admin_can_update_other_user_role(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)
        headers = make_auth(f["u_admin"])

        # Promoting viewer to manager
        payload = {"role": "manager"}
        res = client.patch(f"/api/v1/auth/users/{f['u_viewer'].id}", json=payload, headers=headers)
        assert res.status_code == 200
        assert res.json()["role"] == "manager"

        # Revert back to viewer
        payload = {"role": "viewer"}
        res = client.patch(f"/api/v1/auth/users/{f['u_viewer'].id}", json=payload, headers=headers)
        assert res.status_code == 200
        assert res.json()["role"] == "viewer"

    def test_non_admin_cannot_access_user_management(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # Editor
        res = client.get("/api/v1/auth/users", headers=make_auth(f["u_editor"]))
        assert res.status_code == 403

        # Viewer
        res = client.get("/api/v1/auth/users", headers=make_auth(f["u_viewer"]))
        assert res.status_code == 403

    def test_invalid_role_assignment_rejected(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)
        headers = make_auth(f["u_admin"])

        payload = {"role": "superuser"}
        res = client.patch(f"/api/v1/auth/users/{f['u_editor'].id}", json=payload, headers=headers)
        assert res.status_code == 422  # Pydantic regex validation failure

    def test_viewer_compensation_redaction_on_workers_list(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # 1. Admin reads workers -> full salary & advance exposed
        res_admin = client.get("/api/v1/hr/workers", headers=make_auth(f["u_admin"]))
        assert res_admin.status_code == 200
        w_admin = next(w for w in res_admin.json() if w["id"] == f["worker"].id)
        assert w_admin["basic_rate_paisa"] == 4500000
        assert w_admin["outstanding_advance_paisa"] == 500000

        # 2. Viewer reads workers -> sensitive compensation fields are strictly absent
        res_viewer = client.get("/api/v1/hr/workers", headers=make_auth(f["u_viewer"]))
        assert res_viewer.status_code == 200
        w_viewer = next(w for w in res_viewer.json() if w["id"] == f["worker"].id)
        assert "basic_rate_paisa" not in w_viewer
        assert "outstanding_advance_paisa" not in w_viewer
        assert "overtime_rate_paisa_override" not in w_viewer
        if w_viewer.get("current_month"):
            assert "gross_pay_paisa" not in w_viewer["current_month"]
            assert "advance_deduction_paisa" not in w_viewer["current_month"]
            assert "net_paid_paisa" not in w_viewer["current_month"]

    def test_viewer_blocked_from_worker_financial_history(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # Viewer forbidden
        res_viewer = client.get(f"/api/v1/hr/workers/{f['worker'].id}/history", headers=make_auth(f["u_viewer"]))
        assert res_viewer.status_code == 403

        # Editor allowed
        res_editor = client.get(f"/api/v1/hr/workers/{f['worker'].id}/history", headers=make_auth(f["u_editor"]))
        assert res_editor.status_code == 200
        assert res_editor.json()["worker"]["id"] == f["worker"].id

    def test_fixed_asset_deletion_restricted_to_admin(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # 1. Viewer attempt -> 403
        res = client.delete(f"/api/v1/fixed-assets/{f['asset_c1'].id}", headers=make_auth(f["u_viewer"]))
        assert res.status_code == 403

        # 2. Editor attempt -> 403
        res = client.delete(f"/api/v1/fixed-assets/{f['asset_c1'].id}", headers=make_auth(f["u_editor"]))
        assert res.status_code == 403

        # 3. Cross-company Admin attempt -> 404 (strictly tenant isolated)
        res = client.delete(f"/api/v1/fixed-assets/{f['asset_c1'].id}", headers=make_auth(f["u_c2_admin"]))
        assert res.status_code == 404

        # 4. Same-tenant Admin attempt -> 200 (allowed)
        res = client.delete(f"/api/v1/fixed-assets/{f['asset_c1'].id}", headers=make_auth(f["u_admin"]))
        assert res.status_code == 200
        assert res.json()["id"] == f["asset_c1"].id

    def test_bom_item_deletion_restricted_to_admin(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # 1. Viewer attempt -> 403
        res = client.delete(f"/api/v1/production/bom/{f['bom'].id}", headers=make_auth(f["u_viewer"]))
        assert res.status_code == 403

        # 2. Editor attempt -> 403
        res = client.delete(f"/api/v1/production/bom/{f['bom'].id}", headers=make_auth(f["u_editor"]))
        assert res.status_code == 403

        # 3. Admin attempt -> 200 (allowed)
        res = client.delete(f"/api/v1/production/bom/{f['bom'].id}", headers=make_auth(f["u_admin"]))
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"

    def test_sales_expense_deletion_restricted_to_admin(self, setup_day_2_fixtures):
        f = setup_day_2_fixtures
        client = TestClient(app)

        # 1. Viewer attempt -> 403
        res = client.delete(f"/api/v1/sales/expenses/{f['expense'].id}", headers=make_auth(f["u_viewer"]))
        assert res.status_code == 403

        # 2. Editor attempt -> 403
        res = client.delete(f"/api/v1/sales/expenses/{f['expense'].id}", headers=make_auth(f["u_editor"]))
        assert res.status_code == 403

        # 3. Admin attempt -> 200 (allowed)
        res = client.delete(f"/api/v1/sales/expenses/{f['expense'].id}", headers=make_auth(f["u_admin"]))
        assert res.status_code == 200
        assert res.json()["id"] == f["expense"].id
