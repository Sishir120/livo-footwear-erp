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
  AlertCircle
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";

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

  const handleCreateBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productId || !producedQty) return;

    setSubmitting(true);
    try {
      const res = await fetch("/api/v1/production/batches", {
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
        setShowModal(false);
        setProducedQty("");
        setTargetQty("");
        setBatchNumber(`BATCH-${Date.now().toString().slice(-4)}`);
        loadData();
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
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle size={16} /> Record Finished Batch
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
                  <th style={{ width: "130px" }}>Batch Number</th>
                  <th style={{ width: "140px" }}>Date (AD / BS)</th>
                  <th>Footwear Model</th>
                  <th style={{ width: "70px", textAlign: "center" }}>Size</th>
                  <th style={{ width: "90px" }}>Color</th>
                  <th style={{ textAlign: "right", width: "110px" }}>Target</th>
                  <th style={{ textAlign: "right", width: "130px" }}>Produced</th>
                  <th style={{ textAlign: "right", width: "90px" }}>Workers</th>
                  <th style={{ width: "120px", textAlign: "center" }}>Stock Impact</th>
                  <th style={{ width: "100px", textAlign: "center" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredBatches.map((b) => {
                  const p = getProduct(b.product_id);
                  return (
                    <tr key={b.id}>
                      <td style={{ fontWeight: "700", color: "#3b82f6" }} className="num-mono">
                        {b.batch_number}
                      </td>
                      <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                        {b.date_ad} <span style={{ fontSize: "11px", color: "#64748b" }}>({b.date_bs} BS)</span>
                      </td>
                      <td style={{ fontWeight: "600" }}>
                        {p ? (
                          <>
                            {p.code} - {p.name}
                          </>
                        ) : (
                          `Product #${b.product_id}`
                        )}
                      </td>
                      <td style={{ textAlign: "center" }} className="num-mono">
                        {p?.size || "-"}
                      </td>
                      <td style={{ color: "#94a3b8" }}>{p?.color || "-"}</td>
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
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Form with Sequential Keyboard Traversal */}
      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: "16px" }}>
          <div className="glass-card" style={{ width: "100%", maxWidth: "520px", padding: "24px", background: "#131d33", border: "1px solid rgba(255,255,255,0.15)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Factory size={20} color="#10b981" />
                <h3 style={{ fontSize: "17px", fontWeight: "700", color: "#f8fafc" }}>
                  Record Finished Production Batch
                </h3>
              </div>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateBatch} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
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
                  autoFocus
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

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button ref={submitBtnRef} type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Writing to Stock Ledger..." : "Commit Batch"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
