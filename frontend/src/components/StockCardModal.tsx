"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  X,
  FileText,
  Boxes,
  ArrowDownRight,
  ArrowUpRight,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Filter,
  Calendar,
  Layers,
  Warehouse as WarehouseIcon,
  RefreshCw
} from "lucide-react";

interface StockMovementItem {
  id: number;
  product_id: number;
  product_code: string;
  product_name: string;
  category: string;
  warehouse_id: number;
  warehouse_name: string;
  size: string;
  quantity: number;
  direction: number;
  qty_in: number;
  qty_out: number;
  running_balance: number;
  movement_type: string;
  source_doc_ref: string;
  ref_type: string;
  ref_id: number | null;
  reversal_of_id: number | null;
  reason_code: string;
  reason_text: string;
  actor_id: number;
  actor_name: string;
  approved_by_id: number | null;
  approved_by_name: string | null;
  date_ad: string;
  date_bs: string;
  notes: string;
  created_at: string | null;
}

interface StockCardModalProps {
  product: {
    id: number;
    code: string;
    name: string;
    category?: string;
    color?: string;
    unit_price?: number;
    sizes?: Record<number, number>;
  };
  userRole?: string;
  onClose: () => void;
  onStockChanged?: () => void;
}

const PARIS_POINTS = [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43];

