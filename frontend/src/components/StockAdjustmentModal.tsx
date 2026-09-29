"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  X,
  Sliders,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Layers,
  Warehouse as WarehouseIcon,
  RefreshCw
} from "lucide-react";
import { useLocale } from "../context/LocaleContext";

interface ProductOption {
  id: number;
  code: string;
  name: string;
  category?: string;
  size?: string;
  color?: string;
  current_stock_pairs?: number;
}

interface WarehouseOption {
  id: number;
  name: string;
  code: string;
}

interface StockAdjustmentModalProps {
  userRole?: string;
  preselectedProduct?: ProductOption | null;
  onClose: () => void;
  onSuccess: (updatedProductCode?: string) => void;
}

const PARIS_POINTS = [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43];

export function StockAdjustmentModal({
  userRole,
  preselectedProduct,
  onClose,
  onSuccess
}: StockAdjustmentModalProps) {
  const { locale, isNepali } = useLocale();

  const reasonCodes = useMemo(() => [
    {
      code: "RECOUNT_CORRECTION",
      label: locale === "en" ? "Recount Correction" : "गणना संशोधन (Recount Correction)",
      requiresSupervisor: false
    },
    {
      code: "DAMAGED",
      label: locale === "en" ? "Damaged / Broken" : "क्षतिग्रस्त / बिग्रेको (Damaged / Broken)",
      requiresSupervisor: true
    },
    {
      code: "SAMPLE_ISSUE",
      label: locale === "en" ? "Sample Issue" : "नमुना निकासी (Sample Issue)",
      requiresSupervisor: true
    },
    {
      code: "THEFT_LOSS",
      label: locale === "en" ? "Theft / Pilferage Loss" : "हराएको / अपचलन (Theft / Pilferage Loss)",
      requiresSupervisor: true
    },
    {
      code: "SCRAP",
      label: locale === "en" ? "Factory Scrap / Reject" : "कारखाना स्क्र्याप (Factory Scrap / Reject)",
      requiresSupervisor: true
    },
    {
      code: "OTHER",
      label: locale === "en" ? "Other (Specify in Notes)" : "अन्य - खुलाउनु पर्ने (Other - Specify in Notes)",
      requiresSupervisor: true
    }
  ], [locale]);

  // If user is a viewer or viewer_demo, reject rendering immediately
  const isViewer = userRole === "viewer" || userRole === "viewer_demo";

  const [products, setProducts] = useState<ProductOption[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseOption[]>([]);
  const [loadingInitial, setLoadingInitial] = useState(true);

  // Form State
  const [selectedProductId, setSelectedProductId] = useState<number | null>(preselectedProduct ? preselectedProduct.id : null);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number>(1);
  const [selectedSize, setSelectedSize] = useState<string>(preselectedProduct?.size || "40");
  const [action, setAction] = useState<"add" | "reduce">("add");
  const [quantity, setQuantity] = useState<string>("1");
  const [reasonCode, setReasonCode] = useState<string>("RECOUNT_CORRECTION");
  const [reasonText, setReasonText] = useState<string>("");
  const [supervisorToken, setSupervisorToken] = useState<string>("");

  // Live Balance Check
  const [currentBalance, setCurrentBalance] = useState<number>(0);
  const [fetchingBalance, setFetchingBalance] = useState<boolean>(false);

  // UI state
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load products & warehouses
  useEffect(() => {
    let isMounted = true;
    async function loadData() {
      try {
        const [prodRes, whRes] = await Promise.all([
          fetch("/api/v1/stock/balance"),
          fetch("/api/v1/stock/warehouses")
        ]);

        if (prodRes.ok && isMounted) {
          const prodData = await prodRes.json();
          setProducts(prodData || []);
          if (!selectedProductId && prodData.length > 0) {
            setSelectedProductId(prodData[0].id);
            if (prodData[0].size) setSelectedSize(prodData[0].size);
          }
        }

        if (whRes.ok && isMounted) {
          const whData = await whRes.json();
          setWarehouses(whData || []);
          if (whData.length > 0) {
            setSelectedWarehouseId(whData[0].id);
          }
        }
      } catch (e) {
        console.error("Failed to load initial adjustment data", e);
      } finally {
        if (isMounted) setLoadingInitial(false);
      }
    }
    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch current on-hand balance for selected product, warehouse, and size
  useEffect(() => {
    if (!selectedProductId) return;

    let isMounted = true;
    async function checkStock() {
      setFetchingBalance(true);
      try {
        const res = await fetch(`/api/v1/stock/ledger?product_id=${selectedProductId}&warehouse_id=${selectedWarehouseId}&size=${selectedSize}&limit=1`);
        if (res.ok && isMounted) {
          const data = await res.json();
          if (data.items && data.items.length > 0) {
            setCurrentBalance(data.items[0].running_balance || 0);
          } else {
            // Check fallback from product list
            const currentP = products.find((p) => p.id === selectedProductId);
            setCurrentBalance(currentP?.current_stock_pairs || 0);
          }
        }
      } catch {
        if (isMounted) setCurrentBalance(0);
      } finally {
        if (isMounted) setFetchingBalance(false);
      }
    }
    checkStock();
    return () => {
      isMounted = false;
    };
  }, [selectedProductId, selectedWarehouseId, selectedSize, products]);

  // Projected Balance Math
  const parsedQty = Math.max(0, parseInt(quantity, 10) || 0);
  const delta = action === "add" ? parsedQty : -parsedQty;
  const projectedBalance = currentBalance + delta;
  const isFloorViolated = action === "reduce" && projectedBalance < 0;

  // Supervisor token necessity
  const requiresSupervisor =
    action === "reduce" &&
    reasonCode !== "RECOUNT_CORRECTION" &&
    userRole !== "admin";

  // Form Validation
  const isFormValid = useMemo(() => {
    if (!selectedProductId || parsedQty <= 0) return false;
    if (isFloorViolated) return false;
    if (action === "reduce" || reasonCode === "OTHER") {
      if (!reasonText.trim()) return false;
    }
    if (requiresSupervisor && !supervisorToken.trim()) return false;
    return true;
  }, [selectedProductId, parsedQty, isFloorViolated, action, reasonCode, reasonText, requiresSupervisor, supervisorToken]);

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || submitting) return;

    setSubmitting(true);
    setError(null);

    try {
      const payload = {
        product_id: selectedProductId,
        warehouse_id: selectedWarehouseId,
        size: selectedSize,
        quantity_delta: delta,
        reason_code: reasonCode,
        reason_text: reasonText.trim() || undefined,
        supervisor_token: requiresSupervisor ? supervisorToken.trim() : undefined
      };

      const res = await fetch("/api/v1/stock/adjustments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || (locale === "en" ? "Stock adjustment failed" : "स्टक मिलान असफल भयो (Stock adjustment failed)"));
      }

      const activeProduct = products.find((p) => p.id === selectedProductId);
      onSuccess(activeProduct?.code);
      onClose();
    } catch (e: any) {
      setError(e.message || "Failed to submit adjustment");
    } finally {
      setSubmitting(false);
    }
  };

  // If viewer, safeguard: do not mount the drawer at all
  if (isViewer) {
    return null;
  }

  return (
    <div
      className="modal-overlay"
      role="presentation"
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        zIndex: 10000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px"
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
    >
      <div
        className="modal-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="adj-modal-title"
        style={{
          width: "100%",
          maxWidth: "580px",
          background: "#FFFFFF",
          border: "2px solid #1E3A8A",
          borderRadius: "4px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {/* HEADER */}
        <div
          style={{
            background: "#1E3A8A",
            color: "#FFFFFF",
            padding: "12px 18px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Sliders size={18} />
            <h2 id="adj-modal-title" style={{ fontSize: "15px", fontWeight: "700", margin: 0 }}>
              {locale === "en" ? "Controlled Stock Adjustment" : "नियन्त्रित स्टक मिलान (Controlled Stock Adjustment)"}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close adjustment modal"
            style={{
              background: "none",
              border: "none",
              color: "#FFFFFF",
              cursor: "pointer",
              display: "flex",
              alignItems: "center"
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* ERROR BANNER */}
        {error && (
          <div
            role="alert"
            style={{
              background: "#FEF2F2",
              borderBottom: "1px solid #EF4444",
              padding: "10px 18px",
              color: "#991B1B",
              fontSize: "12.5px",
              display: "flex",
              alignItems: "center",
              gap: "8px"
            }}
          >
            <AlertTriangle size={16} color="#DC2626" />
            <span>{error}</span>
          </div>
        )}

        {/* FORM BODY */}
        <form onSubmit={handleSubmit} style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: "14px" }}>
          {/* Article / Product Selection */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
              {locale === "en" ? "Footwear Article SKU *" : "जुत्ता मोडल / आर्टिकल (Footwear Article SKU) *"}
            </label>
            <select
              value={selectedProductId || ""}
              onChange={(e) => {
                const pId = Number(e.target.value);
                setSelectedProductId(pId);
                const p = products.find((item) => item.id === pId);
                if (p && p.size) setSelectedSize(p.size);
              }}
              disabled={submitting || loadingInitial}
              className="input-field"
              style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", fontWeight: "500" }}
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} [{p.code}] - Size {p.size || "Multi"} ({p.current_stock_pairs ?? 0} pairs)
                </option>
              ))}
            </select>
          </div>

          {/* Warehouse and Size Row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
                {locale === "en" ? "Warehouse *" : "वेयरहाउस (Warehouse) *"}
              </label>
              <select
                value={selectedWarehouseId}
                onChange={(e) => setSelectedWarehouseId(Number(e.target.value))}
                disabled={submitting}
                className="input-field"
                style={{ width: "100%", padding: "6px 8px", fontSize: "12px" }}
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
                {locale === "en" ? "Size (Sizes 32–43) *" : "साइज (Size 32–43) *"}
              </label>
              <select
                value={selectedSize}
                onChange={(e) => setSelectedSize(e.target.value)}
                disabled={submitting}
                className="input-field"
                style={{ width: "100%", padding: "6px 8px", fontSize: "12px", fontWeight: "700" }}
              >
                {PARIS_POINTS.map((sz) => (
                  <option key={sz} value={String(sz)}>
                    {locale === "en" ? `Size ${sz} (Paris Point)` : `साइज ${sz} (Paris Point)`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Action Radio Selection: Add vs Reduce */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "6px" }}>
              {locale === "en" ? "Adjustment Action *" : "मिलान कार्य (Adjustment Action) *"}
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <label
                style={{
                  border: action === "add" ? "2px solid #059669" : "1px solid #CBD5E1",
                  background: action === "add" ? "#ECFDF5" : "#FFFFFF",
                  borderRadius: "4px",
                  padding: "8px 12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer"
                }}
              >
                <input
                  type="radio"
                  name="action_type"
                  value="add"
                  checked={action === "add"}
                  onChange={() => setAction("add")}
                  disabled={submitting}
                />
                <div>
                  <div style={{ fontSize: "12.5px", fontWeight: "700", color: "#065F46" }}>
                    {locale === "en" ? "Add Stock (+)" : "बढोत्तरी (Add Stock / +)"}
                  </div>
                  <div style={{ fontSize: "10.5px", color: "#64748B" }}>
                    {locale === "en" ? "Physical recount surplus, found inventory" : "गणना थप, भौतिक फेला"}
                  </div>
                </div>
              </label>

              <label
                style={{
                  border: action === "reduce" ? "2px solid #DC2626" : "1px solid #CBD5E1",
                  background: action === "reduce" ? "#FEF2F2" : "#FFFFFF",
                  borderRadius: "4px",
                  padding: "8px 12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  cursor: "pointer"
                }}
              >
                <input
                  type="radio"
                  name="action_type"
                  value="reduce"
                  checked={action === "reduce"}
                  onChange={() => setAction("reduce")}
                  disabled={submitting}
                />
                <div>
                  <div style={{ fontSize: "12.5px", fontWeight: "700", color: "#991B1B" }}>
                    {locale === "en" ? "Reduce Stock (-)" : "घटबढ / हानी (Reduce Stock / -)"}
                  </div>
                  <div style={{ fontSize: "10.5px", color: "#64748B" }}>
                    {locale === "en" ? "Damage, sample issue, theft, scrap" : "क्षति, नमुना, हराएको, स्क्र्याप"}
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Quantity & Reason Code Row */}
          <div style={{ display: "grid", gridTemplateColumns: "130px 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
                {locale === "en" ? "Quantity (Pairs) *" : "जोर परिमाण (Pairs) *"}
              </label>
              <input
                type="number"
                min="1"
                step="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                disabled={submitting}
                className="input-field num-mono-bold"
                style={{ width: "100%", padding: "6px 8px", fontSize: "13px" }}
                required
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
                {locale === "en" ? "Reason Code *" : "कारण कोड (Reason Code) *"}
              </label>
              <select
                value={reasonCode}
                onChange={(e) => setReasonCode(e.target.value)}
                disabled={submitting}
                className="input-field"
                style={{ width: "100%", padding: "6px 8px", fontSize: "12px" }}
              >
                {reasonCodes.map((r) => (
                  <option key={r.code} value={r.code}>
                    {r.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Supervisor Authorization Token (Rendered only when reducing stock with non-recount by non-admin) */}
          {requiresSupervisor && (
            <div
              style={{
                background: "#FFFBEB",
                border: "1px solid #F59E0B",
                borderRadius: "4px",
                padding: "10px 12px"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#92400E", fontSize: "12px", fontWeight: "700", marginBottom: "4px" }}>
                <Lock size={14} />
                <span>
                  {locale === "en"
                    ? "Supervisor Authorization Token *"
                    : "सुपरभाइजर प्रमाणीकरण टोकन (Supervisor Authorization Token) *"}
                </span>
              </div>
              <p style={{ fontSize: "11px", color: "#78350F", margin: "0 0 6px" }}>
                {locale === "en"
                  ? "Administrator privilege or valid supervisor token required for stock reduction."
                  : "स्टक हानी/क्षति घटबढका लागि एड्मिन अधिकार वा सुपरभाइजर टोकन अनिवार्य छ।"}
              </p>
              <input
                type="password"
                placeholder={locale === "en" ? "Enter Supervisor Token / Admin Password" : "सुपरभाइजर टोकन वा एड्मिन पासवर्ड"}
                value={supervisorToken}
                onChange={(e) => setSupervisorToken(e.target.value)}
                disabled={submitting}
                className="input-field"
                style={{ width: "100%", padding: "6px 8px", fontSize: "12px", background: "#FFFFFF" }}
                required
              />
            </div>
          )}

          {/* Reason Text / Justification */}
          <div>
            <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#0F172A", marginBottom: "4px" }}>
              {locale === "en"
                ? `Reason Text / Audit Notes ${action === "reduce" || reasonCode === "OTHER" ? "*" : "(Optional)"}`
                : `विवरण / कैफियत (Reason Text / Audit Notes) ${action === "reduce" || reasonCode === "OTHER" ? "*" : "(ऐच्छिक)"}`}
            </label>
            <input
              type="text"
              placeholder={locale === "en" ? "e.g., Physical floor audit mismatch, wet sole damaged in monsoon rack" : "जस्तै: भौतिक गणना फरक, वर्षामा सोल बिग्रिएको"}
              value={reasonText}
              onChange={(e) => setReasonText(e.target.value)}
              disabled={submitting}
              className="input-field"
              style={{ width: "100%", padding: "6px 8px", fontSize: "12px" }}
              required={action === "reduce" || reasonCode === "OTHER"}
            />
          </div>

          {/* LIVE BALANCE VS PROJECTED BALANCE CALLOUT */}
          <div
            style={{
              background: isFloorViolated ? "#FEF2F2" : "#F8FAFC",
              border: isFloorViolated ? "2px solid #DC2626" : "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "10px 14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}
          >
            <div>
              <div style={{ fontSize: "11px", color: "#475569", fontWeight: "600", textTransform: "uppercase" }}>
                {locale === "en" ? "Current Stock" : "हालको मौज्दात (Current)"}
              </div>
              <div className="num-mono-bold" style={{ fontSize: "16px", color: "#0F172A" }}>
                {fetchingBalance ? "..." : currentBalance} {locale === "en" ? "pairs" : "जोर"}
              </div>
            </div>

            <div style={{ fontSize: "18px", color: "#94A3B8" }}>→</div>

            <div>
              <div style={{ fontSize: "11px", color: "#475569", fontWeight: "600", textTransform: "uppercase" }}>
                {locale === "en" ? "Adjustment" : "मिलान (Adjustment)"}
              </div>
              <div
                className="num-mono-bold"
                style={{ fontSize: "16px", color: action === "add" ? "#059669" : "#DC2626" }}
              >
                {action === "add" ? `+${parsedQty}` : `-${parsedQty}`} {locale === "en" ? "pairs" : "जोर"}
              </div>
            </div>

            <div style={{ fontSize: "18px", color: "#94A3B8" }}>=</div>

            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "11px", color: isFloorViolated ? "#991B1B" : "#475569", fontWeight: "700", textTransform: "uppercase" }}>
                {locale === "en" ? "Projected Stock" : "प्रक्षेपित मौज्दात (Projected)"}
              </div>
              <div
                className="num-mono-bold"
                style={{
                  fontSize: "17px",
                  fontWeight: "700",
                  color: isFloorViolated ? "#DC2626" : "#1E3A8A"
                }}
              >
                {projectedBalance} {locale === "en" ? "pairs" : "जोर"}
              </div>
            </div>
          </div>

          {/* Zero Floor Error Alert */}
          {isFloorViolated && (
            <div
              role="alert"
              style={{
                background: "#FEF2F2",
                border: "1px solid #EF4444",
                borderRadius: "3px",
                padding: "8px 12px",
                color: "#991B1B",
                fontSize: "12px",
                fontWeight: "600",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <AlertTriangle size={15} color="#DC2626" />
              <span>
                {locale === "en"
                  ? `Rejected: Stock balance cannot be negative (Projected: ${projectedBalance} pairs).`
                  : `अस्वीकृत (Rejected): स्टक मौज्दात ऋणात्मक (Negative: ${projectedBalance}) हुन पाउँदैन।`}
              </span>
            </div>
          )}

          {/* ACTION BUTTONS */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              style={{
                background: "#F1F5F9",
                border: "1px solid #CBD5E1",
                borderRadius: "3px",
                padding: "7px 14px",
                fontSize: "12.5px",
                fontWeight: "600",
                cursor: "pointer",
                color: "#475569"
              }}
            >
              {locale === "en" ? "Cancel" : "रद्द गर्नुहोस् (Cancel)"}
            </button>
            <button
              type="submit"
              disabled={!isFormValid || submitting}
              className="btn-primary"
              style={{
                padding: "7px 18px",
                fontSize: "12.5px",
                opacity: !isFormValid || submitting ? 0.5 : 1,
                cursor: !isFormValid || submitting ? "not-allowed" : "pointer"
              }}
            >
              {submitting
                ? (locale === "en" ? "Submitting..." : "प्रविष्टि हुँदैछ...")
                : (locale === "en" ? "Submit Stock Adjustment" : "स्टक मिलान प्रविष्टि गर्नुहोस् (Submit Adjustment)")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
