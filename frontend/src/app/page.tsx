"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/AppShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { SkeletonLoader } from "@/components/SkeletonLoader";
import { Building2, Lock, UserCheck, ShieldAlert, Info, Shield, FileText } from "lucide-react";
import { LegalModal } from "@/components/LegalModal";
import { useLocale } from "@/context/LocaleContext";

// Dynamic Code-Splitting: Defer heavy views (e.g. recharts) until authenticated navigation
const DailyReportView = dynamic(
  () => import("@/components/DailyReportView").then((mod) => mod.DailyReportView),
  { loading: () => <SkeletonLoader title="Loading Daily Analytics..." type="dashboard" />, ssr: false }
);

const StockReportView = dynamic(
  () => import("@/components/StockReportView").then((mod) => mod.StockReportView),
  { loading: () => <SkeletonLoader title="Loading Stock Ledger..." type="dashboard" />, ssr: false }
);

const SalesInvoiceView = dynamic(
  () => import("@/components/SalesInvoiceView").then((mod) => mod.SalesInvoiceView),
  { loading: () => <SkeletonLoader title="Loading Sales & Invoicing..." type="table" />, ssr: false }
);

const ProductionView = dynamic(
  () => import("@/components/ProductionView").then((mod) => mod.ProductionView),
  { loading: () => <SkeletonLoader title="Loading Production Batches..." type="table" />, ssr: false }
);

const PurchaseView = dynamic(
  () => import("@/components/PurchaseView").then((mod) => mod.PurchaseView),
  { loading: () => <SkeletonLoader title="Loading Purchase & Materials..." type="table" />, ssr: false }
);

const SettingsView = dynamic(
  () => import("@/components/SettingsView").then((mod) => mod.SettingsView),
  { loading: () => <SkeletonLoader title="Loading System Settings..." type="form" />, ssr: false }
);

