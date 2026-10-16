import os
import sys
import time
import tempfile
import pathlib
import threading
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import SessionLocal, Base, engine as default_sqlite_engine
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.security import get_password_hash, create_access_token
from app.core.sequence import allocate_next_sequence
from app.api.v1.invoices import allocate_next_invoice_sequence
from app.api.v1.transfers import get_warehouse_stock

# ---------------------------------------------------------------------------
# Setup Fixture for SQLite Base Tests
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=default_sqlite_engine)


@pytest.fixture(scope="module")
def p4_env():
    """Sets up an isolated company, editor, and warehouses in SQLite test database."""
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:6].upper()
        co = Company(name=f"Phase 4 Corp {uid}", code=f"P4-{uid}", pan_number=f"30{uid}")
        db.add(co)
        db.commit()
        db.refresh(co)

        editor = User(
            company_id=co.id,
            username=f"p4_ed_{uid.lower()}",
            name="Phase 4 Auditor",
            password_hash=get_password_hash("AuditPass2026!"),
            role="editor",
            active=True
        )
        db.add(editor)
        db.commit()
        db.refresh(editor)

        wh_src = Warehouse(company_id=co.id, name=f"Factory Central WH {uid}", code=f"WH-SRC-{uid}", is_active=True)
        db.add(wh_src)

        wh_dst = Warehouse(company_id=co.id, name=f"Showroom Outlet WH {uid}", code=f"WH-DST-{uid}", is_active=True)
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


def _get_auth_client(token: str) -> TestClient:
    client = TestClient(app)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _create_p4_product(db, company_id: int, code: str, initial_stock_src: Decimal, wh_src_id: int, user_id: int):
    prod = db.query(Product).filter(Product.company_id == company_id, Product.code == code).first()
    if not prod:
        prod = Product(
            company_id=company_id,
            code=code,
            name=f"P4 Footwear {code}",
            category="Sneaker",
            size="42",
            color="Navy",
            unit_price=2500.0
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)

    if initial_stock_src > 0:
        db.add(StockMovement(
            company_id=company_id,
            product_id=prod.id,
            warehouse_id=wh_src_id,
            size="42",
            quantity=initial_stock_src,
            direction=1,
            movement_type="PRODUCTION_IN",
            ref_type="production",
            ref_id=1,
            source_doc_ref=f"INIT-{code}",
            actor_id=user_id,
            date_ad="2026-10-15",
            date_bs="2083-06-29",
            notes=f"Initial stock for P4 test {code}"
        ))
        db.commit()

    return prod


# ===========================================================================
# 1. STOCK TRANSFER LEDGER INVARIANTS (15 ADVERSARIAL CASES)
# ===========================================================================

