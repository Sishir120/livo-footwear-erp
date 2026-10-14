"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  PlusCircle,
  FileText,
  Truck,
  PackageCheck,
  Search,
  Download,
  Upload,
  Image as ImageIcon,
  Paperclip,
  X,
  Eye,
  CheckCircle2,
  Calendar,
  Layers,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Calculator,
  SlidersHorizontal,
  RefreshCw
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";
import { NepaliDatePicker } from "./NepaliDatePicker";
import { getTodayAd, getTodayBs } from "../lib/nepaliDate";

export function PurchaseView({ userRole }: { userRole?: string }) {
  const [activeTab, setActiveTab] = useState<"orders" | "ledger" | "landed_costs">("orders");
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [purchases, setPurchases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("all");

  // Create PO Modal State
  const [showPOModal, setShowPOModal] = useState(false);
  const [poSupplierId, setPoSupplierId] = useState("");
  const [poMaterialId, setPoMaterialId] = useState("");
  const [poQuantity, setPoQuantity] = useState("");
  const [poUnitPrice, setPoUnitPrice] = useState("");
  const [poDateAd, setPoDateAd] = useState(() => getTodayAd());
  const [poDateBs, setPoDateBs] = useState(() => getTodayBs().formatted);
  const [poStatus, setPoStatus] = useState<"ORDERED" | "RECEIVED">("ORDERED");
  const [poNotes, setPoNotes] = useState("");
  const [submittingPO, setSubmittingPO] = useState(false);

  // Goods Receipt (GRN) & Landed Cost Modal State
  const [showGRNModal, setShowGRNModal] = useState(false);
  const [selectedPOForGRN, setSelectedPOForGRN] = useState<any | null>(null);
  const [grnQuantity, setGrnQuantity] = useState("");
  const [grnDateAd, setGrnDateAd] = useState(() => getTodayAd());
  const [grnDateBs, setGrnDateBs] = useState(() => getTodayBs().formatted);
  const [carryingInNpr, setCarryingInNpr] = useState("");
  const [importDutyNpr, setImportDutyNpr] = useState("");
  const [chinaCarryingNpr, setChinaCarryingNpr] = useState("");
  const [insuranceNpr, setInsuranceNpr] = useState("");
  const [grnNotes, setGrnNotes] = useState("");
  const [submittingGRN, setSubmittingGRN] = useState(false);

  // Stock Card Modal State
  const [showStockCardModal, setShowStockCardModal] = useState(false);
  const [selectedMaterialForCard, setSelectedMaterialForCard] = useState<any | null>(null);
  const [stockCardData, setStockCardData] = useState<any | null>(null);
  const [loadingCard, setLoadingCard] = useState(false);

  // Stock Adjustment Modal State
  const [showAdjustmentModal, setShowAdjustmentModal] = useState(false);
  const [adjMaterialId, setAdjMaterialId] = useState<number | null>(null);
  const [adjType, setAdjType] = useState<"RECOUNT" | "DAMAGE" | "SAMPLE" | "ADJUSTMENT">("RECOUNT");
  const [adjDirection, setAdjDirection] = useState<1 | -1>(1);
  const [adjQuantity, setAdjQuantity] = useState("");
  const [adjDateAd, setAdjDateAd] = useState(() => getTodayAd());
  const [adjDateBs, setAdjDateBs] = useState(() => getTodayBs().formatted);
  const [adjNotes, setAdjNotes] = useState("");
  const [submittingAdj, setSubmittingAdj] = useState(false);

  // Vendor Bill Attachment State
  const [attachedFile, setAttachedFile] = useState<{ name: string; size: string; previewUrl: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [previewAttachment, setPreviewAttachment] = useState<{ title: string; url: string } | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [supRes, matRes, purRes] = await Promise.all([
        fetch("/api/v1/purchase/suppliers"),
        fetch("/api/v1/purchase/raw-materials"),
        fetch("/api/v1/purchase/purchases")
      ]);
      if (supRes.ok) setSuppliers(await supRes.json());
      if (matRes.ok) setMaterials(await matRes.json());
      if (purRes.ok) setPurchases(await purRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getSupplier = (id: number) => suppliers.find((s) => s.id === id);
  const getMaterial = (id: number) => materials.find((m) => m.id === id);

  // Open GRN modal for a purchase order
  const handleOpenGRN = (po: any) => {
    setSelectedPOForGRN(po);
    setGrnQuantity(String(po.quantity));
    setCarryingInNpr(po.carrying_in_paisa ? String(po.carrying_in_paisa / 100) : "");
    setImportDutyNpr(po.import_duty_paisa ? String(po.import_duty_paisa / 100) : "");
    setChinaCarryingNpr(po.china_carrying_paisa ? String(po.china_carrying_paisa / 100) : "");
    setInsuranceNpr(po.insurance_paisa ? String(po.insurance_paisa / 100) : "");
    setGrnNotes("");
    setShowGRNModal(true);
  };

  // Open stock card modal
  const handleOpenStockCard = async (mat: any) => {
    setSelectedMaterialForCard(mat);
    setShowStockCardModal(true);
    setLoadingCard(true);
    try {
      const res = await fetch(`/api/v1/purchases/materials/${mat.id}/card`);
      if (res.ok) {
        setStockCardData(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingCard(false);
    }
  };

  // Open adjustment modal
  const handleOpenAdjustment = (mat: any) => {
    setAdjMaterialId(mat.id);
    setAdjType("RECOUNT");
    setAdjDirection(1);
    setAdjQuantity("");
    setAdjNotes("");
    setShowAdjustmentModal(true);
  };

  // Submit PO Creation
  const handleCreatePurchaseOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!poSupplierId || !poMaterialId || !poQuantity || !poUnitPrice) return;

    setSubmittingPO(true);
    try {
      const purchaseNotes = attachedFile
        ? `${poNotes ? poNotes + " | " : ""}Attached Bill: ${attachedFile.name}`
        : poNotes;

      const res = await fetch("/api/v1/purchases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_id: parseInt(poSupplierId),
          raw_material_id: parseInt(poMaterialId),
          quantity: parseFloat(poQuantity),
          unit_price: parseFloat(poUnitPrice),
          purchase_date_ad: poDateAd,
          purchase_date_bs: poDateBs,
          order_date_ad: poDateAd,
          order_date_bs: poDateBs,
          receipt_date_ad: poStatus === "RECEIVED" ? poDateAd : null,
          receipt_date_bs: poStatus === "RECEIVED" ? poDateBs : null,
          status: poStatus,
          notes: purchaseNotes
        })
      });

      if (res.ok) {
        setShowPOModal(false);
        setPoQuantity("");
        setPoUnitPrice("");
        setPoNotes("");
        setAttachedFile(null);
        await loadData();
      } else {
        const err = await res.json();
        alert(err.detail || "Error creating purchase order");
      }
    } catch (e) {
      alert("Failed to submit purchase order");
    } finally {
      setSubmittingPO(false);
    }
  };

  // Submit Goods Receipt (GRN) with Landed Cost
  const handleSubmitGRN = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPOForGRN || !grnQuantity) return;

    setSubmittingGRN(true);
    try {
      const payload = {
        receipt_date_ad: grnDateAd,
        receipt_date_bs: grnDateBs,
        received_quantity: parseFloat(grnQuantity),
        carrying_in_paisa: Math.round((parseFloat(carryingInNpr) || 0) * 100),
        import_duty_paisa: Math.round((parseFloat(importDutyNpr) || 0) * 100),
        china_carrying_paisa: Math.round((parseFloat(chinaCarryingNpr) || 0) * 100),
        insurance_paisa: Math.round((parseFloat(insuranceNpr) || 0) * 100),
        notes: grnNotes || undefined
      };

      const res = await fetch(`/api/v1/purchases/${selectedPOForGRN.id}/receive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setShowGRNModal(false);
        setSelectedPOForGRN(null);
        await loadData();
      } else {
        const err = await res.json();
        alert(err.detail || "Error receiving purchase order");
      }
    } catch (e) {
      alert("Failed to post goods receipt");
    } finally {
      setSubmittingGRN(false);
    }
  };

  // Submit Stock Adjustment
  const handleSubmitAdjustment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!adjMaterialId || !adjQuantity) return;

    setSubmittingAdj(true);
    try {
      const res = await fetch(`/api/v1/purchases/materials/${adjMaterialId}/adjust`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          adjustment_type: adjType,
          direction: adjDirection,
          quantity: parseFloat(adjQuantity),
          movement_date_ad: adjDateAd,
          movement_date_bs: adjDateBs,
          notes: adjNotes || undefined
        })
      });

      if (res.ok) {
        setShowAdjustmentModal(false);
        setAdjQuantity("");
        setAdjNotes("");
        await loadData();
        if (selectedMaterialForCard && selectedMaterialForCard.id === adjMaterialId) {
          handleOpenStockCard(selectedMaterialForCard);
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Adjustment failed");
      }
    } catch (e) {
      alert("Failed to submit adjustment");
    } finally {
      setSubmittingAdj(false);
    }
  };

  // Reactive Landed Cost Calculator for GRN Modal
  const landedCalculation = useMemo(() => {
    if (!selectedPOForGRN) return { baseNpr: 0, totalLandedNpr: 0, effectiveRateNpr: 0, markupPct: 0 };
    const qty = parseFloat(grnQuantity) || 0;
    const baseUnitRate = parseFloat(selectedPOForGRN.unit_price) || 0;
    const baseNpr = qty * baseUnitRate;

    const carrying = parseFloat(carryingInNpr) || 0;
    const customs = parseFloat(importDutyNpr) || 0;
    const chinaFreight = parseFloat(chinaCarryingNpr) || 0;
    const insurance = parseFloat(insuranceNpr) || 0;

    const totalLandedNpr = baseNpr + carrying + customs + chinaFreight + insurance;
    const effectiveRateNpr = qty > 0 ? totalLandedNpr / qty : 0;
    const markupPct = baseUnitRate > 0 ? ((effectiveRateNpr - baseUnitRate) / baseUnitRate) * 100 : 0;

    return {
      baseNpr,
      totalLandedNpr,
      effectiveRateNpr,
      markupPct
    };
  }, [selectedPOForGRN, grnQuantity, carryingInNpr, importDutyNpr, chinaCarryingNpr, insuranceNpr]);

  // Filtered Purchases for Tab 1
  const filteredPurchases = useMemo(() => {
    return purchases.filter((p) => {
      const sup = getSupplier(p.supplier_id);
      const mat = getMaterial(p.raw_material_id);
      const supName = sup ? `${sup.name} ${sup.code}`.toLowerCase() : "";
      const matName = mat ? `${mat.name} ${mat.code || ""}`.toLowerCase() : "";
      const grnStr = (p.grn_number || "").toLowerCase();
      const q = searchQuery.toLowerCase();

      const matchesSearch =
        supName.includes(q) ||
        matName.includes(q) ||
        grnStr.includes(q) ||
        (p.purchase_date_ad || "").includes(q) ||
        (p.notes || "").toLowerCase().includes(q);

      const matchesSupplier =
        supplierFilter === "all" || String(p.supplier_id) === supplierFilter;

      return matchesSearch && matchesSupplier;
    });
  }, [purchases, suppliers, materials, searchQuery, supplierFilter]);

  // Filtered Materials for Tab 2
  const filteredMaterials = useMemo(() => {
    return materials.filter((m) => {
      const q = searchQuery.toLowerCase();
      return (
        m.name.toLowerCase().includes(q) ||
        m.code.toLowerCase().includes(q) ||
        m.unit.toLowerCase().includes(q)
      );
    });
  }, [materials, searchQuery]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Top Header & Tab Navigation Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "17px", fontWeight: "700", color: "#0F172A", margin: 0, letterSpacing: "-0.01em" }}>
            Raw Material Procurement & Append-Only Ledger
          </h2>
          <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px" }}>
            Decoupled Purchase Orders, Multi-Column Import Landed Cost, and Immutable Physical Stock Movements
          </div>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {/* Tab Switcher */}
          <div style={{ display: "flex", background: "#F1F5F9", borderRadius: "6px", padding: "3px", border: "1px solid #CBD5E1" }}>
            <button
              onClick={() => setActiveTab("orders")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                background: activeTab === "orders" ? "#1E3A8A" : "transparent",
                color: activeTab === "orders" ? "#FFFFFF" : "#475569"
              }}
            >
              <Truck size={14} />
              <span>Orders & Inward Log (खरिद तथा दाखिला)</span>
            </button>
            <button
              onClick={() => setActiveTab("ledger")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                background: activeTab === "ledger" ? "#1E3A8A" : "transparent",
                color: activeTab === "ledger" ? "#FFFFFF" : "#475569"
              }}
            >
              <Layers size={14} />
              <span>Stock Cards & Ledger (कच्चा पदार्थ मौज्दात)</span>
            </button>
            <button
              onClick={() => setActiveTab("landed_costs")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                fontWeight: "600",
                borderRadius: "4px",
                border: "none",
                cursor: "pointer",
                background: activeTab === "landed_costs" ? "#1E3A8A" : "transparent",
                color: activeTab === "landed_costs" ? "#FFFFFF" : "#475569"
              }}
            >
              <Calculator size={14} />
              <span>Landed Cost Ledger (खरिद खर्च लेजर)</span>
            </button>
          </div>

          {userRole === "editor" && activeTab === "orders" && (
            <button
              className="btn-primary"
              onClick={() => {
                setPoStatus("ORDERED");
                setShowPOModal(true);
              }}
              style={{ background: "#1E3A8A", borderColor: "#1E3A8A", padding: "6px 14px", fontSize: "12px" }}
            >
              <PlusCircle size={15} /> New Purchase Order (खरिद अर्डर)
            </button>
          )}
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-card" style={{ padding: "10px 14px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", background: "#FFFFFF", border: "1px solid #CBD5E1" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "220px", background: "#F8FAFC", padding: "4px 8px", borderRadius: "3px", border: "1px solid #CBD5E1" }}>
          <Search size={14} color="#64748B" />
          <input
            type="text"
            placeholder={activeTab === "orders" ? "Search PO, GRN number, supplier, material..." : "Search material SKU code, name, unit..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ background: "none", border: "none", color: "#0F172A", fontSize: "12px", outline: "none", width: "100%" }}
          />
        </div>

        {activeTab === "orders" && (
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "11px", color: "#475569", fontWeight: "700", textTransform: "uppercase" }}>Supplier:</span>
              <select
                style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "3px", width: "170px", padding: "4px 8px", fontSize: "12px", color: "#0F172A", cursor: "pointer" }}
                value={supplierFilter}
                onChange={(e) => setSupplierFilter(e.target.value)}
              >
                <option value="all">All Suppliers ({suppliers.length})</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={() => {
                if (!filteredPurchases.length) return;
                const headers = ["ID", "Status", "GRN", "Date AD", "Supplier", "Raw Material", "Quantity", "Base Rate", "Effective Rate", "Total Landed NPR"];
                const rows = filteredPurchases.map((p) => [
                  p.id,
                  p.status,
                  p.grn_number || "-",
                  p.purchase_date_ad,
                  getSupplier(p.supplier_id)?.name || p.supplier_id,
                  getMaterial(p.raw_material_id)?.name || p.raw_material_id,
                  p.quantity,
                  p.unit_price,
                  p.effective_unit_rate_paisa ? (p.effective_unit_rate_paisa / 100).toFixed(2) : p.unit_price,
                  p.total_landed_cost_paisa ? (p.total_landed_cost_paisa / 100).toFixed(2) : p.total_amount
                ]);
                exportToCSV("Procurement_Orders_GRN", headers, rows);
              }}
              className="btn-export"
              disabled={!filteredPurchases.length}
            >
              <Download size={13} /> Export CSV
            </button>
          </div>
        )}
      </div>

      {/* TAB 1: Purchase Orders & Inward Log */}
      {activeTab === "orders" && (
        <div className="glass-card" style={{ padding: "14px 16px", background: "#FFFFFF", border: "1px solid #CBD5E1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={16} color="#1E3A8A" />
              <h3 style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Procurement Orders & Inward Receipts ({filteredPurchases.length} Records)
              </h3>
            </div>
            <span style={{ fontSize: "11px", color: "#64748B" }}>Append-only ledger entries reflect upon physical GRN</span>
          </div>

          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>Loading records...</div>
          ) : filteredPurchases.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
              No purchase orders found matching criteria.
            </div>
          ) : (
            <div className="table-container-dense">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th style={{ width: "90px" }}>Status</th>
                    <th style={{ width: "110px" }}>GRN / Voucher</th>
                    <th style={{ width: "130px" }}>Date (AD / BS)</th>
                    <th>Supplier / Origin</th>
                    <th>Raw Material</th>
                    <th style={{ textAlign: "right", width: "90px" }}>Qty</th>
                    <th style={{ textAlign: "right", width: "100px" }}>Base Rate</th>
                    <th style={{ textAlign: "right", width: "110px" }}>Landed Unit Rate</th>
                    <th style={{ textAlign: "right", width: "120px" }}>Total Landed</th>
                    <th style={{ textAlign: "center", width: "110px" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPurchases.map((p) => {
                    const sup = getSupplier(p.supplier_id);
                    const mat = getMaterial(p.raw_material_id);
                    const isReceived = p.status === "RECEIVED";
                    const landedRateNpr = p.effective_unit_rate_paisa ? (p.effective_unit_rate_paisa / 100) : p.unit_price;
                    const totalLandedNpr = p.total_landed_cost_paisa ? (p.total_landed_cost_paisa / 100) : p.total_amount;

                    return (
                      <tr key={p.id}>
                        <td>
                          <span
                            style={{
                              display: "inline-block",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontSize: "10.5px",
                              fontWeight: "700",
                              background: isReceived ? "#DCFCE7" : "#FEF3C7",
                              color: isReceived ? "#166534" : "#92400E",
                              border: `1px solid ${isReceived ? "#86EFAC" : "#FDE68A"}`
                            }}
                          >
                            {p.status}
                          </span>
                        </td>
                        <td style={{ fontFamily: "monospace", fontWeight: "600", color: "#1E3A8A" }}>
                          {p.grn_number || <span style={{ color: "#94A3B8" }}>Pending</span>}
                        </td>
                        <td style={{ fontSize: "12px", color: "#475569" }}>
                          {p.purchase_date_ad}{" "}
                          <span style={{ fontSize: "11px", color: "#64748B" }}>({p.purchase_date_bs})</span>
                        </td>
                        <td style={{ fontWeight: "600", color: "#0F172A" }}>
                          {sup ? `${sup.name} [${sup.code}]` : `Supplier #${p.supplier_id}`}
                        </td>
                        <td style={{ fontWeight: "500", color: "#0F172A" }}>
                          {mat ? `${mat.name} (${mat.unit})` : `Material #${p.raw_material_id}`}
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "600" }} className="num-mono">
                          {p.quantity} {mat?.unit || ""}
                        </td>
                        <td style={{ textAlign: "right", color: "#64748B" }} className="num-mono">
                          Rs. {Number(p.unit_price).toLocaleString()}
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono">
                          Rs. {Number(landedRateNpr).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700", color: "#1E3A8A" }} className="num-mono-bold">
                          Rs. {Number(totalLandedNpr).toLocaleString()}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          {!isReceived && userRole === "editor" ? (
                            <button
                              onClick={() => handleOpenGRN(p)}
                              style={{
                                background: "#16A34A",
                                color: "#FFFFFF",
                                border: "none",
                                borderRadius: "3px",
                                padding: "3px 8px",
                                fontSize: "11px",
                                fontWeight: "600",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px"
                              }}
                            >
                              <PackageCheck size={12} /> Receive (दाखिला)
                            </button>
                          ) : (
                            <span style={{ fontSize: "11px", color: "#059669", fontWeight: "600" }}>✓ Received</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Raw Material Stock Ledger & Cards */}
      {activeTab === "ledger" && (
        <div className="glass-card" style={{ padding: "14px 16px", background: "#FFFFFF", border: "1px solid #CBD5E1" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="#1E3A8A" />
              <h3 style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Physical Raw Material Inventory & Reorder Levels ({filteredMaterials.length} Items)
              </h3>
            </div>
            <span style={{ fontSize: "11px", color: "#64748B" }}>Real-time balance derived from cumulative movement ledger</span>
          </div>

          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th style={{ width: "120px" }}>SKU Code</th>
                  <th>Raw Material Name</th>
                  <th style={{ width: "90px" }}>Unit</th>
                  <th style={{ textAlign: "right", width: "120px" }}>Reorder Level</th>
                  <th style={{ textAlign: "right", width: "140px" }}>Current Physical Balance</th>
                  <th style={{ width: "120px", textAlign: "center" }}>Status</th>
                  <th style={{ width: "160px", textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredMaterials.map((mat) => {
                  const isLow = mat.current_stock <= (mat.reorder_level || 0);

                  return (
                    <tr key={mat.id}>
                      <td style={{ fontFamily: "monospace", fontWeight: "700", color: "#1E3A8A" }}>
                        {mat.code}
                      </td>
                      <td style={{ fontWeight: "600", color: "#0F172A" }}>
                        {mat.name}
                      </td>
                      <td style={{ color: "#475569" }}>
                        <span style={{ background: "#F1F5F9", padding: "1px 6px", borderRadius: "3px", fontSize: "11px" }}>
                          {mat.unit}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        {mat.reorder_level || 0} {mat.unit}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "700", color: isLow ? "#DC2626" : "#0F172A" }} className="num-mono-bold">
                        {Number(mat.current_stock || 0).toLocaleString()} {mat.unit}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {isLow ? (
                          <span style={{ display: "inline-flex", alignItems: "center", gap: "3px", background: "#FEE2E2", color: "#991B1B", border: "1px solid #FCA5A5", padding: "2px 6px", borderRadius: "3px", fontSize: "10.5px", fontWeight: "700" }}>
                            <AlertTriangle size={11} /> REORDER
                          </span>
                        ) : (
                          <span style={{ background: "#DCFCE7", color: "#166534", border: "1px solid #86EFAC", padding: "2px 6px", borderRadius: "3px", fontSize: "10.5px", fontWeight: "700" }}>
                            SUFFICIENT
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <div style={{ display: "flex", gap: "6px", justifyContent: "center" }}>
                          <button
                            onClick={() => handleOpenStockCard(mat)}
                            style={{
                              background: "#EFF6FF",
                              border: "1px solid #BFDBFE",
                              color: "#1E3A8A",
                              borderRadius: "3px",
                              padding: "3px 8px",
                              fontSize: "11px",
                              fontWeight: "600",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px"
                            }}
                          >
                            <Eye size={12} /> Stock Card
                          </button>
                          {userRole === "editor" && (
                            <button
                              onClick={() => handleOpenAdjustment(mat)}
                              style={{
                                background: "#F8FAFC",
                                border: "1px solid #CBD5E1",
                                color: "#475569",
                                borderRadius: "3px",
                                padding: "3px 8px",
                                fontSize: "11px",
                                fontWeight: "600",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px"
                              }}
                            >
                              <SlidersHorizontal size={12} /> Adjust
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Multi-Column Import Landed Cost Ledger */}
      {activeTab === "landed_costs" && (
        <div className="glass-card" style={{ padding: "14px 16px", background: "#FFFFFF", border: "1px solid #CBD5E1" }}>
          {/* Controls Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Calculator size={16} color="#1E3A8A" />
              <h3 style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Import Landed Cost & Procurement Expense Ledger (आयात तथा खरिद खर्च विवरण)
              </h3>
            </div>

            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <div style={{ position: "relative", minWidth: "220px" }}>
                <Search size={14} style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)", color: "#64748B" }} />
                <input
                  type="text"
                  placeholder="खोज्नुहोस् (Supplier, Material, GRN)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "6px 10px 6px 30px",
                    fontSize: "12px",
                    borderRadius: "4px",
                    border: "1px solid #CBD5E1",
                    background: "#F8FAFC"
                  }}
                />
              </div>

              <select
                value={supplierFilter}
                onChange={(e) => setSupplierFilter(e.target.value)}
                style={{
                  padding: "6px 10px",
                  fontSize: "12px",
                  borderRadius: "4px",
                  border: "1px solid #CBD5E1",
                  background: "#F8FAFC"
                }}
              >
                <option value="all">All Suppliers (सबै आपूर्तिकर्ता)</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name}
                  </option>
                ))}
              </select>

              <button
                onClick={() => {
                  const headers = [
                    "S.N.",
                    "Date AD",
                    "Date BS",
                    "Supplier",
                    "Raw Material",
                    "Carrying In (NPR)",
                    "Import Duty (NPR)",
                    "China Carrying In (NPR)",
                    "Insurance (NPR)",
                    "Total Landed Expenses (NPR)",
                    "GRN Number",
                    "Status"
                  ];
                  const rows = filteredPurchases.map((p, idx) => {
                    const sup = getSupplier(p.supplier_id);
                    const mat = getMaterial(p.raw_material_id);
                    const carrying = (p.carrying_in_paisa || 0) / 100;
                    const duty = (p.import_duty_paisa || 0) / 100;
                    const china = (p.china_carrying_paisa || 0) / 100;
                    const ins = (p.insurance_paisa || 0) / 100;
                    const totalLanded = carrying + duty + china + ins;
                    return [
                      idx + 1,
                      p.receipt_date_ad || p.purchase_date_ad || "-",
                      p.receipt_date_bs || p.purchase_date_bs || "-",
                      sup ? sup.name : "-",
                      mat ? mat.name : "-",
                      carrying.toFixed(2),
                      duty.toFixed(2),
                      china.toFixed(2),
                      ins.toFixed(2),
                      totalLanded.toFixed(2),
                      p.grn_number || "-",
                      p.status || "-"
                    ];
                  });
                  exportToCSV("landed_costs_ledger", headers, rows);
                }}
                className="btn-secondary"
                style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", padding: "6px 10px" }}
              >
                <Download size={13} /> Export CSV
              </button>
            </div>
          </div>

          {/* Table */}
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr style={{ background: "#F8FAFC" }}>
                  <th style={{ width: "45px", textAlign: "center" }}>क्र.सं.</th>
                  <th style={{ width: "125px" }}>Date (AD / BS)</th>
                  <th>Particular (Supplier & Raw Material)</th>
                  <th style={{ textAlign: "right", width: "125px" }}>Carrying-in (रु)</th>
                  <th style={{ textAlign: "right", width: "135px" }}>Import Duty (रु)</th>
                  <th style={{ textAlign: "right", width: "145px" }}>China Carrying (रु)</th>
                  <th style={{ textAlign: "right", width: "115px" }}>Insurance (रु)</th>
                  <th style={{ textAlign: "right", width: "145px", background: "#EFF6FF" }}>Total Landed (रु)</th>
                  <th style={{ textAlign: "center", width: "110px" }}>GRN Ref</th>
                </tr>
              </thead>
              <tbody>
                {filteredPurchases.length === 0 ? (
                  <tr>
                    <td colSpan={9} style={{ textAlign: "center", padding: "32px", color: "#64748B" }}>
                      कुनै खरिद खर्च रेकर्ड फेला परेन (No landed cost records found).
                    </td>
                  </tr>
                ) : (
                  filteredPurchases.map((p, index) => {
                    const sup = getSupplier(p.supplier_id);
                    const mat = getMaterial(p.raw_material_id);
                    const carrying = (p.carrying_in_paisa || 0) / 100;
                    const duty = (p.import_duty_paisa || 0) / 100;
                    const china = (p.china_carrying_paisa || 0) / 100;
                    const ins = (p.insurance_paisa || 0) / 100;
                    const totalLanded = carrying + duty + china + ins;

                    return (
                      <tr key={p.id}>
                        <td style={{ textAlign: "center", color: "#64748B", fontSize: "11px" }}>{index + 1}</td>
                        <td style={{ fontSize: "11.5px" }}>
                          <div style={{ fontWeight: "600", color: "#0F172A" }}>{p.receipt_date_ad || p.purchase_date_ad}</div>
                          <div style={{ fontSize: "10.5px", color: "#64748B" }}>{p.receipt_date_bs || p.purchase_date_bs}</div>
                        </td>
                        <td>
                          <div style={{ fontWeight: "600", color: "#1E293B" }}>{sup?.name || "Unknown Supplier"}</div>
                          <div style={{ fontSize: "11px", color: "#475569" }}>
                            {mat?.name || "Item"} &bull; {p.received_quantity || p.quantity} {mat?.unit || "units"}
                          </div>
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: carrying > 0 ? "#0F172A" : "#94A3B8" }}>
                          {carrying > 0 ? `रु ${carrying.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: duty > 0 ? "#0F172A" : "#94A3B8" }}>
                          {duty > 0 ? `रु ${duty.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: china > 0 ? "#0F172A" : "#94A3B8" }}>
                          {china > 0 ? `रु ${china.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: ins > 0 ? "#0F172A" : "#94A3B8" }}>
                          {ins > 0 ? `रु ${ins.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: "700", color: "#1E3A8A", background: "#F8FAFC" }}>
                          {totalLanded > 0 ? `रु ${totalLanded.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "-"}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          {p.grn_number ? (
                            <span style={{ background: "#EEF2FF", color: "#4338CA", border: "1px solid #C7D2FE", padding: "2px 6px", borderRadius: "3px", fontSize: "10.5px", fontWeight: "600", fontFamily: "monospace" }}>
                              {p.grn_number}
                            </span>
                          ) : (
                            <span style={{ fontSize: "10.5px", color: "#94A3B8" }}>Pending</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
              {/* Bottom Totals Row */}
              {filteredPurchases.length > 0 && (() => {
                const totalCarrying = filteredPurchases.reduce((acc, p) => acc + (p.carrying_in_paisa || 0) / 100, 0);
                const totalDuty = filteredPurchases.reduce((acc, p) => acc + (p.import_duty_paisa || 0) / 100, 0);
                const totalChina = filteredPurchases.reduce((acc, p) => acc + (p.china_carrying_paisa || 0) / 100, 0);
                const totalIns = filteredPurchases.reduce((acc, p) => acc + (p.insurance_paisa || 0) / 100, 0);
                const grandTotalLanded = totalCarrying + totalDuty + totalChina + totalIns;

                return (
                  <tfoot>
                    <tr style={{ background: "#F1F5F9", borderTop: "2px solid #CBD5E1", fontWeight: "700" }}>
                      <td colSpan={3} style={{ textAlign: "right", paddingRight: "14px", color: "#0F172A", textTransform: "uppercase", fontSize: "11.5px", letterSpacing: "0.03em" }}>
                        कुल खर्च (Bottom Totals):
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#0F172A" }}>
                        रु {totalCarrying.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#0F172A" }}>
                        रु {totalDuty.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#0F172A" }}>
                        रु {totalChina.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#0F172A" }}>
                        रु {totalIns.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#1E3A8A", background: "#DBEAFE", fontSize: "12.5px" }}>
                        रु {grandTotalLanded.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                );
              })()}
            </table>
          </div>
        </div>
      )}

      {/* CREATE PURCHASE ORDER MODAL */}
      {showPOModal && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" style={{ maxWidth: "560px" }}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Truck size={16} color="#1E3A8A" />
                <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase" }}>
                  Create Purchase Order (खरिद अर्डर)
                </h3>
              </div>
              <button onClick={() => setShowPOModal(false)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreatePurchaseOrder} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Supplier / Vendor</label>
                  <select
                    className="input-field"
                    value={poSupplierId}
                    onChange={(e) => setPoSupplierId(e.target.value)}
                    required
                  >
                    <option value="">-- Select Supplier --</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Raw Material Item</label>
                  <select
                    className="input-field"
                    value={poMaterialId}
                    onChange={(e) => setPoMaterialId(e.target.value)}
                    required
                  >
                    <option value="">-- Select Raw Material --</option>
                    {materials.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.code}) - {m.unit}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Ordered Quantity</label>
                    <input
                      type="number"
                      step="0.01"
                      className="input-field num-mono"
                      placeholder="e.g. 100"
                      value={poQuantity}
                      onChange={(e) => setPoQuantity(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Base Unit Rate (NPR)</label>
                    <input
                      type="number"
                      step="0.01"
                      className="input-field num-mono"
                      placeholder="e.g. 450"
                      value={poUnitPrice}
                      onChange={(e) => setPoUnitPrice(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <NepaliDatePicker
                  label="Order Date (अर्डर मिति)"
                  valueAd={poDateAd}
                  valueBs={poDateBs}
                  onChange={({ ad, bs }) => {
                    setPoDateAd(ad);
                    setPoDateBs(bs);
                  }}
                  required
                />

                <div style={{ display: "flex", gap: "16px", padding: "10px", background: "#F8FAFC", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", fontWeight: "600", color: "#0F172A" }}>
                    <input
                      type="radio"
                      name="poInitialStatus"
                      checked={poStatus === "ORDERED"}
                      onChange={() => setPoStatus("ORDERED")}
                      style={{ accentColor: "#1E3A8A" }}
                    />
                    <span>ORDERED (अर्डर मात्र - मौज्दात परिवर्तन हुँदैन)</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", fontWeight: "600", color: "#0F172A" }}>
                    <input
                      type="radio"
                      name="poInitialStatus"
                      checked={poStatus === "RECEIVED"}
                      onChange={() => setPoStatus("RECEIVED")}
                      style={{ accentColor: "#16A34A" }}
                    />
                    <span>RECEIVED (तुरुन्त दाखिला - स्टक मौज्दात बढ्छ)</span>
                  </label>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>PO Remarks / Notes</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Optional purchase instructions or vendor PO contract no."
                    value={poNotes}
                    onChange={(e) => setPoNotes(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowPOModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submittingPO} style={{ background: "#1E3A8A", borderColor: "#1E3A8A" }}>
                  {submittingPO ? "Creating PO..." : "Create Purchase Order"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* GOODS RECEIPT NOTE (GRN) & LANDED COST MODAL */}
      {showGRNModal && selectedPOForGRN && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" style={{ maxWidth: "640px" }}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Calculator size={18} color="#16A34A" />
                <div>
                  <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase" }}>
                    Goods Receipt Note (GRN) & Landed Cost Allocation
                  </h3>
                  <div style={{ fontSize: "11px", color: "#475569" }}>
                    PO #{selectedPOForGRN.id} • {getMaterial(selectedPOForGRN.raw_material_id)?.name} • {getSupplier(selectedPOForGRN.supplier_id)?.name}
                  </div>
                </div>
              </div>
              <button onClick={() => setShowGRNModal(false)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmitGRN} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Physical Quantity Received</label>
                    <input
                      type="number"
                      step="0.01"
                      className="input-field num-mono"
                      value={grnQuantity}
                      onChange={(e) => setGrnQuantity(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Base Invoice Rate (NPR)</label>
                    <input
                      type="text"
                      className="input-field num-mono"
                      value={`Rs. ${Number(selectedPOForGRN.unit_price).toLocaleString()}`}
                      disabled
                      style={{ background: "#F1F5F9", color: "#475569" }}
                    />
                  </div>
                </div>

                <NepaliDatePicker
                  label="Physical Receipt Date (दाखिला मिति)"
                  valueAd={grnDateAd}
                  valueBs={grnDateBs}
                  onChange={({ ad, bs }) => {
                    setGrnDateAd(ad);
                    setGrnDateBs(bs);
                  }}
                  required
                />

                {/* Multi-Column Landed Cost Auxiliary Expenses */}
                <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "6px", padding: "12px" }}>
                  <div style={{ fontSize: "12px", fontWeight: "700", color: "#1E3A8A", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <SlidersHorizontal size={14} /> Multi-Column Landed Import / Auxiliary Expenses (NPR)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                    <div>
                      <label style={{ fontSize: "11px", color: "#475569", fontWeight: "600" }}>Carrying-in Exp (ढुवानी खर्च)</label>
                      <input
                        type="number"
                        step="0.01"
                        className="input-field num-mono"
                        placeholder="0.00"
                        value={carryingInNpr}
                        onChange={(e) => setCarryingInNpr(e.target.value)}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "11px", color: "#475569", fontWeight: "600" }}>Import Duty Tax (भन्सार महसुल)</label>
                      <input
                        type="number"
                        step="0.01"
                        className="input-field num-mono"
                        placeholder="0.00"
                        value={importDutyNpr}
                        onChange={(e) => setImportDutyNpr(e.target.value)}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "11px", color: "#475569", fontWeight: "600" }}>China Carrying-in Exp (चीन ढुवानी)</label>
                      <input
                        type="number"
                        step="0.01"
                        className="input-field num-mono"
                        placeholder="0.00"
                        value={chinaCarryingNpr}
                        onChange={(e) => setChinaCarryingNpr(e.target.value)}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "11px", color: "#475569", fontWeight: "600" }}>Insurance (बीमा खर्च)</label>
                      <input
                        type="number"
                        step="0.01"
                        className="input-field num-mono"
                        placeholder="0.00"
                        value={insuranceNpr}
                        onChange={(e) => setInsuranceNpr(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                {/* Live Landed Cost Capitalization Calculator Box */}
                <div style={{ background: "#EFF6FF", border: "1px solid #BFDBFE", borderRadius: "6px", padding: "12px" }}>
                  <div style={{ fontSize: "11px", fontWeight: "700", color: "#1E3A8A", textTransform: "uppercase", marginBottom: "6px" }}>
                    Landed Cost Capitalization Summary (स्वतः पूँजीकरण)
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px" }}>
                    <div>
                      <span style={{ color: "#475569" }}>Invoice Base: </span>
                      <strong className="num-mono" style={{ color: "#0F172A" }}>Rs. {landedCalculation.baseNpr.toLocaleString()}</strong>
                    </div>
                    <div>
                      <span style={{ color: "#475569" }}>Total Landed Cost: </span>
                      <strong className="num-mono-bold" style={{ color: "#1E3A8A" }}>Rs. {landedCalculation.totalLandedNpr.toLocaleString()}</strong>
                    </div>
                    <div>
                      <span style={{ color: "#475569" }}>Effective Unit Rate: </span>
                      <strong className="num-mono-bold" style={{ color: "#166534" }}>Rs. {landedCalculation.effectiveRateNpr.toFixed(2)} / {getMaterial(selectedPOForGRN.raw_material_id)?.unit || "unit"}</strong>
                    </div>
                    <div>
                      <span style={{ color: "#475569" }}>Landed Uplift: </span>
                      <strong style={{ color: landedCalculation.markupPct > 0 ? "#D97706" : "#059669" }}>
                        +{landedCalculation.markupPct.toFixed(1)}% over invoice
                      </strong>
                    </div>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Receipt Remarks</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Gate entry voucher, driver phone, or customs bill no."
                    value={grnNotes}
                    onChange={(e) => setGrnNotes(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowGRNModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submittingGRN} style={{ background: "#16A34A", borderColor: "#16A34A" }}>
                  {submittingGRN ? "Posting GRN..." : "Confirm & Post Physical Receipt"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RAW MATERIAL STOCK CARD MODAL */}
      {showStockCardModal && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" style={{ maxWidth: "780px" }}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Layers size={18} color="#1E3A8A" />
                <div>
                  <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase" }}>
                    Stock Card & Audit Ledger (कच्चा पदार्थ मौज्दात कार्ड)
                  </h3>
                  <div style={{ fontSize: "11px", color: "#475569" }}>
                    {selectedMaterialForCard?.name} [{selectedMaterialForCard?.code}] • Unit: {selectedMaterialForCard?.unit}
                  </div>
                </div>
              </div>
              <button onClick={() => setShowStockCardModal(false)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {loadingCard ? (
                <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>Loading stock card...</div>
              ) : stockCardData ? (
                <>
                  {/* Current Balance Banner */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "6px", padding: "10px 14px" }}>
                    <div>
                      <div style={{ fontSize: "11px", textTransform: "uppercase", color: "#64748B", fontWeight: "700" }}>Physical Balance on Hand</div>
                      <div style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                        {stockCardData.current_balance} {stockCardData.material.unit}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: "11px", textTransform: "uppercase", color: "#64748B", fontWeight: "700" }}>Reorder Level</div>
                      <div style={{ fontSize: "14px", fontWeight: "600", color: "#475569" }} className="num-mono">
                        {stockCardData.material.reorder_level} {stockCardData.material.unit}
                      </div>
                    </div>
                    {userRole === "editor" && (
                      <button
                        onClick={() => handleOpenAdjustment(stockCardData.material)}
                        style={{
                          background: "#1E3A8A",
                          color: "#FFFFFF",
                          border: "none",
                          borderRadius: "4px",
                          padding: "6px 12px",
                          fontSize: "11.5px",
                          fontWeight: "600",
                          cursor: "pointer",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px"
                        }}
                      >
                        <SlidersHorizontal size={13} /> Adjust Stock
                      </button>
                    )}
                  </div>

                  {/* Chronological Movements Table */}
                  <div className="table-container-dense">
                    <table className="table-dense">
                      <thead>
                        <tr>
                          <th style={{ width: "120px" }}>Date (AD/BS)</th>
                          <th style={{ width: "110px" }}>Ref Voucher</th>
                          <th style={{ width: "130px" }}>Movement Type</th>
                          <th style={{ textAlign: "right", width: "90px" }}>Inward (+)</th>
                          <th style={{ textAlign: "right", width: "90px" }}>Outward (-)</th>
                          <th style={{ textAlign: "right", width: "100px" }}>Unit Rate</th>
                          <th style={{ textAlign: "right", width: "110px" }}>Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stockCardData.movements.length === 0 ? (
                          <tr>
                            <td colSpan={7} style={{ textAlign: "center", color: "#64748B", padding: "20px" }}>
                              No movements recorded yet in ledger.
                            </td>
                          </tr>
                        ) : (
                          stockCardData.movements.map((m: any) => (
                            <tr key={m.id}>
                              <td style={{ fontSize: "11.5px", color: "#475569" }}>
                                {m.movement_date}{" "}
                                <span style={{ fontSize: "10.5px", color: "#64748B" }}>({m.movement_date_bs})</span>
                              </td>
                              <td style={{ fontFamily: "monospace", fontWeight: "600", color: "#1E3A8A" }}>
                                {m.reference_voucher}
                              </td>
                              <td>
                                <span
                                  style={{
                                    display: "inline-block",
                                    padding: "1px 5px",
                                    borderRadius: "3px",
                                    fontSize: "10px",
                                    fontWeight: "700",
                                    background: m.movement_type === "PURCHASE_RECEIPT" ? "#DCFCE7" : m.movement_type === "BOM_ISSUE" ? "#EFF6FF" : "#FEF3C7",
                                    color: m.movement_type === "PURCHASE_RECEIPT" ? "#166534" : m.movement_type === "BOM_ISSUE" ? "#1E3A8A" : "#92400E"
                                  }}
                                >
                                  {m.movement_type}
                                </span>
                              </td>
                              <td style={{ textAlign: "right", fontWeight: "700", color: "#16A34A" }} className="num-mono">
                                {m.direction === 1 ? `+${m.quantity}` : "-"}
                              </td>
                              <td style={{ textAlign: "right", fontWeight: "700", color: "#DC2626" }} className="num-mono">
                                {m.direction === -1 ? `-${m.quantity}` : "-"}
                              </td>
                              <td style={{ textAlign: "right", color: "#475569" }} className="num-mono">
                                {m.unit_cost_npr ? `Rs. ${m.unit_cost_npr}` : "-"}
                              </td>
                              <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                                {m.running_balance} {stockCardData.material.unit}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : null}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-secondary" onClick={() => setShowStockCardModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STOCK ADJUSTMENT MODAL */}
      {showAdjustmentModal && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" style={{ maxWidth: "480px" }}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <SlidersHorizontal size={16} color="#1E3A8A" />
                <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase" }}>
                  Material Stock Adjustment (मौज्दात समायोजन)
                </h3>
              </div>
              <button onClick={() => setShowAdjustmentModal(false)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSubmitAdjustment} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Adjustment Reason</label>
                  <select
                    className="input-field"
                    value={adjType}
                    onChange={(e: any) => setAdjType(e.target.value)}
                  >
                    <option value="RECOUNT">RECOUNT (भौतिक गणना फरक)</option>
                    <option value="DAMAGE">DAMAGE (क्षतिग्रस्त / खेर गएको)</option>
                    <option value="SAMPLE">SAMPLE (परीक्षण / नमूना)</option>
                    <option value="ADJUSTMENT">GENERAL ADJUSTMENT (सामान्य समायोजन)</option>
                  </select>
                </div>

                <div style={{ display: "flex", gap: "12px", padding: "8px 10px", background: "#F8FAFC", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", fontWeight: "600", color: "#0F172A" }}>
                    <input
                      type="radio"
                      name="adjDir"
                      checked={adjDirection === 1}
                      onChange={() => setAdjDirection(1)}
                      style={{ accentColor: "#16A34A" }}
                    />
                    <span>Addition (+1) (थप)</span>
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", cursor: "pointer", fontWeight: "600", color: "#0F172A" }}>
                    <input
                      type="radio"
                      name="adjDir"
                      checked={adjDirection === -1}
                      onChange={() => setAdjDirection(-1)}
                      style={{ accentColor: "#DC2626" }}
                    />
                    <span>Deduction (-1) (घटाउ)</span>
                  </label>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Quantity</label>
                  <input
                    type="number"
                    step="0.01"
                    className="input-field num-mono"
                    placeholder="e.g. 5.0"
                    value={adjQuantity}
                    onChange={(e) => setAdjQuantity(e.target.value)}
                    required
                  />
                  {adjDirection === -1 && (
                    <div style={{ fontSize: "11px", color: "#D97706", marginTop: "3px" }}>
                      * Protected by zero-stock floor: cannot deduct more than current ledger balance.
                    </div>
                  )}
                </div>

                <NepaliDatePicker
                  label="Adjustment Date (मिति)"
                  valueAd={adjDateAd}
                  valueBs={adjDateBs}
                  onChange={({ ad, bs }) => {
                    setAdjDateAd(ad);
                    setAdjDateBs(bs);
                  }}
                  required
                />

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", color: "#475569", fontWeight: "700" }}>Supervisor Reason / Notes</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Reason for adjustment authorized by supervisor"
                    value={adjNotes}
                    onChange={(e) => setAdjNotes(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowAdjustmentModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={submittingAdj} style={{ background: "#1E3A8A", borderColor: "#1E3A8A" }}>
                  {submittingAdj ? "Posting..." : "Commit Adjustment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
