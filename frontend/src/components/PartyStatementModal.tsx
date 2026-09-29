"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Printer,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  FileText,
  CreditCard,
  Building,
  Phone,
  User,
  ShieldAlert,
  ArrowDownLeft,
  ArrowUpRight
} from "lucide-react";
import { fromPaisa } from "@/lib/currency";
import { useLocale } from "@/context/LocaleContext";

interface PartyStatementModalProps {
  clientId: number;
  onClose: () => void;
  userRole: string;
}

interface StatementLine {
  id: number;
  occurred_at: string | null;
  entry_type: string;
  source_doc_ref: string;
  invoice_id: number | null;
  direction: number;
  amount_paisa: number;
  debit_paisa: number;
  credit_paisa: number;
  running_balance_paisa: number;
  due_date: string | null;
  is_disputed: boolean;
  dispute_notes: string;
  notes: string;
  actor_name: string;
}

interface ClientMeta {
  id: number;
  code: string;
  name: string;
  pan_number: string;
  contact_person: string;
  phone: string;
  address: string;
  credit_limit: number;
  credit_limit_paisa: number;
}

interface StatementSummary {
  total_debit_paisa: number;
  total_credit_paisa: number;
  net_balance_paisa: number;
  statement_lines_count: number;
}

export function PartyStatementModal({ clientId, onClose, userRole }: PartyStatementModalProps) {
  const { isNepali } = useLocale();
  const [loading, setLoading] = useState(true);
  const [client, setClient] = useState<ClientMeta | null>(null);
  const [summary, setSummary] = useState<StatementSummary | null>(null);
  const [lines, setLines] = useState<StatementLine[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [includeDisputed, setIncludeDisputed] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dispute editing state
  const [disputeModalEntry, setDisputeModalEntry] = useState<StatementLine | null>(null);
  const [disputeNotes, setDisputeNotes] = useState("");
  const [isSubmittingDispute, setIsSubmittingDispute] = useState(false);

  const fetchStatement = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.append("date_from", dateFrom);
      if (dateTo) params.append("date_to", dateTo);
      params.append("include_disputed", includeDisputed ? "true" : "false");

      const res = await fetch(`/api/v1/receivables/statement/${clientId}?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Failed to load party statement: ${res.statusText}`);
      }
      const data = await res.json();
      setClient(data.client);
      setSummary(data.summary);
      setLines(data.lines || []);
    } catch (err: any) {
      setError(err.message || "Error loading statement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatement();
  }, [clientId, dateFrom, dateTo, includeDisputed]);

  const handleToggleDispute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disputeModalEntry) return;
    setIsSubmittingDispute(true);
    try {
      const nextStatus = !disputeModalEntry.is_disputed;
      const res = await fetch(`/api/v1/receivables/dispute/${disputeModalEntry.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_disputed: nextStatus,
          dispute_notes: nextStatus ? disputeNotes : null
        })
      });
      if (!res.ok) throw new Error("Failed to update dispute status");
      setDisputeModalEntry(null);
      setDisputeNotes("");
      fetchStatement();
    } catch (err: any) {
      alert(err.message || "Could not update dispute status");
    } finally {
      setIsSubmittingDispute(false);
    }
  };

  const isViewer = userRole === "viewer";

  return (
    <div className="modal-overlay" style={{ zIndex: 100 }}>
      <div
        className="modal-drawer statement-printable"
        style={{
          maxWidth: "1050px",
          width: "95vw",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          background: "#FFFFFF",
          border: "1px solid #CBD5E1",
          borderRadius: "4px"
        }}
      >
        {/* Modal Header */}
        <div
          className="modal-header no-print"
          style={{
            background: "#F8FAFC",
            borderBottom: "1px solid #CBD5E1",
            padding: "12px 18px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FileText size={20} color="#1E3A8A" />
            <div>
              <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                {isNepali ? "ग्राहक हिसाब विवरण (Party Statement)" : "Party Account Statement & Subledger"}
              </h3>
              <div style={{ fontSize: "11px", color: "#475569" }}>
                {isNepali
                  ? "अपरिवर्तनीय लेजर प्रविष्टिहरू • अनुसूची-५ लेखापरीक्षण"
                  : "Auditable append-only ledger entries • Schedule-5 compliant"}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={() => window.print()}
              className="pagination-btn"
              style={{ display: "flex", alignItems: "center", gap: "6px" }}
              title="Print Customer Statement (A4)"
            >
              <Printer size={14} />
              <span>{isNepali ? "खाता प्रिन्ट (Print)" : "Print Statement"}</span>
            </button>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#475569",
                padding: "4px"
              }}
              aria-label="Close statement"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Printable Statement Header */}
        <div style={{ padding: "18px 24px", borderBottom: "1px solid #E2E8F0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
            <div>
              <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748B", fontWeight: "700" }}>
                {isNepali ? "ऋणी खाता विवरण (Debtor Account)" : "Debtor Account"}
              </div>
              <div style={{ fontSize: "18px", fontWeight: "800", color: "#0F172A", marginTop: "2px" }}>
                {client?.name || (isNepali ? "लोड हुँदैछ..." : "Loading...")}
              </div>
              <div style={{ display: "flex", gap: "16px", marginTop: "6px", fontSize: "12px", color: "#475569" }}>
                <span><strong>{isNepali ? "पार्टी कोड:" : "Party Code:"}</strong> {client?.code || "—"}</span>
                {client?.pan_number && <span><strong>{isNepali ? "स्थायी लेखा नं (PAN):" : "PAN:"}</strong> {client.pan_number}</span>}
                {client?.phone && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <Phone size={12} /> {client.phone}
                  </span>
                )}
                {client?.contact_person && (
                  <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <User size={12} /> {client.contact_person}
                  </span>
                )}
              </div>
            </div>

            <div style={{ textAlign: "right", minWidth: "220px" }}>
              <div style={{ fontSize: "11px", textTransform: "uppercase", color: "#64748B", fontWeight: "600" }}>
                {isNepali ? "कुल बाँकी मौज्दात (Net Balance)" : "Net Ledger Balance"}
              </div>
              <div
                className="erp-num"
                style={{
                  fontSize: "22px",
                  fontWeight: "800",
                  color: (summary?.net_balance_paisa ?? 0) > 0 ? "#B91C1C" : "#047857",
                  marginTop: "2px"
                }}
              >
                NPR {fromPaisa(summary?.net_balance_paisa ?? 0)}
              </div>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "2px" }}>
                {isNepali ? "ऋण सीमा (Credit Limit):" : "Credit Limit:"} <strong>NPR {fromPaisa(client?.credit_limit_paisa ?? 0)}</strong>
                {client && client.credit_limit_paisa > 0 && (summary?.net_balance_paisa ?? 0) > client.credit_limit_paisa && (
                  <span style={{ color: "#B91C1C", fontWeight: "700", marginLeft: "6px" }}>
                    {isNepali ? "[सीमा नाघ्यो]" : "[EXCEEDED]"}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Filters Bar (Hidden in Print) */}
          <div
            className="no-print"
            style={{
              marginTop: "16px",
              paddingTop: "12px",
              borderTop: "1px dashed #CBD5E1",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "12px"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#475569" }}>
                <Calendar size={13} />
                <span>{isNepali ? "देखि:" : "From:"}</span>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  style={{
                    padding: "3px 6px",
                    fontSize: "12px",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    background: "#FFFFFF"
                  }}
                />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", color: "#475569" }}>
                <span>{isNepali ? "सम्म:" : "To:"}</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  style={{
                    padding: "3px 6px",
                    fontSize: "12px",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    background: "#FFFFFF"
                  }}
                />
              </div>
              {(dateFrom || dateTo) && (
                <button
                  onClick={() => {
                    setDateFrom("");
                    setDateTo("");
                  }}
                  className="pagination-btn"
                  style={{ padding: "2px 8px", fontSize: "11px" }}
                >
                  {isNepali ? "फिल्टर हटाउनुहोस्" : "Clear Range"}
                </button>
              )}
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#475569", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={includeDisputed}
                onChange={(e) => setIncludeDisputed(e.target.checked)}
              />
              <span>{isNepali ? "विवादित बिजक समावेश (Include Disputed)" : "Include Disputed Invoices"}</span>
            </label>
          </div>
        </div>

        {/* Statement Table Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0" }}>
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
              {isNepali ? "लेखा खाता प्रविष्टिहरू लोड हुँदैछ..." : "Loading auditable statement entries..."}
            </div>
          ) : error ? (
            <div style={{ padding: "30px", color: "#B91C1C", textAlign: "center" }}>
              {error}
            </div>
          ) : lines.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
              {isNepali ? "यस पार्टीको कुनै कारोबार भेटिएन।" : "No statement entries found for this party."}
            </div>
          ) : (
            <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", color: "#475569", textAlign: "left" }}>
                  <th style={{ padding: "8px 12px", width: "95px" }}>{isNepali ? "मिति (Date)" : "Date"}</th>
                  <th style={{ padding: "8px 12px", width: "130px" }}>{isNepali ? "भौचर / बिजक नं (Voucher Ref)" : "Voucher Ref"}</th>
                  <th style={{ padding: "8px 12px" }}>{isNepali ? "विवरण (Particulars)" : "Description / Entry Type"}</th>
                  <th style={{ padding: "8px 12px", width: "95px" }}>{isNepali ? "भाका मिति (Due Date)" : "Due Date"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "110px" }}>{isNepali ? "डेबिट (+) (Debit)" : "Debit (+)"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "110px" }}>{isNepali ? "क्रेडिट (-) (Credit)" : "Credit (-)"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "125px" }}>{isNepali ? "बाँकी मौज्दात (Balance)" : "Balance"}</th>
                  <th className="no-print" style={{ padding: "8px 12px", textAlign: "center", width: "90px" }}>{isNepali ? "जाँच (Audit)" : "Audit"}</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((line) => {
                  const dateStr = line.occurred_at ? line.occurred_at.split("T")[0] : "—";
                  const dueStr = line.due_date ? line.due_date.split("T")[0] : "—";
                  return (
                    <tr
                      key={line.id}
                      style={{
                        borderBottom: "1px solid #E2E8F0",
                        background: line.is_disputed ? "#FEF2F2" : "#FFFFFF"
                      }}
                    >
                      <td style={{ padding: "7px 12px", color: "#475569", whiteSpace: "nowrap" }}>
                        {dateStr}
                      </td>
                      <td style={{ padding: "7px 12px", whiteSpace: "nowrap" }}>
                        {line.invoice_id ? (
                          <a
                            href={`/api/v1/invoices/${line.invoice_id}/printable`}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              color: "#1E3A8A",
                              fontWeight: "600",
                              textDecoration: "underline",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "3px"
                            }}
                            title="Open Printable Tax Invoice"
                          >
                            {line.source_doc_ref}
                          </a>
                        ) : (
                          <span style={{ fontWeight: "600", color: "#0F172A" }}>
                            {line.source_doc_ref || `ENTRY-${line.id}`}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "7px 12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                          <span
                            style={{
                              fontSize: "10.5px",
                              fontWeight: "700",
                              padding: "1px 6px",
                              borderRadius: "2px",
                              background: line.direction === 1 ? "#EFF6FF" : "#F0FDF4",
                              color: line.direction === 1 ? "#1E3A8A" : "#047857",
                              border: `1px solid ${line.direction === 1 ? "#BFDBFE" : "#BBF7D0"}`
                            }}
                          >
                            {line.entry_type}
                          </span>
                          <span style={{ color: "#334155" }}>{line.notes}</span>
                          {line.is_disputed && (
                            <span
                              style={{
                                fontSize: "10px",
                                fontWeight: "700",
                                color: "#B91C1C",
                                background: "#FEE2E2",
                                padding: "1px 5px",
                                borderRadius: "2px",
                                border: "1px solid #FCA5A5",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "2px"
                              }}
                              title={line.dispute_notes}
                            >
                              <AlertTriangle size={10} /> DISPUTED
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: "7px 12px", color: "#64748B", whiteSpace: "nowrap" }}>
                        {dueStr}
                      </td>
                      <td className="erp-num" style={{ padding: "7px 12px", color: line.debit_paisa > 0 ? "#0F172A" : "#94A3B8" }}>
                        {line.debit_paisa > 0 ? fromPaisa(line.debit_paisa) : "—"}
                      </td>
                      <td className="erp-num" style={{ padding: "7px 12px", color: line.credit_paisa > 0 ? "#047857" : "#94A3B8" }}>
                        {line.credit_paisa > 0 ? fromPaisa(line.credit_paisa) : "—"}
                      </td>
                      <td
                        className="erp-num"
                        style={{
                          padding: "7px 12px",
                          fontWeight: "700",
                          color: line.running_balance_paisa > 0 ? "#B91C1C" : "#047857"
                        }}
                      >
                        {fromPaisa(line.running_balance_paisa)}
                      </td>
                      <td className="no-print" style={{ padding: "7px 12px", textAlign: "center" }}>
                        {!isViewer && (
                          <button
                            onClick={() => {
                              setDisputeModalEntry(line);
                              setDisputeNotes(line.dispute_notes || "");
                            }}
                            className="pagination-btn"
                            style={{
                              padding: "2px 6px",
                              fontSize: "10.5px",
                              borderColor: line.is_disputed ? "#FCA5A5" : "#CBD5E1",
                              color: line.is_disputed ? "#B91C1C" : "#475569"
                            }}
                          >
                            {line.is_disputed ? "Resolve" : "Flag"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Modal Footer / Print Summary */}
        <div
          className="modal-footer"
          style={{
            background: "#F8FAFC",
            borderTop: "1px solid #CBD5E1",
            padding: "12px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div style={{ fontSize: "11px", color: "#64748B" }}>
            {isNepali ? "कुल प्रविष्टि संख्या:" : "Total Entries:"} <strong>{lines.length}</strong> • {isNepali ? "प्रमाणित स्टेटमेन्ट मिति" : "Certified Statement Generated on"} {new Date().toLocaleDateString()}
          </div>
          <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
            <div style={{ fontSize: "12px" }}>
              {isNepali ? "कुल डेबिट:" : "Total Debits:"} <strong className="erp-num">NPR {fromPaisa(summary?.total_debit_paisa ?? 0)}</strong>
            </div>
            <div style={{ fontSize: "12px" }}>
              {isNepali ? "कुल क्रेडिट:" : "Total Credits:"} <strong className="erp-num" style={{ color: "#047857" }}>NPR {fromPaisa(summary?.total_credit_paisa ?? 0)}</strong>
            </div>
            <div style={{ fontSize: "13px", fontWeight: "700", paddingLeft: "10px", borderLeft: "2px solid #CBD5E1" }}>
              {isNepali ? "अन्तिम बाँकी:" : "Closing Due:"} <span className="erp-num" style={{ color: (summary?.net_balance_paisa ?? 0) > 0 ? "#B91C1C" : "#047857" }}>
                NPR {fromPaisa(summary?.net_balance_paisa ?? 0)}
              </span>
            </div>
          </div>
        </div>

        {/* Dispute Toggle Sub-Modal */}
        {disputeModalEntry && (
          <div className="modal-overlay" style={{ zIndex: 110 }}>
            <div
              className="modal-drawer"
              style={{
                maxWidth: "460px",
                width: "90vw",
                background: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: "4px",
                padding: "20px"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {disputeModalEntry.is_disputed ? "Resolve Invoice Dispute" : "Flag Entry as Disputed"}
                </h4>
                <button
                  onClick={() => setDisputeModalEntry(null)}
                  style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}
                >
                  <X size={16} />
                </button>
              </div>

              <p style={{ fontSize: "12px", color: "#475569", marginBottom: "14px", lineHeight: "1.5" }}>
                Ref: <strong>{disputeModalEntry.source_doc_ref}</strong> • Amount: <strong>NPR {fromPaisa(disputeModalEntry.amount_paisa)}</strong>
                <br />
                {disputeModalEntry.is_disputed
                  ? "Marking this entry as resolved clears the dispute flag. Balance arithmetic is preserved."
                  : "Flagging marks the invoice for Schedule-5 reconciliation review without dropping statutory liability."}
              </p>

              <form onSubmit={handleToggleDispute}>
                {!disputeModalEntry.is_disputed && (
                  <div style={{ marginBottom: "14px" }}>
                    <label style={{ display: "block", fontSize: "11px", fontWeight: "600", color: "#475569", marginBottom: "4px" }}>
                      Dispute Reason / Notes:
                    </label>
                    <textarea
                      required
                      value={disputeNotes}
                      onChange={(e) => setDisputeNotes(e.target.value)}
                      placeholder="e.g., Rate mismatch on line 2; credit note pending from warehouse"
                      rows={3}
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
                )}

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setDisputeModalEntry(null)}
                    className="pagination-btn"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingDispute}
                    style={{
                      background: disputeModalEntry.is_disputed ? "#047857" : "#B91C1C",
                      color: "#FFFFFF",
                      border: "none",
                      padding: "6px 14px",
                      borderRadius: "3px",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer"
                    }}
                  >
                    {isSubmittingDispute
                      ? "Saving..."
                      : disputeModalEntry.is_disputed
                      ? "Clear Dispute Flag"
                      : "Confirm Dispute Flag"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
