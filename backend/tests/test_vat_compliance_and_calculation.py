"""
LIVO Footwear ERP — Nepal Statutory 13% VAT Compliance & Calculation Test Suite
=============================================================================
Mandatory Verification Suite covering all 12 VAT test scenarios per specifications:
1. Taxable invoice with a known VAT-exclusive subtotal
2. Taxable invoice with a discount
3. VAT-inclusive invoice with correct extraction
4. Multiple line items with consistent rounding
5. Exempt / non-taxable item
6. Invoice edit changing taxable amount & recalculating VAT
7. Return or credit note (अनुसूची-१०) with VAT reduction
8. Duplicate submission & idempotency / concurrency conflict prevention
9. Persisted VAT values matching JSON API and printable Schedule-5 HTML output
10. Invoice totals reconciling with customer accounts receivable subledger
11. Historical finalized invoices retaining original tax values
12. Server-side rejection and authoritative correction of tampered client tax payloads
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, StockMovement, SalesOrder, SalesItem, Invoice
from app.models.receivable import ReceivableEntry
from app.core.security import get_password_hash


@pytest.fixture(scope="module")
def setup_vat_test_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "LIVO_VAT_TEST").first()
    if not comp:
        comp = Company(name="LIVO VAT TEST INDUSTRIES PVT. LTD.", code="LIVO_VAT_TEST", pan_number="609823412")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id, Warehouse.code == "WH-VAT-01").first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="VAT Test Warehouse", code="WH-VAT-01", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    editor = db.query(User).filter(User.username == "vat_editor").first()
    if not editor:
        editor = User(
            company_id=comp.id,
            name="VAT Compliance Officer",
            username="vat_editor",
            password_hash=get_password_hash("VatPass2026!"),
            role="editor",
            active=True
        )
        db.add(editor)
        db.commit()

    db.close()
    return comp.id


def _create_product_and_stock(client, code, name, unit_price, qty=100.0):
    p_res = client.post("/api/v1/production/products", json={
        "code": code,
        "name": name,
        "category": "Boot",
        "size": "42",
        "color": "Black",
        "unit_price": unit_price
    })
    assert p_res.status_code == 200
    prod_id = p_res.json()["id"]

    # Stock movement so ATP passes
    m_res = client.post("/api/v1/stock/movements", json={
        "product_id": prod_id,
        "quantity": qty,
        "direction": 1,
        "reference_type": "production",
        "notes": f"Initial stock for {code}"
    })
    assert m_res.status_code == 200
    return prod_id


def _create_client(client, code, name):
    c_res = client.post("/api/v1/sales/clients", json={
        "code": code,
        "name": name,
        "phone": "9841999999",
        "credit_limit": 5000000.0
    })
    assert c_res.status_code == 200
    return c_res.json()["id"]


# 1. Taxable invoice with a known VAT-exclusive subtotal
def test_1_taxable_invoice_known_vat_exclusive(setup_vat_test_env):
    """
    Subtotal: NPR 1,000.00
    VAT at 13%: NPR 130.00
    Grand Total: NPR 1,130.00
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-EXCL-100", "VAT Exclusive Model", 1000.0)
        c_id = _create_client(client, "CLI-EXCL-1", "Distributor Alpha")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 1000.0}]
        })
        assert o_res.status_code in (200, 201)
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "pricing_mode": "VAT_EXCLUSIVE"
        })
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert float(inv["subtotal"]) == 1000.0
        assert float(inv["vat_amount"]) == 130.0
        assert float(inv["total_amount"]) == 1130.0
        assert inv["vat_amount_paisa"] == 13000
        assert inv["total_amount_paisa"] == 113000
        assert inv["vat_enabled"] is True
        assert float(inv["vat_rate"]) == 13.0


# 2. Taxable invoice with a discount
def test_2_taxable_invoice_with_discount(setup_vat_test_env):
    """
    Subtotal: NPR 10,000.00 (10 pairs @ 1,000)
    Discount: NPR 1,000.00
    Taxable amount: NPR 9,000.00
    VAT at 13%: NPR 1,170.00 (9,000 * 0.13)
    Grand Total: NPR 10,170.00 (9,000 + 1,170)
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-DISC-100", "Discounted Model", 1000.0)
        c_id = _create_client(client, "CLI-DISC-1", "Distributor Beta")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 10, "unit_price": 1000.0}]
        })
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "pricing_mode": "VAT_EXCLUSIVE",
            "discount_amount": 1000.0
        })
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert float(inv["subtotal"]) == 9000.0
        assert float(inv["vat_amount"]) == 1170.0
        assert float(inv["total_amount"]) == 10170.0
        assert inv["vat_amount_paisa"] == 117000
        assert inv["total_amount_paisa"] == 1017000


# 3. VAT-inclusive invoice
def test_3_vat_inclusive_pricing_mode(setup_vat_test_env):
    """
    Inclusive Total: NPR 11,300.00
    Extracted Taxable Amount: NPR 10,000.00 (11,300 / 1.13)
    Extracted VAT: NPR 1,300.00 (11,300 - 10,000)
    Grand Total: NPR 11,300.00
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-INCL-100", "Inclusive Model", 11300.0)
        c_id = _create_client(client, "CLI-INCL-1", "Retail Counter Client")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 11300.0}]
        })
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "pricing_mode": "VAT_INCLUSIVE"
        })
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert float(inv["subtotal"]) == 10000.0
        assert float(inv["vat_amount"]) == 1300.0
        assert float(inv["total_amount"]) == 11300.0
        assert inv["vat_amount_paisa"] == 130000
        assert inv["total_amount_paisa"] == 1130000


