import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models import Company, Invoice
from app.db.repository import TenantRepository

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    c1 = Company(id=1, name="LIVO GROUP", code="LIVO")
    c2 = Company(id=2, name="Branch Factory", code="BR2")
    session.add_all([c1, c2])
    session.commit()
    
    yield session
    session.close()

def generate_next_invoice(db_session, company_id: int, sales_order_id: int, subtotal: float, vat_enabled: bool = False) -> Invoice:
    """Helper generating sequential immutable invoice numbers per company_id"""
    max_seq = db_session.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(
        Invoice.company_id == company_id
    ).scalar()
    
    next_seq = max_seq + 1
    invoice_num = f"INV-{company_id:02d}-{next_seq:05d}"
    
    vat_amount = (subtotal * 0.13) if vat_enabled else 0.0
    total_amount = subtotal + vat_amount
    
    invoice = Invoice(
        company_id=company_id,
        sales_order_id=sales_order_id,
        invoice_number=invoice_num,
        sequence_number=next_seq,
        date_ad="2026-09-25",
        date_bs="2083-06-09",
        subtotal=subtotal,
        vat_enabled=vat_enabled,
        vat_rate=13.0 if vat_enabled else 0.0,
        vat_amount=vat_amount,
        total_amount=total_amount,
        received_amount=total_amount,
        receivable_amount=0.0
    )
    db_session.add(invoice)
    db_session.commit()
    return invoice

def test_sequential_invoice_numbering_per_company(db):
    inv1 = generate_next_invoice(db, company_id=1, sales_order_id=101, subtotal=5000.0)
    assert inv1.sequence_number == 1
    assert inv1.invoice_number == "INV-01-00001"
    
    inv2 = generate_next_invoice(db, company_id=1, sales_order_id=102, subtotal=12000.0)
    assert inv2.sequence_number == 2
    assert inv2.invoice_number == "INV-01-00002"

    # Company 2 sequence must start independently at 1
    inv_c2 = generate_next_invoice(db, company_id=2, sales_order_id=201, subtotal=3000.0)
    assert inv_c2.sequence_number == 1
    assert inv_c2.invoice_number == "INV-02-00001"

def test_void_invoice_preserves_sequence(db):
    inv1 = generate_next_invoice(db, company_id=1, sales_order_id=101, subtotal=5000.0)
    assert inv1.invoice_number == "INV-01-00001"
    
    # Void invoice 1
    inv1.is_void = True
    db.commit()
    
    # Next invoice must be 2, not re-using 1
    inv2 = generate_next_invoice(db, company_id=1, sales_order_id=102, subtotal=8000.0)
    assert inv2.sequence_number == 2
    assert inv2.invoice_number == "INV-01-00002"

def test_unique_invoice_sequence_constraint(db):
    from sqlalchemy.exc import IntegrityError
    # Insert invoice with company_id=1, sequence_number=1
    generate_next_invoice(db, company_id=1, sales_order_id=101, subtotal=1000.0)

    # Attempting to force insert another invoice with the exact same company_id and sequence_number
    duplicate_inv = Invoice(
        company_id=1,
        sales_order_id=102,
        invoice_number="INV-01-00001",
        sequence_number=1,  # Duplicate sequence number for company 1
        date_ad="2026-09-25",
        date_bs="2083-06-09",
        subtotal=1000.0,
        vat_enabled=False,
        vat_rate=0.0,
        vat_amount=0.0,
        total_amount=1000.0,
        received_amount=1000.0,
        receivable_amount=0.0
    )
    db.add(duplicate_inv)
    with pytest.raises(IntegrityError):
        db.commit()

def test_concurrent_invoice_generation_api():
    """
    Simulates sequence number collision to verify that the bounded retry loop in invoices.py
    recalculates max_seq, recovers from IntegrityError, and preserves sequence uniqueness.
    """
    from unittest.mock import patch
    from sqlalchemy.exc import IntegrityError
    from app.db.session import Base, engine, SessionLocal
    from app.models import Company, User, SalesOrder, Client
    from app.api.v1.invoices import generate_invoice, InvoiceCreate

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "LIVO").first()
    if not comp:
        comp = Company(name="LIVO GROUP", code="LIVO")
        db.add(comp)
        db.commit()

    ed = db.query(User).filter(User.username == "concurrent_editor").first()
    if not ed:
        ed = User(
            company_id=comp.id,
            name="Concurrent Editor",
            username="concurrent_editor",
            password_hash="hashed",
            role="editor",
            active=True
        )
        db.add(ed)
        db.commit()

    client_obj = db.query(Client).first()
    if not client_obj:
        client_obj = Client(company_id=comp.id, code="CLI-C01", name="Test Client")
        db.add(client_obj)
        db.commit()

    order = db.query(SalesOrder).first()
    if not order:
        order = SalesOrder(
            company_id=comp.id,
            order_number="SO-CONC-001",
            client_id=client_obj.id,
            order_date_ad="2026-09-26",
            order_date_bs="2083-06-10",
            total_amount=5000.0,
            received_amount=5000.0,
            receivable_amount=0.0
        )
        db.add(order)
        db.commit()

    # Create first invoice
    data = InvoiceCreate(sales_order_id=order.id, vat_enabled=False)
    inv1 = generate_invoice(data, current_user=ed, db=db)
    assert inv1.sequence_number >= 1

    # Test retry loop explicitly: mock db.commit to fail with IntegrityError on 1st attempt, then succeed
    original_commit = db.commit
    commit_attempts = [0]

    def mock_commit():
        commit_attempts[0] += 1
        if commit_attempts[0] == 1:
            raise IntegrityError("mock unique constraint violation", params=None, orig=Exception("unique constraint"))
        return original_commit()

    db.commit = mock_commit

    data2 = InvoiceCreate(sales_order_id=order.id, vat_enabled=False)
    inv2 = generate_invoice(data2, current_user=ed, db=db)
    assert commit_attempts[0] == 2  # Proves 1st attempt failed with IntegrityError and 2nd attempt retried & succeeded!
    assert inv2.sequence_number > inv1.sequence_number

    db.close()






