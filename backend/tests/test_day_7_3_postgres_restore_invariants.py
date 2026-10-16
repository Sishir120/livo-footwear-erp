"""
LIVO Footwear ERP — Day 7.3 PostgreSQL Restore & Invariant Verification Test
============================================================================
Forensic verification of full database-plus-storage recovery into a fresh,
disposable PostgreSQL 16 database and isolated filesystem directory.

Verifies critical business invariants across:
1. Inventory quantities & stock ledger balances
2. Transfer quantities & states
3. Sales invoices, payments, and receivables
4. Purchase receipts & landed costs
5. Worker advances & balances
6. Fixed assets, expenses, and waste records
7. File manifests & physical image references
"""

import os
import time
import hashlib
import pathlib
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone, date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command

from embedded_postgres import get_server

# Models
from app.models.company import Company
from app.models.user import User
from app.models.branch import Branch, BranchType
from app.models.stock import Product, Warehouse, StockMovement
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.sales import Client, SalesOrder, Payment, FactoryExpense
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry
from app.models.worker import Worker, WorkerAdvance
from app.models.asset import FixedAsset
from app.models.waste import WasteRecord
from app.models.gallery import ProductImage
from app.core.security import get_password_hash

# Services
from app.services.backup_service import (
    run_database_backup,
    restore_database_backup,
    run_storage_backup,
    restore_storage_backup,
    create_complete_system_backup,
    BACKUP_DIR
)
from app.config import settings


