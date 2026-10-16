#!/usr/bin/env python3
"""
LIVO Footwear ERP — Authentic Footwear Demo Seeding Script
===========================================================
Populates realistic Nepali industrial footwear manufacturer data for client demonstration:
1. Base Company ('LIVO GROUP OF INDUSTRIES') & Main Warehouse ('WH-MAIN').
2. Standard Demo Personas ('admin_demo' and 'viewer_demo').
3. Core Raw Materials (Rubber Outsoles, Synthetic PU Leather, EVA Sheets, Industrial Adhesive).
4. Authentic Footwear Catalog Models across full Paris Points 32-43 sizing curves:
   - Classic Oxford School Shoes (Sizes 32-38)
   - Urban Glide Casual Sneakers (Sizes 38-43)
   - Sprint Pro EVA Running Shoes (Sizes 39-43)
   - Comfort Trek Summer Sandals (Sizes 37-42)
5. Production Batches and Stock Ledger (+IN) movements with positive inventory curves.
6. Wholesale Clients, Invoiced Sales Orders with decoupled Bikram Sambat 2083 BS dates,
   and partial dispatch tracking.
7. Factory Workers with Advance balances and FIFO recovery records.
"""

import sys
import os
import argparse
from datetime import datetime, date, timezone
from decimal import Decimal

# Ensure backend directory is in python path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.models.company import Company
from app.models.stock import Warehouse, Product, StockMovement
from app.models.user import User
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.production import ProductionBatch
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry
from app.models.worker import Worker, WorkerAdvance
from app.core.security import get_password_hash
from app.config import settings


