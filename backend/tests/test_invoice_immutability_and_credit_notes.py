import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.company import Company
from app.models.user import User
from app.core.security import get_password_hash
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry

@pytest.fixture
def setup_immutability_env():
    db = SessionLocal()
    try:
        # Create or fetch tenant company
        company = db.query(Company).filter(Company.name == "Immutability Test Footwear Ltd").first()
        if not company:
            company = Company(name="Immutability Test Footwear Ltd", code="IMM-CO-1", pan_number="309999999")
            db.add(company)
            db.commit()
            db.refresh(company)

        # Editor user
        editor = db.query(User).filter(User.username == "imm_editor").first()
        if not editor:
            editor = User(
                company_id=company.id,
                username="imm_editor",
                name="Immutability Editor",
                password_hash=get_password_hash("ImmPass2026!"),
                role="editor",
                active=True
            )
            db.add(editor)

        # Viewer user
        viewer = db.query(User).filter(User.username == "imm_viewer").first()
        if not viewer:
            viewer = User(
                company_id=company.id,
                username="imm_viewer",
                name="Immutability Viewer",
                password_hash=get_password_hash("ImmPass2026!"),
                role="viewer",
                active=True
            )
            db.add(viewer)

        # Warehouse
        wh = db.query(Warehouse).filter(Warehouse.company_id == company.id).first()
        if not wh:
            wh = Warehouse(company_id=company.id, name="Imm Warehouse", code="WH-IMM-1", is_active=True)
            db.add(wh)

        db.commit()
        yield {"company_id": company.id}
    finally:
        db.close()


def _login(client: TestClient, username: str = "imm_editor"):
    from app.core.security import create_access_token
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        token = create_access_token({
            "user_id": user.id,
            "company_id": user.company_id,
            "role": user.role,
            "username": user.username
        })
        client.headers["Authorization"] = f"Bearer {token}"
    finally:
        db.close()


def _setup_product_and_order(client: TestClient, sku: str, price: float = 1000.0, qty: int = 5):
    # Create product via production router
    p_res = client.post("/api/v1/production/products", json={
        "code": sku,
        "name": f"Test Model {sku}",
        "category": "Shoe",
        "size": "42",
        "color": "Black",
        "unit_price": price
    })
    assert p_res.status_code == 200
    p_id = p_res.json()["id"]

    # Initial stock so order can be confirmed without insufficient stock error
    m_res = client.post("/api/v1/stock/movements", json={
        "product_id": p_id,
        "quantity": 100.0,
        "direction": 1,
        "reference_type": "production",
        "notes": f"Initial stock for {sku}"
    })
    assert m_res.status_code == 200

    # Create client
    c_res = client.post("/api/v1/sales/clients", json={
        "code": f"CLI-{sku}",
        "name": f"Client for {sku}",
        "credit_limit": 500000.0
    })
    assert c_res.status_code == 200
    c_id = c_res.json()["id"]

    # Create order
    o_res = client.post("/api/v1/sales/orders", json={
        "client_id": c_id,
        "order_date_ad": "2026-10-15",
        "order_date_bs": "2083-06-29",
        "status": "CONFIRMED",
        "items": [{"product_id": p_id, "quantity": qty, "unit_price": price}]
    })
    assert o_res.status_code == 200
    return o_res.json()["id"], p_id, c_id


def test_finalized_invoice_financial_mutation_rejected(setup_immutability_env):
    """Verifies that an issued tax invoice rejects any financial modification attempts."""
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, _ = _setup_product_and_order(client, "IMM-SKU-01", 1000.0, 5)

        # Issue finalized invoice
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert inv_res.status_code == 200
        inv_data = inv_res.json()
        inv_id = inv_data["id"]
        assert inv_data["invoice_number"].startswith("INV-")

        # Attempt to edit discount (financial field)
        patch_res = client.patch(f"/api/v1/invoices/{inv_id}", json={"discount_amount": 500.0})
        assert patch_res.status_code == 400
        assert "immutable" in patch_res.json()["detail"].lower()

        # Attempt to change tax exemption (financial field)
        patch_res2 = client.patch(f"/api/v1/invoices/{inv_id}", json={"is_tax_exempt": True})
        assert patch_res2.status_code == 400
        assert "immutable" in patch_res2.json()["detail"].lower()

        # Attempt to change pricing mode (financial field)
        patch_res3 = client.patch(f"/api/v1/invoices/{inv_id}", json={"pricing_mode": "VAT_INCLUSIVE"})
        assert patch_res3.status_code == 400
        assert "immutable" in patch_res3.json()["detail"].lower()


def test_finalized_invoice_non_financial_edits_allowed(setup_immutability_env):
    """Verifies that non-financial metadata edits (notes) succeed on finalized invoices."""
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, _ = _setup_product_and_order(client, "IMM-SKU-02", 1000.0, 2)

        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        patch_res = client.patch(f"/api/v1/invoices/{inv_id}", json={"notes": "Deliver via Pokhara Express"})
        assert patch_res.status_code == 200


