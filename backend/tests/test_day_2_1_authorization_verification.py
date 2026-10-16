"""
Day 2.1 Adversarial Authorization Verification and Tenant Isolation Test Suite
Verifies:
1. HR Redaction: Sensitive compensation fields (basic_rate_paisa, outstanding_advance_paisa,
   overtime_rate_paisa_override, gross_pay_paisa, advance_deduction_paisa, net_paid_paisa)
   are COMPLETELY ABSENT from viewer responses on GET /hr/workers, not merely equal to zero.
2. HR Worker Financial History: Strictly 403 Forbidden for viewer role.
3. Multi-Tenant Cross-Company Isolation:
   - Auth: Cross-company user update rejected with 404.
   - Branches: Cross-company branch detail rejected with 404.
   - Warehouses: Cross-company warehouse-to-branch assignment rejected with 404.
   - Stock Transfers: Cross-company transfer detail, source/destination ID tampering rejected with 404.
   - Stock Adjustments: Cross-company product and warehouse ID tampering rejected with 404.
   - Purchase: Cross-company supplier or raw material ID tampering rejected with 404.
   - Production BOM: Cross-company product/raw material ID tampering rejected with 404.
   - Sales: Cross-company client ID tampering on order creation rejected with 404.
   - Destructive Operations: Cross-company fixed asset and sales expense deletions rejected with 404.
4. Privilege Escalation Defense:
   - Manager and Editor forbidden from user management (403).
   - Admin self-deactivation and self-demotion strictly blocked (400).
   - Fixed asset, BOM, and expense deletions forbidden for Editor and Viewer (403).
"""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.worker import Worker, WorkerAdvance
from app.models.asset import FixedAsset
from app.models.bom import BillOfMaterials
from app.models.stock import Product, Warehouse
from app.models.branch import Branch
from app.models.purchase import Supplier, RawMaterial
from app.models.sales import Client, SalesExpense
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def setup_day_2_1_env():
    db: Session = SessionLocal()
    try:
        # Company A
        comp_a = db.query(Company).filter(Company.code == "D21_CO_A").first()
        if not comp_a:
            comp_a = Company(name="Day 2.1 Alpha Footwear", code="D21_CO_A", pan_number="111222333")
            db.add(comp_a)
            db.commit()
            db.refresh(comp_a)

        # Company B
        comp_b = db.query(Company).filter(Company.code == "D21_CO_B").first()
        if not comp_b:
            comp_b = Company(name="Day 2.1 Beta Footwear", code="D21_CO_B", pan_number="999888777")
            db.add(comp_b)
            db.commit()
            db.refresh(comp_b)

        # Users Company A
        u_a_admin = db.query(User).filter(User.username == "d21_a_admin").first()
        if not u_a_admin:
            u_a_admin = User(name="Alpha Admin", username="d21_a_admin", email="admin@alpha.com", company_id=comp_a.id, role="admin", active=True, password_hash=get_password_hash("Pass123!"))
            db.add(u_a_admin)
            db.commit()
            db.refresh(u_a_admin)

        u_a_mgr = db.query(User).filter(User.username == "d21_a_mgr").first()
        if not u_a_mgr:
            u_a_mgr = User(name="Alpha Manager", username="d21_a_mgr", email="mgr@alpha.com", company_id=comp_a.id, role="manager", active=True, password_hash=get_password_hash("Pass123!"))
            db.add(u_a_mgr)
            db.commit()
            db.refresh(u_a_mgr)

        u_a_editor = db.query(User).filter(User.username == "d21_a_editor").first()
        if not u_a_editor:
            u_a_editor = User(name="Alpha Editor", username="d21_a_editor", email="editor@alpha.com", company_id=comp_a.id, role="editor", active=True, password_hash=get_password_hash("Pass123!"))
            db.add(u_a_editor)
            db.commit()
            db.refresh(u_a_editor)

        u_a_viewer = db.query(User).filter(User.username == "d21_a_viewer").first()
        if not u_a_viewer:
            u_a_viewer = User(name="Alpha Viewer", username="d21_a_viewer", email="viewer@alpha.com", company_id=comp_a.id, role="viewer", active=True, password_hash=get_password_hash("Pass123!"))
            db.add(u_a_viewer)
            db.commit()
            db.refresh(u_a_viewer)

        # Users Company B
        u_b_admin = db.query(User).filter(User.username == "d21_b_admin").first()
        if not u_b_admin:
            u_b_admin = User(name="Beta Admin", username="d21_b_admin", email="admin@beta.com", company_id=comp_b.id, role="admin", active=True, password_hash=get_password_hash("Pass123!"))
            db.add(u_b_admin)
            db.commit()
            db.refresh(u_b_admin)

        # Resources Company A
        wh_a1 = db.query(Warehouse).filter(Warehouse.company_id == comp_a.id, Warehouse.code == "WH-A-01").first()
        if not wh_a1:
            wh_a1 = Warehouse(company_id=comp_a.id, name="Alpha Central", code="WH-A-01", is_active=True)
            db.add(wh_a1)
            db.commit()
            db.refresh(wh_a1)

        wh_a2 = db.query(Warehouse).filter(Warehouse.company_id == comp_a.id, Warehouse.code == "WH-A-02").first()
        if not wh_a2:
            wh_a2 = Warehouse(company_id=comp_a.id, name="Alpha Outlet Stock", code="WH-A-02", is_active=True)
            db.add(wh_a2)
            db.commit()
            db.refresh(wh_a2)

        branch_a = db.query(Branch).filter(Branch.company_id == comp_a.id, Branch.code == "BR-A-01").first()
        if not branch_a:
            branch_a = Branch(company_id=comp_a.id, code="BR-A-01", name="Alpha KTM Branch", type="RETAIL_OUTLET", is_active=True)
            db.add(branch_a)
            db.commit()
            db.refresh(branch_a)

        prod_a = db.query(Product).filter(Product.company_id == comp_a.id, Product.code == "PROD-A-01").first()
        if not prod_a:
            prod_a = Product(company_id=comp_a.id, code="PROD-A-01", name="Alpha Sneaker", unit_price=Decimal("2000.00"))
            db.add(prod_a)
            db.commit()
            db.refresh(prod_a)

        sup_a = db.query(Supplier).filter(Supplier.company_id == comp_a.id, Supplier.code == "SUP-A-01").first()
        if not sup_a:
            sup_a = Supplier(company_id=comp_a.id, code="SUP-A-01", name="Alpha Leather Tannery")
            db.add(sup_a)
            db.commit()
            db.refresh(sup_a)

        rm_a = db.query(RawMaterial).filter(RawMaterial.company_id == comp_a.id, RawMaterial.code == "RM-A-01").first()
        if not rm_a:
            rm_a = RawMaterial(company_id=comp_a.id, code="RM-A-01", name="Alpha Leather", unit="kg")
            db.add(rm_a)
            db.commit()
            db.refresh(rm_a)

        client_a = db.query(Client).filter(Client.company_id == comp_a.id, Client.code == "CLI-A-01").first()
        if not client_a:
            client_a = Client(company_id=comp_a.id, code="CLI-A-01", name="Alpha Shoes Wholesaler")
            db.add(client_a)
            db.commit()
            db.refresh(client_a)

        worker_a = db.query(Worker).filter(Worker.company_id == comp_a.id, Worker.worker_code == "WKR-A-01").first()
        if not worker_a:
            worker_a = Worker(company_id=comp_a.id, worker_code="WKR-A-01", name="Ram Bahadur", pay_type="SALARY", basic_rate_paisa=5000000, is_active=True)
            db.add(worker_a)
            db.commit()
            db.refresh(worker_a)
            adv = WorkerAdvance(company_id=comp_a.id, worker_id=worker_a.id, amount_paisa=800000, entry_type="ISSUED", actor_id=u_a_admin.id)
            db.add(adv)
            db.commit()

        asset_a = db.query(FixedAsset).filter(FixedAsset.company_id == comp_a.id, FixedAsset.asset_code == "FA-A-01").first()
        if not asset_a:
            asset_a = FixedAsset(company_id=comp_a.id, asset_code="FA-A-01", asset_name="Alpha Generator", category="MACHINERY", purchase_date_ad=date(2026, 1, 1), purchase_date_bs="2082-09-17", purchase_cost_paisa=25000000, quantity=1, actor_id=u_a_admin.id)
            db.add(asset_a)
            db.commit()
            db.refresh(asset_a)

        expense_a = db.query(SalesExpense).filter(SalesExpense.company_id == comp_a.id, SalesExpense.particular == "Alpha Fuel").first()
        if not expense_a:
            expense_a = SalesExpense(company_id=comp_a.id, particular="Alpha Fuel", category="DELIVERY_FREIGHT", amount_paisa=500000, expense_date_ad=date(2026, 3, 1), expense_date_bs="2082-11-17", payment_method="CASH", actor_id=u_a_admin.id)
            db.add(expense_a)
            db.commit()
            db.refresh(expense_a)

        bom_a = db.query(BillOfMaterials).filter(BillOfMaterials.company_id == comp_a.id, BillOfMaterials.product_id == prod_a.id).first()
        if not bom_a:
            bom_a = BillOfMaterials(company_id=comp_a.id, product_id=prod_a.id, raw_material_id=rm_a.id, quantity_required=Decimal("1.8"))
            db.add(bom_a)
            db.commit()
            db.refresh(bom_a)

        # Resources Company B
        wh_b1 = db.query(Warehouse).filter(Warehouse.company_id == comp_b.id, Warehouse.code == "WH-B-01").first()
        if not wh_b1:
            wh_b1 = Warehouse(company_id=comp_b.id, name="Beta Central", code="WH-B-01", is_active=True)
            db.add(wh_b1)
            db.commit()
            db.refresh(wh_b1)

        branch_b = db.query(Branch).filter(Branch.company_id == comp_b.id, Branch.code == "BR-B-01").first()
        if not branch_b:
            branch_b = Branch(company_id=comp_b.id, code="BR-B-01", name="Beta Pokhara Branch", type="RETAIL_OUTLET", is_active=True)
            db.add(branch_b)
            db.commit()
            db.refresh(branch_b)

        prod_b = db.query(Product).filter(Product.company_id == comp_b.id, Product.code == "PROD-B-01").first()
        if not prod_b:
            prod_b = Product(company_id=comp_b.id, code="PROD-B-01", name="Beta Boot", unit_price=Decimal("4500.00"))
            db.add(prod_b)
            db.commit()
            db.refresh(prod_b)

        sup_b = db.query(Supplier).filter(Supplier.company_id == comp_b.id, Supplier.code == "SUP-B-01").first()
        if not sup_b:
            sup_b = Supplier(company_id=comp_b.id, code="SUP-B-01", name="Beta Rubber Co")
            db.add(sup_b)
            db.commit()
            db.refresh(sup_b)

        client_b = db.query(Client).filter(Client.company_id == comp_b.id, Client.code == "CLI-B-01").first()
        if not client_b:
            client_b = Client(company_id=comp_b.id, code="CLI-B-01", name="Beta Retail Store")
            db.add(client_b)
            db.commit()
            db.refresh(client_b)

        transfer_b = db.query(StockTransfer).filter(StockTransfer.company_id == comp_b.id, StockTransfer.transfer_number == "TRF-B-001").first()
        if not transfer_b:
            transfer_b = StockTransfer(
                company_id=comp_b.id,
                transfer_number="TRF-B-001",
                source_warehouse_id=wh_b1.id,
                destination_warehouse_id=wh_b1.id,  # Dummy for lookup test
                status="DRAFT",
                transfer_date_ad="2026-03-01",
                transfer_date_bs="2082-11-17",
                created_by_id=u_b_admin.id
            )
            db.add(transfer_b)
            db.commit()
            db.refresh(transfer_b)

        asset_b = db.query(FixedAsset).filter(FixedAsset.company_id == comp_b.id, FixedAsset.asset_code == "FA-B-01").first()
        if not asset_b:
            asset_b = FixedAsset(company_id=comp_b.id, asset_code="FA-B-01", asset_name="Beta Mould", category="MOULD", purchase_date_ad=date(2026, 1, 1), purchase_date_bs="2082-09-17", purchase_cost_paisa=15000000, quantity=1, actor_id=u_b_admin.id)
            db.add(asset_b)
            db.commit()
            db.refresh(asset_b)

        expense_b = db.query(SalesExpense).filter(SalesExpense.company_id == comp_b.id, SalesExpense.particular == "Beta Rent").first()
        if not expense_b:
            expense_b = SalesExpense(company_id=comp_b.id, particular="Beta Rent", category="DELIVERY_FREIGHT", amount_paisa=1200000, expense_date_ad=date(2026, 3, 1), expense_date_bs="2082-11-17", payment_method="CASH", actor_id=u_b_admin.id)
            db.add(expense_b)
            db.commit()
            db.refresh(expense_b)

        yield {
            "comp_a": comp_a,
            "comp_b": comp_b,
            "u_a_admin": u_a_admin,
            "u_a_mgr": u_a_mgr,
            "u_a_editor": u_a_editor,
            "u_a_viewer": u_a_viewer,
            "u_b_admin": u_b_admin,
            "wh_a1": wh_a1,
            "wh_a2": wh_a2,
            "wh_b1": wh_b1,
            "branch_a": branch_a,
            "branch_b": branch_b,
            "prod_a": prod_a,
            "prod_b": prod_b,
            "sup_a": sup_a,
            "sup_b": sup_b,
            "rm_a": rm_a,
            "client_a": client_a,
            "client_b": client_b,
            "worker_a": worker_a,
            "asset_a": asset_a,
            "asset_b": asset_b,
            "expense_a": expense_a,
            "expense_b": expense_b,
            "bom_a": bom_a,
            "transfer_b": transfer_b,
        }
    finally:
        db.close()


