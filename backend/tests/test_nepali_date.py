import datetime
import random
import pytest
from app.core.nepali_date import (
    bs_to_ad,
    ad_to_bs,
    format_bs_date,
    parse_bs_date,
    today_bs,
    days_in_bs_month,
    is_valid_bs_date,
    NEPALI_MONTHS_EN,
    NEPALI_MONTHS_NE,
    START_BS_YEAR,
    END_BS_YEAR,
)


def test_nepali_date_known_reference_points():
    """Verify known reference points across Bikram Sambat calendar."""
    # 2070-01-01 BS -> 2013-04-14 AD (Sunday)
    ad_2070 = bs_to_ad(2070, 1, 1)
    assert ad_2070 == datetime.date(2013, 4, 14)
    assert ad_to_bs(ad_2070) == (2070, 1, 1)

    # 2083-06-09 BS -> 2026-09-25 AD
    ad_2083_6_9 = bs_to_ad(2083, 6, 9)
    assert ad_2083_6_9 == datetime.date(2026, 9, 25)
    assert ad_to_bs(ad_2083_6_9) == (2083, 6, 9)

    # 2083-01-01 BS -> 2026-04-14 AD
    ad_2083_1_1 = bs_to_ad(2083, 1, 1)
    assert ad_2083_1_1 == datetime.date(2026, 4, 14)
    assert ad_to_bs(ad_2083_1_1) == (2083, 1, 1)

    # 1979-01-01 BS (Anchor date) -> 1922-04-13 AD
    ad_anchor = bs_to_ad(1979, 1, 1)
    assert ad_anchor == datetime.date(1922, 4, 13)
    assert ad_to_bs(ad_anchor) == (1979, 1, 1)


def test_round_trip_random_dates():
    """Verify 200+ random dates have 100% round-trip fidelity between BS and AD."""
    rng = random.Random(42)  # Deterministic seed

    for _ in range(250):
        year = rng.randint(2070, 2090)
        month = rng.randint(1, 12)
        max_days = days_in_bs_month(year, month)
        day = rng.randint(1, max_days)

        ad_date = bs_to_ad(year, month, day)
        bs_back = ad_to_bs(ad_date)
        assert bs_back == (year, month, day), f"Round trip failed for {year}-{month}-{day}"

        # Reverse round trip: ad -> bs -> ad
        ad_back = bs_to_ad(*bs_back)
        assert ad_back == ad_date, f"Reverse round trip failed for AD {ad_date}"


def test_leap_years_and_month_boundaries():
    """Verify end of month and year boundary transitions."""
    # Test every month's last day in year 2083 BS
    for m in range(1, 13):
        max_day = days_in_bs_month(2083, m)
        ad_end = bs_to_ad(2083, m, max_day)
        assert ad_to_bs(ad_end) == (2083, m, max_day)

        # The next day should cross into next month or next year
        next_ad = ad_end + datetime.timedelta(days=1)
        next_bs = ad_to_bs(next_ad)
        if m < 12:
            assert next_bs == (2083, m + 1, 1)
        else:
            assert next_bs == (2084, 1, 1)


def test_invalid_dates_rejected():
    """Test validation raises ValueError for out-of-range or impossible dates."""
    # Month > 12
    with pytest.raises(ValueError):
        bs_to_ad(2083, 13, 1)

    # Month < 1
    with pytest.raises(ValueError):
        bs_to_ad(2083, 0, 1)

    # Day 0
    with pytest.raises(ValueError):
        bs_to_ad(2083, 1, 0)

    # Day exceeding month length
    max_days = days_in_bs_month(2083, 1)  # Usually 31
    with pytest.raises(ValueError):
        bs_to_ad(2083, 1, max_days + 1)

    # Year below range
    with pytest.raises(ValueError):
        bs_to_ad(1970, 1, 1)

    # Year above range
    with pytest.raises(ValueError):
        bs_to_ad(2101, 1, 1)

    # AD date before anchor
    with pytest.raises(ValueError):
        ad_to_bs(datetime.date(1900, 1, 1))


def test_format_and_parse():
    """Test parsing and formatting helpers."""
    assert format_bs_date(2083, 6, 9) == "2083-06-09"
    assert format_bs_date(2083, 1, 5) == "2083-01-05"

    assert parse_bs_date("2083-06-09") == (2083, 6, 9)
    assert parse_bs_date("2083/06/09") == (2083, 6, 9)
    assert parse_bs_date("  2070-01-01  ") == (2070, 1, 1)

    # Invalid parsing
    with pytest.raises(ValueError):
        parse_bs_date("invalid-date")
    with pytest.raises(ValueError):
        parse_bs_date("2083-13-01")
    with pytest.raises(ValueError):
        parse_bs_date("2083-06-45")


def test_today_bs():
    """Test today_bs returns valid components."""
    y, m, d = today_bs()
    assert is_valid_bs_date(y, m, d)
    assert START_BS_YEAR <= y <= END_BS_YEAR
    assert 1 <= m <= 12
    assert 1 <= d <= 32


def test_month_names():
    """Verify month lists have 12 items."""
    assert len(NEPALI_MONTHS_EN) == 12
    assert len(NEPALI_MONTHS_NE) == 12
    assert NEPALI_MONTHS_EN[0] == "Baisakh"
    assert NEPALI_MONTHS_NE[0] == "बैशाख"
    assert NEPALI_MONTHS_EN[11] == "Chaitra"
    assert NEPALI_MONTHS_NE[11] == "चैत्र"
