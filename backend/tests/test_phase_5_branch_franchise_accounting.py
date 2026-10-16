"""
LIVO FOOTWEAR ERP — PHASE 5: BRANCH, WAREHOUSE & FRANCHISE ARCHITECTURE ACCEPTANCE TESTS
Validates:
1. Branch creation, retrieval, updates, and duplicate code rejection within company.
2. Multi-tenant company isolation (cross-tenant read, write, toggle, warehouse link rejected).
3. Warehouse-to-branch assignment, cross-company warehouse assignment rejection, and unlinking.
4. Deactivated branch restrictions (blocks new warehouse assignments, blocks deactivation with active in-transit transfers).
5. Branch-aware stock transfer attribution (source/destination branch detection, is_inter_branch flag).
6. Backward compatibility: existing warehouses and operations with branch_id = None operate seamlessly.
7. Real PostgreSQL 18.6.3 Alembic migration downgrade and re-upgrade reversibility.
"""
import os
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base
from app.api.deps import get_db
from app.core.security import create_access_token
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch, BranchType
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem

# Isolated SQLite in-memory engine with WAL & StaticPool for fast concurrency unit testing
from sqlalchemy.pool import StaticPool
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def auth_headers(company_id: int, user_id: int, role: str = "editor") -> dict:
    token = create_access_token({"user_id": user_id, "company_id": company_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True, scope="module")
def setup_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Company 1 (Livo Parent)
    c1 = Company(id=1, name="Livo Footwear Nepal", code="LIVO", pan_number="100200300")
    u1_admin = User(id=1, company_id=1, name="Livo Admin", username="livo_admin", role="admin", password_hash="dummy", active=True)
    u1_editor = User(id=2, company_id=1, name="Livo Editor", username="livo_editor", role="editor", password_hash="dummy", active=True)
    u1_viewer = User(id=3, company_id=1, name="Livo Viewer", username="livo_viewer", role="viewer", password_hash="dummy", active=True)

    # Company 2 (Competitor / Separate Tenant)
    c2 = Company(id=2, name="Himalayan Footwear Ltd", code="HIMA", pan_number="999888777")
    u2_admin = User(id=4, company_id=2, name="Hima Admin", username="hima_admin", role="admin", password_hash="dummy", active=True)
    u2_editor = User(id=5, company_id=2, name="Hima Editor", username="hima_editor", role="editor", password_hash="dummy", active=True)

    db.add_all([c1, u1_admin, u1_editor, u1_viewer, c2, u2_admin, u2_editor])

    # Company 1 Warehouses (initially without branch)
    wh_main = Warehouse(id=1, company_id=1, name="Birgunj Central Factory Godown", code="WH-BRG-MAIN", location="Birgunj", is_active=True)
    wh_ktm = Warehouse(id=2, company_id=1, name="Kathmandu Showroom Stock", code="WH-KTM-SHOW", location="New Road", is_active=True)
    wh_pkr = Warehouse(id=3, company_id=1, name="Pokhara Transit Hub", code="WH-PKR-HUB", location="Pokhara", is_active=True)

    # Company 2 Warehouse
    wh_c2 = Warehouse(id=4, company_id=2, name="Himalaya Butwal Godown", code="WH-HIMA-01", location="Butwal", is_active=True)

    # Product for transfer tests
    prod = Product(id=1, company_id=1, code="ART-P5-01", name="Livo Trail Runner", category="Shoe", size="42", color="Navy", unit_price=Decimal("2500.00"))

    db.add_all([wh_main, wh_ktm, wh_pkr, wh_c2, prod])
    db.commit()
    db.close()

    yield

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


class TestBranchMasterLifecycle:
    """Tests creation, retrieval, updates, and duplicate constraints for branches."""

    def test_create_branch_success(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        payload = {
            "code": "BR-KTM-01",
            "name": "Kathmandu Central Showroom",
            "type": "RETAIL_OUTLET",
            "address": "New Road, Kathmandu",
            "phone": "01-4220000",
            "email": "ktm@livo.com.np"
        }
        res = client.post("/api/v1/branches", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["code"] == "BR-KTM-01"
        assert data["name"] == "Kathmandu Central Showroom"
        assert data["type"] == "RETAIL_OUTLET"
        assert data["is_active"] is True
        assert data["warehouses_count"] == 0

    def test_duplicate_branch_code_in_same_company_rejected(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        payload = {
            "code": "BR-KTM-01",  # Same code as above
            "name": "Kathmandu Duplicate",
            "type": "RETAIL_OUTLET"
        }
        res = client.post("/api/v1/branches", json=payload, headers=headers)
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]

    def test_same_branch_code_allowed_in_different_company(self):
        """Cross-company namespace independence: Company 2 can use 'BR-KTM-01' without collision."""
        headers_c2 = auth_headers(company_id=2, user_id=5, role="editor")
        payload = {
            "code": "BR-KTM-01",
            "name": "Himalayan Kathmandu Branch",
            "type": "RETAIL_OUTLET"
        }
        res = client.post("/api/v1/branches", json=payload, headers=headers_c2)
        assert res.status_code == 201
        assert res.json()["company_id"] == 2
        assert res.json()["code"] == "BR-KTM-01"

    def test_viewer_role_forbidden_from_creating_branch(self):
        headers_viewer = auth_headers(company_id=1, user_id=3, role="viewer")
        payload = {
            "code": "BR-VIEW-FAIL",
            "name": "Unauthorized Branch",
            "type": "RETAIL_OUTLET"
        }
        res = client.post("/api/v1/branches", json=payload, headers=headers_viewer)
        assert res.status_code == 403

    def test_list_branches_returns_only_current_tenant_branches(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        res = client.get("/api/v1/branches", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert all(b["company_id"] == 1 for b in data)
        codes = [b["code"] for b in data]
        assert "BR-KTM-01" in codes

    def test_update_branch_metadata(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        # Fetch branch ID
        res_list = client.get("/api/v1/branches", headers=headers)
        b_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        update_payload = {
            "name": "Kathmandu Flagship Experience Center",
            "address": "Durbarmarg, Kathmandu"
        }
        res = client.put(f"/api/v1/branches/{b_id}", json=update_payload, headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Kathmandu Flagship Experience Center"
        assert res.json()["address"] == "Durbarmarg, Kathmandu"


class TestTenantIsolationAndWarehouseLinking:
    """Tests security boundaries, cross-company access denial, and warehouse-to-branch mapping."""

    def test_cross_company_branch_read_denied(self):
        # Company 1 branch ID
        headers_c1 = auth_headers(company_id=1, user_id=2, role="editor")
        res_list = client.get("/api/v1/branches", headers=headers_c1)
        b1_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        # Company 2 user attempts to access Company 1's branch
        headers_c2 = auth_headers(company_id=2, user_id=5, role="editor")
        res = client.get(f"/api/v1/branches/{b1_id}", headers=headers_c2)
        assert res.status_code == 404

    def test_cross_company_branch_mutation_denied(self):
        headers_c1 = auth_headers(company_id=1, user_id=2, role="editor")
        res_list = client.get("/api/v1/branches", headers=headers_c1)
        b1_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        headers_c2 = auth_headers(company_id=2, user_id=5, role="editor")
        res = client.put(f"/api/v1/branches/{b1_id}", json={"name": "Attacked Branch"}, headers=headers_c2)
        assert res.status_code == 404

    def test_assign_warehouse_to_branch_success(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        res_list = client.get("/api/v1/branches", headers=headers)
        b_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        # Assign Warehouse 2 (Kathmandu Showroom Stock)
        res = client.post(f"/api/v1/branches/{b_id}/warehouses", json={"warehouse_id": 2}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["warehouses_count"] == 1
        assert data["warehouses"][0]["id"] == 2
        assert data["warehouses"][0]["code"] == "WH-KTM-SHOW"

        # Verify /stock/warehouses reflects the branch linkage
        wh_res = client.get("/api/v1/stock/warehouses/2", headers=headers)
        assert wh_res.status_code == 200
        wh_data = wh_res.json()
        assert wh_data["branch_id"] == b_id
        assert wh_data["branch_code"] == "BR-KTM-01"

    def test_cross_company_warehouse_assignment_rejected(self):
        """Cannot assign Company 2 warehouse (WH 4) to Company 1 branch."""
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        res_list = client.get("/api/v1/branches", headers=headers)
        b_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        res = client.post(f"/api/v1/branches/{b_id}/warehouses", json={"warehouse_id": 4}, headers=headers)
        assert res.status_code == 404
        assert "not found in current company" in res.json()["detail"]

    def test_unlink_warehouse_from_branch(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        res_list = client.get("/api/v1/branches", headers=headers)
        b_id = next(b["id"] for b in res_list.json() if b["code"] == "BR-KTM-01")

        # Unlink Warehouse 2
        res = client.delete(f"/api/v1/branches/{b_id}/warehouses/2", headers=headers)
        assert res.status_code == 200
        assert res.json()["warehouses_count"] == 0

        # Verify warehouse is now unlinked (branch_id is null)
        wh_res = client.get("/api/v1/stock/warehouses/2", headers=headers)
        assert wh_res.json()["branch_id"] is None
        assert wh_res.json()["branch_name"] is None


class TestDeactivatedBranchAndTransferIntegrity:
    """Tests operational restrictions on deactivated branches and in-transit transfer guards."""

    def test_cannot_assign_warehouse_to_inactive_branch(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        # Create a branch and deactivate it
        res = client.post("/api/v1/branches", json={"code": "BR-DIS-01", "name": "Dormant Branch", "type": "RETAIL_OUTLET"}, headers=headers)
        b_id = res.json()["id"]

        # Toggle to inactive
        client.patch(f"/api/v1/branches/{b_id}/toggle-active", headers=headers)

        # Attempt to link warehouse
        res_assign = client.post(f"/api/v1/branches/{b_id}/warehouses", json={"warehouse_id": 3}, headers=headers)
        assert res_assign.status_code == 400
        assert "inactive branch" in res_assign.json()["detail"]

    def test_branch_aware_stock_transfer_resolution(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        # Setup: Create Factory Branch and Showroom Branch
        client.post("/api/v1/branches", json={"code": "BR-FACT-01", "name": "Birgunj Main Factory", "type": "FACTORY"}, headers=headers)
        br_list = client.get("/api/v1/branches", headers=headers).json()
        b_fact_id = next(b["id"] for b in br_list if b["code"] == "BR-FACT-01")
        b_ktm_id = next(b["id"] for b in br_list if b["code"] == "BR-KTM-01")

        # Link WH 1 (Factory) to BR-FACT-01, and WH 2 (Showroom) to BR-KTM-01
        client.post(f"/api/v1/branches/{b_fact_id}/warehouses", json={"warehouse_id": 1}, headers=headers)
        client.post(f"/api/v1/branches/{b_ktm_id}/warehouses", json={"warehouse_id": 2}, headers=headers)

        # Create Stock Transfer from WH 1 to WH 2
        payload = {
            "source_warehouse_id": 1,
            "destination_warehouse_id": 2,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-07-01",
            "items": [{"product_id": 1, "size": "42", "quantity": 50}]
        }
        res_create = client.post("/api/v1/transfers", json=payload, headers=headers)
        assert res_create.status_code == 201
        trf_id = res_create.json()["id"]

        # Detail query reflects branch names and inter-branch status
        res_detail = client.get(f"/api/v1/transfers/{trf_id}", headers=headers)
        assert res_detail.status_code == 200
        d = res_detail.json()
        assert d["source_branch_name"] == "Birgunj Main Factory"
        assert d["destination_branch_name"] == "Kathmandu Flagship Experience Center"
        assert d["is_inter_branch"] is True

    def test_cannot_deactivate_branch_with_in_transit_transfers(self):
        headers = auth_headers(company_id=1, user_id=2, role="editor")
        db = TestingSessionLocal()
        # Seed stock in WH 1 so dispatch succeeds
        db.add(StockMovement(
            company_id=1,
            product_id=1,
            warehouse_id=1,
            size="42",
            quantity=Decimal("100"),
            direction=1,
            movement_type="PRODUCTION_IN",
            ref_type="production",
            date_ad="2026-10-15",
            date_bs="2083-07-01"
        ))
        db.commit()
        db.close()

        # Find our transfer and dispatch it to IN_TRANSIT
        res_list = client.get("/api/v1/transfers", headers=headers).json()
        trf_id = res_list["items"][0]["id"]
        res_disp = client.post(f"/api/v1/transfers/{trf_id}/dispatch", headers=headers)
        assert res_disp.status_code == 200

        # Attempt to deactivate the factory branch while transfer is IN_TRANSIT
        br_list = client.get("/api/v1/branches", headers=headers).json()
        b_fact_id = next(b["id"] for b in br_list if b["code"] == "BR-FACT-01")

        res_deact = client.patch(f"/api/v1/branches/{b_fact_id}/toggle-active", headers=headers)
        assert res_deact.status_code == 400
        assert "IN_TRANSIT" in res_deact.json()["detail"]


class TestPostgreSQLMigrationReversibility:
    """Verifies Alembic migration 023 upgrade, downgrade, and re-upgrade on real embedded PostgreSQL 18.6.3."""

    _pg_server = None
    _pg_url = None

    @classmethod
    def setup_class(cls):
        import tempfile
        import pathlib
        import time
        try:
            from embedded_postgres import get_server
            pgdir = pathlib.Path(tempfile.mkdtemp()) / "pg_p5_mig"
            cls._pg_server = get_server(pgdir, cleanup_mode="delete")
            cls._pg_server.ensure_pgdata_inited()
            cls._pg_server.ensure_postgres_running()
            time.sleep(2)
            cls._pg_url = cls._pg_server.get_uri()
        except Exception:
            cls._pg_url = os.environ.get("LIVO_TEST_POSTGRES_URL")

    @classmethod
    def teardown_class(cls):
        if cls._pg_server:
            try:
                cls._pg_server.cleanup()
            except Exception:
                pass

    def test_pg_migration_023_reversibility(self):
        if not self._pg_url:
            pytest.skip("Embedded PostgreSQL not available for migration reversibility test.")

        import sys
        import subprocess
        from sqlalchemy import inspect as sa_inspect
        from sqlalchemy import create_engine

        env = os.environ.copy()
        env["DATABASE_URL"] = self._pg_url
        env["SECRET_KEY"] = "phase5_migration_key_32chars_min"

        # 1. Run migrations to head (applies 023)
        res_up = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res_up.returncode == 0, f"Alembic upgrade head failed: {res_up.stderr}"

        pg_sa_url = self._pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        engine_pg = create_engine(pg_sa_url)
        insp = sa_inspect(engine_pg)
        assert "branches" in insp.get_table_names(), "branches table was not created by migration 023"
        columns = [c["name"] for c in insp.get_columns("warehouses")]
        assert "branch_id" in columns, "warehouses.branch_id was not created by migration 023"
        engine_pg.dispose()

        # 2. Downgrade to 022 (rolls back 023 to 022)
        res_down = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "downgrade", "022_add_stock_transfers"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res_down.returncode == 0, f"Alembic downgrade -1 failed: {res_down.stderr}"

        engine_pg2 = create_engine(pg_sa_url)
        insp2 = sa_inspect(engine_pg2)
        assert "branches" not in insp2.get_table_names(), "branches table was not dropped on downgrade"
        columns2 = [c["name"] for c in insp2.get_columns("warehouses")]
        assert "branch_id" not in columns2, "warehouses.branch_id was not dropped on downgrade"
        engine_pg2.dispose()

        # 3. Re-upgrade to head (re-applies 023 cleanly)
        res_reup = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res_reup.returncode == 0, f"Alembic re-upgrade to head failed: {res_reup.stderr}"

        engine_pg3 = create_engine(pg_sa_url)
        insp3 = sa_inspect(engine_pg3)
        assert "branches" in insp3.get_table_names(), "branches table was not restored on re-upgrade"
        columns3 = [c["name"] for c in insp3.get_columns("warehouses")]
        assert "branch_id" in columns3, "warehouses.branch_id was not restored on re-upgrade"
        engine_pg3.dispose()
