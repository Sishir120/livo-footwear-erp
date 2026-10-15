"use client";

import React, { useState, useEffect } from "react";
import {
  DollarSign,
  Briefcase,
  Trash2,
  Plus,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Building2,
  Layers,
  Wrench,
  Truck,
  Zap,
  Coffee,
  Users,
  FileSpreadsheet
} from "lucide-react";
import { useLocale } from "@/context/LocaleContext";
import { fromPaisa, toPaisa, TABULAR_NUMS_STYLE } from "@/lib/currency";
import { NepaliDatePicker } from "./NepaliDatePicker";
import { adToBs, todayBs } from "@/lib/nepaliDate";

interface FactoryExpenseItem {
  id: number;
  company_id: number;
  expense_date_ad: string;
  expense_date_bs: string;
  particular: string;
  category: string;
  amount_paisa: number;
  payment_method: string;
  remarks?: string | null;
}

interface FixedAssetItem {
  id: number;
  company_id: number;
  asset_code: string;
  asset_name: string;
  category: string;
  purchase_date_ad: string;
  purchase_date_bs: string;
  purchase_cost_paisa: number;
  quantity: number;
  location?: string | null;
  remarks?: string | null;
}

interface WasteRecordItem {
  id: number;
  company_id: number;
  waste_date_ad: string;
  waste_date_bs: string;
  waste_type: "RAW_MATERIAL_SCRAP" | "FINISHED_PAIR_REJECT" | string;
  raw_material_id?: number | null;
  raw_material_name?: string | null;
  product_id?: number | null;
  product_name?: string | null;
  batch_id?: number | null;
  batch_number?: string | null;
  quantity: number;
  unit: string;
  reason?: string | null;
  disposal_method?: string | null;
}

interface ExpensesAssetsViewProps {
  userRole?: string;
}