# 4. Multiple line items with consistent rounding
def test_4_multiple_line_items_rounding(setup_vat_test_env):
    """
    Line 1: 3 pairs @ 1250.50 = 3751.50
    Line 2: 7 pairs @ 830.25 = 5811.75
    Total Taxable: 9563.25
    VAT at 13%: round(9563.25 * 0.13) = round(1243.2225) = 1243.22
    Grand Total: 9563.25 + 1243.22 = 10806.47
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p1 = _create_product_and_stock(client, "VAT-MULTI-1", "Model 1", 1250.50)
        p2 = _create_product_and_stock(client, "VAT-MULTI-2", "Model 2", 830.25)
        c_id = _create_client(client, "CLI-MULTI-1", "Multi-Line Wholesaler")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [
                {"product_id": p1, "quantity": 3, "unit_price": 1250.50},
                {"product_id": p2, "quantity": 7, "unit_price": 830.25}
            ]
        })
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert float(inv["subtotal"]) == 9563.25
        assert float(inv["vat_amount"]) == 1243.22
        assert float(inv["total_amount"]) == 10806.47


# 5. Exempt or non-taxable item
def test_5_tax_exempt_invoice(setup_vat_test_env):
    """
    Subtotal: NPR 5,000.00
    Exempt: True
    VAT at 0%: NPR 0.00
    Grand Total: NPR 5,000.00
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-EXEMPT-01", "Exempt Export Footwear", 5000.0)
        c_id = _create_client(client, "CLI-EXEMPT-1", "Foreign Export Partner")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 5000.0}]
        })
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "is_tax_exempt": True
        })
        assert inv_res.status_code in (200, 201)
        inv = inv_res.json()

        assert float(inv["subtotal"]) == 5000.0
        assert float(inv["vat_amount"]) == 0.0
        assert float(inv["total_amount"]) == 5000.0
        assert inv["vat_enabled"] is False
        assert float(inv["vat_rate"]) == 0.0


# 6. Invoice edit that changes the taxable amount
def test_6_invoice_edit_changes_taxable_and_vat(setup_vat_test_env):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-EDIT-01", "Editable Model", 2000.0)
        c_id = _create_client(client, "CLI-EDIT-1", "Editable Client")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 5, "unit_price": 2000.0}]  # 10,000 NPR
        })
        order_id = o_res.json()["id"]

        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        inv_id = inv_res.json()["id"]

        # Edit invoice to add discount of NPR 2,000 (taxable becomes 8,000)
        patch_res = client.patch(f"/api/v1/invoices/{inv_id}", json={
            "discount_amount": 2000.0
        })
        assert patch_res.status_code == 200
        updated_inv = patch_res.json()

        assert float(updated_inv["subtotal"]) == 8000.0
        assert float(updated_inv["vat_amount"]) == 1040.0  # 8000 * 0.13
        assert float(updated_inv["total_amount"]) == 9040.0


# 7. Return or credit note
def test_7_credit_note_reduces_vat_liability(setup_vat_test_env):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-CN-01", "Credit Note Model", 1000.0)
        c_id = _create_client(client, "CLI-CN-1", "Distributor Gamma")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 10, "unit_price": 1000.0}]
        })
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": o_res.json()["id"]})
        inv_id = inv_res.json()["id"]

        # Issue Credit Note for NPR 1,130 (1000 taxable + 130 VAT)
        cn_res = client.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
            "amount_paisa": 113000,
            "reason": "Damaged goods return - 1 pair"
        })
        assert cn_res.status_code == 200
        cn_data = cn_res.json()
        assert cn_data["total_credit_paisa"] == 113000
        assert cn_data["taxable_credit_paisa"] == 100000
        assert cn_data["vat_credit_paisa"] == 13000


# 8. Duplicate submission & conflict prevention
def test_8_duplicate_invoice_prevention(setup_vat_test_env):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-DUP-01", "Duplicate Guard Model", 1000.0)
        c_id = _create_client(client, "CLI-DUP-1", "Dup Client")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 1000.0}]
        })
        order_id = o_res.json()["id"]

        # First issuance succeeds
        first_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert first_res.status_code in (200, 201)

        # Duplicate issuance returns 409 Conflict
        second_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert second_res.status_code == 409


