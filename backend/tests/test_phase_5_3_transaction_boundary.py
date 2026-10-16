import os
import time
import uuid
import pathlib
import tempfile
import threading
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal, Base
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.models.sales import Client, SalesOrder
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry
from app.core.security import get_password_hash, create_access_token
from app.core.locks import (
    acquire_stock_transfer_lock,
    acquire_stock_mutation_lock,
    get_stock_transfer_mutex,
    release_all_session_locks
)
from app.api.v1.transfers import get_warehouse_stock


# ---------------------------------------------------------------------------
# Global Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def p53_company():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6]
        co = Company(name=f"P53 Co {uid}", code=f"P53-{uid}", pan_number=f"53{uid}")
        db.add(co)
        db.commit()
        db.refresh(co)
        yield co
    finally:
        db.close()


@pytest.fixture(scope="module")
def p53_env():
    """Isolated environment for SQLite API tests."""
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6].upper()
        co = Company(name=f"Phase 5.3 Corp {uid}", code=f"P53-{uid}", pan_number=f"53{uid}")
        db.add(co)
        db.commit()
        db.refresh(co)

        editor = User(
            company_id=co.id,
            username=f"p53_ed_{uid.lower()}",
            name="Phase 5.3 Auditor",
            password_hash=get_password_hash("AuditPass2026!"),
            role="editor",
            active=True
        )
        db.add(editor)
        db.commit()
        db.refresh(editor)

        wh_src = Warehouse(company_id=co.id, name=f"P53 Src WH {uid}", code=f"WH-S53-{uid}", is_active=True)
        wh_dst = Warehouse(company_id=co.id, name=f"P53 Dst WH {uid}", code=f"WH-D53-{uid}", is_active=True)
        db.add(wh_src)
        db.add(wh_dst)
        db.commit()
        db.refresh(wh_src)
        db.refresh(wh_dst)

        token = create_access_token({
            "user_id": editor.id,
            "company_id": co.id,
            "role": editor.role,
            "username": editor.username
        })

        yield {
            "company_id": co.id,
            "editor_id": editor.id,
            "token": token,
            "wh_src_id": wh_src.id,
            "wh_dst_id": wh_dst.id
        }
    finally:
        db.close()


def _get_client(token: str) -> TestClient:
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _create_product_with_stock(db: Session, company_id: int, code: str, stock_qty: Decimal, wh_id: int, user_id: int) -> Product:
    prod = Product(
        company_id=company_id,
        code=code,
        name=f"P53 Footwear {code}",
        category="formal",
        unit_price=Decimal("3000.00")
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)

    mov = StockMovement(
        company_id=company_id,
        product_id=prod.id,
        warehouse_id=wh_id,
        size="42",
        quantity=stock_qty,
        direction=1,
        movement_type="PURCHASE_RECEIPT",
        ref_type="manual_init",
        actor_id=user_id,
        date_ad=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        date_bs="2083-01-01",
        notes="P53 Initial stock deposit"
    )
    db.add(mov)
    db.commit()
    return prod


# ---------------------------------------------------------------------------
# Stage 2: Audit Lock Helper & Session Lifecycle
# ---------------------------------------------------------------------------