export function ExpensesAssetsView({ userRole }: ExpensesAssetsViewProps) {
  const { locale } = useLocale();
  const [activeSubTab, setActiveSubTab] = useState<"expenses" | "assets" | "waste">("expenses");

  // Notifications
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ----------------------------------------------------
  // SUBTAB 1: FACTORY OPERATING EXPENSES
  // ----------------------------------------------------
  const [expenses, setExpenses] = useState<FactoryExpenseItem[]>([]);
  const [expenseTotalNpr, setExpenseTotalNpr] = useState<number>(0);
  const [loadingExpenses, setLoadingExpenses] = useState(false);
  const [expenseCategoryFilter, setExpenseCategoryFilter] = useState("ALL");
  const [showAddExpenseModal, setShowAddExpenseModal] = useState(false);

  // Expense form
  const [expDateAd, setExpDateAd] = useState(() => new Date().toISOString().split("T")[0]);
  const [expDateBs, setExpDateBs] = useState(() => {
    try { return todayBs().formatted; } catch { return "2083-01-01"; }
  });
  const [expParticular, setExpParticular] = useState("");
  const [expCategory, setExpCategory] = useState("ELECTRICITY_WATER");
  const [expAmountNpr, setExpAmountNpr] = useState("");
  const [expPaymentMethod, setExpPaymentMethod] = useState("CASH");
  const [expRemarks, setExpRemarks] = useState("");
  const [submittingExpense, setSubmittingExpense] = useState(false);

  const fetchExpenses = async () => {
    setLoadingExpenses(true);
    try {
      let url = "/api/v1/expenses/factory?limit=300";
      if (expenseCategoryFilter !== "ALL") {
        url += `&category=${encodeURIComponent(expenseCategoryFilter)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setExpenses(data.items || []);
        setExpenseTotalNpr(data.total_amount_npr || 0);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingExpenses(false);
    }
  };

  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expParticular.trim() || !expAmountNpr || Number(expAmountNpr) <= 0) {
      setErrorMsg(locale === "en" ? "Enter particular and valid amount" : "कृपया विवरण र रकम प्रविष्ट गर्नुहोस्");
      return;
    }
    setSubmittingExpense(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/expenses/factory", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          expense_date_ad: expDateAd,
          expense_date_bs: expDateBs,
          particular: expParticular.trim(),
          category: expCategory,
          amount_npr: Number(expAmountNpr),
          payment_method: expPaymentMethod,
          remarks: expRemarks.trim() || null
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Failed to save factory expense");
        return;
      }
      setSuccessMsg(locale === "en" ? "Operating expense recorded successfully!" : "सञ्चालन खर्च सुरक्षित भयो!");
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowAddExpenseModal(false);
      setExpParticular("");
      setExpAmountNpr("");
      setExpRemarks("");
      fetchExpenses();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to record expense");
    } finally {
      setSubmittingExpense(false);
    }
  };

  const handleDeleteExpense = async (id: number) => {
    if (!window.confirm(locale === "en" ? "Delete this expense entry?" : "के तपाईं यो खर्च मेटाउन चाहनुहुन्छ?")) return;
    try {
      const res = await fetch(`/api/v1/expenses/factory/${id}`, { method: "DELETE" });
      if (res.ok) {
        setSuccessMsg(locale === "en" ? "Expense deleted" : "खर्च विवरण मेटाइयो");
        setTimeout(() => setSuccessMsg(null), 3500);
        fetchExpenses();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // ----------------------------------------------------
  // SUBTAB 2: FIXED ASSETS REGISTER
  // ----------------------------------------------------
  const [assets, setAssets] = useState<FixedAssetItem[]>([]);
  const [assetTotalValuationNpr, setAssetTotalValuationNpr] = useState<number>(0);
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [assetCategoryFilter, setAssetCategoryFilter] = useState("ALL");
  const [showAddAssetModal, setShowAddAssetModal] = useState(false);

  // Asset form
  const [assetCode, setAssetCode] = useState("");
  const [assetName, setAssetName] = useState("");
  const [assetCategory, setAssetCategory] = useState("MACHINERY");
  const [assetDateAd, setAssetDateAd] = useState(() => new Date().toISOString().split("T")[0]);
  const [assetDateBs, setAssetDateBs] = useState(() => {
    try { return todayBs().formatted; } catch { return "2083-01-01"; }
  });
  const [assetCostNpr, setAssetCostNpr] = useState("");
  const [assetQuantity, setAssetQuantity] = useState("1");
  const [assetLocation, setAssetLocation] = useState("Pokhara Factory Main Floor");
  const [assetRemarks, setAssetRemarks] = useState("");
  const [submittingAsset, setSubmittingAsset] = useState(false);

  const fetchAssets = async () => {
    setLoadingAssets(true);
    try {
      let url = "/api/v1/fixed-assets?limit=300";
      if (assetCategoryFilter !== "ALL") {
        url += `&category=${encodeURIComponent(assetCategoryFilter)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setAssets(data.items || []);
        setAssetTotalValuationNpr(data.total_valuation_npr || 0);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAssets(false);
    }
  };

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assetCode.trim() || !assetName.trim() || !assetCostNpr) {
      setErrorMsg(locale === "en" ? "Enter asset code, name, and purchase cost" : "कृपया सम्पत्ति कोड, नाम र लागत भर्नुहोस्");
      return;
    }
    setSubmittingAsset(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/fixed-assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_code: assetCode.trim().toUpperCase(),
          asset_name: assetName.trim(),
          category: assetCategory,
          purchase_date_ad: assetDateAd,
          purchase_date_bs: assetDateBs,
          cost_npr: Number(assetCostNpr),
          quantity: parseInt(assetQuantity, 10) || 1,
          location: assetLocation.trim() || null,
          remarks: assetRemarks.trim() || null
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Failed to register fixed asset");
        return;
      }
      setSuccessMsg(locale === "en" ? "Fixed asset registered successfully!" : "स्थिर सम्पत्ति सफलतापूर्वक दर्ता भयो!");
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowAddAssetModal(false);
      setAssetCode("");
      setAssetName("");
      setAssetCostNpr("");
      setAssetRemarks("");
      fetchAssets();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to register fixed asset");
    } finally {
      setSubmittingAsset(false);
    }
  };

  const handleDeleteAsset = async (id: number) => {
    if (!window.confirm(locale === "en" ? "Delete this asset record?" : "के तपाईं यो सम्पत्ति मेटाउन चाहनुहुन्छ?")) return;
    try {
      const res = await fetch(`/api/v1/fixed-assets/${id}`, { method: "DELETE" });
      if (res.ok) {
        setSuccessMsg(locale === "en" ? "Asset record deleted" : "सम्पत्ति विवरण मेटाइयो");
        setTimeout(() => setSuccessMsg(null), 3500);
        fetchAssets();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // ----------------------------------------------------
  // SUBTAB 3: WASTE & SCRAP FLOOR LOG
  // ----------------------------------------------------
  const [wasteRecords, setWasteRecords] = useState<WasteRecordItem[]>([]);
  const [totalScrapKg, setTotalScrapKg] = useState<number>(0);
  const [totalRejectPairs, setTotalRejectPairs] = useState<number>(0);
  const [loadingWaste, setLoadingWaste] = useState(false);
  const [wasteTypeFilter, setWasteTypeFilter] = useState("ALL");
  const [showAddWasteModal, setShowAddWasteModal] = useState(false);

  // Waste form
  const [wasteDateAd, setWasteDateAd] = useState(() => new Date().toISOString().split("T")[0]);
  const [wasteDateBs, setWasteDateBs] = useState(() => {
    try { return todayBs().formatted; } catch { return "2083-01-01"; }
  });
  const [wasteType, setWasteType] = useState<"RAW_MATERIAL_SCRAP" | "FINISHED_PAIR_REJECT">("RAW_MATERIAL_SCRAP");
  const [wasteQuantity, setWasteQuantity] = useState("");
  const [wasteUnit, setWasteUnit] = useState("kg");
  const [wasteReason, setWasteReason] = useState("");
  const [wasteDisposalMethod, setWasteDisposalMethod] = useState("DISCARDED");
  const [submittingWaste, setSubmittingWaste] = useState(false);

  const fetchWaste = async () => {
    setLoadingWaste(true);
    try {
      let url = "/api/v1/waste?limit=300";
      if (wasteTypeFilter !== "ALL") {
        url += `&waste_type=${encodeURIComponent(wasteTypeFilter)}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setWasteRecords(data.items || []);
        setTotalScrapKg(data.total_raw_scrap_kg || 0);
        setTotalRejectPairs(data.total_reject_pairs || 0);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingWaste(false);
    }
  };

  const handleCreateWaste = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wasteQuantity || Number(wasteQuantity) <= 0) {
      setErrorMsg(locale === "en" ? "Enter valid scrap quantity" : "कृपया मान्य परिमाण प्रविष्ट गर्नुहोस्");
      return;
    }
    setSubmittingWaste(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/waste", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          waste_date_ad: wasteDateAd,
          waste_date_bs: wasteDateBs,
          waste_type: wasteType,
          quantity: Number(wasteQuantity),
          unit: wasteType === "FINISHED_PAIR_REJECT" ? "pair" : wasteUnit,
          reason: wasteReason.trim() || null,
          disposal_method: wasteDisposalMethod
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Failed to record scrap");
        return;
      }
      setSuccessMsg(locale === "en" ? "Waste/Scrap logged successfully!" : "फोहोर तथा स्क्र्याप दर्ता भयो!");
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowAddWasteModal(false);
      setWasteQuantity("");
      setWasteReason("");
      fetchWaste();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to log scrap");
    } finally {
      setSubmittingWaste(false);
    }
  };

  const handleDeleteWaste = async (id: number) => {
    if (!window.confirm(locale === "en" ? "Delete this scrap entry?" : "के तपाईं यो स्क्र्याप रेकर्ड मेटाउन चाहनुहुन्छ?")) return;
    try {
      const res = await fetch(`/api/v1/waste/${id}`, { method: "DELETE" });
      if (res.ok) {
        setSuccessMsg(locale === "en" ? "Scrap log deleted" : "स्क्र्याप रेकर्ड मेटाइयो");
        setTimeout(() => setSuccessMsg(null), 3500);
        fetchWaste();
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeSubTab === "expenses") fetchExpenses();
    if (activeSubTab === "assets") fetchAssets();
    if (activeSubTab === "waste") fetchWaste();
  }, [activeSubTab, expenseCategoryFilter, assetCategoryFilter, wasteTypeFilter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", background: "#1E3A8A", color: "#FFFFFF", borderRadius: "6px" }}>
              <Briefcase size={20} />
            </span>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "-0.01em" }}>
              {locale === "en"
                ? "Back-Office: Operating Expenses, Fixed Assets & Scrap Log"
                : "कारखाना सञ्चालन खर्च, स्थिर सम्पत्ति तथा स्क्र्याप रेकर्ड"}
            </h1>
          </div>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            {locale === "en"
              ? "Factory operating expenditure, capitalized equipment register, and manufacturing scrap monitoring."
              : "कारखानाको नियमित खर्च (भाडा, इन्धन, मर्मत), प्लान्ट मेसिनरी दर्ता, र उत्पादन फ्लोर स्क्र्याप अनुगमन।"}
          </p>
        </div>

        {/* Global Action / Refresh */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={() => {
              if (activeSubTab === "expenses") fetchExpenses();
              if (activeSubTab === "assets") fetchAssets();
              if (activeSubTab === "waste") fetchWaste();
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 12px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              fontSize: "12.5px",
              fontWeight: "600",
              color: "#334155",
              cursor: "pointer"
            }}
          >
            <RefreshCw size={14} className={loadingExpenses || loadingAssets || loadingWaste ? "animate-spin" : ""} />
            {locale === "en" ? "Refresh" : "ताजा गर्नुहोस्"}
          </button>

          {activeSubTab === "expenses" && userRole !== "viewer" && (
            <button
              type="button"
              id="btn-add-expense"
              onClick={() => setShowAddExpenseModal(true)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                background: "#1E3A8A",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "4px",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              <Plus size={16} />
              {locale === "en" ? "+ Record Expense" : "+ खर्च प्रविष्ट गर्नुहोस्"}
            </button>
          )}

          {activeSubTab === "assets" && userRole !== "viewer" && (
            <button
              type="button"
              id="btn-add-asset"
              onClick={() => setShowAddAssetModal(true)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                background: "#047857",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "4px",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              <Plus size={16} />
              {locale === "en" ? "+ Register Asset" : "+ नयाँ स्थिर सम्पत्ति थप्नुहोस्"}
            </button>
          )}

          {activeSubTab === "waste" && userRole !== "viewer" && (
            <button
              type="button"
              id="btn-add-waste"
              onClick={() => setShowAddWasteModal(true)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                background: "#BE123C",
                color: "#FFFFFF",
                border: "none",
                borderRadius: "4px",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer"
              }}
            >
              <Plus size={16} />
              {locale === "en" ? "+ Log Scrap / Reject" : "+ फोहोर/स्क्र्याप दर्ता"}
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", color: "#166534", padding: "10px 14px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <CheckCircle2 size={16} color="#16A34A" /> {successMsg}
        </div>
      )}
      {errorMsg && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", color: "#991B1B", padding: "10px 14px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <AlertCircle size={16} color="#DC2626" /> {errorMsg}
        </div>
      )}

      {/* Navigation Sub-Tabs */}
      <div style={{ display: "flex", borderBottom: "2px solid #CBD5E1", gap: "6px" }}>
        <button
          type="button"
          onClick={() => setActiveSubTab("expenses")}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeSubTab === "expenses" ? "3px solid #1E3A8A" : "3px solid transparent",
            background: activeSubTab === "expenses" ? "#EFF6FF" : "transparent",
            color: activeSubTab === "expenses" ? "#1E3A8A" : "#475569",
            cursor: "pointer",
            borderRadius: "4px 4px 0 0"
          }}
        >
          {locale === "en" ? "Factory Operating Expenses" : "कारखाना सञ्चालन खर्च (Operating Expenses)"}
        </button>
        <button
          type="button"
          onClick={() => setActiveSubTab("assets")}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeSubTab === "assets" ? "3px solid #047857" : "3px solid transparent",
            background: activeSubTab === "assets" ? "#F0FDF4" : "transparent",
            color: activeSubTab === "assets" ? "#047857" : "#475569",
            cursor: "pointer",
            borderRadius: "4px 4px 0 0"
          }}
        >
          {locale === "en" ? "Fixed Assets Register" : "स्थिर सम्पत्ति दर्ता (Fixed Assets)"}
        </button>
        <button
          type="button"
          onClick={() => setActiveSubTab("waste")}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeSubTab === "waste" ? "3px solid #BE123C" : "3px solid transparent",
            background: activeSubTab === "waste" ? "#FFF1F2" : "transparent",
            color: activeSubTab === "waste" ? "#BE123C" : "#475569",
            cursor: "pointer",
            borderRadius: "4px 4px 0 0"
          }}
        >
          {locale === "en" ? "Waste & Scrap Floor Log" : "फोहोर तथा स्क्र्याप रेकर्ड (Waste & Scrap)"}
        </button>
      </div>

      {/* --------------------------------------------------------------------- */}
      {/* TAB 1: OPERATING EXPENSES */}
      {/* --------------------------------------------------------------------- */}
      {activeSubTab === "expenses" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Summary Metric Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px" }}>
            <div style={{ background: "#FFFFFF", padding: "16px", borderRadius: "4px", border: "1px solid #CBD5E1", borderLeft: "4px solid #1E3A8A" }}>
              <div style={{ fontSize: "11.5px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>
                {locale === "en" ? "Total Operating Expenses" : "कुल सञ्चालन खर्च"}
              </div>
              <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
                NPR {expenseTotalNpr.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                {locale === "en" ? `${expenses.length} expense vouchers recorded` : `${expenses.length} खर्च भौचर दर्ता`}
              </div>
            </div>
          </div>

          {/* Filter Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#FFFFFF", padding: "10px 14px", borderRadius: "4px", border: "1px solid #CBD5E1", flexWrap: "wrap" }}>
            <Filter size={15} color="#64748B" />
            <span style={{ fontSize: "12px", fontWeight: "600", color: "#334155" }}>{locale === "en" ? "Category:" : "वर्ग:"}</span>
            {[
              "ALL",
              "FACTORY_RENT",
              "ELECTRICITY_WATER",
              "GENERATOR_FUEL",
              "MACHINE_MAINTENANCE",
              "OFFICE_SUPPLIES",
              "TEA_REFRESHMENT",
              "FACTORY_LABOR",
              "OTHER"
            ].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setExpenseCategoryFilter(cat)}
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  fontWeight: "600",
                  borderRadius: "3px",
                  border: "1px solid",
                  borderColor: expenseCategoryFilter === cat ? "#1E3A8A" : "#CBD5E1",
                  background: expenseCategoryFilter === cat ? "#EFF6FF" : "#FFFFFF",
                  color: expenseCategoryFilter === cat ? "#1E3A8A" : "#475569",
                  cursor: "pointer"
                }}
              >
                {cat.replace("_", " ")}
              </button>
            ))}
          </div>

          {/* Expenses Table */}
          <div style={{ background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1", overflow: "hidden" }}>
            <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "8px 12px", width: "50px" }}>S.N.</th>
                  <th style={{ padding: "8px 12px", width: "150px" }}>{locale === "en" ? "Date (BS / AD)" : "मिति (वि.सं / ई.सं)"}</th>
                  <th style={{ padding: "8px 12px" }}>{locale === "en" ? "Particular / Description" : "विवरण"}</th>
                  <th style={{ padding: "8px 12px", width: "160px" }}>{locale === "en" ? "Category" : "वर्ग"}</th>
                  <th style={{ padding: "8px 12px", width: "100px" }}>{locale === "en" ? "Payment" : "भुक्तानी"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "130px" }}>{locale === "en" ? "Amount (NPR)" : "रकम (रु)"}</th>
                  <th style={{ padding: "8px 12px", width: "140px" }}>{locale === "en" ? "Remarks" : "कैफियत"}</th>
                  {userRole !== "viewer" && <th style={{ padding: "8px 12px", width: "60px", textAlign: "center" }}>Action</th>}
                </tr>
              </thead>
              <tbody>
                {loadingExpenses ? (
                  <tr>
                    <td colSpan={8} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      <RefreshCw size={16} className="animate-spin" style={{ margin: "0 auto 6px" }} />
                      Loading expenses...
                    </td>
                  </tr>
                ) : expenses.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      No factory operating expenses found.
                    </td>
                  </tr>
                ) : (
                  expenses.map((exp, idx) => (
                    <tr key={exp.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                      <td className="num-mono" style={{ padding: "8px 12px", color: "#64748B" }}>{idx + 1}</td>
                      <td style={{ padding: "8px 12px", whiteSpace: "nowrap" }}>
                        <div style={{ fontWeight: "600", color: "#0F172A" }}>{exp.expense_date_bs} BS</div>
                        <div style={{ fontSize: "10px", color: "#64748B" }}>{exp.expense_date_ad} AD</div>
                      </td>
                      <td style={{ padding: "8px 12px", fontWeight: "600", color: "#0F172A" }}>{exp.particular}</td>
                      <td style={{ padding: "8px 12px" }}>
                        <span style={{ fontSize: "11px", fontWeight: "600", background: "#EFF6FF", color: "#1E3A8A", padding: "2px 6px", borderRadius: "3px", border: "1px solid #BFDBFE" }}>
                          {exp.category}
                        </span>
                      </td>
                      <td style={{ padding: "8px 12px" }}>
                        <span style={{ fontSize: "10.5px", fontWeight: "700", color: exp.payment_method === "BANK" ? "#1E40AF" : "#15803D" }}>
                          {exp.payment_method}
                        </span>
                      </td>
                      <td className="num-mono-bold" style={{ padding: "8px 12px", textAlign: "right", color: "#0F172A" }}>
                        {fromPaisa(exp.amount_paisa)}
                      </td>
                      <td style={{ padding: "8px 12px", color: "#64748B", fontSize: "11px" }}>{exp.remarks || "—"}</td>
                      {userRole !== "viewer" && (
                        <td style={{ padding: "8px 12px", textAlign: "center" }}>
                          <button
                            type="button"
                            onClick={() => handleDeleteExpense(exp.id)}
                            style={{ background: "none", border: "none", color: "#BE123C", cursor: "pointer", padding: "4px" }}
                            title="Delete Expense"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 2: FIXED ASSETS REGISTER */}
      {/* --------------------------------------------------------------------- */}
      {activeSubTab === "assets" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Summary Metric Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px" }}>
            <div style={{ background: "#FFFFFF", padding: "16px", borderRadius: "4px", border: "1px solid #CBD5E1", borderLeft: "4px solid #047857" }}>
              <div style={{ fontSize: "11.5px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>
                {locale === "en" ? "Capitalized Plant Valuation" : "स्थिर सम्पत्ति कुल मुल्यांकन"}
              </div>
              <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
                NPR {assetTotalValuationNpr.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                {locale === "en" ? `${assets.length} fixed asset entries` : `${assets.length} स्थिर सम्पत्ति रेकर्ड`}
              </div>
            </div>
          </div>

          {/* Filter Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#FFFFFF", padding: "10px 14px", borderRadius: "4px", border: "1px solid #CBD5E1", flexWrap: "wrap" }}>
            <Filter size={15} color="#64748B" />
            <span style={{ fontSize: "12px", fontWeight: "600", color: "#334155" }}>{locale === "en" ? "Asset Category:" : "सम्पत्ति वर्ग:"}</span>
            {["ALL", "MACHINERY", "MOULD", "VEHICLE", "TOOLS", "FURNITURE", "OTHER"].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setAssetCategoryFilter(cat)}
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  fontWeight: "600",
                  borderRadius: "3px",
                  border: "1px solid",
                  borderColor: assetCategoryFilter === cat ? "#047857" : "#CBD5E1",
                  background: assetCategoryFilter === cat ? "#F0FDF4" : "#FFFFFF",
                  color: assetCategoryFilter === cat ? "#047857" : "#475569",
                  cursor: "pointer"
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Assets Table */}
          <div style={{ background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1", overflow: "hidden" }}>
            <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "8px 12px", width: "90px" }}>{locale === "en" ? "Asset Code" : "कोड"}</th>
                  <th style={{ padding: "8px 12px" }}>{locale === "en" ? "Asset Description / Name" : "सम्पत्ति विवरण"}</th>
                  <th style={{ padding: "8px 12px", width: "120px" }}>{locale === "en" ? "Category" : "वर्ग"}</th>
                  <th style={{ padding: "8px 12px", width: "140px" }}>{locale === "en" ? "Acquisition Date" : "खरिद मिति"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "70px" }}>{locale === "en" ? "Qty" : "परिमाण"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "120px" }}>{locale === "en" ? "Unit Cost" : "प्रति एकाइ"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "130px" }}>{locale === "en" ? "Total Valuation" : "कुल लागत"}</th>
                  <th style={{ padding: "8px 12px", width: "150px" }}>{locale === "en" ? "Location / Plant" : "कारखाना स्थान"}</th>
                  {userRole !== "viewer" && <th style={{ padding: "8px 12px", width: "60px", textAlign: "center" }}>Action</th>}
                </tr>
              </thead>
              <tbody>
                {loadingAssets ? (
                  <tr>
                    <td colSpan={9} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      <RefreshCw size={16} className="animate-spin" style={{ margin: "0 auto 6px" }} />
                      Loading fixed assets...
                    </td>
                  </tr>
                ) : assets.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      No capital fixed assets registered.
                    </td>
                  </tr>
                ) : (
                  assets.map((asset) => (
                    <tr key={asset.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                      <td className="num-mono-bold" style={{ padding: "8px 12px", color: "#047857" }}>{asset.asset_code}</td>
                      <td style={{ padding: "8px 12px", fontWeight: "600", color: "#0F172A" }}>{asset.asset_name}</td>
                      <td style={{ padding: "8px 12px" }}>
                        <span style={{ fontSize: "10.5px", fontWeight: "700", background: "#F1F5F9", color: "#334155", padding: "2px 6px", borderRadius: "3px" }}>
                          {asset.category}
                        </span>
                      </td>
                      <td style={{ padding: "8px 12px", whiteSpace: "nowrap" }}>
                        <div style={{ fontWeight: "600", color: "#0F172A" }}>{asset.purchase_date_bs} BS</div>
                        <div style={{ fontSize: "10px", color: "#64748B" }}>{asset.purchase_date_ad} AD</div>
                      </td>
                      <td className="num-mono" style={{ padding: "8px 12px", textAlign: "right" }}>{asset.quantity}</td>
                      <td className="num-mono" style={{ padding: "8px 12px", textAlign: "right" }}>
                        {fromPaisa(asset.purchase_cost_paisa)}
                      </td>
                      <td className="num-mono-bold" style={{ padding: "8px 12px", textAlign: "right", color: "#0F172A" }}>
                        {fromPaisa(asset.purchase_cost_paisa * asset.quantity)}
                      </td>
                      <td style={{ padding: "8px 12px", color: "#475569", fontSize: "11px" }}>{asset.location || "—"}</td>
                      {userRole !== "viewer" && (
                        <td style={{ padding: "8px 12px", textAlign: "center" }}>
                          <button
                            type="button"
                            onClick={() => handleDeleteAsset(asset.id)}
                            style={{ background: "none", border: "none", color: "#BE123C", cursor: "pointer", padding: "4px" }}
                            title="Delete Asset"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* TAB 3: WASTE & SCRAP FLOOR LOG */}
      {/* --------------------------------------------------------------------- */}
      {activeSubTab === "waste" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Summary Metric Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "14px" }}>
            <div style={{ background: "#FFFFFF", padding: "16px", borderRadius: "4px", border: "1px solid #CBD5E1", borderLeft: "4px solid #D97706" }}>
              <div style={{ fontSize: "11.5px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>
                {locale === "en" ? "Raw Material Floor Scrap" : "कच्चा पदार्थ स्क्र्याप"}
              </div>
              <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
                {totalScrapKg.toFixed(2)} KG
              </div>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>Leather, rubber, synthetic cut-offs</div>
            </div>

            <div style={{ background: "#FFFFFF", padding: "16px", borderRadius: "4px", border: "1px solid #CBD5E1", borderLeft: "4px solid #BE123C" }}>
              <div style={{ fontSize: "11.5px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>
                {locale === "en" ? "Finished Footwear Rejects" : "तयारी जुत्ता रिजेक्ट (जोडी)"}
              </div>
              <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
                {totalRejectPairs.toFixed(0)} PAIRS
              </div>
              <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>Sole adhesion, stitching, finish defects</div>
            </div>
          </div>

          {/* Filter Bar */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", background: "#FFFFFF", padding: "10px 14px", borderRadius: "4px", border: "1px solid #CBD5E1", flexWrap: "wrap" }}>
            <Filter size={15} color="#64748B" />
            <span style={{ fontSize: "12px", fontWeight: "600", color: "#334155" }}>{locale === "en" ? "Scrap Type:" : "स्क्र्याप प्रकार:"}</span>
            {["ALL", "RAW_MATERIAL_SCRAP", "FINISHED_PAIR_REJECT"].map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setWasteTypeFilter(t)}
                style={{
                  padding: "4px 8px",
                  fontSize: "11px",
                  fontWeight: "600",
                  borderRadius: "3px",
                  border: "1px solid",
                  borderColor: wasteTypeFilter === t ? "#BE123C" : "#CBD5E1",
                  background: wasteTypeFilter === t ? "#FFF1F2" : "#FFFFFF",
                  color: wasteTypeFilter === t ? "#BE123C" : "#475569",
                  cursor: "pointer"
                }}
              >
                {t === "RAW_MATERIAL_SCRAP" ? "RAW MATERIAL SCRAP" : t === "FINISHED_PAIR_REJECT" ? "FINISHED PAIR REJECT" : "ALL"}
              </button>
            ))}
          </div>

          {/* Waste Table */}
          <div style={{ background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1", overflow: "hidden" }}>
            <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
              <thead>
                <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", textAlign: "left", color: "#475569" }}>
                  <th style={{ padding: "8px 12px", width: "50px" }}>S.N.</th>
                  <th style={{ padding: "8px 12px", width: "150px" }}>{locale === "en" ? "Date (BS / AD)" : "मिति"}</th>
                  <th style={{ padding: "8px 12px", width: "180px" }}>{locale === "en" ? "Waste Type" : "प्रकार"}</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", width: "120px" }}>{locale === "en" ? "Quantity" : "परिमाण"}</th>
                  <th style={{ padding: "8px 12px" }}>{locale === "en" ? "Reason / Quality Defect" : "कारण / कैफियत"}</th>
                  <th style={{ padding: "8px 12px", width: "140px" }}>{locale === "en" ? "Disposal Method" : "निकासी विधि"}</th>
                  {userRole !== "viewer" && <th style={{ padding: "8px 12px", width: "60px", textAlign: "center" }}>Action</th>}
                </tr>
              </thead>
              <tbody>
                {loadingWaste ? (
                  <tr>
                    <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      <RefreshCw size={16} className="animate-spin" style={{ margin: "0 auto 6px" }} />
                      Loading scrap logs...
                    </td>
                  </tr>
                ) : wasteRecords.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ padding: "24px", textAlign: "center", color: "#64748B" }}>
                      No scrap or reject records found.
                    </td>
                  </tr>
                ) : (
                  wasteRecords.map((w, idx) => (
                    <tr key={w.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                      <td className="num-mono" style={{ padding: "8px 12px", color: "#64748B" }}>{idx + 1}</td>
                      <td style={{ padding: "8px 12px", whiteSpace: "nowrap" }}>
                        <div style={{ fontWeight: "600", color: "#0F172A" }}>{w.waste_date_bs} BS</div>
                        <div style={{ fontSize: "10px", color: "#64748B" }}>{w.waste_date_ad} AD</div>
                      </td>
                      <td style={{ padding: "8px 12px" }}>
                        <span
                          style={{
                            fontSize: "10.5px",
                            fontWeight: "700",
                            padding: "2px 6px",
                            borderRadius: "3px",
                            background: w.waste_type === "RAW_MATERIAL_SCRAP" ? "#FEF3C7" : "#FEE2E2",
                            color: w.waste_type === "RAW_MATERIAL_SCRAP" ? "#B45309" : "#991B1B",
                            border: "1px solid",
                            borderColor: w.waste_type === "RAW_MATERIAL_SCRAP" ? "#FCD34D" : "#FCA5A5"
                          }}
                        >
                          {w.waste_type.replace("_", " ")}
                        </span>
                      </td>
                      <td className="num-mono-bold" style={{ padding: "8px 12px", textAlign: "right", color: "#0F172A" }}>
                        {w.quantity} {w.unit}
                      </td>
                      <td style={{ padding: "8px 12px", color: "#334155" }}>{w.reason || "—"}</td>
                      <td style={{ padding: "8px 12px" }}>
                        <span style={{ fontSize: "10.5px", fontWeight: "600", color: "#475569" }}>
                          {w.disposal_method || "DISCARDED"}
                        </span>
                      </td>
                      {userRole !== "viewer" && (
                        <td style={{ padding: "8px 12px", textAlign: "center" }}>
                          <button
                            type="button"
                            onClick={() => handleDeleteWaste(w.id)}
                            style={{ background: "none", border: "none", color: "#BE123C", cursor: "pointer", padding: "4px" }}
                            title="Delete Record"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* MODAL 1: RECORD EXPENSE */}
      {/* --------------------------------------------------------------------- */}
      {showAddExpenseModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "460px", padding: "24px", boxShadow: "0 10px 25px rgba(0,0,0,0.15)", border: "1px solid #CBD5E1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Record Operating Expense" : "कारखाना सञ्चालन खर्च प्रविष्ट गर्नुहोस्"}
              </h3>
              <button type="button" onClick={() => setShowAddExpenseModal(false)} style={{ background: "none", border: "none", fontSize: "18px", color: "#64748B", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleCreateExpense} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Expense Date (Bikram Sambat / AD) *" : "खर्च मिति (वि.सं / ई.सं) *"}
                </label>
                <NepaliDatePicker
                  valueAd={expDateAd}
                  compact
                  onChange={({ ad, bs }) => {
                    setExpDateAd(ad);
                    setExpDateBs(bs);
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Particulars / Description *" : "विवरण *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Generator Diesel 50L or Factory Electricity Bill"
                  value={expParticular}
                  onChange={(e) => setExpParticular(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Category *" : "खर्च वर्ग *"}
                  </label>
                  <select
                    value={expCategory}
                    onChange={(e) => setExpCategory(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF" }}
                  >
                    <option value="FACTORY_RENT">FACTORY RENT</option>
                    <option value="ELECTRICITY_WATER">ELECTRICITY & WATER</option>
                    <option value="GENERATOR_FUEL">GENERATOR FUEL</option>
                    <option value="MACHINE_MAINTENANCE">MACHINE MAINTENANCE</option>
                    <option value="OFFICE_SUPPLIES">OFFICE SUPPLIES</option>
                    <option value="TEA_REFRESHMENT">TEA & REFRESHMENT</option>
                    <option value="FACTORY_LABOR">FACTORY LABOR</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Payment Method *" : "भुक्तानी माध्यम *"}
                  </label>
                  <select
                    value={expPaymentMethod}
                    onChange={(e) => setExpPaymentMethod(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF" }}
                  >
                    <option value="CASH">CASH (नगद)</option>
                    <option value="BANK">BANK (बैंक)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Amount (NPR) *" : "रकम (नेपाली रुपैयाँ) *"}
                </label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="0.00"
                  value={expAmountNpr}
                  onChange={(e) => setExpAmountNpr(e.target.value)}
                  className="num-mono"
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Remarks / Bill No." : "कैफियत / बिल नं"}
                </label>
                <input
                  type="text"
                  placeholder="Optional bill or voucher reference"
                  value={expRemarks}
                  onChange={(e) => setExpRemarks(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddExpenseModal(false)}
                  style={{ padding: "8px 14px", fontSize: "12.5px", fontWeight: "600", background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", color: "#475569", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingExpense}
                  style={{ padding: "8px 18px", fontSize: "12.5px", fontWeight: "600", background: "#1E3A8A", border: "none", borderRadius: "4px", color: "#FFFFFF", cursor: submittingExpense ? "not-allowed" : "pointer" }}
                >
                  {submittingExpense ? "Recording..." : "Save Expense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* MODAL 2: REGISTER FIXED ASSET */}
      {/* --------------------------------------------------------------------- */}
      {showAddAssetModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "480px", padding: "24px", boxShadow: "0 10px 25px rgba(0,0,0,0.15)", border: "1px solid #CBD5E1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Register Capital Fixed Asset" : "स्थिर सम्पत्ति दर्ता गर्नुहोस्"}
              </h3>
              <button type="button" onClick={() => setShowAddAssetModal(false)} style={{ background: "none", border: "none", fontSize: "18px", color: "#64748B", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleCreateAsset} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Asset Code *" : "सम्पत्ति कोड *"}
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. MCH-SOLE-01"
                    value={assetCode}
                    onChange={(e) => setAssetCode(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", textTransform: "uppercase" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Category *" : "वर्ग *"}
                  </label>
                  <select
                    value={assetCategory}
                    onChange={(e) => setAssetCategory(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF" }}
                  >
                    <option value="MACHINERY">MACHINERY</option>
                    <option value="MOULD">MOULD (फर्मा/डाई)</option>
                    <option value="VEHICLE">VEHICLE (सवारी)</option>
                    <option value="TOOLS">TOOLS</option>
                    <option value="FURNITURE">FURNITURE</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Asset Name / Model Description *" : "सम्पत्ति विवरण / मोडल *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Hydraulic Sole Press Machine 50-Ton"
                  value={assetName}
                  onChange={(e) => setAssetName(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Acquisition Date (Bikram Sambat / AD) *" : "खरिद मिति *"}
                </label>
                <NepaliDatePicker
                  valueAd={assetDateAd}
                  compact
                  onChange={({ ad, bs }) => {
                    setAssetDateAd(ad);
                    setAssetDateBs(bs);
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Quantity *" : "संख्या *"}
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={assetQuantity}
                    onChange={(e) => setAssetQuantity(e.target.value)}
                    className="num-mono"
                    style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Unit Cost (NPR) *" : "प्रति एकाइ लागत (रु) *"}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="0.00"
                    value={assetCostNpr}
                    onChange={(e) => setAssetCostNpr(e.target.value)}
                    className="num-mono"
                    style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Factory Floor Location" : "कारखाना स्थान"}
                </label>
                <input
                  type="text"
                  placeholder="e.g. Pokhara Plant Floor 1 - Assembly Line A"
                  value={assetLocation}
                  onChange={(e) => setAssetLocation(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddAssetModal(false)}
                  style={{ padding: "8px 14px", fontSize: "12.5px", fontWeight: "600", background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", color: "#475569", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAsset}
                  style={{ padding: "8px 18px", fontSize: "12.5px", fontWeight: "600", background: "#047857", border: "none", borderRadius: "4px", color: "#FFFFFF", cursor: submittingAsset ? "not-allowed" : "pointer" }}
                >
                  {submittingAsset ? "Saving..." : "Register Asset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --------------------------------------------------------------------- */}
      {/* MODAL 3: LOG SCRAP / REJECT */}
      {/* --------------------------------------------------------------------- */}
      {showAddWasteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "460px", padding: "24px", boxShadow: "0 10px 25px rgba(0,0,0,0.15)", border: "1px solid #CBD5E1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Log Manufacturing Scrap / Rejection" : "उत्पादन स्क्र्याप / रिजेक्ट दर्ता गर्नुहोस्"}
              </h3>
              <button type="button" onClick={() => setShowAddWasteModal(false)} style={{ background: "none", border: "none", fontSize: "18px", color: "#64748B", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleCreateWaste} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Waste Classification *" : "स्क्र्याप वर्गीकरण *"}
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setWasteType("RAW_MATERIAL_SCRAP");
                      setWasteUnit("kg");
                    }}
                    style={{
                      flex: 1,
                      padding: "8px 10px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: "600",
                      border: "1px solid",
                      borderColor: wasteType === "RAW_MATERIAL_SCRAP" ? "#D97706" : "#CBD5E1",
                      background: wasteType === "RAW_MATERIAL_SCRAP" ? "#FEF3C7" : "#FFFFFF",
                      color: wasteType === "RAW_MATERIAL_SCRAP" ? "#92400E" : "#475569",
                      cursor: "pointer"
                    }}
                  >
                    Raw Material Scrap
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setWasteType("FINISHED_PAIR_REJECT");
                      setWasteUnit("pair");
                    }}
                    style={{
                      flex: 1,
                      padding: "8px 10px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: "600",
                      border: "1px solid",
                      borderColor: wasteType === "FINISHED_PAIR_REJECT" ? "#BE123C" : "#CBD5E1",
                      background: wasteType === "FINISHED_PAIR_REJECT" ? "#FFF1F2" : "#FFFFFF",
                      color: wasteType === "FINISHED_PAIR_REJECT" ? "#BE123C" : "#475569",
                      cursor: "pointer"
                    }}
                  >
                    Finished Pair Reject
                  </button>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Date (Bikram Sambat / AD) *" : "मिति *"}
                </label>
                <NepaliDatePicker
                  valueAd={wasteDateAd}
                  compact
                  onChange={({ ad, bs }) => {
                    setWasteDateAd(ad);
                    setWasteDateBs(bs);
                  }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Quantity *" : "परिमाण *"}
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="e.g. 4.5"
                    value={wasteQuantity}
                    onChange={(e) => setWasteQuantity(e.target.value)}
                    className="num-mono"
                    style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Unit" : "एकाइ"}
                  </label>
                  <input
                    type="text"
                    readOnly
                    value={wasteType === "FINISHED_PAIR_REJECT" ? "pair" : wasteUnit}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#F1F5F9", color: "#64748B" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Reason / Quality Defect Details" : "कारण तथा कैफियत"}
                </label>
                <input
                  type="text"
                  placeholder="e.g. Offcut trimmings, stitching alignment fault"
                  value={wasteReason}
                  onChange={(e) => setWasteReason(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Disposal Method" : "निकासी विधि"}
                </label>
                <select
                  value={wasteDisposalMethod}
                  onChange={(e) => setWasteDisposalMethod(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF" }}
                >
                  <option value="DISCARDED">DISCARDED (नष्ट/फालिएको)</option>
                  <option value="RECYCLED">RECYCLED (पुनःप्रयोग)</option>
                  <option value="SOLD_AS_SCRAP">SOLD AS SCRAP (कवाडी बिक्री)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddWasteModal(false)}
                  style={{ padding: "8px 14px", fontSize: "12.5px", fontWeight: "600", background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", color: "#475569", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingWaste}
                  style={{ padding: "8px 18px", fontSize: "12.5px", fontWeight: "600", background: "#BE123C", border: "none", borderRadius: "4px", color: "#FFFFFF", cursor: submittingWaste ? "not-allowed" : "pointer" }}
                >
                  {submittingWaste ? "Recording..." : "Log Scrap Entry"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