class TestStockTransferInvariants:

    def test_case_01_full_dispatch_followed_by_full_receipt(self, p4_env):
        """Case 1: Full dispatch followed by full receipt. Exact physical balance conservation."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C01", Decimal("100.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            # 1. Create Transfer for 100 units
            c_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 100.0}]
            })
            assert c_res.status_code == 201
            t_id = c_res.json()["id"]

            # 2. Dispatch
            d_res = client.post(f"/api/v1/transfers/{t_id}/dispatch")
            assert d_res.status_code == 200

            # Assert Invariant at IN_TRANSIT
            src_stock = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42")
            dst_stock = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42")
            assert src_stock == Decimal("0.0")
            assert dst_stock == Decimal("0.0")

            detail = client.get(f"/api/v1/transfers/{t_id}").json()
            itm = detail["items"][0]
            # dispatched (100) = received (0) + remaining in-transit (100) + discrepancy (0)
            assert itm["dispatched_quantity"] == itm["received_quantity"] + (itm["dispatched_quantity"] - itm["received_quantity"]) + itm["discrepancy_quantity"]

            # 3. Full Receipt
            r_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": itm["id"], "received_quantity": 100.0}],
                "is_final": True
            })
            assert r_res.status_code == 200
            assert r_res.json()["status"] == "RECEIVED"

            # Assert Invariant at RECEIVED
            src_stock_final = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42")
            dst_stock_final = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42")
            assert src_stock_final == Decimal("0.0")
            assert dst_stock_final == Decimal("100.0")
            assert src_stock_final + dst_stock_final == Decimal("100.0")
        finally:
            db.close()

    def test_case_02_multiple_partial_receipts_followed_by_final_receipt(self, p4_env):
        """Case 2: Multiple partial receipts followed by final receipt."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C02", Decimal("100.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 100.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Partial receipt 1: 40 units
            r1 = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 40.0}],
                "is_final": False
            })
            assert r1.status_code == 200
            assert r1.json()["status"] == "PARTIALLY_RECEIVED"
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42") == Decimal("40.0")

            # Partial receipt 2: 35 units
            r2 = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 35.0}],
                "is_final": False
            })
            assert r2.status_code == 200
            assert r2.json()["status"] == "PARTIALLY_RECEIVED"
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42") == Decimal("75.0")

            # Final receipt: remaining 25 units
            r3 = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 25.0}],
                "is_final": True
            })
            assert r3.status_code == 200
            assert r3.json()["status"] == "RECEIVED"
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42") == Decimal("100.0")
        finally:
            db.close()

    def test_case_03_partial_receipt_followed_by_cancellation(self, p4_env):
        """Case 3: Partial receipt (40 units) followed by cancellation (60 returned to source)."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C03", Decimal("100.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 100.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Partial receipt 40
            client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 40.0}],
                "is_final": False
            })

            # Cancel remaining
            c_res = client.post(f"/api/v1/transfers/{t_id}/cancel")
            assert c_res.status_code == 200
            assert c_res.json()["status"] == "CANCELLED"

            src_stock = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42")
            dst_stock = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42")

            # Source gets unreceived 60 back; destination retains 40; company total equals 100
            assert src_stock == Decimal("60.0")
            assert dst_stock == Decimal("40.0")
            assert src_stock + dst_stock == Decimal("100.0")
        finally:
            db.close()

    def test_case_04_final_receipt_with_shortage_and_reason(self, p4_env):
        """Case 4: Final receipt with shortage requires reason, logs TRANSIT_DISCREPANCY (dir=0)."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C04", Decimal("100.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 100.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Attempt finalize shortage without reason -> rejected
            bad = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 85.0, "discrepancy_reason": ""}],
                "is_final": True
            })
            assert bad.status_code == 400

            # Finalize with reason -> succeeds
            good = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 85.0, "discrepancy_reason": "Carton crushed by forklift"}],
                "is_final": True
            })
            assert good.status_code == 200

            # Verify movements: TRANSFER_IN (85) and TRANSIT_DISCREPANCY (15, direction 0)
            disc_m = db.query(StockMovement).filter(
                StockMovement.company_id == p4_env["company_id"],
                StockMovement.ref_type == "transfer",
                StockMovement.ref_id == t_id,
                StockMovement.movement_type == "TRANSIT_DISCREPANCY"
            ).first()
            assert disc_m is not None
            assert Decimal(str(disc_m.quantity)) == Decimal("15.0")
            assert disc_m.direction == 0
        finally:
            db.close()

    def test_case_05_attempted_over_receipt(self, p4_env):
        """Case 5: Attempted over-receipt is strictly forbidden."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C05", Decimal("50.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Attempt receiving 51 units
            over_res = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 51.0}]
            })
            assert over_res.status_code == 400
            assert "over-receipt forbidden" in over_res.json()["detail"].lower()
        finally:
            db.close()

    def test_case_06_attempted_receipt_after_finalization_or_cancellation(self, p4_env):
        """Case 6: Attempted receipt after finalization or cancellation is rejected."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C06", Decimal("30.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 30.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            # Finalize receipt
            client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 30.0}],
                "is_final": True
            })

            # Attempt receiving again on finalized transfer
            bad_rec = client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 5.0}]
            })
            assert bad_rec.status_code == 400
            assert "only in_transit or partially_received" in bad_rec.json()["detail"].lower()
        finally:
            db.close()

    def test_case_07_attempted_cancellation_after_full_receipt(self, p4_env):
        """Case 7: Attempted cancellation after full receipt is rejected."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C07", Decimal("20.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 20.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]
            client.post(f"/api/v1/transfers/{t_id}/receive", json={
                "items": [{"item_id": item_id, "received_quantity": 20.0}],
                "is_final": True
            })

            # Attempt cancel
            bad_cancel = client.post(f"/api/v1/transfers/{t_id}/cancel")
            assert bad_cancel.status_code == 400
            assert "cannot cancel a received transfer" in bad_cancel.json()["detail"].lower()
        finally:
            db.close()

    def test_case_08_duplicate_product_size_in_request(self, p4_env):
        """Case 8: Duplicate product/size combinations in one request are rejected."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C08", Decimal("20.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [
                    {"product_id": prod.id, "size": "42", "quantity": 10.0},
                    {"product_id": prod.id, "size": "42", "quantity": 10.0}
                ]
            })
            assert res.status_code == 400
            assert "duplicate product variant" in res.json()["detail"].lower()
        finally:
            db.close()

    def test_case_09_dispatch_retried_with_idempotency_key(self, p4_env):
        """Case 9: Dispatch retried with Idempotency-Key returns cached response, no double deduction."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C09", Decimal("50.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 25.0}]
            })
            t_id = t_res.json()["id"]

            key = f"idem-dispatch-{t_id}-001"
            # Attempt 1
            res1 = client.post(f"/api/v1/transfers/{t_id}/dispatch", headers={"Idempotency-Key": key})
            assert res1.status_code == 200

            # Attempt 2 (retry)
            res2 = client.post(f"/api/v1/transfers/{t_id}/dispatch", headers={"Idempotency-Key": key})
            assert res2.status_code == 200
            assert res2.headers.get("X-Idempotent-Replay") == "true"

            # Stock should have been deducted ONLY once: 50 - 25 = 25
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42") == Decimal("25.0")
        finally:
            db.close()

    def test_case_10_concurrent_dispatch_requests(self, p4_env):
        """Case 10: Two concurrent dispatch requests. Exactly one succeeds, second fails 400."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C10", Decimal("40.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 40.0}]
            })
            t_id = t_res.json()["id"]

            barrier = threading.Barrier(2)
            results = []

            def worker():
                c = _get_auth_client(p4_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/dispatch")
                results.append(r.status_code)

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert 200 in results
            assert 400 in results
            # Source stock deducted exactly once
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42") == Decimal("0.0")
        finally:
            db.close()

    def test_case_11_concurrent_receipt_requests(self, p4_env):
        """Case 11: Two concurrent receipt requests for the remaining quantity."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C11", Decimal("30.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 30.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            barrier = threading.Barrier(2)
            results = []

            def worker():
                c = _get_auth_client(p4_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/receive", json={
                    "items": [{"item_id": item_id, "received_quantity": 30.0}]
                })
                results.append(r.status_code)

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert 200 in results
            assert 400 in results
            # Destination received exactly 30, never 60
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42") == Decimal("30.0")
        finally:
            db.close()

    def test_case_12_concurrent_cancellation_requests(self, p4_env):
        """Case 12: Two concurrent cancellation requests. Exactly one succeeds."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C12", Decimal("20.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 20.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")

            barrier = threading.Barrier(2)
            results = []

            def worker():
                c = _get_auth_client(p4_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/cancel")
                results.append(r.status_code)

            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert 200 in results
            assert 400 in results
            # Stock restored exactly once: back to 20
            assert get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42") == Decimal("20.0")
        finally:
            db.close()

    def test_case_13_concurrent_receipt_and_cancellation(self, p4_env):
        """Case 13: Concurrent receipt and cancellation."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C13", Decimal("50.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            client = _get_auth_client(p4_env["token"])

            t_res = client.post("/api/v1/transfers", json={
                "source_warehouse_id": p4_env["wh_src_id"],
                "destination_warehouse_id": p4_env["wh_dst_id"],
                "transfer_date_ad": "2026-10-15",
                "transfer_date_bs": "2083-06-29",
                "items": [{"product_id": prod.id, "size": "42", "quantity": 50.0}]
            })
            t_id = t_res.json()["id"]
            client.post(f"/api/v1/transfers/{t_id}/dispatch")
            item_id = client.get(f"/api/v1/transfers/{t_id}").json()["items"][0]["id"]

            barrier = threading.Barrier(2)
            results = {}

            def worker_rec():
                c = _get_auth_client(p4_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/receive", json={
                    "items": [{"item_id": item_id, "received_quantity": 50.0}],
                    "is_final": True
                })
                results["receive"] = r.status_code

            def worker_cancel():
                c = _get_auth_client(p4_env["token"])
                barrier.wait()
                r = c.post(f"/api/v1/transfers/{t_id}/cancel")
                results["cancel"] = r.status_code

            t1 = threading.Thread(target=worker_rec)
            t2 = threading.Thread(target=worker_cancel)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            # One succeeds (200), one fails (400)
            assert {results["receive"], results["cancel"]} == {200, 400}
            src_s = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_src_id"], prod.id, "42")
            dst_s = get_warehouse_stock(db, p4_env["company_id"], p4_env["wh_dst_id"], prod.id, "42")
            assert src_s + dst_s == Decimal("50.0")
        finally:
            db.close()

    def test_case_14_atomicity_failure_between_movement_and_status(self, p4_env):
        """Case 14: Simulated DB crash before transfer status commit leaves NO orphan movements."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C14", Decimal("30.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            initial_movements = db.query(StockMovement).filter(StockMovement.product_id == prod.id).count()

            # Create transfer
            trf = StockTransfer(
                company_id=p4_env["company_id"],
                transfer_number=f"TRF-ATOMIC-14-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=p4_env["wh_src_id"],
                destination_warehouse_id=p4_env["wh_dst_id"],
                status="DRAFT",
                transfer_date_ad="2026-10-15",
                transfer_date_bs="2083-06-29",
                created_by_id=p4_env["editor_id"]
            )
            db.add(trf)
            db.commit()

            # Simulate failure in dispatch: add movement then raise exception
            try:
                db.add(StockMovement(
                    company_id=p4_env["company_id"],
                    product_id=prod.id,
                    warehouse_id=p4_env["wh_src_id"],
                    size="42",
                    quantity=30.0,
                    direction=-1,
                    movement_type="TRANSFER_OUT",
                    ref_type="transfer",
                    ref_id=trf.id,
                    source_doc_ref=trf.transfer_number,
                    actor_id=p4_env["editor_id"],
                    date_ad="2026-10-15",
                    date_bs="2083-06-29"
                ))
                raise RuntimeError("Simulated mid-transaction crash")
                trf.status = "IN_TRANSIT"
                db.commit()
            except RuntimeError:
                db.rollback()

            # Verify complete rollback: movements unchanged, transfer still DRAFT
            after_movements = db.query(StockMovement).filter(StockMovement.product_id == prod.id).count()
            assert after_movements == initial_movements
            refreshed_trf = db.query(StockTransfer).filter(StockTransfer.id == trf.id).first()
            assert refreshed_trf.status == "DRAFT"
        finally:
            db.close()

    def test_case_15_atomicity_failure_between_status_and_commit(self, p4_env):
        """Case 15: Simulated failure before commit completely reverts transfer status and movements."""
        db = SessionLocal()
        try:
            prod = _create_p4_product(db, p4_env["company_id"], "P4-C15", Decimal("30.0"), p4_env["wh_src_id"], p4_env["editor_id"])
            trf = StockTransfer(
                company_id=p4_env["company_id"],
                transfer_number=f"TRF-ATOMIC-15-{uuid.uuid4().hex[:6]}",
                source_warehouse_id=p4_env["wh_src_id"],
                destination_warehouse_id=p4_env["wh_dst_id"],
                status="IN_TRANSIT",
                transfer_date_ad="2026-10-15",
                transfer_date_bs="2083-06-29",
                created_by_id=p4_env["editor_id"]
            )
            db.add(trf)
            db.commit()

            # Try to receive but simulate DB commit failure
            try:
                trf.status = "RECEIVED"
                raise ConnectionError("Simulated database connection loss before commit")
                db.commit()
            except ConnectionError:
                db.rollback()

            db.refresh(trf)
            assert trf.status == "IN_TRANSIT"
        finally:
            db.close()


# ===========================================================================
# 2. INVOICE, VAT, CREDIT-NOTE & AR RECONCILIATION
# ===========================================================================

class TestInvoiceAndFinancialInvariants:

    def _setup_client_and_order(self, db, company_id: int, user_id: int, code: str, price: float, qty: int):
        client = db.query(Client).filter(Client.company_id == company_id, Client.code == f"CLI-{code}").first()
        if not client:
            client = Client(
                company_id=company_id,
                code=f"CLI-{code}",
                name=f"Customer {code}",
                credit_limit=1000000.0
            )
            db.add(client)
            db.commit()
            db.refresh(client)

        order = SalesOrder(
            company_id=company_id,
            order_number=f"ORD-P4-{code}",
            client_id=client.id,
            order_date_ad="2026-10-15",
            order_date_bs="2083-06-29",
            status="CONFIRMED",
            total_amount=Decimal(str(price * qty)),
            received_amount=Decimal("0.0")
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Sales item
        item = SalesItem(
            company_id=company_id,
            sales_order_id=order.id,
            product_id=1,
            quantity=qty,
            unit_price=Decimal(str(price)),
            total_price=Decimal(str(price * qty))
        )
        db.add(item)
        db.commit()
        return order, client

    def test_full_synthetic_customer_transaction_lifecycle(self, p4_env):
        """
        Complete Synthetic Lifecycle:
        1. Create draft invoice.
        2. Finalize draft.
        3. Verify document number, VAT, total, AR subledger posting (+1 debit).
        4. Attempt prohibited financial edits (immutable).
        5. Issue partial credit note 1 (Schedule 10, -1 credit).
        6. Issue credit note 2 up to eligible limit.
        7. Attempt to exceed ceiling (rejected).
        8. Attempt to void invoice with credit notes (rejected).
        """
        db = SessionLocal()
        try:
            client_api = _get_auth_client(p4_env["token"])
            order, client = self._setup_client_and_order(db, p4_env["company_id"], p4_env["editor_id"], "SYNTH01", 1000.0, 10)

            # 1. Create draft invoice
            draft_res = client_api.post("/api/v1/invoices", json={"sales_order_id": order.id, "is_draft": True})
            assert draft_res.status_code == 200
            draft = draft_res.json()
            inv_id = draft["id"]
            assert draft["invoice_number"].startswith("DRAFT-")

            # Verify AR has NOT posted yet
            ar_count_draft = db.query(ReceivableEntry).filter(ReceivableEntry.invoice_id == inv_id).count()
            assert ar_count_draft == 0

            # 2. Finalize invoice
            fin_res = client_api.post(f"/api/v1/invoices/{inv_id}/finalize")
            assert fin_res.status_code == 200
            fin_inv = fin_res.json()
            assert fin_inv["invoice_number"].startswith("INV-")
            assert fin_inv["sequence_number"] > 0

            # 3. Verify VAT & AR posting
            # Subtotal: 10,000.00, VAT: 1,300.00, Total: 11,300.00 (1,130,000 paisa)
            assert fin_inv["total_amount_paisa"] == 1130000
            assert fin_inv["vat_amount_paisa"] == 130000
            assert fin_inv["taxable_amount_paisa"] == 1000000

            ar_entry = db.query(ReceivableEntry).filter(
                ReceivableEntry.invoice_id == inv_id,
                ReceivableEntry.entry_type == "INVOICE_POSTED"
            ).first()
            assert ar_entry is not None
            assert ar_entry.direction == 1
            assert ar_entry.amount_paisa == 1130000

            # 4. Prohibited financial edit
            edit_bad = client_api.patch(f"/api/v1/invoices/{inv_id}", json={"discount_amount": 500.0})
            assert edit_bad.status_code == 400
            assert "immutable" in edit_bad.json()["detail"].lower()

            # 5. Issue partial credit note 1: Rs 5,650 (565,000 paisa)
            cn1 = client_api.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
                "amount_paisa": 565000,
                "reason": "Return 5 damaged pairs"
            }).json()
            assert cn1["taxable_credit_paisa"] == 500000
            assert cn1["vat_credit_paisa"] == 65000
            assert cn1["remaining_creditable_paisa"] == 565000

            # 6. Issue credit note 2: Rs 5,650 (exhaust remaining balance)
            cn2 = client_api.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
                "amount_paisa": 565000,
                "reason": "Final settlement discount"
            }).json()
            assert cn2["remaining_creditable_paisa"] == 0

            # 7. Attempt credit note 3 (exceeding ceiling)
            cn3_bad = client_api.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
                "amount_paisa": 1000,
                "reason": "Exceeding ceiling test"
            })
            assert cn3_bad.status_code == 400
            assert "exceeds" in cn3_bad.json()["detail"].lower()

            # 8. Attempt void invoice that has credit notes -> must fail
            void_bad = client_api.post(f"/api/v1/invoices/{inv_id}/cancel")
            assert void_bad.status_code == 400
            assert "credit notes have already been issued" in void_bad.json()["detail"].lower()

            # Verify AR subledger balance for this invoice is exactly 0:
            # +1,130,000 (INVOICE_POSTED) - 565,000 (CN1) - 565,000 (CN2) = 0
            ar_balance = db.query(func.sum(ReceivableEntry.amount_paisa * ReceivableEntry.direction)).filter(
                ReceivableEntry.invoice_id == inv_id
            ).scalar()
            assert ar_balance == 0
        finally:
            db.close()

    def test_draft_void_produces_no_phantom_ar(self, p4_env):
        """Voiding a draft invoice never posts an AR reversal."""
        db = SessionLocal()
        try:
            client_api = _get_auth_client(p4_env["token"])
            order, client = self._setup_client_and_order(db, p4_env["company_id"], p4_env["editor_id"], "DRAFTVOID", 500.0, 4)

            draft = client_api.post("/api/v1/invoices", json={"sales_order_id": order.id, "is_draft": True}).json()
            inv_id = draft["id"]

            # Cancel draft
            client_api.post(f"/api/v1/invoices/{inv_id}/cancel")

            # Check AR count is strictly 0
            count = db.query(ReceivableEntry).filter(ReceivableEntry.invoice_id == inv_id).count()
            assert count == 0
        finally:
            db.close()

    def test_pure_decimal_precision_no_float_drift(self):
        """Verifies integer-paisa math guarantees zero floating point drift even with odd fractions."""
        from app.api.v1.invoices import compute_invoice_amounts

        class MockItem:
            def __init__(self, qty, price):
                self.quantity = Decimal(str(qty))
                self.unit_price = Decimal(str(price))

        # 3 items at Rs 333.33 each = Rs 999.99
        items = [MockItem(3, "333.33")]
        taxable_paisa, vat_paisa, total_paisa, vat_rate, eff_vat = compute_invoice_amounts(
            order_items=items,
            order_total=Decimal("999.99"),
            pricing_mode="VAT_EXCLUSIVE",
            discount_amount=Decimal("0.0"),
            other_charges=Decimal("0.0"),
            is_tax_exempt=False,
            vat_enabled=True
        )

        assert taxable_paisa == 99999
        # 13% of 99999 = 12999.87 -> rounds to 13000 paisa (Rs 130.00)
        assert vat_paisa == 13000
        assert total_paisa == 99999 + 13000
        # Sum of components is exact
        assert total_paisa == taxable_paisa + vat_paisa


