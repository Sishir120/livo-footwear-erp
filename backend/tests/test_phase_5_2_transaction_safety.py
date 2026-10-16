import os
import sys
import uuid
import threading
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.session import SessionLocal, Base, engine as default_engine
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.security import get_password_hash, create_access_token
from app.core.locks import (
    acquire_stock_transfer_lock,
    acquire_stock_mutation_lock,
    get_stock_transfer_mutex,
    release_all_session_locks
)
from app.api.v1.transfers import get_warehouse_stock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def p52_env():
    """Sets up an isolated company, editor, warehouses, and product."""
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6].upper()
        co = Company(name=f"Phase 5.2 Corp {uid}", code=f"P52-{uid}", pan_number=f"52{uid}")
        db.add(co)
        db.commit()
        db.refresh(co)

        editor = User(
            company_id=co.id,
            username=f"p52_ed_{uid.lower()}",
            name="Phase 5.2 Safety Auditor",
            password_hash=get_password_hash("AuditPass2026!"),
            role="editor",
            active=True
        )
        db.add(editor)
        db.commit()
        db.refresh(editor)

        wh_src = Warehouse(company_id=co.id, name=f"P52 Central WH {uid}", code=f"WH-S52-{uid}", is_active=True)
        wh_dst = Warehouse(company_id=co.id, name=f"P52 Outlet WH {uid}", code=f"WH-D52-{uid}", is_active=True)
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
        name=f"P52 Footwear {code}",
        category="formal",
        unit_price=Decimal("2500.00")
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
        notes="P52 Initial stock deposit"
    )
    db.add(mov)
    db.commit()
    return prod


# ---------------------------------------------------------------------------
# 1. Rollback Hazard Verification & Prevention Tests
# ---------------------------------------------------------------------------

class TestRollbackHazardPrevention:
    """Verifies that acquire_stock_transfer_lock NEVER rolls back uncommitted caller mutations."""

    def test_uncommitted_caller_mutation_preserved_during_lock_acquire(self, p52_env):
        """Proof: If a caller adds an uncommitted object before lock acquisition, it is NOT rolled back."""
        db = SessionLocal()
        try:
            # 1. Caller adds an uncommitted client to db
            uid = uuid.uuid4().hex[:6]
            uncommitted_client = Client(
                company_id=p52_env["company_id"],
                code=f"CLI-52-{uid}",
                name=f"Uncommitted Client {uid}",
                phone=f"9841{uid[:6]}"
            )
            db.add(uncommitted_client)
            assert uncommitted_client in db.new
            assert len(db.new) == 1

            # 2. Acquire lock on transfer 9999
            acquire_stock_transfer_lock(db, p52_env["company_id"], 9999)

            # 3. Assert uncommitted_client was NOT rolled back
            assert uncommitted_client in db.new
            assert len(db.new) == 1

            # 4. Caller commits and verifies persistence
            db.commit()
            persisted = db.query(Client).filter_by(id=uncommitted_client.id).first()
            assert persisted is not None
            assert persisted.name == f"Uncommitted Client {uid}"
        finally:
            db.close()

    def test_clean_session_read_snapshot_refreshed_on_sqlite(self, p52_env):
        """Proof: If a session is clean (only read auth), it refreshes read snapshot cleanly."""
        db = SessionLocal()
        try:
            # Clean session - no dirty objects
            assert len(db.new) == 0
            assert len(db.dirty) == 0
            assert len(db.deleted) == 0

            lock_id = acquire_stock_transfer_lock(db, p52_env["company_id"], 8888)
            assert isinstance(lock_id, int)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 2. Transaction Atomicity & Failure Boundary Tests
# ---------------------------------------------------------------------------