def test_postgres_restore_business_invariants(tmp_path, monkeypatch):
    pgdata = tmp_path / "pgdata_day73"
    server = get_server(pgdata, cleanup_mode="delete")
    server.ensure_pgdata_inited()
    server.ensure_postgres_running()
    time.sleep(1.5)

    staging_base = tmp_path / "staging_storage"
    prod_upload_dir = staging_base / "static" / "uploads" / "products"
    prod_upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("app.services.backup_service.BACKEND_DIR", staging_base)

    try:
        raw_master_url = server.get_uri("postgres")
        sa_master_url = raw_master_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        admin_engine = create_engine(sa_master_url, isolation_level="AUTOCOMMIT")

        src_db = "livo_inv_src"
        dst_db = "livo_inv_dst"

        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {src_db}"))
            conn.execute(text(f"DROP DATABASE IF EXISTS {dst_db}"))
            conn.execute(text(f"CREATE DATABASE {src_db}"))
            conn.execute(text(f"CREATE DATABASE {dst_db}"))

        src_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{src_db}"
        src_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{src_db}"
        dst_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{dst_db}"
        dst_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{dst_db}"

        # 1. Run migrations
        backend_dir = pathlib.Path(__file__).resolve().parent.parent
        alembic_ini = backend_dir / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", src_sa_url)
        command.upgrade(cfg, "head")

        # 2. Seed comprehensive business entities
        src_engine = create_engine(src_sa_url)
        with Session(src_engine) as session:
            # Company & Warehouses & Branches
            comp = Company(name="LIVO Invariant Test Corp", code="LIVO_INV", pan_number="609998877")
            session.add(comp)
            session.commit()
            session.refresh(comp)

            wh1 = Warehouse(company_id=comp.id, code="WH-FACTORY", name="Main Birgunj Factory", is_active=True)
            wh2 = Warehouse(company_id=comp.id, code="WH-SHOWROOM", name="Kathmandu Showroom", is_active=True)
            session.add_all([wh1, wh2])
            session.commit()
            session.refresh(wh1)
            session.refresh(wh2)

            br1 = Branch(company_id=comp.id, code="BR-KTM", name="Kathmandu Branch", type=BranchType.RETAIL_OUTLET.value)
            session.add(br1)
            session.commit()

            admin = User(company_id=comp.id, name="Admin Inv", username="admin_inv", password_hash="hash123", role="admin", active=True)
            session.add(admin)
            session.commit()
            session.refresh(admin)

            # 1. Inventory & Ledger
            prod = Product(company_id=comp.id, code="BOOT-TREK-01", name="Himalayan Trek Boot", size="41", unit_price=Decimal("4500.00"))
            session.add(prod)
            session.commit()
            session.refresh(prod)

            mov = StockMovement(
                company_id=comp.id,
                warehouse_id=wh1.id,
                product_id=prod.id,
                quantity=200,
                direction=1,
                ref_type="production",
                movement_type="PRODUCTION_IN",
                date_ad="2026-10-16",
                date_bs="2083-06-30",
                actor_id=admin.id,
                notes="Initial production run batch 1"
            )
            session.add(mov)

            # 2. Stock Transfer
            transfer = StockTransfer(
                company_id=comp.id,
                transfer_number="TRF-2026-001",
                source_warehouse_id=wh1.id,
                destination_warehouse_id=wh2.id,
                status="IN_TRANSIT",
                transfer_date_ad="2026-10-16",
                transfer_date_bs="2083-06-30",
                created_by_id=admin.id,
                notes="Inter-warehouse stock rebalancing"
            )
            session.add(transfer)
            session.commit()
            session.refresh(transfer)

            trf_item = StockTransferItem(
                company_id=comp.id,
                transfer_id=transfer.id,
                product_id=prod.id,
                requested_quantity=50,
                dispatched_quantity=50
            )
            session.add(trf_item)

            # 3. Purchases & Raw Materials
            sup = Supplier(company_id=comp.id, code="SUP-01", name="Nepal Leather Tannery Ltd")
            session.add(sup)
            session.commit()
            session.refresh(sup)

            rm = RawMaterial(company_id=comp.id, code="MAT-LTHR-01", name="Full Grain Buffalo Leather", unit="kg")
            session.add(rm)
            session.commit()
            session.refresh(rm)

            po = Purchase(
                company_id=comp.id,
                supplier_id=sup.id,
                raw_material_id=rm.id,
                quantity=Decimal("50.0"),
                unit_price=Decimal("350.00"),
                total_amount=Decimal("17500.00"),
                purchase_date_ad="2026-10-16",
                purchase_date_bs="2083-06-30",
                carrying_in_paisa=100000,
                status="RECEIVED"
            )
            session.add(po)

            # 4. Sales, Invoices, Payments, Receivables
            client = Client(company_id=comp.id, code="CLI-01", name="Himalayan Sports Goods")
            session.add(client)
            session.commit()
            session.refresh(client)

            so = SalesOrder(
                company_id=comp.id,
                order_number="SO-2026-990",
                client_id=client.id,
                order_date_ad="2026-10-16",
                order_date_bs="2083-06-30",
                total_amount=Decimal("22600.00"),
                status="DISPATCHED"
            )
            session.add(so)
            session.commit()
            session.refresh(so)

            inv = Invoice(
                company_id=comp.id,
                sales_order_id=so.id,
                invoice_number="INV-2026-0001",
                sequence_number=1,
                date_ad="2026-10-16",
                date_bs="2083-06-30",
                subtotal=Decimal("20000.00"),
                vat_enabled=True,
                vat_rate=Decimal("13.0"),
                vat_amount=Decimal("2600.00"),
                total_amount=Decimal("22600.00"),
                received_amount=Decimal("10000.00"),
                receivable_amount=Decimal("12600.00")
            )
            session.add(inv)
            session.commit()
            session.refresh(inv)

            pmt = Payment(
                company_id=comp.id,
                sales_order_id=so.id,
                client_id=client.id,
                amount=Decimal("10000.00"),
                payment_date_ad="2026-10-16",
                payment_date_bs="2083-06-30",
                payment_method="bank"
            )
            session.add(pmt)

            recv = ReceivableEntry(
                company_id=comp.id,
                client_id=client.id,
                entry_type="INVOICE_POSTED",
                direction=1,
                amount_paisa=2260000,
                invoice_id=inv.id,
                actor_id=admin.id
            )
            session.add(recv)

            # 5. Worker & Advance
            worker = Worker(
                company_id=comp.id,
                worker_code="W-INV-01",
                name="Ram Bahadur Gurung",
                pay_type="SALARY",
                basic_rate_paisa=3500000,
                is_active=True
            )
            session.add(worker)
            session.commit()
            session.refresh(worker)

            adv = WorkerAdvance(
                company_id=comp.id,
                worker_id=worker.id,
                amount_paisa=500000,  # Rs. 5,000.00
                entry_type="ISSUED",
                date=date(2026, 10, 15),
                actor_id=admin.id,
                notes="Festival advance Dashain"
            )
            session.add(adv)

            # 6. Fixed Asset, Factory Expense, Waste Record
            asset = FixedAsset(
                company_id=comp.id,
                asset_code="AST-CUTTER-01",
                asset_name="Industrial Sole Cutting Machine",
                category="MACHINERY",
                purchase_date_ad=date(2026, 10, 1),
                purchase_date_bs="2083-06-15",
                purchase_cost_paisa=45000000,
                quantity=1,
                actor_id=admin.id
            )
            exp = FactoryExpense(
                company_id=comp.id,
                expense_date_ad=date(2026, 10, 16),
                expense_date_bs="2083-06-30",
                particular="NEA Electricity Bill",
                category="ELECTRICITY",
                amount_paisa=1520000,
                payment_method="BANK",
                actor_id=admin.id
            )
            waste = WasteRecord(
                company_id=comp.id,
                waste_date_ad=date(2026, 10, 16),
                waste_date_bs="2083-06-30",
                waste_type="RAW_MATERIAL_SCRAP",
                raw_material_id=rm.id,
                quantity=14.50,
                unit="kg",
                actor_id=admin.id
            )
            session.add_all([asset, exp, waste])

            # 7. Physical Image Asset on Disk
            img_file = prod_upload_dir / "trek_boot_01.jpg"
            img_bytes = b"\xff\xd8\xff\xe0_MOCK_TREK_BOOT_IMAGE_BYTES_12345"
            with open(img_file, "wb") as f:
                f.write(img_bytes)

            p_img = ProductImage(
                company_id=comp.id,
                product_id=prod.id,
                image_url="/api/v1/gallery/images/trek_boot_01.jpg",
                file_name="trek_boot_01.jpg",
                mime_type="image/jpeg",
                file_size_bytes=len(img_bytes),
                is_primary=True
            )
            session.add(p_img)
            session.commit()

        # 3. Perform synchronized backup
        monkeypatch.setattr(settings, "DATABASE_URL", src_raw_url)
        backup_manifest = create_complete_system_backup()
        assert backup_manifest["overall_status"] == "success"

        db_file = BACKUP_DIR / backup_manifest["database_backup"]["file_name"]
        storage_file = Path(backup_manifest["storage_backup"]["file_path"])

        # 4. Restore into fresh isolated database and separate filesystem target
        restored_storage_base = tmp_path / "restored_storage"
        restored_storage_base.mkdir(parents=True, exist_ok=True)

        res_db = restore_database_backup(db_file, target_db_url=dst_raw_url)
        assert res_db["status"] == "success"

        res_storage = restore_storage_backup(storage_file, target_base_dir=restored_storage_base)
        assert res_storage["status"] == "success"

        # 5. Connect to restored database and verify all 7 critical business invariants
        dst_engine = create_engine(dst_sa_url)
        with Session(dst_engine) as session:
            # Table row counts
            counts = {
                "companies": session.query(Company).count(),
                "warehouses": session.query(Warehouse).count(),
                "products": session.query(Product).count(),
                "stock_movements": session.query(StockMovement).count(),
                "stock_transfers": session.query(StockTransfer).count(),
                "stock_transfer_items": session.query(StockTransferItem).count(),
                "suppliers": session.query(Supplier).count(),
                "raw_materials": session.query(RawMaterial).count(),
                "purchases": session.query(Purchase).count(),
                "clients": session.query(Client).count(),
                "invoices": session.query(Invoice).count(),
                "payments": session.query(Payment).count(),
                "receivable_entries": session.query(ReceivableEntry).count(),
                "workers": session.query(Worker).count(),
                "worker_advances": session.query(WorkerAdvance).count(),
                "fixed_assets": session.query(FixedAsset).count(),
                "factory_expenses": session.query(FactoryExpense).count(),
                "waste_records": session.query(WasteRecord).count(),
                "product_images": session.query(ProductImage).count(),
            }

            for model_name, cnt in counts.items():
                assert cnt >= 1, f"Table {model_name} has unexpected count: {cnt}"

            # Invariant 1: Inventory & Stock Ledger
            r_prod = session.query(Product).filter_by(code="BOOT-TREK-01").first()
            assert r_prod is not None
            assert r_prod.unit_price == Decimal("4500.00")
            r_mov = session.query(StockMovement).filter_by(product_id=r_prod.id).first()
            assert r_mov.quantity == 200
            assert r_mov.movement_type == "PRODUCTION_IN"

            # Invariant 2: Transfer Quantities & States
            r_trf = session.query(StockTransfer).filter_by(transfer_number="TRF-2026-001").first()
            assert r_trf.status == "IN_TRANSIT"
            r_item = session.query(StockTransferItem).filter_by(transfer_id=r_trf.id).first()
            assert r_item.requested_quantity == 50
            assert r_item.dispatched_quantity == 50

            # Invariant 3: Sales, Invoices, Payments, Receivables
            r_inv = session.query(Invoice).filter_by(invoice_number="INV-2026-0001").first()
            assert r_inv.subtotal == Decimal("20000.00")
            assert r_inv.vat_amount == Decimal("2600.00")  # 13% Nepal VAT
            assert r_inv.total_amount == Decimal("22600.00")
            assert r_inv.received_amount == Decimal("10000.00")
            assert r_inv.receivable_amount == Decimal("12600.00")

            r_recv = session.query(ReceivableEntry).filter_by(invoice_id=r_inv.id).first()
            assert r_recv.amount_paisa == 2260000

            # Invariant 4: Purchase Receipts & Landed Costs
            r_po = session.query(Purchase).first()
            assert r_po.total_amount == Decimal("17500.00")
            assert r_po.carrying_in_paisa == 100000
            assert r_po.status == "RECEIVED"

            # Invariant 5: Worker Advances
            r_adv = session.query(WorkerAdvance).first()
            assert r_adv.amount_paisa == 500000
            assert r_adv.entry_type == "ISSUED"

            # Invariant 6: Fixed Assets, Expenses, Waste
            r_ast = session.query(FixedAsset).filter_by(asset_code="AST-CUTTER-01").first()
            assert r_ast.purchase_cost_paisa == 45000000

            r_exp = session.query(FactoryExpense).filter_by(category="ELECTRICITY").first()
            assert r_exp.amount_paisa == 1520000

            r_waste = session.query(WasteRecord).first()
            assert r_waste.quantity == 14.50

            # Invariant 7: File Manifests & Restored Files
            r_img = session.query(ProductImage).first()
            restored_file = restored_storage_base / "static" / "uploads" / "products" / r_img.file_name
            assert restored_file.exists()
            assert restored_file.stat().st_size == len(img_bytes)
            assert hashlib.sha256(restored_file.read_bytes()).hexdigest() == hashlib.sha256(img_bytes).hexdigest()

    finally:
        try:
            src_engine.dispose()
            dst_engine.dispose()
        except Exception:
            pass
        server.cleanup()
