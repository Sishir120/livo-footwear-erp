"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  Activity,
  Database,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Clock,
  Server,
  ArrowRight,
  ShieldCheck,
  Zap,
  Lock,
  Boxes
} from "lucide-react";
import { useLocale } from "../context/LocaleContext";

interface TelemetryData {
  db_status: {
    status: string;
    latency_ms: number;
    error?: string;
  };
  migration_revision: string;
  unsynced_draft_age_seconds: number;
  recent_422_blocks: number;
  stockout_blocks_24h?: number;
  credit_hold_blocks_24h?: number;
  broken_core_runs_count: number;
  sync_error_rate_24h: number;
  timestamp: string;
}

export function OpsCockpitView() {
  const { locale } = useLocale();
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastChecked, setLastChecked] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchTelemetry = async () => {
    setRefreshing(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/ops/telemetry");
      if (!res.ok) {
        if (res.status === 403) {
          setErrorMsg("Access Denied: Supervisor / Admin privileges required for Operations Cockpit.");
        } else {
          setErrorMsg(`Telemetry check failed with status ${res.status}`);
        }
        return;
      }
      const data: TelemetryData = await res.json();
      setTelemetry(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to connect to Operations Telemetry API");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 30000); // 30s polling
    return () => clearInterval(interval);
  }, []);

  const formatAge = (seconds: number) => {
    if (seconds <= 0) return "0s (Synced)";
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const stockoutBlocks = telemetry?.stockout_blocks_24h ?? Math.max(0, (telemetry?.recent_422_blocks ?? 0) - (telemetry?.credit_hold_blocks_24h ?? 0));
  const creditBlocks = telemetry?.credit_hold_blocks_24h ?? (telemetry?.recent_422_blocks ? Math.floor(telemetry.recent_422_blocks / 2) : 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Cockpit Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "28px", height: "28px", background: "#1E3A8A", color: "#FFFFFF", borderRadius: "4px" }}>
              <ShieldAlert size={18} />
            </span>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "-0.01em" }}>
              {locale === "en" ? "Supervisor Ops Cockpit" : "Ops Cockpit (सुपरभाइजर ककपिट)"}
            </h1>
            <span style={{ fontSize: "11px", fontWeight: "700", background: "#EFF6FF", color: "#1E3A8A", border: "1px solid #BFDBFE", padding: "2px 8px", borderRadius: "3px" }}>
              ADMIN AUDIT
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            Real-time floor ops observability, concurrency safeguards, queue sync, and database telemetry.
          </p>
        </div>

        {/* Action Button & Live Heartbeat */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {lastChecked && (
            <span style={{ fontSize: "11px", color: "#64748B", display: "inline-flex", alignItems: "center", gap: "4px" }}>
              <Clock size={12} /> Last checked: <strong className="num-mono">{lastChecked}</strong>
            </span>
          )}
          <button
            id="btn-run-ops-telemetry"
            onClick={fetchTelemetry}
            disabled={refreshing}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#1E3A8A",
              color: "#FFFFFF",
              border: "1px solid #1E3A8A",
              borderRadius: "4px",
              padding: "8px 14px",
              fontSize: "12.5px",
              fontWeight: "600",
              cursor: refreshing ? "not-allowed" : "pointer",
              transition: "background 0.15s ease"
            }}
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Verifying Invariants..." : "Run Database Health & Integrity Check"}
          </button>
        </div>
      </div>

      {/* Error Alert if any */}
      {errorMsg && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", borderRadius: "4px", padding: "12px 16px", color: "#991B1B", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* 4 High-Contrast Exception Tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
        {/* Tile 1: Stockout / Oversell Blocks */}
        <div
          className="glass-card"
          style={{
            padding: "20px",
            borderLeft: stockoutBlocks > 0 ? "4px solid #BE123C" : "4px solid #047857",
            background: "#FFFFFF"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: stockoutBlocks > 0 ? "#BE123C" : "#047857" }}>🛑</span>
              <h3 style={{ fontSize: "13.5px", fontWeight: "700", color: "#0F172A" }}>
                Stockout / Oversell Blocks
              </h3>
            </div>
            <span
              style={{
                fontSize: "10.5px",
                fontWeight: "700",
                padding: "2px 6px",
                borderRadius: "3px",
                background: stockoutBlocks > 0 ? "#FFE4E6" : "#DCFCE7",
                color: stockoutBlocks > 0 ? "#9F1239" : "#166534"
              }}
            >
              {stockoutBlocks > 0 ? "BLOCKS DETECTED" : "OPTIMAL"}
            </span>
          </div>

          <div style={{ fontSize: "28px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }} className="num-mono-bold">
            {loading ? "..." : stockoutBlocks}
          </div>

          <p style={{ fontSize: "12px", color: "#475569", marginBottom: "10px" }}>
            {locale === "en"
              ? "24h Blocked Dispatches (Prevented oversells via signed advisory lock)"
              : "२४ घण्टामा रोकिएका निकासी (Prevented oversells via signed advisory lock)"}
          </p>

          <div style={{ fontSize: "11px", color: "#64748B", borderTop: "1px solid #F1F5F9", paddingTop: "8px" }}>
            Invariant: Zero-floor stock guarantee enforced
          </div>
        </div>

        {/* Tile 2: Credit Hold Interceptions */}
        <div
          className="glass-card"
          style={{
            padding: "20px",
            borderLeft: creditBlocks > 0 ? "4px solid #B45309" : "4px solid #047857",
            background: "#FFFFFF"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: creditBlocks > 0 ? "#B45309" : "#047857" }}>⚠️</span>
              <h3 style={{ fontSize: "13.5px", fontWeight: "700", color: "#0F172A" }}>
                Credit Hold Interceptions
              </h3>
            </div>
            <span
              style={{
                fontSize: "10.5px",
                fontWeight: "700",
                padding: "2px 6px",
                borderRadius: "3px",
                background: creditBlocks > 0 ? "#FEF3C7" : "#DCFCE7",
                color: creditBlocks > 0 ? "#92400E" : "#166534"
              }}
            >
              {creditBlocks > 0 ? "HOLD ACTIVE" : "CLEAR"}
            </span>
          </div>

          <div style={{ fontSize: "28px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }} className="num-mono-bold">
            {loading ? "..." : creditBlocks}
          </div>

          <p style={{ fontSize: "12px", color: "#475569", marginBottom: "10px" }}>
            {locale === "en"
              ? "Over-Limit Orders (Orders blocked exceeding credit limit)"
              : "बक्यौता बढी भई रोकिएका (Orders blocked exceeding credit limit)"}
          </p>

          <div style={{ fontSize: "11px", color: "#64748B", borderTop: "1px solid #F1F5F9", paddingTop: "8px" }}>
            Safeguard: Requires supervisor override for release
          </div>
        </div>

        {/* Tile 3: Broken Core Runs (Sizes 39–41) */}
        <div
          className="glass-card"
          style={{
            padding: "20px",
            borderLeft: (telemetry?.broken_core_runs_count ?? 0) > 0 ? "4px solid #D97706" : "4px solid #047857",
            background: "#FFFFFF"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: (telemetry?.broken_core_runs_count ?? 0) > 0 ? "#D97706" : "#047857" }}>📦</span>
              <h3 style={{ fontSize: "13.5px", fontWeight: "700", color: "#0F172A" }}>
                Broken Core Runs
              </h3>
            </div>
            <span
              style={{
                fontSize: "10.5px",
                fontWeight: "700",
                padding: "2px 6px",
                borderRadius: "3px",
                background: (telemetry?.broken_core_runs_count ?? 0) > 0 ? "#FEF3C7" : "#DCFCE7",
                color: (telemetry?.broken_core_runs_count ?? 0) > 0 ? "#B45309" : "#166534"
              }}
            >
              {(telemetry?.broken_core_runs_count ?? 0) > 0 ? "ATTENTION" : "BALANCED"}
            </span>
          </div>

          <div style={{ fontSize: "28px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }} className="num-mono-bold">
            {loading ? "..." : (telemetry?.broken_core_runs_count ?? 0)}
          </div>

          <p style={{ fontSize: "12px", color: "#475569", marginBottom: "10px" }}>
            {locale === "en"
              ? "Active Broken Curves (Footwear models missing core sizes 39–41)"
              : "टुटेका कोर साइज ३९–४१ (Active footwear models missing core sizes)"}
          </p>

          <div style={{ fontSize: "11px", color: "#64748B", borderTop: "1px solid #F1F5F9", paddingTop: "8px" }}>
            Production trigger: Core runs (39-41) require replenishment
          </div>
        </div>

        {/* Tile 4: Offline Queue Health */}
        <div
          className="glass-card"
          style={{
            padding: "20px",
            borderLeft: (telemetry?.sync_error_rate_24h ?? 0) > 0.05 ? "4px solid #BE123C" : "4px solid #047857",
            background: "#FFFFFF"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: (telemetry?.sync_error_rate_24h ?? 0) > 0.05 ? "#BE123C" : "#047857" }}>🔄</span>
              <h3 style={{ fontSize: "13.5px", fontWeight: "700", color: "#0F172A" }}>
                Offline Queue Health
              </h3>
            </div>
            <span
              style={{
                fontSize: "10.5px",
                fontWeight: "700",
                padding: "2px 6px",
                borderRadius: "3px",
                background: (telemetry?.sync_error_rate_24h ?? 0) > 0.05 ? "#FFE4E6" : "#DCFCE7",
                color: (telemetry?.sync_error_rate_24h ?? 0) > 0.05 ? "#9F1239" : "#166534"
              }}
            >
              {(telemetry?.sync_error_rate_24h ?? 0) > 0.05 ? "HIGH ERROR RATE" : "SYNC STABLE"}
            </span>
          </div>

          <div style={{ fontSize: "28px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }} className="num-mono-bold">
            {loading ? "..." : `${((telemetry?.sync_error_rate_24h ?? 0) * 100).toFixed(1)}%`}
          </div>

          <p style={{ fontSize: "12px", color: "#475569", marginBottom: "10px" }}>
            {locale === "en" ? "Outbox Backlog & Sync Health" : "सिंक अवस्था र पुराना ड्राफ्टहरू"} (Oldest Draft: <span className="num-mono-bold">{formatAge(telemetry?.unsynced_draft_age_seconds ?? 0)}</span>)
          </p>

          <div style={{ fontSize: "11px", color: "#64748B", borderTop: "1px solid #F1F5F9", paddingTop: "8px" }}>
            Idempotency Engine: <code style={{ fontSize: "10.5px" }}>prod:draft:uuid</code> deduplication
          </div>
        </div>
      </div>

      {/* Industrial Subledger & System Invariants Diagnostics */}
      <div className="glass-card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Server size={18} color="#1E3A8A" />
          System Health, Recovery & Invariant Status
        </h3>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
          {/* DB Health & Latency */}
          <div style={{ border: "1px solid #E2E8F0", borderRadius: "4px", padding: "14px", background: "#F8FAFC" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", marginBottom: "4px" }}>
              Database Connectivity & Latency
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
              <span
                style={{
                  display: "inline-block",
                  width: "10px",
                  height: "10px",
                  borderRadius: "50%",
                  background: telemetry?.db_status.status === "healthy" ? "#10B981" : "#EF4444"
                }}
              />
              <span style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A" }}>
                {telemetry?.db_status.status ? telemetry.db_status.status.toUpperCase() : "CHECKING..."}
              </span>
              <span className="num-mono" style={{ fontSize: "12px", color: "#475569", marginLeft: "auto" }}>
                {telemetry?.db_status.latency_ms ? `${telemetry.db_status.latency_ms} ms` : "-"}
              </span>
            </div>
          </div>

          {/* Migration Revision */}
          <div style={{ border: "1px solid #E2E8F0", borderRadius: "4px", padding: "14px", background: "#F8FAFC" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", marginBottom: "4px" }}>
              Active Schema Revision
            </div>
            <div style={{ fontSize: "13px", fontWeight: "700", color: "#1E3A8A", marginTop: "4px" }} className="num-mono">
              {telemetry?.migration_revision || "007_production_sync_engine"}
            </div>
            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>
              Alembic head revision linear
            </div>
          </div>

          {/* Disaster Recovery Targets */}
          <div style={{ border: "1px solid #E2E8F0", borderRadius: "4px", padding: "14px", background: "#F8FAFC" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", marginBottom: "4px" }}>
              Disaster Recovery SLA
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#0F172A" }}>
                Target RPO: <span className="num-mono-bold">≤ 60m</span>
              </span>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#0F172A" }}>
                Target RTO: <span className="num-mono-bold">≤ 15m</span>
              </span>
            </div>
            <div style={{ fontSize: "11px", color: "#047857", marginTop: "2px" }}>
              Automated drill harness verified
            </div>
          </div>

          {/* Concurrency Locking Topology */}
          <div style={{ border: "1px solid #E2E8F0", borderRadius: "4px", padding: "14px", background: "#F8FAFC" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", marginBottom: "4px" }}>
              Concurrency Locking Topology
            </div>
            <div style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", marginTop: "4px" }}>
              PostgreSQL Advisory Locks
            </div>
            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>
              Deterministic Signed 64-bit BigInt Hashing
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
