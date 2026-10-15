import datetime
import pytest
from decimal import Decimal
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.nepali_date import (
    bs_to_ad,
    ad_to_bs,
    format_bs_date,
    parse_bs_date,
    today_bs,
    days_in_bs_month,
    is_valid_bs_date,
    validate_bs_date,
    ad_to_bs_str,
    bs_to_ad_date,
    validate_nepali_date_field,
    parse_ad_date,
    START_BS_YEAR,
    END_BS_YEAR,
)
from app.main import app
from app.db.session import Base, engine, SessionLocal
from app.models import Company, User, Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# 1. Calendar Engine Boundaries and Round-Trip Fidelity
# ---------------------------------------------------------------------------

def test_anchor_boundary_dates():
    """Verify exact anchor date and outer boundary limits of the BS calendar."""
    # Anchor 1979-01-01 BS == 1922-04-13 AD
    ad_anchor = bs_to_ad(1979, 1, 1)
    assert ad_anchor == datetime.date(1922, 4, 13)
    assert ad_to_bs(ad_anchor) == (1979, 1, 1)

    # Maximum supported BS date (2100-12-last_day)
    max_days_2100_chaitra = days_in_bs_month(2100, 12)
    assert max_days_2100_chaitra in {30, 31}
    ad_max = bs_to_ad(2100, 12, max_days_2100_chaitra)
    assert ad_to_bs(ad_max) == (2100, 12, max_days_2100_chaitra)

    # Historical Nepali Milestones
    # Nepal Constitution Day: 2072-06-03 BS == 2015-09-20 AD
    ad_const = bs_to_ad(2072, 6, 3)
    assert ad_const == datetime.date(2015, 9, 20)
    assert ad_to_bs(ad_const) == (2072, 6, 3)

    # Nepali New Year 2083: 2083-01-01 BS == 2026-04-14 AD
    ad_ny_2083 = bs_to_ad(2083, 1, 1)
    assert ad_ny_2083 == datetime.date(2026, 4, 14)
    assert ad_to_bs(ad_ny_2083) == (2083, 1, 1)


def test_client_operational_window_fidelity():
    """Verify 100% round-trip fidelity for every month across 2070 BS to 2090 BS."""
    for year in range(2070, 2091):
        for month in range(1, 13):
            max_d = days_in_bs_month(year, month)
            # Test first day, mid day, and last day of every month
            for d in [1, 15, max_d]:
                ad = bs_to_ad(year, month, d)
                bs_result = ad_to_bs(ad)
                assert bs_result == (year, month, d), f"Fidelity error at {year}-{month}-{d}"

                # String formatter check
                bs_str = format_bs_date(year, month, d)
                assert bs_to_ad_date(bs_str) == ad
                assert ad_to_bs_str(ad) == bs_str


# ---------------------------------------------------------------------------
# 2. Date-Only Semantics and Timezone Safety
# ---------------------------------------------------------------------------

def test_date_only_semantics_no_timezone_drift():
    """
    Verify conversion relies strictly on date-only arithmetic,
    preventing drift across UTC vs NPT (UTC+5:45) vs US PST (UTC-8).
    """
    test_ad = datetime.date(2026, 9, 25)
    expected_bs = (2083, 6, 9)
    assert ad_to_bs(test_ad) == expected_bs

    # Simulated datetime at 23:59:59 UTC
    utc_dt = datetime.datetime(2026, 9, 25, 23, 59, 59, tzinfo=datetime.timezone.utc)
    # Using parse_ad_date ensures date extraction preserves the intended calendar day
    assert ad_to_bs(parse_ad_date(utc_dt)) == expected_bs

    # Nepal Standard Time (UTC+05:45)
    npt_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=45))
    npt_dt = datetime.datetime(2026, 9, 25, 6, 0, 0, tzinfo=npt_tz)
    assert ad_to_bs(parse_ad_date(npt_dt)) == expected_bs


# ---------------------------------------------------------------------------
# 3. Invalid Date Rejection & Validation Helpers
# ---------------------------------------------------------------------------

