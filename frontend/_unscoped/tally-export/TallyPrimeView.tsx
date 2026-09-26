"use client";

import React, { useState, useEffect } from "react";
import { BookOpen, Scale, TrendingUp, Users, Search, Calendar, FileCheck, ArrowRightLeft } from "lucide-react";

export function TallyPrimeView() {
  const [subTab, setSubTab] = useState<"daybook" | "trial" | "pl" | "outstanding">("daybook");
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [daybookData, setDaybookData] = useState<any>(null);
  const [trialData, setTrialData] = useState<any>(null);
  const [plData, setPlData] = useState<any>(null);
  const [outstandingData, setOutstandingData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetchActiveTabData();
  }, [subTab, selectedDate]);

  const fetchActiveTabData = async () => {
    setLoading(true);
    try {
      if (subTab === "daybook") {
        const res = await fetch(`/api/v1/tally/daybook?date_ad=${selectedDate}`);
        if (res.ok) setDaybookData(await res.json());
      } else if (subTab === "trial") {
        const res = await fetch("/api/v1/tally/trial-balance");
        if (res.ok) setTrialData(await res.json());
      } else if (subTab === "pl") {
        const res = await fetch("/api/v1/tally/profit-loss");
        if (res.ok) setPlData(await res.json());
      } else if (subTab === "outstanding") {
        const res = await fetch("/api/v1/tally/outstanding");
        if (res.ok) setOutstandingData(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Gateway of Tally Header Bar */}
      <div className="glass-card" style={{ padding: "20px", background: "linear-gradient(135deg, rgba(30,41,59,0.9) 0%, rgba(15,23,42,0.95) 100%)", borderColor: "rgba(59, 130, 246, 0.3)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px", marginBottom: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="badge badge-warning" style={{ fontWeight: "700" }}>TALLY PRIME ENGINE</span>
              <span style={{ fontSize: "12px", color: "#94a3b8" }}>Double-Entry Financial Suite</span>
            </div>
            <h2 style={{ fontSize: "22px", fontWeight: "700", marginTop: "4px", color: "#f8fafc" }}>
              Gateway of Tally — Financial Statements
            </h2>
          </div>

          {/* Alt+G Go To Search Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "rgba(15, 23, 42, 0.8)", padding: "8px 14px", borderRadius: "8px", border: "1px solid var(--border-color)", width: "280px" }}>
            <Search size={16} color="#fbbf24" />
            <input
              type="text"
              placeholder="Alt+G Go To (Ledger / Voucher)..."
              style={{ background: "none", border: "none", color: "#fff", outline: "none", fontSize: "13px", width: "100%" }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Tally Quick Nav Subtabs */}
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
          <button
            className={`btn-secondary ${subTab === "daybook" ? "btn-primary" : ""}`}
            style={{ padding: "8px 14px", fontSize: "13px" }}
            onClick={() => setSubTab("daybook")}
          >
            <BookOpen size={16} /> Day Book [D]
          </button>

          <button
            className={`btn-secondary ${subTab === "trial" ? "btn-primary" : ""}`}
            style={{ padding: "8px 14px", fontSize: "13px" }}
            onClick={() => setSubTab("trial")}
          >
            <Scale size={16} /> Trial Balance [T]
          </button>

          <button
            className={`btn-secondary ${subTab === "pl" ? "btn-primary" : ""}`}
            style={{ padding: "8px 14px", fontSize: "13px" }}
            onClick={() => setSubTab("pl")}
          >
            <TrendingUp size={16} /> Profit & Loss [P]
          </button>

          <button
            className={`btn-secondary ${subTab === "outstanding" ? "btn-primary" : ""}`}
            style={{ padding: "8px 14px", fontSize: "13px" }}
            onClick={() => setSubTab("outstanding")}
          >
            <Users size={16} /> Outstanding Debtors [O]
          </button>
        </div>
      </div>

      {/* 1. Tally Day Book View */}
      {subTab === "daybook" && (
        <div className="glass-card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
              <BookOpen size={18} color="#fbbf24" /> Tally Prime Day Book Transactions
            </h3>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Calendar size={16} color="#94a3b8" />
              <input
                type="date"
                className="input-field"
                style={{ width: "160px" }}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
            </div>
          </div>

          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>Loading Tally Day Book...</div>
          ) : !daybookData || daybookData.vouchers.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>No vouchers recorded for {selectedDate}.</div>
          ) : (
            <div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Voucher Type</th>
                    <th>Voucher No</th>
                    <th>Particulars (Account)</th>
                    <th style={{ textAlign: "right" }}>Debit Amount (Dr)</th>
                    <th style={{ textAlign: "right" }}>Credit Amount (Cr)</th>
                  </tr>
                </thead>
                <tbody>
                  {daybookData.vouchers.map((v: any) => (
                    <tr key={v.id}>
                      <td><span className="badge badge-info">{v.voucher_type}</span></td>
                      <td style={{ fontWeight: "700", color: "#3b82f6" }}>{v.voucher_number}</td>
                      <td style={{ fontWeight: "600" }}>{v.particulars}</td>
                      <td style={{ textAlign: "right", color: v.debit_amount > 0 ? "#34d399" : "#64748b", fontWeight: "600" }}>
                        {v.debit_amount > 0 ? `Rs. ${v.debit_amount.toLocaleString()}` : "-"}
                      </td>
                      <td style={{ textAlign: "right", color: v.credit_amount > 0 ? "#f43f5e" : "#64748b", fontWeight: "600" }}>
                        {v.credit_amount > 0 ? `Rs. ${v.credit_amount.toLocaleString()}` : "-"}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ background: "rgba(255, 255, 255, 0.05)", fontWeight: "700" }}>
                    <td colSpan={3} style={{ textAlign: "right" }}>Total Day Book Balance:</td>
                    <td style={{ textAlign: "right", color: "#34d399" }}>Rs. {daybookData.total_debit.toLocaleString()}</td>
                    <td style={{ textAlign: "right", color: "#f43f5e" }}>Rs. {daybookData.total_credit.toLocaleString()}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 2. Trial Balance View */}
      {subTab === "trial" && (
        <div className="glass-card" style={{ padding: "20px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
            <Scale size={18} color="#34d399" /> Tally Prime Trial Balance Summary
          </h3>

          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>Computing Trial Balance...</div>
          ) : trialData ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Account Group / Ledger</th>
                  <th style={{ textAlign: "right" }}>Debit (Dr)</th>
                  <th style={{ textAlign: "right" }}>Credit (Cr)</th>
                </tr>
              </thead>
              <tbody>
                {trialData.groups.map((g: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: "600" }}>{g.group}</td>
                    <td style={{ textAlign: "right", color: g.debit > 0 ? "#34d399" : "#64748b", fontWeight: "600" }}>
                      {g.debit > 0 ? `Rs. ${g.debit.toLocaleString()}` : "-"}
                    </td>
                    <td style={{ textAlign: "right", color: g.credit > 0 ? "#f43f5e" : "#64748b", fontWeight: "600" }}>
                      {g.credit > 0 ? `Rs. ${g.credit.toLocaleString()}` : "-"}
                    </td>
                  </tr>
                ))}
                <tr style={{ background: "rgba(59, 130, 246, 0.1)", fontWeight: "700", fontSize: "15px" }}>
                  <td>Grand Total:</td>
                  <td style={{ textAlign: "right", color: "#34d399" }}>Rs. {trialData.total_debit.toLocaleString()}</td>
                  <td style={{ textAlign: "right", color: "#f43f5e" }}>Rs. {trialData.total_credit.toLocaleString()}</td>
                </tr>
              </tbody>
            </table>
          ) : null}
        </div>
      )}

      {/* 3. Profit & Loss View */}
      {subTab === "pl" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "20px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
            <TrendingUp size={18} color="#60a5fa" /> Tally Prime Trading & Profit & Loss Statement
          </h3>

          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>Calculating Profit & Loss...</div>
          ) : plData ? (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
              <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "20px", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "13px", color: "#94a3b8" }}>GROSS SALES REVENUE</div>
                <div style={{ fontSize: "26px", fontWeight: "700", color: "#34d399", marginTop: "6px" }}>
                  Rs. {plData.trading_account.gross_sales_revenue.toLocaleString()}
                </div>
              </div>

              <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "20px", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "13px", color: "#94a3b8" }}>RAW MATERIAL PURCHASES</div>
                <div style={{ fontSize: "26px", fontWeight: "700", color: "#f87171", marginTop: "6px" }}>
                  Rs. {plData.trading_account.raw_material_purchases.toLocaleString()}
                </div>
              </div>

              <div style={{ background: "rgba(15, 23, 42, 0.6)", padding: "20px", borderRadius: "10px", border: "1px solid var(--border-color)" }}>
                <div style={{ fontSize: "13px", color: "#94a3b8" }}>NET GROSS PROFIT ({plData.trading_account.gross_profit_margin_pct}%)</div>
                <div style={{ fontSize: "26px", fontWeight: "700", color: "#fbbf24", marginTop: "6px" }}>
                  Rs. {plData.net_profit.toLocaleString()}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* 4. Outstanding Aging View */}
      {subTab === "outstanding" && (
        <div className="glass-card" style={{ padding: "20px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
            <Users size={18} color="#fbbf24" /> Sundry Debtors Outstanding Aging Report
          </h3>

          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>Loading Outstanding Balances...</div>
          ) : outstandingData ? (
            <div>
              <div style={{ marginBottom: "16px", fontSize: "14px", color: "#94a3b8" }}>
                Total Outstanding Receivables: <strong style={{ color: "#f87171", fontSize: "16px" }}>Rs. {outstandingData.total_outstanding_receivables.toLocaleString()}</strong>
              </div>

              <table className="data-table">
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Client Name</th>
                    <th>Contact Phone</th>
                    <th style={{ textAlign: "right" }}>Credit Limit</th>
                    <th style={{ textAlign: "right" }}>Outstanding Receivable</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {outstandingData.clients.map((c: any) => (
                    <tr key={c.client_id}>
                      <td style={{ fontWeight: "700", color: "#3b82f6" }}>{c.code}</td>
                      <td style={{ fontWeight: "600" }}>{c.name}</td>
                      <td>{c.contact}</td>
                      <td style={{ textAlign: "right" }}>Rs. {c.credit_limit.toLocaleString()}</td>
                      <td style={{ textAlign: "right", color: c.outstanding_receivable > 0 ? "#f87171" : "#34d399", fontWeight: "700" }}>
                        Rs. {c.outstanding_receivable.toLocaleString()}
                      </td>
                      <td>
                        <span className={`badge ${c.status === 'Overdue' ? 'badge-danger' : 'badge-success'}`}>
                          {c.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
