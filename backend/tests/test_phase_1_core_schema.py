import pytest
import datetime
import uuid
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.company import Company
from app.models.purchase import Supplier, RawMaterial, Purchase
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.worker import Worker
from app.db.session import Base, engine, SessionLocal
from app.core.nepali_date import (
    validate_bs_date,
    ad_to_bs_str,
    bs_to_ad_date,
    validate_nepali_date_field,
    is_valid_bs_date,
)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def _make_company(db_session, prefix: str) -> Company:
    uid = uuid.uuid4().hex[:6].upper()
    comp = Company(name=f"Co {prefix} {uid}", code=f"{prefix}_{uid}")
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)
    return comp


def test_raw_material_unit_constraint_and_defaults(db_session):
    """Test RawMaterial model supports allowed units ('kg', 'pcs', 'litre') and defaults."""
    company = _make_company(db_session, "RM_TEST")

    # Valid unit 'kg'
    rm1 = RawMaterial(
        company_id=company.id,
        code=f"RM-KG-{uuid.uuid4().hex[:4]}",
        name="Leather Sole Rubber",
        unit="kg"
    )
    db_session.add(rm1)
    db_session.commit()

    assert rm1.unit == "kg"
    assert rm1.reorder_level == 0.0
    assert rm1.current_stock == 0.0

    # Valid unit 'pcs'
    rm2 = RawMaterial(
        company_id=company.id,
        code=f"RM-PCS-{uuid.uuid4().hex[:4]}",
        name="Metal Buckles",
        unit="pcs",
        reorder_level=50.0,
        current_stock=200.0
    )
    db_session.add(rm2)
    db_session.commit()
    assert rm2.unit == "pcs"
    assert rm2.reorder_level == 50.0
    assert rm2.current_stock == 200.0

    # Valid unit 'litre'
    rm3 = RawMaterial(
        company_id=company.id,
        code=f"RM-LTR-{uuid.uuid4().hex[:4]}",
        name="Sole Adhesive Glue",
        unit="litre"
    )
    db_session.add(rm3)
    db_session.commit()
    assert rm3.unit == "litre"

    # Invalid unit should fail check constraint
    rm_invalid = RawMaterial(
        company_id=company.id,
        code=f"RM-INV-{uuid.uuid4().hex[:4]}",
        name="Invalid Unit Material",
        unit="meters"
    )
    db_session.add(rm_invalid)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_purchase_order_date_segregation_and_status(db_session):
    """Test Purchase model supports ordered/receipt date segregation and status."""
    company = _make_company(db_session, "PO_TEST")

    supplier = Supplier(company_id=company.id, code=f"SUP-{uuid.uuid4().hex[:4]}", name="Alpha Leather Tannery")
    rm = RawMaterial(company_id=company.id, code=f"RM-{uuid.uuid4().hex[:4]}", name="Raw Cowhide", unit="kg")
    db_session.add_all([supplier, rm])
    db_session.commit()

    # Purchase with segregated dates and status
    order_d = datetime.date(2026, 10, 1)
    receipt_d = datetime.date(2026, 10, 10)

    po = Purchase(
        company_id=company.id,
        supplier_id=supplier.id,
        raw_material_id=rm.id,
        quantity=Decimal("500.00"),
        unit_price=Decimal("1200.00"),
        total_amount=Decimal("600000.00"),
        purchase_date_ad="2026-10-10",
        purchase_date_bs="2083-06-24",
        order_date_ad=order_d,
        order_date_bs="2083-06-15",
        receipt_date_ad=receipt_d,
        receipt_date_bs="2083-06-24",
        status="RECEIVED"
    )
    db_session.add(po)
    db_session.commit()

    assert po.order_date_ad == order_d
    assert po.order_date_bs == "2083-06-15"
    assert po.receipt_date_ad == receipt_d
    assert po.receipt_date_bs == "2083-06-24"
    assert po.status == "RECEIVED"


def test_sales_order_dispatch_dates_and_status(db_session):
    """Test SalesOrder supports dispatch_date_ad, dispatch_date_bs and status."""
    company = _make_company(db_session, "SO_TEST")

    client = Client(company_id=company.id, code=f"CL-{uuid.uuid4().hex[:4]}", name="Kathmandu Retail Hub")
    db_session.add(client)
    db_session.commit()

    disp_d = datetime.date(2026, 10, 12)
    order = SalesOrder(
        company_id=company.id,
        order_number=f"SO-{uuid.uuid4().hex[:6]}",
        client_id=client.id,
        order_date_ad="2026-10-10",
        order_date_bs="2083-06-24",
        dispatch_date_ad=disp_d,
        dispatch_date_bs="2083-06-26",
        status="DISPATCHED",
        total_amount=Decimal("15000.00"),
        delivered=True
    )
    db_session.add(order)
    db_session.commit()

    assert order.dispatch_date_ad == disp_d
    assert order.dispatch_date_bs == "2083-06-26"
    assert order.status == "DISPATCHED"


def test_worker_profile_extensions(db_session):
    """Test Worker model extensions: photo_url, temp/perm addresses, inactive date/reason."""
    company = _make_company(db_session, "WKR_TEST")

    inact_d = datetime.date(2026, 10, 11)
    worker = Worker(
        company_id=company.id,
        worker_code=f"WKR-{uuid.uuid4().hex[:4]}",
        name="Suman Shrestha",
        pay_type="SALARY",
        basic_rate_paisa=3500000,
        phone="9841234567",
        photo_url="/static/uploads/workers/wkr_999.jpg",
        temporary_address="Koteshwor-32, Kathmandu",
        permanent_address="Banepa-05, Kavre",
        inactive_date=inact_d,
        inactive_reason="Resigned for higher studies",
        is_active=False
    )
    db_session.add(worker)
    db_session.commit()

    assert worker.photo_url == "/static/uploads/workers/wkr_999.jpg"
    assert worker.temporary_address == "Koteshwor-32, Kathmandu"
    assert worker.permanent_address == "Banepa-05, Kavre"
    assert worker.inactive_date == inact_d
    assert worker.inactive_reason == "Resigned for higher studies"
    assert worker.is_active is False


def test_nepali_date_validation_and_conversions():
    """Test Bikram Sambat date engine hardening in 2070–2090 BS range."""
    # 1. Validation across valid dates in 2070-2090 BS
    assert validate_bs_date("2070-01-01") is True
    assert validate_bs_date("2080-05-15") is True
    assert validate_bs_date("2083-06-09") is True
    assert validate_bs_date("2090-12-30") is True

    # 2. Validation failures for invalid months and days
    assert validate_bs_date("2083-13-01") is False  # Month > 12
    assert validate_bs_date("2083-00-01") is False  # Month 0
    assert validate_bs_date("2083-02-35") is False  # Day > 32
    assert validate_bs_date("invalid-date") is False
    assert validate_bs_date("") is False
    assert validate_bs_date(None) is False

    # 3. Round-trip conversion: AD -> BS string -> AD date
    ad_input = datetime.date(2026, 9, 25)
    bs_str = ad_to_bs_str(ad_input)
    assert isinstance(bs_str, str)
    assert len(bs_str) == 10  # YYYY-MM-DD
    ad_reconstructed = bs_to_ad_date(bs_str)
    assert ad_reconstructed == ad_input

    # 4. Dependency validator
    assert validate_nepali_date_field("2083-06-09") == "2083-06-09"
    with pytest.raises(HTTPException) as exc_info:
        validate_nepali_date_field("2083-99-99")
    assert exc_info.value.status_code == 422
