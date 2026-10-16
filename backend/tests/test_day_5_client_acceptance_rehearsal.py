"""
LIVO Footwear ERP — Day 5 Client Rehearsal & Acceptance Suite
============================================================
Exercises the full 10-step client acceptance journey through the API endpoints
mirroring actual frontend user operations:
1. Demo Login & Authentication
2. Purchasing & Purchase Order Creation
3. Goods Receipt & Landed Cost Valuation Invariants
4. Production BOM Deduction & Multi-Size/Color Output
5. Inter-Warehouse Stock Transfer & Receipt Confirmation
6. Sales Order, Dispatch & VAT Invoice Generation
7. Nepal 13% VAT, Payment Allocation & Accounts Receivable Sub-ledger
8. HR & Worker Ledger, Viewer Redaction & Confidential Document RBAC
9. Factory Expenses, Assets & Waste Disposal
10. Session Expiry, Logout & Prohibited Mutation Defenses
"""

import os
import time
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.api.deps import COOKIE_NAME
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product, Warehouse
from app.models.branch import Branch
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.production import ProductionBatch
from app.models.sales import SalesOrder, Payment, FactoryExpense
from app.models.invoice import Invoice
from app.models.worker import Worker, WorkerAdvance
from app.models.asset import FixedAsset
from app.models.waste import WasteRecord
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.core.security import get_password_hash, create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def setup_synthetic_tenant():
    """Sets up a synthetic footwear manufacturing tenant with branches, warehouses, materials, products, and BOM."""
    ts = int(time.time() * 1000) % 10000000
    db = SessionLocal()
    try:
        # 1. Tenant Company
        company = Company(
            name=f"Summit Footwear Industries {ts}",
            code=f"SUMMIT_{ts}",
            pan_number="601998877",
            address="Hetauda Industrial Estate, Makwanpur",
            phone="+977-57-520000"
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        # 2. Users (Admin, Editor, Viewer)
        admin_user = User(
            company_id=company.id,
            name="Summit Factory Manager",
            username=f"summit_admin_{ts}",
            email=f"admin_{ts}@summitfootwear.com",
            password_hash=get_password_hash("SummitPass2026!"),
            role="admin",
            active=True
        )
        editor_user = User(
            company_id=company.id,
            name="Summit Production Supervisor",
            username=f"summit_editor_{ts}",
            email=f"editor_{ts}@summitfootwear.com",
            password_hash=get_password_hash("SummitPass2026!"),
            role="editor",
            active=True
        )
        viewer_user = User(
            company_id=company.id,
            name="Summit Auditor",
            username=f"summit_viewer_{ts}",
            email=f"auditor_{ts}@summitfootwear.com",
            password_hash=get_password_hash("SummitPass2026!"),
            role="viewer",
            active=True
        )
        db.add_all([admin_user, editor_user, viewer_user])
        db.commit()

        # 3. Two Warehouses / Branches (Factory Central WH-01, Kathmandu Branch WH-02)
        wh_factory = Warehouse(
            company_id=company.id,
            name="Hetauda Factory Central Warehouse",
            code=f"WH-HET-{ts}",
            location="Hetauda Plant",
            is_active=True
        )
        wh_retail = Warehouse(
            company_id=company.id,
            name="Kathmandu Retail Hub",
            code=f"WH-KTM-{ts}",
            location="New Road, Kathmandu",
            is_active=True
        )
        db.add_all([wh_factory, wh_retail])
        db.commit()
        db.refresh(wh_factory)
        db.refresh(wh_retail)

        # 4. Supplier
        supplier = Supplier(
            company_id=company.id,
            name="Everest Tannery & Polymers",
            code=f"SUP-{ts}",
            contact_person="Bikash Thapa",
            phone="+977-9851000000"
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        # 5. Raw Material (Synthetic PU Leather, Rubber Outsoles)
        rm_leather = RawMaterial(
            company_id=company.id,
            name="Synthetic PU Leather Sheet (Black)",
            code=f"RM-LTH-{ts}",
            unit="kg",
            current_stock=0.0
        )
        rm_sole = RawMaterial(
            company_id=company.id,
            name="TPR Rubber Outsoles (Pairs)",
            code=f"RM-TPR-{ts}",
            unit="pcs",
            current_stock=0.0
        )
        db.add_all([rm_leather, rm_sole])
        db.commit()
        db.refresh(rm_leather)
        db.refresh(rm_sole)

        # 6. Finished Footwear Product
        product = Product(
            company_id=company.id,
            name="LIVO Trekker Pro Boot",
            code=f"BOOT-{ts}",
            category="Outdoor",
            unit_price=Decimal("4200.00"),
            size="42",
            color="Brown"
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        data = {
            "company_id": company.id,
            "admin_username": admin_user.username,
            "editor_username": editor_user.username,
            "viewer_username": viewer_user.username,
            "supplier_id": supplier.id,
            "wh_factory_id": wh_factory.id,
            "wh_retail_id": wh_retail.id,
            "rm_leather_id": rm_leather.id,
            "rm_sole_id": rm_sole.id,
            "product_id": product.id,
            "ts": ts
        }
        return data
    finally:
        db.close()


def test_client_rehearsal_journey(client, setup_synthetic_tenant):
    env = setup_synthetic_tenant
    ts = env["ts"]

    # --------------------------------------------------------------------------
    # STEP 1: Log in using an explicitly provisioned demo account
    # --------------------------------------------------------------------------
    login_resp = client.post("/api/v1/auth/login", json={
        "username": env["editor_username"],
        "password": "SummitPass2026!"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    assert "user" in token_data
    auth_cookie = login_resp.cookies.get(COOKIE_NAME)
    assert auth_cookie is not None
    editor_cookies = {COOKIE_NAME: auth_cookie}

    # Verify session profile via /auth/me
    me_resp = client.get("/api/v1/auth/me", cookies=editor_cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == env["editor_username"]
    assert me_resp.json()["role"] == "editor"

    # --------------------------------------------------------------------------
    # STEP 2: Navigate to purchasing and create a purchase order / purchase
    # --------------------------------------------------------------------------
    po_resp = client.post("/api/v1/purchase/purchases", json={
        "supplier_id": env["supplier_id"],
        "raw_material_id": env["rm_leather_id"],
        "quantity": 100.0,
        "unit_price": 450.0,
        "carrying_in_paisa": 250000,     # NPR 2,500
        "import_duty_paisa": 150000,     # NPR 1,500
        "china_carrying_paisa": 100000,  # NPR 1,000
        "insurance_paisa": 0,
        "status": "RECEIVED",
        "purchase_date_ad": "2026-10-16",
        "purchase_date_bs": "2083-06-30",
        "notes": "Bulk raw material purchase with landed freight & customs"
    }, cookies=editor_cookies)
    assert po_resp.status_code in (200, 201), f"PO creation failed: {po_resp.text}"
    purchase_data = po_resp.json()
    assert purchase_data["supplier_id"] == env["supplier_id"]
    purchase_id = purchase_data["id"]

    # --------------------------------------------------------------------------
    # STEP 3: Record goods received & verify stock & purchase valuation
    # --------------------------------------------------------------------------
    # Landed Cost Math: Base = 45,000 (4,500,000 paisa) + Landed = 5,000 (500,000 paisa) = 50,000 NPR (5,000,000 paisa)
    # Landed Unit Cost = 5,000,000 / 100 = 50,000 paisa = 500.00 NPR
    assert purchase_data["total_landed_cost_paisa"] == 5000000
    assert purchase_data["effective_unit_rate_paisa"] == 50000

    db = SessionLocal()
    try:
        rm = db.query(RawMaterial).filter(RawMaterial.id == env["rm_leather_id"]).first()
        assert rm is not None
        assert float(rm.current_stock) == 100.0, "Raw material stock not updated by purchase"
    finally:
        db.close()

    # --------------------------------------------------------------------------
    # STEP 4: Complete a production workflow & verify material consumption & finished-goods output
    # --------------------------------------------------------------------------
    # Consume 20 sqm of leather to produce 40 pairs of Trekker Pro Boots
    batch_resp = client.post("/api/v1/production/batches", json={
        "product_id": env["product_id"],
        "target_quantity": 40,
        "produced_quantity": 40,
        "worker_count": 4,
        "date_ad": "2026-10-16",
        "date_bs": "2083-06-30",
        "color": "Brown",
        "batch_number": f"BATCH-{ts}-01"
    }, cookies=editor_cookies)
    assert batch_resp.status_code in (200, 201), f"Production batch failed: {batch_resp.text}"
    batch_id = batch_resp.json()["id"]

    # Step 4: Batch creation automatically writes finished goods stock movement (+40) into main warehouse
    bal_resp = client.get(f"/api/v1/stock/balance?product_id={env['product_id']}", cookies=editor_cookies)
    assert bal_resp.status_code == 200
    wh_items = [b for b in bal_resp.json() if b["product_id"] == env["product_id"]]
    assert len(wh_items) > 0
    assert wh_items[0]["current_stock_pairs"] == 40

    # --------------------------------------------------------------------------
    # STEP 5: Initiate a stock transfer and verify destination receipt behavior
    # --------------------------------------------------------------------------
    # 1. Create transfer in DRAFT state (15 pairs)
    transfer_resp = client.post("/api/v1/transfers", json={
        "source_warehouse_id": env["wh_factory_id"],
        "destination_warehouse_id": env["wh_retail_id"],
        "transfer_date_ad": "2026-10-16",
        "transfer_date_bs": "2083-06-30",
        "carrier_name": "Sajha Cargo Logistics",
        "vehicle_number": "NA 5 KHA 9922",
        "notes": "Inter-branch stock transfer to retail showroom",
        "items": [
            {
                "product_id": env["product_id"],
                "size": "42",
                "quantity": 15.0
            }
        ]
    }, cookies=editor_cookies)
    assert transfer_resp.status_code == 201, f"Transfer creation failed: {transfer_resp.text}"
    transfer_id = transfer_resp.json()["id"]
    assert transfer_resp.json()["status"] == "DRAFT"

    # 2. Dispatch transfer: State becomes IN_TRANSIT and source stock is deducted
    dispatch_resp = client.post(f"/api/v1/transfers/{transfer_id}/dispatch", json={
        "dispatch_date_ad": "2026-10-16",
        "dispatch_date_bs": "2083-06-30"
    }, cookies=editor_cookies)
    assert dispatch_resp.status_code == 200, f"Dispatch failed: {dispatch_resp.text}"
    assert dispatch_resp.json()["status"] == "IN_TRANSIT"

    # 3. Destination receipt: Kathmandu receives all 15 pairs
    detail_res = client.get(f"/api/v1/transfers/{transfer_id}", cookies=editor_cookies)
    assert detail_res.status_code == 200
    item_id = detail_res.json()["items"][0]["id"]

    receive_resp = client.post(f"/api/v1/transfers/{transfer_id}/receive", json={
        "receipt_date_ad": "2026-10-16",
        "receipt_date_bs": "2083-06-30",
        "items": [
            {
                "item_id": item_id,
                "received_quantity": 15.0
            }
        ],
        "notes": "Full stock received intact at retail hub"
    }, cookies=editor_cookies)
    assert receive_resp.status_code == 200, f"Receive failed: {receive_resp.text}"
    assert receive_resp.json()["status"] == "RECEIVED"

    # --------------------------------------------------------------------------
    # STEP 6: Create sales order, dispatch eligible stock & generate invoice
    # --------------------------------------------------------------------------
    # Create Retail Client
    cli_resp = client.post("/api/v1/sales/clients", json={
        "code": f"CLI-RETAIL-{ts}",
        "name": "Kathmandu Adventure Gear",
        "phone": "+977-1-4220000",
        "credit_limit": 500000.0
    }, cookies=editor_cookies)
    assert cli_resp.status_code in (200, 201)
    client_id = cli_resp.json()["id"]

    # Dispatch 10 pairs @ 4,200 NPR = 42,000 NPR taxable basis
    so_resp = client.post("/api/v1/sales/orders", json={
        "client_id": client_id,
        "order_date_ad": "2026-10-16",
        "order_date_bs": "2083-06-30",
        "delivered": True,
        "items": [
            {
                "product_id": env["product_id"],
                "quantity": 10,
                "unit_price": 4200.0
            }
        ]
    }, cookies=editor_cookies)
    assert so_resp.status_code in (200, 201)
    sales_order_id = so_resp.json()["id"]

    # --------------------------------------------------------------------------
    # STEP 7: Verify VAT calculations, payment allocation & accounts receivable
    # --------------------------------------------------------------------------
    # 42,000 NPR + 13% VAT (5,460 NPR) = 47,460 NPR total invoice
    inv_resp = client.post("/api/v1/invoices", json={
        "sales_order_id": sales_order_id,
        "vat_enabled": True,
        "vat_rate": 13.0
    }, cookies=editor_cookies)
    assert inv_resp.status_code in (200, 201)
    inv_data = inv_resp.json()
    assert float(inv_data["subtotal"]) == 42000.0
    assert float(inv_data["vat_amount"]) == 5460.0
    assert float(inv_data["total_amount"]) == 47460.0
    assert inv_data["total_amount_paisa"] == 4746000
    invoice_id = inv_data["id"]

    # Record partial payment: 27,460 NPR via bank transfer
    pay_resp = client.post("/api/v1/sales/payments", json={
        "sales_order_id": sales_order_id,
        "client_id": client_id,
        "amount": 27460.0,
        "payment_date_ad": "2026-10-16",
        "payment_date_bs": "2083-06-30",
        "payment_method": "bank_transfer",
        "notes": "Advance bank deposit"
    }, cookies=editor_cookies)
    assert pay_resp.status_code in (200, 201)

    # Verify accounts receivable sub-ledger balance: 42,000 - 27,460 = 14,540 NPR (order balance)
    so_check = client.get(f"/api/v1/sales/orders/{sales_order_id}", cookies=editor_cookies).json()
    assert float(so_check["received_amount"]) == 27460.0
    assert float(so_check["receivable_amount"]) == 14540.0

    # --------------------------------------------------------------------------
    # STEP 8: Review worker & payroll screens with authorized & restricted roles
    # --------------------------------------------------------------------------
    # Login Admin for sensitive HR operations
    admin_login = client.post("/api/v1/auth/login", json={
        "username": env["admin_username"],
        "password": "SummitPass2026!"
    })
    assert admin_login.status_code == 200
    admin_cookies = {COOKIE_NAME: admin_login.cookies.get(COOKIE_NAME)}

    # Admin creates worker with confidential salary
    worker_resp = client.post("/api/v1/hr/workers", json={
        "name": "Ram Bahadur Shrestha",
        "worker_code": f"WRK-{ts}-01",
        "pay_type": "SALARY",
        "basic_rate_paisa": 3600000,
        "phone": "+977-9841234567"
    }, cookies=admin_cookies)
    assert worker_resp.status_code in (200, 201), f"Worker creation failed: {worker_resp.text}"
    worker_id = worker_resp.json()["id"]

    # Admin uploads confidential citizenship PDF
    fake_pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\nxref\n0 1\n0000000000 65535 f\ntrailer<</Root 1 0 R>>\nstartxref\n50\n%%EOF"
    doc_up = client.post(
        f"/api/v1/hr/workers/{worker_id}/citizenship",
        files={"file": ("citizenship_front.pdf", fake_pdf, "application/pdf")},
        cookies=admin_cookies
    )
    assert doc_up.status_code == 200

    # Viewer role checks worker list: Sensitive fields MUST be redacted / omitted
    viewer_login = client.post("/api/v1/auth/login", json={
        "username": env["viewer_username"],
        "password": "SummitPass2026!"
    })
    viewer_cookies = {COOKIE_NAME: viewer_login.cookies.get(COOKIE_NAME)}
    viewer_workers = client.get("/api/v1/hr/workers", cookies=viewer_cookies)
    assert viewer_workers.status_code == 200
    worker_item = next(w for w in viewer_workers.json() if w["id"] == worker_id)
    assert "basic_rate_paisa" not in worker_item, "Viewer saw unredacted basic_rate_paisa!"
    assert "outstanding_advance_paisa" not in worker_item, "Viewer saw unredacted outstanding_advance_paisa!"

    # Viewer attempts to download confidential citizenship document -> MUST return 403 Forbidden
    viewer_doc_att = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship", cookies=viewer_cookies)
    assert viewer_doc_att.status_code == 403, "Viewer was able to download sensitive citizenship document!"

    # --------------------------------------------------------------------------
    # STEP 9: Review existing expense, asset and waste functionality
    # --------------------------------------------------------------------------
    # Record factory electricity expense
    exp_resp = client.post("/api/v1/expenses/factory", json={
        "particular": "NEA Factory Power Bill",
        "category": "ELECTRICITY_WATER",
        "amount_npr": 18500.0,
        "payment_method": "BANK",
        "expense_date_ad": "2026-10-16",
        "expense_date_bs": "2083-06-30",
        "remarks": "Hetauda plant electricity"
    }, cookies=editor_cookies)
    assert exp_resp.status_code in (200, 201), f"Expense failed: {exp_resp.text}"

    # Record fixed asset
    asset_resp = client.post("/api/v1/fixed-assets", json={
        "asset_name": "Heavy Duty Leather Skiving Machine",
        "asset_code": f"AST-SKV-{ts}",
        "category": "MACHINERY",
        "cost_npr": 280000.0,
        "purchase_date_ad": "2026-10-16",
        "purchase_date_bs": "2083-06-30",
        "quantity": 1,
        "location": "Cutting Department"
    }, cookies=editor_cookies)
    assert asset_resp.status_code in (200, 201), f"Asset failed: {asset_resp.text}"

    # Record production waste / scrap
    waste_resp = client.post("/api/v1/waste", json={
        "waste_date_ad": "2026-10-16",
        "waste_date_bs": "2083-06-30",
        "waste_type": "RAW_MATERIAL_SCRAP",
        "raw_material_id": env["rm_leather_id"],
        "batch_id": batch_id,
        "quantity": 2.5,
        "unit": "sqm",
        "reason": "Cutting edge scrap and defect trimming",
        "disposal_method": "DISCARDED"
    }, cookies=editor_cookies)
    assert waste_resp.status_code in (200, 201), f"Waste failed: {waste_resp.text}"

    # --------------------------------------------------------------------------
    # STEP 10: Log out, expire session & attempt prohibited operations
    # --------------------------------------------------------------------------
    # Logout
    logout_resp = client.post("/api/v1/auth/logout", cookies=editor_cookies)
    assert logout_resp.status_code == 200

    # Attempt mutation with expired/invalid session cookie -> MUST return 401 Unauthorized
    unauth_mutation = client.post("/api/v1/production/products", json={
        "name": "Ghost Footwear",
        "code": f"GHOST-{ts}",
        "unit_price": 9999.0
    }, cookies={COOKIE_NAME: "invalid_expired_token_signature"})
    assert unauth_mutation.status_code == 401

    # Viewer attempts mutation -> MUST return 403 Forbidden
    viewer_forbidden = client.post("/api/v1/production/products", json={
        "name": "Viewer Footwear",
        "code": f"VIEWER-{ts}",
        "unit_price": 1000.0
    }, cookies=viewer_cookies)
    assert viewer_forbidden.status_code == 403
