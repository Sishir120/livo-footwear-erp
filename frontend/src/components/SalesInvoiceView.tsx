"use client";

import React, { useState, useEffect } from "react";
import { PlusCircle, ShoppingBag, Printer, FileText, CheckCircle2 } from "lucide-react";

export function SalesInvoiceView({ userRole }: { userRole?: string }) {
  const [clients, setClients] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [clientId, setClientId] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("10");
  const [unitPrice, setUnitPrice] = useState("3200");
  const [receivedAmount, setReceivedAmount] = useState("10000");
  const [orderDateAd, setOrderDateAd] = useState(new Date().toISOString().split("T")[0]);
  const [orderDateBs, setOrderDateBs] = useState("2083-06-09");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [cliRes, prodRes, ordRes, invRes] = await Promise.all([
        fetch("/api/v1/sales/clients"),
        fetch("/api/v1/production/products"),
        fetch("/api/v1/sales/orders"),
        fetch("/api/v1/invoices")
      ]);
      if (cliRes.ok) setClients(await cliRes.json());
      if (prodRes.ok) setProducts(await prodRes.json());
      if (ordRes.ok) setOrders(await ordRes.json());
      if (invRes.ok) setInvoices(await invRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId || !productId || !quantity) return;

    setSubmitting(true);
    try {
      const orderNum = `SO-${Date.now().toString().slice(-4)}`;
      const res = await fetch("/api/v1/sales/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_number: orderNum,
          client_id: parseInt(clientId),
          order_date_ad: orderDateAd,
          order_date_bs: orderDateBs,
          received_amount: parseFloat(receivedAmount || "0"),
          delivered: true,
          items: [
            {
              product_id: parseInt(productId),
              quantity: parseFloat(quantity),
              unit_price: parseFloat(unitPrice)
            }
          ]
        })
      });

      if (res.ok) {
        const order = await res.json();
        // Generate Invoice for the order automatically
        await fetch("/api/v1/invoices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sales_order_id: order.id, vat_enabled: false })
        });

        setShowOrderModal(false);
        loadData();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to create sales order");
      }
    } catch (e) {
      alert("Error saving sales order");
    } finally {
      setSubmitting(false);
    }
  };

  const openPrintableInvoice = (invoiceId: number) => {
    window.open(`/api/v1/invoices/${invoiceId}/printable`, "_blank");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: "20px", fontWeight: "700" }}>Sales Orders & Printable Invoices</h2>
        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowOrderModal(true)}>
            <PlusCircle size={18} /> Record New Sale
          </button>
        )}
      </div>

      {/* Invoices List */}
      <div className="glass-card" style={{ padding: "20px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc" }}>
          Issued Sequential Invoices
        </h3>

        {loading ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>Loading invoices...</div>
        ) : invoices.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", color: "#94a3b8" }}>No sales invoices issued yet.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Invoice Number</th>
                  <th>Date (AD / BS)</th>
                  <th style={{ textAlign: "right" }}>Total Amount</th>
                  <th style={{ textAlign: "right" }}>Received Amt</th>
                  <th style={{ textAlign: "right" }}>Receivable Balance</th>
                  <th>Print Tax Invoice</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td style={{ fontWeight: "700", color: "#3b82f6" }}>{inv.invoice_number}</td>
                    <td>{inv.date_ad} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({inv.date_bs} BS)</span></td>
                    <td style={{ textAlign: "right", fontWeight: "600" }}>Rs. {inv.total_amount.toLocaleString()}</td>
                    <td style={{ textAlign: "right", color: "#34d399", fontWeight: "600" }}>Rs. {inv.received_amount.toLocaleString()}</td>
                    <td style={{ textAlign: "right", color: inv.receivable_amount > 0 ? "#f87171" : "#94a3b8", fontWeight: "600" }}>
                      Rs. {inv.receivable_amount.toLocaleString()}
                    </td>
                    <td>
                      <button className="btn-secondary" style={{ padding: "4px 10px", fontSize: "12px" }} onClick={() => openPrintableInvoice(inv.id)}>
                        <Printer size={14} /> Printable Invoice
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Order Modal */}
      {showOrderModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div className="glass-card" style={{ width: "100%", maxWidth: "520px", padding: "24px", background: "#1e293b" }}>
            <h3 style={{ fontSize: "18px", marginBottom: "16px" }}>Record Footwear Sale & Issue Invoice</h3>
            <form onSubmit={handleCreateOrder} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Client / Customer</label>
                <select className="input-field" value={clientId} onChange={(e) => setClientId(e.target.value)} required>
                  <option value="">-- Select Client --</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Product Item</label>
                <select className="input-field" value={productId} onChange={(e) => setProductId(e.target.value)} required>
                  <option value="">-- Select Product --</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>{p.code} - {p.name} (Rs. {p.unit_price})</option>
                  ))}
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Quantity (pairs)</label>
                  <input type="number" className="input-field" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Unit Rate (Rs.)</label>
                  <input type="number" className="input-field" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} required />
                </div>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "#94a3b8" }}>Received Amount Now (Rs.)</label>
                <input type="number" className="input-field" value={receivedAmount} onChange={(e) => setReceivedAmount(e.target.value)} required />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Order Date AD</label>
                  <input type="date" className="input-field" value={orderDateAd} onChange={(e) => setOrderDateAd(e.target.value)} required />
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8" }}>Order Date BS</label>
                  <input type="text" className="input-field" value={orderDateBs} onChange={(e) => setOrderDateBs(e.target.value)} required />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "12px" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowOrderModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "Writing to Ledger..." : "Save & Issue Invoice"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