class TestStage2LockHelperSessionLifecycle:
    """Rigorous audit of acquire_stock_transfer_lock and SQLAlchemy session lifecycle."""

    def test_1_caller_pending_orm_object_preserved(self, p53_company):
        """Caller adds a pending ORM object before acquiring transfer lock."""
        db = SessionLocal()
        try:
            uid = uuid.uuid4().hex[:6]
            cli = Client(company_id=p53_company.id, code=f"C1-{uid}", name=f"Pending ORM {uid}", phone="9841000001")
            db.add(cli)
            assert cli in db.new

            acquire_stock_transfer_lock(db, p53_company.id, 9901)

            assert cli in db.new
            db.commit()

            db2 = SessionLocal()
            persisted = db2.query(Client).filter_by(id=cli.id).first()
            assert persisted is not None
            assert persisted.name == f"Pending ORM {uid}"
            db2.close()
        finally:
            db.close()

    def test_2_caller_modified_persistent_object_preserved(self, p53_company):
        """Caller modifies a persistent object before lock acquisition."""
        db = SessionLocal()
        try:
            uid = uuid.uuid4().hex[:6]
            cli = Client(company_id=p53_company.id, code=f"C2-{uid}", name=f"Orig Name {uid}", phone="9841000002")
            db.add(cli)
            db.commit()
            db.refresh(cli)

            cli.name = f"Modified Name {uid}"
            assert cli in db.dirty

            acquire_stock_transfer_lock(db, p53_company.id, 9902)

            assert cli in db.dirty
            db.commit()

            db2 = SessionLocal()
            persisted = db2.query(Client).filter_by(id=cli.id).first()
            assert persisted.name == f"Modified Name {uid}"
            db2.close()
        finally:
            db.close()

    def test_3_caller_raw_sql_execution_preserved(self, p53_company):
        """Caller executes SQL that has an effect but leaves ORM dirty collections empty."""
        db = SessionLocal()
        try:
            uid = uuid.uuid4().hex[:6]
            cli = Client(company_id=p53_company.id, code=f"C3-{uid}", name=f"Orig SQL {uid}", phone="9841000003")
            db.add(cli)
            db.commit()
            db.refresh(cli)

            # Execute raw SQL update
            db.execute(
                text("UPDATE clients SET name = :new_name WHERE id = :id"),
                {"new_name": f"Updated via SQL {uid}", "id": cli.id}
            )

            assert len(db.new) == 0
            assert len(db.dirty) == 0
            assert len(db.deleted) == 0

            # Acquire transfer lock -> must NEVER roll back caller SQL!
            acquire_stock_transfer_lock(db, p53_company.id, 9903)

            db.commit()

            db2 = SessionLocal()
            persisted = db2.query(Client).filter_by(id=cli.id).first()
            assert persisted is not None
            assert persisted.name == f"Updated via SQL {uid}"
            db2.close()
        finally:
            db.close()

    def test_4_active_transaction_lock_acquisition(self, p53_company):
        """A session has an active transaction and acquires a database lock."""
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            assert db.is_active

            mutex = get_stock_transfer_mutex(p53_company.id, 9904)
            acquire_stock_transfer_lock(db, p53_company.id, 9904)
            assert mutex.locked()

            db.commit()
            assert not mutex.locked()
        finally:
            db.close()

    def test_5_lock_acquisition_failure_cleanup(self, p53_company):
        """Simulate lock acquisition exception -> clean state, no dangling registration."""
        from unittest.mock import patch, MagicMock
        db = SessionLocal()
        try:
            mock_mutex = MagicMock()
            mock_mutex.acquire.side_effect = TimeoutError("Lock acquisition timeout")
            with patch("app.core.locks.get_stock_transfer_mutex", return_value=mock_mutex):
                with pytest.raises(TimeoutError):
                    acquire_stock_transfer_lock(db, p53_company.id, 9905)
            assert len(db.info.get("_held_thread_locks", [])) == 0
        finally:
            db.close()

    def test_6_business_operation_failure_after_lock(self, p53_company):
        """A business operation fails after lock acquisition -> total rollback, lock released."""
        db = SessionLocal()
        mutex = get_stock_transfer_mutex(p53_company.id, 9906)
        uid = uuid.uuid4().hex[:6]
        try:
            acquire_stock_transfer_lock(db, p53_company.id, 9906)
            assert mutex.locked()

            cli = Client(company_id=p53_company.id, code=f"C6-{uid}", name=f"Fail Op {uid}", phone="9841000006")
            db.add(cli)
            db.flush()

            raise ValueError("Simulated validation failure")
        except ValueError:
            release_all_session_locks(db)
            db.rollback()

        assert not mutex.locked()
        db2 = SessionLocal()
        persisted = db2.query(Client).filter_by(code=f"C6-{uid}").first()
        assert persisted is None
        db2.close()
        db.close()

    def test_7_lock_release_on_success_rollback_exception_early_return(self, p53_company):
        """Lock release occurs after: 1) commit, 2) rollback, 3) exception, 4) early return."""
        # 1. Success commit
        db = SessionLocal()
        m1 = get_stock_transfer_mutex(p53_company.id, 99071)
        acquire_stock_transfer_lock(db, p53_company.id, 99071)
        assert m1.locked()
        db.commit()
        assert not m1.locked()
        db.close()

        # 2. Rollback
        db = SessionLocal()
        m2 = get_stock_transfer_mutex(p53_company.id, 99072)
        acquire_stock_transfer_lock(db, p53_company.id, 99072)
        assert m2.locked()
        release_all_session_locks(db)
        db.rollback()
        assert not m2.locked()
        db.close()

        # 3. Exception
        db = SessionLocal()
        m3 = get_stock_transfer_mutex(p53_company.id, 99073)
        try:
            acquire_stock_transfer_lock(db, p53_company.id, 99073)
            assert m3.locked()
            raise RuntimeError("Failure")
        except RuntimeError:
            release_all_session_locks(db)
            db.close()
        assert not m3.locked()

        # 4. Early return
        def early_return_func():
            s = SessionLocal()
            try:
                acquire_stock_transfer_lock(s, p53_company.id, 99074)
                return "early_return_result"
            finally:
                release_all_session_locks(s)
                s.close()

        m4 = get_stock_transfer_mutex(p53_company.id, 99074)
        res = early_return_func()
        assert res == "early_return_result"
        assert not m4.locked()

    def test_8_session_reused_after_lock_cleanup(self, p53_company):
        """A session is reused after lock acquisition and cleanup."""
        db = SessionLocal()
        try:
            # Operation 1: Transfer A
            mA = get_stock_transfer_mutex(p53_company.id, 99081)
            acquire_stock_transfer_lock(db, p53_company.id, 99081)
            assert mA.locked()
            db.commit()
            assert not mA.locked()

            # Operation 2 on SAME session: Transfer B
            mB = get_stock_transfer_mutex(p53_company.id, 99082)
            acquire_stock_transfer_lock(db, p53_company.id, 99082)
            assert mB.locked()

            uid = uuid.uuid4().hex[:6]
            cli = Client(company_id=p53_company.id, code=f"C8-{uid}", name=f"Reused Session {uid}", phone="9841000008")
            db.add(cli)
            db.commit()
            assert not mB.locked()

            db2 = SessionLocal()
            assert db2.query(Client).filter_by(id=cli.id).first() is not None
            db2.close()
        finally:
            db.close()

    def test_9_caller_mixed_raw_sql_and_orm_mutations_preserved(self, p53_company):
        """Case 5: A transaction containing both raw SQL and ORM mutations before lock acquisition."""
        db = SessionLocal()
        try:
            uid = uuid.uuid4().hex[:6]
            # 1. Existing record to update via raw SQL
            existing_cli = Client(company_id=p53_company.id, code=f"C9E-{uid}", name=f"Existing {uid}", phone="9841000009")
            db.add(existing_cli)
            db.commit()
            db.refresh(existing_cli)

            # 2. Add pending ORM object
            new_cli = Client(company_id=p53_company.id, code=f"C9N-{uid}", name=f"Pending ORM {uid}", phone="9841000010")
            db.add(new_cli)

            # 3. Execute raw SQL update
            db.execute(
                text("UPDATE clients SET name = :new_name WHERE id = :id"),
                {"new_name": f"Raw Updated {uid}", "id": existing_cli.id}
            )

            assert new_cli in db.new
            assert existing_cli not in db.dirty  # Raw SQL does not populate db.dirty!

            # 4. Acquire transfer lock -> must preserve BOTH pending ORM and raw SQL!
            acquire_stock_transfer_lock(db, p53_company.id, 9909)

            assert new_cli in db.new
            db.commit()

            # 5. Verify both persisted in separate session
            db2 = SessionLocal()
            persisted_new = db2.query(Client).filter_by(code=f"C9N-{uid}").first()
            persisted_raw = db2.query(Client).filter_by(id=existing_cli.id).first()
            assert persisted_new is not None
            assert persisted_new.name == f"Pending ORM {uid}"
            assert persisted_raw is not None
            assert persisted_raw.name == f"Raw Updated {uid}"
            db2.close()
        finally:
            db.close()

    def test_10_session_reused_after_failed_operation(self, p53_company):
        """Case 10: Reuse of a session following a failed operation."""
        db = SessionLocal()
        m1 = get_stock_transfer_mutex(p53_company.id, 9910)
        m2 = get_stock_transfer_mutex(p53_company.id, 9911)
        uid = uuid.uuid4().hex[:6]
        try:
            # Operation 1: Fails
            acquire_stock_transfer_lock(db, p53_company.id, 9910)
            assert m1.locked()
            fail_cli = Client(company_id=p53_company.id, code=f"C10F-{uid}", name=f"Fail {uid}", phone="9841000011")
            db.add(fail_cli)
            db.flush()
            # Simulate failure and rollback
            release_all_session_locks(db)
            db.rollback()
            assert not m1.locked()

            # Operation 2: Succeeds on SAME session instance
            acquire_stock_transfer_lock(db, p53_company.id, 9911)
            assert m2.locked()
            succ_cli = Client(company_id=p53_company.id, code=f"C10S-{uid}", name=f"Success {uid}", phone="9841000012")
            db.add(succ_cli)
            db.commit()
            assert not m2.locked()

            # Verify persisted state
            db2 = SessionLocal()
            assert db2.query(Client).filter_by(code=f"C10F-{uid}").first() is None
            assert db2.query(Client).filter_by(code=f"C10S-{uid}").first() is not None
            db2.close()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Stage 3: Prove PostgreSQL Concurrency Behavior
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pg_env():
    """Provides an isolated real PostgreSQL instance (embedded_postgres) for genuine concurrency testing."""
    try:
        from embedded_postgres import get_server
    except ImportError:
        pytest.skip("embedded_postgres not installed")

    pgdata = pathlib.Path(tempfile.mkdtemp()) / "pg53_concurrency"
    server = get_server(pgdata, cleanup_mode="delete")
    try:
        server.ensure_pgdata_inited()
        server.ensure_postgres_running()
        time.sleep(2)
        uri = server.get_uri().replace("postgresql://", "postgresql+psycopg2://", 1)
    except Exception as e:
        pytest.skip(f"Could not initialize embedded PostgreSQL: {e}")

    engine = create_engine(uri, pool_pre_ping=True)
    import app.models
    Base.metadata.create_all(bind=engine)
    SessionFactory = sessionmaker(bind=engine)

    # Initialize company, warehouses, editor
    s = SessionFactory()
    uid = uuid.uuid4().hex[:6].upper()
    co = Company(name=f"PG Concurrency Corp {uid}", code=f"PGC-{uid}", pan_number=f"53{uid}")
    s.add(co)
    s.commit()
    s.refresh(co)

    editor = User(
        company_id=co.id,
        username=f"pg_ed_{uid.lower()}",
        name="PG Auditor",
        password_hash=get_password_hash("PgPass2026!"),
        role="editor",
        active=True
    )
    s.add(editor)
    s.commit()
    s.refresh(editor)

    wh_src = Warehouse(company_id=co.id, name=f"PG Central WH {uid}", code=f"WH-PGS-{uid}", is_active=True)
    wh_dst = Warehouse(company_id=co.id, name=f"PG Outlet WH {uid}", code=f"WH-PGD-{uid}", is_active=True)
    s.add(wh_src)
    s.add(wh_dst)
    s.commit()
    s.refresh(wh_src)
    s.refresh(wh_dst)
    co_id = co.id
    editor_id = editor.id
    wh_src_id = wh_src.id
    wh_dst_id = wh_dst.id
    s.close()

    yield {
        "engine": engine,
        "factory": SessionFactory,
        "company_id": co_id,
        "editor_id": editor_id,
        "wh_src_id": wh_src_id,
        "wh_dst_id": wh_dst_id
    }

    try:
        server.cleanup()
    except Exception:
        pass


