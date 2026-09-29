import html
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.company import Company
from app.models.invoice import Invoice, InvoiceSequence
from app.models.sales import SalesOrder, SalesItem, Client
from app.models.receivable import ReceivableEntry
from app.db.repository import TenantRepository
from app.core.currency import quantize_npr, calculate_vat

router = APIRouter(prefix="/invoices", tags=["Invoices"])

class InvoiceCreate(BaseModel):
    sales_order_id: int = Field(..., gt=0)
    vat_enabled: bool = False
    vat_rate: float = Field(13.0, ge=0.0, le=100.0)

@router.get("")
def list_invoices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(Invoice, db, current_user.company_id)
    return repo.get_all()

def allocate_next_invoice_sequence(db: Session, company_id: int) -> int:
    """
    Allocates the next monotonic sequence number for a company using an atomic row lock
    on invoice_sequences (SELECT ... FOR UPDATE).
    Eliminates race condition collisions and HTTP 409 sequence collision storms in O(1) time.
    """
    seq_row = db.query(InvoiceSequence).filter(
        InvoiceSequence.company_id == company_id
    ).with_for_update().first()

    if not seq_row:
        # Seed initial sequence from max existing invoice sequence for the company
        max_existing = db.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(
            Invoice.company_id == company_id
        ).scalar() or 0
        seq_row = InvoiceSequence(
            company_id=company_id,
            current_sequence=max_existing
        )
        db.add(seq_row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            seq_row = db.query(InvoiceSequence).filter(
                InvoiceSequence.company_id == company_id
            ).with_for_update().first()
            if not seq_row:
                raise

    seq_row.current_sequence += 1
    db.flush()
    return seq_row.current_sequence


@router.post("")
def generate_invoice(data: InvoiceCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    invoice_repo = TenantRepository(Invoice, db, current_user.company_id)
    order_repo = TenantRepository(SalesOrder, db, current_user.company_id)

    order = order_repo.get_by_id(data.sales_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    # Defensive Security & Statutory Invariant: Prevent duplicate tax liabilities
    # Under Nepal IRD Schedule-5 VAT rules, a sales order cannot have duplicate active VAT invoices.
    if data.vat_enabled:
        existing_vat_inv = db.query(Invoice).filter(
            Invoice.sales_order_id == order.id,
            Invoice.company_id == current_user.company_id,
            Invoice.vat_enabled == True,
            Invoice.is_void == False
        ).first()
        if existing_vat_inv:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active tax invoice ({existing_vat_inv.invoice_number}) with VAT liability already exists for Sales Order #{order.id}."
            )

    # Strict Decimal precision with statutory Nepal VAT calculation
    subtotal_taxable, vat_dec, grand_total_dec = calculate_vat(
        order.total_amount,
        vat_enabled=data.vat_enabled,
        custom_rate=Decimal(str(data.vat_rate)) if data.vat_enabled else Decimal("13.0")
    )
    received_dec = quantize_npr(order.received_amount)
    receivable_dec = quantize_npr(grand_total_dec - received_dec)

    subtotal = float(subtotal_taxable)
    vat_amount = float(vat_dec)
    total_amount = float(grand_total_dec)
    receivable_amount = float(receivable_dec)

    # Atomic sequence allocation with bounded fallback retry loop for constraint conflict recovery
    max_retries = 3
    for attempt in range(max_retries):
        try:
            next_seq = allocate_next_invoice_sequence(db, current_user.company_id)
            invoice_num = f"INV-{current_user.company_id:02d}-{next_seq:05d}"

            invoice = invoice_repo.create(
                sales_order_id=order.id,
                invoice_number=invoice_num,
                sequence_number=next_seq,
                date_ad=order.order_date_ad,
                date_bs=order.order_date_bs,
                subtotal=subtotal,
                vat_enabled=data.vat_enabled,
                vat_rate=data.vat_rate if data.vat_enabled else 0.0,
                vat_amount=vat_amount,
                total_amount=total_amount,
                received_amount=order.received_amount,
                receivable_amount=total_amount - order.received_amount,
                is_void=False
            )

            # Statutory AR Subledger posting: INVOICE_POSTED (+1 debit)
            due_dt = None
            if order.order_date_ad:
                try:
                    parsed_d = datetime.strptime(order.order_date_ad, "%Y-%m-%d").date()
                    due_dt = datetime.combine(parsed_d + timedelta(days=30), datetime.min.time(), tzinfo=timezone.utc)
                except Exception:
                    due_dt = datetime.now(timezone.utc) + timedelta(days=30)
            else:
                due_dt = datetime.now(timezone.utc) + timedelta(days=30)

            rec_repo = TenantRepository(ReceivableEntry, db, current_user.company_id)
            rec_repo.create(
                client_id=order.client_id,
                entry_type="INVOICE_POSTED",
                direction=1,
                amount_paisa=int(round(total_amount * 100)),
                source_doc_ref=invoice_num,
                invoice_id=invoice.id,
                actor_id=current_user.id,
                occurred_at=datetime.now(timezone.utc),
                due_date=due_dt,
                is_disputed=False,
                notes=f"Tax invoice {invoice_num} issued for Order #{order.order_number}"
            )

            db.commit()
            return invoice
        except IntegrityError:
            db.rollback()
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Concurrent invoice creation collision. Please try again."
                )


@router.post("/{invoice_id}/cancel")
def cancel_invoice(invoice_id: int, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    """
    Voids an invoice adhering to Nepal statutory VAT rules (RULES.md §2).
    The record is NEVER physically deleted, preserving the sequence and audit trail.
    Writes a matching VOID_REVERSAL entry (-1 direction) to the AR subledger.
    """
    invoice_repo = TenantRepository(Invoice, db, current_user.company_id)
    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.is_void = True

    # Post VOID_REVERSAL to AR subledger
    order = db.query(SalesOrder).filter(SalesOrder.id == invoice.sales_order_id).first()
    if order:
        rec_repo = TenantRepository(ReceivableEntry, db, current_user.company_id)
        rec_repo.create(
            client_id=order.client_id,
            entry_type="VOID_REVERSAL",
            direction=-1,
            amount_paisa=int(round(invoice.total_amount * 100)),
            source_doc_ref=f"VOID-{invoice.invoice_number}",
            invoice_id=invoice.id,
            actor_id=current_user.id,
            occurred_at=datetime.now(timezone.utc),
            due_date=None,
            is_disputed=False,
            notes=f"Void cancellation reversal for {invoice.invoice_number}"
        )

    db.commit()
    db.refresh(invoice)
    return {"message": "Invoice successfully marked as void", "id": invoice.id, "invoice_number": invoice.invoice_number, "is_void": True}


@router.get("/{invoice_id}/printable", response_class=HTMLResponse)
def get_printable_invoice(invoice_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Renders a clean printable HTML invoice containing Company Name, PAN, Items, Rate, Date,
    Received Amt, Receivable Amt, and optional VAT line per TASKS.md §1.4.
    All interpolated fields are strictly sanitized with html.escape() to neutralize Stored XSS.
    """
    invoice_repo = TenantRepository(Invoice, db, current_user.company_id)
    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    company = db.query(Company).filter(Company.id == current_user.company_id).first()
    # RULES.md §0: all business-table queries must carry company_id filter
    order = db.query(SalesOrder).filter(
        SalesOrder.id == invoice.sales_order_id,
        SalesOrder.company_id == current_user.company_id
    ).first()
    client = db.query(Client).filter(
        Client.id == order.client_id,
        Client.company_id == current_user.company_id
    ).first() if order else None
    items = db.query(SalesItem).filter(
        SalesItem.sales_order_id == invoice.sales_order_id,
        SalesItem.company_id == current_user.company_id
    ).all() if order else []

    # Sanitized strings for XSS defense
    safe_company_name = html.escape(company.name if company else "LIVO GROUP OF INDUSTRIES")
    safe_company_address = html.escape((company.address if company and company.address else "Kathmandu, Nepal"))
    safe_company_phone = html.escape((company.phone if company and company.phone else "+977-1-4000000"))
    safe_company_pan = html.escape((company.pan_number if company and company.pan_number else "609823412"))

    safe_inv_num = html.escape(str(invoice.invoice_number))
    safe_date_ad = html.escape(str(invoice.date_ad))
    safe_date_bs = html.escape(str(invoice.date_bs))

    safe_client_name = html.escape(client.name if client else "N/A")
    safe_client_address = html.escape(client.address if client and client.address else "N/A")
    safe_client_phone = html.escape(client.phone if client and client.phone else "N/A")
    safe_order_ref = html.escape(order.order_number if order else "N/A")

    items_html = ""
    for idx, item in enumerate(items, 1):
        raw_prod_name = item.product.name if item.product else f"Product #{item.product_id}"
        safe_prod_name = html.escape(raw_prod_name)
        items_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{safe_prod_name}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{item.quantity:.0f} pairs</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">Rs. {item.unit_price:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">Rs. {item.total_price:,.2f}</td>
        </tr>
        """

    vat_row_html = ""
    if invoice.vat_enabled:
        vat_row_html = f"""
        <tr>
            <td colspan="4" style="text-align: right; padding: 8px; font-weight: bold;">VAT ({invoice.vat_rate}%):</td>
            <td style="text-align: right; padding: 8px; font-weight: bold;">Rs. {invoice.vat_amount:,.2f}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Invoice {safe_inv_num} - {safe_company_name}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; color: #333; }}
            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #2b3a4a; padding-bottom: 15px; margin-bottom: 20px; }}
            .company-title {{ font-size: 24px; font-weight: bold; color: #1a252f; }}
            .badge {{ background: #eef2f5; padding: 4px 8px; border-radius: 4px; font-size: 14px; font-weight: 600; }}
            .info-grid {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th {{ background: #f4f6f8; border: 1px solid #ddd; padding: 10px; text-align: left; }}
            .totals {{ float: right; width: 350px; background: #fafbfc; border: 1px solid #e1e4e8; padding: 15px; border-radius: 6px; }}
            .totals table {{ margin-bottom: 0; }}
            .totals td {{ border: none; padding: 6px 0; }}
            .print-btn {{ display: block; margin-bottom: 20px; background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 15px; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <button class="print-btn" onclick="window.print()">🖨️ Print Invoice</button>
        
        <div class="header">
            <div>
                <div class="company-title">{safe_company_name}</div>
                <div>Address: {safe_company_address} | Phone: {safe_company_phone}</div>
                <div>PAN Number: <strong>{safe_company_pan}</strong></div>
            </div>
            <div style="text-align: right;">
                <h2 style="margin: 0; color: #2563eb;">TAX INVOICE</h2>
                <div style="font-size: 16px; margin-top: 5px;"><strong>{safe_inv_num}</strong></div>
                <div>Date (AD): {safe_date_ad} | (BS): {safe_date_bs}</div>
            </div>
        </div>

        <div class="info-grid">
            <div>
                <strong>Billed To:</strong><br>
                Client: {safe_client_name}<br>
                Address: {safe_client_address}<br>
                Phone: {safe_client_phone}
            </div>
            <div style="text-align: right;">
                <strong>Order Ref:</strong> {safe_order_ref}<br>
                <strong>Payment Status:</strong> <span class="badge">{'PAID' if invoice.receivable_amount <= 0 else 'PARTIAL / UNPAID'}</span>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="text-align: center; width: 50px;">#</th>
                    <th>Item Description</th>
                    <th style="text-align: right;">Quantity</th>
                    <th style="text-align: right;">Rate</th>
                    <th style="text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="totals">
            <table>
                <tr>
                    <td>Subtotal:</td>
                    <td style="text-align: right;">Rs. {invoice.subtotal:,.2f}</td>
                </tr>
                {vat_row_html}
                <tr style="border-top: 2px solid #333; font-weight: bold; font-size: 16px;">
                    <td style="padding-top: 8px;">Grand Total:</td>
                    <td style="text-align: right; padding-top: 8px; color: #1e40af;">Rs. {invoice.total_amount:,.2f}</td>
                </tr>
                <tr>
                    <td style="color: #166534; font-weight: 600;">Received Amount:</td>
                    <td style="text-align: right; color: #166534; font-weight: 600;">Rs. {invoice.received_amount:,.2f}</td>
                </tr>
                <tr>
                    <td style="color: #991b1b; font-weight: 600;">Receivable Balance:</td>
                    <td style="text-align: right; color: #991b1b; font-weight: 600;">Rs. {invoice.receivable_amount:,.2f}</td>
                </tr>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
