import React from "react";
import Link from "next/link";
import { Shield, ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Privacy Policy | LIVO GROUP OF INDUSTRIES ERP",
  description: "Corporate Privacy Policy for LIVO Footwear ERP"
};

export default function PrivacyPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0b1120", color: "#f8fafc", padding: "40px 20px" }}>
      <div style={{ maxWidth: "760px", margin: "0 auto" }}>
        <Link
          href="/"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            color: "#3b82f6",
            fontSize: "13px",
            textDecoration: "none",
            marginBottom: "24px"
          }}
        >
          <ArrowLeft size={16} /> Return to LIVO ERP Sign In
        </Link>

        <div className="glass-card" style={{ padding: "32px", background: "#0f172a", borderRadius: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "20px" }}>
            <div style={{ padding: "10px", background: "rgba(59, 130, 246, 0.15)", borderRadius: "8px" }}>
              <Shield size={24} color="#3b82f6" />
            </div>
            <div>
              <h1 style={{ fontSize: "22px", fontWeight: "700" }}>Corporate Privacy Policy</h1>
              <p style={{ fontSize: "12px", color: "#94a3b8" }}>LIVO GROUP OF INDUSTRIES • Footwear ERP Platform</p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "18px", fontSize: "14px", lineHeight: "1.6", color: "#cbd5e1" }}>
            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                1. System Scope & Identity Management
              </h2>
              <p>
                This Enterprise Resource Planning application is deployed strictly for internal manufacturing,
                inventory tracking, and sales invoicing operations of LIVO GROUP OF INDUSTRIES. Collected personal
                identifiable information is limited to employee usernames, encrypted passwords, roles, and administrative
                activity logs necessary for system security.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                2. Multi-Tenant Cryptographic Isolation
              </h2>
              <p>
                All company operational data is partitioned logically using relational <code>company_id</code> tenant
                wrappers. Strict tenant boundaries are enforced at the database repository tier to prevent accidental
                data exposure across production facilities.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                3. Immutable Operational Audit Logging
              </h2>
              <p>
                In compliance with industrial bookkeeping regulations, write transactions create non-deletable audit
                log entries capturing client IP, timestamp, user account identity, and changed ledger parameters.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                4. Session Security & Cookie Usage
              </h2>
              <p>
                JSON Web Tokens (JWT) are stored and transmitted exclusively via encrypted <code>httpOnly</code>,
                <code>Secure</code>, and <code>SameSite=Lax</code> session cookies. LocalStorage is not used for credential
                persistence.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
