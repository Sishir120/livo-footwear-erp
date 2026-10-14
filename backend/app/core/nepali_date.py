"""
Deterministic, dependency-free Bikram Sambat (BS) & Gregorian (AD) calendar engine.
Provides exact bidirectional date conversion, validation, and formatting for Nepali dates.
Canonical reference: BS 1979-01-01 is AD 1922-04-13.
Supports years 1979 to 2100 BS (including client-required 2070–2090 BS).
"""

import datetime
from typing import Tuple, List

# Month names
NEPALI_MONTHS_EN: List[str] = [
    "Baisakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin",
    "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
]

NEPALI_MONTHS_NE: List[str] = [
    "बैशाख", "जेठ", "असार", "श्रावण", "भाद्र", "आश्विन",
    "कार्तिक", "मंसिर", "पौष", "माघ", "फाल्गुन", "चैत्र"
]

START_BS_YEAR = 1979
END_BS_YEAR = 2100
REFERENCE_AD_DATE = datetime.date(1922, 4, 13)  # Corresponds to 1979-01-01 BS

# Table of days per month from 1979 to 2100 BS (122 years)
BS_CALENDAR_DATA: List[List[int]] = [
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 1979
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 1980
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 1981
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1982
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 1983
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 1984
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 1985
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1986
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 1987
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 1988
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 1989
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1990
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 1991
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 1992
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1993
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1994
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 1995
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 1996
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1997
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 1998
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 1999
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2000
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2001
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2002
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2003
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2004
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2005
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2006
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2007
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31],  # 2008
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2009
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2010
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2011
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 2012
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2013
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2014
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2015
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 2016
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2017
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2018
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2019
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2020
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2021
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 2022
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2023
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2024
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2025
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2026
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2027
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2028
    [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],  # 2029
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2030
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2031
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2032
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2033
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2034
    [30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31],  # 2035
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2036
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2037
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2038
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 2039
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2040
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2041
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2042
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 2043
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2044
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2045
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2046
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2047
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2048
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 2049
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2050
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2051
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2052
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 2053
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2054
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2055
    [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30],  # 2056
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2057
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2058
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2059
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2060
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2061
    [31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31],  # 2062
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2063
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2064
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2065
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31],  # 2066
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2067
    [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2068
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2069
    [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30],  # 2070
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2071
    [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2072
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2073
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2074
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2075
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 2076
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2077
    [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30],  # 2078
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2079
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30],  # 2080
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31],  # 2081
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2082
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30],  # 2083
    [31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30],  # 2084
    [31, 32, 31, 32, 30, 31, 30, 30, 29, 30, 30, 30],  # 2085
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30],  # 2086
    [31, 31, 32, 31, 31, 31, 30, 30, 30, 30, 30, 30],  # 2087
    [30, 31, 32, 32, 30, 31, 30, 30, 29, 30, 30, 30],  # 2088
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30],  # 2089
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30],  # 2090
    [31, 31, 32, 31, 31, 31, 30, 30, 29, 30, 30, 30],  # 2091
    [30, 31, 32, 32, 31, 30, 30, 30, 29, 30, 30, 30],  # 2092
    [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30],  # 2093
    [31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30],  # 2094
    [31, 31, 32, 31, 31, 31, 30, 29, 30, 30, 30, 30],  # 2095
    [30, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30],  # 2096
    [31, 32, 31, 31, 31, 30, 30, 30, 29, 30, 30, 30],  # 2097
    [31, 31, 32, 31, 31, 31, 29, 30, 29, 30, 29, 31],  # 2098
    [31, 31, 32, 31, 31, 31, 30, 29, 29, 30, 30, 30],  # 2099
    [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31],  # 2100
]

TOTAL_DAYS_IN_CALENDAR = sum(sum(year) for year in BS_CALENDAR_DATA)


def days_in_bs_month(year: int, month: int) -> int:
    """Returns number of days in a specific BS year and month."""
    if not (START_BS_YEAR <= year <= END_BS_YEAR):
        raise ValueError(f"Year {year} out of supported BS range ({START_BS_YEAR}–{END_BS_YEAR})")
    if not (1 <= month <= 12):
        raise ValueError(f"Month {month} must be between 1 and 12")
    return BS_CALENDAR_DATA[year - START_BS_YEAR][month - 1]


def is_valid_bs_date(year: int, month: int, day: int) -> bool:
    """Returns True if the BS date is valid and within supported range."""
    if not (START_BS_YEAR <= year <= END_BS_YEAR):
        return False
    if not (1 <= month <= 12):
        return False
    max_days = BS_CALENDAR_DATA[year - START_BS_YEAR][month - 1]
    return 1 <= day <= max_days