# 9. Persisted VAT values matching invoice UI, printable output, and PDF
def test_9_persisted_vat_matches_printable_html(setup_vat_test_env):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-PRINT-01", "Printable Model", 2500.0)
        c_id = _create_client(client, "CLI-PRINT-1", "Printable Buyer")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 4, "unit_price": 2500.0}]  # 10,000 NPR
        })
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": o_res.json()["id"]})
        inv = inv_res.json()
        inv_id = inv["id"]

        # Fetch printable HTML
        print_res = client.get(f"/api/v1/invoices/{inv_id}/printable")
        assert print_res.status_code == 200
        html = print_res.text

        # Verify exact Schedule-5 statutory elements in printable output
        assert "TAX INVOICE" in html
        assert "609823412" in html  # PAN Number
        assert "Rs. 10,000.00" in html  # Subtotal
        assert "Rs. 1,300.00" in html   # 13% VAT
        assert "Rs. 11,300.00" in html  # Grand Total
        assert "१३% मूल्य अभिवृद्धि कर" in html


# 10. Invoice totals reconciling with the accounting ledger
def test_10_invoice_reconciles_with_ar_subledger(setup_vat_test_env):
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-AR-01", "AR Ledger Model", 4000.0)
        c_id = _create_client(client, "CLI-AR-1", "AR Ledger Client")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 2, "unit_price": 4000.0}]  # 8,000 NPR
        })
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": o_res.json()["id"]})
        inv = inv_res.json()

        # Grand Total with VAT is 8,000 + 1,040 = 9,040 NPR (904,000 paisa)
        assert inv["total_amount_paisa"] == 904000

        # Verify Receivable Entry matches total_amount_paisa exactly
        db = SessionLocal()
        entry = db.query(ReceivableEntry).filter(
            ReceivableEntry.invoice_id == inv["id"],
            ReceivableEntry.entry_type == "INVOICE_POSTED"
        ).first()
        assert entry is not None
        assert entry.amount_paisa == 904000
        assert entry.direction == 1
        db.close()


# 11. Historical finalized invoices retaining their original tax values
def test_11_historical_invoices_retain_original_tax(setup_vat_test_env):
    """
    Ensures that voiding an invoice or retrieving older invoices does not alter their persisted tax amounts.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-HIST-01", "Historical Model", 1000.0)
        c_id = _create_client(client, "CLI-HIST-1", "Historical Client")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 1000.0}]
        })
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": o_res.json()["id"]})
        inv_id = inv_res.json()["id"]

        # Void invoice
        cancel_res = client.post(f"/api/v1/invoices/{inv_id}/cancel")
        assert cancel_res.status_code == 200

        # Re-fetch invoice: must retain 130 VAT and 1130 Total, with is_void=True
        get_res = client.get(f"/api/v1/invoices/{inv_id}")
        assert get_res.status_code == 200
        hist_inv = get_res.json()
        assert hist_inv["is_void"] is True
        assert float(hist_inv["vat_amount"]) == 130.0
        assert float(hist_inv["total_amount"]) == 1130.0


# 12. Server-side rejection / correction of manipulated client-supplied tax amounts
def test_12_server_corrects_manipulated_client_tax(setup_vat_test_env):
    """
    Adversarial test: client submits tampered vat_amount = 0 on taxable sale.
    Authoritative backend overrides and enforces exact 13% VAT.
    """
    with TestClient(app) as client:
        client.post("/api/v1/auth/login", json={"username": "vat_editor", "password": "VatPass2026!"})
        p_id = _create_product_and_stock(client, "VAT-TAMPER-01", "Tamper Proof Model", 2000.0)
        c_id = _create_client(client, "CLI-TAMPER-1", "Tamper Test Buyer")

        o_res = client.post("/api/v1/sales/orders", json={
            "client_id": c_id,
            "order_date_ad": "2026-10-15",
            "order_date_bs": "2083-06-29",
            "status": "CONFIRMED",
            "items": [{"product_id": p_id, "quantity": 1, "unit_price": 2000.0}]
        })
        order_id = o_res.json()["id"]

        # Attempt to inject 0 VAT
        res = client.post("/api/v1/invoices", json={
            "sales_order_id": order_id,
            "vat_enabled": False,
            "vat_amount": 0.0,
            "vat_rate": 0.0
        })
        assert res.status_code in (200, 201)
        inv = res.json()

        # Authoritative backend recalculated to 13% statutory VAT
        assert float(inv["subtotal"]) == 2000.0
        assert float(inv["vat_amount"]) == 260.0
        assert float(inv["total_amount"]) == 2260.0
        assert inv["vat_amount_paisa"] == 26000
        assert inv["total_amount_paisa"] == 226000
