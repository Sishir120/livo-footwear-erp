"use client";

import React, { useState, useEffect } from "react";
import {
  Truck,
  ArrowRight,
  Plus,
  RefreshCw,
  X,
  CheckCircle,
  AlertTriangle,
  Clock,
  Ban,
  PackageCheck
} from "lucide-react";
import { useLocale } from "../context/LocaleContext";
import { todayBs } from "../lib/nepaliDate";

interface StockTransferModalProps {
  isOpen: boolean;
  onClose: () => void;
  userRole?: string;
  onSuccess?: () => void;
}

interface TransferItemRow {
  product_id: number;
  product_code?: string;
  product_name?: string;
  size?: string;
  requested_quantity: number;
  dispatched_quantity: number;
  received_quantity: number;
  discrepancy_quantity: number;
  discrepancy_reason?: string;
}

interface TransferSummary {
  id: number;
  transfer_number: string;
  source_warehouse_id: number;
  source_warehouse_name: string;
  destination_warehouse_id: number;
  destination_warehouse_name: string;
  status: "DRAFT" | "IN_TRANSIT" | "PARTIALLY_RECEIVED" | "RECEIVED" | "CANCELLED";
  transfer_date_ad: string;
  transfer_date_bs: string;
  dispatch_date_ad?: string;
  receipt_date_ad?: string;
  carrier_name?: string;
  vehicle_number?: string;
  items_count: number;
  created_at: string;
}