export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("daily");

  // Login form state
  const [username, setUsername] = useState("editor_admin");
  const [password, setPassword] = useState("LivoEditor2026!");
  const [loginError, setLoginError] = useState("");
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  const [legalModal, setLegalModal] = useState<"privacy" | "terms" | null>(null);

  useEffect(() => {
    checkUser();

    // Pre-warm Render backend directly from browser if NEXT_PUBLIC_API_URL is configured
    if (process.env.NEXT_PUBLIC_API_URL) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/health`, { mode: "cors" })
        .then(() => console.log("Backend warmed successfully"))
        .catch(() => console.log("Backend wake-up initiated"));
    }

    // Register service worker for offline read caching if available
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch((err) => console.log("SW register err:", err));
    }
  }, []);

  const checkUser = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/me");
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    setLoginSubmitting(true);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      } else if (res.status === 504 || res.status === 502) {
        setLoginError("Demo server is currently waking up from sleep (Render free tier requires ~45–50s on cold start). Please wait 20 seconds and click Sign In again.");
      } else {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        setLoginError(err.detail || "Invalid login credentials.");
      }
    } catch (e) {
      setLoginError("Demo server is currently waking up or unreachable. If sleeping, Render free-tier takes ~50s to start. Please retry in a few seconds.");
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await fetch("/api/v1/auth/logout", { method: "POST" });
    setUser(null);
  };

  const quickFillLogin = (role: "editor" | "viewer") => {
    if (role === "editor") {
      setUsername("editor_admin");
      setPassword("LivoEditor2026!");
    } else {
      setUsername("viewer_user");
      setPassword("LivoViewer2026!");
    }
  };

  const { locale, setLocale, t } = useLocale();

  if (loading) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0b1120", color: "#f8fafc" }} role="status" aria-live="polite">
        <div style={{ textAlign: "center" }}>
          <Building2 size={48} color="#3b82f6" style={{ marginBottom: "16px" }} />
          <h2 style={{ fontSize: "16px", fontWeight: "600" }}>Initializing LIVO ERP System...</h2>
        </div>
      </div>
    );
  }

  // Render Login Screen if unauthenticated
  if (!user) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#090d16", padding: "20px" }}>
        <div className="glass-card" style={{ width: "100%", maxWidth: "440px", padding: "36px", borderRadius: "8px", background: "#0f172a", border: "1px solid rgba(255, 255, 255, 0.12)", position: "relative" }}>
          
          {/* Bilingual Language Switcher (EN | नेपाली) */}
          <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px" }}>
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
                  padding: "3px 8px",
                  fontSize: "11px",
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
                  padding: "3px 8px",
                  fontSize: "11px",
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
          </div>

          <div style={{ textAlign: "center", marginBottom: "28px" }}>
            <div style={{ width: "52px", height: "52px", background: "rgba(59, 130, 246, 0.12)", border: "1px solid rgba(59, 130, 246, 0.3)", borderRadius: "8px", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: "12px" }}>
              <Building2 size={28} color="#3b82f6" />
            </div>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#f8fafc", letterSpacing: "0.02em" }}>{t("login_title")}</h1>
            <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>{t("login_subtitle")}</p>
          </div>

          {loginError && (
            <div
              role="alert"
              aria-live="polite"
              style={{ background: "rgba(244, 63, 94, 0.15)", border: "1px solid rgba(244, 63, 94, 0.3)", padding: "10px 14px", borderRadius: "6px", color: "#f87171", fontSize: "13px", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}
            >
              <ShieldAlert size={16} /> {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "6px" }}>{t("username")}</label>
              <input type="text" className="input-field" value={username} onChange={(e) => setUsername(e.target.value)} required aria-label={t("username")} />
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "6px" }}>{t("password")}</label>
              <input type="password" className="input-field" value={password} onChange={(e) => setPassword(e.target.value)} required aria-label={t("password")} />
            </div>

            <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "11px", marginTop: "8px", borderRadius: "6px" }} disabled={loginSubmitting}>
              <Lock size={16} /> {loginSubmitting ? "Authenticating..." : t("login_button")}
            </button>
          </form>

          {/* Role Fill Shortcuts */}
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid var(--border-color)", textAlign: "center" }}>
            <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "10px" }}>Role Access Preset:</div>
            <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
              <button className="btn-secondary" style={{ fontSize: "12px", padding: "6px 12px", borderRadius: "6px" }} onClick={() => quickFillLogin("editor")}>
                <UserCheck size={12} color="#34d399" /> Editor Admin
              </button>
              <button className="btn-secondary" style={{ fontSize: "12px", padding: "6px 12px", borderRadius: "6px" }} onClick={() => quickFillLogin("viewer")}>
                <UserCheck size={12} color="#60a5fa" /> Viewer Only
              </button>
            </div>
            <div style={{ marginTop: "16px", padding: "8px 12px", background: "rgba(15, 23, 42, 0.8)", border: "1px solid var(--border-subtle)", borderRadius: "6px", fontSize: "11px", color: "#94a3b8", textAlign: "left", display: "flex", alignItems: "flex-start", gap: "8px" }}>
              <Info size={14} color="#60a5fa" style={{ flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong>Infrastructure Notice:</strong> Cloud backend operates on standard container scaling. If sleeping after inactivity, initial connection takes ~45s.
              </div>
            </div>
          </div>
        </div>

        {/* Compliance & Legal Footer */}
        <div style={{ marginTop: "20px", textAlign: "center", fontSize: "12px", color: "#64748b", display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", gap: "16px", justifyContent: "center" }}>
            <button
              onClick={() => setLegalModal("privacy")}
              style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "12px", cursor: "pointer", textDecoration: "underline" }}
            >
              Privacy Policy
            </button>
            <span>•</span>
            <button
              onClick={() => setLegalModal("terms")}
              style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "12px", cursor: "pointer", textDecoration: "underline" }}
            >
              Terms & Conditions
            </button>
          </div>
          <div>© 2026 LIVO GROUP OF INDUSTRIES. All rights reserved.</div>
        </div>

        {legalModal && <LegalModal type={legalModal} onClose={() => setLegalModal(null)} />}
      </div>
    );
  }

  // Render Authenticated AppShell with screen-level ErrorBoundaries
  return (
    <AppShell activeTab={activeTab} setActiveTab={setActiveTab} user={user} onLogout={handleLogout}>
      {activeTab === "daily" && (
        <ErrorBoundary screenName="Daily Report">
          <DailyReportView />
        </ErrorBoundary>
      )}

      {activeTab === "stock" && (
        <ErrorBoundary screenName="Stock Ledger">
          <StockReportView />
        </ErrorBoundary>
      )}

      {/* NOTE: Tally Accounting tab removed from Phase 1 — archived in frontend/_unscoped/tally-export/ */}

      {activeTab === "sales" && (
        <ErrorBoundary screenName="Sales & Invoicing">
          <SalesInvoiceView userRole={user.role} />
        </ErrorBoundary>
      )}

      {activeTab === "production" && (
        <ErrorBoundary screenName="Production">
          <ProductionView userRole={user.role} />
        </ErrorBoundary>
      )}

      {activeTab === "purchase" && (
        <ErrorBoundary screenName="Purchase Raw Materials">
          <PurchaseView userRole={user.role} />
        </ErrorBoundary>
      )}

      {activeTab === "settings" && (
        <ErrorBoundary screenName="Settings & Diagnostics">
          <SettingsView />
        </ErrorBoundary>
      )}
    </AppShell>
  );
}