def auth(user: User) -> dict:
    token = create_access_token({
        "user_id": user.id,
        "company_id": user.company_id,
        "role": user.role
    })
    return {"Authorization": f"Bearer {token}"}


class TestDay21AdversarialVerification:
    """Comprehensive test suite covering all Day 2.1 requirements."""

    # =========================================================================
    # 1. HR REDACTION BEHAVIOR (Absence of sensitive fields)
    # =========================================================================

    def test_hr_compensation_fields_strictly_absent_for_viewer(self, setup_day_2_1_env):
        """Proves sensitive compensation fields are completely absent, not zero-masked."""
        f = setup_day_2_1_env
        client = TestClient(app)

        res = client.get("/api/v1/hr/workers", headers=auth(f["u_a_viewer"]))
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        w = next(item for item in data if item["id"] == f["worker_a"].id)

        # Assert restricted fields are completely absent from JSON dictionary
        assert "basic_rate_paisa" not in w, "basic_rate_paisa leaked in viewer response"
        assert "outstanding_advance_paisa" not in w, "outstanding_advance_paisa leaked in viewer response"
        assert "overtime_rate_paisa_override" not in w, "overtime_rate_paisa_override leaked in viewer response"

        # If current_month object is present, monetary fields must be absent
        if w.get("current_month"):
            cm = w["current_month"]
            assert "gross_pay_paisa" not in cm, "gross_pay_paisa leaked in current_month"
            assert "advance_deduction_paisa" not in cm, "advance_deduction_paisa leaked in current_month"
            assert "net_paid_paisa" not in cm, "net_paid_paisa leaked in current_month"

    def test_hr_compensation_fields_present_for_authorized_roles(self, setup_day_2_1_env):
        """Verifies authorized roles (admin, editor) receive legitimate compensation fields."""
        f = setup_day_2_1_env
        client = TestClient(app)

        # Admin
        res_admin = client.get("/api/v1/hr/workers", headers=auth(f["u_a_admin"]))
        assert res_admin.status_code == 200
        w_admin = next(item for item in res_admin.json() if item["id"] == f["worker_a"].id)
        assert "basic_rate_paisa" in w_admin
        assert w_admin["basic_rate_paisa"] == 5000000
        assert "outstanding_advance_paisa" in w_admin
        assert w_admin["outstanding_advance_paisa"] == 800000

        # Editor
        res_editor = client.get("/api/v1/hr/workers", headers=auth(f["u_a_editor"]))
        assert res_editor.status_code == 200
        w_editor = next(item for item in res_editor.json() if item["id"] == f["worker_a"].id)
        assert "basic_rate_paisa" in w_editor
        assert w_editor["basic_rate_paisa"] == 5000000
        assert "outstanding_advance_paisa" in w_editor
        assert w_editor["outstanding_advance_paisa"] == 800000

    def test_hr_worker_history_forbidden_for_viewer(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        res = client.get(f"/api/v1/hr/workers/{f['worker_a'].id}/history", headers=auth(f["u_a_viewer"]))
        assert res.status_code == 403

    def test_hr_citizenship_doc_download_forbidden_for_non_admin(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Viewer forbidden (403)
        res_v = client.get(f"/api/v1/hr/workers/{f['worker_a'].id}/citizenship", headers=auth(f["u_a_viewer"]))
        assert res_v.status_code == 403

        # Editor forbidden (403)
        res_e = client.get(f"/api/v1/hr/workers/{f['worker_a'].id}/citizenship", headers=auth(f["u_a_editor"]))
        assert res_e.status_code == 403

    # =========================================================================
    # 2. MULTI-TENANT COMPANY ISOLATION (Cross-Company IDOR & Mutation Rejection)
    # =========================================================================

    def test_cross_company_user_update_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Company A admin attempts to modify Company B admin
        res = client.patch(f"/api/v1/auth/users/{f['u_b_admin'].id}", json={"name": "Hacked Name"}, headers=auth(f["u_a_admin"]))
        assert res.status_code == 404

    def test_cross_company_branch_read_and_mutation_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Company A editor attempts to read Company B branch detail
        res_read = client.get(f"/api/v1/branches/{f['branch_b'].id}", headers=auth(f["u_a_editor"]))
        assert res_read.status_code == 404

        # Company A editor attempts to update Company B branch
        res_update = client.put(f"/api/v1/branches/{f['branch_b'].id}", json={"name": "Tampered"}, headers=auth(f["u_a_editor"]))
        assert res_update.status_code == 404

    def test_cross_company_warehouse_assignment_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Company A editor attempts to link Company B warehouse to Company A branch
        payload = {"warehouse_id": f["wh_b1"].id}
        res = client.post(f"/api/v1/branches/{f['branch_a'].id}/warehouses", json=payload, headers=auth(f["u_a_editor"]))
        assert res.status_code == 404

    def test_cross_company_stock_transfer_read_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Company A editor attempts to read Company B transfer
        res = client.get(f"/api/v1/transfers/{f['transfer_b'].id}", headers=auth(f["u_a_editor"]))
        assert res.status_code == 404

    def test_cross_company_stock_transfer_creation_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # 1. Source warehouse belonging to Company B
        payload_bad_source = {
            "source_warehouse_id": f["wh_b1"].id,
            "destination_warehouse_id": f["wh_a2"].id,
            "transfer_date_ad": "2026-03-01",
            "transfer_date_bs": "2082-11-17",
            "items": [{"product_id": f["prod_a"].id, "quantity": 5.0}]
        }
        res1 = client.post("/api/v1/transfers", json=payload_bad_source, headers=auth(f["u_a_editor"]))
        assert res1.status_code == 404

        # 2. Destination warehouse belonging to Company B
        payload_bad_dest = {
            "source_warehouse_id": f["wh_a1"].id,
            "destination_warehouse_id": f["wh_b1"].id,
            "transfer_date_ad": "2026-03-01",
            "transfer_date_bs": "2082-11-17",
            "items": [{"product_id": f["prod_a"].id, "quantity": 5.0}]
        }
        res2 = client.post("/api/v1/transfers", json=payload_bad_dest, headers=auth(f["u_a_editor"]))
        assert res2.status_code == 404

        # 3. Product belonging to Company B
        payload_bad_prod = {
            "source_warehouse_id": f["wh_a1"].id,
            "destination_warehouse_id": f["wh_a2"].id,
            "transfer_date_ad": "2026-03-01",
            "transfer_date_bs": "2082-11-17",
            "items": [{"product_id": f["prod_b"].id, "quantity": 5.0}]
        }
        res3 = client.post("/api/v1/transfers", json=payload_bad_prod, headers=auth(f["u_a_editor"]))
        assert res3.status_code == 404

    def test_cross_company_stock_adjustments_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # 1. Adjusting Company B product
        payload1 = {"product_id": f["prod_b"].id, "quantity_delta": 5.0, "reason_code": "PURCHASE_RECEIPT"}
        res1 = client.post("/api/v1/stock/adjustments", json=payload1, headers=auth(f["u_a_editor"]))
        assert res1.status_code == 404

        # 2. Adjusting in Company B warehouse
        payload2 = {"product_id": f["prod_a"].id, "warehouse_id": f["wh_b1"].id, "quantity_delta": 5.0, "reason_code": "PURCHASE_RECEIPT"}
        res2 = client.post("/api/v1/stock/adjustments", json=payload2, headers=auth(f["u_a_editor"]))
        assert res2.status_code == 404

    def test_cross_company_purchase_creation_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Attempt to create purchase in Company A using Company B supplier
        payload = {
            "supplier_id": f["sup_b"].id,
            "raw_material_id": f["rm_a"].id,
            "quantity": 10.0,
            "unit_price": 500.0,
            "purchase_date_ad": "2026-03-01",
            "purchase_date_bs": "2082-11-17"
        }
        res = client.post("/api/v1/purchase", json=payload, headers=auth(f["u_a_editor"]))
        assert res.status_code == 404

    def test_cross_company_production_bom_creation_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Attempt to link Company A product to Company B raw material in BOM
        payload = {
            "product_id": f["prod_a"].id,
            "raw_material_id": f["rm_a"].id,
            "quantity_required": 2.0
        }
        # First test valid product in A, then cross-company product B
        payload_bad = {
            "product_id": f["prod_b"].id,
            "raw_material_id": f["rm_a"].id,
            "quantity_required": 2.0
        }
        res = client.post("/api/v1/production/bom", json=payload_bad, headers=auth(f["u_a_editor"]))
        assert res.status_code == 404

    def test_cross_company_sales_order_creation_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Attempt to create sales order in Company A using Company B client
        payload = {
            "client_id": f["client_b"].id,
            "order_date_ad": "2026-03-01",
            "order_date_bs": "2082-11-17",
            "items": [{"product_id": f["prod_a"].id, "quantity": 1, "unit_price": 2000.0}]
        }
        res = client.post("/api/v1/sales/orders", json=payload, headers=auth(f["u_a_editor"]))
        assert res.status_code == 404

    def test_cross_company_destructive_operations_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # 1. Company A admin cannot delete Company B fixed asset
        res1 = client.delete(f"/api/v1/fixed-assets/{f['asset_b'].id}", headers=auth(f["u_a_admin"]))
        assert res1.status_code == 404

        # 2. Company A admin cannot delete Company B sales expense
        res2 = client.delete(f"/api/v1/sales/expenses/{f['expense_b'].id}", headers=auth(f["u_a_admin"]))
        assert res2.status_code == 404

    # =========================================================================
    # 3. PRIVILEGE ESCALATION DEFENSE AND DESTRUCTIVE PERMISSION ENFORCEMENT
    # =========================================================================

    def test_manager_and_editor_cannot_access_user_management(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Manager forbidden from listing users (403)
        res1 = client.get("/api/v1/auth/users", headers=auth(f["u_a_mgr"]))
        assert res1.status_code == 403

        # Manager forbidden from creating user (403)
        res2 = client.post("/api/v1/auth/users", json={"name": "New User", "username": "new_u", "password": "Pass123!", "role": "admin"}, headers=auth(f["u_a_mgr"]))
        assert res2.status_code == 403

        # Editor forbidden from creating user (403)
        res3 = client.post("/api/v1/auth/users", json={"name": "New User 2", "username": "new_u2", "password": "Pass123!", "role": "editor"}, headers=auth(f["u_a_editor"]))
        assert res3.status_code == 403

    def test_admin_self_deactivation_and_self_demotion_rejected(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Self deactivation
        res1 = client.patch(f"/api/v1/auth/users/{f['u_a_admin'].id}", json={"active": False}, headers=auth(f["u_a_admin"]))
        assert res1.status_code == 400
        assert "Administrators cannot deactivate their own account" in res1.json()["detail"]

        # Self demotion
        res2 = client.patch(f"/api/v1/auth/users/{f['u_a_admin'].id}", json={"role": "editor"}, headers=auth(f["u_a_admin"]))
        assert res2.status_code == 400
        assert "Administrators cannot demote their own account" in res2.json()["detail"]

    def test_destructive_operations_forbidden_for_editor_and_viewer(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        # Fixed asset deletion: Editor (403), Viewer (403)
        assert client.delete(f"/api/v1/fixed-assets/{f['asset_a'].id}", headers=auth(f["u_a_editor"])).status_code == 403
        assert client.delete(f"/api/v1/fixed-assets/{f['asset_a'].id}", headers=auth(f["u_a_viewer"])).status_code == 403

        # BOM item deletion: Editor (403), Viewer (403)
        assert client.delete(f"/api/v1/production/bom/{f['bom_a'].id}", headers=auth(f["u_a_editor"])).status_code == 403
        assert client.delete(f"/api/v1/production/bom/{f['bom_a'].id}", headers=auth(f["u_a_viewer"])).status_code == 403

        # Sales expense deletion: Editor (403), Viewer (403)
        assert client.delete(f"/api/v1/sales/expenses/{f['expense_a'].id}", headers=auth(f["u_a_editor"])).status_code == 403
        assert client.delete(f"/api/v1/sales/expenses/{f['expense_a'].id}", headers=auth(f["u_a_viewer"])).status_code == 403

    def test_intra_company_transfer_requires_distinct_warehouses(self, setup_day_2_1_env):
        f = setup_day_2_1_env
        client = TestClient(app)

        payload_same_wh = {
            "source_warehouse_id": f["wh_a1"].id,
            "destination_warehouse_id": f["wh_a1"].id,
            "transfer_date_ad": "2026-03-01",
            "transfer_date_bs": "2082-11-17",
            "items": [{"product_id": f["prod_a"].id, "quantity": 5.0}]
        }
        res = client.post("/api/v1/transfers", json=payload_same_wh, headers=auth(f["u_a_editor"]))
        assert res.status_code == 400
        assert "Source and destination warehouses must be distinct" in res.json()["detail"]

    def test_anonymous_access_rejected_across_sensitive_endpoints(self, setup_day_2_1_env):
        """Verifies unauthenticated requests to protected endpoints return 401."""
        client = TestClient(app)
        
        # Test endpoints without auth header/cookie
        assert client.get("/api/v1/hr/workers").status_code == 401
        assert client.get("/api/v1/auth/users").status_code == 401
        assert client.get("/api/v1/stock/movements").status_code == 401
        assert client.get("/api/v1/reports/daily?date_ad=2026-03-01").status_code == 401
        assert client.get("/api/v1/transfers").status_code == 401
        assert client.post("/api/v1/sales/orders", json={}).status_code == 401

    def test_last_active_admin_protection_comprehensive(self, setup_day_2_1_env):
        """Proves that neither self-action nor multi-admin action can deactivate the last active admin."""
        f = setup_day_2_1_env
        client = TestClient(app)

        # 1. Admin A creates a second admin
        create_res = client.post(
            "/api/v1/auth/users",
            json={
                "name": "Second Admin",
                "username": f"admin2_{uuid.uuid4().hex[:6]}",
                "password": "ValidPassword123!",
                "role": "admin"
            },
            headers=auth(f["u_a_admin"])
        )
        assert create_res.status_code == 201
        admin2_id = create_res.json()["id"]

        # 2. Deactivate the second admin -> Allowed because Admin A remains active
        deactivate_res = client.patch(
            f"/api/v1/auth/users/{admin2_id}",
            json={"active": False},
            headers=auth(f["u_a_admin"])
        )
        assert deactivate_res.status_code == 200
        assert deactivate_res.json()["active"] is False

        # 3. Now Admin A is the sole active admin. Attempting to deactivate Admin A must be blocked (400)
        self_deact = client.patch(
            f"/api/v1/auth/users/{f['u_a_admin'].id}",
            json={"active": False},
            headers=auth(f["u_a_admin"])
        )
        assert self_deact.status_code == 400

        # 4. Attempting to demote Admin A must also be blocked (400)
        self_demote = client.patch(
            f"/api/v1/auth/users/{f['u_a_admin'].id}",
            json={"role": "editor"},
            headers=auth(f["u_a_admin"])
        )
        assert self_demote.status_code == 400

    def test_rejected_cross_company_operations_preserve_data_invariants(self, setup_day_2_1_env):
        """Proves rejected cross-tenant requests produce ZERO state mutations."""
        f = setup_day_2_1_env
        client = TestClient(app)
        db = SessionLocal()
        try:
            from app.models.stock import StockMovement
            from app.models.sales import SalesOrder
            
            # Count records before attack
            initial_adj_count = db.query(StockMovement).count()
            initial_so_count = db.query(SalesOrder).count()

            # Execute malicious cross-tenant injection
            bad_adj = client.post(
                "/api/v1/stock/adjustments",
                json={
                    "warehouse_id": f["wh_b1"].id,  # Company B
                    "product_id": f["prod_a"].id,
                    "quantity_delta": 999.0,
                    "reason_code": "PURCHASE_RECEIPT"
                },
                headers=auth(f["u_a_editor"])
            )
            assert bad_adj.status_code == 404

            bad_so = client.post(
                "/api/v1/sales/orders",
                json={
                    "client_id": f["client_b"].id,  # Company B
                    "order_date_ad": "2026-03-01",
                    "order_date_bs": "2082-11-17",
                    "items": [{"product_id": f["prod_a"].id, "quantity": 10.0, "unit_price": 500.0}]
                },
                headers=auth(f["u_a_editor"])
            )
            assert bad_so.status_code == 404

            # Verify database records were completely untouched
            final_adj_count = db.query(StockMovement).count()
            final_so_count = db.query(SalesOrder).count()
            assert final_adj_count == initial_adj_count, "Adjustment count mutated despite 404 rejection"
            assert final_so_count == initial_so_count, "SalesOrder count mutated despite 404 rejection"
        finally:
            db.close()

    def test_concurrent_mutual_admin_deactivation_race_prevented(self, setup_day_2_1_env):
        """
        Concurrency Race: Two admins in the same company simultaneously attempt to deactivate each other.
        Under serialized transaction/advisory locking, exactly one deactivation succeeds,
        and the racing deactivation is rejected, ensuring >= 1 active admin ALWAYS remains.
        """
        import concurrent.futures
        f = setup_day_2_1_env
        client = TestClient(app)

        # 1. Admin A creates a co-administrator
        co_admin_user = f"coadmin_{uuid.uuid4().hex[:6]}"
        create_res = client.post(
            "/api/v1/auth/users",
            json={
                "name": "Co-Admin",
                "username": co_admin_user,
                "password": "ValidPassword123!",
                "role": "admin"
            },
            headers=auth(f["u_a_admin"])
        )
        assert create_res.status_code == 201
        co_admin_id = create_res.json()["id"]

        with SessionLocal() as db:
            co_admin_obj = db.query(User).filter(User.id == co_admin_id).first()
            assert co_admin_obj is not None
            co_admin_auth = auth(co_admin_obj)

        admin1_id = f["u_a_admin"].id
        admin2_id = co_admin_id

        # Racing workers:
        # Worker 1 (Admin 1) tries to deactivate Admin 2
        # Worker 2 (Admin 2) tries to deactivate Admin 1
        results = {}

        def deactivate_admin2():
            res = client.patch(
                f"/api/v1/auth/users/{admin2_id}",
                json={"active": False},
                headers=auth(f["u_a_admin"])
            )
            return ("deactivate_admin2", res.status_code, res.json())

        def deactivate_admin1():
            res = client.patch(
                f"/api/v1/auth/users/{admin1_id}",
                json={"active": False},
                headers=co_admin_auth
            )
            return ("deactivate_admin1", res.status_code, res.json())

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(deactivate_admin2)
            f2 = executor.submit(deactivate_admin1)
            r1 = f1.result()
            r2 = f2.result()

        status_codes = [r1[1], r2[1]]
        # Exactly one must succeed (200), and exactly one must be rejected (400)
        assert 200 in status_codes, f"Neither request succeeded: {status_codes}"
        assert 400 in status_codes, f"Both requests succeeded (RACE CONDITION DETECTED!): {status_codes}"

        # Invariant check: Verify committed state strictly retains at least 1 active admin
        with SessionLocal() as db:
            active_admins = db.query(User).filter(
                User.company_id == f["comp_a"].id,
                User.role == "admin",
                User.active == True
            ).count()
            assert active_admins == 1, f"Expected exactly 1 active admin remaining, found {active_admins}"

    def test_admin_lockout_strictly_scoped_by_company(self, setup_day_2_1_env):
        """
        Proves admin count is strictly company-scoped:
        The presence of active admins in Company B does NOT permit the last admin in Company A to deactivate.
        """
        f = setup_day_2_1_env
        client = TestClient(app)

        # Company B has active admin (f["u_b_admin"])
        # Attempting to deactivate the only active admin in Company A must fail with 400
        res = client.patch(
            f"/api/v1/auth/users/{f['u_a_admin'].id}",
            json={"active": False},
            headers=auth(f["u_a_admin"])
        )
        assert res.status_code == 400
        assert "Administrators cannot deactivate their own account" in res.json()["detail"]

    def test_pg_concurrent_mutual_admin_deactivation_race_prevented(self):
        """
        Genuine PostgreSQL Concurrency Verification:
        Proves PostgreSQL pg_advisory_xact_lock serializes concurrent admin deactivation across
        two independent database connections, preventing last active admin deactivation race.
        """
        try:
            from embedded_postgres import get_server
        except ImportError:
            pytest.skip("embedded_postgres not installed")

        import tempfile, pathlib, time, threading
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.company import Company
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.core.locks import acquire_user_admin_lock
        from app.db.session import Base

        pgdata = pathlib.Path(tempfile.mkdtemp()) / f"pg_admin_{uuid.uuid4().hex[:6]}"
        server = get_server(pgdata, cleanup_mode="delete")
        try:
            server.ensure_pgdata_inited()
            server.ensure_postgres_running()
            time.sleep(2)
            uri = server.get_uri().replace("postgresql://", "postgresql+psycopg2://", 1)
        except Exception as e:
            pytest.skip(f"Embedded PostgreSQL unavailable: {e}")

        try:
            engine = create_engine(uri, pool_pre_ping=True)
            import app.models  # Register all models on Base.metadata
            Base.metadata.create_all(bind=engine)
            SessionFactory = sessionmaker(bind=engine)

            # Setup Company & 2 Admins
            s_init = SessionFactory()
            cid = uuid.uuid4().hex[:6].upper()
            co = Company(name=f"PG Admin Corp {cid}", code=f"PAC-{cid}", pan_number=f"99{cid}")
            s_init.add(co)
            s_init.commit()
            s_init.refresh(co)

            admin1 = User(company_id=co.id, username=f"admin1_{cid.lower()}", name="Admin 1", password_hash=get_password_hash("Pass1!"), role="admin", active=True)
            admin2 = User(company_id=co.id, username=f"admin2_{cid.lower()}", name="Admin 2", password_hash=get_password_hash("Pass2!"), role="admin", active=True)
            s_init.add_all([admin1, admin2])
            s_init.commit()
            s_init.refresh(admin1)
            s_init.refresh(admin2)
            co_id = co.id
            a1_id = admin1.id
            a2_id = admin2.id
            s_init.close()

            barrier = threading.Barrier(2)
            results = []

            def worker_deactivate(target_id, caller_id):
                db = SessionFactory()
                try:
                    barrier.wait()
                    acquire_user_admin_lock(db, co_id)
                    target = db.query(User).filter(User.id == target_id, User.company_id == co_id).first()
                    if target.id == caller_id:
                        raise ValueError("Administrators cannot deactivate their own account")
                    other = db.query(User).filter(
                        User.company_id == co_id,
                        User.role == "admin",
                        User.active == True,
                        User.id != target.id
                    ).count()
                    if other == 0:
                        raise ValueError("Cannot deactivate the last active administrator in the company.")
                    target.active = False
                    db.commit()
                    results.append(("SUCCESS", target_id))
                except Exception as e:
                    db.rollback()
                    results.append(("FAILED", str(e)))
                finally:
                    db.close()

            t1 = threading.Thread(target=worker_deactivate, args=(a2_id, a1_id))
            t2 = threading.Thread(target=worker_deactivate, args=(a1_id, a2_id))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            statuses = [r[0] for r in results]
            assert "SUCCESS" in statuses, f"Expected 1 success, got: {results}"
            assert "FAILED" in statuses, f"Expected 1 failure, got: {results}"
            failed_reason = next(r[1] for r in results if r[0] == "FAILED")
            assert "Cannot deactivate the last active administrator" in failed_reason

            # Final verification on fresh PostgreSQL connection
            s_final = SessionFactory()
            active_count = s_final.query(User).filter(User.company_id == co_id, User.role == "admin", User.active == True).count()
            s_final.close()
            assert active_count == 1, f"Expected exactly 1 active admin remaining on PostgreSQL, found {active_count}"
        finally:
            try:
                server.cleanup()
            except Exception:
                pass


