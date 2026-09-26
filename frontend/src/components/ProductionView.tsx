"use client";

import React, { useState, useEffect } from "react";
import { PlusCircle, Factory, Users, CheckCircle2 } from "lucide-react";

export function ProductionView({ userRole }: { userRole?: string }) {
  const [products, setProducts] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: "20px", fontWeight: "700" }}>Production Batches → Stock Ledger</h2>
        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle size={18} /> Record Finished Batch
          </button>
        )}
      </div>

      {/* Batches list */}
      <div className="glass-card" style={{ padding: "20px" }}>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>Loading batches...</div>
        ) : batches.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>No finished production batches recorded yet.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date (AD / BS)</th>
                  <th>Batch Number</th>
                  <th>Product ID</th>
                  <th style={{ textAlign: "right" }}>Target Pairs</th>
                  <th style={{ textAlign: "right" }}>Produced Pairs</th>
                  <th style={{ textAlign: "right" }}>Active Workers</th>
                  <th>Stock Movement</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((b) => (
                  <tr key={b.id}>
                    <td>{b.date_ad} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({b.date_bs} BS)</span></td>
                    <td style={{ fontWeight: "700", color: "#3b82f6" }}>{b.batch_number}</td>
                    <td>Product #{b.product_id}</td>
                    <td style={{ textAlign: "right" }}>{b.target_quantity}</td>
                    <td style={{ textAlign: "right", fontWeight: "700", color: "#34d399" }}>
                      {b.produced_quantity} pairs
                    </td>
                    <td style={{ textAlign: "right" }}>{b.worker_count}</td>
                    <td>
                      <span className="badge badge-success">
                        <CheckCircle2 size={12} style={{ marginRight: "4px" }} /> +{b.produced_quantity} IN
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal Form */}
      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div className="glass-card" style={{ width: "100%", maxWidth: "500px", padding: "24px", background: "#1e293b" }}>
            <h3 style={{ fontSize: "18px", marginBottom: "16px" }}>Record Finished Production Batch</h3>
            <form onSubmit={handleCreateBatch} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Batch Number</label>
                <input type="text" className="input-field" value={batchNumber} onChange={(e) => setBatchNumber(e.target.value)} required />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Footwear Product</label>
                <select className="input-field" value={productId} onChange={(e) => setProductId(e.target.value)} required>
                  <option value="">-- Select Product --</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.code} - {p.name} (Size: {p.size}, {p.color})</option>
                  ))}
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Produced Pairs</label>
                  <input type="number" className="input-field" placeholder="e.g. 50" value={producedQty} onChange={(e) => setProducedQty(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Worker Count</label>
                  <input type="number" className="input-field" value={workerCount} onChange={(e) => setWorkerCount(e.target.value)} required />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Date AD</label>
                  <input type="date" className="input-field" value={dateAd} onChange={(e) => setDateAd(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Date BS</label>
                  <input type="text" className="input-field" value={dateBs} onChange={(e) => setDateBs(e.target.value)} required />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "12px" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Writing to Ledger..." : "Save Batch"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