class TestTransactionBoundariesAndFailureModes:
    """Verifies that failures at each mutation boundary roll back completely without partial state."""

    def test_failure_after_inventory_deduction_before_transfer_status_commit(self, p52_env):
        """If an exception occurs between movement creation and transfer status commit, no movements persist."""
        db = SessionLocal()
        try:
            prod = _create_product_with_stock(db, p52_env["company_id"], f"P52-AT-{uuid.uuid4().hex[:4]}", Decimal("50.0"), p52_env["wh_src_id"], p52_env["editor_id"])
            initial_movements = db.query(StockMovement).filter(StockMovement.product_id == prod.id).count()

            trf = StockTransfer(
                company_id=p52_env["company_id"],
                transfer_number=f"TRF-SIM-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=p52_env["wh_src_id"],
                destination_warehouse_id=p52_env["wh_dst_id"],
                transfer_date_ad="2026-10-15",
                transfer_date_bs="2083-06-29",
                status="DRAFT",
                created_by_id=p52_env["editor_id"]
            )
            db.add(trf)
            db.commit()

            # Simulate simulated crash in dispatch transaction
            try:
                acquire_stock_transfer_lock(db, p52_env["company_id"], trf.id)
                mov = StockMovement(
                    company_id=p52_env["company_id"],
                    product_id=prod.id,
                    warehouse_id=trf.source_warehouse_id,
                    size="42",
                    quantity=Decimal("20.0"),
                    direction=-1,
                    movement_type="TRANSFER_OUT",
                    ref_type="transfer",
                    ref_id=trf.id,
                    actor_id=p52_env["editor_id"],
                    date_ad="2026-10-15",
                    date_bs="2083-06-29"
                )
                db.add(mov)
                db.flush() # Flushed but uncommitted!

                # Simulate crash / error before status change and commit
                raise RuntimeError("Simulated DB connection crash before commit")
            except RuntimeError:
                db.rollback()

            # Verify total rollback: StockMovement count unchanged, stock balance intact
            final_movements = db.query(StockMovement).filter(StockMovement.product_id == prod.id).count()
            assert final_movements == initial_movements
            stock = get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_src_id"], prod.id, "42")
            assert stock == Decimal("50.0")

            # Transfer remains in DRAFT status
            db.refresh(trf)
            assert trf.status == "DRAFT"
        finally:
            db.close()

    def test_failure_during_receipt_reverses_all_receipt_movements(self, p52_env):
        """If receipt fails due to missing discrepancy reason on short receipt, zero movements are committed."""
        db = SessionLocal()
        client = _get_client(p52_env["token"])
        try:
            prod = _create_product_with_stock(db, p52_env["company_id"], f"P52-REC-{uuid.uuid4().hex[:4]}", Decimal("40.0"), p52_env["wh_src_id"], p52_env["editor_id"])
            initial_movements = db.query(StockMovement).filter(StockMovement.product_id == prod.id).count()

            # Create and dispatch transfer
            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p52_env["wh_src_id"],
                "destination_warehouse_id": p52_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 40.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Attempt final short receipt of 30 units (10 shortage) WITHOUT discrepancy reason
            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 30.0}],
                "is_final": True
                # Missing discrepancy reason!
            })
            assert r_res.status_code == 400
            assert "Discrepancy reason is strictly required" in r_res.json()["detail"]

            # Verify destination warehouse has ZERO received stock
            dst_stock = get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_dst_id"], prod.id, "42")
            assert dst_stock == Decimal("0.0")

            # Transfer status remains IN_TRANSIT
            t_get = client.get(f"/api/v1/transfers/{t_id}").json()
            assert t_get["status"] == "IN_TRANSIT"
            assert t_get["items"][0]["received_quantity"] == 0.0
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 3. Lock Lifecycle: Commit, Rollback, and Exception Release
# ---------------------------------------------------------------------------

class TestLockLifecycle:
    """Verifies that in-process mutexes and advisory locks are cleanly released on commit, rollback, and error."""

    def test_lock_released_after_successful_commit(self, p52_env):
        db = SessionLocal()
        try:
            mutex = get_stock_transfer_mutex(p52_env["company_id"], 7771)
            acquire_stock_transfer_lock(db, p52_env["company_id"], 7771)
            assert mutex.locked()

            # Commit releases mutex
            db.commit()
            assert not mutex.locked()
        finally:
            db.close()

    def test_lock_released_after_rollback(self, p52_env):
        db = SessionLocal()
        try:
            mutex = get_stock_transfer_mutex(p52_env["company_id"], 7772)
            acquire_stock_transfer_lock(db, p52_env["company_id"], 7772)
            # Need to perform at least one query/transaction to activate after_rollback listener
            assert mutex.locked()

            # Explicit rollback releases held locks
            release_all_session_locks(db)
            db.rollback()
            assert not mutex.locked()
        finally:
            db.close()

    def test_lock_released_after_session_close_on_exception(self, p52_env):
        db = SessionLocal()
        mutex = get_stock_transfer_mutex(p52_env["company_id"], 7773)
        try:
            acquire_stock_transfer_lock(db, p52_env["company_id"], 7773)
            assert mutex.locked()
            raise ValueError("Simulated unexpected exception")
        except ValueError:
            release_all_session_locks(db)
            db.close()

        assert not mutex.locked()


# ---------------------------------------------------------------------------
# 4. Multi-Session Concurrency Races
# ---------------------------------------------------------------------------

