"use client";

import React, { useState, useEffect } from "react";
import {
  Calendar,
  Search,
  Filter,
  RefreshCw,
  Plus,
  FileText,
  AlertTriangle,
  AlertCircle,
  CreditCard,
  Building,
  TrendingDown,
  DollarSign,
  Download,
  CheckCircle2,
  X
} from "lucide-react";
import { fromPaisa, toPaisa } from "@/lib/currency";
import { PartyStatementModal } from "./PartyStatementModal";
import { useLocale } from "@/context/LocaleContext";

interface PartyAgingViewProps {
  userRole: string;
}

interface AgingParty {
  client_id: number;
  client_code: string;
  client_name: string;
  pan_number: string;
  contact_person: string;
  phone: string;
  credit_limit_paisa: number;
  current_paisa: number;
  days_31_60_paisa: number;
  days_61_90_paisa: number;
  over_90_paisa: number;
  total_due_paisa: number;
  unallocated_credit_paisa: number;
  credit_limit_exceeded: boolean;
  active_invoice_count: number;
}

interface AgingSummary {
  current_paisa: number;
  days_31_60_paisa: number;
  days_61_90_paisa: number;
  over_90_paisa: number;
  total_due_paisa: number;
  unallocated_credit_paisa: number;
}

interface UnpaidInvoice {
  invoice_id: number;
  invoice_number: string;
  invoice_date: string;
  due_date: string | null;
  total_paisa: number;
  allocated_paisa: number;
  remaining_paisa: number;
}

