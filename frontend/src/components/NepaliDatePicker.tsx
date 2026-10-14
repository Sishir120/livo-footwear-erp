"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Calendar as CalendarIcon,
  Clock,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import {
  adToBs,
  bsToAd,
  formatAd,
  formatBs,
  parseBsDate,
  getTodayAd,
  getTodayBs,
  isValidBsDate,
  daysInBsMonth,
  NEPALI_MONTHS_EN,
  NEPALI_MONTHS_NE,
  NEPALI_DAYS_SHORT,
  NEPALI_DAYS_EN,
  START_BS_YEAR,
  END_BS_YEAR,
} from "../lib/nepaliDate";

export interface NepaliDatePickerProps {
  valueAd?: string; // Format: YYYY-MM-DD
  valueBs?: string; // Format: YYYY-MM-DD
  onChange: (dates: { ad: string; bs: string }) => void;
  disabled?: boolean;
  required?: boolean;
  label?: string;
  className?: string;
  compact?: boolean;
}

export function NepaliDatePicker({
  valueAd,
  valueBs,
  onChange,
  disabled = false,
  required = false,
  label,
  className = "",
  compact = false,
}: NepaliDatePickerProps) {
  // Internal state for controlled inputs
  const [currentAd, setCurrentAd] = useState<string>(() => {
    if (valueAd) return valueAd;
    if (valueBs) {
      const parsed = parseBsDate(valueBs);
      if (parsed) {
        try {
          return formatAd(bsToAd(parsed.year, parsed.month, parsed.day));
        } catch {
          // fallback
        }
      }
    }
    return getTodayAd();
  });

  const [currentBs, setCurrentBs] = useState<string>(() => {
    if (valueBs) return valueBs;
    if (valueAd) {
      try {
        return adToBs(valueAd).formatted;
      } catch {
        // fallback
      }
    }
    return getTodayBs().formatted;
  });

  const [bsInputError, setBsInputError] = useState<string | null>(null);
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  // Calendar view navigation state (year & month currently being viewed in calendar popup)
  const initialParsed = parseBsDate(currentBs) || getTodayBs();
  const [viewYear, setViewYear] = useState<number>(initialParsed.year);
  const [viewMonth, setViewMonth] = useState<number>(initialParsed.month);

  const containerRef = useRef<HTMLDivElement>(null);
  const calendarRef = useRef<HTMLDivElement>(null);

  // Synchronize when external props change
  useEffect(() => {
    if (valueAd && valueAd !== currentAd) {
      setCurrentAd(valueAd);
      try {
        const bsRes = adToBs(valueAd);
        setCurrentBs(bsRes.formatted);
        setBsInputError(null);
        setViewYear(bsRes.year);
        setViewMonth(bsRes.month);
      } catch {
        // Invalid AD date
      }
    }
  }, [valueAd]);

  useEffect(() => {
    if (valueBs && valueBs !== currentBs) {
      setCurrentBs(valueBs);
      const parsed = parseBsDate(valueBs);
      if (parsed) {
        try {
          const adObj = bsToAd(parsed.year, parsed.month, parsed.day);
          const adStr = formatAd(adObj);
          setCurrentAd(adStr);
          setBsInputError(null);
          setViewYear(parsed.year);
          setViewMonth(parsed.month);
        } catch {
          // Invalid BS date
        }
      }
    }
  }, [valueBs]);

  // Close calendar popup on outside click or Escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsCalendarOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsCalendarOpen(false);
      }
    }

    if (isCalendarOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isCalendarOpen]);

  // Handle AD input change
  const handleAdChange = (newAd: string) => {
    setCurrentAd(newAd);
    if (!newAd) return;

    try {
      const bsConverted = adToBs(newAd);
      setCurrentBs(bsConverted.formatted);
      setViewYear(bsConverted.year);
      setViewMonth(bsConverted.month);
      setBsInputError(null);
      onChange({ ad: newAd, bs: bsConverted.formatted });
    } catch (e: any) {
      setBsInputError(e?.message || "Invalid AD date for BS conversion");
    }
  };

  // Handle BS text input change
  const handleBsChange = (newBs: string) => {
    setCurrentBs(newBs);
    setBsInputError(null);

    // If fully typed (10 chars, YYYY-MM-DD)
    if (newBs.length === 10) {
      const parsed = parseBsDate(newBs);
      if (parsed) {
        try {
          const adObj = bsToAd(parsed.year, parsed.month, parsed.day);
          const adStr = formatAd(adObj);
          setCurrentAd(adStr);
          setViewYear(parsed.year);
          setViewMonth(parsed.month);
          setBsInputError(null);
          onChange({ ad: adStr, bs: newBs });
        } catch (e: any) {
          setBsInputError(e?.message || "Invalid BS date");
        }
      } else {
        setBsInputError("अमान्य मिति (Invalid BS Date)");
      }
    }
  };

  // Quick action: Set Today
  const handleSetToday = (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    const todayAd = getTodayAd();
    const todayBs = getTodayBs();
    setCurrentAd(todayAd);
    setCurrentBs(todayBs.formatted);
    setViewYear(todayBs.year);
    setViewMonth(todayBs.month);
    setBsInputError(null);
    setIsCalendarOpen(false);
    onChange({ ad: todayAd, bs: todayBs.formatted });
  };

  // Navigate calendar month
  const handlePrevMonth = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (viewMonth === 1) {
      if (viewYear > START_BS_YEAR) {
        setViewYear((y) => y - 1);
        setViewMonth(12);
      }
    } else {
      setViewMonth((m) => m - 1);
    }
  };

  const handleNextMonth = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (viewMonth === 12) {
      if (viewYear < END_BS_YEAR) {
        setViewYear((y) => y + 1);
        setViewMonth(1);
      }
    } else {
      setViewMonth((m) => m + 1);
    }
  };

  // Select a day in the calendar grid
  const handleSelectDay = (day: number) => {
    try {
      const newBs = formatBs(viewYear, viewMonth, day);
      const adObj = bsToAd(viewYear, viewMonth, day);
      const newAd = formatAd(adObj);

      setCurrentBs(newBs);
      setCurrentAd(newAd);
      setBsInputError(null);
      setIsCalendarOpen(false);
      onChange({ ad: newAd, bs: newBs });
    } catch (e: any) {
      setBsInputError(e?.message || "Failed to select date");
    }
  };

  // Calculate calendar grid properties
  let totalDaysInMonth = 30;
  try {
    totalDaysInMonth = daysInBsMonth(viewYear, viewMonth);
  } catch {
    totalDaysInMonth = 30;
  }

  let firstDayOfWeek = 0; // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
  try {
    const firstDayAd = bsToAd(viewYear, viewMonth, 1);
    firstDayOfWeek = firstDayAd.getUTCDay();
  } catch {
    firstDayOfWeek = 0;
  }

  const todayBs = getTodayBs();
  const selectedParsed = parseBsDate(currentBs);

  // Generate Year options around business range (e.g. 2070 to 2095)
  const availableYears: number[] = [];
  for (let y = Math.max(START_BS_YEAR, 2065); y <= Math.min(END_BS_YEAR, 2095); y++) {
    availableYears.push(y);
  }

  return (
    <div
      ref={containerRef}
      className={`nepali-date-picker-container relative ${className}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: compact ? "2px" : "4px",
        position: "relative",
      }}
    >
      {label && (
        <label
          style={{
            fontSize: "11px",
            fontWeight: "700",
            color: "#475569",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{label}</span>
          {!disabled && (
            <button
              type="button"
              onClick={handleSetToday}
              style={{
                background: "none",
                border: "none",
                color: "#1E3A8A",
                cursor: "pointer",
                fontSize: "11px",
                fontWeight: "600",
                display: "inline-flex",
                alignItems: "center",
                gap: "2px",
                padding: "0 2px",
              }}
              title="Set to Today (आज)"
            >
              <Clock size={11} />
              <span>आज (Today)</span>
            </button>
          )}
        </label>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: compact ? "1fr 1fr" : "1fr 1fr auto",
          gap: "8px",
          alignItems: "center",
        }}
      >
        {/* Bikram Sambat Input with Clickable Calendar Trigger */}
        <div style={{ position: "relative" }}>
          <div
            style={{
              position: "absolute",
              top: "2px",
              left: "6px",
              fontSize: "9.5px",
              fontWeight: "700",
              color: "#1E3A8A",
              pointerEvents: "none",
              textTransform: "uppercase",
              letterSpacing: "0.03em",
              zIndex: 1,
            }}
          >
            मिति (B.S.)
          </div>
          <input
            type="text"
            value={currentBs}
            onChange={(e) => handleBsChange(e.target.value)}
            onClick={() => {
              if (!disabled) {
                const parsed = parseBsDate(currentBs) || getTodayBs();
                setViewYear(parsed.year);
                setViewMonth(parsed.month);
                setIsCalendarOpen(true);
              }
            }}
            placeholder="2083-06-24"
            disabled={disabled}
            required={required}
            maxLength={10}
            style={{
              width: "100%",
              padding: "16px 28px 3px 8px",
              fontSize: "12.5px",
              fontWeight: "600",
              fontFamily: "monospace",
              color: "#0F172A",
              background: disabled ? "#F1F5F9" : "#FFFFFF",
              border: bsInputError ? "1.5px solid #EF4444" : isCalendarOpen ? "1.5px solid #1E3A8A" : "1px solid #CBD5E1",
              borderRadius: "4px",
              outline: "none",
              boxSizing: "border-box",
              cursor: disabled ? "not-allowed" : "pointer",
            }}
            title="Nepali Date (Bikram Sambat - Click to open calendar)"
          />

          {/* Calendar Icon Button */}
          {!disabled && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                const parsed = parseBsDate(currentBs) || getTodayBs();
                setViewYear(parsed.year);
                setViewMonth(parsed.month);
                setIsCalendarOpen((prev) => !prev);
              }}
              style={{
                position: "absolute",
                right: "6px",
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                color: isCalendarOpen ? "#1E3A8A" : "#64748B",
                cursor: "pointer",
                padding: "2px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Open Bikram Sambat Calendar"
              aria-label="Open Bikram Sambat Calendar"
            >
              <CalendarIcon size={16} />
            </button>
          )}
        </div>

        {/* Gregorian (AD) Input */}
        <div style={{ position: "relative" }}>
          <div
            style={{
              position: "absolute",
              top: "2px",
              left: "6px",
              fontSize: "9.5px",
              fontWeight: "700",
              color: "#64748B",
              pointerEvents: "none",
              textTransform: "uppercase",
              letterSpacing: "0.03em",
              zIndex: 1,
            }}
          >
            Date (A.D.)
          </div>
          <input
            type="date"
            value={currentAd}
            onChange={(e) => handleAdChange(e.target.value)}
            disabled={disabled}
            required={required}
            style={{
              width: "100%",
              padding: "16px 6px 3px 6px",
              fontSize: "12px",
              fontWeight: "600",
              fontFamily: "monospace",
              color: "#0F172A",
              background: disabled ? "#F1F5F9" : "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              outline: "none",
              boxSizing: "border-box",
            }}
            title="Gregorian Date (YYYY-MM-DD)"
          />
        </div>

        {/* Quick Today Button */}
        {!label && !compact && !disabled && (
          <button
            type="button"
            onClick={handleSetToday}
            style={{
              padding: "7px 10px",
              fontSize: "11px",
              fontWeight: "600",
              color: "#1E3A8A",
              background: "#EFF6FF",
              border: "1px solid #BFDBFE",
              borderRadius: "4px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              whiteSpace: "nowrap",
            }}
            title="Set Today (आज)"
          >
            <Clock size={12} />
            <span>आज</span>
          </button>
        )}
      </div>

      {bsInputError && (
        <span style={{ fontSize: "11px", color: "#EF4444", marginTop: "2px" }}>
          {bsInputError}
        </span>
      )}

      {/* ========================================================================= */}
      {/* INTERACTIVE BIKRAM SAMBAT CALENDAR POPOVER                                */}
      {/* ========================================================================= */}
      {isCalendarOpen && (
        <div
          ref={calendarRef}
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            zIndex: 9999,
            width: "320px",
            backgroundColor: "#FFFFFF",
            borderRadius: "8px",
            border: "1px solid #CBD5E1",
            boxShadow:
              "0 10px 25px -5px rgba(0, 0, 0, 0.2), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
            padding: "12px",
            boxSizing: "border-box",
          }}
        >
          {/* Calendar Header: Month/Year navigation & selection */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "10px",
              gap: "4px",
            }}
          >
            <button
              type="button"
              onClick={handlePrevMonth}
              style={{
                background: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: "4px",
                padding: "4px 6px",
                cursor: "pointer",
                color: "#1E293B",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Previous Month (अघिल्लो महिना)"
            >
              <ChevronLeft size={16} />
            </button>

            {/* Month Selector */}
            <select
              value={viewMonth}
              onChange={(e) => setViewMonth(parseInt(e.target.value, 10))}
              style={{
                padding: "4px 6px",
                fontSize: "12px",
                fontWeight: "700",
                color: "#0F172A",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                background: "#FFFFFF",
                outline: "none",
                cursor: "pointer",
                flex: "1.2",
              }}
            >
              {NEPALI_MONTHS_NE.map((neName, idx) => (
                <option key={idx + 1} value={idx + 1}>
                  {neName} ({NEPALI_MONTHS_EN[idx]})
                </option>
              ))}
            </select>

            {/* Year Selector */}
            <select
              value={viewYear}
              onChange={(e) => setViewYear(parseInt(e.target.value, 10))}
              style={{
                padding: "4px 6px",
                fontSize: "12px",
                fontWeight: "700",
                color: "#0F172A",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                background: "#FFFFFF",
                outline: "none",
                cursor: "pointer",
                flex: "0.8",
              }}
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>
                  {y} BS
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={handleNextMonth}
              style={{
                background: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: "4px",
                padding: "4px 6px",
                cursor: "pointer",
                color: "#1E293B",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              title="Next Month (पछिल्लो महिना)"
            >
              <ChevronRight size={16} />
            </button>
          </div>

          {/* Days-of-week header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(7, 1fr)",
              gap: "2px",
              textAlign: "center",
              marginBottom: "6px",
              borderBottom: "1px solid #F1F5F9",
              paddingBottom: "4px",
            }}
          >
            {NEPALI_DAYS_SHORT.map((dayName, idx) => {
              const isSaturday = idx === 6;
              return (
                <div
                  key={idx}
                  style={{
                    fontSize: "10px",
                    fontWeight: "700",
                    color: isSaturday ? "#DC2626" : "#64748B",
                  }}
                  title={NEPALI_DAYS_EN[idx]}
                >
                  {dayName}
                </div>
              );
            })}
          </div>

          {/* Day Numbers Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(7, 1fr)",
              gap: "3px",
              textAlign: "center",
            }}
          >
            {/* Blank offset cells before the 1st of the month */}
            {Array.from({ length: firstDayOfWeek }).map((_, idx) => (
              <div key={`offset-${idx}`} style={{ height: "30px" }} />
            ))}

            {/* Day cells 1 to totalDaysInMonth */}
            {Array.from({ length: totalDaysInMonth }).map((_, idx) => {
              const d = idx + 1;
              const isSaturday = (firstDayOfWeek + idx) % 7 === 6;
              const isToday =
                todayBs.year === viewYear &&
                todayBs.month === viewMonth &&
                todayBs.day === d;
              const isSelected =
                selectedParsed &&
                selectedParsed.year === viewYear &&
                selectedParsed.month === viewMonth &&
                selectedParsed.day === d;

              return (
                <button
                  key={d}
                  type="button"
                  onClick={() => handleSelectDay(d)}
                  style={{
                    height: "30px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "12px",
                    fontWeight: isSelected ? "800" : isToday ? "700" : "500",
                    color: isSelected
                      ? "#FFFFFF"
                      : isSaturday
                      ? "#DC2626"
                      : "#0F172A",
                    backgroundColor: isSelected
                      ? "#1E3A8A"
                      : isToday
                      ? "#EFF6FF"
                      : "transparent",
                    border: isToday && !isSelected
                      ? "1.5px solid #2563EB"
                      : "1px solid transparent",
                    borderRadius: "4px",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = "#F1F5F9";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) {
                      e.currentTarget.style.backgroundColor = isToday
                        ? "#EFF6FF"
                        : "transparent";
                    }
                  }}
                  title={`${viewYear}-${String(viewMonth).padStart(2, "0")}-${String(d).padStart(2, "0")} BS`}
                >
                  {d}
                </button>
              );
            })}
          </div>

          {/* Calendar Footer: Quick Jump to Today & Close */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "10px",
              paddingTop: "8px",
              borderTop: "1px solid #E2E8F0",
              fontSize: "11px",
            }}
          >
            <button
              type="button"
              onClick={handleSetToday}
              style={{
                background: "none",
                border: "none",
                color: "#1E3A8A",
                fontWeight: "700",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "3px",
                padding: "2px 4px",
              }}
              title="Jump to today"
            >
              <Clock size={12} />
              <span>आज: {todayBs.formatted}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsCalendarOpen(false)}
              style={{
                background: "#F1F5F9",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                color: "#475569",
                fontWeight: "600",
                cursor: "pointer",
                padding: "3px 8px",
                display: "flex",
                alignItems: "center",
                gap: "2px",
              }}
            >
              <X size={12} />
              <span>बन्द</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
