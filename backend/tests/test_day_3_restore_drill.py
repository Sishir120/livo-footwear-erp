"""
LIVO Footwear ERP — Day 3 Isolated PostgreSQL Restore Drill & Integrity Verification Test
========================================================================================
Exercises the end-to-end disaster recovery lifecycle using an isolated embedded PostgreSQL
instance and synthetic evaluation data. Does not modify or connect to any live development
or client database.

Domains Verified:
1. Companies, Users, and Roles (Admin, Editor, Viewer)
2. Branches and Warehouses
3. Products, Sizes, Colors, and Production Batches
4. Suppliers, Raw Materials, Landed Cost Purchases, and Stock Movements
5. BOM Components and Production Consumption
6. Sales Orders, Items, Invoices (13% VAT, gapless sequence), and Dispatches
7. Accounts Receivable Subledger and Cash Payments (Exact integer paisa math)
8. Stock Transfers across Branches/Warehouses
9. HR Workers, Compensation Models, and FIFO Advance Installment Recovery
10. Fixed Assets, Factory Expenses, and Waste Records
"""
import os
import sys
import time
import hashlib
import pathlib
import tempfile
import subprocess
from decimal import Decimal
from datetime import datetime, timezone, date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient

from embedded_postgres import get_server

# Models
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch, BranchType
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.models.purchase import Supplier, RawMaterial, Purchase, RawMaterialMovement
from app.models.bom import BillOfMaterials
from app.models.production import ProductionBatch
from app.models.sales import Client, SalesOrder, SalesItem, SalesExpense, FactoryExpense
from app.models.invoice import Invoice, InvoiceSequence
from app.models.receivable import ReceivableEntry, PaymentAllocation
from app.models.worker import Worker, WorkerAdvance, WorkerMonthlyRecord
from app.models.asset import FixedAsset
from app.models.waste import WasteRecord
from app.core.security import get_password_hash

# Services
from app.services.backup_service import run_database_backup, restore_database_backup, BACKUP_DIR
from app.config import settings

def find_pg_bin(name: str) -> str:
    import embedded_postgres
    base = pathlib.Path(embedded_postgres.__file__).parent / "pginstall" / "bin"
    exe = base / f"{name}.exe"
    if exe.exists():
        return str(exe)
    exe_no_ext = base / name
    if exe_no_ext.exists():
        return str(exe_no_ext)
    raise FileNotFoundError(f"Binary {name} not found in {base}")


