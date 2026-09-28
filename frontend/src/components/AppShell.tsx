"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  BarChart3,
  Boxes,
  ShoppingBag,
  Factory,
  FileText,
  Settings as SettingsIcon,
  LogOut,
  Menu,
  X,
  CheckCircle2,
  AlertCircle,
  UserCheck
} from "lucide-react";

import { LegalModal } from "./LegalModal";
import { useLocale } from "../context/LocaleContext";
import { subscribeQueueChange, replayQueue } from "../lib/offlineQueue";

interface AppShellProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: { name: string; username: string; role: string; company_id: number } | null;
  onLogout: () => void;
  children: React.ReactNode;
}

export function AppShell({ activeTab, setActiveTab, user, onLogout, children }: AppShellProps) {
  const { locale, setLocale, t } = useLocale();
  const [dbStatus, setDbStatus] = useState<string>("checking...");
  const [appVersion, setAppVersion] = useState<string>("1.0.0");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [legalModal, setLegalModal] = useState<"privacy" | "terms" | null>(null);

  // Offline outbox queue state
  const [isOnline, setIsOnline] = useState(true);
  const [queuedCount, setQueuedCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    setIsOnline(typeof navigator !== "undefined" ? navigator.onLine : true);

    const handleOnline = () => {
      setIsOnline(true);
      setIsSyncing(true);
      replayQueue().finally(() => setIsSyncing(false));
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    const unsubscribe = subscribeQueueChange((count) => {
      setQueuedCount(count);
    });

    const handleToast = (e: any) => {
      if (e.detail?.message) {
        setToastMessage(e.detail.message);
        setTimeout(() => setToastMessage(null), 4000);
      }
    };
    window.addEventListener("livo:toast", handleToast);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("livo:toast", handleToast);
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    fetch("/api/v1/health")
      .then((res) => res.json())
      .then((data) => {
        setDbStatus(data.database === "healthy" ? "Healthy" : data.database);
        setAppVersion(data.version || "1.0.0");
      })
      .catch(() => setDbStatus("Disconnected"));
  }, []);

  const navItems = [
    { id: "daily", label: t("dashboard"), icon: BarChart3 },
    { id: "stock", label: t("stock_ledger"), icon: Boxes },
    { id: "sales", label: t("sales_invoicing"), icon: ShoppingBag },
    { id: "production", label: t("production_batches"), icon: Factory },
    { id: "purchase", label: t("purchase_raw_materials"), icon: FileText },
    { id: "settings", label: t("settings_backups"), icon: SettingsIcon },
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`} aria-label="Main Navigation">
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Building2 size={24} color="#3b82f6" />
            <div>
              <div style={{ fontWeight: "700", fontSize: "16px", letterSpacing: "0.02em", color: "#f8fafc" }}>LIVO GROUP</div>
              <div style={{ fontSize: "11px", color: "#94a3b8" }}>Footwear ERP</div>
            </div>
          </div>
          <button onClick={() => setMobileOpen(false)} style={{ background: "none", border: "none", color: "#94a3b8", display: "none" }} className="mobile-close-btn" aria-label="Close navigation menu">
            <X size={20} />
          </button>
        </div>

        {/* User Role Badge */}
        {user && (
          <div style={{ padding: "16px 24px", borderBottom: "1px solid var(--border-color)", background: "rgba(255, 255, 255, 0.02)" }}>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "#f8fafc" }}>{user.name}</div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
              <span className={`badge ${user.role === "editor" ? "badge-success" : "badge-info"}`}>
                <UserCheck size={12} style={{ marginRight: "4px" }} />
                {user.role === "editor" ? t("role_editor") : t("role_viewer")}
              </span>
            </div>
          </div>
        )}

        {/* Navigation items */}
        <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: "4px" }} aria-label="Sidebar Menu">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setMobileOpen(false);
                }}
                aria-current={isActive ? "page" : undefined}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  border: "none",
                  borderLeft: isActive ? "3px solid #3b82f6" : "3px solid transparent",
                  background: isActive ? "rgba(59, 130, 246, 0.16)" : "transparent",
                  color: isActive ? "#60a5fa" : "#94a3b8",
                  fontWeight: isActive ? "600" : "400",
                  fontSize: "13.5px",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.15s ease"
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Footer: Version & DB Health Self-Check & Legal Compliance */}
        <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border-color)", fontSize: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ color: "#64748b" }}>DB Status:</span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px", color: dbStatus === "Healthy" ? "#34d399" : "#f43f5e", fontWeight: "600" }}>
              {dbStatus === "Healthy" ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
              {dbStatus}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "#64748b", marginBottom: "10px" }}>
            <span>Version:</span>
            <span style={{ fontWeight: "600", color: "#94a3b8" }}>v{appVersion}</span>
          </div>

          <div style={{ paddingTop: "8px", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "8px", fontSize: "11px", color: "#64748b", justifyContent: "center" }}>
            <button onClick={() => setLegalModal("privacy")} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}>
              Privacy Policy
            </button>
            <span>•</span>
            <button onClick={() => setLegalModal("terms")} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}>
              Terms & Conditions
            </button>
          </div>
        </div>

        {legalModal && <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />}
      </aside>

      {/* Main Container */}
      <div className="main-wrapper">
        <header className="app-header">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button onClick={() => setMobileOpen(true)} className="mobile-menu-btn" style={{ background: "none", border: "none", color: "#f8fafc", cursor: "pointer" }} aria-label="Open mobile navigation menu">
              <Menu size={24} />
            </button>
            <h1 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
              {navItems.find((n) => n.id === activeTab)?.label || "Dashboard"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
            {/* Offline Outbox Status Badge */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {!isOnline ? (
                <span
                  style={{
                    background: "rgba(234, 179, 8, 0.2)",
                    color: "#fde047",
                    border: "1px solid rgba(234, 179, 8, 0.4)",
                    padding: "4px 8px",
                    fontSize: "11px",
                    fontWeight: "600",
                    borderRadius: "4px"
                  }}
                >
                  🟡 Offline ({queuedCount} queued)
                </span>
              ) : queuedCount > 0 ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsSyncing(true);
                    replayQueue().finally(() => setIsSyncing(false));
                  }}
                  disabled={isSyncing}
                  style={{
                    background: "rgba(59, 130, 246, 0.2)",
                    color: "#93c5fd",
                    border: "1px solid rgba(59, 130, 246, 0.4)",
                    padding: "4px 8px",
                    fontSize: "11px",
                    fontWeight: "600",
                    borderRadius: "4px",
                    cursor: "pointer"
                  }}
                >
                  {isSyncing ? "🔄 Syncing..." : `🔄 Sync (${queuedCount})`}
                </button>
              ) : (
                <span
                  style={{
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#34d399",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    padding: "4px 8px",
                    fontSize: "11px",
                    fontWeight: "600",
                    borderRadius: "4px"
                  }}
                >
                  🟢 Live
                </span>
              )}
            </div>

            {/* Bilingual Language Switcher (EN | नेपाली) */}
            <div
              role="group"
              aria-label="Language selection / भाषा छनोट"
              style={{
                display: "inline-flex",
                background: "rgba(15, 23, 42, 0.8)",
                padding: "3px",
                borderRadius: "6px",
                border: "1px solid rgba(255, 255, 255, 0.12)"
              }}
            >
              <button
                type="button"
                onClick={() => setLocale("en")}
                aria-label="Switch to English"
                style={{
                  padding: "8px 14px",
                  fontSize: "12px",
                  fontWeight: "600",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  background: locale === "en" ? "#2563eb" : "transparent",
                  color: locale === "en" ? "#ffffff" : "#94a3b8",
                  transition: "all 0.15s ease"
                }}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLocale("ne")}
                aria-label="नेपाली भाषामा बदल्नुहोस्"
                style={{
                  padding: "8px 14px",
                  fontSize: "12px",
                  fontWeight: "600",
                  borderRadius: "4px",
                  border: "none",
                  cursor: "pointer",
                  background: locale === "ne" ? "#2563eb" : "transparent",
                  color: locale === "ne" ? "#ffffff" : "#94a3b8",
                  transition: "all 0.15s ease"
                }}
              >
                नेपाली
              </button>
            </div>

            <button onClick={onLogout} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "13px" }} aria-label={t("logout")}>
              <LogOut size={14} /> {t("logout")}
            </button>
          </div>
        </header>

        {/* Global Toast Notification */}
        {toastMessage && (
          <div
            role="status"
            aria-live="polite"
            style={{
              position: "fixed",
              top: "60px",
              right: "24px",
              zIndex: 9999,
              background: "#0f172a",
              color: "#fde047",
              border: "1px solid #ca8a04",
              borderRadius: "6px",
              padding: "10px 16px",
              boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
              fontSize: "13px",
              fontWeight: "600",
              display: "flex",
              alignItems: "center",
              gap: "8px"
            }}
          >
            <span>⚠️ {toastMessage}</span>
          </div>
        )}

        <main style={{ padding: "24px", flex: 1, overflowY: "auto" }} id="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