def test_draft_invoice_lifecycle_and_finalization(setup_immutability_env):
    """Verifies that draft invoices can be created, edited financially, and then finalized."""
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, _ = _setup_product_and_order(client, "IMM-SKU-03", 2000.0, 5)

        # 1. Create draft invoice
        draft_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id, "is_draft": True})
        assert draft_res.status_code == 200
        draft_data = draft_res.json()
        draft_id = draft_data["id"]
        assert draft_data["invoice_number"].startswith("DRAFT-")
        assert draft_data["sequence_number"] == 0
        assert float(draft_data["subtotal"]) == 10000.0

        # 2. Edit draft invoice financially (add discount 2,000)
        edit_res = client.patch(f"/api/v1/invoices/{draft_id}", json={"discount_amount": 2000.0})
        assert edit_res.status_code == 200
        edited_data = edit_res.json()
        assert float(edited_data["subtotal"]) == 8000.0
        assert float(edited_data["vat_amount"]) == 1040.0
        assert float(edited_data["total_amount"]) == 9040.0

        # 3. Finalize draft invoice
        fin_res = client.post(f"/api/v1/invoices/{draft_id}/finalize")
        assert fin_res.status_code == 200
        fin_data = fin_res.json()
        assert fin_data["invoice_number"].startswith("INV-")
        assert fin_data["sequence_number"] > 0

        # 4. Once finalized, further financial edits are blocked
        block_res = client.patch(f"/api/v1/invoices/{draft_id}", json={"discount_amount": 1000.0})
        assert block_res.status_code == 400


def test_credit_note_workflow_and_overcredit_rejection(setup_immutability_env):
    """Verifies credit note calculations, multi-credit support, and over-credit protection."""
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, _ = _setup_product_and_order(client, "IMM-SKU-04", 1000.0, 10)

        # Subtotal: 10,000, VAT: 1,300, Total: 11,300 (1,130,000 paisa)
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # Partial credit note 1: Rs. 5,650 (565,000 paisa)
        cn1_res = client.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
            "amount_paisa": 565000,
            "reason": "Return 5 pairs damaged in transit"
        })
        assert cn1_res.status_code == 200
        cn1 = cn1_res.json()
        assert cn1["total_credit_paisa"] == 565000
        assert cn1["taxable_credit_paisa"] == 500000
        assert cn1["vat_credit_paisa"] == 65000
        assert cn1["remaining_creditable_paisa"] == 565000

        # Partial credit note 2: Rs. 5,650 (exhausts remaining balance)
        cn2_res = client.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
            "amount_paisa": 565000,
            "reason": "Final settlement discount"
        })
        assert cn2_res.status_code == 200
        assert cn2_res.json()["remaining_creditable_paisa"] == 0

        # Attempt credit note 3: Over-crediting must be rejected
        cn3_res = client.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
            "amount_paisa": 10000,
            "reason": "Excess credit test"
        })
        assert cn3_res.status_code == 400
        assert "exceeds" in cn3_res.json()["detail"].lower()


def test_unauthorized_user_cannot_mutate_or_credit_invoice(setup_immutability_env):
    """Verifies that viewer role cannot finalize draft invoices or issue credit notes."""
    with TestClient(app) as client:
        _login(client, "imm_viewer")
        # Viewer cannot issue credit note
        cn_res = client.post("/api/v1/invoices/1/credit-note", json={"amount_paisa": 1000, "reason": "Test"})
        assert cn_res.status_code in (401, 403)

        # Viewer cannot finalize invoice
        fin_res = client.post("/api/v1/invoices/1/finalize")
        assert fin_res.status_code in (401, 403)


def test_draft_invoice_cancellation_does_not_post_ar_reversal(setup_immutability_env):
    """
    Adversarial Accounting Invariant Test:
    Draft invoices never posted an initial debit to customer AR.
    Therefore, voiding a draft must NEVER write a VOID_REVERSAL to AR.
    """
    env = setup_immutability_env
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, client_id = _setup_product_and_order(client, "IMM-DRAFT-CANCEL", 1000.0, 3)

        # 1. Create draft invoice
        draft_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id, "is_draft": True})
        assert draft_res.status_code == 200
        draft_id = draft_res.json()["id"]

        db = SessionLocal()
        try:
            # Check AR count for this invoice before cancel (should be 0)
            initial_ar = db.query(ReceivableEntry).filter(ReceivableEntry.invoice_id == draft_id).count()
            assert initial_ar == 0
        finally:
            db.close()

        # 2. Cancel draft invoice
        canc_res = client.post(f"/api/v1/invoices/{draft_id}/cancel")
        assert canc_res.status_code == 200
        assert canc_res.json()["is_void"] is True

        # 3. Check AR count after cancel (must still be 0! No phantom negative AR!)
        db = SessionLocal()
        try:
            after_ar = db.query(ReceivableEntry).filter(ReceivableEntry.invoice_id == draft_id).count()
            assert after_ar == 0
        finally:
            db.close()


def test_finalized_invoice_with_credit_notes_cannot_be_voided(setup_immutability_env):
    """
    Adversarial Statutory VAT Invariant Test:
    Under Nepal VAT rules, once Schedule-10 credit notes are issued against an invoice,
    voiding the original invoice is blocked to preserve Schedule-10 audit matching.
    """
    with TestClient(app) as client:
        _login(client, "imm_editor")
        order_id, _, _ = _setup_product_and_order(client, "IMM-CN-NOVOID", 1000.0, 5)

        # Issue finalized invoice
        inv_res = client.post("/api/v1/invoices", json={"sales_order_id": order_id})
        assert inv_res.status_code == 200
        inv_id = inv_res.json()["id"]

        # Issue partial credit note
        cn_res = client.post(f"/api/v1/invoices/{inv_id}/credit-note", json={
            "amount_paisa": 100000,
            "reason": "Damaged goods return"
        })
        assert cn_res.status_code == 200

        # Attempt to void the invoice -> must be blocked
        void_res = client.post(f"/api/v1/invoices/{inv_id}/cancel")
        assert void_res.status_code == 400
        assert "credit notes have already been issued" in void_res.json()["detail"].lower()
