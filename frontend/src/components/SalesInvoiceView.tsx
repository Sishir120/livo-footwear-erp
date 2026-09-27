"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  PlusCircle,
  ShoppingBag,
  Printer,
  FileText,
  CheckCircle2,
  Search,
  Download,
  X,
  CreditCard,
  DollarSign,
  AlertTriangle,
  Receipt,
  Ban
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";

export function SalesInvoiceView({ userRole }: { userRole?: string }) {
  const [clients, setClients] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSubTab, setActiveSubTab] = useState<"invoices" | "orders">("invoices");

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
  const [continuousMode, setContinuousMode] = useState(true);
  const [keepClient, setKeepClient] = useState(true);
  const [successFeedback, setSuccessFeedback] = useState("");

  // Field Refs for Sequential Keyboard Traversal
  const clientRef = useRef<HTMLSelectElement>(null);
  const productRef = useRef<HTMLSelectElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);
  const unitPriceRef = useRef<HTMLInputElement>(null);
  const receivedAmountRef = useRef<HTMLInputElement>(null);
  const orderDateAdRef = useRef<HTMLInputElement>(null);
  const orderDateBsRef = useRef<HTMLInputElement>(null);
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
          setShowOrderModal(true);
        }
      } else if (e.key === "Escape" && showOrderModal) {
        e.preventDefault();
        setShowOrderModal(false);
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [showOrderModal, userRole]);

  // Auto-focus appropriate field when modal opens
  useEffect(() => {
    if (showOrderModal) {
      setTimeout(() => {
        if (keepClient && clientId) {
          productRef.current?.focus();
        } else {
          clientRef.current?.focus();
        }
      }, 50);
    }
  }, [showOrderModal]);

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

  const getClientByOrderId = (orderId: number) => {
    const ord = orders.find((o) => o.id === orderId);
    if (!ord) return null;
    return clients.find((c) => c.id === ord.client_id);
  };

  const getClientById = (id: number) => {
    return clients.find((c) => c.id === id);
  };

  const handleProductChange = (prodId: string) => {
    setProductId(prodId);
    const prod = products.find((p) => String(p.id) === prodId);
    if (prod && prod.unit_price) {
      setUnitPrice(String(prod.unit_price));
    }
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
      handleCreateOrder(e as any, false);
    }
  };

  const handleCreateOrder = async (e: React.FormEvent, forceClose = false) => {
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
        const invRes = await fetch("/api/v1/invoices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sales_order_id: order.id, vat_enabled: false })
        });
        const invData = invRes.ok ? await invRes.json() : null;
        loadData();

        if (forceClose || !continuousMode) {
          setShowOrderModal(false);
          setProductId("");
          setQuantity("10");
          setUnitPrice("");
          setReceivedAmount("0");
        } else {
          // Continuous Mode: Keep modal open, reset product/quantities, retain client if selected
          const invMsg = invData?.invoice_number ? ` (Invoice #${invData.invoice_number})` : "";
          setSuccessFeedback(`✓ Order ${orderNum}${invMsg} issued! Ready for next sale.`);
          setTimeout(() => setSuccessFeedback(""), 3500);

          if (!keepClient) {
            setClientId("");
          }
          setProductId("");
          setQuantity("10");
          setUnitPrice("");
          setReceivedAmount("0");

          setTimeout(() => {
            if (keepClient && clientId) {
              productRef.current?.focus();
            } else {
              clientRef.current?.focus();
            }
          }, 60);
        }
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

  // Filtered Invoices
  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      const client = getClientByOrderId(inv.sales_order_id);
      const clientStr = client ? `${client.name} ${client.code}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      return (
        inv.invoice_number.toLowerCase().includes(q) ||
        clientStr.includes(q) ||
        inv.date_ad.includes(q) ||
        inv.date_bs.includes(q)
      );
    });
  }, [invoices, orders, clients, searchQuery]);

  // Filtered Orders
  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      const client = getClientById(o.client_id);
      const clientStr = client ? `${client.name} ${client.code}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      return (
        o.order_number.toLowerCase().includes(q) ||
        clientStr.includes(q) ||
        o.order_date_ad.includes(q) ||
        o.order_date_bs.includes(q)
      );
    });
  }, [orders, clients, searchQuery]);

  // Pagination for large dataset (~100+ entities)
  const [invoicePage, setInvoicePage] = useState(1);
  const [orderPage, setOrderPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const totalInvoicePages = Math.ceil(filteredInvoices.length / ITEMS_PER_PAGE) || 1;
  const paginatedInvoices = useMemo(() => {
    const start = (invoicePage - 1) * ITEMS_PER_PAGE;
    return filteredInvoices.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredInvoices, invoicePage]);

  const totalOrderPages = Math.ceil(filteredOrders.length / ITEMS_PER_PAGE) || 1;
  const paginatedOrders = useMemo(() => {
    const start = (orderPage - 1) * ITEMS_PER_PAGE;
    return filteredOrders.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredOrders, orderPage]);

  // Nepal VAT Statutory Void Action
  const handleCancelInvoice = async (invoiceId: number) => {
    if (!confirm("Are you sure you want to void this invoice under Nepal VAT statutory rules? This action cannot be undone.")) return;
    try {
      const res = await fetch(`/api/v1/invoices/${invoiceId}/cancel`, { method: "POST" });
      if (res.ok) {
        alert("Invoice marked as VOID successfully.");
        loadData();
      } else {
        const err = await res.json();
        alert(err.detail || "Failed to cancel invoice");
      }
    } catch (e) {
      alert("Network error cancelling invoice");
    }
  };

  // CSV Exporters
  const handleExportInvoices = () => {
    if (!filteredInvoices.length) return;
    const headers = [
      "Invoice Number",
      "Client / Buyer",
      "Date AD",
      "Date BS",
      "Subtotal (NPR)",
      "VAT Amount (NPR)",
      "Total Amount (NPR)",
      "Received (NPR)",
      "Receivable Balance (NPR)",
      "Sequential Integrity Status"
    ];
    const rows = filteredInvoices.map((inv) => {
      const client = getClientByOrderId(inv.sales_order_id);
      return [
        inv.invoice_number,
        client?.name || `Order #${inv.sales_order_id}`,
        inv.date_ad,
        inv.date_bs,
        inv.subtotal_amount,
        inv.vat_amount,
        inv.total_amount,
        inv.received_amount,
        inv.receivable_amount,
        "Immutable Sequential"
      ];
    });
    exportToCSV("Sales_Invoices_Ledger", headers, rows);
  };

  const handleExportOrders = () => {
    if (!filteredOrders.length) return;
    const headers = [
      "Order Number",
      "Client Name",
      "Client Code",
      "Date AD",
      "Date BS",
      "Total Amount (NPR)",
      "Received (NPR)",
      "Receivable (NPR)",
      "Dispatch Status"
    ];
    const rows = filteredOrders.map((o) => {
      const client = getClientById(o.client_id);
      return [
        o.order_number,
        client?.name || `Client #${o.client_id}`,
        client?.code || "-",
        o.order_date_ad,
        o.order_date_bs,
        o.total_amount,
        o.received_amount,
        o.receivable_amount,
        o.delivered ? "Delivered" : "Pending"
      ];
    });
    exportToCSV("Sales_Orders_Ledger", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Title & Action Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "18px", fontWeight: "700", color: "#f8fafc" }}>
            Sales Orders & Issued Sequential Invoices
          </h2>
          <div style={{ fontSize: "12px", color: "#94a3b8" }}>
            Non-resettable, gapless sequential invoice numbers enforced by PostgreSQL UniqueConstraint
          </div>
        </div>

        {userRole === "editor" && (
          <button className="btn-primary" onClick={() => setShowOrderModal(true)} title="Shortcut: Alt+N or press 'N' on table">
            <PlusCircle size={16} /> Record Sale & Issue Invoice <span style={{ fontSize: "11px", opacity: 0.85, marginLeft: "4px", background: "rgba(255,255,255,0.2)", padding: "1px 5px", borderRadius: "3px" }}>Alt+N</span>
          </button>
        )}
      </div>

      {/* Tabs & Search Filter Bar */}
      <div className="glass-card" style={{ padding: "12px 18px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        {/* Sub-tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <button
            onClick={() => setActiveSubTab("invoices")}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "none",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              background: activeSubTab === "invoices" ? "#3b82f6" : "rgba(255,255,255,0.05)",
              color: activeSubTab === "invoices" ? "#ffffff" : "#94a3b8",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <Receipt size={14} /> Issued Invoices ({invoices.length})
          </button>
          <button
            onClick={() => setActiveSubTab("orders")}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "none",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              background: activeSubTab === "orders" ? "#3b82f6" : "rgba(255,255,255,0.05)",
              color: activeSubTab === "orders" ? "#ffffff" : "#94a3b8",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <ShoppingBag size={14} /> Sales Orders ({orders.length})
          </button>
        </div>

        {/* Search & Export */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(15, 23, 42, 0.6)", padding: "4px 10px", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
            <Search size={14} color="#94a3b8" />
            <input
              type="text"
              placeholder="Search invoice number, client..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "12px", outline: "none", width: "180px" }}
            />
          </div>

          <button
            onClick={activeSubTab === "invoices" ? handleExportInvoices : handleExportOrders}
            className="btn-export"
          >
            <Download size={13} /> Export to CSV
          </button>
        </div>
      </div>

      {/* Main Table View */}
      <div className="glass-card" style={{ padding: "18px 20px" }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading records...</div>
        ) : activeSubTab === "invoices" ? (
          /* INVOICES TABLE */
          filteredInvoices.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
              No sales invoices found matching criteria.
            </div>
          ) : (
            <div className="table-container-dense">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th style={{ width: "130px" }}>Invoice No.</th>
                    <th>Billed Customer</th>
                    <th style={{ width: "140px" }}>Date (AD / BS)</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Invoice Total</th>
                    <th style={{ textAlign: "right", width: "120px" }}>Cash Received</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Receivable</th>
                    <th style={{ width: "130px", textAlign: "center" }}>Print Action</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedInvoices.map((inv) => {
                    const client = getClientByOrderId(inv.sales_order_id);
                    return (
                      <tr key={inv.id} style={{ opacity: inv.is_void ? 0.75 : 1 }}>
                        <td style={{ fontWeight: "700", color: inv.is_void ? "#94a3b8" : "#3b82f6", textDecoration: inv.is_void ? "line-through" : "none" }} className="num-mono">
                          {inv.invoice_number}
                          {inv.is_void && (
                            <span style={{ marginLeft: "6px", fontSize: "10px", color: "#f43f5e", background: "rgba(244,63,94,0.15)", border: "1px solid rgba(244,63,94,0.3)", borderRadius: "3px", padding: "1px 4px", textDecoration: "none", display: "inline-block" }}>
                              VOID
                            </span>
                          )}
                        </td>
                        <td style={{ fontWeight: "600" }}>
                          {client ? (
                            <>
                              {client.name} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({client.code})</span>
                            </>
                          ) : (
                            `Order #${inv.sales_order_id}`
                          )}
                        </td>
                        <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                          {inv.date_ad} <span style={{ fontSize: "11px", color: "#64748b" }}>({inv.date_bs} BS)</span>
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700" }} className="num-mono-bold">
                          Rs. {inv.total_amount?.toLocaleString()}
                        </td>
                        <td style={{ textAlign: "right", color: "#10b981", fontWeight: "600" }} className="num-mono">
                          Rs. {inv.received_amount?.toLocaleString()}
                        </td>
                        <td
                          style={{
                            textAlign: "right",
                            color: inv.receivable_amount > 0 ? "#f87171" : "#94a3b8",
                            fontWeight: "600"
                          }}
                          className="num-mono"
                        >
                          Rs. {inv.receivable_amount?.toLocaleString()}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <div style={{ display: "inline-flex", gap: "6px", alignItems: "center" }}>
                            <button
                              className="btn-secondary"
                              style={{ padding: "3px 8px", fontSize: "11px", borderRadius: "4px" }}
                              onClick={() => openPrintableInvoice(inv.id)}
                              title="Open printable tax invoice"
                            >
                              <Printer size={12} /> Tax Invoice
                            </button>
                            {userRole === "editor" && !inv.is_void && (
                              <button
                                className="btn-secondary"
                                style={{ padding: "3px 8px", fontSize: "11px", borderRadius: "4px", color: "#f43f5e", borderColor: "rgba(244,63,94,0.3)" }}
                                onClick={() => handleCancelInvoice(inv.id)}
                                title="Void invoice per Nepal statutory VAT rules"
                              >
                                <Ban size={12} /> Void
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredInvoices.length > ITEMS_PER_PAGE && (
                <div className="pagination-bar">
                  <span>
                    Showing {(invoicePage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(invoicePage * ITEMS_PER_PAGE, filteredInvoices.length)} of {filteredInvoices.length} invoices
                  </span>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      className="pagination-btn"
                      onClick={() => setInvoicePage((p) => Math.max(1, p - 1))}
                      disabled={invoicePage === 1}
                    >
                      Previous
                    </button>
                    <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                      Page {invoicePage} of {totalInvoicePages}
                    </span>
                    <button
                      className="pagination-btn"
                      onClick={() => setInvoicePage((p) => Math.min(totalInvoicePages, p + 1))}
                      disabled={invoicePage === totalInvoicePages}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        ) : (
          /* ORDERS TABLE */
          filteredOrders.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
              No sales orders found matching criteria.
            </div>
          ) : (
            <div className="table-container-dense">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th style={{ width: "130px" }}>Order Number</th>
                    <th>Customer Name</th>
                    <th style={{ width: "140px" }}>Date (AD / BS)</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Total Amount</th>
                    <th style={{ textAlign: "right", width: "120px" }}>Received</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Balance Due</th>
                    <th style={{ width: "110px", textAlign: "center" }}>Dispatch</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedOrders.map((o) => {
                    const client = getClientById(o.client_id);
                    return (
                      <tr key={o.id}>
                        <td style={{ fontWeight: "700", color: "#3b82f6" }} className="num-mono">
                          {o.order_number}
                        </td>
                        <td style={{ fontWeight: "600" }}>
                          {client ? (
                            <>
                              {client.name} <span style={{ fontSize: "11px", color: "#94a3b8" }}>({client.code})</span>
                            </>
                          ) : (
                            `Client #${o.client_id}`
                          )}
                        </td>
                        <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                          {o.order_date_ad} <span style={{ fontSize: "11px", color: "#64748b" }}>({o.order_date_bs} BS)</span>
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700" }} className="num-mono-bold">
                          Rs. {o.total_amount?.toLocaleString()}
                        </td>
                        <td style={{ textAlign: "right", color: "#10b981", fontWeight: "600" }} className="num-mono">
                          Rs. {o.received_amount?.toLocaleString()}
                        </td>
                        <td
                          style={{
                            textAlign: "right",
                            color: o.receivable_amount > 0 ? "#f87171" : "#94a3b8",
                            fontWeight: "600"
                          }}
                          className="num-mono"
                        >
                          Rs. {o.receivable_amount?.toLocaleString()}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <span className={`badge ${o.delivered ? "badge-success" : "badge-warning"}`}>
                            {o.delivered ? "Delivered" : "Pending"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>

              {filteredOrders.length > ITEMS_PER_PAGE && (
                <div className="pagination-bar">
                  <span>
                    Showing {(orderPage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(orderPage * ITEMS_PER_PAGE, filteredOrders.length)} of {filteredOrders.length} sales orders
                  </span>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <button
                      className="pagination-btn"
                      onClick={() => setOrderPage((p) => Math.max(1, p - 1))}
                      disabled={orderPage === 1}
                    >
                      Previous
                    </button>
                    <span style={{ fontSize: "12px", color: "#94a3b8" }}>
                      Page {orderPage} of {totalOrderPages}
                    </span>
                    <button
                      className="pagination-btn"
                      onClick={() => setOrderPage((p) => Math.min(totalOrderPages, p + 1))}
                      disabled={orderPage === totalOrderPages}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        )}
      </div>

      {/* Record Sale Modal Drawer with Sequential Keyboard Navigation */}
      {showOrderModal && (
        <div className="modal-overlay">
          <div className="modal-drawer">
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShoppingBag size={18} color="#3b82f6" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#f8fafc" }}>
                  Record Footwear Sale & Issue Invoice
                </h3>
              </div>
              <button onClick={() => setShowOrderModal(false)} style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={(e) => handleCreateOrder(e, false)} onKeyDown={handleFormKeyDown} style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              <div className="modal-body">
                {/* Success Feedback Toast for Continuous Entry */}
                {successFeedback && (
                  <div style={{ background: "rgba(59, 130, 246, 0.15)", border: "1px solid #3b82f6", borderRadius: "6px", padding: "10px 14px", display: "flex", alignItems: "center", gap: "8px", color: "#93c5fd", fontSize: "13px", fontWeight: "600" }}>
                    <CheckCircle2 size={16} />
                    <span>{successFeedback}</span>
                  </div>
                )}

                <div style={{ display: "flex", flexDirection: "column", gap: "6px", background: "rgba(15, 23, 42, 0.5)", padding: "10px 12px", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#e2e8f0", cursor: "pointer", userSelect: "none" }}>
                      <input
                        type="checkbox"
                        checked={continuousMode}
                        onChange={(e) => setContinuousMode(e.target.checked)}
                        style={{ accentColor: "#3b82f6", cursor: "pointer" }}
                      />
                      <span>Continuous Rapid Entry Mode</span>
                    </label>
                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                      Hands-free rapid sales logging
                    </span>
                  </div>

                  {continuousMode && (
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "#94a3b8", cursor: "pointer", userSelect: "none", marginLeft: "22px" }}>
                      <input
                        type="checkbox"
                        checked={keepClient}
                        onChange={(e) => setKeepClient(e.target.checked)}
                        style={{ accentColor: "#3b82f6", cursor: "pointer" }}
                      />
                      <span>Retain selected client for multiple item orders</span>
                    </label>
                  )}
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Client / Customer</label>
                  <select
                    ref={clientRef}
                    className="input-field"
                    value={clientId}
                    onChange={(e) => setClientId(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, productRef)}
                    required
                  >
                    <option value="">-- Select Client / Distributor --</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code}) - PAN: {c.pan_number || "N/A"}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Footwear SKU</label>
                  <select
                    ref={productRef}
                    className="input-field"
                    value={productId}
                    onChange={(e) => handleProductChange(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, quantityRef)}
                    required
                  >
                    <option value="">-- Select Product Item --</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.code} - {p.name} (Wholesale: Rs. {p.unit_price})
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Quantity (Pairs)</label>
                    <input
                      ref={quantityRef}
                      type="number"
                      className="input-field num-mono"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, unitPriceRef)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Wholesale Unit Rate (Rs.)</label>
                    <input
                      ref={unitPriceRef}
                      type="number"
                      className="input-field num-mono"
                      value={unitPrice}
                      onChange={(e) => setUnitPrice(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, receivedAmountRef)}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Initial Cash Received (Rs.)</label>
                  <input
                    ref={receivedAmountRef}
                    type="number"
                    className="input-field num-mono"
                    value={receivedAmount}
                    onChange={(e) => setReceivedAmount(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, orderDateAdRef)}
                    required
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Order Date (AD)</label>
                    <input
                      ref={orderDateAdRef}
                      type="date"
                      className="input-field"
                      value={orderDateAd}
                      onChange={(e) => setOrderDateAd(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, orderDateBsRef)}
                      required
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "12px", color: "#94a3b8", fontWeight: "600" }}>Order Date (BS)</label>
                    <input
                      ref={orderDateBsRef}
                      type="text"
                      className="input-field"
                      value={orderDateBs}
                      onChange={(e) => setOrderDateBs(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, submitButtonRef)}
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
                  <button type="button" className="btn-secondary" onClick={() => setShowOrderModal(false)}>
                    Close
                  </button>
                  {continuousMode && (
                    <button type="button" className="btn-secondary" onClick={(e) => handleCreateOrder(e, true)} disabled={submitting}>
                      Save & Close
                    </button>
                  )}
                  <button ref={submitButtonRef} type="submit" className="btn-primary" disabled={submitting}>
                    {submitting ? "Writing to Ledger..." : continuousMode ? "Save & Next Sale ↵" : "Save & Issue Invoice"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
