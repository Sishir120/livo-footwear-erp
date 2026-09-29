"use client";

import React, { useState, useEffect } from "react";
import {
  Wifi,
  WifiOff,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  X,
  Trash2,
  Send
} from "lucide-react";
import {
  subscribeDraftChanges,
  getAllDrafts,
  deleteDraft,
  drainPendingProductionDrafts,
  ProductionDraft
} from "@/lib/offlineDb";
import { useLocale } from "../context/LocaleContext";

export function NetworkStatusBadge() {
  const { locale } = useLocale();
  const [isOnline, setIsOnline] = useState(true);
  const [draftStats, setDraftStats] = useState({ pending: 0, rejected: 0, syncing: 0 });
  const [syncingProgress, setSyncingProgress] = useState<{ current: number; total: number } | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [draftsList, setDraftsList] = useState<ProductionDraft[]>([]);
  const [isSyncingNow, setIsSyncingNow] = useState(false);

  // 1. Connection check with ping debounce
  useEffect(() => {
    let mounted = true;

    const checkHealth = async () => {
      if (typeof navigator !== "undefined" && !navigator.onLine) {
        if (mounted) setIsOnline(false);
        return;
      }
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const res = await fetch("/api/v1/health", {
          signal: controller.signal,
          cache: "no-store"
        });
        clearTimeout(timeoutId);
        if (mounted) setIsOnline(res.ok);
      } catch {
        if (mounted) setIsOnline(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);

    const handleOnline = () => {
      setIsOnline(true);
      // Auto-drain drafts upon reconnection
      triggerSync();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    // 2. Subscribe to draft queue changes
    const unsub = subscribeDraftChanges((stats) => {
      if (mounted) setDraftStats(stats);
    });

    return () => {
      mounted = false;
      clearInterval(interval);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      unsub();
    };
  }, []);

  const triggerSync = async () => {
    if (isSyncingNow) return;
    setIsSyncingNow(true);
    try {
      await drainPendingProductionDrafts((curr, tot) => {
        setSyncingProgress({ current: curr, total: tot });
      });
      // Refresh drawer list if open
      if (showDrawer) {
        const updated = await getAllDrafts();
        setDraftsList(updated);
      }
    } finally {
      setIsSyncingNow(false);
      setSyncingProgress(null);
    }
  };

  const handleOpenDrawer = async () => {
    const list = await getAllDrafts();
    setDraftsList(list);
    setShowDrawer(true);
  };

  const handleDeleteDraft = async (key: string) => {
    await deleteDraft(key);
    const updated = await getAllDrafts();
    setDraftsList(updated);
  };

  // Convert number to Nepali digits
  const toNeDigits = (num: number): string => {
    const neMap = ["०", "१", "२", "३", "४", "५", "६", "७", "८", "९"];
    return String(num).split("").map((d) => neMap[parseInt(d, 10)] ?? d).join("");
  };

  // Determine visual badge state
  const totalQueue = draftStats.pending + draftStats.syncing;
  const hasConflicts = draftStats.rejected > 0;
  const isSyncing = isSyncingNow || draftStats.syncing > 0;

  let badgeBg = "#DCFCE7";
  let badgeBorder = "#86EFAC";
  let badgeText = "#166534";
  let badgeIcon = <Wifi size={13} color="#166534" />;
  let badgeLabel = locale === "en" ? "Online" : "अनलाइन (Online)";

  if (!isOnline) {
    badgeBg = "#FEF3C7";
    badgeBorder = "#FCD34D";
    badgeText = "#92400E";
    badgeIcon = <WifiOff size={13} color="#92400E" />;
    if (locale === "en") {
      badgeLabel = totalQueue > 0 ? `Offline (${totalQueue} batches stored)` : "Offline";
    } else {
      badgeLabel = totalQueue > 0
        ? `अफलाइन (Offline — ${toNeDigits(totalQueue)} ब्याच सुरक्षित)`
        : "अफलाइन (Offline)";
    }
  } else if (hasConflicts) {
    badgeBg = "#FEE2E2";
    badgeBorder = "#FCA5A5";
    badgeText = "#991B1B";
    badgeIcon = <AlertTriangle size={13} color="#991B1B" />;
    badgeLabel = locale === "en"
      ? `Sync conflict (${draftStats.rejected} batches require review)`
      : `सिंक समस्या (Sync conflict — ${toNeDigits(draftStats.rejected)} ब्याच समीक्षा आवश्यक)`;
  } else if (isSyncing) {
    badgeBg = "#DBEAFE";
    badgeBorder = "#93C5FD";
    badgeText = "#1E40AF";
    badgeIcon = <RefreshCw size={13} className="animate-spin" color="#1E40AF" />;
    if (locale === "en") {
      badgeLabel = syncingProgress
        ? `Syncing... (${syncingProgress.current}/${syncingProgress.total})`
        : "Syncing queue...";
    } else {
      badgeLabel = syncingProgress
        ? `सिंक हुँदै... (Syncing ${syncingProgress.current}/${syncingProgress.total})`
        : "सिंक हुँदै... (Syncing queue)";
    }
  } else if (totalQueue > 0) {
    badgeBg = "#FEF3C7";
    badgeBorder = "#FCD34D";
    badgeText = "#92400E";
    badgeIcon = <RefreshCw size={13} color="#92400E" />;
    badgeLabel = locale === "en"
      ? `${totalQueue} batches queued`
      : `${toNeDigits(totalQueue)} ब्याच सिंक पर्खाइमा (Queued)`;
  }

  return (
    <>
      {/* Visual Header Badge */}
      <button
        onClick={handleOpenDrawer}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          padding: "3px 10px",
          borderRadius: "4px",
          fontSize: "11.5px",
          fontWeight: "600",
          backgroundColor: badgeBg,
          border: `1px solid ${badgeBorder}`,
          color: badgeText,
          cursor: "pointer",
          transition: "all 0.15s ease",
          userSelect: "none"
        }}
        title="Click to view offline production queue & draft sync drawer"
      >
        {badgeIcon}
        <span>{badgeLabel}</span>
      </button>

      {/* Offline Queue Inspector Drawer */}
      {showDrawer && (
        <div className="modal-overlay" style={{ zIndex: 150 }}>
          <div
            className="modal-drawer"
            style={{
              maxWidth: "640px",
              width: "92vw",
              maxHeight: "88vh",
              display: "flex",
              flexDirection: "column",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px"
            }}
          >
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <RefreshCw size={18} color="#1E3A8A" />
                <div>
                  <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                    Offline Production Draft Queue (IndexedDB)
                  </h3>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>
                    Durable local device storage • Idempotent reconciliation
                  </div>
                </div>
              </div>
              <button
                onClick={() => setShowDrawer(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Queue List Content */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div style={{ fontSize: "12px", color: "#475569" }}>
                  Status: <strong>{isOnline ? "Online (Connected)" : "Offline (Local Only)"}</strong> • Total Drafts: <strong>{draftsList.length}</strong>
                </div>
                {isOnline && draftsList.some((d) => d.status === "PENDING" || d.status === "REJECTED") && (
                  <button
                    onClick={triggerSync}
                    disabled={isSyncingNow}
                    className="pagination-btn"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      background: "#1E3A8A",
                      color: "#FFFFFF",
                      border: "none",
                      padding: "4px 12px"
                    }}
                  >
                    <Send size={12} />
                    <span>{isSyncingNow ? "Syncing..." : "Sync All Now"}</span>
                  </button>
                )}
              </div>

              {draftsList.length === 0 ? (
                <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
                  <CheckCircle2 size={32} color="#047857" style={{ margin: "0 auto 8px" }} />
                  <div style={{ fontWeight: "600", color: "#0F172A" }}>All batches synchronized</div>
                  <div style={{ fontSize: "12px", marginTop: "2px" }}>No pending or uncommitted offline drafts on this workstation.</div>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {draftsList.map((draft) => {
                    const isRejected = draft.status === "REJECTED" || draft.status === "CONFLICT";
                    const isDraftSyncing = draft.status === "SYNCING";

                    return (
                      <div
                        key={draft.idempotencyKey}
                        style={{
                          border: `1px solid ${isRejected ? "#FCA5A5" : "#CBD5E1"}`,
                          background: isRejected ? "#FEF2F2" : "#FFFFFF",
                          borderRadius: "4px",
                          padding: "12px"
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                              <span style={{ fontWeight: "700", fontSize: "13px", color: "#0F172A" }}>
                                {draft.modelName || `Product #${draft.productId}`}
                              </span>
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontWeight: "700",
                                  padding: "1px 6px",
                                  borderRadius: "3px",
                                  background: isRejected ? "#FEE2E2" : isDraftSyncing ? "#DBEAFE" : "#FEF3C7",
                                  color: isRejected ? "#B91C1C" : isDraftSyncing ? "#1E40AF" : "#92400E",
                                  border: `1px solid ${isRejected ? "#FCA5A5" : isDraftSyncing ? "#93C5FD" : "#FCD34D"}`
                                }}
                              >
                                {draft.status}
                              </span>
                            </div>
                            <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
                              Key: <code style={{ fontSize: "10.5px" }}>{draft.idempotencyKey.slice(0, 32)}...</code>
                              {" • "}
                              Device: {new Date(draft.createdAtDevice).toLocaleTimeString()}
                            </div>
                          </div>

                          <button
                            onClick={() => handleDeleteDraft(draft.idempotencyKey)}
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              color: "#94A3B8",
                              padding: "4px"
                            }}
                            title="Discard local draft"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>

                        {/* Size quantities summary */}
                        <div style={{ marginTop: "8px", fontSize: "12px", color: "#334155" }}>
                          Total Pairs: <strong>{draft.totalPairs}</strong>
                          {" • "}
                          Sizes: {Object.entries(draft.sizeQuantities || {})
                            .map(([sz, q]) => `${sz}:${q}`)
                            .join(", ")}
                        </div>

                        {/* Error reason if rejected */}
                        {draft.errorDetails && (
                          <div
                            style={{
                              marginTop: "8px",
                              padding: "6px 10px",
                              background: "#FFFFFF",
                              border: "1px solid #FCA5A5",
                              borderRadius: "3px",
                              fontSize: "11.5px",
                              color: "#B91C1C",
                              display: "flex",
                              alignItems: "center",
                              gap: "6px"
                            }}
                          >
                            <AlertTriangle size={13} />
                            <span>Server rejection reason: {draft.errorDetails}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="modal-footer" style={{ padding: "10px 16px" }}>
              <div style={{ fontSize: "11px", color: "#64748B" }}>
                Drafts are kept in browser storage until reconciled with master ERP server.
              </div>
              <button
                type="button"
                onClick={() => setShowDrawer(false)}
                className="pagination-btn"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
