"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  PlusCircle,
  Factory,
  Users,
  CheckCircle2,
  Search,
  Download,
  X,
  Layers,
  Calendar,
  AlertCircle,
  Printer
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";
import { ThermalLabelModal, BoxLabelData } from "./ThermalLabelModal";
import { apiFetch } from "../lib/api";

export function ProductionView({ userRole }: { userRole?: string }) {
  const [products, setProducts] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [productFilter, setProductFilter] = useState("all");

  // Form State
  const [showModal, setShowModal] = useState(false);
  const [batchNumber, setBatchNumber] = useState(`BATCH-${Date.now().toString().slice(-4)}`);
  const [productId, setProductId] = useState("");
  const [targetQty, setTargetQty] = useState("");
  const [producedQty, setProducedQty] = useState("");
  const [workerCount, setWorkerCount] = useState("4");
  const [dateAd, setDateAd] = useState(new Date().toISOString().split("T")[0]);
  const [dateBs, setDateBs] = useState("2083-06-09");
  const [submitting, setSubmitting] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
  const [successFeedback, setSuccessFeedback] = useState("");
  const [showLabelModal, setShowLabelModal] = useState(false);
  const [currentLabelData, setCurrentLabelData] = useState<BoxLabelData>({
    productName: "LIVO FOOTWEAR",
    sku: "",
    size: "41",
    batchNumber: "",
  });

  // Field Refs for Sequential Keyboard Navigation
  const batchNumRef = useRef<HTMLInputElement>(null);
  const productSelectRef = useRef<HTMLSelectElement>(null);
  const targetQtyRef = useRef<HTMLInputElement>(null);
  const producedQtyRef = useRef<HTMLInputElement>(null);
  const workerCountRef = useRef<HTMLInputElement>(null);
  const dateAdRef = useRef<HTMLInputElement>(null);
  const dateBsRef = useRef<HTMLInputElement>(null);
  const submitBtnRef = useRef<HTMLButtonElement>(null);

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

  // Auto-focus first field when modal opens
  useEffect(() => {
    if (showModal) {
      setTimeout(() => {
        if (productId) {
          targetQtyRef.current?.focus();
        } else {
          productSelectRef.current?.focus();
        }
      }, 50);
    }
  }, [showModal]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prodRes, batchRes] = await Promise.all([
        fetch("/api/v1/production/products"),
        fetch("/api/v1/production/batches")
      ]);
      if (prodRes.ok) setProducts(await prodRes.json());
      if (batchRes.ok) setBatches(await batchRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getProduct = (id: number) => {
    return products.find((p) => p.id === id);
  };

  const handleKeyDown = (e: React.KeyboardEvent, nextRef: React.RefObject<any>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      nextRef.current?.focus();
    }
  };

  const handleFormKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleCreateBatch(e as any, false);
    }
  };

  const handleCreateBatch = async (e: React.FormEvent, forceClose = false) => {
    e.preventDefault();
    if (!productId || !producedQty) return;

    setSubmitting(true);
    try {
      const res = await apiFetch("/api/v1/production/batches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          batch_number: batchNumber,
          product_id: parseInt(productId),
          target_quantity: parseFloat(targetQty || producedQty),
          produced_quantity: parseFloat(producedQty),
          worker_count: parseInt(workerCount),
          date_ad: dateAd,
          date_bs: dateBs
        })
      });

      if (res.ok) {
        const savedBatch = batchNumber;
        const prod = getProduct(parseInt(productId));
        setCurrentLabelData({
          productName: prod?.name || "LIVO FOOTWEAR",
          sku: prod?.code || savedBatch,
          size: prod?.size || "41",
          color: prod?.color || "Black",
          batchNumber: savedBatch,
          dateStr: dateAd,
        });
        setShowLabelModal(true);
        loadData();
        if (forceClose || !continuousMode) {
          setShowModal(false);
          setProducedQty("");
          setTargetQty("");
          setProductId("");
          setBatchNumber(`BATCH-${Date.now().toString().slice(-4)}`);
        } else {
          // Continuous Entry Mode: maintain worker count and date, clear entry, advance batch
          setSuccessFeedback(`✓ ${savedBatch} committed to ledger! Box label generated.`);
          setTimeout(() => setSuccessFeedback(""), 3500);
          setProducedQty("");
          setTargetQty("");
          setProductId("");
          setBatchNumber(`BATCH-${Date.now().toString().slice(-4)}`);
          setTimeout(() => {
            productSelectRef.current?.focus();
          }, 60);
        }
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to record production batch");
      }
    } catch (e) {
      alert("Error saving batch");
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered Batches
  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      const p = getProduct(b.product_id);
      const prodName = p ? `${p.name} ${p.code}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      const matchesSearch =
        b.batch_number.toLowerCase().includes(q) ||
        prodName.includes(q) ||
        b.date_ad.includes(q) ||
        b.date_bs.includes(q);

      const matchesProduct =
        productFilter === "all" || String(b.product_id) === productFilter;

      return matchesSearch && matchesProduct;
    });
  }, [batches, products, searchQuery, productFilter]);

  // Pagination for 100+ entities
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const totalPages = Math.ceil(filteredBatches.length / ITEMS_PER_PAGE) || 1;

  const paginatedBatches = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredBatches.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredBatches, currentPage]);

  // CSV Exporter
  const handleExportCSV = () => {
    if (!filteredBatches.length) return;
    const headers = [
      "Batch Number",
      "Date AD",
      "Date BS",
      "Product SKU",
      "Product Name",
      "Size",
      "Color",
      "Target Pairs",
      "Produced Pairs",
      "Active Workers",
      "Status",
      "Stock Inward Movement"
    ];
    const rows = filteredBatches.map((b) => {
      const p = getProduct(b.product_id);
      return [
        b.batch_number,
        b.date_ad,
        b.date_bs,
        p?.code || `ID #${b.product_id}`,
        p?.name || "Product",
        p?.size || "-",
        p?.color || "-",
        b.target_quantity,
        b.produced_quantity,
        b.worker_count,
        b.status,
        `+${b.produced_quantity} pairs`
      ];
    });
    exportToCSV("Production_Batches_Ledger", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Title & Action Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
            Production Batches → Stock Ledger
          </h2>
          <div style={{ fontSize: "12px", color: "#94a3b8" }}>
            Finished production batches automatically trigger append-only stock inward movements
          </div>
        </div>

        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowModal(true)} title="Shortcut: Alt+N or press 'N' on table">
            <PlusCircle size={16} /> Record Finished Batch <span style={{ fontSize: "11px", opacity: 0.85, marginLeft: "4px", background: "rgba(255,255,255,0.2)", padding: "1px 5px", borderRadius: "3px" }}>Alt+N</span>
          </button>
        )}
      </div>

      {/* Filter and Quick Search Bar */}
      <div className="glass-card" style={{ padding: "14px 20px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "220px", background: "rgba(15, 23, 42, 0.6)", padding: "6px 12px", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
          <Search size={16} color="#94a3b8" />
          <input
            type="text"
            placeholder="Search batch number, footwear model, date..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "13px", outline: "none", width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Model:</span>
            <select
              className="input-field"
              style={{ width: "180px", padding: "6px 10px", fontSize: "12px", cursor: "pointer" }}
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
            >
              <option value="all">All Products ({products.length})</option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </div>

          <button onClick={handleExportCSV} className="btn-export" disabled={!filteredBatches.length}>
            <Download size={14} /> Export to CSV
          </button>
        </div>
      </div>

      {/* Batches Table */}
      <div className="glass-card" style={{ padding: "18px 20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Factory size={18} color="#3b82f6" />
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
              Logged Production Batches ({filteredBatches.length} Entries)
            </h3>
          </div>
          <span style={{ fontSize: "12px", color: "#64748b" }}>Immutable manufacturing log</span>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading batches...</div>
        ) : filteredBatches.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
            No production batches found matching criteria.
          </div>
        ) : (
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th className="sticky-col-left-1" style={{ width: "120px" }}>Batch Number</th>
                  <th className="sticky-col-left-2" style={{ minWidth: "160px" }}>Footwear Model</th>
                  <th style={{ width: "130px" }}>Date (AD / BS)</th>
                  <th style={{ width: "65px", textAlign: "center" }}>Size</th>
                  <th style={{ width: "80px" }}>Color</th>
                  <th style={{ textAlign: "right", width: "95px" }}>Target</th>
                  <th style={{ textAlign: "right", width: "115px" }}>Produced</th>
                  <th style={{ textAlign: "right", width: "75px" }}>Workers</th>
                  <th style={{ width: "125px", textAlign: "center" }}>Stock Impact</th>
                  <th style={{ width: "95px", textAlign: "center" }}>Status</th>
                  <th style={{ width: "85px", textAlign: "center" }}>Label</th>
                </tr>
              </thead>
              <tbody>
                {paginatedBatches.map((b) => {
                  const p = getProduct(b.product_id);
                  return (
                    <tr key={b.id}>
                      <td className="sticky-col-left-1 num-mono" style={{ fontWeight: "700", color: "#3b82f6" }}>
                        {b.batch_number}
                      </td>
                      <td className="sticky-col-left-2" style={{ fontWeight: "600", color: "#f8fafc" }}>
                        {p ? (
                          <>
                            {p.code} - {p.name}
                          </>
                        ) : (
                          `Product #${b.product_id}`
                        )}
                      </td>
                      <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                        {b.date_ad} <span style={{ fontSize: "11px", color: "#64748b" }}>({b.date_bs})</span>
                      </td>
                      <td style={{ textAlign: "center" }} className="num-mono">
                        <span style={{ padding: "2px 6px", background: "rgba(37,99,235,0.12)", color: "#60a5fa", borderRadius: "3px", fontWeight: "600", fontSize: "11px" }}>
                          {p?.size || "-"}
                        </span>
                      </td>
                      <td style={{ color: "#94a3b8", fontSize: "11px" }}>{p?.color || "-"}</td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        {b.target_quantity} prs
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "700", color: "#10b981" }} className="num-mono-bold">
                        {b.produced_quantity} pairs
                      </td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        {b.worker_count}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className="badge badge-success num-mono">
                          <CheckCircle2 size={11} style={{ marginRight: "3px" }} /> +{b.produced_quantity} IN
                        </span>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className="badge badge-info">{b.status || "Completed"}</span>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          type="button"
                          onClick={() => {
                            setCurrentLabelData({
                              productName: p?.name || "LIVO FOOTWEAR",
                              sku: p?.code || b.batch_number,
                              size: p?.size || "41",
                              color: p?.color || "-",
                              batchNumber: b.batch_number,
                              dateStr: b.date_ad,
                            });
                            setShowLabelModal(true);
                          }}
                          style={{
                            background: "rgba(255,255,255,0.06)",
                            border: "1px solid rgba(255,255,255,0.15)",
                            color: "#94a3b8",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "11px"
                          }}
                          title="Print 2x1 Thermal Box Label"
                        >
                          <Printer size={12} /> Label
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredBatches.length > ITEMS_PER_PAGE && (
              <div className="pagination-bar" role="navigation" aria-label="Production batch pagination">
                <span>
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(currentPage * ITEMS_PER_PAGE, filteredBatches.length)} of {filteredBatches.length} production batches
                </span>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    aria-label="Previous page of batches"
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
                    aria-label="Next page of batches"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal Drawer Form with Sequential Keyboard Traversal */}
      {showModal && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" aria-labelledby="production-drawer-title">
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Factory size={16} color="#10b981" />
                <h3 id="production-drawer-title" style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
                  Record Finished Production Batch
                </h3>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ display: "flex", gap: "4px" }}>
                  <span className="kbd-hint">Ctrl+Enter ↵</span>
                  <span className="kbd-hint">Esc</span>
                </div>
                <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", marginLeft: "4px" }} aria-label="Close production batch dialog">
                  <X size={18} />
                </button>
              </div>
            </div>

            <form onSubmit={(e) => handleCreateBatch(e, false)} onKeyDown={handleFormKeyDown} style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              <div className="modal-body">
                {/* Success Feedback Alert for Continuous Entry */}
                {successFeedback && (
                  <div role="status" aria-live="polite" style={{ background: "rgba(16, 185, 129, 0.15)", border: "1px solid #10b981", borderRadius: "6px", padding: "10px 14px", display: "flex", alignItems: "center", gap: "8px", color: "#6ee7b7", fontSize: "13px", fontWeight: "600" }}>
                    <CheckCircle2 size={16} />
                    <span>{successFeedback}</span>
                  </div>
                )}

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(15, 23, 42, 0.5)", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#e2e8f0", cursor: "pointer", userSelect: "none" }}>
                    <input
                      type="checkbox"
                      checked={continuousMode}
                      onChange={(e) => setContinuousMode(e.target.checked)}
                      style={{ accentColor: "#10b981", cursor: "pointer" }}
                    />
                    <span>Continuous Rapid Entry Mode</span>
                  </label>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>
                    Keeps form open for back-to-back entries
                  </span>
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Batch Number</label>
                  <input
                    ref={batchNumRef}
                    type="text"
                    className="input-field num-mono"
                    value={batchNumber}
                    onChange={(e) => setBatchNumber(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, productSelectRef)}
                    required
                  />
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Footwear Model SKU</label>
                  <select
                    ref={productSelectRef}
                    className="input-field"
                    value={productId}
                    onChange={(e) => setProductId(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, targetQtyRef)}
                    required
                  >
                    <option value="">-- Select Finished Shoe SKU --</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.code} - {p.name} (Size: {p.size}, {p.color})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Target Pairs</label>
                    <input
                      ref={targetQtyRef}
                      type="number"
                      className="input-field num-mono"
                      placeholder="e.g. 50"
                      value={targetQty}
                      onChange={(e) => setTargetQty(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, producedQtyRef)}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Actual Produced Pairs</label>
                    <input
                      ref={producedQtyRef}
                      type="number"
                      className="input-field num-mono"
                      placeholder="e.g. 50"
                      value={producedQty}
                      onChange={(e) => setProducedQty(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, workerCountRef)}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Active Worker Count</label>
                  <input
                    ref={workerCountRef}
                    type="number"
                    className="input-field num-mono"
                    placeholder="e.g. 4"
                    value={workerCount}
                    onChange={(e) => setWorkerCount(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, dateAdRef)}
                    required
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Production Date (AD)</label>
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
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Production Date (BS)</label>
                    <input
                      ref={dateBsRef}
                      type="text"
                      className="input-field"
                      value={dateBs}
                      onChange={(e) => setDateBs(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, submitBtnRef)}
                      required
                    />
                  </div>
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
                    <button type="button" className="btn-secondary" onClick={(e) => handleCreateBatch(e, true)} disabled={submitting}>
                      Commit & Close
                    </button>
                  )}
                  <button ref={submitBtnRef} type="submit" className="btn-primary" disabled={submitting}>
                    {submitting ? "Writing to Stock Ledger..." : continuousMode ? "Commit & Next Batch ↵" : "Commit Batch"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2x1 Thermal Box Label Print Modal */}
      <ThermalLabelModal
        isOpen={showLabelModal}
        onClose={() => setShowLabelModal(false)}
        labelData={currentLabelData}
      />
    </div>
  );
}
