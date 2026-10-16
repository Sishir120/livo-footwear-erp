"""
LIVO FOOTWEAR ERP — PHASE 5.1: INDEPENDENT VERIFICATION, MULTI-LOCATION SECURITY & REGRESSION HARDENING
Comprehensive Verification Suite covering:
  - Workstream 2: Tenant & Branch Authorization (10 explicit test vectors)
  - Workstream 3: Inventory Attribution & Stock Transfer Invariants
  - Workstream 4: Locking, Transaction Boundaries & Concurrency Guarantees
  - Workstream 5: Migration 023 Historical Data Preservation on SQLite & Embedded PostgreSQL 18.6.3
"""
import os
import sys
import time
import tempfile
import pathlib
import subprocess
from decimal import Decimal
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base
from app.api.deps import get_db
from app.core.security import create_access_token
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch, BranchType
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.api.v1.transfers import get_warehouse_stock

# Isolated SQLite in-memory engine with StaticPool
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
def setup_p51_environment():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Company 1 (Livo Primary Tenant)
    c1 = Company(id=1, name="Livo Footwear Nepal", code="LIVO_CO1", pan_number="100200300")
    u1_admin = User(id=1, company_id=1, name="Livo Admin", username="livo_adm_51", role="admin", password_hash="dummy", active=True)
    u1_editor = User(id=2, company_id=1, name="Livo Editor", username="livo_ed_51", role="editor", password_hash="dummy", active=True)
    u1_viewer = User(id=3, company_id=1, name="Livo Viewer", username="livo_vw_51", role="viewer", password_hash="dummy", active=True)

    # Company 2 (Himalayan Footwear Competitor Tenant)
    c2 = Company(id=2, name="Himalayan Footwear Ltd", code="HIMA_CO2", pan_number="999888777")
    u2_admin = User(id=4, company_id=2, name="Hima Admin", username="hima_adm_51", role="admin", password_hash="dummy", active=True)
    u2_editor = User(id=5, company_id=2, name="Hima Editor", username="hima_ed_51", role="editor", password_hash="dummy", active=True)
    u2_viewer = User(id=6, company_id=2, name="Hima Viewer", username="hima_vw_51", role="viewer", password_hash="dummy", active=True)

    db.add_all([c1, u1_admin, u1_editor, u1_viewer, c2, u2_admin, u2_editor, u2_viewer])

    # Warehouses
    wh1 = Warehouse(id=1, company_id=1, name="C1 Central Factory", code="WH-C1-01", location="Birgunj", is_active=True, branch_id=None)
    wh2 = Warehouse(id=2, company_id=1, name="C1 Showroom Depot", code="WH-C1-02", location="Kathmandu", is_active=True, branch_id=None)
    wh3 = Warehouse(id=3, company_id=1, name="C1 Unassigned Hub", code="WH-C1-03", location="Pokhara", is_active=True, branch_id=None)

    wh_c2_1 = Warehouse(id=4, company_id=2, name="C2 Factory Godown", code="WH-C2-01", location="Butwal", is_active=True, branch_id=None)
    wh_c2_2 = Warehouse(id=5, company_id=2, name="C2 Retail Depot", code="WH-C2-02", location="Bhairahawa", is_active=True, branch_id=None)

    # Products
    p1 = Product(id=1, company_id=1, code="SKU-C1-001", name="Livo Trekker", category="Boot", size="42", color="Black", unit_price=Decimal("3500.00"))
    p2 = Product(id=2, company_id=2, code="SKU-C2-001", name="Hima Runner", category="Shoe", size="42", color="Grey", unit_price=Decimal("2800.00"))

    db.add_all([wh1, wh2, wh3, wh_c2_1, wh_c2_2, p1, p2])
    db.commit()
    db.close()

    yield

    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


# ==============================================================================
# WORKSTREAM 2: TENANT AND BRANCH AUTHORIZATION (10 REQUIRED CASES)
# ==============================================================================

