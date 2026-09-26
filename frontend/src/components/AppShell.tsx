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

interface AppShellProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  user: { name: string; username: string; role: string; company_id: number } | null;
  onLogout: () => void;
  children: React.ReactNode;
}

export function AppShell({ activeTab, setActiveTab, user, onLogout, children }: AppShellProps) {
  const [dbStatus, setDbStatus] = useState<string>("checking...");
  const [appVersion, setAppVersion] = useState<string>("1.0.0");
  const [mobileOpen, setMobileOpen] = useState(false);

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
    { id: "daily", label: "Daily Report", icon: BarChart3 },
    { id: "stock", label: "Stock Ledger", icon: Boxes },
    { id: "sales", label: "Sales & Invoices", icon: ShoppingBag },
    { id: "production", label: "Production", icon: Factory },
    { id: "purchase", label: "Purchase Raw Mat", icon: FileText },
    { id: "settings", label: "Settings & Diag", icon: SettingsIcon },
    // NOTE: Tally Accounting removed from Phase 1 nav — not client-requested.
    // Component archived at: frontend/_unscoped/tally-export/TallyPrimeView.tsx
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border-color)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Building2 size={24} color="#3b82f6" />
            <div>
              <div style={{ fontWeight: "700", fontSize: "16px", letterSpacing: "0.02em", color: "#f8fafc" }}>LIVO GROUP</div>
              <div style={{ fontSize: "11px", color: "#94a3b8" }}>Footwear ERP</div>
            </div>
          </div>
          <button onClick={() => setMobileOpen(false)} style={{ background: "none", border: "none", color: "#94a3b8", display: "none" }} className="mobile-close-btn">
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
                {user.role.toUpperCase()} ROLE
              </span>
            </div>
          </div>
        )}

        {/* Navigation items */}
        <nav style={{ flex: 1, padding: "16px 12px", display: "flex", flexDirection: "column", gap: "4px" }}>
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
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  border: "none",
                  background: isActive ? "linear-gradient(90deg, rgba(59, 130, 246, 0.2) 0%, rgba(59, 130, 246, 0.05) 100%)" : "transparent",
                  color: isActive ? "#3b82f6" : "#94a3b8",
                  fontWeight: isActive ? "600" : "400",
                  fontSize: "14px",
                  cursor: "pointer",
                  textAlign: "left",
                  transition: "all 0.2s"
                }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Footer: Version & DB Health Self-Check */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border-color)", fontSize: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ color: "#64748b" }}>DB Status:</span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px", color: dbStatus === "Healthy" ? "#34d399" : "#f43f5e", fontWeight: "600" }}>
              {dbStatus === "Healthy" ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
              {dbStatus}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: "#64748b" }}>
            <span>Version:</span>
            <span style={{ fontWeight: "600", color: "#94a3b8" }}>v{appVersion}</span>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="main-wrapper">
        <header className="app-header">
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button onClick={() => setMobileOpen(true)} className="mobile-menu-btn" style={{ background: "none", border: "none", color: "#f8fafc", cursor: "pointer" }}>
              <Menu size={24} />
            </button>
            <h1 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
              {navItems.find((n) => n.id === activeTab)?.label || "Dashboard"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <button onClick={onLogout} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "13px" }}>
              <LogOut size={14} /> Logout
            </button>
          </div>
        </header>

        <main style={{ padding: "24px", flex: 1, overflowY: "auto" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
