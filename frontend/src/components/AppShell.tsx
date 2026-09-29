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
        <div style={{ padding: "18px 20px", borderBottom: "1px solid var(--border-color)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Building2 size={24} color="#1E3A8A" />
            <div>
              <div style={{ fontWeight: "700", fontSize: "15px", letterSpacing: "0.02em", color: "#0F172A" }}>LIVO GROUP</div>
              <div style={{ fontSize: "11px", color: "#64748B" }}>Footwear ERP</div>
            </div>
          </div>
          <button onClick={() => setMobileOpen(false)} style={{ background: "none", border: "none", color: "#475569", display: "none" }} className="mobile-close-btn" aria-label="Close navigation menu">
            <X size={20} />
          </button>
        </div>

        {/* User Role Badge */}
        {user && (
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border-color)", background: "#F8FAFC" }}>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "#0F172A" }}>{user.name}</div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
              <span className={`badge ${user.role === "editor" ? "badge-success" : "badge-info"}`}>
                <UserCheck size={12} style={{ marginRight: "4px" }} />
                {user.role === "editor" ? t("role_editor") : t("role_viewer")}
              </span>
            </div>
          </div>
        )}

        {/* Navigation items */}
        <nav style={{ flex: 1, padding: "14px 10px", display: "flex", flexDirection: "column", gap: "3px" }} aria-label="Sidebar Menu">
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
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "4px",
                  border: "none",
                  borderLeft: isActive ? "3px solid #1E3A8A" : "3px solid transparent",
                  background: isActive ? "#EFF6FF" : "transparent",
                  color: isActive ? "#1E3A8A" : "#475569",
                  fontWeight: isActive ? "600" : "500",
                  fontSize: "13px",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.12s ease"
                }}
              >
                <Icon size={17} color={isActive ? "#1E3A8A" : "#64748B"} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Footer: Version & DB Health Self-Check & Legal Compliance */}
        <div style={{ padding: "14px 18px", borderTop: "1px solid var(--border-color)", fontSize: "11.5px", background: "#F8FAFC" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
            <span style={{ color: "#64748B" }}>DB Status:</span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px", color: dbStatus === "Healthy" ? "#047857" : "#BE123C", fontWeight: "600" }}>
              {dbStatus === "Healthy" ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
              {dbStatus}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "#64748B", marginBottom: "8px" }}>
            <span>Version:</span>
            <span style={{ fontWeight: "600", color: "#334155" }}>v{appVersion}</span>
          </div>

          <div style={{ paddingTop: "6px", borderTop: "1px solid var(--border-subtle)", display: "flex", gap: "8px", fontSize: "11px", color: "#64748B", justifyContent: "center" }}>
            <button onClick={() => setLegalModal("privacy")} style={{ background: "none", border: "none", color: "#475569", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}>
              Privacy Policy
            </button>
            <span>•</span>
            <button onClick={() => setLegalModal("terms")} style={{ background: "none", border: "none", color: "#475569", fontSize: "11px", cursor: "pointer", textDecoration: "underline" }}>
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
            <button onClick={() => setMobileOpen(true)} className="mobile-menu-btn" style={{ background: "none", border: "none", color: "#0F172A", cursor: "pointer" }} aria-label="Open mobile navigation menu">
              <Menu size={22} />
            </button>
            <h1 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A" }}>
              {navItems.find((n) => n.id === activeTab)?.label || "Dashboard"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {/* Offline Outbox Status Badge */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              {!isOnline ? (
                <span className="badge badge-warning">
                  Offline ({queuedCount} queued)
                </span>
              ) : queuedCount > 0 ? (
                <button
                  type="button"
                  onClick={() => {
                    setIsSyncing(true);
                    replayQueue().finally(() => setIsSyncing(false));
                  }}
                  disabled={isSyncing}
                  className="badge badge-info"
                  style={{ cursor: "pointer" }}
                >
                  {isSyncing ? "Syncing..." : `Sync (${queuedCount})`}
                </button>
              ) : (
                <span className="badge badge-success">
                  ● Live
                </span>
              )}
            </div>

            {/* Bilingual Language Switcher (EN | नेपाली) */}
            <div
              role="group"
              aria-label="Language selection / भाषा छनोट"
              style={{
                display: "inline-flex",
                background: "#F1F5F9",
                padding: "2px",
                borderRadius: "4px",
                border: "1px solid var(--border-color)"
              }}
            >
              <button
                type="button"
                onClick={() => setLocale("en")}
                aria-label="Switch to English"
                style={{
                  padding: "4px 10px",
                  fontSize: "11px",
                  fontWeight: "600",
                  borderRadius: "3px",
                  border: "none",
                  cursor: "pointer",
                  background: locale === "en" ? "#1E3A8A" : "transparent",
                  color: locale === "en" ? "#FFFFFF" : "#475569",
                  transition: "all 0.12s ease"
                }}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLocale("ne")}
                aria-label="नेपाली भाषामा बदल्नुहोस्"
                style={{
                  padding: "4px 10px",
                  fontSize: "11px",
                  fontWeight: "600",
                  borderRadius: "3px",
                  border: "none",
                  cursor: "pointer",
                  background: locale === "ne" ? "#1E3A8A" : "transparent",
                  color: locale === "ne" ? "#FFFFFF" : "#475569",
                  transition: "all 0.12s ease"
                }}
              >
                नेपाली
              </button>
            </div>

            <button onClick={onLogout} className="btn-secondary" style={{ padding: "5px 10px", fontSize: "12px" }} aria-label={t("logout")}>
              <LogOut size={13} /> {t("logout")}
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