def bs_to_ad(year: int, month: int, day: int) -> datetime.date:
    """
    Converts Bikram Sambat (BS) date to Gregorian (AD) date.
    Raises ValueError on invalid BS date.
    """
    if not is_valid_bs_date(year, month, day):
        if not (START_BS_YEAR <= year <= END_BS_YEAR):
            raise ValueError(f"Year {year} out of supported BS range ({START_BS_YEAR}–{END_BS_YEAR})")
        if not (1 <= month <= 12):
            raise ValueError(f"Month {month} must be between 1 and 12")
        max_days = BS_CALENDAR_DATA[year - START_BS_YEAR][month - 1]
        raise ValueError(f"Day {day} exceeds month {month} length of {max_days} days for BS year {year}")

    year_idx = year - START_BS_YEAR
    days_offset = 0

    # Accumulate days of previous years
    for y in range(year_idx):
        days_offset += sum(BS_CALENDAR_DATA[y])

    # Accumulate days of previous months in the same year
    for m in range(month - 1):
        days_offset += BS_CALENDAR_DATA[year_idx][m]

    # Add day of month (0-indexed offset)
    days_offset += (day - 1)

    return REFERENCE_AD_DATE + datetime.timedelta(days=days_offset)


def ad_to_bs(ad_date: datetime.date) -> Tuple[int, int, int]:
    """
    Converts Gregorian (AD) date to Bikram Sambat (BS) date (year, month, day).
    Raises ValueError if ad_date is outside the supported range.
    """
    delta_days = (ad_date - REFERENCE_AD_DATE).days
    if delta_days < 0 or delta_days >= TOTAL_DAYS_IN_CALENDAR:
        raise ValueError(f"AD date {ad_date} is out of supported BS range")

    year_idx = 0
    while year_idx < len(BS_CALENDAR_DATA):
        year_days = sum(BS_CALENDAR_DATA[year_idx])
        if delta_days < year_days:
            break
        delta_days -= year_days
        year_idx += 1

    year = START_BS_YEAR + year_idx
    month = 1
    for m_idx in range(12):
        m_days = BS_CALENDAR_DATA[year_idx][m_idx]
        if delta_days < m_days:
            month = m_idx + 1
            break
        delta_days -= m_days

    day = delta_days + 1
    return (year, month, day)


def format_bs_date(year: int, month: int, day: int, separator: str = "-") -> str:
    """Formats BS date as YYYY{sep}MM{sep}DD."""
    return f"{year:04d}{separator}{month:02d}{separator}{day:02d}"


def parse_bs_date(date_str: str) -> Tuple[int, int, int]:
    """
    Parses a string like '2083-06-09' or '2083/06/09' into (year, month, day).
    Raises ValueError on invalid format or date.
    """
    clean_str = date_str.strip().replace("/", "-")
    parts = clean_str.split("-")
    if len(parts) != 3:
        raise ValueError(f"Invalid BS date format: '{date_str}'. Expected 'YYYY-MM-DD'")

    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError(f"BS date components must be integers: '{date_str}'")

    if not is_valid_bs_date(y, m, d):
        raise ValueError(f"Invalid BS date values: '{date_str}'")

    return (y, m, d)


def today_bs() -> Tuple[int, int, int]:
    """
    Returns today's BS date using Nepal Standard Time (UTC+05:45).
    """
    npt_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=45))
    npt_now = datetime.datetime.now(npt_tz).date()
    return ad_to_bs(npt_now)


def validate_bs_date(date_str: str) -> bool:
    """
    Validates whether incoming date string is a valid Bikram Sambat date.
    Returns True if valid, False if malformed, out-of-range, or invalid day/month.
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return False
    try:
        parse_bs_date(date_str)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def ad_to_bs_str(ad_date: datetime.date) -> str:
    """
    Converts Gregorian (AD) date object to formatted Bikram Sambat (BS) date string (YYYY-MM-DD).
    """
    if not isinstance(ad_date, datetime.date):
        raise TypeError(f"Expected datetime.date object, got {type(ad_date)}")
    y, m, d = ad_to_bs(ad_date)
    return format_bs_date(y, m, d)


def bs_to_ad_date(bs_str: str) -> datetime.date:
    """
    Converts Bikram Sambat (BS) date string (YYYY-MM-DD) to Gregorian (AD) date object.
    Raises ValueError on invalid format or non-existent calendar date.
    """
    y, m, d = parse_bs_date(bs_str)
    return bs_to_ad(y, m, d)


def validate_nepali_date_field(date_bs: str) -> str:
    """
    FastAPI validation dependency / helper for verifying incoming date_bs string.
    Rejects invalid calendar days or months with HTTP 422.
    """
    from fastapi import HTTPException, status
    if not validate_bs_date(date_bs):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid Nepali date (BS): '{date_bs}'. Expected valid YYYY-MM-DD within supported calendar."
        )
    return date_bs


def parse_ad_date(date_val) -> datetime.date:
    """Safely coerces strings, datetimes or dates into a datetime.date instance."""
    if isinstance(date_val, datetime.date) and not isinstance(date_val, datetime.datetime):
        return date_val
    if isinstance(date_val, datetime.datetime):
        return date_val.date()
    if isinstance(date_val, str):
        val = date_val.strip()
        try:
            return datetime.datetime.strptime(val[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    return datetime.date.today()