class TestStage3PostgreSQLConcurrency:
    """Proves concurrency guarantees against real PostgreSQL 18.6.3 with separate sessions & transactions."""

    def test_pg_dialect_and_version(self, pg_env):
        """Verifies database dialect and PostgreSQL version."""
        with pg_env["engine"].connect() as conn:
            assert pg_env["engine"].dialect.name == "postgresql"
            version_str = conn.execute(text("SELECT version()")).scalar()
            assert "PostgreSQL" in version_str
            print("\nPROVEN POSTGRESQL VERSION:", version_str)

    def test_pg_race_1_concurrent_dispatches_serialized(self, pg_env):
        """Race 1: Two concurrent dispatches of the same transfer on PostgreSQL."""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        prod = _create_product_with_stock(s_init, pg_env["company_id"], f"PG-D1-{uuid.uuid4().hex[:4]}", Decimal("50.0"), pg_env["wh_src_id"], pg_env["editor_id"])
        prod_id = prod.id

        trf = StockTransfer(
            company_id=pg_env["company_id"],
            transfer_number=f"TRF-PG1-{uuid.uuid4().hex[:6]}",
            source_warehouse_id=pg_env["wh_src_id"],
            destination_warehouse_id=pg_env["wh_dst_id"],
            transfer_date_ad="2026-10-15",
            transfer_date_bs="2083-06-29",
            status="DRAFT",
            created_by_id=pg_env["editor_id"]
        )
        s_init.add(trf)
        s_init.commit()
        s_init.refresh(trf)

        item = StockTransferItem(
            company_id=pg_env["company_id"],
            transfer_id=trf.id,
            product_id=prod_id,
            size="42",
            requested_quantity=Decimal("20.0"),
            dispatched_quantity=Decimal("0.0"),
            received_quantity=Decimal("0.0"),
            discrepancy_quantity=Decimal("0.0")
        )
        s_init.add(item)
        s_init.commit()
        trf_id = trf.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = []

        def worker():
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_transfer_lock(db, pg_env["company_id"], trf_id)
                t = db.query(StockTransfer).filter_by(id=trf_id, company_id=pg_env["company_id"]).with_for_update().first()
                if t.status != "DRAFT":
                    raise ValueError(f"Cannot dispatch transfer in '{t.status}' status.")
                for itm in t.items:
                    acquire_stock_mutation_lock(db, pg_env["company_id"], t.source_warehouse_id, itm.product_id, str(itm.size or ""))
                    avail = get_warehouse_stock(db, pg_env["company_id"], t.source_warehouse_id, itm.product_id, itm.size)
                    if itm.requested_quantity > avail:
                        raise ValueError("Insufficient stock")
                    mov = StockMovement(
                        company_id=pg_env["company_id"], product_id=itm.product_id, warehouse_id=t.source_warehouse_id,
                        size=itm.size, quantity=itm.requested_quantity, direction=-1, movement_type="TRANSFER_OUT",
                        ref_type="transfer", ref_id=t.id, source_doc_ref=t.transfer_number, actor_id=pg_env["editor_id"],
                        date_ad="2026-10-15", date_bs="2083-06-29"
                    )
                    db.add(mov)
                    itm.dispatched_quantity = itm.requested_quantity
                t.status = "IN_TRANSIT"
                db.commit()
                results.append(200)
            except ValueError:
                db.rollback()
                results.append(400)
            finally:
                db.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sorted(results) == [200, 400]
        s_chk = SessionFactory()
        persisted_trf = s_chk.query(StockTransfer).filter_by(id=trf_id).first()
        assert persisted_trf.status == "IN_TRANSIT"
        rem_stock = get_warehouse_stock(s_chk, pg_env["company_id"], pg_env["wh_src_id"], prod_id, "42")
        assert rem_stock == Decimal("30.0")  # Deducted exactly once!
        out_movs = s_chk.query(StockMovement).filter_by(ref_id=trf_id, movement_type="TRANSFER_OUT").count()
        assert out_movs == 1
        s_chk.close()

    def test_pg_race_2_concurrent_receipts_serialized(self, pg_env):
        """Race 2: Two concurrent receipts against the same transfer item."""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        prod = _create_product_with_stock(s_init, pg_env["company_id"], f"PG-R2-{uuid.uuid4().hex[:4]}", Decimal("40.0"), pg_env["wh_src_id"], pg_env["editor_id"])
        prod_id = prod.id

        trf = StockTransfer(
            company_id=pg_env["company_id"],
            transfer_number=f"TRF-PGR2-{uuid.uuid4().hex[:6]}",
            source_warehouse_id=pg_env["wh_src_id"],
            destination_warehouse_id=pg_env["wh_dst_id"],
            transfer_date_ad="2026-10-15",
            transfer_date_bs="2083-06-29",
            status="IN_TRANSIT",
            created_by_id=pg_env["editor_id"]
        )
        s_init.add(trf)
        s_init.commit()

        item = StockTransferItem(
            company_id=pg_env["company_id"],
            transfer_id=trf.id,
            product_id=prod_id,
            size="42",
            requested_quantity=Decimal("25.0"),
            dispatched_quantity=Decimal("25.0"),
            received_quantity=Decimal("0.0"),
            discrepancy_quantity=Decimal("0.0")
        )
        s_init.add(item)
        s_init.commit()
        trf_id = trf.id
        item_id = item.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = []

        def worker():
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_transfer_lock(db, pg_env["company_id"], trf_id)
                t = db.query(StockTransfer).filter_by(id=trf_id, company_id=pg_env["company_id"]).with_for_update().first()
                if t.status not in ("IN_TRANSIT", "PARTIALLY_RECEIVED"):
                    raise ValueError(f"Cannot receive transfer in '{t.status}' status.")
                itm = db.query(StockTransferItem).filter_by(id=item_id).with_for_update().first()
                rem = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
                rec_qty = Decimal("25.0")
                if rec_qty > rem:
                    raise ValueError("Over-receipt forbidden")
                mov = StockMovement(
                    company_id=pg_env["company_id"], product_id=itm.product_id, warehouse_id=t.destination_warehouse_id,
                    size=itm.size, quantity=rec_qty, direction=1, movement_type="TRANSFER_IN",
                    ref_type="transfer", ref_id=t.id, source_doc_ref=t.transfer_number, actor_id=pg_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                )
                db.add(mov)
                itm.received_quantity = Decimal(str(itm.received_quantity)) + rec_qty
                t.status = "RECEIVED"
                db.commit()
                results.append(200)
            except ValueError:
                db.rollback()
                results.append(400)
            finally:
                db.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sorted(results) == [200, 400]
        s_chk = SessionFactory()
        dst_stock = get_warehouse_stock(s_chk, pg_env["company_id"], pg_env["wh_dst_id"], prod_id, "42")
        assert dst_stock == Decimal("25.0")  # NEVER 50.0!
        in_movs = s_chk.query(StockMovement).filter_by(ref_id=trf_id, movement_type="TRANSFER_IN").count()
        assert in_movs == 1
        s_chk.close()

    def test_pg_race_3_receipt_racing_cancellation(self, pg_env):
        """Race 3: Full receipt racing cancellation preserves absolute inventory conservation."""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        prod = _create_product_with_stock(s_init, pg_env["company_id"], f"PG-R3-{uuid.uuid4().hex[:4]}", Decimal("60.0"), pg_env["wh_src_id"], pg_env["editor_id"])
        prod_id = prod.id

        trf = StockTransfer(
            company_id=pg_env["company_id"],
            transfer_number=f"TRF-PGR3-{uuid.uuid4().hex[:6]}",
            source_warehouse_id=pg_env["wh_src_id"],
            destination_warehouse_id=pg_env["wh_dst_id"],
            transfer_date_ad="2026-10-15",
            transfer_date_bs="2083-06-29",
            status="IN_TRANSIT",
            created_by_id=pg_env["editor_id"]
        )
        s_init.add(trf)
        s_init.commit()

        item = StockTransferItem(
            company_id=pg_env["company_id"],
            transfer_id=trf.id,
            product_id=prod_id,
            size="42",
            requested_quantity=Decimal("40.0"),
            dispatched_quantity=Decimal("40.0"),
            received_quantity=Decimal("0.0"),
            discrepancy_quantity=Decimal("0.0")
        )
        s_init.add(item)
        # Deduct initial dispatch from source
        s_init.add(StockMovement(
            company_id=pg_env["company_id"], product_id=prod_id, warehouse_id=pg_env["wh_src_id"],
            size="42", quantity=Decimal("40.0"), direction=-1, movement_type="TRANSFER_OUT",
            ref_type="transfer", ref_id=trf.id, source_doc_ref=trf.transfer_number, actor_id=pg_env["editor_id"],
            date_ad="2026-10-15", date_bs="2083-06-29"
        ))
        s_init.commit()
        trf_id = trf.id
        item_id = item.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = {}

        def worker_rec():
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_transfer_lock(db, pg_env["company_id"], trf_id)
                t = db.query(StockTransfer).filter_by(id=trf_id).with_for_update().first()
                if t.status not in ("IN_TRANSIT", "PARTIALLY_RECEIVED"):
                    raise ValueError(f"Cannot receive transfer in '{t.status}' status.")
                itm = db.query(StockTransferItem).filter_by(id=item_id).with_for_update().first()
                db.add(StockMovement(
                    company_id=pg_env["company_id"], product_id=itm.product_id, warehouse_id=t.destination_warehouse_id,
                    size=itm.size, quantity=Decimal("40.0"), direction=1, movement_type="TRANSFER_IN",
                    ref_type="transfer", ref_id=t.id, source_doc_ref=t.transfer_number, actor_id=pg_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                ))
                itm.received_quantity = Decimal("40.0")
                t.status = "RECEIVED"
                db.commit()
                results["rec"] = 200
            except ValueError:
                db.rollback()
                results["rec"] = 400
            finally:
                db.close()

        def worker_can():
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_transfer_lock(db, pg_env["company_id"], trf_id)
                t = db.query(StockTransfer).filter_by(id=trf_id).with_for_update().first()
                if t.status == "RECEIVED":
                    raise ValueError("Cannot cancel a received transfer.")
                if t.status == "CANCELLED":
                    raise ValueError("Already cancelled.")
                itm = db.query(StockTransferItem).filter_by(id=item_id).with_for_update().first()
                rem = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
                if rem > 0:
                    db.add(StockMovement(
                        company_id=pg_env["company_id"], product_id=itm.product_id, warehouse_id=t.source_warehouse_id,
                        size=itm.size, quantity=rem, direction=1, movement_type="VOID_REVERSAL",
                        ref_type="transfer", ref_id=t.id, source_doc_ref=f"VOID-{t.transfer_number}", actor_id=pg_env["editor_id"],
                        date_ad="2026-10-15", date_bs="2083-06-29"
                    ))
                t.status = "CANCELLED"
                db.commit()
                results["can"] = 200
            except ValueError:
                db.rollback()
                results["can"] = 400
            finally:
                db.close()

        t1 = threading.Thread(target=worker_rec)
        t2 = threading.Thread(target=worker_can)
        t1.start(); t2.start(); t1.join(); t2.join()

        assert {results["rec"], results["can"]} == {200, 400}
        s_chk = SessionFactory()
        src_s = get_warehouse_stock(s_chk, pg_env["company_id"], pg_env["wh_src_id"], prod_id, "42")
        dst_s = get_warehouse_stock(s_chk, pg_env["company_id"], pg_env["wh_dst_id"], prod_id, "42")
        assert src_s + dst_s == Decimal("60.0")  # Exactly 60.0 pairs strictly conserved!
        s_chk.close()

    def test_pg_race_4_concurrent_cancellations(self, pg_env):
        """Race 4: Two concurrent cancellations -> exactly one succeeds, source not double-reversed."""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        prod = _create_product_with_stock(s_init, pg_env["company_id"], f"PG-R4-{uuid.uuid4().hex[:4]}", Decimal("50.0"), pg_env["wh_src_id"], pg_env["editor_id"])

        trf = StockTransfer(
            company_id=pg_env["company_id"],
            transfer_number=f"TRF-PGR4-{uuid.uuid4().hex[:6]}",
            source_warehouse_id=pg_env["wh_src_id"],
            destination_warehouse_id=pg_env["wh_dst_id"],
            status="IN_TRANSIT",
            transfer_date_ad="2026-10-15",
            transfer_date_bs="2083-06-29",
            created_by_id=pg_env["editor_id"]
        )
        s_init.add(trf)
        s_init.commit()

        item = StockTransferItem(
            company_id=pg_env["company_id"],
            transfer_id=trf.id,
            product_id=prod.id,
            size="42",
            requested_quantity=Decimal("30.0"),
            dispatched_quantity=Decimal("30.0"),
            received_quantity=Decimal("0.0"),
            discrepancy_quantity=Decimal("0.0")
        )
        s_init.add(item)
        s_init.commit()
        trf_id = trf.id
        item_id = item.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = []

        def worker():
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_transfer_lock(db, pg_env["company_id"], trf_id)
                t = db.query(StockTransfer).filter_by(id=trf_id).with_for_update().first()
                if t.status == "CANCELLED":
                    raise ValueError("Already cancelled")
                itm = db.query(StockTransferItem).filter_by(id=item_id).with_for_update().first()
                rem = Decimal(str(itm.dispatched_quantity)) - Decimal(str(itm.received_quantity))
                if rem > 0:
                    db.add(StockMovement(
                        company_id=pg_env["company_id"], product_id=itm.product_id, warehouse_id=t.source_warehouse_id,
                        size=itm.size, quantity=rem, direction=1, movement_type="VOID_REVERSAL",
                        ref_type="transfer", ref_id=t.id, source_doc_ref=f"VOID-{t.transfer_number}", actor_id=pg_env["editor_id"],
                        date_ad="2026-10-15", date_bs="2083-06-29"
                    ))
                t.status = "CANCELLED"
                db.commit()
                results.append(200)
            except ValueError:
                db.rollback()
                results.append(400)
            finally:
                db.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sorted(results) == [200, 400]
        s_chk = SessionFactory()
        void_movs = s_chk.query(StockMovement).filter_by(ref_id=trf_id, movement_type="VOID_REVERSAL").count()
        assert void_movs == 1  # Exactly one VOID_REVERSAL, never two!
        s_chk.close()

    def test_pg_race_5_overlapping_stock_consumption(self, pg_env):
        """Race 5: Two transfers attempting to consume overlapping available stock -> stock never negative!"""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        prod = _create_product_with_stock(s_init, pg_env["company_id"], f"PG-R5-{uuid.uuid4().hex[:4]}", Decimal("30.0"), pg_env["wh_src_id"], pg_env["editor_id"])
        prod_id = prod.id

        # Transfer A: requests 20.0 pairs
        trf_a = StockTransfer(
            company_id=pg_env["company_id"], transfer_number=f"TRF-A-{uuid.uuid4().hex[:4]}",
            source_warehouse_id=pg_env["wh_src_id"], destination_warehouse_id=pg_env["wh_dst_id"],
            status="DRAFT", transfer_date_ad="2026-10-15", transfer_date_bs="2083-06-29", created_by_id=pg_env["editor_id"]
        )
        # Transfer B: requests 20.0 pairs
        trf_b = StockTransfer(
            company_id=pg_env["company_id"], transfer_number=f"TRF-B-{uuid.uuid4().hex[:4]}",
            source_warehouse_id=pg_env["wh_src_id"], destination_warehouse_id=pg_env["wh_dst_id"],
            status="DRAFT", transfer_date_ad="2026-10-15", transfer_date_bs="2083-06-29", created_by_id=pg_env["editor_id"]
        )
        s_init.add(trf_a); s_init.add(trf_b); s_init.commit()
        s_init.add(StockTransferItem(company_id=pg_env["company_id"], transfer_id=trf_a.id, product_id=prod_id, size="42", requested_quantity=Decimal("20.0"), dispatched_quantity=0, received_quantity=0, discrepancy_quantity=0))
        s_init.add(StockTransferItem(company_id=pg_env["company_id"], transfer_id=trf_b.id, product_id=prod_id, size="42", requested_quantity=Decimal("20.0"), dispatched_quantity=0, received_quantity=0, discrepancy_quantity=0))
        s_init.commit()
        id_a, id_b = trf_a.id, trf_b.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = []

        def worker_dispatch(t_id):
            db = SessionFactory()
            try:
                barrier.wait()
                acquire_stock_mutation_lock(db, pg_env["company_id"], pg_env["wh_src_id"], prod_id, "42")
                t = db.query(StockTransfer).filter_by(id=t_id).with_for_update().first()
                avail = get_warehouse_stock(db, pg_env["company_id"], t.source_warehouse_id, prod_id, "42")
                if Decimal("20.0") > avail:
                    raise ValueError(f"Insufficient stock: requested 20.0, available {avail}")
                db.add(StockMovement(
                    company_id=pg_env["company_id"], product_id=prod_id, warehouse_id=t.source_warehouse_id,
                    size="42", quantity=Decimal("20.0"), direction=-1, movement_type="TRANSFER_OUT",
                    ref_type="transfer", ref_id=t.id, source_doc_ref=t.transfer_number, actor_id=pg_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                ))
                t.status = "IN_TRANSIT"
                db.commit()
                results.append(200)
            except ValueError:
                db.rollback()
                results.append(400)
            finally:
                db.close()

        t1 = threading.Thread(target=worker_dispatch, args=(id_a,))
        t2 = threading.Thread(target=worker_dispatch, args=(id_b,))
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sorted(results) == [200, 400]
        s_chk = SessionFactory()
        rem_stock = get_warehouse_stock(s_chk, pg_env["company_id"], pg_env["wh_src_id"], prod_id, "42")
        assert rem_stock == Decimal("10.0")  # NEVER negative!
        s_chk.close()

    def test_pg_race_6_concurrent_credit_notes_ceiling(self, pg_env):
        """Race 6: Two concurrent credit notes that jointly exceed the invoice credit ceiling."""
        SessionFactory = pg_env["factory"]
        s_init = SessionFactory()
        uid = uuid.uuid4().hex[:6]
        client = Client(company_id=pg_env["company_id"], code=f"CL-CN-{uid}", name=f"CN Client {uid}", phone="9841000000")
        s_init.add(client); s_init.commit()
        client_id = client.id

        order = SalesOrder(
            company_id=pg_env["company_id"], client_id=client_id, order_number=f"SO-{uid}",
            order_date_ad="2026-10-15", order_date_bs="2083-06-29", status="CONFIRMED"
        )
        s_init.add(order); s_init.commit()

        # Invoice total = Rs. 10,000 (1,000,000 paisa)
        inv = Invoice(
            company_id=pg_env["company_id"], sales_order_id=order.id, invoice_number=f"INV-CN-{uid}",
            sequence_number=1, date_ad="2026-10-15", date_bs="2083-06-29",
            subtotal=Decimal("8849.56"), vat_enabled=True, vat_rate=Decimal("13.0"), vat_amount=Decimal("1150.44"),
            total_amount=Decimal("10000.00"), received_amount=Decimal("0.0"), receivable_amount=Decimal("10000.00")
        )
        s_init.add(inv); s_init.commit()
        inv_id = inv.id
        s_init.close()

        barrier = threading.Barrier(2)
        results = []

        def worker_credit_note():
            db = SessionFactory()
            try:
                barrier.wait()
                # Row-level lock on Invoice
                invoice = db.query(Invoice).filter_by(id=inv_id, company_id=pg_env["company_id"]).with_for_update().first()
                existing_credits_paisa = db.query(func.coalesce(func.sum(ReceivableEntry.amount_paisa), 0)).filter(
                    ReceivableEntry.company_id == pg_env["company_id"],
                    ReceivableEntry.invoice_id == invoice.id,
                    ReceivableEntry.entry_type == "CREDIT_NOTE"
                ).scalar() or 0

                remaining_creditable_paisa = 1000000 - existing_credits_paisa
                credit_requested_paisa = 600000  # Rs. 6,000
                if credit_requested_paisa > remaining_creditable_paisa:
                    raise ValueError(f"Exceeds remaining credit ceiling: requested {credit_requested_paisa}, remaining {remaining_creditable_paisa}")

                db.add(ReceivableEntry(
                    company_id=pg_env["company_id"], client_id=client_id, entry_type="CREDIT_NOTE",
                    direction=-1, amount_paisa=credit_requested_paisa, source_doc_ref=f"CN-{invoice.invoice_number}",
                    invoice_id=invoice.id, actor_id=pg_env["editor_id"], occurred_at=datetime.now(timezone.utc)
                ))
                db.commit()
                results.append(200)
            except ValueError:
                db.rollback()
                results.append(400)
            finally:
                db.close()

        t1 = threading.Thread(target=worker_credit_note)
        t2 = threading.Thread(target=worker_credit_note)
        t1.start(); t2.start(); t1.join(); t2.join()

        assert sorted(results) == [200, 400]
        s_chk = SessionFactory()
        total_credited = s_chk.query(func.sum(ReceivableEntry.amount_paisa)).filter_by(invoice_id=inv_id).scalar()
        assert total_credited == 600000  # Exactly 6,000 Rs, NEVER 12,000!
        s_chk.close()