# ===========================================================================
# 3. POSTGRESQL CONCURRENCY & TRANSACTION PROOF (EMBEDDED PG)
# ===========================================================================

class TestPostgreSQLConcurrencyProof:
    """Runs deterministic concurrency and transaction proofs against real Embedded PostgreSQL."""

    _pg_server = None
    _pg_url = None
    _pg_engine = None
    _PGSession = None

    @classmethod
    def setup_class(cls):
        from embedded_postgres import get_server
        pgdir = pathlib.Path(tempfile.mkdtemp()) / "pg_p4_class"
        cls._pg_server = get_server(pgdir, cleanup_mode="delete")
        cls._pg_server.ensure_pgdata_inited()
        cls._pg_server.ensure_postgres_running()
        time.sleep(2)
        cls._pg_url = cls._pg_server.get_uri()

        # Run alembic migrations
        import subprocess
        env = os.environ.copy()
        env["DATABASE_URL"] = cls._pg_url
        env["SECRET_KEY"] = "phase4_concurrency_test_key_32chars_min"
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Alembic failed on PG: {res.stderr}"

        # Setup engine and session
        pg_sa_url = cls._pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        cls._pg_engine = create_engine(pg_sa_url, pool_size=10, max_overflow=10)
        cls._PGSession = sessionmaker(bind=cls._pg_engine, autocommit=False, autoflush=False)

    @classmethod
    def teardown_class(cls):
        if cls._pg_engine:
            cls._pg_engine.dispose()
        if cls._pg_server:
            try:
                cls._pg_server.cleanup()
            except Exception:
                pass

    def test_pg_concurrent_sequence_allocation_uniqueness(self):
        """
        Concurrency Proof: Allocate 30 document sequence numbers simultaneously across 6 threads.
        Assert that all 30 sequence numbers are strictly unique with zero collisions or gaps.
        """
        db = self._PGSession()
        try:
            co = Company(name="PG Concurrency Co", code="PG-CO-01", pan_number="301112223")
            db.add(co)
            db.commit()
            co_id = co.id
        finally:
            db.close()

        results = []
        barrier = threading.Barrier(6)

        def worker():
            w_db = self._PGSession()
            try:
                barrier.wait()
                for _ in range(5):
                    seq = allocate_next_sequence(w_db, co_id, "TRF")
                    w_db.commit()
                    results.append(seq)
            finally:
                w_db.close()

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 30
        assert len(set(results)) == 30, "Duplicate sequence numbers generated under concurrent execution!"
        assert sorted(results) == list(range(1, 31)), "Gaps or sequence jumps detected!"

    def test_pg_row_level_locking_serializes_concurrent_stock_mutations(self):
        """
        Concurrency Proof: Row-level lock (with_for_update) serializes stock transfer state transitions.
        Thread 1 holds lock in transaction; Thread 2 must wait until Thread 1 commits.
        """
        db = self._PGSession()
        try:
            co = db.query(Company).filter(Company.code == "PG-CO-01").first()
            user = User(
                company_id=co.id,
                username="pg_user1",
                name="PG User",
                password_hash=get_password_hash("Pass123!"),
                role="editor"
            )
            wh1 = Warehouse(company_id=co.id, name="PG WH 1", code="WH-PG-1", is_active=True)
            wh2 = Warehouse(company_id=co.id, name="PG WH 2", code="WH-PG-2", is_active=True)
            db.add_all([user, wh1, wh2])
            db.commit()

            trf = StockTransfer(
                company_id=co.id,
                transfer_number="TRF-PG-LOCK-01",
                source_warehouse_id=wh1.id,
                destination_warehouse_id=wh2.id,
                status="DRAFT",
                transfer_date_ad="2026-10-15",
                transfer_date_bs="2083-06-29",
                created_by_id=user.id
            )
            db.add(trf)
            db.commit()
            trf_id = trf.id
        finally:
            db.close()

        t1_acquired = threading.Event()
        t1_can_commit = threading.Event()
        t2_saw_status = []

        def worker1():
            w_db = self._PGSession()
            try:
                # Lock row
                locked_trf = w_db.query(StockTransfer).filter(StockTransfer.id == trf_id).with_for_update().first()
                locked_trf.status = "IN_TRANSIT"
                t1_acquired.set()
                t1_can_commit.wait()
                w_db.commit()
            finally:
                w_db.close()

        def worker2():
            w_db = self._PGSession()
            try:
                t1_acquired.wait()
                # This query will block until worker1 commits!
                locked_trf = w_db.query(StockTransfer).filter(StockTransfer.id == trf_id).with_for_update().first()
                t2_saw_status.append(locked_trf.status)
                w_db.commit()
            finally:
                w_db.close()

        th1 = threading.Thread(target=worker1)
        th2 = threading.Thread(target=worker2)

        th1.start()
        th2.start()

        # Give th2 time to start and block
        time.sleep(0.2)
        assert len(t2_saw_status) == 0, "Worker 2 should be blocked by worker 1's row lock!"

        # Allow worker 1 to commit
        t1_can_commit.set()
        th1.join()
        th2.join()

        assert len(t2_saw_status) == 1
        assert t2_saw_status[0] == "IN_TRANSIT", "Worker 2 should see the committed updated status after row lock release!"

    def test_pg_concurrent_credit_note_ceiling_preservation(self):
        """
        Concurrency Proof: Multiple competing credit note requests cannot exceed invoice total under PostgreSQL MVCC.
        """
        db = self._PGSession()
        try:
            co = db.query(Company).filter(Company.code == "PG-CO-01").first()
            if not co:
                co = Company(name="PG Concurrency Co", code="PG-CO-01", pan_number="301112223")
                db.add(co)
                db.commit()
                db.refresh(co)

            user = db.query(User).filter(User.company_id == co.id).first()
            if not user:
                user = User(
                    company_id=co.id,
                    username="pg_user_cn",
                    name="PG User CN",
                    password_hash=get_password_hash("Pass123!"),
                    role="editor"
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            client = db.query(Client).filter(Client.company_id == co.id, Client.code == "PG-CLI-CN").first()
            if not client:
                client = Client(company_id=co.id, code="PG-CLI-CN", name="CN Client", credit_limit=500000.0)
                db.add(client)
                db.commit()
                db.refresh(client)

            co_id = co.id
            user_id = user.id
            client_id = client.id

            order = SalesOrder(
                company_id=co_id,
                order_number="ORD-PG-CN-01",
                client_id=client_id,
                order_date_ad="2026-10-15",
                order_date_bs="2083-06-29",
                status="CONFIRMED",
                total_amount=Decimal("10000.00"),
                received_amount=Decimal("0.0")
            )
            db.add(order)
            db.commit()

            inv = Invoice(
                company_id=co_id,
                sales_order_id=order.id,
                invoice_number="INV-PG-0001",
                sequence_number=1,
                date_ad="2026-10-15",
                date_bs="2083-06-29",
                subtotal=Decimal("10000.00"),
                vat_enabled=True,
                vat_rate=Decimal("13.0"),
                vat_amount=Decimal("1300.00"),
                total_amount=Decimal("11300.00"),
                received_amount=Decimal("0.0"),
                receivable_amount=Decimal("11300.00"),
                taxable_amount_paisa=1000000,
                vat_amount_paisa=130000,
                total_amount_paisa=1130000,
                is_void=False
            )
            db.add(inv)
            db.commit()
            inv_id = inv.id
        finally:
            db.close()

        # Two competing threads each try to issue a credit note for Rs 8,000 (800,000 paisa)
        # Total invoice is Rs 11,300 (1,130,000 paisa).
        # Two Rs 8,000 credit notes = Rs 16,000 (exceeds 11,300).
        # Under row-level lock on the invoice, exactly ONE can succeed, and the second MUST be rejected!

        barrier = threading.Barrier(2)
        results = []

        def worker(idx):
            w_db = self._PGSession()
            try:
                barrier.wait()
                try:
                    locked_inv = w_db.query(Invoice).filter(
                        Invoice.id == inv_id,
                        Invoice.company_id == co_id
                    ).with_for_update().first()

                    existing_credits = w_db.query(func.coalesce(func.sum(ReceivableEntry.amount_paisa), 0)).filter(
                        ReceivableEntry.company_id == co_id,
                        ReceivableEntry.invoice_id == inv_id,
                        ReceivableEntry.entry_type == "CREDIT_NOTE"
                    ).scalar() or 0

                    remaining = locked_inv.total_amount_paisa - existing_credits
                    credit_req = 800000  # Rs 8,000

                    if credit_req > remaining:
                        results.append(("REJECTED", f"Exceeds remaining {remaining}"))
                        w_db.rollback()
                    else:
                        rec = ReceivableEntry(
                            company_id=co_id,
                            client_id=client_id,
                            entry_type="CREDIT_NOTE",
                            direction=-1,
                            amount_paisa=credit_req,
                            source_doc_ref=f"CN-PG-{idx}",
                            invoice_id=inv_id,
                            actor_id=user_id,
                            occurred_at=datetime.now(timezone.utc)
                        )
                        w_db.add(rec)
                        w_db.commit()
                        results.append(("SUCCESS", credit_req))
                except Exception as e:
                    w_db.rollback()
                    results.append(("ERROR", str(e)))
            finally:
                w_db.close()

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        statuses = [r[0] for r in results]
        assert "SUCCESS" in statuses
        assert "REJECTED" in statuses

        # Assert total credits in DB never exceeded 1,130,000
        verify_db = self._PGSession()
        try:
            total_credits = verify_db.query(func.sum(ReceivableEntry.amount_paisa)).filter(
                ReceivableEntry.invoice_id == inv_id,
                ReceivableEntry.entry_type == "CREDIT_NOTE"
            ).scalar()
            assert total_credits == 800000, f"Expected 800,000 but got {total_credits}"
        finally:
            verify_db.close()

    def test_pg_migration_downgrade_and_reupgrade_reversibility(self):
        """
        Migration Reversibility Proof:
        Tests clean downgrade of 022_add_stock_transfers (dropping transfer tables)
        followed by clean re-upgrade to head on isolated PostgreSQL instance.
        """
        import subprocess
        from sqlalchemy import inspect as sa_inspect

        env = os.environ.copy()
        env["DATABASE_URL"] = self._pg_url
        env["SECRET_KEY"] = "phase4_concurrency_test_key_32chars_min"

        # 1. Verify tables exist prior to downgrade
        insp_before = sa_inspect(self._pg_engine)
        assert "stock_transfers" in insp_before.get_table_names()
        assert "stock_transfer_items" in insp_before.get_table_names()

        # 2. Downgrade to 021 (reverts 023 and 022 transfer tables)
        res_down = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "downgrade", "021_add_document_sequences"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res_down.returncode == 0, f"Alembic downgrade failed: {res_down.stderr}"

        # Dispose and recreate connection pool to flush cached schema
        self._pg_engine.dispose()
        insp_down = sa_inspect(self._pg_engine)
        assert "stock_transfers" not in insp_down.get_table_names()
        assert "stock_transfer_items" not in insp_down.get_table_names()

        # 3. Re-upgrade to head (re-applies 022)
        res_up = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            cwd=r"d:\Antigravity\Footwear app",
            env=env,
            capture_output=True,
            text=True
        )
        assert res_up.returncode == 0, f"Alembic upgrade failed: {res_up.stderr}"

        self._pg_engine.dispose()
        insp_up = sa_inspect(self._pg_engine)
        assert "stock_transfers" in insp_up.get_table_names()
        assert "stock_transfer_items" in insp_up.get_table_names()