export function StockCardModal({ product, userRole, onClose, onStockChanged }: StockCardModalProps) {
  const [movements, setMovements] = useState<StockMovementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [sizeFilter, setSizeFilter] = useState<string>("all");
  const [movementTypeFilter, setMovementTypeFilter] = useState<string>("all");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // Live Paris Points Curve
  const [liveCurve, setLiveCurve] = useState<Record<number, number>>({});

  // Deep-Link Reference Voucher Inspection state
  const [inspectDoc, setInspectDoc] = useState<StockMovementItem | null>(null);

  // Reversal Confirmation state
  const [reversingMovement, setReversingMovement] = useState<StockMovementItem | null>(null);
  const [reversalLoading, setReversalLoading] = useState(false);

  const canReverse = userRole !== "viewer" && userRole !== "viewer_demo";

  // Fetch live curve for the model
  const fetchLiveCurve = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/stock/curve/${product.id}`);
      if (res.ok) {
        const data = await res.json();
        if (data.curve) {
          setLiveCurve(data.curve);
        }
      }
    } catch {
      // Fallback to product.sizes if provided
      if (product.sizes) {
        setLiveCurve(product.sizes);
      }
    }
  }, [product.id, product.sizes]);

  // Fetch movements from /api/v1/stock/ledger
  const fetchLedger = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("product_id", String(product.id));
      if (sizeFilter !== "all") params.set("size", sizeFilter);
      if (movementTypeFilter !== "all") params.set("movement_type", movementTypeFilter);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      params.set("limit", "200");

      const res = await fetch(`/api/v1/stock/ledger?${params.toString()}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to load stock movements");
      }
      const data = await res.json();
      setMovements(data.items || []);
    } catch (e: any) {
      setError(e.message || "Failed to load ledger records");
    } finally {
      setLoading(false);
    }
  }, [product.id, sizeFilter, movementTypeFilter, dateFrom, dateTo]);

  useEffect(() => {
    fetchLiveCurve();
  }, [fetchLiveCurve]);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (inspectDoc) {
          setInspectDoc(null);
        } else if (reversingMovement) {
          setReversingMovement(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [inspectDoc, reversingMovement, onClose]);

  // Execute Reversal
  const handleExecuteReversal = async () => {
    if (!reversingMovement) return;
    setReversalLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await fetch(`/api/v1/stock/reversals/${reversingMovement.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Reversal request failed");
      }
      setSuccessMsg(`Movement #${reversingMovement.id} successfully reversed.`);
      setReversingMovement(null);
      await fetchLedger();
      await fetchLiveCurve();
      if (onStockChanged) onStockChanged();
    } catch (e: any) {
      setError(e.message || "Failed to execute reversal");
    } finally {
      setReversalLoading(false);
    }
  };

  // Helper for High-Contrast Type Badges
  const renderMovementBadge = (type: string) => {
    switch (type) {
      case "PRODUCTION_IN":
        return (
          <span
            style={{
              background: "#ECFDF5",
              color: "#065F46",
              border: "1px solid #10B981",
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "11px",
              fontWeight: "700",
              letterSpacing: "0.02em",
              display: "inline-block",
              whiteSpace: "nowrap"
            }}
          >
            [उत्पादन दाखिला]
          </span>
        );
      case "SALES_OUT":
        return (
          <span
            style={{
              background: "#EFF6FF",
              color: "#1E40AF",
              border: "1px solid #3B82F6",
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "11px",
              fontWeight: "700",
              letterSpacing: "0.02em",
              display: "inline-block",
              whiteSpace: "nowrap"
            }}
          >
            [बिक्री निकासी]
          </span>
        );
      case "ADJUSTMENT_IN":
      case "ADJUSTMENT_OUT":
      case "ADJUSTMENT":
        return (
          <span
            style={{
              background: "#FFFBEB",
              color: "#92400E",
              border: "1px solid #F59E0B",
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "11px",
              fontWeight: "700",
              letterSpacing: "0.02em",
              display: "inline-block",
              whiteSpace: "nowrap"
            }}
          >
            [स्टक मिलान]
          </span>
        );
      case "VOID_REVERSAL":
        return (
          <span
            style={{
              background: "#FEF2F2",
              color: "#991B1B",
              border: "1px solid #EF4444",
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "11px",
              fontWeight: "700",
              letterSpacing: "0.02em",
              display: "inline-block",
              whiteSpace: "nowrap"
            }}
          >
            [रद्द फिर्ता]
          </span>
        );
      default:
        return (
          <span
            style={{
              background: "#F1F5F9",
              color: "#334155",
              border: "1px solid #CBD5E1",
              padding: "2px 6px",
              borderRadius: "3px",
              fontSize: "11px",
              fontWeight: "700",
              display: "inline-block"
            }}
          >
            [{type}]
          </span>
        );
    }
  };

  const totalPairsAcrossCurve = useMemo(() => {
    return Object.values(liveCurve).reduce((sum, v) => sum + (Number(v) || 0), 0);
  }, [liveCurve]);

  return (
    <div
      className="modal-overlay"
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px"
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stock-card-title"
        style={{
          width: "100%",
          maxWidth: "1180px",
          maxHeight: "92vh",
          display: "flex",
          flexDirection: "column",
          background: "#FFFFFF",
          border: "1px solid #CBD5E1",
          borderRadius: "4px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
          overflow: "hidden"
        }}
      >
        {/* HEADER / STICKY META DOCK */}
        <div
          style={{
            position: "sticky",
            top: 0,
            zIndex: 10,
            background: "#F8FAFC",
            borderBottom: "2px solid #CBD5E1",
            padding: "14px 20px"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  background: "#1E3A8A",
                  color: "#FFFFFF",
                  padding: "6px",
                  borderRadius: "3px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}
              >
                <Boxes size={18} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2 id="stock-card-title" style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                    {product.name}
                  </h2>
                  <span
                    style={{
                      background: "#E2E8F0",
                      color: "#0F172A",
                      fontSize: "11px",
                      fontWeight: "700",
                      padding: "2px 6px",
                      borderRadius: "3px",
                      fontFamily: "monospace"
                    }}
                  >
                    SKU: {product.code}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px", display: "flex", gap: "12px" }}>
                  <span>वर्ग (Category): <strong>{product.category || "Footwear"}</strong></span>
                  <span>रंग (Color): <strong>{product.color || "Standard"}</strong></span>
                  <span>मूल्य (Price): <strong>Rs. {product.unit_price ? product.unit_price.toLocaleString() : "0"}</strong></span>
                  <span>वेयरहाउस (Warehouse): <strong>Main Finished Warehouse (WH-MAIN)</strong></span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <div
                style={{
                  textAlign: "right",
                  padding: "4px 12px",
                  background: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  borderRadius: "3px"
                }}
              >
                <div style={{ fontSize: "10px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>
                  कुल मौज्दात (Total On-Hand)
                </div>
                <div style={{ fontSize: "18px", fontWeight: "700", color: "#1E3A8A" }} className="num-mono-bold">
                  {totalPairsAcrossCurve.toLocaleString()} <span style={{ fontSize: "12px", fontWeight: "400" }}>जोर (pairs)</span>
                </div>
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close stock card"
                style={{
                  background: "transparent",
                  border: "1px solid #CBD5E1",
                  borderRadius: "3px",
                  padding: "6px",
                  cursor: "pointer",
                  color: "#475569",
                  display: "flex",
                  alignItems: "center"
                }}
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* HORIZONTAL PARIS POINTS (32-43) LIVE STOCK CURVE DOCK */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "3px",
              padding: "8px 12px"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", color: "#0F172A", textTransform: "uppercase", letterSpacing: "0.03em" }}>
                पेरिस पोइन्ट साइज मौज्दात वक्र (Paris Points 32–43 Live Curve)
              </div>
              <div style={{ fontSize: "11px", color: "#64748B" }}>
                कुनै साइज क्लिक गरी लेजर फिल्टर गर्नुहोस्
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(12, 1fr)",
                gap: "4px"
              }}
            >
              {PARIS_POINTS.map((sz) => {
                const count = liveCurve[sz] ?? (product.sizes ? product.sizes[sz] : 0) ?? 0;
                const isSelected = sizeFilter === String(sz);
                const hasStock = count > 0;
                return (
                  <button
                    key={sz}
                    type="button"
                    onClick={() => setSizeFilter(isSelected ? "all" : String(sz))}
                    title={`Size ${sz}: ${count} pairs on-hand`}
                    style={{
                      border: isSelected ? "2px solid #1E3A8A" : "1px solid #CBD5E1",
                      borderRadius: "3px",
                      padding: "4px 2px",
                      textAlign: "center",
                      cursor: "pointer",
                      background: isSelected ? "#EFF6FF" : hasStock ? "#F8FAFC" : "#FFFFFF",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "2px"
                    }}
                  >
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: isSelected ? "700" : "600",
                        color: isSelected ? "#1E3A8A" : "#0F172A"
                      }}
                    >
                      {sz}
                    </span>
                    <span
                      className="num-mono-bold"
                      style={{
                        fontSize: "12px",
                        fontWeight: "700",
                        color: hasStock ? (count <= 10 ? "#D97706" : "#059669") : "#94A3B8"
                      }}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* FEEDBACK BANNERS */}
        {error && (
          <div
            role="alert"
            style={{
              background: "#FEF2F2",
              borderBottom: "1px solid #EF4444",
              padding: "8px 20px",
              color: "#991B1B",
              fontSize: "12.5px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertTriangle size={15} color="#EF4444" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              style={{ background: "none", border: "none", color: "#991B1B", cursor: "pointer", fontWeight: "700" }}
            >
              ×
            </button>
          </div>
        )}

        {successMsg && (
          <div
            role="status"
            style={{
              background: "#ECFDF5",
              borderBottom: "1px solid #10B981",
              padding: "8px 20px",
              color: "#065F46",
              fontSize: "12.5px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <CheckCircle2 size={15} color="#10B981" />
              <span>{successMsg}</span>
            </div>
            <button
              onClick={() => setSuccessMsg(null)}
              style={{ background: "none", border: "none", color: "#065F46", cursor: "pointer", fontWeight: "700" }}
            >
              ×
            </button>
          </div>
        )}

        {/* FILTERS TOOLBAR */}
        <div
          style={{
            padding: "10px 20px",
            background: "#FFFFFF",
            borderBottom: "1px solid #CBD5E1",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "10px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#475569" }}>
              <Filter size={14} color="#1E3A8A" />
              <span style={{ fontWeight: "600" }}>साइज:</span>
              <select
                value={sizeFilter}
                onChange={(e) => setSizeFilter(e.target.value)}
                className="input-field"
                style={{ padding: "4px 8px", fontSize: "12px", width: "95px" }}
              >
                <option value="all">सबै (All)</option>
                {PARIS_POINTS.map((sz) => (
                  <option key={sz} value={String(sz)}>
                    साइज {sz}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#475569" }}>
              <span style={{ fontWeight: "600" }}>प्रकार (Type):</span>
              <select
                value={movementTypeFilter}
                onChange={(e) => setMovementTypeFilter(e.target.value)}
                className="input-field"
                style={{ padding: "4px 8px", fontSize: "12px", width: "170px" }}
              >
                <option value="all">सबै प्रकार (All Types)</option>
                <option value="PRODUCTION_IN">उत्पादन दाखिला (Production In)</option>
                <option value="SALES_OUT">बिक्री निकासी (Sales Out)</option>
                <option value="ADJUSTMENT_IN">स्टक मिलान बढोत्तरी (Adj In)</option>
                <option value="ADJUSTMENT_OUT">स्टक मिलान घटबढ (Adj Out)</option>
                <option value="VOID_REVERSAL">रद्द फिर्ता (Void Reversal)</option>
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#475569" }}>
              <Calendar size={14} />
              <span>मिति:</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="input-field"
                style={{ padding: "3px 6px", fontSize: "11.5px", width: "120px" }}
              />
              <span>-</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="input-field"
                style={{ padding: "3px 6px", fontSize: "11.5px", width: "120px" }}
              />
            </div>

            {(sizeFilter !== "all" || movementTypeFilter !== "all" || dateFrom || dateTo) && (
              <button
                type="button"
                onClick={() => {
                  setSizeFilter("all");
                  setMovementTypeFilter("all");
                  setDateFrom("");
                  setDateTo("");
                }}
                style={{
                  background: "#F1F5F9",
                  border: "1px solid #CBD5E1",
                  borderRadius: "3px",
                  padding: "4px 8px",
                  fontSize: "11px",
                  cursor: "pointer",
                  color: "#475569"
                }}
              >
                फिल्टर हटाउनुहोस् (Reset)
              </button>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", color: "#475569" }}>
              जम्मा दाखिला/निकासी: <strong>{movements.length}</strong>
            </span>
            <button
              type="button"
              onClick={() => {
                fetchLedger();
                fetchLiveCurve();
              }}
              className="btn-secondary"
              style={{ padding: "4px 8px", fontSize: "11.5px" }}
              title="Refresh ledger records"
            >
              <RefreshCw size={12} />
            </button>
          </div>
        </div>

        {/* CHRONOLOGICAL MOVEMENT TABLE */}
        <div style={{ flex: 1, overflowY: "auto", padding: "0 20px 20px" }}>
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#475569" }}>
              <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px", color: "#1E3A8A" }} />
              <div>स्टक भौचर विवरण लोड हुँदैछ (Loading stock ledger)...</div>
            </div>
          ) : movements.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
              यस फिल्टर मा कुनै पनि स्टक कारोबार फेला परेन। (No stock movements found matching filter).
            </div>
          ) : (
            <div className="table-container-dense" style={{ marginTop: "12px" }}>
              <table className="table-dense" style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th style={{ width: "110px" }}>मिति / समय</th>
                    <th style={{ width: "130px" }}>भौचर नं (Ref No)</th>
                    <th style={{ width: "70px", textAlign: "center" }}>साइज</th>
                    <th style={{ width: "130px" }}>प्रकार (Type)</th>
                    <th style={{ width: "85px", textAlign: "right" }}>दाखिला (+ जोर)</th>
                    <th style={{ width: "85px", textAlign: "right" }}>निकासी (- जोर)</th>
                    <th style={{ width: "95px", textAlign: "right" }}>बाँकी (Balance)</th>
                    <th style={{ width: "110px" }}>कर्मचारी (Operator)</th>
                    <th style={{ minWidth: "150px" }}>विवरण / कारण</th>
                    {canReverse && <th style={{ width: "75px", textAlign: "center" }}>कार्य</th>}
                  </tr>
                </thead>
                <tbody>
                  {movements.map((m) => {
                    const isReversed = movements.some((other) => other.reversal_of_id === m.id);
                    const isReversalItself = m.movement_type === "VOID_REVERSAL";
                    const isEligibleForReversal = canReverse && !isReversed && !isReversalItself;

                    return (
                      <tr
                        key={m.id}
                        style={{
                          background: isReversed ? "#F8FAFC" : "#FFFFFF",
                          opacity: isReversed ? 0.75 : 1
                        }}
                      >
                        {/* Date / Time */}
                        <td style={{ fontSize: "11px", whiteSpace: "nowrap" }}>
                          <div>{m.date_ad}</div>
                          {m.created_at && (
                            <div style={{ fontSize: "10px", color: "#64748B" }}>
                              {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          )}
                        </td>

                        {/* Ref No with Deep-Link Inspection */}
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button
                            type="button"
                            onClick={() => setInspectDoc(m)}
                            title="Click to view full voucher detail"
                            style={{
                              background: "none",
                              border: "none",
                              padding: 0,
                              color: "#1E3A8A",
                              fontWeight: "700",
                              fontSize: "11.5px",
                              fontFamily: "monospace",
                              cursor: "pointer",
                              textDecoration: "underline",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px"
                            }}
                          >
                            {m.source_doc_ref || `MOV-${m.id}`}
                            <ExternalLink size={10} color="#1E3A8A" />
                          </button>
                          {isReversed && (
                            <span
                              style={{
                                fontSize: "9.5px",
                                color: "#991B1B",
                                marginLeft: "4px",
                                fontWeight: "700"
                              }}
                            >
                              (रद्द)
                            </span>
                          )}
                        </td>

                        {/* Size */}
                        <td style={{ textAlign: "center", fontWeight: "700", fontSize: "11.5px" }}>
                          {m.size || "-"}
                        </td>

                        {/* High-Contrast Badge */}
                        <td>{renderMovementBadge(m.movement_type)}</td>

                        {/* In (+ जोर) */}
                        <td
                          className="num-mono"
                          style={{
                            textAlign: "right",
                            fontVariantNumeric: "tabular-nums",
                            color: m.qty_in > 0 ? "#059669" : "#94A3B8",
                            fontWeight: m.qty_in > 0 ? "700" : "400"
                          }}
                        >
                          {m.qty_in > 0 ? `+${m.qty_in}` : "-"}
                        </td>

                        {/* Out (- जोर) */}
                        <td
                          className="num-mono"
                          style={{
                            textAlign: "right",
                            fontVariantNumeric: "tabular-nums",
                            color: m.qty_out > 0 ? "#DC2626" : "#94A3B8",
                            fontWeight: m.qty_out > 0 ? "700" : "400"
                          }}
                        >
                          {m.qty_out > 0 ? `-${m.qty_out}` : "-"}
                        </td>

                        {/* Running Balance */}
                        <td
                          className="num-mono-bold"
                          style={{
                            textAlign: "right",
                            fontVariantNumeric: "tabular-nums",
                            fontWeight: "700",
                            color: "#0F172A",
                            background: "#F8FAFC"
                          }}
                        >
                          {m.running_balance.toLocaleString()}
                        </td>

                        {/* Operator */}
                        <td style={{ fontSize: "11px", color: "#334155", whiteSpace: "nowrap" }}>
                          {m.actor_name || "System"}
                        </td>

                        {/* Reason / Notes */}
                        <td style={{ fontSize: "11.5px", color: "#475569" }}>
                          {m.reason_code && (
                            <span
                              style={{
                                background: "#E2E8F0",
                                color: "#0F172A",
                                padding: "1px 4px",
                                borderRadius: "2px",
                                fontSize: "10px",
                                fontWeight: "600",
                                marginRight: "4px"
                              }}
                            >
                              {m.reason_code}
                            </span>
                          )}
                          <span>{m.reason_text || m.notes || "-"}</span>
                        </td>

                        {/* Reversal Action */}
                        {canReverse && (
                          <td style={{ textAlign: "center" }}>
                            {isEligibleForReversal ? (
                              <button
                                type="button"
                                onClick={() => setReversingMovement(m)}
                                title="Reverse this movement record"
                                style={{
                                  background: "#FEF2F2",
                                  border: "1px solid #FCA5A5",
                                  color: "#991B1B",
                                  borderRadius: "3px",
                                  padding: "2px 6px",
                                  fontSize: "10.5px",
                                  fontWeight: "700",
                                  cursor: "pointer",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px"
                                }}
                              >
                                <RotateCcw size={10} /> रद्द
                              </button>
                            ) : (
                              <span style={{ fontSize: "10px", color: "#94A3B8" }}>-</span>
                            )}
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* MODAL: DEEP-LINK VOUCHER INSPECTION */}
        {inspectDoc && (
          <div
            className="modal-overlay"
            role="presentation"
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15, 23, 42, 0.7)",
              zIndex: 10005,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "20px"
            }}
            onClick={(e) => {
              if (e.target === e.currentTarget) setInspectDoc(null);
            }}
          >
            <div
              className="glass-card"
              role="dialog"
              aria-modal="true"
              style={{
                width: "100%",
                maxWidth: "520px",
                background: "#FFFFFF",
                border: "2px solid #1E3A8A",
                borderRadius: "4px",
                boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
                overflow: "hidden"
              }}
            >
              <div
                style={{
                  background: "#1E3A8A",
                  color: "#FFFFFF",
                  padding: "12px 16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <FileText size={16} />
                  <span style={{ fontWeight: "700", fontSize: "13.5px" }}>
                    स्टक भौचर विवरण (Stock Voucher Inspection)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setInspectDoc(null)}
                  style={{ background: "none", border: "none", color: "#FFFFFF", cursor: "pointer" }}
                >
                  <X size={16} />
                </button>
              </div>

              <div style={{ padding: "16px 20px", fontSize: "12.5px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "8px 12px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
                  <div style={{ color: "#64748B", fontWeight: "600" }}>भौचर नं (Ref No):</div>
                  <div style={{ fontWeight: "700", color: "#0F172A", fontFamily: "monospace" }}>
                    {inspectDoc.source_doc_ref || `MOV-${inspectDoc.id}`}
                  </div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>कारोबार प्रकार:</div>
                  <div>{renderMovementBadge(inspectDoc.movement_type)}</div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>उत्पादन / जुत्ता:</div>
                  <div style={{ fontWeight: "600", color: "#0F172A" }}>
                    {inspectDoc.product_name} ({inspectDoc.product_code})
                  </div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>साइज (Size):</div>
                  <div style={{ fontWeight: "700", color: "#0F172A" }}>
                    {inspectDoc.size || "All Sizes"}
                  </div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>परिमाण (Qty):</div>
                  <div className="num-mono-bold" style={{ fontWeight: "700", color: inspectDoc.direction === 1 ? "#059669" : "#DC2626" }}>
                    {inspectDoc.direction === 1 ? `+${inspectDoc.quantity}` : `-${inspectDoc.quantity}`} जोर (pairs)
                  </div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>वेयरहाउस:</div>
                  <div style={{ color: "#0F172A" }}>{inspectDoc.warehouse_name}</div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>मिति (AD / BS):</div>
                  <div style={{ color: "#0F172A" }}>
                    {inspectDoc.date_ad} {inspectDoc.date_bs ? `(${inspectDoc.date_bs})` : ""}
                  </div>

                  <div style={{ color: "#64748B", fontWeight: "600" }}>प्रविष्टि कर्मचारी:</div>
                  <div style={{ color: "#0F172A" }}>{inspectDoc.actor_name} (ID: #{inspectDoc.actor_id})</div>

                  {inspectDoc.reason_code && (
                    <>
                      <div style={{ color: "#64748B", fontWeight: "600" }}>कारण कोड:</div>
                      <div style={{ fontWeight: "700", color: "#0F172A" }}>{inspectDoc.reason_code}</div>
                    </>
                  )}

                  <div style={{ color: "#64748B", fontWeight: "600" }}>कैफियत (Notes):</div>
                  <div style={{ color: "#334155" }}>{inspectDoc.reason_text || inspectDoc.notes || "None"}</div>
                </div>

                <div style={{ marginTop: "14px", display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    onClick={() => setInspectDoc(null)}
                    className="btn-primary"
                    style={{ padding: "6px 14px", fontSize: "12px" }}
                  >
                    बन्द गर्नुहोस् (Close)
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* MODAL: CONFIRM VOID REVERSAL */}
        {reversingMovement && (
          <div
            className="modal-overlay"
            role="presentation"
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15, 23, 42, 0.7)",
              zIndex: 10006,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "20px"
            }}
            onClick={(e) => {
              if (e.target === e.currentTarget && !reversalLoading) setReversingMovement(null);
            }}
          >
            <div
              className="glass-card"
              role="dialog"
              aria-modal="true"
              style={{
                width: "100%",
                maxWidth: "460px",
                background: "#FFFFFF",
                border: "2px solid #EF4444",
                borderRadius: "4px",
                boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
                padding: "20px"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px", color: "#991B1B" }}>
                <AlertTriangle size={22} color="#DC2626" />
                <h3 style={{ margin: 0, fontSize: "15px", fontWeight: "700" }}>
                  स्टक कारोबार रद्द पुष्टि (Confirm Void Reversal)
                </h3>
              </div>

              <p style={{ fontSize: "12.5px", color: "#334155", lineHeight: "1.5", margin: "0 0 14px" }}>
                के तपाईं साच्चिकै भौचर <strong>#{reversingMovement.id}</strong> (
                {reversingMovement.source_doc_ref || reversingMovement.movement_type}) लाई रद्द (VOID) गर्न चाहनुहुन्छ?
              </p>

              <div
                style={{
                  background: "#FEF2F2",
                  border: "1px solid #FCA5A5",
                  padding: "10px 12px",
                  borderRadius: "3px",
                  fontSize: "12px",
                  color: "#7F1D1D",
                  marginBottom: "16px"
                }}
              >
                <div>साइज: <strong>{reversingMovement.size || "N/A"}</strong></div>
                <div>रद्द हुने परिमाण: <strong>{reversingMovement.quantity} जोर</strong></div>
                <div>
                  प्रभाव:{" "}
                  <strong>
                    {reversingMovement.direction === 1
                      ? `मौज्दात घट्नेछ (-${reversingMovement.quantity})`
                      : `मौज्दात थपिनेछ (+${reversingMovement.quantity})`}
                  </strong>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
                <button
                  type="button"
                  disabled={reversalLoading}
                  onClick={() => setReversingMovement(null)}
                  style={{
                    background: "#F1F5F9",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    padding: "6px 12px",
                    fontSize: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                    color: "#475569"
                  }}
                >
                  रद्द नगर्नुहोस् (Cancel)
                </button>
                <button
                  type="button"
                  disabled={reversalLoading}
                  onClick={handleExecuteReversal}
                  style={{
                    background: "#DC2626",
                    border: "none",
                    borderRadius: "3px",
                    padding: "6px 14px",
                    fontSize: "12px",
                    fontWeight: "700",
                    cursor: "pointer",
                    color: "#FFFFFF",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px"
                  }}
                >
                  {reversalLoading ? "प्रक्रियामा..." : "रद्द निश्चित गर्नुहोस् (Confirm Void)"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
