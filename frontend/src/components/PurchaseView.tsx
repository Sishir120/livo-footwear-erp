"use client";

import React, { useState, useEffect } from "react";
import { PlusCircle, FileText, Truck, PackageCheck } from "lucide-react";

export function PurchaseView({ userRole }: { userRole?: string }) {
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [purchases, setPurchases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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

  const handleCreatePurchase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierId || !materialId || !quantity || !unitPrice) return;

    setSubmitting(true);
    try {
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
          notes
        })
      });
      if (res.ok) {
        setShowModal(false);
        setQuantity("");
        setUnitPrice("");
        setNotes("");
        loadData();
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: "20px", fontWeight: "700" }}>Raw Material Purchases</h2>
        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <PlusCircle size={18} /> Record New Purchase
          </button>
        )}
      </div>

      {/* Purchases List */}
      <div className="glass-card" style={{ padding: "20px" }}>
        {loading ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>Loading records...</div>
        ) : purchases.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>No raw material purchases recorded yet.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date (AD / BS)</th>
                  <th>Supplier ID</th>
                  <th>Material ID</th>
                  <th style={{ textAlign: "right" }}>Quantity</th>
                  <th style={{ textAlign: "right" }}>Unit Price</th>
                  <th style={{ textAlign: "right" }}>Total Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {purchases.map((p) => (
                  <tr key={p.id}>
                    <td>{p.purchase_date_ad} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({p.purchase_date_bs} BS)</span></td>
                    <td>Supplier #{p.supplier_id}</td>
                    <td>Material #{p.raw_material_id}</td>
                    <td style={{ textAlign: "right", fontWeight: "600" }}>{p.quantity}</td>
                    <td style={{ textAlign: "right" }}>Rs. {p.unit_price.toLocaleString()}</td>
                    <td style={{ textAlign: "right", fontWeight: "700", color: "#34d399" }}>
                      Rs. {p.total_amount.toLocaleString()}
                    </td>
                    <td><span className="badge badge-success">Completed</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Entry Modal */}
      {showModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div className="glass-card" style={{ width: "100%", maxWidth: "500px", padding: "24px", background: "#1e293b" }}>
            <h3 style={{ fontSize: "18px", marginBottom: "16px" }}>Record Raw Material Purchase</h3>
            <form onSubmit={handleCreatePurchase} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Supplier</label>
                <select className="input-field" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required>
                  <option value="">-- Select Supplier --</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Raw Material</label>
                <select className="input-field" value={materialId} onChange={(e) => setMaterialId(e.target.value)} required>
                  <option value="">-- Select Raw Material --</option>
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>{m.name} ({m.unit})</option>
                  ))}
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Quantity</label>
                  <input type="number" step="0.1" className="input-field" placeholder="e.g. 100" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Unit Rate (Rs.)</label>
                  <input type="number" step="0.1" className="input-field" placeholder="e.g. 450" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} required />
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
                  {submitting ? "Saving..." : "Save Purchase"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