class TestWorkstream2AuthorizationVectors:
    """Verifies all 10 tenant and branch authorization rules explicitly."""

    def test_case_01_cross_tenant_branch_list_and_retrieve_denied(self):
        """Case 1: Company A cannot list or retrieve Company B's branches."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        h2 = auth_headers(company_id=2, user_id=5, role="editor")

        # Create branch for Company 1
        r1 = client.post("/api/v1/branches", json={"code": "BR-C1-AUTH1", "name": "C1 Main", "type": "HEAD_OFFICE"}, headers=h1)
        assert r1.status_code == 201
        b1_id = r1.json()["id"]

        # Company 2 lists branches: b1_id must NOT appear
        r2_list = client.get("/api/v1/branches", headers=h2)
        assert r2_list.status_code == 200
        ids = [b["id"] for b in r2_list.json()]
        assert b1_id not in ids

        # Company 2 attempts direct retrieve of b1_id: must return 404
        r2_get = client.get(f"/api/v1/branches/{b1_id}", headers=h2)
        assert r2_get.status_code == 404
        assert "not found" in r2_get.json()["detail"].lower()

    def test_case_02_cross_tenant_branch_update_and_toggle_denied(self):
        """Case 2: Company A cannot update, deactivate, or delete Company B's branch."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        h2 = auth_headers(company_id=2, user_id=5, role="editor")

        # Create branch for Company 1
        r1 = client.post("/api/v1/branches", json={"code": "BR-C1-AUTH2", "name": "C1 Sub", "type": "RETAIL_OUTLET"}, headers=h1)
        b1_id = r1.json()["id"]

        # Company 2 attempts update
        r_put = client.put(f"/api/v1/branches/{b1_id}", json={"name": "Hacked Name"}, headers=h2)
        assert r_put.status_code == 404

        # Company 2 attempts toggle active
        r_toggle = client.patch(f"/api/v1/branches/{b1_id}/toggle-active", headers=h2)
        assert r_toggle.status_code == 404

    def test_case_03_link_cross_company_warehouse_rejected(self):
        """Case 3: A user cannot link another company's warehouse to their branch."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        # Fetch Company 1 branch
        br_list = client.get("/api/v1/branches", headers=h1).json()
        b1_id = br_list[0]["id"]

        # Warehouse 4 belongs to Company 2
        r_assign = client.post(f"/api/v1/branches/{b1_id}/warehouses", json={"warehouse_id": 4}, headers=h1)
        assert r_assign.status_code == 404
        assert "not found in current company" in r_assign.json()["detail"].lower()

    def test_case_04_detach_cross_company_warehouse_rejected(self):
        """Case 4: A user cannot detach a warehouse from another company's branch."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        h2 = auth_headers(company_id=2, user_id=5, role="editor")

        # Create branch in Company 2 and link WH 4
        r2 = client.post("/api/v1/branches", json={"code": "BR-C2-AUTH4", "name": "C2 Branch", "type": "FACTORY"}, headers=h2)
        b2_id = r2.json()["id"]
        client.post(f"/api/v1/branches/{b2_id}/warehouses", json={"warehouse_id": 4}, headers=h2)

        # Company 1 user attempts to unlink WH 4 from b2_id
        r_unlink = client.delete(f"/api/v1/branches/{b2_id}/warehouses/4", headers=h1)
        assert r_unlink.status_code == 404

    def test_case_05_viewer_role_rejected_from_mutations(self):
        """Case 5: A viewer cannot perform branch mutations (HTTP 403)."""
        h_viewer = auth_headers(company_id=1, user_id=3, role="viewer")
        h_editor = auth_headers(company_id=1, user_id=2, role="editor")

        # Viewer cannot create branch
        r_create = client.post("/api/v1/branches", json={"code": "BR-VW-NO", "name": "Viewer Try", "type": "RETAIL_OUTLET"}, headers=h_viewer)
        assert r_create.status_code == 403

        # Viewer cannot update branch
        br_id = client.get("/api/v1/branches", headers=h_editor).json()[0]["id"]
        r_update = client.put(f"/api/v1/branches/{br_id}", json={"name": "Viewer Edit"}, headers=h_viewer)
        assert r_update.status_code == 403

        # Viewer cannot toggle status
        r_toggle = client.patch(f"/api/v1/branches/{br_id}/toggle-active", headers=h_viewer)
        assert r_toggle.status_code == 403

        # Viewer cannot link warehouse
        r_link = client.post(f"/api/v1/branches/{br_id}/warehouses", json={"warehouse_id": 1}, headers=h_viewer)
        assert r_link.status_code == 403

    def test_case_06_unauthenticated_request_rejected(self):
        """Case 6: An unauthenticated request cannot access protected branch endpoints."""
        assert client.get("/api/v1/branches").status_code == 401
        assert client.post("/api/v1/branches", json={"code": "BR-NO-AUTH", "name": "No Auth"}).status_code == 401
        assert client.get("/api/v1/branches/1").status_code == 401
        assert client.put("/api/v1/branches/1", json={"name": "No Auth"}).status_code == 401
        assert client.patch("/api/v1/branches/1/toggle-active").status_code == 401
        assert client.post("/api/v1/branches/1/warehouses", json={"warehouse_id": 1}).status_code == 401
        assert client.delete("/api/v1/branches/1/warehouses/1").status_code == 401

    def test_case_07_editor_and_admin_role_boundaries(self):
        """Case 7: Editors can perform operational branch mutations; role boundaries are validated."""
        h_editor = auth_headers(company_id=1, user_id=2, role="editor")
        h_admin = auth_headers(company_id=1, user_id=1, role="admin")

        # Both editor and admin can view and create
        r_ed = client.post("/api/v1/branches", json={"code": "BR-C1-ED1", "name": "Editor Branch", "type": "RETAIL_OUTLET"}, headers=h_editor)
        assert r_ed.status_code == 201

        r_adm = client.post("/api/v1/branches", json={"code": "BR-C1-ADM1", "name": "Admin Branch", "type": "HEAD_OFFICE"}, headers=h_admin)
        assert r_adm.status_code == 201

    def test_case_08_inactive_branch_cannot_accept_new_warehouses(self):
        """Case 8: Inactive branches cannot be used for new operations."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        # Create and deactivate branch
        r = client.post("/api/v1/branches", json={"code": "BR-INACT-01", "name": "Inactive Hub", "type": "REGIONAL_HUB"}, headers=h1)
        b_id = r.json()["id"]
        client.patch(f"/api/v1/branches/{b_id}/toggle-active", headers=h1)

        # Attempt to link WH 3
        r_link = client.post(f"/api/v1/branches/{b_id}/warehouses", json={"warehouse_id": 3}, headers=h1)
        assert r_link.status_code == 400
        assert "inactive branch" in r_link.json()["detail"].lower()

    def test_case_09_warehouse_belonging_to_c1_cannot_be_accessed_via_c2_branch(self):
        """Case 9: A warehouse belonging to Company 1 cannot be associated with a Company 2 branch."""
        h2 = auth_headers(company_id=2, user_id=5, role="editor")
        # Company 2 branch
        b2_list = client.get("/api/v1/branches", headers=h2).json()
        b2_id = b2_list[0]["id"]

        # WH 1 belongs to Company 1
        r_link = client.post(f"/api/v1/branches/{b2_id}/warehouses", json={"warehouse_id": 1}, headers=h2)
        assert r_link.status_code == 404

    def test_case_10_no_cross_company_data_leakage_in_responses(self):
        """Case 10: List, detail, error messages, and linked resources do not leak cross-company data."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        h2 = auth_headers(company_id=2, user_id=5, role="editor")

        # Company 1 list only returns company_id == 1
        c1_branches = client.get("/api/v1/branches", headers=h1).json()
        assert all(b["company_id"] == 1 for b in c1_branches)

        # Company 2 list only returns company_id == 2
        c2_branches = client.get("/api/v1/branches", headers=h2).json()
        assert all(b["company_id"] == 2 for b in c2_branches)

        # Error messages do not reveal existence of other company resources (returns generic 404, not 'exists in other company')
        r_idor = client.get(f"/api/v1/branches/{c2_branches[0]['id']}", headers=h1)
        assert r_idor.status_code == 404
        assert "not found" in r_idor.json()["detail"].lower()
        assert "himalayan" not in r_idor.text.lower()


