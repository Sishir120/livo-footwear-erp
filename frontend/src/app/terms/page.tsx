import React from "react";
import Link from "next/link";
import { FileText, ArrowLeft } from "lucide-react";

export const metadata = {
  title: "Terms & Conditions | LIVO GROUP OF INDUSTRIES ERP",
  description: "Enterprise Terms & Conditions for LIVO Footwear ERP"
};

export default function TermsPage() {
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
            <div style={{ padding: "10px", background: "rgba(16, 185, 129, 0.15)", borderRadius: "8px" }}>
              <FileText size={24} color="#10b981" />
            </div>
            <div>
              <h1 style={{ fontSize: "22px", fontWeight: "700" }}>Terms & Conditions of ERP Usage</h1>
              <p style={{ fontSize: "12px", color: "#94a3b8" }}>LIVO GROUP OF INDUSTRIES • Operational Guidelines</p>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "18px", fontSize: "14px", lineHeight: "1.6", color: "#cbd5e1" }}>
            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                1. System Authorization & Account Responsibility
              </h2>
              <p>
                Access to this ERP system is strictly limited to authorized factory personnel and administrative officers
                of LIVO GROUP OF INDUSTRIES. Users are responsible for maintaining confidentiality of credentials.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                2. Append-Only Inventory Invariants
              </h2>
              <p>
                All finished footwear pairs and raw material stock quantities are strictly derived from append-only
                movement registers. Manual direct balance overwrites are prevented at database level to guarantee complete
                traceability of manufacturing yields and material scrap rates.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                3. Sequential Tax Invoice Compliance
              </h2>
              <p>
                Invoices generated in the sales module follow non-resettable, gapless sequence numbers enforced by
                PostgreSQL unique constraints. Alteration or deletion of issued tax invoices is prohibited.
              </p>
            </section>

            <section>
              <h2 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", marginBottom: "6px" }}>
                4. Data Confidentiality & Proprietary Sizing Models
              </h2>
              <p>
                Product codes, Paris Point size distribution curves, dealer discount agreements, and vendor pricing are
                confidential trade assets of LIVO GROUP OF INDUSTRIES.
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
