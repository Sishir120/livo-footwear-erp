"use client";

import React, { useState } from "react";
import { Building2, Lock, UserCheck, ShieldAlert, Info, Eye, EyeOff } from "lucide-react";
import { LegalModal } from "@/components/LegalModal";
import { useLocale } from "@/context/LocaleContext";

export default function LoginPage() {
  const [username, setUsername] = useState("admin_demo");
  const [password, setPassword] = useState("LivoAdmin2026!");
  const [showPassword, setShowPassword] = useState(false);
  const [clipboardNotice, setClipboardNotice] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  const [legalModal, setLegalModal] = useState<"privacy" | "terms" | null>(null);

  const { locale, setLocale, t } = useLocale();

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
        // Successful authentication -> navigate to root workspace
        window.location.href = "/";
      } else if (res.status === 504 || res.status === 502) {
        setLoginError("Demo server is currently waking up from sleep (Render free tier requires ~45–50s on cold start). Please wait 20 seconds and click Sign In again.");
      } else {
        const err = await res.json().catch(() => ({ detail: "Login failed" }));
        setLoginError(err.detail || "Invalid login credentials.");
      }
    } catch (e) {
      setLoginError("Demo server is currently waking up or unreachable. Please retry in a few moments.");
    } finally {
      setLoginSubmitting(false);
    }
  };

  const quickFillLogin = (role: "admin" | "viewer") => {
    if (role === "admin") {
      setUsername("admin_demo");
      setPassword("LivoAdmin2026!");
    } else {
      setUsername("viewer_demo");
      setPassword("LivoViewer2026!");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#F8FAFC", padding: "20px" }}>
      <div className="glass-card" style={{ width: "100%", maxWidth: "440px", padding: "36px", borderRadius: "4px", background: "#FFFFFF", border: "1px solid #CBD5E1", position: "relative" }}>
        
        {/* Bilingual Language Switcher (EN | नेपाली) */}
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "12px" }}>
          <div
            role="group"
            aria-label="Language selection / भाषा छनोट"
            style={{
              display: "inline-flex",
              background: "#F1F5F9",
              padding: "2px",
              borderRadius: "4px",
              border: "1px solid #CBD5E1"
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
        </div>

        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ width: "48px", height: "48px", background: "#EFF6FF", border: "1px solid #BFDBFE", borderRadius: "4px", display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: "12px" }}>
            <Building2 size={24} color="#1E3A8A" />
          </div>
          <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "0.01em" }}>{t("login_title")}</h1>
          <p style={{ fontSize: "12px", color: "#475569", marginTop: "4px" }}>{t("login_subtitle")}</p>
        </div>

        {loginError && (
          <div
            role="alert"
            aria-live="polite"
            style={{ background: "#FFF1F2", border: "1px solid #FECDD3", padding: "10px 14px", borderRadius: "4px", color: "#BE123C", fontSize: "12.5px", marginBottom: "18px", display: "flex", alignItems: "center", gap: "8px" }}
          >
            <ShieldAlert size={16} /> {loginError}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={{ fontSize: "12px", color: "#334155", fontWeight: "600", display: "block", marginBottom: "5px" }}>{t("username")}</label>
            <input type="text" className="input-field" value={username} onChange={(e) => setUsername(e.target.value)} required aria-label={t("username")} />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "5px" }}>
              <label style={{ fontSize: "12px", color: "#334155", fontWeight: "600" }}>{t("password")}</label>
              <span style={{ fontSize: "11px", color: "#64748B" }}>Protected Field</span>
            </div>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <input
                type={showPassword ? "text" : "password"}
                className="input-field"
                style={{ paddingRight: "42px" }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onCopy={(e) => {
                  e.preventDefault();
                  setClipboardNotice("Clipboard copying is disabled for password security.");
                  setTimeout(() => setClipboardNotice(""), 3500);
                }}
                onCut={(e) => {
                  e.preventDefault();
                  setClipboardNotice("Clipboard cutting is disabled for password security.");
                  setTimeout(() => setClipboardNotice(""), 3500);
                }}
                onPaste={(e) => {
                  e.preventDefault();
                  setClipboardNotice("Direct paste is disabled for credential protection. Please type or use Presets.");
                  setTimeout(() => setClipboardNotice(""), 3500);
                }}
                autoComplete="current-password"
                required
                aria-label={t("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
                style={{
                  position: "absolute",
                  right: "6px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  padding: "6px",
                  color: "#64748B",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  borderRadius: "4px"
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {clipboardNotice && (
              <div style={{ fontSize: "11px", color: "#B45309", marginTop: "4px", display: "flex", alignItems: "center", gap: "5px", background: "#FEF3C7", padding: "4px 8px", borderRadius: "3px" }}>
                <ShieldAlert size={12} color="#B45309" /> {clipboardNotice}
              </div>
            )}
          </div>

          <button type="submit" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "10px", marginTop: "6px" }} disabled={loginSubmitting}>
            <Lock size={15} /> {loginSubmitting ? "Authenticating..." : t("login_button")}
          </button>
        </form>

        {/* Role Fill Shortcuts */}
        <div style={{ marginTop: "20px", paddingTop: "18px", borderTop: "1px solid #CBD5E1", textAlign: "center" }}>
          <div style={{ fontSize: "11.5px", color: "#475569", marginBottom: "8px" }}>Role Access Preset:</div>
          <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
            <button type="button" className="btn-secondary" style={{ fontSize: "12px", padding: "5px 12px" }} onClick={() => quickFillLogin("admin")}>
              <UserCheck size={12} color="#047857" /> Admin Operator
            </button>
            <button type="button" className="btn-secondary" style={{ fontSize: "12px", padding: "5px 12px" }} onClick={() => quickFillLogin("viewer")}>
              <UserCheck size={12} color="#1E40AF" /> Auditor Viewer
            </button>
          </div>
          <div style={{ marginTop: "14px", padding: "8px 12px", background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "11px", color: "#475569", textAlign: "left", display: "flex", alignItems: "flex-start", gap: "8px" }}>
            <Info size={14} color="#1E40AF" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong>Infrastructure Notice:</strong> Cloud backend operates on standard container scaling. If sleeping after inactivity, initial connection takes ~45s.
            </div>
          </div>
        </div>
      </div>

      {/* Compliance & Legal Footer */}
      <div style={{ marginTop: "16px", textAlign: "center", fontSize: "12px", color: "#64748B", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ display: "flex", gap: "16px", justifyContent: "center" }}>
          <button
            onClick={() => setLegalModal("privacy")}
            style={{ background: "none", border: "none", color: "#475569", fontSize: "12px", cursor: "pointer", textDecoration: "underline" }}
          >
            Privacy Policy
          </button>
          <span>•</span>
          <button
            onClick={() => setLegalModal("terms")}
            style={{ background: "none", border: "none", color: "#475569", fontSize: "12px", cursor: "pointer", textDecoration: "underline" }}
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