export function PartyAgingView({ userRole }: PartyAgingViewProps) {
  const { isNepali } = useLocale();
  const [loading, setLoading] = useState(true);
  const [asOfDate, setAsOfDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [parties, setParties] = useState<AgingParty[]>([]);
  const [summary, setSummary] = useState<AgingSummary | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Record Payment Modal State
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [payClientId, setPayClientId] = useState<number | "">("");
  const [payAmountNpr, setPayAmountNpr] = useState("");
  const [payMethod, setPayMethod] = useState<"CASH" | "BANK">("BANK");
  const [payRef, setPayRef] = useState("");
  const [payDate, setPayDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [payNotes, setPayNotes] = useState("");
  const [unpaidInvoices, setUnpaidInvoices] = useState<UnpaidInvoice[]>([]);
  const [invoiceAllocations, setInvoiceAllocations] = useState<{ [invoiceId: number]: string }>({});
  const [isSubmittingPayment, setIsSubmittingPayment] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  const fetchAging = async () => {
    setLoading(true);
    setError(null);
    try {
      const url = asOfDate
        ? `/api/v1/receivables/aging?as_of_date=${asOfDate}`
        : "/api/v1/receivables/aging";
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load aging data: ${res.statusText}`);
      }
      const data = await res.json();
      setParties(data.items || []);
      setSummary(data.summary || null);
    } catch (err: any) {
      setError(err.message || "Failed to load aging matrix");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAging();
  }, [asOfDate]);

  // When client changes in payment modal, fetch unpaid invoices
  useEffect(() => {
    if (!payClientId) {
      setUnpaidInvoices([]);
      setInvoiceAllocations({});
      return;
    }
    fetch(`/api/v1/receivables/invoices/${payClientId}`)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setUnpaidInvoices(data);
          // Pre-fill full allocations if payment amount matches
          const allocs: { [k: number]: string } = {};
          data.forEach((inv) => {
            allocs[inv.invoice_id] = "";
          });
          setInvoiceAllocations(allocs);
        }
      })
      .catch(() => setUnpaidInvoices([]));
  }, [payClientId]);

  const handleRecordPayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!payClientId || !payAmountNpr) return;

    setPaymentError(null);
    setIsSubmittingPayment(true);

    try {
      const totalPaisa = toPaisa(payAmountNpr);
      if (totalPaisa <= 0) {
        throw new Error("Payment amount must be greater than zero");
      }

      // Collect allocations
      const allocList: { invoice_id: number; amount_paisa: number }[] = [];
      let totalAllocated = 0;
      for (const [invIdStr, amtStr] of Object.entries(invoiceAllocations)) {
        const invId = parseInt(invIdStr, 10);
        const p = toPaisa(amtStr);
        if (p > 0) {
          allocList.push({ invoice_id: invId, amount_paisa: p });
          totalAllocated += p;
        }
      }

      if (totalAllocated > totalPaisa) {
        throw new Error(
          `Allocated amount (NPR ${fromPaisa(totalAllocated)}) cannot exceed payment amount (NPR ${fromPaisa(totalPaisa)})`
        );
      }

      const payload = {
        client_id: Number(payClientId),
        amount_paisa: totalPaisa,
        payment_method: payMethod,
        reference: payRef || null,
        payment_date: payDate || null,
        notes: payNotes || null,
        invoice_allocations: allocList.length > 0 ? allocList : null
      };

      const res = await fetch("/api/v1/receivables/payments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to record payment");
      }

      setShowPaymentModal(false);
      setPayClientId("");
      setPayAmountNpr("");
      setPayRef("");
      setPayNotes("");
      setInvoiceAllocations({});
      fetchAging();
    } catch (err: any) {
      setPaymentError(err.message || "Failed to record payment");
    } finally {
      setIsSubmittingPayment(false);
    }
  };

  const filteredParties = parties.filter((p) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      p.client_name.toLowerCase().includes(term) ||
      p.client_code.toLowerCase().includes(term) ||
      (p.pan_number && p.pan_number.toLowerCase().includes(term))
    );
  });

  const isViewer = userRole === "viewer";

  const handleExportCSV = () => {
    if (!parties.length) return;
    const headers = [
      "Client Code",
      "Client Name",
      "PAN",
      "Current (0-30d) NPR",
      "31-60d NPR",
      "61-90d NPR",
      ">90d Overdue NPR",
      "Total Due NPR",
      "Unallocated Credit NPR",
      "Credit Limit NPR",
      "Credit Exceeded"
    ];
    const rows = filteredParties.map((p) => [
      `"${p.client_code}"`,
      `"${p.client_name}"`,
      `"${p.pan_number || ""}"`,
      fromPaisa(p.current_paisa, false),
      fromPaisa(p.days_31_60_paisa, false),
      fromPaisa(p.days_61_90_paisa, false),
      fromPaisa(p.over_90_paisa, false),
      fromPaisa(p.total_due_paisa, false),
      fromPaisa(p.unallocated_credit_paisa, false),
      fromPaisa(p.credit_limit_paisa, false),
      p.credit_limit_exceeded ? "YES" : "NO"
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `AR_Aging_${asOfDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ padding: "20px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Top Banner / Title Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "18px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "800", color: "#0F172A", margin: 0, letterSpacing: "-0.01em" }}>
              {isNepali ? "पार्टी बाँकी तथा उमेरगत हिसाब (Party Aging Subledger)" : "Accounts Receivable Aging Subledger"}
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#EFF6FF",
                color: "#1E3A8A",
                border: "1px solid #BFDBFE",
                padding: "2px 8px",
                borderRadius: "3px"
              }}
            >
              {isNepali ? "अनुसूची-५ अडिट (SCHEDULE-5)" : "SCHEDULE-5 AUDIT"}
            </span>
          </div>
          <p style={{ fontSize: "12.5px", color: "#475569", marginTop: "3px", margin: 0 }}>
            {isNepali
              ? "अपरिवर्तनीय लेजर खाताबाट तयार गरिएको शुद्ध पैसामा आधारित हिसाब।"
              : "Party balances derived from append-only ledger entries with exact integer paisa arithmetic."}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* As-Of Date Selector */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              padding: "4px 10px",
              borderRadius: "4px"
            }}
          >
            <Calendar size={14} color="#64748B" />
            <span style={{ fontSize: "12px", color: "#475569", fontWeight: "500" }}>{isNepali ? "मिति:" : "As of:"}</span>
            <input
              type="date"
              value={asOfDate}
              onChange={(e) => setAsOfDate(e.target.value)}
              style={{
                border: "none",
                fontSize: "12px",
                color: "#0F172A",
                fontWeight: "600",
                outline: "none",
                background: "transparent"
              }}
            />
          </div>

          <button
            onClick={fetchAging}
            disabled={loading}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
            title="Refresh Aging Subledger"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{isNepali ? "ताजा गर्नुहोस्" : "Refresh"}</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Download size={13} />
            <span>Export CSV</span>
          </button>

          {/* Record Payment Button (Hidden in Viewer role) */}
          {!isViewer && (
            <button
              onClick={() => {
                setShowPaymentModal(true);
                setPaymentError(null);
              }}
              style={{
                background: "#1E3A8A",
                color: "#FFFFFF",
                border: "none",
                padding: "6px 14px",
                borderRadius: "4px",
                fontSize: "12.5px",
                fontWeight: "600",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <Plus size={14} />
              <span>{isNepali ? "+ भुक्तानी प्रविष्टि (+ Record Payment)" : "+ Record Payment"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Summary KPI Cards Grid (Industrial Paper theme) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "12px",
          marginBottom: "18px"
        }}
      >
        {/* Total Receivables */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #1E3A8A" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748B" }}>
            {isNepali ? "कुल बाँकी रकम (Total Due)" : "Total Outstanding"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#0F172A", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.total_due_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {parties.length} {isNepali ? "ग्राहक खाताहरू" : "customer accounts"}
          </div>
        </div>

        {/* Current (0-30d) */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #047857" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748B" }}>
            {isNepali ? "चालु (०–३० दिन) (Current)" : "Current (0–30 Days)"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#047857", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.current_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "नियमित म्यादभित्र" : "Within payment terms"}
          </div>
        </div>

        {/* 31-60d Overdue */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #D97706" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748B" }}>
            {isNepali ? "३१–६० दिन बाँकी (Overdue)" : "31–60 Days Overdue"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#D97706", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.days_31_60_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "ताकेता चरण" : "Payment follow-up stage"}
          </div>
        </div>

        {/* 61-90d Overdue (Functional Warning Border #A16207) */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #A16207" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#A16207" }}>
            {isNepali ? "६१–९० दिन बाँकी (Overdue)" : "61–90 Days Overdue"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#A16207", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.days_61_90_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "कडा ताकेता आवश्यक" : "Credit-warning alert"}
          </div>
        </div>

        {/* >90d Overdue (Functional Danger Border #B91C1C) */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #B91C1C" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#B91C1C" }}>
            {isNepali ? "> ९० दिन नाघेको (Default Risk)" : "> 90 Days Overdue"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#B91C1C", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.over_90_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#B91C1C", marginTop: "3px", fontWeight: "600" }}>
            {isNepali ? "जोखिमपूर्ण बाँकी" : "Critical default risk"}
          </div>
        </div>

        {/* Unallocated Credits */}
        <div className="glass-card" style={{ padding: "14px 16px", borderLeft: "4px solid #64748B" }}>
          <div style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "#64748B" }}>
            {isNepali ? "असमायोजित अग्रिम (Unallocated)" : "Unallocated Credits"}
          </div>
          <div className="erp-num" style={{ fontSize: "20px", fontWeight: "800", color: "#475569", marginTop: "4px" }}>
            NPR {fromPaisa(summary?.unallocated_credit_paisa ?? 0)}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "मिलान गर्न बाँकी" : "Unsettled receipts"}
          </div>
        </div>
      </div>

      {/* Search and Filter Row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", gap: "12px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "#FFFFFF",
            border: "1px solid #CBD5E1",
            padding: "6px 12px",
            borderRadius: "4px",
            width: "360px"
          }}
        >
          <Search size={15} color="#64748B" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={isNepali ? "पार्टी नाम, कोड वा प्यान खोज्नुहोस्..." : "Search party by name, code or PAN..."}
            style={{
              border: "none",
              outline: "none",
              fontSize: "12.5px",
              width: "100%",
              background: "transparent"
            }}
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8" }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div style={{ fontSize: "12px", color: "#64748B" }}>
          {isNepali ? (
            <>देखाउँदै <strong>{filteredParties.length}</strong> मध्ये <strong>{parties.length}</strong> ग्राहक • खाता हेर्न क्लिक गर्नुहोस्</>
          ) : (
            <>Showing <strong>{filteredParties.length}</strong> of <strong>{parties.length}</strong> debtor accounts • Click row to open Statement</>
          )}
        </div>
      </div>

      {/* Main Party Aging Table */}
      <div className="glass-card" style={{ overflowX: "auto" }}>
        {loading ? (
          <div style={{ padding: "50px", textAlign: "center", color: "#64748B" }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 8px" }} />
            <div>{isNepali ? "पार्टी बाँकी खाता लोड हुँदैछ..." : "Loading accounts receivable aging subledger..."}</div>
          </div>
        ) : error ? (
          <div style={{ padding: "40px", color: "#B91C1C", textAlign: "center" }}>
            <AlertCircle size={24} style={{ margin: "0 auto 8px" }} />
            <div>{error}</div>
          </div>
        ) : filteredParties.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
            {isNepali ? "कुनै ग्राहक भेटिएन।" : "No debtor parties matching query."}
          </div>
        ) : (
          <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", color: "#475569", textAlign: "left" }}>
                <th style={{ padding: "10px 14px" }}>{isNepali ? "पार्टी / ग्राहक (Party / Client)" : "Party / Client"}</th>
                <th style={{ padding: "10px 14px", width: "110px" }}>{isNepali ? "ऋण सीमा (Limit)" : "Credit Limit"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "120px" }}>{isNepali ? "चालु (०-३० दिन)" : "Current (0-30d)"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "110px" }}>{isNepali ? "३१–६० दिन" : "31–60d"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "110px" }}>{isNepali ? "६१–९० दिन" : "61–90d"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "110px" }}>{isNepali ? "> ९० दिन" : "> 90d"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "130px" }}>{isNepali ? "कुल बाँकी (Total Due)" : "Total Due"}</th>
                <th style={{ padding: "10px 14px", textAlign: "right", width: "110px" }}>{isNepali ? "अग्रिम (Credit)" : "Unallocated"}</th>
                <th style={{ padding: "10px 14px", textAlign: "center", width: "80px" }}>{isNepali ? "कार्य (Actions)" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {filteredParties.map((party) => {
                const hasWarning61 = party.days_61_90_paisa > 0;
                const hasDanger90 = party.over_90_paisa > 0;

                let rowBorderLeft = "3px solid transparent";
                if (hasDanger90) {
                  rowBorderLeft = "3px solid #B91C1C";
                } else if (hasWarning61) {
                  rowBorderLeft = "3px solid #A16207";
                }

                return (
                  <tr
                    key={party.client_id}
                    onClick={() => setSelectedClientId(party.client_id)}
                    style={{
                      borderBottom: "1px solid #E2E8F0",
                      borderLeft: rowBorderLeft,
                      cursor: "pointer",
                      transition: "background-color 0.1s ease"
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#F8FAFC")}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#FFFFFF")}
                  >
                    {/* Party Identity */}
                    <td style={{ padding: "8px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span style={{ fontWeight: "700", color: "#0F172A", fontSize: "12.5px" }}>
                          {party.client_name}
                        </span>
                        {party.credit_limit_exceeded && (
                          <span
                            style={{
                              fontSize: "9.5px",
                              fontWeight: "800",
                              background: "#FEF2F2",
                              color: "#B91C1C",
                              border: "1px solid #FCA5A5",
                              padding: "1px 4px",
                              borderRadius: "2px"
                            }}
                            title="Net outstanding exceeds authorized credit limit"
                          >
                            {isNepali ? "रोक (HOLD)" : "HOLD"}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: "11px", color: "#64748B", display: "flex", gap: "8px", marginTop: "1px" }}>
                        <span>{isNepali ? "कोड:" : "Code:"} {party.client_code}</span>
                        {party.pan_number && <span>PAN: {party.pan_number}</span>}
                        {party.phone && <span>Ph: {party.phone}</span>}
                      </div>
                    </td>

                    {/* Credit Limit */}
                    <td className="erp-num" style={{ padding: "8px 14px", color: "#64748B" }}>
                      {party.credit_limit_paisa > 0 ? fromPaisa(party.credit_limit_paisa) : (isNepali ? "सीमा छैन" : "No Limit")}
                    </td>

                    {/* Current (0-30d) */}
                    <td className="erp-num" style={{ padding: "8px 14px", color: party.current_paisa > 0 ? "#047857" : "#94A3B8" }}>
                      {party.current_paisa > 0 ? fromPaisa(party.current_paisa) : "—"}
                    </td>

                    {/* 31-60d */}
                    <td className="erp-num" style={{ padding: "8px 14px", color: party.days_31_60_paisa > 0 ? "#D97706" : "#94A3B8" }}>
                      {party.days_31_60_paisa > 0 ? fromPaisa(party.days_31_60_paisa) : "—"}
                    </td>

                    {/* 61-90d (Highlighted with warning border #A16207) */}
                    <td
                      className="erp-num"
                      style={{
                        padding: "8px 14px",
                        fontWeight: party.days_61_90_paisa > 0 ? "700" : "normal",
                        color: party.days_61_90_paisa > 0 ? "#A16207" : "#94A3B8",
                        backgroundColor: party.days_61_90_paisa > 0 ? "#FEFCE8" : "transparent"
                      }}
                    >
                      {party.days_61_90_paisa > 0 ? fromPaisa(party.days_61_90_paisa) : "—"}
                    </td>

                    {/* > 90d (Highlighted with danger border #B91C1C) */}
                    <td
                      className="erp-num"
                      style={{
                        padding: "8px 14px",
                        fontWeight: party.over_90_paisa > 0 ? "800" : "normal",
                        color: party.over_90_paisa > 0 ? "#B91C1C" : "#94A3B8",
                        backgroundColor: party.over_90_paisa > 0 ? "#FEF2F2" : "transparent"
                      }}
                    >
                      {party.over_90_paisa > 0 ? fromPaisa(party.over_90_paisa) : "—"}
                    </td>

                    {/* Total Due */}
                    <td
                      className="erp-num"
                      style={{
                        padding: "8px 14px",
                        fontWeight: "800",
                        fontSize: "13px",
                        color: party.total_due_paisa > 0 ? "#0F172A" : "#64748B"
                      }}
                    >
                      {fromPaisa(party.total_due_paisa)}
                    </td>

                    {/* Unallocated Credit */}
                    <td className="erp-num" style={{ padding: "8px 14px", color: party.unallocated_credit_paisa > 0 ? "#1E3A8A" : "#94A3B8" }}>
                      {party.unallocated_credit_paisa > 0 ? fromPaisa(party.unallocated_credit_paisa) : "—"}
                    </td>

                    {/* Actions */}
                    <td style={{ padding: "8px 14px", textAlign: "center" }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedClientId(party.client_id);
                        }}
                        className="pagination-btn"
                        style={{ padding: "3px 8px", fontSize: "11px" }}
                      >
                        {isNepali ? "खाता (Statement)" : "Statement"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Party Statement Modal */}
      {selectedClientId && (
        <PartyStatementModal
          clientId={selectedClientId}
          onClose={() => setSelectedClientId(null)}
          userRole={userRole}
        />
      )}

      {/* Record Payment Drawer / Modal */}
      {showPaymentModal && (
        <div className="modal-overlay" style={{ zIndex: 120 }}>
          <div
            className="modal-drawer"
            style={{
              maxWidth: "600px",
              width: "92vw",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px"
            }}
          >
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <CreditCard size={18} color="#1E3A8A" />
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  Record Accounts Receivable Payment
                </h3>
              </div>
              <button
                onClick={() => setShowPaymentModal(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleRecordPayment}>
              <div className="modal-body">
                {paymentError && (
                  <div
                    style={{
                      background: "#FEF2F2",
                      border: "1px solid #FCA5A5",
                      padding: "8px 12px",
                      borderRadius: "3px",
                      color: "#B91C1C",
                      fontSize: "12px"
                    }}
                  >
                    {paymentError}
                  </div>
                )}

                {/* Client Selection */}
                <div>
                  <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                    Select Debtor Party:
                  </label>
                  <select
                    required
                    value={payClientId}
                    onChange={(e) => setPayClientId(e.target.value ? Number(e.target.value) : "")}
                    style={{
                      width: "100%",
                      padding: "8px",
                      fontSize: "12.5px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "3px",
                      background: "#FFFFFF"
                    }}
                  >
                    <option value="">-- Choose Party --</option>
                    {parties.map((p) => (
                      <option key={p.client_id} value={p.client_id}>
                        {p.client_name} ({p.client_code}) — Due: NPR {fromPaisa(p.total_due_paisa)}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Amount and Method Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Payment Amount (NPR):
                    </label>
                    <input
                      required
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder="0.00"
                      value={payAmountNpr}
                      onChange={(e) => setPayAmountNpr(e.target.value)}
                      className="erp-num"
                      style={{
                        width: "100%",
                        padding: "8px",
                        fontSize: "13px",
                        border: "1px solid #CBD5E1",
                        borderRadius: "3px",
                        boxSizing: "border-box"
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Payment Method:
                    </label>
                    <select
                      value={payMethod}
                      onChange={(e) => setPayMethod(e.target.value as "CASH" | "BANK")}
                      style={{
                        width: "100%",
                        padding: "8px",
                        fontSize: "12.5px",
                        border: "1px solid #CBD5E1",
                        borderRadius: "3px",
                        background: "#FFFFFF"
                      }}
                    >
                      <option value="BANK">BANK / Cheque / Transfer</option>
                      <option value="CASH">CASH Counter Receipt</option>
                    </select>
                  </div>
                </div>

                {/* Reference and Date Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Reference / Cheque #:
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. CHQ-990812 or Bank Ref"
                      value={payRef}
                      onChange={(e) => setPayRef(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        fontSize: "12.5px",
                        border: "1px solid #CBD5E1",
                        borderRadius: "3px",
                        boxSizing: "border-box"
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Receipt Date:
                    </label>
                    <input
                      type="date"
                      value={payDate}
                      onChange={(e) => setPayDate(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        fontSize: "12px",
                        border: "1px solid #CBD5E1",
                        borderRadius: "3px",
                        boxSizing: "border-box"
                      }}
                    />
                  </div>
                </div>

                {/* Optional Invoice Allocation Table */}
                {unpaidInvoices.length > 0 && (
                  <div style={{ marginTop: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <label style={{ fontSize: "11.5px", fontWeight: "600", color: "#475569" }}>
                        Settle Specific Invoices (Optional):
                      </label>
                      <span style={{ fontSize: "11px", color: "#64748B" }}>
                        Unallocated portion remains as advance credit
                      </span>
                    </div>

                    <div style={{ maxHeight: "160px", overflowY: "auto", border: "1px solid #CBD5E1", borderRadius: "3px" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "11.5px" }}>
                        <thead>
                          <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", textAlign: "left" }}>
                            <th style={{ padding: "6px 8px" }}>Invoice</th>
                            <th style={{ padding: "6px 8px" }}>Date</th>
                            <th style={{ padding: "6px 8px", textAlign: "right" }}>Remaining</th>
                            <th style={{ padding: "6px 8px", textAlign: "right", width: "100px" }}>Allocate NPR</th>
                          </tr>
                        </thead>
                        <tbody>
                          {unpaidInvoices.map((inv) => (
                            <tr key={inv.invoice_id} style={{ borderBottom: "1px solid #E2E8F0" }}>
                              <td style={{ padding: "6px 8px", fontWeight: "600", color: "#1E3A8A" }}>
                                {inv.invoice_number}
                              </td>
                              <td style={{ padding: "6px 8px", color: "#64748B" }}>
                                {inv.invoice_date}
                              </td>
                              <td className="erp-num" style={{ padding: "6px 8px", color: "#0F172A" }}>
                                {fromPaisa(inv.remaining_paisa)}
                              </td>
                              <td style={{ padding: "4px 8px", textAlign: "right" }}>
                                <input
                                  type="number"
                                  step="0.01"
                                  placeholder="0.00"
                                  value={invoiceAllocations[inv.invoice_id] || ""}
                                  onChange={(e) =>
                                    setInvoiceAllocations({
                                      ...invoiceAllocations,
                                      [inv.invoice_id]: e.target.value
                                    })
                                  }
                                  className="erp-num"
                                  style={{
                                    width: "90px",
                                    padding: "3px 6px",
                                    fontSize: "11.5px",
                                    border: "1px solid #CBD5E1",
                                    borderRadius: "2px"
                                  }}
                                />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Notes */}
                <div>
                  <label style={{ display: "block", fontSize: "11.5px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                    Internal Ledger Notes:
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Received via Prabhu Bank A/C 001928"
                    value={payNotes}
                    onChange={(e) => setPayNotes(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "8px",
                      fontSize: "12.5px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "3px",
                      boxSizing: "border-box"
                    }}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={() => setShowPaymentModal(false)}
                  className="pagination-btn"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingPayment}
                  style={{
                    background: "#047857",
                    color: "#FFFFFF",
                    border: "none",
                    padding: "8px 18px",
                    borderRadius: "4px",
                    fontSize: "12.5px",
                    fontWeight: "600",
                    cursor: "pointer"
                  }}
                >
                  {isSubmittingPayment ? "Posting Payment..." : "Commit Payment Receipt"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