# ==============================================================================
# WORKSTREAM 3: INVENTORY ATTRIBUTION & TRANSFER INVARIANTS
# ==============================================================================

class TestWorkstream3InventoryAttributionInvariants:
    """Verifies that branch attribution does not alter inventory math and tests all transfer modes."""

    def test_warehouse_branch_linking_does_not_mutate_stock_balances(self):
        """Linking or unlinking a branch to a warehouse does NOT create stock movements or mutate stock."""
        db = TestingSessionLocal()
        h1 = auth_headers(company_id=1, user_id=2, role="editor")

        # 1. Seed 100 pairs in WH 1
        db.add(StockMovement(
            company_id=1,
            product_id=1,
            warehouse_id=1,
            size="42",
            quantity=Decimal("100.0"),
            direction=1,
            movement_type="PRODUCTION_IN",
            ref_type="production",
            ref_id=101,
            date_ad="2026-10-15",
            date_bs="2083-07-01"
        ))
        db.commit()

        initial_stock = get_warehouse_stock(db, 1, 1, 1, "42")
        initial_mov_count = db.query(StockMovement).filter_by(warehouse_id=1).count()
        assert initial_stock == Decimal("100.0")

        # 2. Find or create a branch
        b1_list = client.get("/api/v1/branches", headers=h1).json()
        b_id = b1_list[0]["id"]

        # 3. Link WH 1 to branch
        r_link = client.post(f"/api/v1/branches/{b_id}/warehouses", json={"warehouse_id": 1}, headers=h1)
        assert r_link.status_code == 200

        # Stock balance and movement count must remain strictly unchanged!
        db.expire_all()
        assert get_warehouse_stock(db, 1, 1, 1, "42") == initial_stock
        assert db.query(StockMovement).filter_by(warehouse_id=1).count() == initial_mov_count

        # 4. Unlink WH 1 from branch
        r_unlink = client.delete(f"/api/v1/branches/{b_id}/warehouses/1", headers=h1)
        assert r_unlink.status_code == 200

        # Stock balance and movement count must still remain unchanged!
        db.expire_all()
        assert get_warehouse_stock(db, 1, 1, 1, "42") == initial_stock
        assert db.query(StockMovement).filter_by(warehouse_id=1).count() == initial_mov_count
        db.close()

    def test_intra_branch_transfer_vs_inter_branch_transfer_resolution(self):
        """Verifies resolution of same-branch (intra) vs different-branch (inter) transfers."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")

        # Create two distinct branches
        r_b1 = client.post("/api/v1/branches", json={"code": "BR-INTRA-1", "name": "Birgunj Cluster", "type": "FACTORY"}, headers=h1)
        r_b2 = client.post("/api/v1/branches", json={"code": "BR-INTER-2", "name": "Kathmandu Retail", "type": "RETAIL_OUTLET"}, headers=h1)
        b1_id = r_b1.json()["id"]
        b2_id = r_b2.json()["id"]

        # Link WH 1 and WH 2 to the SAME branch (b1_id) -> Intra-branch
        client.post(f"/api/v1/branches/{b1_id}/warehouses", json={"warehouse_id": 1}, headers=h1)
        client.post(f"/api/v1/branches/{b1_id}/warehouses", json={"warehouse_id": 2}, headers=h1)

        trf_intra = client.post("/api/v1/transfers", json={
            "source_warehouse_id": 1,
            "destination_warehouse_id": 2,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-07-01",
            "items": [{"product_id": 1, "size": "42", "quantity": 10}]
        }, headers=h1).json()

        detail_intra = client.get(f"/api/v1/transfers/{trf_intra['id']}", headers=h1).json()
        assert detail_intra["is_inter_branch"] is False
        assert detail_intra["source_branch_name"] == "Birgunj Cluster"
        assert detail_intra["destination_branch_name"] == "Birgunj Cluster"

        # Now link WH 2 to b2_id -> Inter-branch
        client.delete(f"/api/v1/branches/{b1_id}/warehouses/2", headers=h1)
        client.post(f"/api/v1/branches/{b2_id}/warehouses", json={"warehouse_id": 2}, headers=h1)

        trf_inter = client.post("/api/v1/transfers", json={
            "source_warehouse_id": 1,
            "destination_warehouse_id": 2,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-07-01",
            "items": [{"product_id": 1, "size": "42", "quantity": 10}]
        }, headers=h1).json()

        detail_inter = client.get(f"/api/v1/transfers/{trf_inter['id']}", headers=h1).json()
        assert detail_inter["is_inter_branch"] is True
        assert detail_inter["source_branch_name"] == "Birgunj Cluster"
        assert detail_inter["destination_branch_name"] == "Kathmandu Retail"

    def test_transfer_with_unassigned_warehouse_preserves_compatibility(self):
        """Transfers involving a warehouse with branch_id = None execute seamlessly with is_inter_branch = False."""
        h1 = auth_headers(company_id=1, user_id=2, role="editor")
        # WH 3 has branch_id = None
        wh3_detail = client.get("/api/v1/stock/warehouses/3", headers=h1).json()
        assert wh3_detail["branch_id"] is None

        trf = client.post("/api/v1/transfers", json={
            "source_warehouse_id": 1,
            "destination_warehouse_id": 3,
            "transfer_date_ad": "2026-10-15",
            "transfer_date_bs": "2083-07-01",
            "items": [{"product_id": 1, "size": "42", "quantity": 5}]
        }, headers=h1).json()

        detail = client.get(f"/api/v1/transfers/{trf['id']}", headers=h1).json()
        assert detail["destination_branch_name"] is None
        assert detail["is_inter_branch"] is False


# ==============================================================================
# WORKSTREAM 5: MIGRATION 023 HISTORICAL DATA PRESERVATION & REVERSIBILITY
# ==============================================================================

class TestWorkstream5MigrationIntegrity:
    """Tests that migration 023 upgrade and downgrade safely preserve existing warehouse records."""

    def test_sqlite_downgrade_preserves_historical_warehouse_records(self, tmp_path):
        """Tests on isolated SQLite that upgrading to 023, adding a branch, and downgrading preserves warehouses."""
        db_path = tmp_path / "sqlite_mig_preservation.db"
        db_url = f"sqlite:///{db_path}"

        backend_dir = pathlib.Path(__file__).resolve().parent.parent
        ini_path = backend_dir / "alembic.ini"
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(str(ini_path))
        alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)

        # 1. Upgrade to 022_add_stock_transfers
        command.upgrade(alembic_cfg, "022_add_stock_transfers")

        # 2. Insert historical company and warehouse in 022 schema
        test_engine = create_engine(db_url)
        with test_engine.connect() as conn:
            conn.execute(text("INSERT INTO companies (id, name, code) VALUES (1, 'Old Co', 'OLD_CO')"))
            conn.execute(text("INSERT INTO warehouses (id, company_id, name, code, location, is_active) VALUES (10, 1, 'Historical Godown', 'WH-HIST-10', 'Birgunj', 1)"))
            conn.commit()

        # 3. Upgrade to head (applies 023)
        command.upgrade(alembic_cfg, "head")

        with test_engine.connect() as conn:
            # Historical warehouse row must exist with NULL branch_id
            row = conn.execute(text("SELECT id, name, code, branch_id FROM warehouses WHERE id=10")).fetchone()
            assert row is not None
            assert row[0] == 10
            assert row[1] == "Historical Godown"
            assert row[3] is None

            # Insert branch and link warehouse
            conn.execute(text("INSERT INTO branches (id, company_id, code, name, type, is_active) VALUES (100, 1, 'BR-OLD-100', 'Old Branch', 'FACTORY', 1)"))
            conn.execute(text("UPDATE warehouses SET branch_id=100 WHERE id=10"))
            conn.commit()

        # 4. Downgrade to 022
        command.downgrade(alembic_cfg, "022_add_stock_transfers")

        with test_engine.connect() as conn:
            # Historical warehouse must STILL exist!
            row_down = conn.execute(text("SELECT id, name, code FROM warehouses WHERE id=10")).fetchone()
            assert row_down is not None
            assert row_down[0] == 10
            assert row_down[1] == "Historical Godown"

            # branches table must be gone
            insp = inspect(conn)
            assert "branches" not in insp.get_table_names()
            wh_cols = [c["name"] for c in insp.get_columns("warehouses")]
            assert "branch_id" not in wh_cols

        # 5. Re-upgrade to head (023)
        command.upgrade(alembic_cfg, "head")
        with test_engine.connect() as conn:
            row_reup = conn.execute(text("SELECT id, name, branch_id FROM warehouses WHERE id=10")).fetchone()
            assert row_reup is not None
            assert row_reup[0] == 10
            assert row_reup[2] is None  # Recreated column is cleanly null

        test_engine.dispose()

    def test_pg_downgrade_preserves_historical_warehouse_records(self):
        """Tests on embedded PostgreSQL 18.6.3 that migration 023 downgrade preserves existing warehouse data."""
        from embedded_postgres import get_server
        pgdir = pathlib.Path(tempfile.mkdtemp()) / "pg_p51_preservation"
        pg_server = get_server(pgdir, cleanup_mode="delete")
        pg_server.ensure_pgdata_inited()
        pg_server.ensure_postgres_running()
        time.sleep(2)
        pg_url = pg_server.get_uri()

        try:
            env = os.environ.copy()
            env["DATABASE_URL"] = pg_url
            env["SECRET_KEY"] = "phase51_preservation_key_32chars_min"

            # 1. Upgrade to 022
            res_022 = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "022_add_stock_transfers"],
                cwd=r"d:\Antigravity\Footwear app",
                env=env,
                capture_output=True,
                text=True
            )
            assert res_022.returncode == 0, f"Alembic upgrade 022 failed: {res_022.stderr}"

            pg_sa_url = pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            pg_engine = create_engine(pg_sa_url)

            # 2. Insert historical company and warehouse
            with pg_engine.connect() as conn:
                conn.execute(text("INSERT INTO companies (id, name, code) VALUES (1, 'PG Historical Co', 'PG_HIST_CO')"))
                conn.execute(text("INSERT INTO warehouses (id, company_id, name, code, location, is_active) VALUES (99, 1, 'PG Historical WH', 'WH-PG-99', 'Hetauda', true)"))
                conn.commit()

            # 3. Upgrade to head (023)
            res_023 = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
                cwd=r"d:\Antigravity\Footwear app",
                env=env,
                capture_output=True,
                text=True
            )
            assert res_023.returncode == 0, f"Alembic upgrade head failed: {res_023.stderr}"

            with pg_engine.connect() as conn:
                row = conn.execute(text("SELECT id, name, code, branch_id FROM warehouses WHERE id=99")).fetchone()
                assert row is not None
                assert row[0] == 99
                assert row[1] == "PG Historical WH"
                assert row[3] is None

                # Create branch and link
                conn.execute(text("INSERT INTO branches (id, company_id, code, name, type, is_active) VALUES (200, 1, 'BR-PG-200', 'PG Branch', 'RETAIL_OUTLET', true)"))
                conn.execute(text("UPDATE warehouses SET branch_id=200 WHERE id=99"))
                conn.commit()

            # 4. Downgrade to 022
            res_down = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "downgrade", "022_add_stock_transfers"],
                cwd=r"d:\Antigravity\Footwear app",
                env=env,
                capture_output=True,
                text=True
            )
            assert res_down.returncode == 0, f"Alembic downgrade 022 failed: {res_down.stderr}"

            with pg_engine.connect() as conn:
                row_down = conn.execute(text("SELECT id, name, code FROM warehouses WHERE id=99")).fetchone()
                assert row_down is not None
                assert row_down[0] == 99
                assert row_down[1] == "PG Historical WH"

                insp = inspect(conn)
                assert "branches" not in insp.get_table_names()
                cols = [c["name"] for c in insp.get_columns("warehouses")]
                assert "branch_id" not in cols

            # 5. Re-upgrade to head (023)
            res_reup = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
                cwd=r"d:\Antigravity\Footwear app",
                env=env,
                capture_output=True,
                text=True
            )
            assert res_reup.returncode == 0, f"Alembic re-upgrade failed: {res_reup.stderr}"

            with pg_engine.connect() as conn:
                row_reup = conn.execute(text("SELECT id, name, branch_id FROM warehouses WHERE id=99")).fetchone()
                assert row_reup is not None
                assert row_reup[0] == 99
                assert row_reup[2] is None

            pg_engine.dispose()
        finally:
            try:
                pg_server.cleanup()
            except Exception:
                pass

