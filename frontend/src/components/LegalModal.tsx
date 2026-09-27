"use client";

import React from "react";
import { Shield, FileText, X } from "lucide-react";

interface LegalModalProps {
  type: "privacy" | "terms" | null;
  onClose: () => void;
}

export function LegalModal({ type, onClose }: LegalModalProps) {
  if (!type) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.8)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 200,
        padding: "20px"
      }}
    >
      <div
        className="glass-card"
        style={{
          width: "100%",
          maxWidth: "680px",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          background: "#0d1527",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          borderRadius: "8px",
          overflow: "hidden"
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid var(--border-color)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            {type === "privacy" ? (
              <Shield size={20} color="#3b82f6" />
            ) : (
              <FileText size={20} color="#10b981" />
            )}
            <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#f8fafc" }}>
              {type === "privacy" ? "Corporate Privacy Policy" : "Terms & Conditions of ERP Usage"}
            </h3>
          </div>
          <button
            onClick={onClose}
            style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", padding: "4px" }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: "20px", overflowY: "auto", fontSize: "13px", lineHeight: "1.6", color: "#cbd5e1" }}>
          {type === "privacy" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  1. Internal Industrial Application Scope
                </h4>
                <p>
                  This Enterprise Resource Planning (ERP) platform is proprietary software deployed exclusively for
                  authorized personnel of LIVO GROUP OF INDUSTRIES. It is an internal operational system; personal user
                  data is restricted to identity authentication and organizational role management.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  2. Tenant Isolation & Cryptographic Partitioning
                </h4>
                <p>
                  All database records are logically partitioned by company identifier (<code>company_id</code>). Multi-tenant
                  query wrappers enforce strict boundary isolation across all relational queries, preventing unauthorized
                  inter-company data leakage or unauthorized cross-facility access.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  3. Audit Logging & Access Traceability
                </h4>
                <p>
                  Every state-changing transaction (inward purchase, finished production batch, sales invoice dispatch, or
                  void authorization) records an immutable audit trail capturing user ID, timestamp (UTC), endpoint URI,
                  and client network IP address for statutory compliance and internal quality assurance.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  4. Credential Security & Cookies
                </h4>
                <p>
                  User passwords are cryptographically hashed using modern Argon2id algorithms. Authentication tokens
                  (JWT) are transmitted exclusively via encrypted HTTP-only, secure, SameSite cookies to protect against
                  cross-site scripting (XSS) and unauthorized token extraction.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  5. No Third-Party Telemetry or Ad Tracking
                </h4>
                <p>
                  LIVO ERP contains zero third-party advertising trackers, external analytics beacons, or behavioral
                  profiling SDKs. All operational metrics belong strictly to LIVO GROUP OF INDUSTRIES.
                </p>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  1. Authorized Industrial Use
                </h4>
                <p>
                  Access to this ERP system is granted exclusively to active employees, facility supervisors, and executive
                  management of LIVO GROUP OF INDUSTRIES. Sharing operational credentials, automated scraping, or
                  unauthorized extraction of footwear bills of materials (BOM) is strictly prohibited.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  2. Immutable Double-Entry Ledger Principles
                </h4>
                <p>
                  In accordance with manufacturing auditing standards, raw material and finished goods stock balances
                  cannot be directly modified or overwritten. All physical quantity updates must occur through validated,
                  sequential stock movements (+IN from production or purchases; -OUT from verified sales dispatches).
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  3. Sequential Tax Invoice Integrity
                </h4>
                <p>
                  Invoices issued within this system utilize strict, sequential, gapless sequence numbers enforced by
                  database unique constraints. Invoices once recorded cannot be deleted; disputed or returned orders must
                  be handled through official void state workflows with recorded administrative justification.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  4. Commercial Confidentiality
                </h4>
                <p>
                  All wholesale rates, distributor pricing agreements, PAN registration numbers, supplier contracts,
                  and raw material inventory valuations constitute trade secrets of LIVO GROUP OF INDUSTRIES.
                </p>
              </div>

              <div>
                <h4 style={{ color: "#f8fafc", fontWeight: "600", marginBottom: "4px" }}>
                  5. System Administration & Backup Retention
                </h4>
                <p>
                  System administrators perform scheduled daily encrypted database snapshots. Factory users are
                  responsible for verifying batch counts and invoice summaries before closing daily production registers.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "12px 20px",
            borderTop: "1px solid var(--border-color)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "#090d16"
          }}
        >
          <span style={{ fontSize: "11px", color: "#64748b" }}>
            LIVO GROUP OF INDUSTRIES — Corporate Governance & IT Policy
          </span>
          <button type="button" className="btn-secondary" style={{ padding: "6px 14px", fontSize: "12px" }} onClick={onClose}>
            Acknowledge & Close
          </button>
        </div>
      </div>
    </div>
  );
}