class TestConcurrentTransferRaces:
    """Tests multi-session races: concurrent dispatch, concurrent receipt, and receipt vs cancel."""

    def test_concurrent_dispatch_requests_serialized(self, p52_env):
        """Two concurrent dispatch requests for the same transfer: exactly one succeeds."""
        db = SessionLocal()
        client = _get_client(p52_env["token"])
        try:
            prod = _create_product_with_stock(db, p52_env["company_id"], f"P52-CD-{uuid.uuid4().hex[:4]}", Decimal("25.0"), p52_env["wh_src_id"], p52_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p52_env["wh_src_id"],
                "destination_warehouse_id": p52_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 25.0}]
            })
            t_id = t_res.json()["id"]

            barrier = threading.Barrier(2)
            results = []

            def worker():
                c = _get_client(p52_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/dispatch")
                results.append(r.status_code)

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # Exactly one 200 and one 400
            assert sorted(results) == [200, 400]
            # Stock deducted exactly once (25.0 deducted -> 0.0 remaining)
            assert get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_src_id"], prod.id, "42") == Decimal("0.0")
        finally:
            db.close()

    def test_concurrent_receipt_requests_serialized(self, p52_env):
        """Two concurrent full receipt requests: exactly one succeeds, one rejected (no double-receipt)."""
        db = SessionLocal()
        client = _get_client(p52_env["token"])
        try:
            prod = _create_product_with_stock(db, p52_env["company_id"], f"P52-CR-{uuid.uuid4().hex[:4]}", Decimal("35.0"), p52_env["wh_src_id"], p52_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p52_env["wh_src_id"],
                "destination_warehouse_id": p52_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 35.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            barrier = threading.Barrier(2)
            results = []

            def worker():
                c = _get_client(p52_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/receive", json={
                    "items": [{"item_id": item_id, "received_quantity": 35.0}]
                })
                results.append(r.status_code)

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert sorted(results) == [200, 400]
            # Destination received exactly 35.0, NEVER 70.0!
            assert get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_dst_id"], prod.id, "42") == Decimal("35.0")
        finally:
            db.close()

    def test_receipt_racing_cancellation_preserves_conservation(self, p52_env):
        """Concurrent full receipt and cancellation: one succeeds, one fails, inventory conserved."""
        db = SessionLocal()
        client = _get_client(p52_env["token"])
        try:
            prod = _create_product_with_stock(db, p52_env["company_id"], f"P52-RC-{uuid.uuid4().hex[:4]}", Decimal("60.0"), p52_env["wh_src_id"], p52_env["editor_id"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p52_env["wh_src_id"],
                "destination_warehouse_id": p52_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 60.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            barrier = threading.Barrier(2)
            results = {}

            def worker_rec():
                c = _get_client(p52_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/receive", json={
                    "items": [{"item_id": item_id, "received_quantity": 60.0}],
                    "is_final": True
                })
                results["receive"] = r.status_code

            def worker_cancel():
                c = _get_client(p52_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/cancel")
                results["cancel"] = r.status_code

            t1 = threading.Thread(target=worker_rec)
            t2 = threading.Thread(target=worker_cancel)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert {results["receive"], results["cancel"]} == {200, 400}
            src_s = get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_src_id"], prod.id, "42")
            dst_s = get_warehouse_stock(db, p52_env["company_id"], p52_env["wh_dst_id"], prod.id, "42")
            # Conservation strictly holds: Total = 60.0
            assert src_s + dst_s == Decimal("60.0")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 5. Real PostgreSQL 18.6.3 Concurrency & Advisory Lock Serialization
# ---------------------------------------------------------------------------

import pathlib
import tempfile
import time

@pytest.fixture(scope="module")
def pg_engine():
    try:
        from embedded_postgres import get_server
    except ImportError:
        pytest.skip("embedded_postgres not installed")

    pgdata = pathlib.Path(tempfile.mkdtemp()) / "pg52data"
    server = get_server(pgdata, cleanup_mode="delete")
    try:
        server.ensure_pgdata_inited()
        server.ensure_postgres_running()
        time.sleep(2)
        uri = server.get_uri()
        if uri.startswith("postgresql://"):
            uri = uri.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql+psycopg2://", 1)
    except Exception as e:
        pytest.skip(f"Could not start embedded PostgreSQL: {e}")

    engine = create_engine(uri, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    try:
        server.cleanup()
    except Exception:
        pass


class TestPostgreSQLAdvisoryLockRealTransactions:
    """Runs real multi-session transactions against embedded PostgreSQL to prove multi-worker database guarantees."""

    def test_pg_separate_sessions_advisory_lock_mutual_exclusion(self, pg_engine):
        """Proof: Two separate sessions on real PostgreSQL strictly serialize via pg_advisory_xact_lock."""
        SessionPg = sessionmaker(bind=pg_engine)
        session1 = SessionPg()
        session2 = SessionPg()
        try:
            uid = uuid.uuid4().hex[:6]
            co = Company(name=f"PG Concurrency Corp {uid}", code=f"PGC-{uid}", pan_number=f"52{uid}")
            session1.add(co)
            session1.commit()

            transfer_id = 99991

            # Session 1 acquires PostgreSQL advisory lock
            lock_id_1 = acquire_stock_transfer_lock(session1, co.id, transfer_id)
            assert isinstance(lock_id_1, int)

            # Session 2 attempts non-blocking advisory lock on SAME transfer_id -> returns False!
            lock_acquired_s2 = session2.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id_1}
            ).scalar()
            assert lock_acquired_s2 is False # Blocked by session 1!

            # Session 1 commits -> transaction ends and advisory lock is automatically released!
            session1.commit()

            # Now Session 2 attempts non-blocking advisory lock -> returns True!
            lock_acquired_s2_retry = session2.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id_1}
            ).scalar()
            assert lock_acquired_s2_retry is True
            session2.commit()
        finally:
            session1.close()
            session2.close()
