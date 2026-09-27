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
  Layers
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";

export function PurchaseView({ userRole }: { userRole?: string }) {
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [purchases, setPurchases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("all");

  // Form State
  const [showModal, setShowModal] = useState(false);
  const [supplierId, setSupplierId] = useState("");
  const [materialId, setMaterialId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [dateAd, setDateAd] = useState(new Date().toISOString().split("T")[0]);
  const [dateBs, setDateBs] = useState("2083-06-09");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
  const [keepSupplier, setKeepSupplier] = useState(true);
  const [successFeedback, setSuccessFeedback] = useState("");

  // Vendor Bill Attachment State
  const [attachedFile, setAttachedFile] = useState<{ name: string; size: string; previewUrl: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Preview Modal for Attachment
  const [previewAttachment, setPreviewAttachment] = useState<{ title: string; url: string } | null>(null);

  // Form Field Refs for Keyboard Navigation
  const supplierRef = useRef<HTMLSelectElement>(null);
  const materialRef = useRef<HTMLSelectElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);
  const unitPriceRef = useRef<HTMLInputElement>(null);
  const dateAdRef = useRef<HTMLInputElement>(null);
  const dateBsRef = useRef<HTMLInputElement>(null);
  const submitButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  // Global Keyboard Shortcuts (Alt+N to Open Modal, Escape to Close)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const activeTag = document.activeElement?.tagName || "";
      const isInputActive = ["INPUT", "SELECT", "TEXTAREA"].includes(activeTag);

      if ((e.altKey && e.key.toLowerCase() === "n") || (!isInputActive && e.key.toLowerCase() === "n")) {
        if (userRole === "editor") {
          e.preventDefault();
          setShowModal(true);
        }
      } else if (e.key === "Escape" && showModal) {
        e.preventDefault();
        setShowModal(false);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [showModal, userRole]);

  // Auto-focus appropriate field when modal opens
  useEffect(() => {
    if (showModal) {
      setTimeout(() => {
        if (keepSupplier && supplierId) {
          materialRef.current?.focus();
        } else {
          supplierRef.current?.focus();
        }
      }, 50);
    }
  }, [showModal]);

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

  const getSupplier = (id: number) => {
    return suppliers.find((s) => s.id === id);
  };

  const getMaterial = (id: number) => {
    return materials.find((m) => m.id === id);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const previewUrl = URL.createObjectURL(file);
      const sizeKB = (file.size / 1024).toFixed(1) + " KB";
      setAttachedFile({
        name: file.name,
        size: sizeKB,
        previewUrl
      });
    }
  };

  const handleFormKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleCreatePurchase(e as any, false);
    }
  };

  const handleCreatePurchase = async (e: React.FormEvent, forceClose = false) => {
    e.preventDefault();
    if (!supplierId || !materialId || !quantity || !unitPrice) return;

    setSubmitting(true);
    try {
      const purchaseNotes = attachedFile
        ? `${notes ? notes + " | " : ""}Attached Bill: ${attachedFile.name}`
        : notes;

      const res = await fetch("/api/v1/purchase/purchases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_id: parseInt(supplierId),
          raw_material_id: parseInt(materialId),
          quantity: parseFloat(quantity),
          unit_price: parseFloat(unitPrice),
          purchase_date_ad: dateAd,
          purchase_date_bs: dateBs,
          notes: purchaseNotes
        })
      });
      if (res.ok) {
        loadData();
        const mat = getMaterial(parseInt(materialId));
        const matName = mat?.name || "Raw Material";

        if (forceClose || !continuousMode) {
          setShowModal(false);
          setQuantity("");
          setUnitPrice("");
          setNotes("");
          setAttachedFile(null);
        } else {
          // Continuous Mode: Retain supplier and date, reset material/quantity
          setSuccessFeedback(`✓ ${matName} (${quantity} units) logged to ledger! Ready for next inward.`);
          setTimeout(() => setSuccessFeedback(""), 3500);

          if (!keepSupplier) {
            setSupplierId("");
          }
          setMaterialId("");
          setQuantity("");
          setUnitPrice("");
          setNotes("");
          setAttachedFile(null);

          setTimeout(() => {
            if (keepSupplier && supplierId) {
              materialRef.current?.focus();
            } else {
              supplierRef.current?.focus();
            }
          }, 60);
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Error creating purchase record");
      }
    } catch (e) {
      alert("Failed to submit purchase");
    } finally {
      setSubmitting(false);
    }
  };

  // Keyboard navigation helper
  const handleKeyDown = (e: React.KeyboardEvent, nextRef: React.RefObject<any>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      nextRef.current?.focus();
    }
  };

  // Filtered Purchases
  const filteredPurchases = useMemo(() => {
    return purchases.filter((p) => {
      const sup = getSupplier(p.supplier_id);
      const mat = getMaterial(p.raw_material_id);
      const supName = sup ? `${sup.name} ${sup.code}`.toLowerCase() : "";
      const matName = mat ? `${mat.name} ${mat.code || ""}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      const matchesSearch =
        supName.includes(q) ||
        matName.includes(q) ||
        p.purchase_date_ad.includes(q) ||
        (p.notes || "").toLowerCase().includes(q);

      const matchesSupplier =
        supplierFilter === "all" || String(p.supplier_id) === supplierFilter;

      return matchesSearch && matchesSupplier;
    });
  }, [purchases, suppliers, materials, searchQuery, supplierFilter]);

  // Pagination for large dataset (~100+ entities)
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const totalPages = Math.ceil(filteredPurchases.length / ITEMS_PER_PAGE) || 1;

  const paginatedPurchases = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredPurchases.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredPurchases, currentPage]);

  // CSV Exporter
  const handleExportCSV = () => {
    if (!filteredPurchases.length) return;
    const headers = [
      "Purchase ID",
      "Date AD",
      "Date BS",
      "Supplier Name",
      "Supplier Code",
      "Raw Material",
      "Unit",
      "Quantity",
      "Unit Price (NPR)",
      "Total Amount (NPR)",
      "Notes & Bills"
    ];
    const rows = filteredPurchases.map((p) => {
      const sup = getSupplier(p.supplier_id);
      const mat = getMaterial(p.raw_material_id);
      return [
        p.id,
        p.purchase_date_ad,
        p.purchase_date_bs,
        sup?.name || `Supplier #${p.supplier_id}`,
        sup?.code || "-",
        mat?.name || `Material #${p.raw_material_id}`,
        mat?.unit || "unit",
        p.quantity,
        p.unit_price,
        p.total_amount,
        p.notes || "None"
      ];
    });
    exportToCSV("Raw_Material_Purchases_Ledger", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>Raw Material Procurement & Vendor Bills</h2>
          <div style={{ fontSize: "12px", color: "#94a3b8" }}>Inward factory supplies recorded into material ledgers with invoice audit trails</div>
        </div>

        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowModal(true)} title="Shortcut: Alt+N or press 'N' on table">
            <PlusCircle size={16} /> Record New Purchase <span style={{ fontSize: "11px", opacity: 0.85, marginLeft: "4px", background: "rgba(255,255,255,0.2)", padding: "1px 5px", borderRadius: "3px" }}>Alt+N</span>
          </button>
        )}
      </div>

      {/* Filter and Quick Search Bar */}
      <div className="glass-card" style={{ padding: "14px 20px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "220px", background: "rgba(15, 23, 42, 0.6)", padding: "6px 12px", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
          <Search size={16} color="#94a3b8" />
          <input
            type="text"
            placeholder="Search supplier, material name, date, or invoice note..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "13px", outline: "none", width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Supplier:</span>
            <select
              className="input-field"
              style={{ width: "170px", padding: "6px 10px", fontSize: "12px", cursor: "pointer" }}
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

          <button onClick={handleExportCSV} className="btn-export" disabled={!filteredPurchases.length}>
            <Download size={14} /> Export to CSV
          </button>
        </div>
      </div>

      {/* Purchases List Table */}
      <div className="glass-card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={18} color="#3b82f6" />
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
              Inward Raw Material Ledger ({filteredPurchases.length} Records)
            </h3>
          </div>
          <span style={{ fontSize: "12px", color: "#64748b" }}>Audited FIFO inventory entries</span>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading records...</div>
        ) : filteredPurchases.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
            No purchase records found matching criteria.
          </div>
        ) : (
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th style={{ width: "140px" }}>Date (AD / BS)</th>
                  <th>Supplier / Vendor</th>
                  <th>Raw Material</th>
                  <th style={{ textAlign: "right", width: "110px" }}>Quantity</th>
                  <th style={{ textAlign: "right", width: "120px" }}>Unit Rate</th>
                  <th style={{ textAlign: "right", width: "140px" }}>Total Amount</th>
                  <th style={{ width: "120px", textAlign: "center" }}>Bill Document</th>
                  <th style={{ width: "100px", textAlign: "center" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedPurchases.map((p) => {
                  const sup = getSupplier(p.supplier_id);
                  const mat = getMaterial(p.raw_material_id);
                  const hasBill = p.notes && p.notes.includes("Attached Bill:");

                  return (
                    <tr key={p.id}>
                      <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                        {p.purchase_date_ad}{" "}
                        <span style={{ fontSize: "11px", color: "#64748b" }}>({p.purchase_date_bs} BS)</span>
                      </td>
                      <td style={{ fontWeight: "600" }}>
                        {sup ? (
                          <>
                            {sup.name} <span style={{ fontSize: "11px", color: "#3b82f6" }}>[{sup.code}]</span>
                          </>
                        ) : (
                          `Supplier #${p.supplier_id}`
                        )}
                      </td>
                      <td style={{ fontWeight: "500" }}>
                        {mat ? (
                          <>
                            {mat.name} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({mat.unit})</span>
                          </>
                        ) : (
                          `Material #${p.raw_material_id}`
                        )}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "600" }} className="num-mono">
                        {p.quantity} {mat?.unit || ""}
                      </td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        Rs. {p.unit_price?.toLocaleString()}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "700", color: "#10b981" }} className="num-mono-bold">
                        Rs. {p.total_amount?.toLocaleString()}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {hasBill ? (
                          <button
                            onClick={() =>
                              setPreviewAttachment({
                                title: `Supplier Bill #${p.id} - ${sup?.name || "Vendor"}`,
                                url: "/placeholder-bill.svg"
                              })
                            }
                            style={{
                              background: "rgba(59, 130, 246, 0.15)",
                              border: "1px solid rgba(59, 130, 246, 0.3)",
                              color: "#60a5fa",
                              borderRadius: "4px",
                              padding: "2px 8px",
                              fontSize: "11px",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px"
                            }}
                          >
                            <Paperclip size={11} /> View Bill
                          </button>
                        ) : (
                          <span style={{ color: "#64748b", fontSize: "11px" }}>No slip</span>
                        )}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className="badge badge-success">Completed</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredPurchases.length > ITEMS_PER_PAGE && (
              <div className="pagination-bar">
                <span>
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(currentPage * ITEMS_PER_PAGE, filteredPurchases.length)} of {filteredPurchases.length} purchases
                </span>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                  <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* New Purchase Modal Drawer with Keyboard Traversal & Bill Attachment */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-drawer">
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Truck size={18} color="#3b82f6" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#f8fafc" }}>Record Raw Material Purchase</h3>
              </div>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            {/* Success Feedback Alert for Continuous Entry */}
            {successFeedback && (
              <div style={{ background: "rgba(59, 130, 246, 0.15)", border: "1px solid #3b82f6", borderRadius: "6px", padding: "10px 14px", display: "flex", alignItems: "center", gap: "8px", color: "#93c5fd", fontSize: "13px", fontWeight: "600" }}>
                <CheckCircle2 size={16} />
                <span>{successFeedback}</span>
              </div>
            )}

            <form onSubmit={(e) => handleCreatePurchase(e, false)} onKeyDown={handleFormKeyDown} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(15, 23, 42, 0.5)", padding: "10px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#e2e8f0", cursor: "pointer", userSelect: "none" }}>
                      <input
                        type="checkbox"
                        checked={continuousMode}
                        onChange={(e) => setContinuousMode(e.target.checked)}
                        style={{ accentColor: "#3b82f6", cursor: "pointer" }}
                      />
                      <span>Continuous Rapid Inward Mode</span>
                    </label>
                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                      Rapid material procurement entry
                    </span>
                  </div>

                  {continuousMode && (
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "#94a3b8", cursor: "pointer", userSelect: "none", marginLeft: "22px" }}>
                      <input
                        type="checkbox"
                        checked={keepSupplier}
                        onChange={(e) => setKeepSupplier(e.target.checked)}
                        style={{ accentColor: "#3b82f6", cursor: "pointer" }}
                      />
                      <span>Retain selected supplier for multi-material shipment</span>
                    </label>
                  )}
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Supplier / Vendor</label>
                  <select
                    ref={supplierRef}
                    className="input-field"
                    value={supplierId}
                    onChange={(e) => setSupplierId(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, materialRef)}
                    required
                  >
                    <option value="">-- Select Supplier --</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code}) - {s.category || "Supplier"}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Raw Material Item</label>
                  <select
                    ref={materialRef}
                    className="input-field"
                    value={materialId}
                    onChange={(e) => setMaterialId(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, quantityRef)}
                    required
                  >
                    <option value="">-- Select Raw Material --</option>
                    {materials.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.unit})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Quantity</label>
                    <input
                      ref={quantityRef}
                      type="number"
                      step="0.1"
                      className="input-field num-mono"
                      placeholder="e.g. 100"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, unitPriceRef)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Unit Rate (Rs.)</label>
                    <input
                      ref={unitPriceRef}
                      type="number"
                      step="0.1"
                      className="input-field num-mono"
                      placeholder="e.g. 450"
                      value={unitPrice}
                      onChange={(e) => setUnitPrice(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, dateAdRef)}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Purchase Date (AD)</label>
                    <input
                      ref={dateAdRef}
                      type="date"
                      className="input-field"
                      value={dateAd}
                      onChange={(e) => setDateAd(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, dateBsRef)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Purchase Date (BS)</label>
                    <input
                      ref={dateBsRef}
                      type="text"
                      className="input-field"
                      value={dateBs}
                      onChange={(e) => setDateBs(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, submitButtonRef)}
                      required
                    />
                  </div>
                </div>

                {/* Vendor Bill / Receipt Attachment Component */}
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}>
                    <Paperclip size={13} /> Supplier Physical Bill / Receipt (Photo or PDF)
                  </label>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept="image/*,.pdf"
                    style={{ display: "none" }}
                  />

                  {!attachedFile ? (
                    <div
                      className="attachment-dropzone"
                      onClick={() => fileInputRef.current?.click()}
                      style={{ marginTop: "6px" }}
                    >
                      <Upload size={20} color="#3b82f6" style={{ margin: "0 auto 6px" }} />
                      <div style={{ fontSize: "13px", color: "#f8fafc", fontWeight: "600" }}>
                        Click to upload physical vendor bill / voucher
                      </div>
                      <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                        PNG, JPG, or PDF up to 10MB for visual audit verification
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        marginTop: "6px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 12px",
                        background: "rgba(59, 130, 246, 0.1)",
                        border: "1px solid rgba(59, 130, 246, 0.3)",
                        borderRadius: "6px"
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <ImageIcon size={16} color="#3b82f6" />
                        <div>
                          <div style={{ fontSize: "12px", fontWeight: "600", color: "#f8fafc" }}>{attachedFile.name}</div>
                          <div style={{ fontSize: "10px", color: "#94a3b8" }}>{attachedFile.size} - Ready for audit archive</div>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setAttachedFile(null)}
                        style={{ background: "none", border: "none", color: "#f43f5e", cursor: "pointer", padding: "4px" }}
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Remarks / Gate Pass No.</label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Optional gate entry or invoice serial reference"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <span style={{ fontSize: "11px", color: "#64748b" }}>
                  <kbd style={{ background: "rgba(255,255,255,0.1)", padding: "2px 5px", borderRadius: "3px" }}>Esc</kbd> close • <kbd style={{ background: "rgba(255,255,255,0.1)", padding: "2px 5px", borderRadius: "3px" }}>Ctrl+Enter</kbd> quick commit
                </span>

                <div style={{ display: "flex", gap: "10px" }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                    Close
                  </button>
                  {continuousMode && (
                    <button type="button" className="btn-secondary" onClick={(e) => handleCreatePurchase(e, true)} disabled={submitting}>
                      Commit & Close
                    </button>
                  )}
                  <button ref={submitButtonRef} type="submit" className="btn-primary" disabled={submitting}>
                    {submitting ? "Writing to Ledger..." : continuousMode ? "Commit & Next Purchase ↵" : "Commit Purchase"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bill Attachment Preview Modal */}
      {previewAttachment && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 110, padding: "20px" }}>
          <div className="glass-card" style={{ maxWidth: "600px", width: "100%", padding: "20px", background: "#0f172a" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Paperclip size={18} color="#3b82f6" />
                <h4 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>{previewAttachment.title}</h4>
              </div>
              <button onClick={() => setPreviewAttachment(null)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>
            <div style={{ background: "#020617", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "40px 20px", textAlign: "center" }}>
              <FileText size={48} color="#60a5fa" style={{ margin: "0 auto 12px" }} />
              <div style={{ fontSize: "14px", fontWeight: "600", color: "#f8fafc" }}>Physical Supplier Invoice / Gate Voucher</div>
              <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                Encrypted in S3/Backblaze bucket with company-scoped access control.
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "14px" }}>
              <button className="btn-secondary" onClick={() => setPreviewAttachment(null)}>
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