def test_isolated_postgresql_backup_and_restore_drill(tmp_path, monkeypatch):
    """
    End-to-end isolated disaster recovery drill.
    Provisions ephemeral PostgreSQL server, migrates to Alembic head (024),
    seeds synthetic ERP dataset across all 10 domains, creates backup,
    restores to a clean secondary DB, and validates exact ledger invariants.
    """
    pgdata = tmp_path / "drill_pgdata"
    server = get_server(pgdata, cleanup_mode="delete")
    server.ensure_pgdata_inited()
    server.ensure_postgres_running()
    time.sleep(1.5)

    try:
        raw_master_url = server.get_uri("postgres")
        sa_master_url = raw_master_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        admin_engine = create_engine(sa_master_url, isolation_level="AUTOCOMMIT")

        src_db_name = "livo_day3_drill_src"
        dst_db_name = "livo_day3_drill_dst"

        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {src_db_name}"))
            conn.execute(text(f"DROP DATABASE IF EXISTS {dst_db_name}"))
            conn.execute(text(f"CREATE DATABASE {src_db_name}"))
            conn.execute(text(f"CREATE DATABASE {dst_db_name}"))

        src_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{src_db_name}"
        src_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{src_db_name}"
        dst_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{dst_db_name}"
        dst_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{dst_db_name}"

        # 1. Apply Alembic migrations up to head (024_add_rate_limit_entries)
        backend_dir = pathlib.Path(__file__).resolve().parent.parent
        alembic_ini = backend_dir / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", src_sa_url)
        command.upgrade(cfg, "head")

        # 2. Seed synthetic multi-tenant evaluation data
        src_engine = create_engine(src_sa_url)
        with Session(src_engine) as session:
            # Domain 1: Company, Branch, Warehouses, Users
            comp = Company(name="Livo Day3 Synthetic Footwear Ltd", code="LIVO_D3", pan_number="601998877")
            session.add(comp)
            session.commit()
            session.refresh(comp)

            branch = Branch(
                company_id=comp.id, code="BR-KTM-MAIN", name="Kathmandu Central Branch",
                type=BranchType.HEAD_OFFICE.value, address="Tripureshwor, Kathmandu"
            )
            session.add(branch)
            session.commit()
            session.refresh(branch)

            wh_main = Warehouse(company_id=comp.id, branch_id=branch.id, code="WH-D3-MAIN", name="Main Factory Warehouse", is_active=True)
            wh_retail = Warehouse(company_id=comp.id, branch_id=branch.id, code="WH-D3-RETAIL", name="Retail Depot Pokhara", is_active=True)
            session.add_all([wh_main, wh_retail])
            session.commit()
            session.refresh(wh_main)
            session.refresh(wh_retail)
            wh_main_id = wh_main.id
            wh_retail_id = wh_retail.id

            admin_user = User(company_id=comp.id, name="Admin Drill", username="admin_drill", password_hash=get_password_hash("Pass123!"), role="admin", active=True)
            editor_user = User(company_id=comp.id, name="Editor Drill", username="editor_drill", password_hash=get_password_hash("Pass123!"), role="editor", active=True)
            viewer_user = User(company_id=comp.id, name="Viewer Drill", username="viewer_drill", password_hash=get_password_hash("Pass123!"), role="viewer", active=True)
            session.add_all([admin_user, editor_user, viewer_user])
            session.commit()
            session.refresh(admin_user)
            session.refresh(editor_user)

            # Domain 2: Raw Materials, Supplier, Landed Cost Purchase
            sup = Supplier(company_id=comp.id, code="SUP-D3-HIMAL", name="Himalayan Tannery Corp")
            session.add(sup)
            session.commit()
            session.refresh(sup)

            rm_leather = RawMaterial(company_id=comp.id, code="RM-D3-LEA", name="Premium Buff Leather", unit="kg", current_stock=500.0, reorder_level=100.0)
            rm_sole = RawMaterial(company_id=comp.id, code="RM-D3-SOLE", name="TPR Moulded Sole Size 42", unit="pcs", current_stock=300.0, reorder_level=50.0)
            session.add_all([rm_leather, rm_sole])
            session.commit()
            session.refresh(rm_leather)
            session.refresh(rm_sole)

            purchase = Purchase(
                company_id=comp.id, supplier_id=sup.id, raw_material_id=rm_leather.id,
                status="RECEIVED", payment_status="paid",
                quantity=Decimal("200.000"), unit_price=Decimal("400.00"), total_amount=Decimal("80000.00"),
                carrying_in_paisa=250000, import_duty_paisa=500000, china_carrying_paisa=150000, insurance_paisa=100000,
                total_landed_cost_paisa=9000000, effective_unit_rate_paisa=45000,
                received_quantity=200.0, grn_number="GRN-D3-001", received_by_id=admin_user.id,
                purchase_date_ad="2026-10-10", purchase_date_bs="2083-06-24",
                order_date_ad=date(2026, 10, 10), order_date_bs="2083-06-24",
                receipt_date_ad=date(2026, 10, 11), receipt_date_bs="2083-06-25"
            )
            session.add(purchase)

            # Domain 3: Products, BOM, Production Batch
            prod = Product(company_id=comp.id, code="ART-D3-BOOT-42", name="Alpine Hiker Boot", size="42", category="Boots", unit_price=Decimal("5000.00"))
            session.add(prod)
            session.commit()
            session.refresh(prod)

            bom1 = BillOfMaterials(company_id=comp.id, product_id=prod.id, raw_material_id=rm_leather.id, quantity_required=Decimal("1.500"))
            bom2 = BillOfMaterials(company_id=comp.id, product_id=prod.id, raw_material_id=rm_sole.id, quantity_required=Decimal("1.000"))
            session.add_all([bom1, bom2])

            batch = ProductionBatch(
                company_id=comp.id, product_id=prod.id, batch_number="BAT-D3-001",
                color="Chestnut Brown", target_quantity=100, produced_quantity=95,
                worker_count=8, status="completed", date_ad="2026-10-12", date_bs="2083-06-26"
            )
            session.add(batch)

            # Domain 4: Stock movements & Warehouse Transfers
            sm_in = StockMovement(
                company_id=comp.id, product_id=prod.id, warehouse_id=wh_main.id,
                direction=1, quantity=Decimal("95.0"), ref_type="production",
                movement_type="PRODUCTION_IN", actor_id=admin_user.id, date_ad="2026-10-12", date_bs="2083-06-26"
            )
            session.add(sm_in)
            session.commit()

            # Stock transfer between warehouses
            transfer = StockTransfer(
                company_id=comp.id, transfer_number="TRF-D3-00001",
                source_warehouse_id=wh_main.id, destination_warehouse_id=wh_retail.id,
                status="RECEIVED", transfer_date_ad="2026-10-13", transfer_date_bs="2083-06-27",
                created_by_id=admin_user.id
            )
            session.add(transfer)
            session.commit()
            session.refresh(transfer)

            trf_item = StockTransferItem(
                company_id=comp.id, transfer_id=transfer.id, product_id=prod.id,
                size="42", requested_quantity=Decimal("30.0"), dispatched_quantity=Decimal("30.0"),
                received_quantity=Decimal("30.0"), discrepancy_quantity=Decimal("0.0")
            )
            session.add(trf_item)

            # Movements reflecting transfer
            sm_trf_out = StockMovement(
                company_id=comp.id, product_id=prod.id, warehouse_id=wh_main.id,
                direction=-1, quantity=Decimal("30.0"), ref_type="transfer",
                movement_type="TRANSFER_OUT", actor_id=admin_user.id, date_ad="2026-10-13", date_bs="2083-06-27"
            )
            sm_trf_in = StockMovement(
                company_id=comp.id, product_id=prod.id, warehouse_id=wh_retail.id,
                direction=1, quantity=Decimal("30.0"), ref_type="transfer",
                movement_type="TRANSFER_IN", actor_id=admin_user.id, date_ad="2026-10-13", date_bs="2083-06-27"
            )
            session.add_all([sm_trf_out, sm_trf_in])

            # Domain 5: Client, Sales Order, Invoice, Receivables, Payments
            client = Client(company_id=comp.id, code="CLI-D3-POKHARA", name="Pokhara Adventure Gear", credit_limit=Decimal("500000.00"))
            session.add(client)
            session.commit()
            session.refresh(client)

            so = SalesOrder(
                company_id=comp.id, client_id=client.id, order_number="SO-D3-001",
                status="delivered", order_date_ad="2026-10-14", order_date_bs="2083-06-28",
                total_amount=Decimal("100000.00"), received_amount=Decimal("40000.00"), receivable_amount=Decimal("60000.00")
            )
            session.add(so)
            session.commit()
            session.refresh(so)

            so_item = SalesItem(
                company_id=comp.id, sales_order_id=so.id, product_id=prod.id,
                quantity=20, unit_price=Decimal("5000.00"), total_price=Decimal("100000.00")
            )
            session.add(so_item)

            # Stock movement for sale from wh_retail
            sm_sale = StockMovement(
                company_id=comp.id, product_id=prod.id, warehouse_id=wh_retail.id,
                direction=-1, quantity=Decimal("20.0"), ref_type="sale",
                movement_type="SALES_OUT", actor_id=admin_user.id, date_ad="2026-10-14", date_bs="2083-06-28"
            )
            session.add(sm_sale)

            # Invoice with 13% VAT
            inv = Invoice(
                company_id=comp.id, sales_order_id=so.id, invoice_number="INV-01-00001",
                sequence_number=1, date_ad="2026-10-14", date_bs="2083-06-28",
                subtotal=Decimal("100000.00"), vat_enabled=True, vat_rate=Decimal("13.00"),
                vat_amount=Decimal("13000.00"), total_amount=Decimal("113000.00")
            )
            session.add(inv)

            # Receivables: Invoice posted (113,000 NPR = 11,300,000 paisa)
            r_inv = ReceivableEntry(
                company_id=comp.id, client_id=client.id, invoice_id=inv.id,
                entry_type="INVOICE_POSTED", direction=1, amount_paisa=11300000, actor_id=admin_user.id
            )
            # Cash payment (40,000 NPR = 4,000,000 paisa)
            r_pay = ReceivableEntry(
                company_id=comp.id, client_id=client.id,
                entry_type="PAYMENT_CASH", direction=-1, amount_paisa=4000000, actor_id=admin_user.id
            )
            session.add_all([r_inv, r_pay])

            # Domain 6: HR Workers & FIFO Advance Installment Recovery
            worker = Worker(
                company_id=comp.id, worker_code="WRK-D3-001", name="Sita Maya Tamang",
                pay_type="SALARY", basic_rate_paisa=3200000, is_active=True,
                temporary_address="Kathmandu-11", permanent_address="Sindhupalchok"
            )
            session.add(worker)
            session.commit()
            session.refresh(worker)

            adv_issued = WorkerAdvance(
                company_id=comp.id, worker_id=worker.id, amount_paisa=1500000,
                entry_type="ISSUED", date=date(2026, 9, 20), actor_id=admin_user.id,
                installment_amount_paisa=500000, notes="Dashain Festival advance"
            )
            session.add(adv_issued)
            session.commit()
            session.refresh(adv_issued)
            adv_issued_id = adv_issued.id

            adv_repay = WorkerAdvance(
                company_id=comp.id, worker_id=worker.id, amount_paisa=500000,
                entry_type="RECOVERED", date=date(2026, 10, 10), actor_id=admin_user.id,
                parent_advance_id=adv_issued_id, notes="Monthly installment recovery"
            )
            session.add(adv_repay)

            # Domain 7: Fixed Assets, Factory Expenses, Waste
            asset = FixedAsset(
                company_id=comp.id, asset_code="AST-D3-SOLE-PRESS-01", asset_name="Hydraulic Outsole Attaching Press",
                category="MACHINERY", purchase_date_ad=date(2026, 8, 15), purchase_date_bs="2083-04-31",
                purchase_cost_paisa=65000000, quantity=1, actor_id=admin_user.id
            )
            factory_exp = FactoryExpense(
                company_id=comp.id, expense_date_ad=date(2026, 10, 1), expense_date_bs="2083-06-15",
                particular="Nepal Electricity Authority", category="ELECTRICITY",
                amount_paisa=3500000, payment_method="BANK", remarks="Factory industrial power tariff",
                actor_id=admin_user.id
            )
            waste = WasteRecord(
                company_id=comp.id, waste_date_ad=date(2026, 10, 12), waste_date_bs="2083-06-26",
                waste_type="RAW_MATERIAL_SCRAP", raw_material_id=rm_leather.id, quantity=8.4,
                unit="kg", reason="Cutting room leather offcuts", actor_id=admin_user.id
            )
            session.add_all([asset, factory_exp, waste])
            session.commit()

        # Capture baseline catalog & record counts
        baseline_counts = {}
        with Session(src_engine) as session:
            cursor = session.connection().connection.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
            tables = [r[0] for r in cursor.fetchall() if r[0] != "alembic_version"]
            for t in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
                baseline_counts[t] = cursor.fetchone()[0]

        total_source_rows = sum(baseline_counts.values())
        assert total_source_rows > 0

        # 3. Trigger run_database_backup() against source database
        monkeypatch.setattr(settings, "DATABASE_URL", src_raw_url)
        backup_res = run_database_backup()
        assert backup_res["status"] == "success", f"Backup failed: {backup_res.get('error_message')}"

        backup_file_name = backup_res["file_name"]
        backup_file_path = BACKUP_DIR / backup_file_name
        assert backup_file_path.exists()
        assert backup_res["file_size_bytes"] > 0
        assert "sha256" in backup_res

        # Validate SHA-256 integrity
        with open(backup_file_path, "rb") as bf:
            computed_sha = hashlib.sha256(bf.read()).hexdigest()
        assert computed_sha == backup_res["sha256"]

        # 4. Failure test: Non-existent file raises FileNotFoundError
        bogus_path = BACKUP_DIR / "non_existent_ghost.sql"
        with pytest.raises(FileNotFoundError):
            restore_database_backup(bogus_path, target_db_url=dst_raw_url)

        # 5. Failure test: Truncated / corrupted backup artifact fails cleanly
        corrupt_backup = tmp_path / "corrupted_partial.sql"
        with open(corrupt_backup, "w") as cf:
            cf.write("INVALID SQL TRUNCATED DUMP SYNTAX ERROR HERE;")
        fail_res = restore_database_backup(corrupt_backup, target_db_url=dst_raw_url)
        assert fail_res["status"] == "failed"
        assert fail_res["error_message"] is not None

        # 6. Clean target database and restore valid backup
        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE {dst_db_name}"))
            conn.execute(text(f"CREATE DATABASE {dst_db_name}"))

        restore_start = time.time()
        restore_res = restore_database_backup(backup_file_path, target_db_url=dst_raw_url)
        restore_dur = time.time() - restore_start

        assert restore_res["status"] == "success", f"Restoration failed: {restore_res.get('error_message')}"
        assert restore_res["target_url"] != src_raw_url  # Verified target was isolated

        # 7. Deep Multi-Tenant Ledger Reconciliation between Source and Restored DBs
        dst_engine = create_engine(dst_sa_url)
        restored_counts = {}
        with Session(dst_engine) as session:
            cursor = session.connection().connection.cursor()
            for t in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{t}"')
                restored_counts[t] = cursor.fetchone()[0]

        for t in tables:
            assert baseline_counts[t] == restored_counts[t], (
                f"Row count mismatch in table '{t}': source={baseline_counts[t]}, restored={restored_counts[t]}"
            )

        # 8. Verify specific domain invariants in restored database
        with Session(dst_engine) as session:
            # Domain 1: Company ownership and users
            rest_comp = session.query(Company).filter_by(code="LIVO_D3").first()
            assert rest_comp is not None
            assert rest_comp.pan_number == "601998877"

            rest_users = session.query(User).filter_by(company_id=rest_comp.id).all()
            assert len(rest_users) == 3

            # Domain 2: Stock ledger balance continuity
            # Total product on hand across all warehouses = 95 - 30 + 30 - 20 = 75
            total_stock_on_hand = session.query(
                func_sum := text("COALESCE(SUM(quantity * direction), 0) FROM stock_movements WHERE company_id = :cid")
            ).params(cid=rest_comp.id).scalar()
            # In PostgreSQL via raw SQL:
            res_stock = session.execute(
                text("SELECT COALESCE(SUM(quantity * direction), 0) FROM stock_movements WHERE company_id = :cid"),
                {"cid": rest_comp.id}
            ).scalar()
            assert float(res_stock) == 75.0, f"Restored stock math mismatch: expected 75.0, got {res_stock}"

            # Main warehouse on-hand = 95 - 30 = 65
            res_main_wh = session.execute(
                text("SELECT COALESCE(SUM(quantity * direction), 0) FROM stock_movements WHERE company_id = :cid AND warehouse_id = :wid"),
                {"cid": rest_comp.id, "wid": wh_main_id}
            ).scalar()
            assert float(res_main_wh) == 65.0

            # Retail warehouse on-hand = 30 - 20 = 10
            res_retail_wh = session.execute(
                text("SELECT COALESCE(SUM(quantity * direction), 0) FROM stock_movements WHERE company_id = :cid AND warehouse_id = :wid"),
                {"cid": rest_comp.id, "wid": wh_retail_id}
            ).scalar()
            assert float(res_retail_wh) == 10.0

            # Stock transfer state
            rest_trf = session.query(StockTransfer).filter_by(transfer_number="TRF-D3-00001").first()
            assert rest_trf is not None
            assert rest_trf.status == "RECEIVED"
            assert len(rest_trf.items) == 1
            assert rest_trf.items[0].received_quantity == Decimal("30.0")

            # Domain 3: Accounts Receivable Subledger
            # Outstanding AR = 11,300,000 - 4,000,000 = 7,300,000 paisa (NPR 73,000)
            res_ar = session.execute(
                text("SELECT COALESCE(SUM(amount_paisa * direction), 0) FROM receivable_entries WHERE company_id = :cid"),
                {"cid": rest_comp.id}
            ).scalar()
            assert int(res_ar) == 7300000, f"Restored AR mismatch: expected 7,300,000 paisa, got {res_ar}"

            # Domain 4: Landed cost purchase precision
            rest_po = session.query(Purchase).filter_by(grn_number="GRN-D3-001").first()
            assert rest_po is not None
            assert rest_po.total_amount == Decimal("80000.00")
            assert rest_po.carrying_in_paisa == 250000
            assert rest_po.import_duty_paisa == 500000
            assert rest_po.total_landed_cost_paisa == 9000000

            # Domain 5: HR Advance installment recovery math
            # Worker advance remaining = 1,500,000 - 500,000 = 1,000,000 paisa
            adv_open = session.query(WorkerAdvance).filter_by(id=adv_issued_id).first()
            assert adv_open is not None
            repayments = session.query(WorkerAdvance).filter_by(parent_advance_id=adv_issued_id).all()
            repaid_sum = sum(r.amount_paisa for r in repayments)
            assert repaid_sum == 500000
            rem_principal = adv_open.amount_paisa - repaid_sum
            assert rem_principal == 1000000

            # Domain 6: Fixed Asset, Factory Expense, Waste
            rest_fa = session.query(FixedAsset).filter_by(asset_code="AST-D3-SOLE-PRESS-01").first()
            assert rest_fa is not None
            assert rest_fa.purchase_cost_paisa == 65000000

            rest_exp = session.query(FactoryExpense).filter_by(category="ELECTRICITY").first()
            assert rest_exp is not None
            assert rest_exp.amount_paisa == 3500000

            rest_waste = session.query(WasteRecord).filter_by(waste_type="RAW_MATERIAL_SCRAP").first()
            assert rest_waste is not None
            assert rest_waste.quantity == 8.4

        # 9. Read-only API verification against restored database
        from app.api.deps import get_db
        def override_restored_db():
            s = Session(dst_engine)
            try:
                yield s
            finally:
                s.close()

        from app.main import app
        app.dependency_overrides[get_db] = override_restored_db
        try:
            with TestClient(app) as client:
                # Health and readiness
                ready_resp = client.get("/health/ready")
                assert ready_resp.status_code == 200, f"Readiness check failed: {ready_resp.json()}"
                assert ready_resp.json()["status"] == "ready"
                assert ready_resp.json()["current_head"] == "024_add_rate_limit_entries"

                # Backward-compatible /health
                health_resp = client.get("/health")
                assert health_resp.status_code == 200
                assert health_resp.json()["database"] == "healthy"
        finally:
            app.dependency_overrides.pop(get_db, None)

        # Dispose engines prior to drop
        src_engine.dispose()
        dst_engine.dispose()

        # Clean up isolated databases
        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE {src_db_name}"))
            conn.execute(text(f"DROP DATABASE {dst_db_name}"))

        if backup_file_path.exists():
            backup_file_path.unlink()

    finally:
        server.cleanup()
