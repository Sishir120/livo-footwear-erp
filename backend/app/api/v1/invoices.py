from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from app.api.deps import get_db, get_current_user, require_editor
from app.models.user import User
from app.models.company import Company
from app.models.invoice import Invoice
from app.models.sales import SalesOrder, SalesItem, Client
from app.db.repository import TenantRepository

router = APIRouter(prefix="/invoices", tags=["Invoices"])

class InvoiceCreate(BaseModel):
    sales_order_id: int = Field(..., gt=0)
    vat_enabled: bool = False
    vat_rate: float = Field(13.0, ge=0.0, le=100.0)

@router.get("")
def list_invoices(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TenantRepository(Invoice, db, current_user.company_id)
    return repo.get_all()

from sqlalchemy.exc import IntegrityError

@router.post("")
def generate_invoice(data: InvoiceCreate, current_user: User = Depends(require_editor), db: Session = Depends(get_db)):
    invoice_repo = TenantRepository(Invoice, db, current_user.company_id)
    order_repo = TenantRepository(SalesOrder, db, current_user.company_id)

    order = order_repo.get_by_id(data.sales_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Sales order not found")

    subtotal = order.total_amount
    vat_amount = (subtotal * (data.vat_rate / 100.0)) if data.vat_enabled else 0.0
    total_amount = subtotal + vat_amount

    # Retry loop to handle concurrent request sequence number collisions safely under the DB unique constraint
    max_retries = 3
    for attempt in range(max_retries):
        max_seq = db.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(
            Invoice.company_id == current_user.company_id
        ).scalar()

        next_seq = max_seq + 1
        invoice_num = f"INV-{current_user.company_id:02d}-{next_seq:05d}"

        try:
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
    """
    invoice_repo = TenantRepository(Invoice, db, current_user.company_id)
    invoice = invoice_repo.get_by_id(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.is_void = True
    db.commit()
    db.refresh(invoice)
    return {"message": "Invoice successfully marked as void", "id": invoice.id, "invoice_number": invoice.invoice_number, "is_void": True}


@router.get("/{invoice_id}/printable", response_class=HTMLResponse)
def get_printable_invoice(invoice_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Renders a clean printable HTML invoice containing Company Name, PAN, Items, Rate, Date,
    Received Amt, Receivable Amt, and optional VAT line per TASKS.md §1.4.
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

    items_html = ""
    for idx, item in enumerate(items, 1):
        prod_name = item.product.name if item.product else f"Product #{item.product_id}"
        items_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{prod_name}</td>
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
        <title>Invoice {invoice.invoice_number} - {company.name}</title>
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
                <div class="company-title">{company.name}</div>
                <div>Address: {company.address or 'Kathmandu, Nepal'} | Phone: {company.phone or '+977-1-4000000'}</div>
                <div>PAN Number: <strong>{company.pan_number or 'N/A'}</strong></div>
            </div>
            <div style="text-align: right;">
                <h2 style="margin: 0; color: #2563eb;">TAX INVOICE</h2>
                <div style="font-size: 16px; margin-top: 5px;"><strong>{invoice.invoice_number}</strong></div>
                <div>Date (AD): {invoice.date_ad} | (BS): {invoice.date_bs}</div>
            </div>
        </div>

        <div class="info-grid">
            <div>
                <strong>Billed To:</strong><br>
                Client: {client.name if client else 'N/A'}<br>
                Address: {client.address if client else 'N/A'}<br>
                Phone: {client.phone if client else 'N/A'}
            </div>
            <div style="text-align: right;">
                <strong>Order Ref:</strong> {order.order_number if order else 'N/A'}<br>
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