export function StockTransferModal({ isOpen, onClose, userRole }: StockTransferModalProps) {
  const { locale } = useLocale();
  const [transfers, setTransfers] = useState<TransferSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTransfer, setSelectedTransfer] = useState<any>(null);
  const [showReceiveModal, setShowReceiveModal] = useState(false);

  // Form states
  const [warehouses, setWarehouses] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [sourceWhId, setSourceWhId] = useState<number | "">("");
  const [destWhId, setDestWhId] = useState<number | "">("");
  const [transferDateAd, setTransferDateAd] = useState(() => new Date().toISOString().split("T")[0]);
  const [transferDateBs, setTransferDateBs] = useState(() => {
    try { return todayBs().formatted; } catch { return "2083-01-01"; }
  });
  const [carrierName, setCarrierName] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [transferNotes, setTransferNotes] = useState("");
  const [itemProductId, setItemProductId] = useState<number | "">("");
  const [itemSize, setItemSize] = useState("41");
  const [itemQuantity, setItemQuantity] = useState("10");
  const [pendingItems, setPendingItems] = useState<{ product_id: number; product_name: string; size: string; quantity: number }[]>([]);

  // Receive state
  const [receiveQuantities, setReceiveQuantities] = useState<Record<number, number>>({});
  const [discrepancyReasons, setDiscrepancyReasons] = useState<Record<number, string>>({});
  const [isFinalReceipt, setIsFinalReceipt] = useState(true);
  const [receiveNotes, setReceiveNotes] = useState("");

  // Notification
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchTransfers();
      fetchWarehousesAndProducts();
    }
  }, [isOpen, statusFilter]);

  const fetchTransfers = async () => {
    setLoading(true);
    try {
      let url = "/api/v1/transfers?limit=200";
      if (statusFilter !== "ALL") {
        url += `&status=${statusFilter}`;
      }
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTransfers(data.items || []);
      }
    } catch (e) {
      console.error("Failed to load transfers", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchWarehousesAndProducts = async () => {
    try {
      const [whRes, pRes] = await Promise.all([
        fetch("/api/v1/stock/warehouses"),
        fetch("/api/v1/stock/balance?limit=100")
      ]);
      if (whRes.ok) {
        const whData = await whRes.json();
        setWarehouses(whData.items || whData || []);
      }
      if (pRes.ok) {
        const pData = await pRes.json();
        setProducts(pData.items || pData || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddItem = () => {
    if (!itemProductId || Number(itemQuantity) <= 0) return;
    const prod = products.find((p) => p.id === Number(itemProductId));
    setPendingItems([
      ...pendingItems,
      {
        product_id: Number(itemProductId),
        product_name: prod ? `${prod.name} (${prod.code})` : `Product #${itemProductId}`,
        size: itemSize,
        quantity: Number(itemQuantity)
      }
    ]);
    setItemProductId("");
    setItemQuantity("10");
  };

  const handleCreateTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sourceWhId || !destWhId || pendingItems.length === 0) {
      setErrorMsg(locale === "en" ? "Select source, destination, and at least one item" : "स्रोत, गन्तव्य गोदाम र कम्तीमा एक वस्तु चयन गर्नुहोस्");
      return;
    }
    if (sourceWhId === destWhId) {
      setErrorMsg(locale === "en" ? "Source and destination cannot be identical" : "स्रोत र गन्तव्य गोदाम एउटै हुन सक्दैनन्");
      return;
    }

    try {
      const res = await fetch("/api/v1/transfers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_warehouse_id: Number(sourceWhId),
          destination_warehouse_id: Number(destWhId),
          transfer_date_ad: transferDateAd,
          transfer_date_bs: transferDateBs,
          carrier_name: carrierName.trim() || null,
          vehicle_number: vehicleNumber.trim() || null,
          notes: transferNotes.trim() || null,
          items: pendingItems.map((itm) => ({
            product_id: itm.product_id,
            size: itm.size,
            quantity: itm.quantity
          }))
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Failed to create transfer");
        return;
      }
      setSuccessMsg(locale === "en" ? "Transfer created in DRAFT state!" : "स्थानान्तरण ड्राफ्ट सिर्जना भयो!");
      setTimeout(() => setSuccessMsg(null), 3500);
      setShowCreateModal(false);
      setPendingItems([]);
      fetchTransfers();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create transfer");
    }
  };

  const handleDispatch = async (tId: number) => {
    if (!window.confirm(locale === "en" ? "Confirm dispatch? Source warehouse stock will be deducted." : "सामान पठाउने निश्चित गर्नुहोस्? स्रोत गोदामबाट मौज्दात घट्नेछ।")) return;
    try {
      const res = await fetch(`/api/v1/transfers/${tId}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Dispatch failed");
        return;
      }
      setSuccessMsg(locale === "en" ? "Dispatched! Transfer is now IN TRANSIT." : "सामान पठाइयो! स्थानान्तरण बाटोमा (In-Transit) छ।");
      setTimeout(() => setSuccessMsg(null), 3500);
      fetchTransfers();
    } catch (err) {
      console.error(err);
    }
  };

  const openReceiveModal = async (t: TransferSummary) => {
    try {
      const res = await fetch(`/api/v1/transfers/${t.id}`);
      if (res.ok) {
        const full = await res.json();
        setSelectedTransfer(full);
        const qMap: Record<number, number> = {};
        full.items.forEach((itm: any) => {
          const remaining = Math.max(0, itm.dispatched_quantity - itm.received_quantity);
          qMap[itm.id] = remaining;
        });
        setReceiveQuantities(qMap);
        setIsFinalReceipt(true);
        setShowReceiveModal(true);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleConfirmReceive = async () => {
    if (!selectedTransfer) return;
    try {
      const payload = {
        receipt_date_ad: new Date().toISOString().split("T")[0],
        receipt_date_bs: todayBs().formatted,
        is_final: isFinalReceipt,
        items: selectedTransfer.items.map((itm: any) => ({
          item_id: itm.id,
          received_quantity: Number(receiveQuantities[itm.id] ?? Math.max(0, itm.dispatched_quantity - itm.received_quantity)),
          discrepancy_reason: discrepancyReasons[itm.id] || null
        })),
        notes: receiveNotes.trim() || null
      };

      const res = await fetch(`/api/v1/transfers/${selectedTransfer.id}/receive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Receipt failed");
        return;
      }
      setSuccessMsg(locale === "en" ? "Goods received and verified at destination warehouse!" : "सामान गन्तव्य गोदाममा दाखिला भयो!");
      setTimeout(() => setSuccessMsg(null), 3500);
      setShowReceiveModal(false);
      setSelectedTransfer(null);
      fetchTransfers();
    } catch (e) {
      console.error(e);
    }
  };

  const handleCancel = async (tId: number, status: string) => {
    const promptMsg = (status === "IN_TRANSIT" || status === "PARTIALLY_RECEIVED")
      ? (locale === "en" ? "Cancel transfer? Unreceived in-transit stock will be restored to source warehouse." : "बाटोमा रहेको स्थानान्तरण रद्द गर्ने? प्राप्त नभएको मौज्दात स्रोत गोदाममा फिर्ता हुनेछ।")
      : (locale === "en" ? "Cancel draft transfer?" : "ड्राफ्ट स्थानान्तरण रद्द गर्ने?");
    if (!window.confirm(promptMsg)) return;

    try {
      const res = await fetch(`/api/v1/transfers/${tId}/cancel`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "Cancellation failed");
        return;
      }
      setSuccessMsg(locale === "en" ? "Transfer cancelled successfully." : "स्थानान्तरण रद्द भयो।");
      setTimeout(() => setSuccessMsg(null), 3500);
      fetchTransfers();
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1100, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(15, 23, 42, 0.65)", backdropFilter: "blur(4px)", padding: "20px" }}>
      <div style={{ background: "#FFFFFF", borderRadius: "10px", width: "100%", maxWidth: "1100px", maxHeight: "90vh", display: "flex", flexDirection: "column", boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)", overflow: "hidden" }}>
        
        {/* Modal Header */}
        <div style={{ padding: "18px 24px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "36px", height: "36px", background: "#1E3A8A", color: "#FFFFFF", borderRadius: "8px" }}>
              <Truck size={20} />
            </span>
            <div>
              <h2 style={{ fontSize: "17px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                {locale === "en" ? "Multi-Warehouse Stock Transfers & Destination Receipts" : "अन्तर-गोदाम मौज्दात स्थानान्तरण तथा प्राप्ति"}
              </h2>
              <p style={{ fontSize: "12px", color: "#64748B", margin: "2px 0 0 0" }}>
                {locale === "en" ? "Source dispatch, in-transit custody tracking, and independent destination goods receipt." : "स्रोत गोदामबाट निकासी, इन-ट्रान्जिट अनुगमन, र गन्तव्य गोदाममा स्वतन्त्र दाखिला।" }
              </p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", padding: "6px" }}>
            <X size={20} />
          </button>
        </div>

        {/* Alerts */}
        {successMsg && (
          <div style={{ margin: "14px 24px 0 24px", padding: "10px 14px", background: "#ECFDF5", border: "1px solid #A7F3D0", borderRadius: "6px", color: "#065F46", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle size={16} />
            {successMsg}
          </div>
        )}
        {errorMsg && (
          <div style={{ margin: "14px 24px 0 24px", padding: "10px 14px", background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "6px", color: "#991B1B", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertTriangle size={16} />
            {errorMsg}
          </div>
        )}

        {/* Toolbar */}
        <div style={{ padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #F1F5F9", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span style={{ fontSize: "12.5px", fontWeight: "600", color: "#475569" }}>{locale === "en" ? "Status:" : "अवस्था:"}</span>
            {["ALL", "DRAFT", "IN_TRANSIT", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                style={{
                  padding: "5px 10px",
                  borderRadius: "4px",
                  border: statusFilter === st ? "1px solid #1E3A8A" : "1px solid #CBD5E1",
                  background: statusFilter === st ? "#EFF6FF" : "#FFFFFF",
                  color: statusFilter === st ? "#1E3A8A" : "#475569",
                  fontSize: "12px",
                  fontWeight: "600",
                  cursor: "pointer"
                }}
              >
                {st}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button onClick={fetchTransfers} style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "7px 12px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12.5px", fontWeight: "600", color: "#334155", cursor: "pointer" }}>
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              {locale === "en" ? "Refresh" : "ताजा"}
            </button>
            {userRole !== "viewer" && (
              <button onClick={() => setShowCreateModal(true)} style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "7px 14px", background: "#1E3A8A", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "12.5px", fontWeight: "600", cursor: "pointer" }}>
                <Plus size={15} />
                {locale === "en" ? "+ New Transfer" : "+ नयाँ स्थानान्तरण"}
              </button>
            )}
          </div>
        </div>

        {/* Transfers Table */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "2px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px" }}>{locale === "en" ? "Transfer #" : "नम्बर"}</th>
                <th style={{ padding: "10px" }}>{locale === "en" ? "Source Location" : "स्रोत गोदाम"}</th>
                <th style={{ padding: "10px" }}>{locale === "en" ? "Destination" : "गन्तव्य गोदाम"}</th>
                <th style={{ padding: "10px" }}>{locale === "en" ? "Date (BS/AD)" : "मिति"}</th>
                <th style={{ padding: "10px" }}>{locale === "en" ? "Carrier / Vehicle" : "यातायात"}</th>
                <th style={{ padding: "10px", textAlign: "center" }}>{locale === "en" ? "Status" : "अवस्था"}</th>
                <th style={{ padding: "10px", textAlign: "right" }}>{locale === "en" ? "Actions" : "कार्यहरू"}</th>
              </tr>
            </thead>
            <tbody>
              {transfers.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "30px", textAlign: "center", color: "#94A3B8" }}>
                    {locale === "en" ? "No transfers recorded in this status." : "कुनै स्थानान्तरण भेटिएन।"}
                  </td>
                </tr>
              ) : (
                transfers.map((t) => (
                  <tr key={t.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={{ padding: "10px", fontWeight: "600", color: "#0F172A" }}>{t.transfer_number}</td>
                    <td style={{ padding: "10px", color: "#334155" }}>{t.source_warehouse_name || `WH #${t.source_warehouse_id}`}</td>
                    <td style={{ padding: "10px", color: "#334155" }}>
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                        <ArrowRight size={13} color="#94A3B8" />
                        {t.destination_warehouse_name || `WH #${t.destination_warehouse_id}`}
                      </span>
                    </td>
                    <td style={{ padding: "10px", color: "#64748B" }}>{t.transfer_date_bs} <span style={{ fontSize: "11px" }}>({t.transfer_date_ad})</span></td>
                    <td style={{ padding: "10px", color: "#64748B" }}>
                      {t.carrier_name ? `${t.carrier_name} ${t.vehicle_number ? `(${t.vehicle_number})` : ""}` : "—"}
                    </td>
                    <td style={{ padding: "10px", textAlign: "center" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "3px 8px",
                          borderRadius: "12px",
                          fontSize: "11px",
                          fontWeight: "700",
                          background:
                            t.status === "RECEIVED" ? "#DCFCE7" :
                            t.status === "IN_TRANSIT" ? "#FEF3C7" :
                            t.status === "PARTIALLY_RECEIVED" ? "#E0E7FF" :
                            t.status === "CANCELLED" ? "#FEE2E2" : "#F1F5F9",
                          color:
                            t.status === "RECEIVED" ? "#15803D" :
                            t.status === "IN_TRANSIT" ? "#B45309" :
                            t.status === "PARTIALLY_RECEIVED" ? "#4338CA" :
                            t.status === "CANCELLED" ? "#B91C1C" : "#475569"
                        }}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px", textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "6px" }}>
                        {t.status === "DRAFT" && userRole !== "viewer" && (
                          <button
                            onClick={() => handleDispatch(t.id)}
                            style={{ padding: "4px 8px", background: "#1E3A8A", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: "600", cursor: "pointer" }}
                          >
                            {locale === "en" ? "Dispatch" : "पठाउनुहोस्"}
                          </button>
                        )}
                        {(t.status === "IN_TRANSIT" || t.status === "PARTIALLY_RECEIVED") && userRole !== "viewer" && (
                          <button
                            onClick={() => openReceiveModal(t)}
                            style={{ padding: "4px 8px", background: "#047857", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "11px", fontWeight: "600", cursor: "pointer" }}
                          >
                            {locale === "en" ? "Receive" : "दाखिला गर्नुहोस्"}
                          </button>
                        )}
                        {(t.status === "DRAFT" || t.status === "IN_TRANSIT" || t.status === "PARTIALLY_RECEIVED") && userRole !== "viewer" && (
                          <button
                            onClick={() => handleCancel(t.id, t.status)}
                            style={{ padding: "4px 8px", background: "#FFFFFF", color: "#BE123C", border: "1px solid #FECDD3", borderRadius: "4px", fontSize: "11px", fontWeight: "600", cursor: "pointer" }}
                          >
                            {locale === "en" ? "Cancel" : "रद्द"}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Modal Footer */}
        <div style={{ padding: "12px 24px", borderTop: "1px solid #E2E8F0", background: "#F8FAFC", display: "flex", justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "7px 16px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12.5px", fontWeight: "600", color: "#334155", cursor: "pointer" }}>
            {locale === "en" ? "Close" : "बन्द गर्नुहोस्"}
          </button>
        </div>
      </div>

      {/* CREATE TRANSFER SUB-MODAL */}
      {showCreateModal && (
        <div style={{ position: "fixed", inset: 0, zIndex: 1200, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0, 0, 0, 0.5)", padding: "20px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "8px", width: "100%", maxWidth: "600px", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #E2E8F0", paddingBottom: "10px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "700", margin: 0 }}>{locale === "en" ? "Create Stock Transfer" : "नयाँ मौज्दात स्थानान्तरण"}</h3>
              <button onClick={() => setShowCreateModal(false)} style={{ background: "none", border: "none", cursor: "pointer" }}><X size={18} /></button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", color: "#475569" }}>{locale === "en" ? "Source Warehouse" : "स्रोत गोदाम"}</label>
                <select value={sourceWhId} onChange={(e) => setSourceWhId(e.target.value ? Number(e.target.value) : "")} style={{ width: "100%", padding: "7px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px", marginTop: "3px" }}>
                  <option value="">{locale === "en" ? "-- Select Source --" : "-- स्रोत चयन --"}</option>
                  {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", color: "#475569" }}>{locale === "en" ? "Destination Warehouse" : "गन्तव्य गोदाम"}</label>
                <select value={destWhId} onChange={(e) => setDestWhId(e.target.value ? Number(e.target.value) : "")} style={{ width: "100%", padding: "7px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px", marginTop: "3px" }}>
                  <option value="">{locale === "en" ? "-- Select Destination --" : "-- गन्तव्य चयन --"}</option>
                  {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", color: "#475569" }}>{locale === "en" ? "Carrier Name" : "यातायात कम्पनी"}</label>
                <input value={carrierName} onChange={(e) => setCarrierName(e.target.value)} placeholder="e.g. Sajha Cargo" style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px", marginTop: "3px" }} />
              </div>
              <div>
                <label style={{ fontSize: "12px", fontWeight: "600", color: "#475569" }}>{locale === "en" ? "Vehicle Number" : "गाडी नम्बर"}</label>
                <input value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)} placeholder="e.g. BA 2 KHA 1234" style={{ width: "100%", padding: "6px 8px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px", marginTop: "3px" }} />
              </div>
            </div>

            {/* Item Entry */}
            <div style={{ padding: "10px", background: "#F8FAFC", borderRadius: "6px", border: "1px solid #E2E8F0" }}>
              <div style={{ fontSize: "12px", fontWeight: "700", marginBottom: "8px", color: "#0F172A" }}>{locale === "en" ? "Add Transfer Items" : "वस्तुहरू थप्नुहोस्"}</div>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr auto", gap: "8px", alignItems: "flex-end" }}>
                <div>
                  <label style={{ fontSize: "11px", color: "#64748B" }}>Product</label>
                  <select value={itemProductId} onChange={(e) => setItemProductId(e.target.value ? Number(e.target.value) : "")} style={{ width: "100%", padding: "6px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px" }}>
                    <option value="">-- Product --</option>
                    {products.map((p) => <option key={p.product_id || p.id} value={p.product_id || p.id}>{p.name} ({p.code})</option>)}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "#64748B" }}>Size</label>
                  <input value={itemSize} onChange={(e) => setItemSize(e.target.value)} style={{ width: "100%", padding: "6px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px" }} />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "#64748B" }}>Qty</label>
                  <input type="number" value={itemQuantity} onChange={(e) => setItemQuantity(e.target.value)} style={{ width: "100%", padding: "6px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "12px" }} />
                </div>
                <button type="button" onClick={handleAddItem} style={{ padding: "7px 12px", background: "#047857", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}>+ Add</button>
              </div>

              {pendingItems.length > 0 && (
                <div style={{ marginTop: "10px" }}>
                  {pendingItems.map((itm, idx) => (
                    <div key={idx} style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", padding: "4px 0", borderBottom: "1px dashed #CBD5E1" }}>
                      <span>{itm.product_name} (Size {itm.size})</span>
                      <span style={{ fontWeight: "600" }}>{itm.quantity} pairs</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "10px" }}>
              <button type="button" onClick={() => setShowCreateModal(false)} style={{ padding: "7px 14px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12px", cursor: "pointer" }}>Cancel</button>
              <button type="button" onClick={handleCreateTransfer} style={{ padding: "7px 14px", background: "#1E3A8A", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}>Save Draft Transfer</button>
            </div>
          </div>
        </div>
      )}

      {/* DESTINATION RECEIPT MODAL */}
      {showReceiveModal && selectedTransfer && (
        <div style={{ position: "fixed", inset: 0, zIndex: 1200, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0, 0, 0, 0.5)", padding: "20px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "8px", width: "100%", maxWidth: "650px", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #E2E8F0", paddingBottom: "10px" }}>
              <div>
                <h3 style={{ fontSize: "15px", fontWeight: "700", margin: 0 }}>Destination Goods Receipt ({selectedTransfer.transfer_number})</h3>
                <p style={{ fontSize: "12px", color: "#64748B", margin: 0 }}>Receiving at: {selectedTransfer.destination_warehouse_name}</p>
              </div>
              <button onClick={() => setShowReceiveModal(false)} style={{ background: "none", border: "none", cursor: "pointer" }}><X size={18} /></button>
            </div>

            <div style={{ maxHeight: "300px", overflowY: "auto" }}>
              <table style={{ width: "100%", fontSize: "12px", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#F8FAFC", textAlign: "left", color: "#64748B" }}>
                    <th style={{ padding: "6px" }}>Item</th>
                    <th style={{ padding: "6px" }}>Dispatched</th>
                    <th style={{ padding: "6px" }}>Prior Recv</th>
                    <th style={{ padding: "6px" }}>In-Transit</th>
                    <th style={{ padding: "6px" }}>Receiving Now</th>
                    <th style={{ padding: "6px" }}>Discrepancy Note</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedTransfer.items.map((itm: any) => {
                    const remaining = Math.max(0, itm.dispatched_quantity - itm.received_quantity);
                    return (
                      <tr key={itm.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                        <td style={{ padding: "6px" }}>{itm.product_name} ({itm.size})</td>
                        <td style={{ padding: "6px", fontWeight: "600" }}>{itm.dispatched_quantity}</td>
                        <td style={{ padding: "6px", color: "#64748B" }}>{itm.received_quantity}</td>
                        <td style={{ padding: "6px", fontWeight: "600", color: "#B45309" }}>{remaining}</td>
                        <td style={{ padding: "6px" }}>
                          <input
                            type="number"
                            min="0"
                            max={remaining}
                            value={receiveQuantities[itm.id] ?? remaining}
                            onChange={(e) => setReceiveQuantities({ ...receiveQuantities, [itm.id]: Number(e.target.value) })}
                            style={{ width: "70px", padding: "4px", borderRadius: "4px", border: "1px solid #CBD5E1" }}
                          />
                        </td>
                        <td style={{ padding: "6px" }}>
                          <input
                            type="text"
                            placeholder="Reason if shortage"
                            value={discrepancyReasons[itm.id] || ""}
                            onChange={(e) => setDiscrepancyReasons({ ...discrepancyReasons, [itm.id]: e.target.value })}
                            style={{ width: "100%", padding: "4px", borderRadius: "4px", border: "1px solid #CBD5E1", fontSize: "11px" }}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 12px", background: "#F8FAFC", borderRadius: "6px", border: "1px solid #E2E8F0" }}>
              <input
                type="checkbox"
                id="isFinalReceipt"
                checked={isFinalReceipt}
                onChange={(e) => setIsFinalReceipt(e.target.checked)}
                style={{ cursor: "pointer" }}
              />
              <label htmlFor="isFinalReceipt" style={{ fontSize: "12px", color: "#334155", cursor: "pointer", fontWeight: "500" }}>
                {locale === "en" ? "Finalize shipment (close any remaining unreceived quantity as discrepancy loss)" : "दाखिला अन्तिम गर्नुहोस् (बाँकी सामानलाई क्षति वा अभावको रूपमा बन्द गर्नुहोस्)"}
              </label>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}>
              <button type="button" onClick={() => setShowReceiveModal(false)} style={{ padding: "7px 14px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12px", cursor: "pointer" }}>Cancel</button>
              <button type="button" onClick={handleConfirmReceive} style={{ padding: "7px 14px", background: "#047857", color: "#FFFFFF", border: "none", borderRadius: "4px", fontSize: "12px", fontWeight: "600", cursor: "pointer" }}>Confirm & Receive Stock</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