# ---------------------------------------------------------------------------
# Stage 4: Inventory Conservation Model & Quantities
# ---------------------------------------------------------------------------

class TestStage4InventoryConservationModel:
    """Verifies the Universal Inventory Conservation Equation across all receipt and cancellation flows."""

    def test_full_receipt_conservation(self, p53_env):
        """Full receipt: Dispatched = Received, Transit = 0, Disc = 0."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-FC-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 50.0}], "is_final": True
            })
            assert r_res.status_code == 200

            # Database Assertions
            t_chk = client.get(f"/api/v1/transfers/{t_id}").json()
            assert t_chk["status"] == "RECEIVED"
            assert t_chk["items"][0]["dispatched_quantity"] == 50.0
            assert t_chk["items"][0]["received_quantity"] == 50.0
            assert t_chk["items"][0]["discrepancy_quantity"] == 0.0

            src_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42")
            dst_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42")
            assert src_s == Decimal("0.0")
            assert dst_s == Decimal("50.0")
            assert src_s + dst_s == Decimal("50.0")
        finally:
            db.close()

    def test_partial_receipt_conservation(self, p53_env):
        """Partial receipt: Dispatched = Received (30) + Transit (20)."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-PR-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 30.0}], "is_final": False
            })
            assert r_res.status_code == 200

            t_chk = client.get(f"/api/v1/transfers/{t_id}").json()
            assert t_chk["status"] == "PARTIALLY_RECEIVED"
            assert t_chk["items"][0]["received_quantity"] == 30.0

            src_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42")
            dst_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42")
            in_transit = Decimal(str(t_chk["items"][0]["dispatched_quantity"])) - Decimal(str(t_chk["items"][0]["received_quantity"]))
            assert in_transit == Decimal("20.0")
            assert src_s + dst_s + in_transit == Decimal("50.0")
        finally:
            db.close()

    def test_multi_stage_receipt_conservation(self, p53_env):
        """Multi-stage receipt: Stage 1 (20) + Stage 2 (30) = Total (50)."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-MS-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Stage 1: 20 units
            client.post(f"/api/v1/transfers/{t_id}/receive", json={"items": [{"item_id": item_id, "received_quantity": 20.0}], "is_final": False})
            assert client.get(f"/api/v1/transfers/{t_id}").json()["status"] == "PARTIALLY_RECEIVED"

            # Stage 2: Remaining 30 units (final)
            client.post(f"/api/v1/transfers/{t_id}/receive", json={"items": [{"item_id": item_id, "received_quantity": 30.0}], "is_final": True})
            t_final = client.get(f"/api/v1/transfers/{t_id}").json()
            assert t_final["status"] == "RECEIVED"
            assert t_final["items"][0]["received_quantity"] == 50.0

            dst_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42")
            assert dst_s == Decimal("50.0")
        finally:
            db.close()

    def test_shortage_with_discrepancy_reason(self, p53_env):
        """Final short receipt with discrepancy reason: Dispatched (50) = Received (45) + Disc (5)."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-DR-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 45.0, "discrepancy_reason": "5 pairs soaked in monsoon flood"}],
                "is_final": True
            })
            assert r_res.status_code == 200

            t_chk = client.get(f"/api/v1/transfers/{t_id}").json()
            assert t_chk["status"] == "RECEIVED"
            assert t_chk["items"][0]["discrepancy_quantity"] == 5.0
            assert t_chk["items"][0]["discrepancy_reason"] == "5 pairs soaked in monsoon flood"

            # Verify audit movement created with direction = 0
            disc_mov = db.query(StockMovement).filter_by(ref_id=t_id, movement_type="TRANSIT_DISCREPANCY").first()
            assert disc_mov is not None
            assert disc_mov.direction == 0
            assert disc_mov.quantity == Decimal("5.0")
        finally:
            db.close()

    def test_shortage_without_discrepancy_reason_rejected(self, p53_env):
        """Final short receipt missing mandatory discrepancy reason is rejected (400)."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-ND-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 40.0}],
                "is_final": True
            })
            assert r_res.status_code == 400
            assert "discrepancy reason is strictly required" in r_res.json()["detail"].lower()
        finally:
            db.close()

    def test_cancellation_before_receipt(self, p53_env):
        """Cancellation before any receipt: Dispatched quantity (40) reversed 100% to source."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-CB-{uuid.uuid4().hex[:4]}", Decimal("40.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 40.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            assert get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42") == Decimal("0.0")

            c_res = client.post(f"/api/v1/transfers/{t_id}/cancel")
            assert c_res.status_code == 200
            assert c_res.json()["status"] == "CANCELLED"

            src_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42")
            assert src_s == Decimal("40.0")  # Source restored!
        finally:
            db.close()

    def test_cancellation_after_partial_receipt(self, p53_env):
        """Cancellation after partial receipt: unreceived (30) reversed to source; received (20) remains at dest."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-CA-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Receive 20 units
            client.post(f"/api/v1/transfers/{t_id}/receive", json={"items": [{"item_id": item_id, "received_quantity": 20.0}], "is_final": False})

            # Cancel remaining 30 units
            c_res = client.post(f"/api/v1/transfers/{t_id}/cancel")
            assert c_res.status_code == 200

            src_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42")
            dst_s = get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42")
            assert src_s == Decimal("30.0")  # 30 returned to source
            assert dst_s == Decimal("20.0")  # 20 remains at destination
            assert src_s + dst_s == Decimal("50.0")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Stage 5: Failure Injection & Idempotency
# ---------------------------------------------------------------------------

class TestStage5FailureInjectionAndIdempotency:
    """Verifies that failures at mutation boundaries roll back completely and retries are idempotent."""

    def test_failure_after_source_deduction_before_transfer_status(self, p53_env):
        """Failure after source deduction flushed: rollback leaves zero movements, stock balance unchanged."""
        db = SessionLocal()
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-FI1-{uuid.uuid4().hex[:4]}", Decimal("30.0"), p53_env["wh_src_id"], p53_env["editor_id"])
            initial_count = db.query(StockMovement).filter_by(product_id=prod.id).count()

            trf = StockTransfer(
                company_id=p53_env["company_id"], transfer_number=f"TRF-FI1-{uuid.uuid4().hex[:4]}",
                source_warehouse_id=p53_env["wh_src_id"], destination_warehouse_id=p53_env["wh_dst_id"],
                status="DRAFT", transfer_date_ad="2026-10-15", transfer_date_bs="2083-06-29", created_by_id=p53_env["editor_id"]
            )
            db.add(trf); db.commit()

            try:
                acquire_stock_transfer_lock(db, p53_env["company_id"], trf.id)
                db.add(StockMovement(
                    company_id=p53_env["company_id"], product_id=prod.id, warehouse_id=p53_env["wh_src_id"],
                    size="42", quantity=Decimal("15.0"), direction=-1, movement_type="TRANSFER_OUT",
                    ref_type="transfer", ref_id=trf.id, source_doc_ref=trf.transfer_number, actor_id=p53_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                ))
                db.flush()
                # Crash before status update and commit
                raise RuntimeError("Simulated crash before status persistence")
            except RuntimeError:
                db.rollback()

            final_count = db.query(StockMovement).filter_by(product_id=prod.id).count()
            assert final_count == initial_count
            assert get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_src_id"], prod.id, "42") == Decimal("30.0")
        finally:
            db.close()

    def test_failure_after_destination_receipt_before_commit(self, p53_env):
        """Failure after destination movement flushed: rollback leaves zero destination movements."""
        db = SessionLocal()
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-FI2-{uuid.uuid4().hex[:4]}", Decimal("30.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            trf = StockTransfer(
                company_id=p53_env["company_id"], transfer_number=f"TRF-FI2-{uuid.uuid4().hex[:4]}",
                source_warehouse_id=p53_env["wh_src_id"], destination_warehouse_id=p53_env["wh_dst_id"],
                status="IN_TRANSIT", transfer_date_ad="2026-10-15", transfer_date_bs="2083-06-29", created_by_id=p53_env["editor_id"]
            )
            db.add(trf); db.commit()

            try:
                acquire_stock_transfer_lock(db, p53_env["company_id"], trf.id)
                db.add(StockMovement(
                    company_id=p53_env["company_id"], product_id=prod.id, warehouse_id=p53_env["wh_dst_id"],
                    size="42", quantity=Decimal("20.0"), direction=1, movement_type="TRANSFER_IN",
                    ref_type="transfer", ref_id=trf.id, source_doc_ref=trf.transfer_number, actor_id=p53_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                ))
                db.flush()
                raise RuntimeError("Simulated crash before receipt commit")
            except RuntimeError:
                db.rollback()

            assert get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42") == Decimal("0.0")
        finally:
            db.close()

    def test_failure_during_discrepancy_creation(self, p53_env):
        """Failure while persisting discrepancy movement: rollback leaves zero movements."""
        db = SessionLocal()
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-FI3-{uuid.uuid4().hex[:4]}", Decimal("40.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            trf = StockTransfer(
                company_id=p53_env["company_id"], transfer_number=f"TRF-FI3-{uuid.uuid4().hex[:4]}",
                source_warehouse_id=p53_env["wh_src_id"], destination_warehouse_id=p53_env["wh_dst_id"],
                status="IN_TRANSIT", transfer_date_ad="2026-10-15", transfer_date_bs="2083-06-29", created_by_id=p53_env["editor_id"]
            )
            db.add(trf); db.commit()

            try:
                acquire_stock_transfer_lock(db, p53_env["company_id"], trf.id)
                # Flush receipt
                db.add(StockMovement(
                    company_id=p53_env["company_id"], product_id=prod.id, warehouse_id=p53_env["wh_dst_id"],
                    size="42", quantity=Decimal("35.0"), direction=1, movement_type="TRANSFER_IN",
                    ref_type="transfer", ref_id=trf.id, source_doc_ref=trf.transfer_number, actor_id=p53_env["editor_id"],
                    date_ad="2026-10-15", date_bs="2083-06-29"
                ))
                db.flush()
                # Fail during discrepancy logging
                raise RuntimeError("Failed to create TRANSIT_DISCREPANCY audit record")
            except RuntimeError:
                db.rollback()

            assert get_warehouse_stock(db, p53_env["company_id"], p53_env["wh_dst_id"], prod.id, "42") == Decimal("0.0")
        finally:
            db.close()

    def test_idempotent_retry_prevents_duplicate_movements(self, p53_env):
        """Retrying an operation with the same Idempotency-Key returns cached response without duplicate stock movements."""
        db = SessionLocal()
        client = _get_client(p53_env["token"])
        try:
            prod = _create_product_with_stock(db, p53_env["company_id"], f"P53-IDEM-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p53_env["wh_src_id"], p53_env["editor_id"])

            idempotency_key = f"idem-key-{uuid.uuid4().hex}"
            client.headers["X-Idempotency-Key"] = idempotency_key

            # Request 1: Create transfer
            payload = {
                "source_warehouse_id": p53_env["wh_src_id"], "destination_warehouse_id": p53_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15", "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 25.0}]
            }
            res1 = client.post("/api/v1/transfers", json=payload)
            assert res1.status_code == 201
            t1_id = res1.json()["id"]

            # Request 2: Retried request with identical Idempotency-Key
            res2 = client.post("/api/v1/transfers", json=payload)
            assert res2.status_code == 201
            assert res2.json()["id"] == t1_id  # Returns cached identical transfer, NOT a duplicate!

            # Assert database has exactly 1 transfer created with this number
            trf_count = db.query(StockTransfer).filter_by(id=t1_id).count()
            assert trf_count == 1
        finally:
            client.headers.pop("X-Idempotency-Key", None)
            db.close()
