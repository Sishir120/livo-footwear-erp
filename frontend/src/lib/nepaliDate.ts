/**
 * Deterministic, dependency-free Bikram Sambat (BS) & Gregorian (AD) calendar engine.
 * Full bidirectional conversion, validation, and formatting for Nepali dates.
 * Anchor: 1979-01-01 BS is 1922-04-13 AD.
 * Covers years 1979 to 2100 BS.
 */

export const NEPALI_MONTHS_EN: readonly string[] = [
  "Baisakh", "Jestha", "Ashadh", "Shrawan", "Bhadra", "Ashwin",
  "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
];

export const NEPALI_MONTHS_NE: readonly string[] = [
  "बैशाख", "जेठ", "असार", "श्रावण", "भाद्र", "आश्विन",
  "कार्तिक", "मंसिर", "पौष", "माघ", "फाल्गुन", "चैत्र"
];

export const NEPALI_DAYS_SHORT: readonly string[] = [
  "आइत", "सोम", "मंगल", "बुध", "बिही", "शुक्र", "शनि"
];

export const NEPALI_DAYS_EN: readonly string[] = [
  "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"
];

export const START_BS_YEAR = 1979;
export const END_BS_YEAR = 2100;

export const BS_CALENDAR_DATA: readonly (readonly number[])[] = [
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 1979
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 1980
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 1981
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1982
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 1983
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 1984
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 1985
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1986
  [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 1987
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 1988
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 1989
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1990
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 1991
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 1992
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1993
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1994
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 1995
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 1996
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1997
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 1998
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 1999
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2000
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2001
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2002
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2003
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2004
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2005
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2006
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2007
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31], // 2008
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2009
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2010
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2011
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 2012
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2013
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2014
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2015
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 2016
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2017
  [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2018
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2019
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2020
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2021
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 2022
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2023
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2024
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2025
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2026
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2027
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2028
  [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30], // 2029
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2030
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2031
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2032
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2033
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2034
  [30, 32, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31], // 2035
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2036
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2037
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2038
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 2039
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2040
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2041
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2042
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 2043
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2044
  [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2045
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2046
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2047
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2048
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 2049
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2050
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2051
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2052
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 2053
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2054
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2055
  [31, 31, 32, 31, 32, 30, 30, 29, 30, 29, 30, 30], // 2056
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2057
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2058
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2059
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2060
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2061
  [31, 31, 31, 32, 31, 31, 29, 30, 29, 30, 29, 31], // 2062
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2063
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2064
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2065
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 29, 31], // 2066
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2067
  [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2068
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2069
  [31, 31, 31, 32, 31, 31, 29, 30, 30, 29, 30, 30], // 2070
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2071
  [31, 32, 31, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2072
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2073
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2074
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2075
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 2076
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2077
  [31, 31, 31, 32, 31, 31, 30, 29, 30, 29, 30, 30], // 2078
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2079
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 30], // 2080
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31], // 2081
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2082
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30], // 2083
  [31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30], // 2084
  [31, 32, 31, 32, 30, 31, 30, 30, 29, 30, 30, 30], // 2085
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30], // 2086
  [31, 31, 32, 31, 31, 31, 30, 30, 30, 30, 30, 30], // 2087
  [30, 31, 32, 32, 30, 31, 30, 30, 29, 30, 30, 30], // 2088
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30], // 2089
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30], // 2090
  [31, 31, 32, 31, 31, 31, 30, 30, 29, 30, 30, 30], // 2091
  [30, 31, 32, 32, 31, 30, 30, 30, 29, 30, 30, 30], // 2092
  [30, 32, 31, 32, 31, 30, 30, 30, 29, 30, 30, 30], // 2093
  [31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 30, 30], // 2094
  [31, 31, 32, 31, 31, 31, 30, 29, 30, 30, 30, 30], // 2095
  [30, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30], // 2096
  [31, 32, 31, 31, 31, 30, 30, 30, 29, 30, 30, 30], // 2097
  [31, 31, 32, 31, 31, 31, 29, 30, 29, 30, 29, 31], // 2098
  [31, 31, 32, 31, 31, 31, 30, 29, 29, 30, 30, 30], // 2099
  [31, 32, 31, 32, 31, 30, 30, 30, 29, 29, 30, 31], // 2100
];

const MS_PER_DAY = 86_400_000;
// Reference AD date: 1922-04-13 corresponds to 1979-01-01 BS
const REFERENCE_AD_UTC = Date.UTC(1922, 3, 13); // month is 0-indexed in JS (3 = April)
const TOTAL_CALENDAR_DAYS = BS_CALENDAR_DATA.reduce((acc, y) => acc + y.reduce((s, m) => s + m, 0), 0);

