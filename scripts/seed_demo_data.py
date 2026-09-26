#!/usr/bin/env python3
"""
Seed script for LIVO GROUP OF INDUSTRIES Footwear ERP.
Populates realistic sample data for the Phase 2a demo deployment.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models.company import Company
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.stock import Product, StockMovement
from app.models.production import ProductionBatch, ProductionMaterialUsage
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.models.invoice import Invoice
from app.core.security import get_password_hash

def seed_demo_data(db_url: str):
    print(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)
    # Strictly rely on Alembic migrations having created all tables (RULES.md §3)
    # Never call Base.metadata.create_all() here.
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Company
        company = db.query(Company).filter(Company.code == "LIVO").first()
        if not company:
            company = Company(
                name="LIVO GROUP OF INDUSTRIES",
                code="LIVO",
                pan_number="600123456",
                address="Balaju Industrial Area, Kathmandu, Nepal",
                phone="+977-1-4350123"
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print("  Created company: LIVO GROUP OF INDUSTRIES")
        else:
            print(f"  Existing company found: {company.name} (id={company.id})")

        company_id = company.id

        # 2. Users
        editor = db.query(User).filter(User.username == "editor_admin", User.company_id == company_id).first()
        if not editor:
            editor = User(
                company_id=company_id,
                name="Factory Operations Editor",
                username="editor_admin",
                email="editor@livogroup.com",
                password_hash=get_password_hash("LivoEditor2026!"),
                role="editor",
                active=True
            )
            db.add(editor)
            print("  Created user: editor_admin")

        viewer = db.query(User).filter(User.username == "viewer_user", User.company_id == company_id).first()
        if not viewer:
            viewer = User(
                company_id=company_id,
                name="Executive Management Viewer",
                username="viewer_user",
                email="viewer@livogroup.com",
                password_hash=get_password_hash("LivoViewer2026!"),
                role="viewer",
                active=True
            )
            db.add(viewer)
            print("  Created user: viewer_user")

        db.commit()

        # 3. Suppliers
        suppliers_data = [
            {"code": "SUP-001", "name": "Himalayan Synthetic Leathers", "contact_person": "Ramesh Adhikari", "phone": "+977-9841234567", "address": "Hetauda Industrial Estate"},
            {"code": "SUP-002", "name": "Everest Sole & Moulds Co.", "contact_person": "Binod Shrestha", "phone": "+977-9851098765", "address": "Birgunj, Parsa"},
            {"code": "SUP-003", "name": "Bagmati Packaging & Cartons", "contact_person": "Sunita Maharjan", "phone": "+977-9803456789", "address": "Patan Industrial Area"},
            {"code": "SUP-004", "name": "Trishuli Fasteners & Rivets", "contact_person": "Dipak KC", "phone": "+977-9812345678", "address": "Kalanki, Kathmandu"},
        ]
        created_suppliers = {}
        for s in suppliers_data:
            existing = db.query(Supplier).filter(Supplier.code == s["code"], Supplier.company_id == company_id).first()
            if not existing:
                existing = Supplier(company_id=company_id, **s)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            created_suppliers[s["code"]] = existing
        print(f"  Seeded {len(created_suppliers)} suppliers")

        # 4. Raw Materials
        materials_data = [
            {"code": "MAT-REX-BLK", "name": "Synthetic PU Rexine (Black)", "unit": "meters", "min_stock_alert": 100.0},
            {"code": "MAT-REX-BRN", "name": "Synthetic PU Rexine (Brown)", "unit": "meters", "min_stock_alert": 80.0},
            {"code": "MAT-SOL-EVA", "name": "EVA Midsole Cushion Sheets", "unit": "sheets", "min_stock_alert": 50.0},
            {"code": "MAT-SOL-RBR", "name": "Vulcanized Rubber Outsoles", "unit": "pairs", "min_stock_alert": 200.0},
            {"code": "MAT-LACE-BLK", "name": "Braided Polyester Laces (Black)", "unit": "pairs", "min_stock_alert": 300.0},
            {"code": "MAT-BOX-LIVO", "name": "LIVO Branded Shoe Packaging Boxes", "unit": "pieces", "min_stock_alert": 500.0},
        ]
        created_materials = {}
        for m in materials_data:
            existing = db.query(RawMaterial).filter(RawMaterial.code == m["code"], RawMaterial.company_id == company_id).first()
            if not existing:
                existing = RawMaterial(company_id=company_id, **m)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            created_materials[m["code"]] = existing
        print(f"  Seeded {len(created_materials)} raw materials")

        # 5. Raw Material Purchases
        purchases_data = [
            {"supplier_id": created_suppliers["SUP-001"].id, "raw_material_id": created_materials["MAT-REX-BLK"].id, "quantity": 250.0, "unit_price": 450.0, "purchase_date_ad": "2026-09-10", "purchase_date_bs": "2083-05-25", "payment_status": "paid"},
            {"supplier_id": created_suppliers["SUP-001"].id, "raw_material_id": created_materials["MAT-REX-BRN"].id, "quantity": 180.0, "unit_price": 460.0, "purchase_date_ad": "2026-09-12", "purchase_date_bs": "2083-05-27", "payment_status": "paid"},
            {"supplier_id": created_suppliers["SUP-002"].id, "raw_material_id": created_materials["MAT-SOL-RBR"].id, "quantity": 600.0, "unit_price": 280.0, "purchase_date_ad": "2026-09-14", "purchase_date_bs": "2083-05-29", "payment_status": "credit"},
            {"supplier_id": created_suppliers["SUP-003"].id, "raw_material_id": created_materials["MAT-BOX-LIVO"].id, "quantity": 1200.0, "unit_price": 45.0, "purchase_date_ad": "2026-09-15", "purchase_date_bs": "2083-05-30", "payment_status": "paid"},
        ]
        for p in purchases_data:
            total_amt = p["quantity"] * p["unit_price"]
            purch = Purchase(company_id=company_id, total_amount=total_amt, **p)
            db.add(purch)
        db.commit()
        print(f"  Seeded {len(purchases_data)} material purchases")

        # 6. Finished Goods Products
        products_data = [
            {"code": "LIVO-M-RUN-BLK-42", "name": "Sprint Runner Sports", "category": "Sports", "size": "42", "color": "Black", "unit_price": 2450.0},
            {"code": "LIVO-M-RUN-BLK-43", "name": "Sprint Runner Sports", "category": "Sports", "size": "43", "color": "Black", "unit_price": 2450.0},
            {"code": "LIVO-M-CAS-BRN-41", "name": "Executive Oxford Casual", "category": "Casual", "size": "41", "color": "Brown", "unit_price": 3100.0},
            {"code": "LIVO-W-TRL-WHT-38", "name": "Aero-Lite Trail Women", "category": "Sports", "size": "38", "color": "White", "unit_price": 2200.0},
            {"code": "LIVO-K-SCH-BLK-32", "name": "Classic Sturdy School Shoe", "category": "School", "size": "32", "color": "Black", "unit_price": 1400.0},
        ]
        created_products = {}
        for p in products_data:
            existing = db.query(Product).filter(Product.code == p["code"], Product.company_id == company_id).first()
            if not existing:
                existing = Product(company_id=company_id, **p)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            created_products[p["code"]] = existing
        print(f"  Seeded {len(created_products)} footwear products")

        # 7. Production Batches and Stock Movements (+IN)
        batches_data = [
            {"batch_number": "BATCH-2026-09-01", "product": created_products["LIVO-M-RUN-BLK-42"], "qty": 150.0, "workers": 8, "date_ad": "2026-09-18", "date_bs": "2083-06-02"},
            {"batch_number": "BATCH-2026-09-02", "product": created_products["LIVO-M-RUN-BLK-43"], "qty": 120.0, "workers": 6, "date_ad": "2026-09-19", "date_bs": "2083-06-03"},
            {"batch_number": "BATCH-2026-09-03", "product": created_products["LIVO-M-CAS-BRN-41"], "qty": 80.0, "workers": 5, "date_ad": "2026-09-20", "date_bs": "2083-06-04"},
            {"batch_number": "BATCH-2026-09-04", "product": created_products["LIVO-W-TRL-WHT-38"], "qty": 110.0, "workers": 7, "date_ad": "2026-09-21", "date_bs": "2083-06-05"},
            {"batch_number": "BATCH-2026-09-05", "product": created_products["LIVO-K-SCH-BLK-32"], "qty": 200.0, "workers": 10, "date_ad": "2026-09-22", "date_bs": "2083-06-06"},
        ]
        for b in batches_data:
            existing_batch = db.query(ProductionBatch).filter(
                ProductionBatch.batch_number == b["batch_number"],
                ProductionBatch.company_id == company_id
            ).first()
            if not existing_batch:
                batch = ProductionBatch(
                    company_id=company_id,
                    batch_number=b["batch_number"],
                    product_id=b["product"].id,
                    target_quantity=b["qty"],
                    produced_quantity=b["qty"],
                    worker_count=b["workers"],
                    status="completed",
                    date_ad=b["date_ad"],
                    date_bs=b["date_bs"],
                    notes=f"Production of {b['product'].name} Size {b['product'].size}"
                )
                db.add(batch)
                db.commit()
                db.refresh(batch)

                # Ledger IN movement
                sm = StockMovement(
                    company_id=company_id,
                    product_id=b["product"].id,
                    quantity=b["qty"],
                    direction=1,
                    ref_type="production",
                    ref_id=batch.id,
                    date_ad=b["date_ad"],
                    date_bs=b["date_bs"],
                    notes=f"Production Batch {b['batch_number']}"
                )
                db.add(sm)
                db.commit()
        print(f"  Seeded {len(batches_data)} production batches with Stock (+IN) movements")

        # 8. Clients
        clients_data = [
            {"code": "CLI-KTM-01", "name": "Bhatbhateni Supermarket Footwear Section", "contact_person": "Prakash Thapa", "phone": "+977-9851122334", "address": "Naxal, Kathmandu", "credit_limit": 500000.0},
            {"code": "CLI-PKR-02", "name": "Annapurna Shoe Palace", "contact_person": "Sanjay Gurung", "phone": "+977-9846011223", "address": "Mahendrapool, Pokhara", "credit_limit": 250000.0},
            {"code": "CLI-BRT-03", "name": "Eastern Wholesale Footwear Hub", "contact_person": "Anil Agarwal", "phone": "+977-9802033445", "address": "Main Road, Biratnagar", "credit_limit": 400000.0},
        ]
        created_clients = {}
        for c in clients_data:
            existing = db.query(Client).filter(Client.code == c["code"], Client.company_id == company_id).first()
            if not existing:
                existing = Client(company_id=company_id, **c)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            created_clients[c["code"]] = existing
        print(f"  Seeded {len(created_clients)} retail/wholesale clients")

        # 9. Sales Orders & Invoices & Stock Movements (-OUT)
        sales_orders_data = [
            {
                "order_number": "ORD-2026-09-001",
                "client": created_clients["CLI-KTM-01"],
                "date_ad": "2026-09-23",
                "date_bs": "2083-06-07",
                "received_amount": 75000.0,
                "vat_enabled": True,
                "items": [
                    {"product": created_products["LIVO-M-RUN-BLK-42"], "qty": 20.0, "rate": 2450.0},
                    {"product": created_products["LIVO-M-RUN-BLK-43"], "qty": 15.0, "rate": 2450.0},
                ]
            },
            {
                "order_number": "ORD-2026-09-002",
                "client": created_clients["CLI-PKR-02"],
                "date_ad": "2026-09-24",
                "date_bs": "2083-06-08",
                "received_amount": 50000.0,
                "vat_enabled": False,
                "items": [
                    {"product": created_products["LIVO-M-CAS-BRN-41"], "qty": 18.0, "rate": 3100.0},
                    {"product": created_products["LIVO-W-TRL-WHT-38"], "qty": 25.0, "rate": 2200.0},
                ]
            },
            {
                "order_number": "ORD-2026-09-003",
                "client": created_clients["CLI-BRT-03"],
                "date_ad": "2026-09-25",
                "date_bs": "2083-06-09",
                "received_amount": 42000.0,
                "vat_enabled": True,
                "items": [
                    {"product": created_products["LIVO-K-SCH-BLK-32"], "qty": 30.0, "rate": 1400.0},
                ]
            },
        ]

        seq = 0
        for ord_data in sales_orders_data:
            existing_ord = db.query(SalesOrder).filter(
                SalesOrder.order_number == ord_data["order_number"],
                SalesOrder.company_id == company_id
            ).first()
            if not existing_ord:
                total_amt = sum(it["qty"] * it["rate"] for it in ord_data["items"])
                receivable = total_amt - ord_data["received_amount"]
                order = SalesOrder(
                    company_id=company_id,
                    order_number=ord_data["order_number"],
                    client_id=ord_data["client"].id,
                    order_date_ad=ord_data["date_ad"],
                    order_date_bs=ord_data["date_bs"],
                    status="delivered",
                    total_amount=total_amt,
                    received_amount=ord_data["received_amount"],
                    receivable_amount=receivable,
                    delivered=True
                )
                db.add(order)
                db.commit()
                db.refresh(order)

                for it in ord_data["items"]:
                    line_amt = it["qty"] * it["rate"]
                    db.add(SalesItem(
                        company_id=company_id,
                        sales_order_id=order.id,
                        product_id=it["product"].id,
                        quantity=it["qty"],
                        unit_price=it["rate"],
                        total_price=line_amt
                    ))
                    # Stock OUT movement
                    db.add(StockMovement(
                        company_id=company_id,
                        product_id=it["product"].id,
                        quantity=it["qty"],
                        direction=-1,
                        ref_type="sale",
                        ref_id=order.id,
                        date_ad=ord_data["date_ad"],
                        date_bs=ord_data["date_bs"],
                        notes=f"Sales Order {ord_data['order_number']}"
                    ))

                # Invoice generation (dynamic sequence query respecting DB unique constraint)
                existing_inv = db.query(Invoice).filter(
                    Invoice.sales_order_id == order.id,
                    Invoice.company_id == company_id
                ).first()
                if not existing_inv:
                    max_seq = db.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(
                        Invoice.company_id == company_id
                    ).scalar()
                    next_seq = max_seq + 1
                    subtotal = total_amt
                    vat_rate = 13.0 if ord_data["vat_enabled"] else 0.0
                    vat_amount = subtotal * (vat_rate / 100.0)
                    inv_total = subtotal + vat_amount

                    inv_num = f"INV-{company_id:02d}-{next_seq:05d}"
                    invoice = Invoice(
                        company_id=company_id,
                        sales_order_id=order.id,
                        invoice_number=inv_num,
                        sequence_number=next_seq,
                        date_ad=ord_data["date_ad"],
                        date_bs=ord_data["date_bs"],
                        subtotal=subtotal,
                        vat_enabled=ord_data["vat_enabled"],
                        vat_rate=vat_rate,
                        vat_amount=vat_amount,
                        total_amount=inv_total,
                        received_amount=ord_data["received_amount"],
                        receivable_amount=inv_total - ord_data["received_amount"],
                        is_void=False
                    )
                    db.add(invoice)
                    db.commit()
        print(f"  Seeded {len(sales_orders_data)} sales orders, items, stock (-OUT) movements, and invoices")

        print("\nDemo Data Seed Completed Successfully!")
        print(f"Summary for company '{company.name}':")
        print(f"  Suppliers: {db.query(Supplier).filter(Supplier.company_id == company_id).count()}")
        print(f"  Materials: {db.query(RawMaterial).filter(RawMaterial.company_id == company_id).count()}")
        print(f"  Purchases: {db.query(Purchase).filter(Purchase.company_id == company_id).count()}")
        print(f"  Products:  {db.query(Product).filter(Product.company_id == company_id).count()}")
        print(f"  Batches:   {db.query(ProductionBatch).filter(ProductionBatch.company_id == company_id).count()}")
        print(f"  Clients:   {db.query(Client).filter(Client.company_id == company_id).count()}")
        print(f"  Orders:    {db.query(SalesOrder).filter(SalesOrder.company_id == company_id).count()}")
        print(f"  Stock Movements: {db.query(StockMovement).filter(StockMovement.company_id == company_id).count()}")
        print(f"  Invoices:  {db.query(Invoice).filter(Invoice.company_id == company_id).count()}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo data for LIVO ERP")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL (Postgres or SQLite)")
    args = parser.parse_args()

    target_url = args.db_url
    if not target_url:
        from app.config import settings
        target_url = settings.DATABASE_URL

    seed_demo_data(target_url)