def test_invalid_bs_dates_comprehensive():
    """Verify illegal calendar dates are rejected gracefully."""
    # Non-existent leap day: verify month max day exceeded
    for y in [2079, 2080, 2081, 2082, 2083]:
        for m in range(1, 13):
            max_d = days_in_bs_month(y, m)
            assert is_valid_bs_date(y, m, max_d) is True
            assert is_valid_bs_date(y, m, max_d + 1) is False
            with pytest.raises(ValueError):
                bs_to_ad(y, m, max_d + 1)

    # Malformed strings
    assert validate_bs_date("") is False
    assert validate_bs_date("   ") is False
    assert validate_bs_date("2083/13/01") is False
    assert validate_bs_date("2083-00-10") is False
    assert validate_bs_date("not-a-date") is False
    assert validate_bs_date("2083-06") is False
    assert validate_bs_date("1970-01-01") is False  # Before calendar start
    assert validate_bs_date("2105-01-01") is False  # After calendar end

    # Valid string
    assert validate_bs_date("2083-06-09") is True
    assert validate_bs_date("2083/06/09") is True

    # FastAPI validation dependency helper
    assert validate_nepali_date_field("2083-06-09") == "2083-06-09"
    with pytest.raises(HTTPException) as exc_info:
        validate_nepali_date_field("2083-13-40")
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# 4. Stock Movement & Adjustment Automatic BS Derivation (Defect Fix Proof)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_test_env():
    from app.middleware.rate_limit import BasicRateLimitMiddleware
    BasicRateLimitMiddleware.reset_all()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    comp = db.query(Company).filter(Company.code == "LIVO_TEST").first()
    if not comp:
        comp = Company(name="LIVO Test Factory", code="LIVO_TEST")
        db.add(comp)
        db.commit()
        db.refresh(comp)

    wh = db.query(Warehouse).filter(Warehouse.company_id == comp.id, Warehouse.code == "WH-TEST").first()
    if not wh:
        wh = Warehouse(company_id=comp.id, name="Test Warehouse", code="WH-TEST", is_active=True)
        db.add(wh)
        db.commit()
        db.refresh(wh)

    admin = db.query(User).filter(User.username == "date_admin").first()
    if not admin:
        admin = User(
            company_id=comp.id,
            name="Date Admin",
            username="date_admin",
            password_hash=get_password_hash("AdminPass123!"),
            role="admin",
            active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    prod = db.query(Product).filter(Product.company_id == comp.id, Product.code == "SHOE-BS").first()
    if not prod:
        prod = Product(
            company_id=comp.id,
            name="Nepal Heritage Boot",
            code="SHOE-BS",
            category="BOOTS",
            unit_price=Decimal("2500.00"),
            size="40",
            color="Black"
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)

    db.close()

    client = TestClient(app)
    # Login as admin
    login_resp = client.post("/api/v1/auth/login", json={"username": "date_admin", "password": "AdminPass123!"})
    assert login_resp.status_code == 200
    client.cookies.update(login_resp.cookies)

    return {"client": client, "company_id": comp.id, "warehouse_id": wh.id, "product_id": prod.id}


def test_stock_movement_derives_bs_date(api_test_env):
    """
    Verify that manual stock movement creates a record with a valid, non-empty date_bs
    matching the canonical conversion of today's AD date (previously hardcoded to "").
    """
    client = api_test_env["client"]
    wh_id = api_test_env["warehouse_id"]
    p_id = api_test_env["product_id"]

    expected_bs = ad_to_bs_str(datetime.date.today())

    payload = {
        "product_id": p_id,
        "warehouse_id": wh_id,
        "movement_type": "ADJUSTMENT_IN",
        "direction": 1,
        "size": "40",
        "quantity": 10,
        "notes": "Testing date_bs derivation"
    }

    res = client.post("/api/v1/stock/movements", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "id" in data
    assert data["date_bs"] == expected_bs

    # Query the movement from DB to verify date_bs is populated accurately
    db = SessionLocal()
    mov = db.query(StockMovement).filter(
        StockMovement.product_id == p_id,
        StockMovement.notes == "Testing date_bs derivation"
    ).order_by(StockMovement.id.desc()).first()
    db.close()

    assert mov is not None
    assert mov.date_bs == expected_bs
    assert mov.date_bs != ""
    assert validate_bs_date(mov.date_bs) is True


def test_stock_adjustment_derives_bs_date(api_test_env):
    """
    Verify that physical stock adjustment creates a record with a valid date_bs
    (previously hardcoded to "").
    """
    client = api_test_env["client"]
    wh_id = api_test_env["warehouse_id"]
    p_id = api_test_env["product_id"]

    expected_bs = ad_to_bs_str(datetime.date.today())

    payload = {
        "warehouse_id": wh_id,
        "product_id": p_id,
        "size": "40",
        "quantity_delta": 5,
        "reason_code": "FOUND",
        "reason_text": "Audit recount found extra pairs"
    }

    res = client.post("/api/v1/stock/adjustments", json=payload)
    assert res.status_code == 200, res.text

    db = SessionLocal()
    adj = db.query(StockMovement).filter(
        StockMovement.product_id == p_id,
        StockMovement.reason_code == "FOUND"
    ).order_by(StockMovement.id.desc()).first()
    db.close()

    assert adj is not None
    assert adj.date_bs == expected_bs
    assert adj.date_bs != ""
    assert validate_bs_date(adj.date_bs) is True


def test_analytics_safe_bs_derivation():
    """
    Verify analytics safe converter uses the verified calendar engine
    instead of the deprecated approximate +56/+8 algorithm.
    """
    from app.api.v1.analytics import _safe_ad_to_bs

    # Known date: 2026-09-25 AD -> 2083-06-09 BS
    assert _safe_ad_to_bs("2026-09-25") == "2083-06-09"

    # Constitution Day: 2015-09-20 AD -> 2072-06-03 BS
    assert _safe_ad_to_bs("2015-09-20") == "2072-06-03"

    # Graceful fallback on malformed date string (coerces to today's valid BS date)
    assert _safe_ad_to_bs("invalid-ad-date") == ad_to_bs_str(datetime.date.today())
