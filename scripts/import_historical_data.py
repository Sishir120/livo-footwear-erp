"""
Historical Data Import Script
Imports 3 months of historical ERP records (suppliers, raw materials, purchases, products, clients,
production batches, sales orders, invoices, stock movements) per PRD.md §4 & RULES.md §7.

Safety Guarantee (RULES.md §7):
Can run against a copy of the database (`--db-path`) or dry-run (`--dry-run`) first before updating primary DB.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.company import Company
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.models.invoice import Invoice

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_historical")

def generate_and_import_historical_data(db_url: str, dry_run: bool = False):
    logger.info(f"Starting historical data import (dry_run={dry_run}) target: {db_url}")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        company = db.query(Company).filter(Company.code == "LIVO").first()
        if not company:
            logger.error("Default company LIVO not found. Ensure DB is initialized.")
            return

        company_id = company.id
        logger.info(f"Importing historical data for Company ID: {company_id} ({company.name})")

        # 1. Historical Suppliers
        suppliers_data = [
            {"code": "SUP-HIST-01", "name": "Nepal Synthetic Leather Industries", "contact_person": "Ram Sharma", "phone": "+977-9851000001", "address": "Balaju Industrial District, Kathmandu"},
            {"code": "SUP-HIST-02", "name": "Himalayan Rubber & EVA Corp", "contact_person": "Sita Thapa", "phone": "+977-9851000002", "address": "Hetauda Industrial Zone, Hetauda"},
            {"code": "SUP-HIST-03", "name": "Everest Packaging & Adhesive Ltd", "contact_person": "Bikash Gurung", "phone": "+977-9851000003", "address": "Biratnagar Industrial Estate"}
        ]
        suppliers = []
        for d in suppliers_data:
            sup = db.query(Supplier).filter(Supplier.code == d["code"], Supplier.company_id == company_id).first()
            if not sup:
                sup = Supplier(company_id=company_id, **d)
                db.add(sup)
                db.flush()
            suppliers.append(sup)

        # 2. Historical Raw Materials
        materials_data = [
            {"code": "MAT-PU-01", "name": "PU Leather Sheets (Black)", "unit": "meters", "min_stock_alert": 100.0},
            {"code": "MAT-EVA-01", "name": "EVA Sole Compound", "unit": "kg", "min_stock_alert": 250.0},
            {"code": "MAT-GLUE-01", "name": "Shoe Adhesive / Glue", "unit": "liters", "min_stock_alert": 50.0}
        ]
        materials = []
        for d in materials_data:
            mat = db.query(RawMaterial).filter(RawMaterial.code == d["code"], RawMaterial.company_id == company_id).first()
            if not mat:
                mat = RawMaterial(company_id=company_id, **d)
                db.add(mat)
                db.flush()
            materials.append(mat)

        # 3. Historical Finished Goods Products
        products_data = [
            {"code": "PROD-BOOT-42", "name": "LIVO Tactical Boot Size 42", "category": "Boot", "size": "42", "color": "Black", "unit_price": 2800.0},
            {"code": "PROD-SLIP-40", "name": "LIVO Comfort Slipper Size 40", "category": "Slipper", "size": "40", "color": "Navy", "unit_price": 750.0},
            {"code": "PROD-SHOE-41", "name": "LIVO Executive Shoe Size 41", "category": "Shoe", "size": "41", "color": "Brown", "unit_price": 3200.0}
        ]
        products = []
        for d in products_data:
            prod = db.query(Product).filter(Product.code == d["code"], Product.company_id == company_id).first()
            if not prod:
                prod = Product(company_id=company_id, **d)
                db.add(prod)
                db.flush()
            products.append(prod)

        # 4. Historical Clients
        clients_data = [
            {"code": "CLI-KTM-01", "name": "Kathmandu Footwear Emporium", "contact_person": "Hari Shrestha", "phone": "+977-9841223344", "address": "New Road, Kathmandu", "credit_limit": 500000.0},
            {"code": "CLI-PKR-02", "name": "Pokhara Shoe Center", "contact_person": "Anita Rai", "phone": "+977-9846112233", "address": "Mahendrapool, Pokhara", "credit_limit": 300000.0}
        ]
        clients = []
        for d in clients_data:
            cli = db.query(Client).filter(Client.code == d["code"], Client.company_id == company_id).first()
            if not cli:
                cli = Client(company_id=company_id, **d)
                db.add(cli)
                db.flush()
            clients.append(cli)

        # 5. Generate 3 Months of Historical Transactions (90 days back)
        today = datetime.now(timezone.utc)
        import_count_purchases = 0
        import_count_batches = 0
        import_count_orders = 0

        # Fetch initial max sequence once before loop
        current_seq = db.query(Invoice).filter(Invoice.company_id == company_id).count()

        for day_offset in range(90, 0, -5):
            date_dt = today - timedelta(days=day_offset)
            date_ad_str = date_dt.strftime("%Y-%m-%d")
            date_bs_str = f"2082-{(date_dt.month % 12) + 1:02d}-{(date_dt.day % 28) + 1:02d}"


            # Purchase record
            purch = Purchase(
                company_id=company_id,
                supplier_id=suppliers[day_offset % len(suppliers)].id,
                raw_material_id=materials[day_offset % len(materials)].id,
                quantity=200.0 + (day_offset * 2),
                unit_price=150.0,
                total_amount=(200.0 + (day_offset * 2)) * 150.0,
                purchase_date_ad=date_ad_str,
                purchase_date_bs=date_bs_str,
                payment_status="paid",
                notes=f"Historical purchase batch 90d window (day -{day_offset})"
            )
            db.add(purch)
            import_count_purchases += 1

            # Production batch & stock ledger entry (+ direction)
            target_qty = 100.0 + day_offset
            prod_batch = ProductionBatch(
                company_id=company_id,
                batch_number=f"PB-HIST-{day_offset:03d}",
                product_id=products[day_offset % len(products)].id,
                target_quantity=target_qty,
                produced_quantity=target_qty,
                worker_count=12,
                status="completed",
                date_ad=date_ad_str,
                date_bs=date_bs_str,
                notes=f"Historical production batch (day -{day_offset})"
            )
            db.add(prod_batch)
            db.flush()

            # Material usage record
            usage = ProductionMaterialUsage(
                company_id=company_id,
                batch_id=prod_batch.id,
                raw_material_id=materials[day_offset % len(materials)].id,
                quantity_used=target_qty * 0.5
            )
            db.add(usage)

            # Stock movement (+)
            stock_in = StockMovement(
                company_id=company_id,
                product_id=products[day_offset % len(products)].id,
                quantity=target_qty,
                direction=1,
                ref_type="production",
                ref_id=prod_batch.id,
                date_ad=date_ad_str,
                date_bs=date_bs_str,
                notes=f"Historical production stock IN (Batch {prod_batch.batch_number})"
            )
            db.add(stock_in)
            import_count_batches += 1

            # Sales order & stock ledger entry (- direction)
            sale_qty = 50.0 + (day_offset // 2)
            unit_price = products[day_offset % len(products)].unit_price
            order_total = sale_qty * unit_price

            sales_order = SalesOrder(
                company_id=company_id,
                order_number=f"SO-HIST-{day_offset:03d}",
                client_id=clients[day_offset % len(clients)].id,
                order_date_ad=date_ad_str,
                order_date_bs=date_bs_str,
                status="delivered",
                total_amount=order_total,
                received_amount=order_total,
                receivable_amount=0.0,
                delivered=True
            )
            db.add(sales_order)
            db.flush()

            sales_item = SalesItem(
                company_id=company_id,
                sales_order_id=sales_order.id,
                product_id=products[day_offset % len(products)].id,
                quantity=sale_qty,
                unit_price=unit_price,
                total_price=order_total
            )
            db.add(sales_item)

            stock_out = StockMovement(
                company_id=company_id,
                product_id=products[day_offset % len(products)].id,
                quantity=sale_qty,
                direction=-1,
                ref_type="sale",
                ref_id=sales_order.id,
                date_ad=date_ad_str,
                date_bs=date_bs_str,
                notes=f"Historical sale stock OUT (Order {sales_order.order_number})"
            )
            db.add(stock_out)

            # Invoice record with sequential sequence_number
            current_seq += 1
            max_seq = current_seq
            inv = Invoice(

                company_id=company_id,
                sales_order_id=sales_order.id,
                invoice_number=f"INV-{company_id:02d}-{max_seq:05d}",
                sequence_number=max_seq,
                date_ad=date_ad_str,
                date_bs=date_bs_str,
                subtotal=order_total,
                vat_enabled=False,
                vat_rate=0.0,
                vat_amount=0.0,
                total_amount=order_total,
                received_amount=order_total,
                receivable_amount=0.0,
                is_void=False
            )
            db.add(inv)
            import_count_orders += 1

        if dry_run:
            logger.info("[DRY RUN] Rolling back historical import transaction.")
            db.rollback()
        else:
            db.commit()
            logger.info(f"[SUCCESS] Committed historical data import: {import_count_purchases} purchases, {import_count_batches} production batches, {import_count_orders} sales & invoices across 3 months.")

    except Exception as e:
        db.rollback()
        logger.error(f"Import failed: {e}", exc_info=True)
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import 3 months of historical ERP data")
    parser.add_argument("--db-url", default="sqlite:///./livo_dev.db", help="Database URL target")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without committing")
    args = parser.parse_args()

    # Determine sqlite path if relative
    url = args.db_url
    if url.startswith("sqlite:///./"):
        sqlite_file = backend_dir / url.replace("sqlite:///./", "")
        url = f"sqlite:///{sqlite_file}"

    generate_and_import_historical_data(url, dry_run=args.dry_run)