export function daysInBsMonth(year: number, month: number): number {
  if (year < START_BS_YEAR || year > END_BS_YEAR) {
    throw new Error(`Year ${year} out of supported BS range (${START_BS_YEAR}–${END_BS_YEAR})`);
  }
  if (month < 1 || month > 12) {
    throw new Error(`Month ${month} must be between 1 and 12`);
  }
  return BS_CALENDAR_DATA[year - START_BS_YEAR][month - 1];
}

export function isValidBsDate(year: number, month: number, day: number): boolean {
  if (year < START_BS_YEAR || year > END_BS_YEAR) return false;
  if (month < 1 || month > 12) return false;
  const maxDays = BS_CALENDAR_DATA[year - START_BS_YEAR][month - 1];
  return day >= 1 && day <= maxDays;
}

export function formatBs(year: number, month: number, day: number, separator = "-"): string {
  const y = String(year).padStart(4, "0");
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${y}${separator}${m}${separator}${d}`;
}

export function formatAd(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function bsToAd(year: number, month: number, day: number): Date {
  if (!isValidBsDate(year, month, day)) {
    throw new Error(`Invalid BS date: ${year}-${month}-${day}`);
  }

  const yearIdx = year - START_BS_YEAR;
  let daysOffset = 0;

  for (let y = 0; y < yearIdx; y++) {
    const yr = BS_CALENDAR_DATA[y];
    for (let m = 0; m < 12; m++) {
      daysOffset += yr[m];
    }
  }

  const currentYearMonths = BS_CALENDAR_DATA[yearIdx];
  for (let m = 0; m < month - 1; m++) {
    daysOffset += currentYearMonths[m];
  }

  daysOffset += (day - 1);

  return new Date(REFERENCE_AD_UTC + daysOffset * MS_PER_DAY);
}

export function adToBs(dateInput: Date | string): {
  year: number;
  month: number;
  day: number;
  formatted: string;
} {
  let targetUtc: number;
  if (typeof dateInput === "string") {
    const parts = dateInput.trim().split("-");
    if (parts.length === 3) {
      targetUtc = Date.UTC(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    } else {
      const parsed = new Date(dateInput);
      targetUtc = Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate());
    }
  } else {
    targetUtc = Date.UTC(dateInput.getUTCFullYear(), dateInput.getUTCMonth(), dateInput.getUTCDate());
  }

  let deltaDays = Math.round((targetUtc - REFERENCE_AD_UTC) / MS_PER_DAY);
  if (deltaDays < 0 || deltaDays >= TOTAL_CALENDAR_DAYS) {
    throw new Error(`AD date is out of supported Bikram Sambat range (1979–2100 BS)`);
  }

  let yearIdx = 0;
  while (yearIdx < BS_CALENDAR_DATA.length) {
    const yr = BS_CALENDAR_DATA[yearIdx];
    let yearDays = 0;
    for (let m = 0; m < 12; m++) yearDays += yr[m];
    if (deltaDays < yearDays) break;
    deltaDays -= yearDays;
    yearIdx++;
  }

  const year = START_BS_YEAR + yearIdx;
  const currentYearMonths = BS_CALENDAR_DATA[yearIdx];
  let month = 1;
  for (let m = 0; m < 12; m++) {
    const mDays = currentYearMonths[m];
    if (deltaDays < mDays) {
      month = m + 1;
      break;
    }
    deltaDays -= mDays;
  }

  const day = deltaDays + 1;
  return {
    year,
    month,
    day,
    formatted: formatBs(year, month, day)
  };
}

export function parseBsDate(dateStr: string): { year: number; month: number; day: number } | null {
  if (!dateStr) return null;
  const clean = dateStr.trim().replace(/\//g, "-");
  const parts = clean.split("-");
  if (parts.length !== 3) return null;

  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const d = parseInt(parts[2], 10);

  if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
  if (!isValidBsDate(y, m, d)) return null;

  return { year: y, month: m, day: d };
}

export function getTodayBs(): {
  year: number;
  month: number;
  day: number;
  formatted: string;
} {
  // Convert current time with Nepal timezone offset (+05:45)
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
  const nptMs = utcMs + (5 * 60 + 45) * 60_000;
  const nptDate = new Date(nptMs);

  return adToBs(nptDate);
}

export function getTodayAd(): string {
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60_000;
  const nptMs = utcMs + (5 * 60 + 45) * 60_000;
  const nptDate = new Date(nptMs);
  return formatAd(nptDate);
}
