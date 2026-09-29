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

const PartyAgingView = dynamic(
  () => import("@/components/PartyAgingView").then((mod) => mod.PartyAgingView),
  { loading: () => <SkeletonLoader title="Loading Accounts Receivable Aging..." type="table" />, ssr: false }
);

const ProductionView = dynamic(
  () => import("@/components/ProductionView").then((mod) => mod.ProductionView),
  { loading: () => <SkeletonLoader title="Loading Production Batches..." type="table" />, ssr: false }
);

const PurchaseView = dynamic(
  () => import("@/components/PurchaseView").then((mod) => mod.PurchaseView),
  { loading: () => <SkeletonLoader title="Loading Purchase & Materials..." type="table" />, ssr: false }
);

const HRManagementView = dynamic(
  () => import("@/components/HRManagementView").then((mod) => mod.HRManagementView),
  { loading: () => <SkeletonLoader title="Loading HR & Worker Ledger..." type="table" />, ssr: false }
);

const SettingsView = dynamic(
  () => import("@/components/SettingsView").then((mod) => mod.SettingsView),
  { loading: () => <SkeletonLoader title="Loading System Settings..." type="form" />, ssr: false }
);

const OpsCockpitView = dynamic(
  () => import("@/components/OpsCockpitView").then((mod) => mod.OpsCockpitView),
  { loading: () => <SkeletonLoader title="Loading Ops Cockpit..." type="dashboard" />, ssr: false }
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
        window.location.href = "/login";
      }
    } catch (e) {
      setUser(null);
      window.location.href = "/login";
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      window.location.href = "/login";
    }
  };

  if (loading || !user) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#F8FAFC", color: "#0F172A" }} role="status" aria-live="polite">
        <div style={{ textAlign: "center" }}>
          <Building2 size={48} color="#1E3A8A" style={{ margin: "0 auto 16px" }} />
          <h2 style={{ fontSize: "16px", fontWeight: "700" }}>Initializing LIVO Industrial ERP...</h2>
          <p style={{ fontSize: "12px", color: "#475569", marginTop: "4px" }}>Verifying session security credentials...</p>
        </div>
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
          <StockReportView userRole={user.role} />
        </ErrorBoundary>
      )}

      {/* NOTE: Tally Accounting tab removed from Phase 1 — archived in frontend/_unscoped/tally-export/ */}

      {activeTab === "sales" && (
        <ErrorBoundary screenName="Sales & Invoicing">
          <SalesInvoiceView userRole={user.role} />
        </ErrorBoundary>
      )}

      {activeTab === "receivables" && (
        <ErrorBoundary screenName="Accounts Receivable Aging">
          <PartyAgingView userRole={user.role} />
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

      {activeTab === "hr" && (
        <ErrorBoundary screenName="HR & Workers">
          <HRManagementView userRole={user.role} />
        </ErrorBoundary>
      )}

      {activeTab === "ops_cockpit" && user?.role === "admin" && (
        <ErrorBoundary screenName="Ops Cockpit">
          <OpsCockpitView />
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
