"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { DailyReportView } from "@/components/DailyReportView";
import { StockReportView } from "@/components/StockReportView";
// NOTE: TallyPrimeView removed from Phase 1 — not client-requested, not in scope.
// Archived at: frontend/_unscoped/tally-export/TallyPrimeView.tsx
import { PurchaseView } from "@/components/PurchaseView";
import { ProductionView } from "@/components/ProductionView";
import { SalesInvoiceView } from "@/components/SalesInvoiceView";
import { SettingsView } from "@/components/SettingsView";
import { Building2, Lock, UserCheck, ShieldAlert } from "lucide-react";

export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("daily");

  // Login form state
  const [username, setUsername] = useState("editor_admin");
  const [password, setPassword] = useState("LivoEditor2026!");
  const [loginError, setLoginError] = useState("");
  const [loginSubmitting, setLoginSubmitting] = useState(false);

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

  if (loading) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0f172a", color: "#f8fafc" }}>
        <div style={{ textAlign: "center" }}>
          <Building2 size={48} color="#3b82f6" style={{ marginBottom: "16px", animation: "pulse 1.5s infinite" }} />
          <h2 style={{ fontSize: "18px", fontWeight: "600" }}>Initializing LIVO ERP System...</h2>
        </div>
      </div>
    );
  }

  // Render Login Screen if unauthenticated
  if (!user) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "radial-gradient(circle at top right, #1e293b 0%, #0f172a 100%)", padding: "20px" }}>
        <div className="glass-card" style={{ width: "100%", maxWidth: "440px", padding: "36px", borderRadius: "16px" }}>
          <div style={{ textAlign: "center", marginBottom: "28px" }}>
            <div style={{ width: "56px", height: "56px", background: "rgba(59, 130, 246, 0.15)", borderRadius: "14px", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: "12px" }}>
              <Building2 size={32} color="#3b82f6" />
            </div>
            <h1 style={{ fontSize: "22px", fontWeight: "700", color: "#f8fafc" }}>LIVO GROUP OF INDUSTRIES</h1>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>Footwear Enterprise Resource Planning</p>
          </div>

          {loginError && (
            <div style={{ background: "rgba(244, 63, 94, 0.15)", border: "1px solid rgba(244, 63, 94, 0.3)", padding: "10px 14px", borderRadius: "8px", color: "#f87171", fontSize: "13px", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
              <ShieldAlert size={16} /> {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "6px" }}>Username</label>
              <input type="text" className="input-field" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", display: "block", marginBottom: "6px" }}>Password</label>
              <input type="password" className="input-field" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>

            <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", marginTop: "8px" }} disabled={loginSubmitting}>
              <Lock size={16} /> {loginSubmitting ? "Authenticating..." : "Sign In to ERP"}
            </button>
          </form>

          {/* Role Fill Shortcuts */}
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: "1px solid var(--border-color)", textAlign: "center" }}>
            <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "10px" }}>Demo Role Select:</div>
            <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
              <button className="btn-secondary" style={{ fontSize: "12px", padding: "6px 12px" }} onClick={() => quickFillLogin("editor")}>
                <UserCheck size={12} color="#34d399" /> Editor Admin
              </button>
              <button className="btn-secondary" style={{ fontSize: "12px", padding: "6px 12px" }} onClick={() => quickFillLogin("viewer")}>
                <UserCheck size={12} color="#60a5fa" /> Viewer Only
              </button>
            </div>
            <div style={{ marginTop: "16px", padding: "8px 12px", background: "rgba(59, 130, 246, 0.08)", borderRadius: "6px", fontSize: "11px", color: "#94a3b8", textAlign: "center" }}>
              💡 <strong>Free-Tier Demo Notice:</strong> Render backend spins down after 15m of inactivity. If cold, the first request takes ~45–50s to wake up.
            </div>
          </div>
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