def seed_footwear_demo(db_url: str):
    print(f"[*] Connecting to database: {db_url}")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 1. Base Tenant Company
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
            print(f"[+] Created tenant company: {company.name}")
        else:
            print(f"[*] Found tenant company: {company.name} (id={company.id})")

        company_id = company.id

        # 2. Main Warehouse
        warehouse = db.query(Warehouse).filter(Warehouse.code == "WH-MAIN", Warehouse.company_id == company_id).first()
        if not warehouse:
            warehouse = Warehouse(
                company_id=company_id,
                name="Main Finished Warehouse",
                code="WH-MAIN",
                location="Factory Premises, Birgunj",
                is_active=True
            )
            db.add(warehouse)
            db.commit()
            db.refresh(warehouse)
            print(f"[+] Created warehouse: {warehouse.name}")

        # 3. Demo Personas
        admin_user = db.query(User).filter(User.username == "admin_demo", User.company_id == company_id).first()
        if not admin_user:
            admin_user = User(
                company_id=company_id,
                name="LIVO System Administrator",
                username="admin_demo",
                email="admin@livogroup.com",
                password_hash=get_password_hash("LivoAdmin2026!"),
                role="admin",
                active=True
            )
            db.add(admin_user)
            print("[+] Created user: admin_demo (role: admin)")

        viewer_user = db.query(User).filter(User.username == "viewer_demo", User.company_id == company_id).first()
        if not viewer_user:
            viewer_user = User(
                company_id=company_id,
                name="LIVO Compliance Auditor",
                username="viewer_demo",
                email="auditor@livogroup.com",
                password_hash=get_password_hash("LivoViewer2026!"),
                role="viewer",
                active=True
            )
            db.add(viewer_user)
            print("[+] Created user: viewer_demo (role: viewer)")

        db.commit()
        db.refresh(admin_user)

        # 4. Raw Materials & Suppliers
        suppliers_data = [
            {"code": "SUP-01", "name": "Himalayan Rubber & Polymer", "contact_person": "Bishnu Shrestha", "phone": "+977-9851011223", "address": "Hetauda"},
            {"code": "SUP-02", "name": "Nepal Synthetic Textiles Ltd", "contact_person": "Gopal Adhikari", "phone": "+977-9841223344", "address": "Biratnagar"},
            {"code": "SUP-03", "name": "Everest Industrial Adhesives", "contact_person": "Sunita Shrestha", "phone": "+977-9803334455", "address": "Kathmandu"},
        ]
        suppliers = {}
        for s in suppliers_data:
            existing = db.query(Supplier).filter(Supplier.code == s["code"], Supplier.company_id == company_id).first()
            if not existing:
                existing = Supplier(company_id=company_id, **s)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            suppliers[s["code"]] = existing

        materials_data = [
            {"code": "RM-SOL-VULC", "name": "Vulcanized Rubber Outsoles", "unit": "pcs", "min_stock_alert": 300.0, "current_stock": 650.0, "reorder_level": 300.0},
            {"code": "RM-SYN-PU", "name": "Synthetic PU Leather (Black & Tan)", "unit": "kg", "min_stock_alert": 150.0, "current_stock": 420.0, "reorder_level": 150.0},
            {"code": "RM-EVA-MID", "name": "High-Density EVA Foam Midsole Sheets", "unit": "pcs", "min_stock_alert": 80.0, "current_stock": 250.0, "reorder_level": 80.0},
            {"code": "RM-ADH-SOLV", "name": "Polyurethane Industrial Adhesive Glue", "unit": "litre", "min_stock_alert": 100.0, "current_stock": 380.0, "reorder_level": 100.0},
        ]
        raw_materials = {}
        for m in materials_data:
            existing = db.query(RawMaterial).filter(RawMaterial.code == m["code"], RawMaterial.company_id == company_id).first()
            if not existing:
                existing = RawMaterial(company_id=company_id, **m)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            raw_materials[m["code"]] = existing
        print(f"[+] Seeded {len(raw_materials)} core footwear raw materials")

        # 5. Footwear Catalog Models across Paris Points 32-43 Curves
        # 4 Core Lines:
        # A. Classic Oxford School Shoes (Black) - Sizes 32 to 38
        # B. Urban Glide Casual Sneakers (Navy/White) - Sizes 38 to 43
        # C. Sprint Pro EVA Running Shoes (Grey/Red) - Sizes 39 to 43
        # D. Comfort Trek Summer Sandals (Tan) - Sizes 37 to 42
        catalog_specs = [
            # School Shoes (Sizes 32-38)
            {"prefix": "LIVO-SCH", "name": "Classic Oxford School Shoe", "category": "School", "color": "Black", "price": 1450.0, "sizes": [("32", 180), ("33", 220), ("34", 260), ("35", 280), ("36", 250), ("37", 200), ("38", 160)]},
            # Casual Sneakers (Sizes 38-43)
            {"prefix": "LIVO-SNK", "name": "Urban Glide Casual Sneaker", "category": "Casual", "color": "Navy Blue", "price": 2850.0, "sizes": [("38", 120), ("39", 180), ("40", 250), ("41", 290), ("42", 240), ("43", 150)]},
            # EVA Running Shoes (Sizes 39-43)
            {"prefix": "LIVO-RUN", "name": "Sprint Pro EVA Running Shoe", "category": "Sports", "color": "Stealth Grey", "price": 3200.0, "sizes": [("39", 140), ("40", 210), ("41", 260), ("42", 230), ("43", 160)]},
            # Summer Sandals (Sizes 37-42)
            {"prefix": "LIVO-SAN", "name": "Comfort Trek Summer Sandal", "category": "Sandals", "color": "Tan Brown", "price": 1850.0, "sizes": [("37", 110), ("38", 160), ("39", 200), ("40", 220), ("41", 190), ("42", 130)]},
        ]

        products = {}
        total_products_created = 0
        total_production_qty = 0

        for line in catalog_specs:
            for size, initial_qty in line["sizes"]:
                code = f"{line['prefix']}-{size}"
                prod = db.query(Product).filter(Product.code == code, Product.company_id == company_id).first()
                if not prod:
                    prod = Product(
                        company_id=company_id,
                        code=code,
                        name=line["name"],
                        category=line["category"],
                        size=size,
                        color=line["color"],
                        unit_price=line["price"]
                    )
                    db.add(prod)
                    db.commit()
                    db.refresh(prod)
                    total_products_created += 1

                products[code] = prod

                # Ensure initial batch & stock ledger +IN movement exists
                batch_num = f"BATCH-INI-{code}"
                existing_batch = db.query(ProductionBatch).filter(ProductionBatch.batch_number == batch_num, ProductionBatch.company_id == company_id).first()
                if not existing_batch:
                    batch = ProductionBatch(
                        company_id=company_id,
                        batch_number=batch_num,
                        product_id=prod.id,
                        target_quantity=initial_qty,
                        produced_quantity=initial_qty,
                        worker_count=8,
                        status="completed",
                        date_ad="2026-09-15",
                        date_bs="2083-05-30",
                        notes=f"Initial Opening Production Run: {line['name']} (Size {size})"
                    )
                    db.add(batch)
                    db.commit()
                    db.refresh(batch)

                    # Stock Movement +IN
                    sm = StockMovement(
                        company_id=company_id,
                        product_id=prod.id,
                        quantity=initial_qty,
                        direction=1,
                        ref_type="production",
                        ref_id=batch.id,
                        date_ad="2026-09-15",
                        date_bs="2083-05-30",
                        notes=f"Opening Finished Goods Stock (Batch {batch_num})"
                    )
                    db.add(sm)
                    db.commit()
                    total_production_qty += initial_qty

        print(f"[+] Footwear catalog seeded: {len(products)} variants across sizes 32-43 (Opening Stock: {total_production_qty} pairs)")

        # 6. Wholesale Clients
        clients_data = [
            {"code": "CLI-KTM-BBD", "name": "Bhatbhateni Department Store (Footwear)", "contact_person": "Prakash Thapa", "phone": "+977-9851122334", "address": "Naxal, Kathmandu", "credit_limit": 800000.0},
            {"code": "CLI-PKR-APS", "name": "Annapurna Footwear Distributors", "contact_person": "Sanjay Gurung", "phone": "+977-9846011223", "address": "Mahendrapool, Pokhara", "credit_limit": 500000.0},
            {"code": "CLI-BRG-HWS", "name": "Himalayan Wholesale Shoes Depot", "contact_person": "Anil Agarwal", "phone": "+977-9802033445", "address": "Main Road, Birgunj", "credit_limit": 600000.0},
        ]
        clients = {}
        for c in clients_data:
            existing = db.query(Client).filter(Client.code == c["code"], Client.company_id == company_id).first()
            if not existing:
                existing = Client(company_id=company_id, **c)
                db.add(existing)
                db.commit()
                db.refresh(existing)
            clients[c["code"]] = existing
        print(f"[+] Seeded {len(clients)} wholesale distribution clients")

        # 7. Sales Orders, Decoupled BS 2083 Dates, Invoices & Dispatch
        # Order 1: Delivered & fully invoiced with 13% VAT (Bhatbhateni)
        # Order 2: Partially dispatched order with decoupled BS dates (Annapurna)
        # Order 3: Confirmed order pending dispatch (Himalayan Wholesale)
        orders_data = [
            {
                "order_number": "ORD-2083-001",
                "client": clients["CLI-KTM-BBD"],
                "order_date_ad": "2026-09-20",
                "order_date_bs": "2083-06-04",
                "dispatch_date_ad": date(2026, 9, 25),
                "dispatch_date_bs": "2083-06-09",
                "status": "DELIVERED",
                "delivered": True,
                "carrier_name": "Sajha Yatayat Cargo",
                "vehicle_number": "BA 2 KHA 4512",
                "dispatch_notes": "Delivered in full to Naxal Central Warehouse",
                "received_amount": 120000.0,
                "vat_enabled": True,
                "items": [
                    {"code": "LIVO-SCH-34", "qty": 40.0, "rate": 1450.0},
                    {"code": "LIVO-SCH-35", "qty": 40.0, "rate": 1450.0},
                    {"code": "LIVO-SNK-41", "qty": 30.0, "rate": 2850.0},
                ]
            },
            {
                "order_number": "ORD-2083-002",
                "client": clients["CLI-PKR-APS"],
                "order_date_ad": "2026-09-28",
                "order_date_bs": "2083-06-12",
                "dispatch_date_ad": date(2026, 10, 2),
                "dispatch_date_bs": "2083-06-16",
                "status": "DISPATCHED",
                "delivered": False,
                "carrier_name": "Pokhara Fast Freight",
                "vehicle_number": "GA 1 KHA 8831",
                "dispatch_notes": "First consignment dispatched via Prithvi Highway route",
                "received_amount": 80000.0,
                "vat_enabled": True,
                "items": [
                    {"code": "LIVO-RUN-41", "qty": 35.0, "rate": 3200.0},
                    {"code": "LIVO-RUN-42", "qty": 30.0, "rate": 3200.0},
                    {"code": "LIVO-SAN-39", "qty": 25.0, "rate": 1850.0},
                ]
            },
            {
                "order_number": "ORD-2083-003",
                "client": clients["CLI-BRG-HWS"],
                "order_date_ad": "2026-10-05",
                "order_date_bs": "2083-06-19",
                "dispatch_date_ad": None,
                "dispatch_date_bs": None,
                "status": "CONFIRMED",
                "delivered": False,
                "carrier_name": None,
                "vehicle_number": None,
                "dispatch_notes": "Awaiting final batch QC inspection before loading",
                "received_amount": 50000.0,
                "vat_enabled": True,
                "items": [
                    {"code": "LIVO-SNK-40", "qty": 20.0, "rate": 2850.0},
                    {"code": "LIVO-SNK-42", "qty": 20.0, "rate": 2850.0},
                    {"code": "LIVO-SAN-40", "qty": 30.0, "rate": 1850.0},
                ]
            }
        ]

        for ord_dict in orders_data:
            existing_ord = db.query(SalesOrder).filter(SalesOrder.order_number == ord_dict["order_number"], SalesOrder.company_id == company_id).first()
            if not existing_ord:
                subtotal = sum(it["qty"] * it["rate"] for it in ord_dict["items"])
                vat_amount = subtotal * 0.13 if ord_dict["vat_enabled"] else 0.0
                total_amt = subtotal + vat_amount
                receivable = total_amt - ord_dict["received_amount"]

                order = SalesOrder(
                    company_id=company_id,
                    order_number=ord_dict["order_number"],
                    client_id=ord_dict["client"].id,
                    order_date_ad=ord_dict["order_date_ad"],
                    order_date_bs=ord_dict["order_date_bs"],
                    dispatch_date_ad=ord_dict["dispatch_date_ad"],
                    dispatch_date_bs=ord_dict["dispatch_date_bs"],
                    status=ord_dict["status"],
                    total_amount=total_amt,
                    received_amount=ord_dict["received_amount"],
                    receivable_amount=receivable,
                    delivered=ord_dict["delivered"],
                    carrier_name=ord_dict["carrier_name"],
                    vehicle_number=ord_dict["vehicle_number"],
                    dispatch_notes=ord_dict["dispatch_notes"],
                    dispatched_at=datetime.now(timezone.utc) if ord_dict["dispatch_date_ad"] else None
                )
                db.add(order)
                db.commit()
                db.refresh(order)

                for it in ord_dict["items"]:
                    prod = products[it["code"]]
                    line_total = it["qty"] * it["rate"]
                    db.add(SalesItem(
                        company_id=company_id,
                        sales_order_id=order.id,
                        product_id=prod.id,
                        quantity=it["qty"],
                        unit_price=it["rate"],
                        total_price=line_total
                    ))

                    # If dispatched or delivered, record stock deduction
                    if ord_dict["status"] in ("DISPATCHED", "DELIVERED"):
                        db.add(StockMovement(
                            company_id=company_id,
                            product_id=prod.id,
                            quantity=it["qty"],
                            direction=-1,
                            ref_type="sale",
                            ref_id=order.id,
                            date_ad=str(ord_dict["dispatch_date_ad"]),
                            date_bs=ord_dict["dispatch_date_bs"],
                            notes=f"Sales Dispatch: {ord_dict['order_number']}"
                        ))

                # If delivered, generate official VAT Invoice
                if ord_dict["status"] == "DELIVERED":
                    max_seq = db.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(Invoice.company_id == company_id).scalar()
                    next_seq = max_seq + 1
                    inv_num = f"INV-2083-{next_seq:04d}"

                    invoice = Invoice(
                        company_id=company_id,
                        sales_order_id=order.id,
                        invoice_number=inv_num,
                        sequence_number=next_seq,
                        date_ad=ord_dict["order_date_ad"],
                        date_bs=ord_dict["order_date_bs"],
                        subtotal=subtotal,
                        vat_enabled=True,
                        vat_rate=13.0,
                        vat_amount=vat_amount,
                        total_amount=total_amt,
                        received_amount=ord_dict["received_amount"],
                        receivable_amount=receivable,
                        is_void=False
                    )
                    db.add(invoice)
                    db.commit()
                    db.refresh(invoice)

                    # Subledger AR entry
                    order_date = datetime.strptime(ord_dict["order_date_ad"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    inv_entry = ReceivableEntry(
                        company_id=company_id,
                        client_id=ord_dict["client"].id,
                        invoice_id=invoice.id,
                        entry_type="INVOICE_POSTED",
                        direction=1,
                        amount_paisa=int(total_amt * 100),
                        source_doc_ref=inv_num,
                        actor_id=admin_user.id,
                        occurred_at=order_date,
                        notes=f"Invoice {inv_num} for Order {ord_dict['order_number']}"
                    )
                    db.add(inv_entry)
                    db.commit()
                    db.refresh(inv_entry)

                    if ord_dict["received_amount"] > 0:
                        pay_entry = ReceivableEntry(
                            company_id=company_id,
                            client_id=ord_dict["client"].id,
                            invoice_id=invoice.id,
                            entry_type="PAYMENT_BANK",
                            direction=-1,
                            amount_paisa=int(ord_dict["received_amount"] * 100),
                            source_doc_ref=f"REC-{inv_num}",
                            actor_id=admin_user.id,
                            occurred_at=order_date,
                            notes=f"Down payment for {inv_num}"
                        )
                        db.add(pay_entry)
                        db.commit()
                else:
                    db.commit()

        print("[+] Seeded wholesale orders with decoupled BS 2083 dates and dispatch records")

        # 8. Factory Workers, Advances, and Installment Recovery
        workers_data = [
            {
                "worker_code": "WKR-101",
                "name": "Ram Bahadur Shrestha",
                "pay_type": "SALARY",
                "basic_rate_paisa": 2500000,  # NPR 25,000 / month
                "phone": "+977-9841556677",
                "permanent_address": "Sindhupalchok, Bagmati",
                "advances": [
                    {
                        "amount_paisa": 1000000,  # NPR 10,000 advance issued
                        "installment_paisa": 250000,  # NPR 2,500 / month installment
                        "date": date(2026, 8, 15),
                        "notes": "Festival Advance: Dashain celebration",
                        "recovery_amount_paisa": 250000,  # 1 installment already recovered
                        "recovery_date": date(2026, 9, 30),
                    }
                ]
            },
            {
                "worker_code": "WKR-202",
                "name": "Sita Kumari Chaudhary",
                "pay_type": "WAGE",
                "basic_rate_paisa": 12000,  # NPR 120 / hour
                "phone": "+977-9801998877",
                "permanent_address": "Dang, Lumbini",
                "advances": [
                    {
                        "amount_paisa": 500000,  # NPR 5,000 advance issued
                        "installment_paisa": 100000,  # NPR 1,000 / month installment
                        "date": date(2026, 9, 1),
                        "notes": "Medical emergency advance",
                        "recovery_amount_paisa": 0,  # No recovery yet
                        "recovery_date": None,
                    }
                ]
            }
        ]

        for w_dict in workers_data:
            worker = db.query(Worker).filter(Worker.worker_code == w_dict["worker_code"], Worker.company_id == company_id).first()
            if not worker:
                worker = Worker(
                    company_id=company_id,
                    worker_code=w_dict["worker_code"],
                    name=w_dict["name"],
                    pay_type=w_dict["pay_type"],
                    basic_rate_paisa=w_dict["basic_rate_paisa"],
                    phone=w_dict["phone"],
                    permanent_address=w_dict["permanent_address"],
                    is_active=True
                )
                db.add(worker)
                db.commit()
                db.refresh(worker)

                for adv_dict in w_dict["advances"]:
                    # Issue advance
                    issued_adv = WorkerAdvance(
                        company_id=company_id,
                        worker_id=worker.id,
                        amount_paisa=adv_dict["amount_paisa"],
                        installment_amount_paisa=adv_dict["installment_paisa"],
                        entry_type="ISSUED",
                        date=adv_dict["date"],
                        notes=adv_dict["notes"],
                        actor_id=admin_user.id
                    )
                    db.add(issued_adv)
                    db.commit()
                    db.refresh(issued_adv)

                    # If recovery exists, record RECOVERED entry linked to parent
                    if adv_dict["recovery_amount_paisa"] > 0:
                        rec_adv = WorkerAdvance(
                            company_id=company_id,
                            worker_id=worker.id,
                            amount_paisa=adv_dict["recovery_amount_paisa"],
                            entry_type="RECOVERED",
                            date=adv_dict["recovery_date"],
                            notes=f"Monthly Installment Deduction for #{issued_adv.id}",
                            actor_id=admin_user.id,
                            parent_advance_id=issued_adv.id
                        )
                        db.add(rec_adv)
                        db.commit()

        print("[+] Seeded factory worker profiles with advances and installment deduction schedules")

        print("\n" + "="*70)
        print(" [SUCCESS] LIVO FOOTWEAR DEMO SEEDING COMPLETED")
        print("="*70)
        print(f"  Company:          {company.name} ({company.code})")
        print(f"  Warehouse:        {warehouse.name} ({warehouse.code})")
        print(f"  Footwear Models:  {db.query(Product).filter(Product.company_id == company_id).count()} variants across sizes 32-43")
        print(f"  Raw Materials:    {db.query(RawMaterial).filter(RawMaterial.company_id == company_id).count()} items")
        print(f"  Sales Orders:     {db.query(SalesOrder).filter(SalesOrder.company_id == company_id).count()} orders")
        print(f"  Tax Invoices:     {db.query(Invoice).filter(Invoice.company_id == company_id).count()} invoices")
        print(f"  Workers Seeded:   {db.query(Worker).filter(Worker.company_id == company_id).count()} profiles")
        print(f"  Demo Credentials: admin_demo / LivoAdmin2026!  (Role: admin)")
        print(f"                    viewer_demo / LivoViewer2026! (Role: viewer)")
        print("="*70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[FATAL ERROR] Seeding failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LIVO ERP Footwear Demo Seeder")
    parser.add_argument("--db-url", default=None, help="Database URL (defaults to DATABASE_URL in config)")
    args = parser.parse_args()

    target_db = args.db_url or settings.DATABASE_URL
    seed_footwear_demo(target_db)
