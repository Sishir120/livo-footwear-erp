"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  TrendingUp,
  Calendar,
  Users,
  Clock,
  Boxes,
  Plus,
  RefreshCw,
  Download,
  AlertCircle,
  X,
  Sliders,
  ChevronRight
} from "lucide-react";
import { TABULAR_NUMS_STYLE } from "@/lib/currency";
import { useLocale } from "@/context/LocaleContext";

interface ProductionAnalyticsViewProps {
  userRole?: string;
}

interface DailyRecord {
  date_ad: string;
  date_bs: string;
  worker_count: number;
  total_working_hours: number;
  pairs_produced: number;
  pairs_per_worker: number;
  pairs_per_hour: number;
}

interface ProductionSummary {
  avg_daily_workers: number;
  total_pairs_produced: number;
  avg_pairs_per_worker: number;
  avg_pairs_per_man_hour: number;
}

export function ProductionAnalyticsView({ userRole }: ProductionAnalyticsViewProps) {
  const { isNepali, t } = useLocale();
  const isViewer = userRole === "viewer";

  const [timeframe, setTimeframe] = useState<"1m" | "3m" | "1y">("1m");
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<ProductionSummary | null>(null);
  const [records, setRecords] = useState<DailyRecord[]>([]);
  const [hoveredPoint, setHoveredPoint] = useState<DailyRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Modal: Log daily hours
  const [showLogModal, setShowLogModal] = useState(false);
  const [logDateAd, setLogDateAd] = useState(() => new Date().toISOString().split("T")[0]);
  const [logWorkers, setLogWorkers] = useState("45");
  const [logHours, setLogHours] = useState("360");
  const [logPairs, setLogPairs] = useState("");
  const [submittingLog, setSubmittingLog] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);

  const fetchRatios = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/analytics/production-ratios?timeframe=${timeframe}`);
      if (!res.ok) throw new Error(`Failed to load ratios: ${res.statusText}`);
      const data = await res.json();
      setSummary(data.summary);
      setRecords(data.daily_records || []);
    } catch (err: any) {
      setError(err.message || "Failed to load production ratios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRatios();
  }, [timeframe]);

  // Submit Daily Log
  const handleLogSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;
    setSubmittingLog(true);
    setLogError(null);

    try {
      const payload: any = {
        date_ad: logDateAd,
        total_workers: parseInt(logWorkers, 10),
        total_working_hours: parseFloat(logHours)
      };
      if (logPairs.trim() !== "") {
        payload.total_pairs_produced = parseInt(logPairs, 10);
      }

      const res = await fetch("/api/v1/analytics/daily-logs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || "Failed to record log");
      }

      setShowLogModal(false);
      setLogPairs("");
      fetchRatios();
    } catch (err: any) {
      setLogError(err.message || "Failed to save daily log");
    } finally {
      setSubmittingLog(false);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (!records.length) return;
    const headers = ["Date AD", "Date BS", "Worker Count", "Shift Hours (TWH)", "Pairs Produced", "Pairs / Worker", "Pairs / Hour"];
    const rows = records.map((r) => [
      r.date_ad,
      r.date_bs,
      r.worker_count,
      r.total_working_hours,
      r.pairs_produced,
      r.pairs_per_worker,
      r.pairs_per_hour
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Production_Ratios_${timeframe}_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // SVG Chart Computations
  const chartData = useMemo(() => {
    if (!records || records.length === 0) return null;
    const maxPairs = Math.max(...records.map((r) => r.pairs_produced), 10);
    const maxRatio = Math.max(...records.map((r) => r.pairs_per_worker), 5);
    return { maxPairs, maxRatio };
  }, [records]);

  const svgWidth = 1000;
  const svgHeight = 280;
  const padding = { top: 30, right: 60, bottom: 40, left: 60 };
  const graphWidth = svgWidth - padding.left - padding.right;
  const graphHeight = svgHeight - padding.top - padding.bottom;

  return (
    <div style={{ padding: "24px 32px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
              {t("ratios_title")}
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#E0E7FF",
                color: "#1E3A8A",
                padding: "2px 8px",
                borderRadius: "3px"
              }}
            >
              POINTS 6 &amp; 9 SPEC
            </span>
          </div>
          <p style={{ fontSize: "12.5px", color: "#475569", marginTop: "4px", margin: 0 }}>
            {t("ratios_desc")}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Timeframe selector tabs */}
          <div style={{ display: "flex", border: "1px solid #CBD5E1", borderRadius: "4px", overflow: "hidden", background: "#FFFFFF" }}>
            <button
              onClick={() => setTimeframe("1m")}
              style={{
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                background: timeframe === "1m" ? "#1E3A8A" : "#FFFFFF",
                color: timeframe === "1m" ? "#FFFFFF" : "#475569",
                border: "none",
                cursor: "pointer"
              }}
            >
              {t("timeframe_1m")}
            </button>
            <button
              onClick={() => setTimeframe("3m")}
              style={{
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                background: timeframe === "3m" ? "#1E3A8A" : "#FFFFFF",
                color: timeframe === "3m" ? "#FFFFFF" : "#475569",
                border: "none",
                borderLeft: "1px solid #CBD5E1",
                borderRight: "1px solid #CBD5E1",
                cursor: "pointer"
              }}
            >
              {t("timeframe_3m")}
            </button>
            <button
              onClick={() => setTimeframe("1y")}
              style={{
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                background: timeframe === "1y" ? "#1E3A8A" : "#FFFFFF",
                color: timeframe === "1y" ? "#FFFFFF" : "#475569",
                border: "none",
                cursor: "pointer"
              }}
            >
              {t("timeframe_1y")}
            </button>
          </div>

          <button onClick={fetchRatios} disabled={loading} className="pagination-btn" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{isNepali ? "ताजा गर्नुहोस्" : "Refresh"}</span>
          </button>

          <button onClick={handleExportCSV} className="pagination-btn" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Download size={13} />
            <span>Export CSV</span>
          </button>

          {!isViewer && (
            <button
              onClick={() => {
                setLogError(null);
                setShowLogModal(true);
              }}
              style={{
                background: "#047857",
                color: "#FFFFFF",
                border: "none",
                padding: "6px 14px",
                borderRadius: "4px",
                fontSize: "12.5px",
                fontWeight: "600",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <Plus size={14} />
              <span>{t("log_shift_hours")}</span>
            </button>
          )}
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "14px", marginBottom: "20px" }}>
        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("avg_workers")}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {summary ? summary.avg_daily_workers : 0} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>workers/day</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>Active floor assembly staff</div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#1E3A8A", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("pairs_produced")}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#1E3A8A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {summary ? summary.total_pairs_produced.toLocaleString() : 0} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>pairs</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>Consolidated finished output</div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#047857", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("pairs_per_worker")}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#047857", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {summary ? summary.avg_pairs_per_worker : 0} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>pairs/worker</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>Output per artisan per day</div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#7C3AED", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("pairs_per_hour")}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#7C3AED", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {summary ? summary.avg_pairs_per_man_hour : 0} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>pairs/hr</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>Hourly factory speed index</div>
        </div>
      </div>

      {/* SVG Dual-Axis Chart Container */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "20px", marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <h2 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
              {isNepali ? "उत्पादन परिमाण र कामदार दक्षता अनुपात ग्राफ" : "Daily Output & Worker Efficiency Ratio Trend"}
            </h2>
            <div style={{ fontSize: "11.5px", color: "#64748B", marginTop: "2px" }}>
              Bars: Finished Pairs Produced • Green Line: Output Ratio (Pairs / Worker)
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px", fontSize: "11.5px", fontWeight: "600" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "12px", height: "12px", background: "#1E3A8A", borderRadius: "2px", display: "inline-block" }}></span>
              <span>Output (Pairs)</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "12px", height: "3px", background: "#059669", display: "inline-block" }}></span>
              <span>Ratio (Pairs/Worker)</span>
            </div>
          </div>
        </div>

        {/* SVG Render */}
        {loading ? (
          <div style={{ height: "280px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748B" }}>
            <RefreshCw size={20} className="animate-spin" style={{ marginRight: "8px" }} />
            <span>Calculating daily production ratio analytics...</span>
          </div>
        ) : !chartData || records.length === 0 ? (
          <div style={{ height: "240px", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", color: "#64748B" }}>
            <Boxes size={36} style={{ marginBottom: "8px", opacity: 0.4 }} />
            <div>No production batches or daily shift logs recorded for this timeframe ({timeframe}).</div>
          </div>
        ) : (
          <div style={{ width: "100%", overflowX: "auto" }}>
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              style={{ width: "100%", minWidth: "750px", height: "auto", overflow: "visible" }}
            >
              {/* Background grid lines */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((frac, i) => {
                const y = padding.top + graphHeight * (1 - frac);
                const valPairs = Math.round(chartData.maxPairs * frac);
                const valRatio = (chartData.maxRatio * frac).toFixed(1);
                return (
                  <g key={i}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={svgWidth - padding.right}
                      y2={y}
                      stroke="#E2E8F0"
                      strokeDasharray={frac > 0 ? "3 3" : undefined}
                    />
                    {/* Left Axis Label (Pairs) */}
                    <text x={padding.left - 8} y={y + 4} textAnchor="end" fontSize="10" fill="#64748B" style={TABULAR_NUMS_STYLE}>
                      {valPairs}
                    </text>
                    {/* Right Axis Label (Ratio) */}
                    <text x={svgWidth - padding.right + 8} y={y + 4} textAnchor="start" fontSize="10" fill="#059669" style={TABULAR_NUMS_STYLE}>
                      {valRatio}
                    </text>
                  </g>
                );
              })}

              {/* Bars (Output Pairs) */}
              {records.map((r, idx) => {
                const step = graphWidth / Math.max(records.length, 1);
                const barWidth = Math.max(Math.min(step * 0.6, 28), 6);
                const x = padding.left + idx * step + (step - barWidth) / 2;
                const barHeight = (r.pairs_produced / chartData.maxPairs) * graphHeight;
                const y = padding.top + graphHeight - barHeight;

                return (
                  <rect
                    key={`bar-${idx}`}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={Math.max(barHeight, 0)}
                    fill="#1E3A8A"
                    rx={2}
                    opacity={hoveredPoint && hoveredPoint.date_ad === r.date_ad ? 1.0 : 0.85}
                    style={{ cursor: "pointer", transition: "opacity 0.15s ease" }}
                    onMouseEnter={() => setHoveredPoint(r)}
                  />
                );
              })}

              {/* Line & Dots (Pairs / Worker Ratio) */}
              {(() => {
                const step = graphWidth / Math.max(records.length, 1);
                const points = records.map((r, idx) => {
                  const cx = padding.left + idx * step + step / 2;
                  const cy = padding.top + graphHeight - (r.pairs_per_worker / chartData.maxRatio) * graphHeight;
                  return { cx, cy, r };
                });
                const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.cx} ${p.cy}`).join(" ");

                return (
                  <g>
                    <path d={pathD} fill="none" stroke="#059669" strokeWidth="2.5" />
                    {points.map((p, idx) => (
                      <circle
                        key={`dot-${idx}`}
                        cx={p.cx}
                        cy={p.cy}
                        r={hoveredPoint && hoveredPoint.date_ad === p.r.date_ad ? 6 : 3.5}
                        fill="#FFFFFF"
                        stroke="#059669"
                        strokeWidth="2.5"
                        style={{ cursor: "pointer" }}
                        onMouseEnter={() => setHoveredPoint(p.r)}
                      />
                    ))}
                  </g>
                );
              })()}

              {/* X Axis Date Labels */}
              {records.map((r, idx) => {
                // Show dates every N steps depending on count
                const step = graphWidth / Math.max(records.length, 1);
                const showEvery = Math.ceil(records.length / 10);
                if (idx % showEvery !== 0 && idx !== records.length - 1) return null;

                const x = padding.left + idx * step + step / 2;
                const label = r.date_ad.slice(5); // MM-DD

                return (
                  <text
                    key={`label-${idx}`}
                    x={x}
                    y={svgHeight - 12}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#64748B"
                    style={TABULAR_NUMS_STYLE}
                  >
                    {label}
                  </text>
                );
              })}
            </svg>
          </div>
        )}

        {/* Hovered Point Card */}
        {hoveredPoint && (
          <div style={{ marginTop: "12px", background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "6px", padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", fontSize: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Calendar size={14} color="#1E3A8A" />
              <span style={{ fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                {hoveredPoint.date_ad} <span style={{ color: "#64748B", fontWeight: "400" }}>({hoveredPoint.date_bs})</span>
              </span>
            </div>
            <div style={{ display: "flex", gap: "16px" }}>
              <div>
                <span style={{ color: "#64748B" }}>Workers: </span>
                <span style={{ fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>{hoveredPoint.worker_count}</span>
              </div>
              <div>
                <span style={{ color: "#64748B" }}>Shift Hours: </span>
                <span style={{ fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>{hoveredPoint.total_working_hours}h</span>
              </div>
              <div>
                <span style={{ color: "#1E3A8A" }}>Output: </span>
                <span style={{ fontWeight: "700", color: "#1E3A8A", ...TABULAR_NUMS_STYLE }}>{hoveredPoint.pairs_produced} pairs</span>
              </div>
              <div>
                <span style={{ color: "#059669" }}>Ratio: </span>
                <span style={{ fontWeight: "700", color: "#059669", ...TABULAR_NUMS_STYLE }}>{hoveredPoint.pairs_per_worker} pairs/worker</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Detailed Tabular Log Table */}
      <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
        <table className="data-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
          <thead>
            <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
              <th style={{ padding: "10px 14px", fontWeight: "600" }}>Date (AD)</th>
              <th style={{ padding: "10px 14px", fontWeight: "600" }}>Date (BS)</th>
              <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Active Workers</th>
              <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Shift Hours (TWH)</th>
              <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Pairs Produced</th>
              <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Ratio (Pairs/Worker)</th>
              <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Speed (Pairs/Hour)</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: "30px", textAlign: "center", color: "#64748B" }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                  <div>Loading production log table...</div>
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
                  <Boxes size={32} style={{ margin: "0 auto 8px", opacity: 0.5 }} />
                  <div>No daily production records found for this period</div>
                </td>
              </tr>
            ) : (
              records.map((r, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #F1F5F9" }}>
                  <td style={{ padding: "10px 14px", fontWeight: "600", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                    {r.date_ad}
                  </td>
                  <td style={{ padding: "10px 14px", color: "#64748B", ...TABULAR_NUMS_STYLE }}>
                    {r.date_bs}
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                    {r.worker_count}
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                    {r.total_working_hours.toFixed(1)} hrs
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "700", color: "#1E3A8A", ...TABULAR_NUMS_STYLE }}>
                    {r.pairs_produced.toLocaleString()}
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "700", color: "#059669", ...TABULAR_NUMS_STYLE }}>
                    {r.pairs_per_worker.toFixed(2)}
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right", color: "#7C3AED", ...TABULAR_NUMS_STYLE }}>
                    {r.pairs_per_hour.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL: LOG DAILY SHIFT HOURS */}
      {showLogModal && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
        >
          <div style={{ background: "#FFFFFF", borderRadius: "8px", width: "100%", maxWidth: "480px", overflow: "hidden", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Clock size={18} color="#047857" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {t("log_shift_hours")}
                </h3>
              </div>
              <button onClick={() => setShowLogModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleLogSubmit} style={{ padding: "20px" }}>
              {logError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {logError}
                </div>
              )}

              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Date (AD) *
                </label>
                <input
                  type="date"
                  required
                  value={logDateAd}
                  onChange={(e) => setLogDateAd(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Total Workers on Floor *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={logWorkers}
                    onChange={(e) => setLogWorkers(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Total Shift Hours *
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    required
                    value={logHours}
                    onChange={(e) => setLogHours(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "18px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Pairs Produced (Optional override, otherwise auto-sums batches)
                </label>
                <input
                  type="number"
                  min="0"
                  placeholder="Leave empty to auto-sum completed batches"
                  value={logPairs}
                  onChange={(e) => setLogPairs(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={submittingLog}
                  style={{ padding: "7px 18px", border: "none", borderRadius: "4px", background: "#047857", color: "#FFFFFF", fontSize: "12.5px", fontWeight: "600", cursor: "pointer" }}
                >
                  {submittingLog ? "Saving..." : t("commit_record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
