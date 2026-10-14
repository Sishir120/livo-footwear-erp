"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  PlusCircle,
  ShoppingBag,
  Printer,
  CheckCircle2,
  Search,
  Download,
  X,
  AlertTriangle,
  Receipt,
  Ban,
  Building2,
  Truck,
  Wallet,
  Trash2
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";
import { useBarcodeScanner } from "../hooks/useBarcodeScanner";
import { apiFetch, extractSupportReference } from "../lib/api";
import { toPaisa, fromPaisa, calculateVat, calculateVatPaisa, amountToEnglishWords, amountToNepaliWords } from "../lib/currency";
import { useLocale } from "../context/LocaleContext";
import { NepaliDatePicker } from "./NepaliDatePicker";
import { getTodayAd, getTodayBs } from "../lib/nepaliDate";

const COMPANY_PAN = "609823412";
const COMPANY_NAME = "LIVO FOOTWEAR INDUSTRIES PVT. LTD.";
const COMPANY_ADDRESS = "Balaju Industrial District, Kathmandu, Nepal";

export function SalesInvoiceView({ userRole }: { userRole?: string }) {
  const { locale } = useLocale();
  const [clients, setClients] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [expenses, setExpenses] = useState<any[]>([]);
  const [stockBalances, setStockBalances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeSubTab, setActiveSubTab] = useState<"invoices" | "orders" | "expenses">("invoices");

  // Orders status filtering
  const [orderStatusFilter, setOrderStatusFilter] = useState<"ALL" | "CONFIRMED" | "DISPATCHED">("ALL");

  // Sales Expenses Subledger State
  const [expenseTotalPaisa, setExpenseTotalPaisa] = useState(0);
  const [expenseTotalNpr, setExpenseTotalNpr] = useState(0);
  const [selectedExpenseCategoryFilter, setSelectedExpenseCategoryFilter] = useState("ALL");
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [expenseDateAd, setExpenseDateAd] = useState(() => getTodayAd());
  const [expenseDateBs, setExpenseDateBs] = useState(() => getTodayBs().formatted);
  const [expenseParticular, setExpenseParticular] = useState("");
  const [expenseCategory, setExpenseCategory] = useState("PACKAGING_MATERIAL");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expensePaymentMethod, setExpensePaymentMethod] = useState("CASH");
  const [expenseOrderId, setExpenseOrderId] = useState("");
  const [expenseRemarks, setExpenseRemarks] = useState("");
  const [expenseSubmitting, setExpenseSubmitting] = useState(false);
  const [expenseError, setExpenseError] = useState<string | null>(null);
  const [expensePage, setExpensePage] = useState(1);

  // Dispatch Modal State (Deferred Dispatch Action)
  const [dispatchingOrder, setDispatchingOrder] = useState<any | null>(null);
  const [dispatchDateAd, setDispatchDateAd] = useState(() => getTodayAd());
  const [dispatchDateBs, setDispatchDateBs] = useState(() => getTodayBs().formatted);
  const [carrierName, setCarrierName] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [dispatchNotes, setDispatchNotes] = useState("");
  const [dispatchSubmitting, setDispatchSubmitting] = useState(false);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  // One-click Immediate Dispatch toggle for direct counter sales
  const [dispatchNow, setDispatchNow] = useState(false);

  // In-App Nepal IRD Physical Tax Invoice Preview Modal State
  const [previewInvoice, setPreviewInvoice] = useState<any | null>(null);

  // Form State
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [clientId, setClientId] = useState("");
  const [productId, setProductId] = useState("");
  const [cartons, setCartons] = useState("1");
  const [loosePairs, setLoosePairs] = useState("0");
  const [quantity, setQuantity] = useState("12");
  const [unitPrice, setUnitPrice] = useState("3200");
  const [receivedAmount, setReceivedAmount] = useState("10000");
  const [orderDateAd, setOrderDateAd] = useState(() => getTodayAd());
  const [orderDateBs, setOrderDateBs] = useState(() => getTodayBs().formatted);
  const [submitting, setSubmitting] = useState(false);
  const [continuousMode, setContinuousMode] = useState(true);
  const [keepClient, setKeepClient] = useState(true);
  const [successFeedback, setSuccessFeedback] = useState("");
  const [errorBanner, setErrorBanner] = useState<{ message: string; refCode?: string } | null>(null);

  // Dual-Unit Carton-to-Pair Physical Validation: Expected Pairs = Cartons * 12 + Loose Pairs
  const numCartons = parseInt(cartons || "0", 10) || 0;
  const numLoose = parseInt(loosePairs || "0", 10) || 0;
  const expectedPairs = numCartons * 12 + numLoose;
  const enteredPairs = parseFloat(quantity || "0") || 0;
  const cartonMismatch = enteredPairs > 0 && expectedPairs !== enteredPairs;
  const cartonMismatchMsg =
    locale === "en"
      ? `Carton and pair mismatch: ${numCartons} Cartons = ${expectedPairs} pairs expected.`
      : `कार्टुन र जोर संख्या मिलेन: ${numCartons} कार्टुन = ${expectedPairs} जोर हुनुपर्छ।`;

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

  // Hardware Barcode Scanner Hook
  useBarcodeScanner((barcode) => {
    const clean = barcode.trim().toUpperCase();
    const matched = products.find(
      (p) =>
        p.code?.toUpperCase() === clean ||
        p.code?.toUpperCase().includes(clean) ||
        clean.includes(p.code?.toUpperCase())
    );

    if (matched) {
      setProductId(String(matched.id));
      if (matched.unit_price) {
        setUnitPrice(String(matched.unit_price));
      }
      setShowOrderModal(true);
      setSuccessFeedback(`Barcode Scanned: ${matched.code} (${matched.name} · Size ${matched.size || "-"})`);
      setTimeout(() => setSuccessFeedback(""), 4500);
      setTimeout(() => {
        quantityRef.current?.focus();
        quantityRef.current?.select();
      }, 50);
    } else {
      setSuccessFeedback(`Barcode detected: "${clean}" (No matching SKU found)`);
      setTimeout(() => setSuccessFeedback(""), 4500);
    }
  }, userRole === "editor");

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
      } else if (e.key === "Escape") {
        if (previewInvoice) {
          e.preventDefault();
          setPreviewInvoice(null);
        } else if (showOrderModal) {
          e.preventDefault();
          setShowOrderModal(false);
        }
      }
    };
    window.addEventListener("keydown", handleGlobalKeyDown);
    return () => window.removeEventListener("keydown", handleGlobalKeyDown);
  }, [showOrderModal, previewInvoice, userRole]);

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

  const loadExpenses = async () => {
    try {
      const res = await fetch("/api/v1/sales/expenses?limit=250");
      if (res.ok) {
        const expData = await res.json();
        setExpenses(expData.items || []);
        setExpenseTotalPaisa(expData.total_amount_paisa || 0);
        setExpenseTotalNpr(expData.total_amount_npr || 0);
      }
    } catch (e) {
      console.error("Failed to load expenses:", e);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [cliRes, prodRes, ordRes, invRes, expRes, stockRes] = await Promise.all([
        fetch("/api/v1/sales/clients"),
        fetch("/api/v1/production/products"),
        fetch("/api/v1/sales/orders"),
        fetch("/api/v1/invoices"),
        fetch("/api/v1/sales/expenses?limit=250"),
        fetch("/api/v1/stock/balance")
      ]);
      if (cliRes.ok) setClients(await cliRes.json());
      if (prodRes.ok) setProducts(await prodRes.json());
      if (ordRes.ok) setOrders(await ordRes.json());
      if (invRes.ok) setInvoices(await invRes.json());
      if (expRes.ok) {
        const expData = await expRes.json();
        setExpenses(expData.items || []);
        setExpenseTotalPaisa(expData.total_amount_paisa || 0);
        setExpenseTotalNpr(expData.total_amount_npr || 0);
      }
      if (stockRes.ok) setStockBalances(await stockRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmDispatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dispatchingOrder) return;
    setDispatchSubmitting(true);
    setDispatchError(null);
    try {
      const res = await apiFetch(`/api/v1/sales/orders/${dispatchingOrder.id}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dispatch_date_ad: dispatchDateAd,
          dispatch_date_bs: dispatchDateBs,
          carrier_name: carrierName.trim() || undefined,
          vehicle_number: vehicleNumber.trim() || undefined,
          dispatch_notes: dispatchNotes.trim() || undefined
        })
      });

      if (res.ok) {
        setSuccessFeedback(`✓ Order ${dispatchingOrder.order_number} successfully dispatched from warehouse!`);
        setTimeout(() => setSuccessFeedback(""), 4000);
        setDispatchingOrder(null);
        await loadData();
      } else {
        const err = await res.json().catch(() => ({}));
        let msg = "Failed to dispatch sales order";
        if (err.detail) {
          if (typeof err.detail === "string") {
            msg = err.detail;
          } else if (err.detail.message) {
            msg = err.detail.message;
          } else if (err.detail.error) {
            msg = `${err.detail.error}: ${err.detail.message || "Insufficient stock"}`;
          }
        }
        setDispatchError(msg);
      }
    } catch (err: any) {
      setDispatchError(err.message || "Network error dispatching order");
    } finally {
      setDispatchSubmitting(false);
    }
  };

  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expenseParticular.trim() || !expenseAmount || parseFloat(expenseAmount) <= 0) {
      setExpenseError("Particular and valid amount are required.");
      return;
    }
    setExpenseSubmitting(true);
    setExpenseError(null);
    try {
      const paisa = toPaisa(expenseAmount);
      const payload: any = {
        expense_date_ad: expenseDateAd,
        expense_date_bs: expenseDateBs,
        particular: expenseParticular.trim(),
        category: expenseCategory,
        amount_paisa: paisa,
        payment_method: expensePaymentMethod,
        remarks: expenseRemarks.trim() || undefined
      };
      if (expenseOrderId) {
        payload.sales_order_id = parseInt(expenseOrderId);
      }
      const res = await apiFetch("/api/v1/sales/expenses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setShowExpenseModal(false);
        setExpenseParticular("");
        setExpenseAmount("");
        setExpenseRemarks("");
        setExpenseOrderId("");
        setSuccessFeedback("✓ Sales expense recorded in subledger successfully.");
        setTimeout(() => setSuccessFeedback(""), 3500);
        await loadExpenses();
      } else {
        const err = await res.json().catch(() => ({}));
        setExpenseError(err.detail || "Failed to record sales expense");
      }
    } catch (err: any) {
      setExpenseError(err.message || "Network error recording sales expense");
    } finally {
      setExpenseSubmitting(false);
    }
  };

  const handleDeleteExpense = async (expenseId: number) => {
    if (!confirm("Are you sure you want to delete this sales expense entry?")) return;
    try {
      const res = await apiFetch(`/api/v1/sales/expenses/${expenseId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setSuccessFeedback("Expense entry deleted.");
        setTimeout(() => setSuccessFeedback(""), 3000);
        await loadExpenses();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to delete expense");
      }
    } catch (err) {
      alert("Network error deleting expense");
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

  const getOrderByInvoice = (salesOrderId: number) => {
    return orders.find((o) => o.id === salesOrderId);
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

    if (cartonMismatch) {
      setErrorBanner({ message: cartonMismatchMsg });
      return;
    }

    setSubmitting(true);
    try {
      const res = await apiFetch("/api/v1/sales/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: parseInt(clientId),
          order_date_ad: orderDateAd,
          order_date_bs: orderDateBs,
          received_amount: (receivedAmount || "0").toString(),
          dispatch_now: dispatchNow,
          status: dispatchNow ? "DISPATCHED" : "CONFIRMED",
          items: [
            {
              product_id: parseInt(productId),
              quantity: parseFloat(quantity),
              unit_price: (unitPrice || "0").toString()
            }
          ]
        })
      });

      if (res.ok) {
        setErrorBanner(null);
        const order = await res.json();
        // Generate Invoice for the order automatically with VAT enabled
        const invRes = await apiFetch("/api/v1/invoices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sales_order_id: order.id, vat_enabled: true })
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
          const orderNum = order.order_number || `#${order.id}`;
          const invMsg = invData?.invoice_number ? ` (Tax Invoice #${invData.invoice_number})` : "";
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
        const reqId = extractSupportReference(res);
        const err = await res.json().catch(() => ({}));
        const detailMsg = err.detail || "Failed to create sales order";
        console.error(`Transaction failed. Support reference: [${reqId}]`, detailMsg);
        setErrorBanner({
          message: detailMsg,
          refCode: reqId
        });
      }
    } catch (e: any) {
      console.error("Network or submission error:", e);
      setErrorBanner({
        message: e?.message || "Error saving sales order. Please verify connection.",
        refCode: "req_network_err"
      });
    } finally {
      setSubmitting(false);
    }
  };

  const openPrintableInvoice = (invoiceId: number) => {
    window.open(`/api/v1/invoices/${invoiceId}/printable`, "_blank");
  };

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

  // Monetary 2-decimal formatting helper
  const fmtNpr = (val: number | string | undefined | null) => {
    if (val === undefined || val === null) return "0.00";
    const num = typeof val === "number" ? val : parseFloat(String(val).replace(/,/g, ""));
    if (isNaN(num)) return "0.00";
    return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Filtered Invoices
  const filteredInvoices = useMemo(() => {
    return invoices.filter((inv) => {
      const client = getClientByOrderId(inv.sales_order_id);
      const clientStr = client ? `${client.name} ${client.code} ${client.pan_number || ""}`.toLowerCase() : "";
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
      const clientStr = client ? `${client.name} ${client.code} ${client.pan_number || ""}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      const matchesSearch = (
        o.order_number?.toLowerCase().includes(q) ||
        clientStr.includes(q) ||
        o.order_date_ad?.includes(q) ||
        o.order_date_bs?.includes(q)
      );
      if (!matchesSearch) return false;

      if (orderStatusFilter === "CONFIRMED") {
        return o.status === "CONFIRMED" || (!o.delivered && o.status !== "DISPATCHED");
      }
      if (orderStatusFilter === "DISPATCHED") {
        return o.status === "DISPATCHED" || o.delivered;
      }
      return true;
    });
  }, [orders, clients, searchQuery, orderStatusFilter]);

  // Filtered Expenses
  const filteredExpenses = useMemo(() => {
    return expenses.filter((exp) => {
      if (selectedExpenseCategoryFilter !== "ALL" && exp.category !== selectedExpenseCategoryFilter) {
        return false;
      }
      const q = searchQuery.toLowerCase();
      if (!q) return true;
      return (
        (exp.particular && exp.particular.toLowerCase().includes(q)) ||
        (exp.category && exp.category.toLowerCase().includes(q)) ||
        (exp.expense_date_ad && exp.expense_date_ad.includes(q)) ||
        (exp.expense_date_bs && exp.expense_date_bs.includes(q)) ||
        (exp.payment_method && exp.payment_method.toLowerCase().includes(q)) ||
        (exp.remarks && exp.remarks.toLowerCase().includes(q)) ||
        (exp.sales_order_id && String(exp.sales_order_id).includes(q))
      );
    });
  }, [expenses, selectedExpenseCategoryFilter, searchQuery]);

  // Pagination
  const [invoicePage, setInvoicePage] = useState(1);
  const [orderPage, setOrderPage] = useState(1);
  const ITEMS_PER_PAGE = 12;

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

  const totalExpensePages = Math.ceil(filteredExpenses.length / ITEMS_PER_PAGE) || 1;
  const paginatedExpenses = useMemo(() => {
    const start = (expensePage - 1) * ITEMS_PER_PAGE;
    return filteredExpenses.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredExpenses, expensePage]);

  // CSV Exporters
  const handleExportInvoices = () => {
    if (!filteredInvoices.length) return;
    const headers = [
      "Invoice Number",
      "Buyer Name",
      "Buyer PAN",
      "Company PAN",
      "Date AD",
      "Date BS",
      "Taxable Subtotal (NPR)",
      "13% VAT Amount (NPR)",
      "Grand Total (NPR)",
      "Received (NPR)",
      "Receivable Balance (NPR)",
      "Status"
    ];
    const rows = filteredInvoices.map((inv) => {
      const client = getClientByOrderId(inv.sales_order_id);
      const subtotal = inv.subtotal ?? (inv.total_amount ? (inv.total_amount / 1.13) : 0);
      const vat = (inv.vat_amount && inv.vat_amount > 0) ? inv.vat_amount : Math.round(subtotal * 0.13 * 100) / 100;
      const totalAmount = inv.total_amount || (subtotal + vat);
      return [
        inv.invoice_number,
        client?.name || "-",
        client?.pan_number || "N/A",
        COMPANY_PAN,
        inv.date_ad,
        inv.date_bs,
        fmtNpr(subtotal),
        fmtNpr(vat),
        fmtNpr(totalAmount),
        fmtNpr(inv.received_amount),
        fmtNpr(inv.receivable_amount),
        inv.is_void ? "VOID" : "ACTIVE"
      ];
    });
    exportToCSV("Nepal_Tax_Invoices_Ledger", headers, rows);
  };

  const handleExportOrders = () => {
    if (!filteredOrders.length) return;
    const headers = [
      "Order Number",
      "Customer Name",
      "Customer PAN",
      "Date AD",
      "Date BS",
      "Total Amount (NPR)",
      "Received (NPR)",
      "Receivable Balance (NPR)",
      "Status",
      "Carrier",
      "Vehicle"
    ];
    const rows = filteredOrders.map((o) => {
      const client = getClientById(o.client_id);
      return [
        o.order_number,
        client?.name || `Client #${o.client_id}`,
        client?.pan_number || "N/A",
        o.order_date_ad,
        o.order_date_bs,
        fmtNpr(o.total_amount),
        fmtNpr(o.received_amount),
        fmtNpr(o.receivable_amount),
        o.status === "DISPATCHED" || o.delivered ? "Dispatched" : "Pending Dispatch",
        o.carrier_name || "-",
        o.vehicle_number || "-"
      ];
    });
    exportToCSV("Sales_Orders_Ledger", headers, rows);
  };

  const handleExportExpenses = () => {
    if (!filteredExpenses.length) return;
    const headers = [
      "S.N.",
      "Date AD",
      "Date BS",
      "Particular",
      "Category",
      "Order Ref",
      "Payment Mode",
      "Amount (NPR)",
      "Remarks"
    ];
    const rows = filteredExpenses.map((exp, idx) => [
      idx + 1,
      exp.expense_date_ad,
      exp.expense_date_bs,
      exp.particular,
      exp.category,
      exp.sales_order_id ? `#${exp.sales_order_id}` : "-",
      exp.payment_method,
      fmtNpr(exp.amount_paisa ? exp.amount_paisa / 100 : exp.amount || 0),
      exp.remarks || "-"
    ]);
    exportToCSV("Sales_Expenses_Ledger", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Statutory Header & Actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0, letterSpacing: "-0.01em" }}>
            {locale === "en"
              ? "Wholesale Sales & Statutory Tax Invoices"
              : "कर बिजक तथा थोक बिक्री (Sales & Invoicing)"}
          </h2>
          <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px" }}>
            Nepal IRD Rule 23(1) Schedule-5 Compliance · Monotonic Sequential Invoices
          </div>
        </div>

        {userRole === "editor" && (
          <button
            className="btn-primary"
            onClick={() => setShowOrderModal(true)}
            title="Shortcut: Alt+N"
            style={{ background: "#1E3A8A", border: "1px solid #1E3A8A", color: "#FFFFFF", padding: "6px 12px", borderRadius: "3px", fontSize: "12px", fontWeight: "700", display: "inline-flex", alignItems: "center", gap: "6px", cursor: "pointer" }}
          >
            <PlusCircle size={15} /> Record Sale & Issue Invoice
            <span style={{ fontSize: "11px", opacity: 0.85, background: "rgba(255,255,255,0.2)", padding: "1px 5px", borderRadius: "3px", marginLeft: "4px" }}>
              Alt+N
            </span>
          </button>
        )}
      </div>

      {/* STATUTORY TAX INVOICE STRIP (Nepal IRD Compliance Banner) */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #CBD5E1",
          borderRadius: "4px",
          padding: "10px 14px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Building2 size={16} color="#1E3A8A" />
            <span style={{ fontSize: "12px", fontWeight: "700", color: "#0F172A" }}>
              {COMPANY_NAME}
            </span>
          </div>

          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#F1F5F9", border: "1px solid #CBD5E1", padding: "2px 8px", borderRadius: "3px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>
              COMPANY PAN:
            </span>
            <span style={{ fontFamily: "monospace", fontSize: "13px", fontWeight: "700", color: "#1E3A8A", letterSpacing: "0.08em" }}>
              {COMPANY_PAN}
            </span>
          </div>

          <span style={{ fontSize: "11px", color: "#475569" }}>
            VAT Act 2052 · IRD Registered
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "11px", color: "#475569" }}>
          <span>Breakdown: <strong style={{ color: "#0F172A" }}>Subtotal</strong> → <strong style={{ color: "#1E3A8A" }}>13% Nepal VAT</strong> → <strong style={{ color: "#0F172A" }}>Grand Total NPR</strong></span>
        </div>
      </div>

      {/* Tabs & Search Filter Bar */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        {/* Sub-tabs */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <button
            onClick={() => setActiveSubTab("invoices")}
            style={{
              padding: "5px 12px",
              borderRadius: "3px",
              border: "1px solid",
              borderColor: activeSubTab === "invoices" ? "#1E3A8A" : "#CBD5E1",
              fontSize: "12px",
              fontWeight: "700",
              cursor: "pointer",
              background: activeSubTab === "invoices" ? "#1E3A8A" : "#FFFFFF",
              color: activeSubTab === "invoices" ? "#FFFFFF" : "#475569",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <Receipt size={13} /> Issued Tax Invoices ({invoices.length})
          </button>
          <button
            onClick={() => setActiveSubTab("orders")}
            style={{
              padding: "5px 12px",
              borderRadius: "3px",
              border: "1px solid",
              borderColor: activeSubTab === "orders" ? "#1E3A8A" : "#CBD5E1",
              fontSize: "12px",
              fontWeight: "700",
              cursor: "pointer",
              background: activeSubTab === "orders" ? "#1E3A8A" : "#FFFFFF",
              color: activeSubTab === "orders" ? "#FFFFFF" : "#475569",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <ShoppingBag size={13} /> Sales Orders ({orders.length})
          </button>
          <button
            onClick={() => setActiveSubTab("expenses")}
            style={{
              padding: "5px 12px",
              borderRadius: "3px",
              border: "1px solid",
              borderColor: activeSubTab === "expenses" ? "#1E3A8A" : "#CBD5E1",
              fontSize: "12px",
              fontWeight: "700",
              cursor: "pointer",
              background: activeSubTab === "expenses" ? "#1E3A8A" : "#FFFFFF",
              color: activeSubTab === "expenses" ? "#FFFFFF" : "#475569",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px"
            }}
          >
            <Wallet size={13} /> Sales Expenses ({expenses.length})
          </button>

          {/* Subtab contextual filter controls */}
          {activeSubTab === "orders" && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: "4px", marginLeft: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748B" }}>Status:</span>
              <select
                value={orderStatusFilter}
                onChange={(e) => setOrderStatusFilter(e.target.value as any)}
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  padding: "3px 8px",
                  borderRadius: "3px",
                  border: "1px solid #CBD5E1",
                  background: "#F8FAFC",
                  color: "#0F172A",
                  cursor: "pointer"
                }}
              >
                <option value="ALL">All Orders ({orders.length})</option>
                <option value="CONFIRMED">Pending Dispatch / Confirmed ({orders.filter(o => o.status === "CONFIRMED" || (!o.delivered && o.status !== "DISPATCHED")).length})</option>
                <option value="DISPATCHED">Dispatched ({orders.filter(o => o.status === "DISPATCHED" || o.delivered).length})</option>
              </select>
            </div>
          )}

          {activeSubTab === "expenses" && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: "4px", marginLeft: "8px" }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: "#64748B" }}>Category:</span>
              <select
                value={selectedExpenseCategoryFilter}
                onChange={(e) => setSelectedExpenseCategoryFilter(e.target.value)}
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  padding: "3px 8px",
                  borderRadius: "3px",
                  border: "1px solid #CBD5E1",
                  background: "#F8FAFC",
                  color: "#0F172A",
                  cursor: "pointer"
                }}
              >
                <option value="ALL">All Categories</option>
                <option value="PACKAGING_MATERIAL">Packaging Material</option>
                <option value="TRANSPORT_FREIGHT">Transport & Freight</option>
                <option value="LOADING_UNLOADING">Loading / Unloading</option>
                <option value="SALES_COMMISSION">Sales Commission</option>
                <option value="MARKETING_PROMOTION">Marketing & Promotion</option>
                <option value="OTHER">Other Expenses</option>
              </select>
            </div>
          )}

          {/* Dual-Unit Packaging Floor Hint */}
          {activeSubTab !== "expenses" && (
            <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#EFF6FF", border: "1px solid #BFDBFE", borderRadius: "3px", padding: "4px 8px", fontSize: "11px", fontWeight: "700", color: "#1E3A8A" }}>
              <span>{locale === "en" ? "1 Carton = 12 Pairs" : "१ कार्टुन = १२ जोर (1 Carton = 12 Pairs)"}</span>
            </div>
          )}
        </div>

        {/* Search & Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {activeSubTab === "expenses" && userRole === "editor" && (
            <button
              onClick={() => {
                setExpenseParticular("");
                setExpenseAmount("");
                setExpenseRemarks("");
                setExpenseOrderId("");
                setExpenseError(null);
                setExpenseDateAd(getTodayAd());
                setExpenseDateBs(getTodayBs().formatted);
                setShowExpenseModal(true);
              }}
              style={{
                background: "#047857",
                border: "1px solid #047857",
                color: "#FFFFFF",
                padding: "4px 10px",
                borderRadius: "3px",
                fontSize: "11.5px",
                fontWeight: "700",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                cursor: "pointer"
              }}
            >
              <PlusCircle size={13} /> + Record Sales Expense
            </button>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "#F8FAFC", padding: "4px 8px", borderRadius: "3px", border: "1px solid #CBD5E1" }}>
            <Search size={13} color="#64748B" />
            <input
              type="text"
              placeholder={activeSubTab === "expenses" ? "Search expense particulars..." : "Search invoice #, PAN, client..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ background: "none", border: "none", color: "#0F172A", fontSize: "12px", outline: "none", width: "190px" }}
            />
          </div>

          <button
            onClick={activeSubTab === "invoices" ? handleExportInvoices : activeSubTab === "orders" ? handleExportOrders : handleExportExpenses}
            className="btn-export"
          >
            <Download size={13} /> Export to CSV
          </button>
        </div>
      </div>

      {/* Main Table View */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "14px 16px" }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>Loading records...</div>
        ) : activeSubTab === "invoices" ? (
          /* INVOICES TABLE (Statutory Nepal IRD 2-Decimal Grid) */
          filteredInvoices.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
              No tax invoices found matching criteria.
            </div>
          ) : (
            <div className="table-container-dense">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th className="sticky-col-left-1" style={{ width: "120px" }}>Invoice No.</th>
                    <th className="sticky-col-left-2" style={{ minWidth: "150px" }}>Buyer / Entity</th>
                    <th style={{ width: "105px" }}>Buyer PAN</th>
                    <th style={{ width: "120px" }}>Date (AD / BS)</th>
                    <th style={{ textAlign: "right", width: "105px" }}>Subtotal (NPR)</th>
                    <th style={{ textAlign: "right", width: "95px" }}>13% VAT</th>
                    <th style={{ textAlign: "right", width: "110px" }}>Grand Total</th>
                    <th style={{ textAlign: "right", width: "100px" }}>Received</th>
                    <th style={{ textAlign: "right", width: "105px" }}>Balance Due</th>
                    <th style={{ width: "130px", textAlign: "center" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedInvoices.map((inv) => {
                    const client = getClientByOrderId(inv.sales_order_id);
                    const subtotal = inv.subtotal ?? (inv.total_amount ? Math.round((inv.total_amount / 1.13) * 100) / 100 : 0);
                    const vatAmount = (inv.vat_amount && inv.vat_amount > 0) ? inv.vat_amount : Math.round(subtotal * 0.13 * 100) / 100;
                    const grandTotal = inv.total_amount || (subtotal + vatAmount);

                    return (
                      <tr key={inv.id} style={{ opacity: inv.is_void ? 0.65 : 1 }}>
                        <td className="sticky-col-left-1 num-mono" style={{ fontWeight: "700", color: inv.is_void ? "#94A3B8" : "#1E3A8A", textDecoration: inv.is_void ? "line-through" : "none" }}>
                          {inv.invoice_number}
                          {inv.is_void && (
                            <span style={{ marginLeft: "4px", fontSize: "9px", color: "#DC2626", background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "2px", padding: "1px 3px", textDecoration: "none", display: "inline-block" }}>
                              VOID
                            </span>
                          )}
                        </td>
                        <td className="sticky-col-left-2" style={{ fontWeight: "600", color: "#0F172A" }}>
                          {client ? (
                            <>
                              {client.name} <span style={{ fontSize: "11px", color: "#64748B" }}>({client.code})</span>
                            </>
                          ) : (
                            `Order #${inv.sales_order_id}`
                          )}
                        </td>
                        <td style={{ fontFamily: "monospace", fontSize: "12px", color: client?.pan_number ? "#0F172A" : "#94A3B8", fontWeight: client?.pan_number ? "700" : "400" }}>
                          {client?.pan_number || "N/A"}
                        </td>
                        <td style={{ fontSize: "12px", color: "#475569" }}>
                          {inv.date_ad} <span style={{ fontSize: "11px", color: "#64748B" }}>({inv.date_bs})</span>
                        </td>
                        <td style={{ textAlign: "right" }} className="num-mono">
                          Rs. {fmtNpr(subtotal)}
                        </td>
                        <td style={{ textAlign: "right", color: "#475569" }} className="num-mono">
                          Rs. {fmtNpr(vatAmount)}
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                          Rs. {fmtNpr(grandTotal)}
                        </td>
                        <td style={{ textAlign: "right", color: "#059669", fontWeight: "600" }} className="num-mono">
                          Rs. {fmtNpr(inv.received_amount)}
                        </td>
                        <td
                          style={{
                            textAlign: "right",
                            color: inv.receivable_amount > 0 ? "#DC2626" : "#64748B",
                            fontWeight: "700"
                          }}
                          className="num-mono"
                        >
                          Rs. {fmtNpr(inv.receivable_amount)}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          <div style={{ display: "inline-flex", gap: "4px", alignItems: "center" }}>
                            <button
                              type="button"
                              onClick={() => {
                                const ord = getOrderByInvoice(inv.sales_order_id);
                                setPreviewInvoice({
                                  ...inv,
                                  client,
                                  order: ord,
                                  subtotal,
                                  vatAmount,
                                  total_amount: grandTotal
                                });
                              }}
                              style={{
                                background: "#FFFFFF",
                                border: "1px solid #CBD5E1",
                                color: "#1E3A8A",
                                padding: "2px 6px",
                                borderRadius: "3px",
                                fontSize: "11px",
                                fontWeight: "700",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "3px"
                              }}
                              title={locale === "en" ? "Preview Tax Invoice" : "Preview Nepal IRD Tax Invoice (कर बिजक)"}
                            >
                              <Printer size={11} /> {locale === "en" ? "Tax Invoice" : "कर बिजक"}
                            </button>
                            {userRole === "editor" && !inv.is_void && (
                              <button
                                type="button"
                                onClick={() => handleCancelInvoice(inv.id)}
                                style={{
                                  background: "#FFFFFF",
                                  border: "1px solid #FECACA",
                                  color: "#DC2626",
                                  padding: "2px 5px",
                                  borderRadius: "3px",
                                  fontSize: "11px",
                                  cursor: "pointer"
                                }}
                                title="Void invoice per Nepal statutory VAT rules"
                              >
                                <Ban size={11} />
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
                    <span style={{ fontSize: "12px", color: "#475569" }}>
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
        ) : activeSubTab === "orders" ? (
          /* ORDERS TABLE */
          filteredOrders.length === 0 ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
              No sales orders found matching criteria.
            </div>
          ) : (
            <div className="table-container-dense">
              <table className="table-dense">
                <thead>
                  <tr>
                    <th style={{ width: "130px" }}>Order Number</th>
                    <th>Customer Name</th>
                    <th style={{ width: "110px" }}>Buyer PAN</th>
                    <th style={{ width: "130px" }}>Date (AD / BS)</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Total Amount (NPR)</th>
                    <th style={{ textAlign: "right", width: "120px" }}>Received</th>
                    <th style={{ textAlign: "right", width: "130px" }}>Balance Due</th>
                    <th style={{ width: "140px", textAlign: "center" }}>Dispatch Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedOrders.map((o) => {
                    const client = getClientById(o.client_id);
                    const isDispatched = o.status === "DISPATCHED" || o.delivered;
                    return (
                      <tr key={o.id}>
                        <td style={{ fontWeight: "700", color: "#1E3A8A" }} className="num-mono">
                          {o.order_number}
                        </td>
                        <td style={{ fontWeight: "600", color: "#0F172A" }}>
                          {client ? (
                            <>
                              {client.name} <span style={{ fontSize: "11px", color: "#64748B" }}>({client.code})</span>
                            </>
                          ) : (
                            `Client #${o.client_id}`
                          )}
                        </td>
                        <td style={{ fontFamily: "monospace", fontSize: "12px", color: client?.pan_number ? "#0F172A" : "#94A3B8" }}>
                          {client?.pan_number || "N/A"}
                        </td>
                        <td style={{ fontSize: "12px", color: "#475569" }}>
                          {o.order_date_ad} <span style={{ fontSize: "11px", color: "#64748B" }}>({o.order_date_bs} BS)</span>
                        </td>
                        <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                          Rs. {fmtNpr(o.total_amount)}
                        </td>
                        <td style={{ textAlign: "right", color: "#059669", fontWeight: "600" }} className="num-mono">
                          Rs. {fmtNpr(o.received_amount)}
                        </td>
                        <td
                          style={{
                            textAlign: "right",
                            color: o.receivable_amount > 0 ? "#DC2626" : "#64748B",
                            fontWeight: "700"
                          }}
                          className="num-mono"
                        >
                          Rs. {fmtNpr(o.receivable_amount)}
                        </td>
                        <td style={{ textAlign: "center" }}>
                          {isDispatched ? (
                            <div>
                              <span className="badge badge-success" style={{ display: "inline-flex", alignItems: "center", gap: "3px" }}>
                                <CheckCircle2 size={11} /> DISPATCHED
                              </span>
                              {o.carrier_name && (
                                <div style={{ fontSize: "10px", color: "#64748B", marginTop: "2px" }}>
                                  {o.carrier_name} {o.vehicle_number ? `(${o.vehicle_number})` : ""}
                                </div>
                              )}
                            </div>
                          ) : (
                            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "3px" }}>
                              <span
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  fontSize: "10.5px",
                                  fontWeight: "700",
                                  background: "#FEF3C7",
                                  color: "#92400E",
                                  border: "1px solid #FCD34D",
                                  padding: "2px 6px",
                                  borderRadius: "3px"
                                }}
                              >
                                <AlertTriangle size={11} color="#D97706" /> PENDING DISPATCH
                              </span>
                              {userRole === "editor" && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setDispatchingOrder(o);
                                    setDispatchDateAd(getTodayAd());
                                    setDispatchDateBs(getTodayBs().formatted);
                                    setCarrierName(o.carrier_name || "");
                                    setVehicleNumber(o.vehicle_number || "");
                                    setDispatchNotes(o.dispatch_notes || "");
                                    setDispatchError(null);
                                  }}
                                  style={{
                                    background: "#1E3A8A",
                                    color: "#FFFFFF",
                                    border: "none",
                                    padding: "2px 7px",
                                    borderRadius: "3px",
                                    fontSize: "10.5px",
                                    fontWeight: "700",
                                    cursor: "pointer",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "4px"
                                  }}
                                  title="Dispatch physical stock from warehouse"
                                >
                                  <Truck size={11} /> Dispatch Now
                                </button>
                              )}
                            </div>
                          )}
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
                    <span style={{ fontSize: "12px", color: "#475569" }}>
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
        ) : (
          /* SALES EXPENSES SUBLEDGER TABLE */
          <div>
            {/* KPI Summary Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginBottom: "14px" }}>
              <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px 14px" }}>
                <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748B", textTransform: "uppercase" }}>
                  Total Sales Expenses (बिक्री खर्च)
                </div>
                <div className="num-mono-bold" style={{ fontSize: "18px", color: "#0F172A", marginTop: "4px" }}>
                  Rs. {fmtNpr(expenseTotalNpr)}
                </div>
                <div style={{ fontSize: "10.5px", color: "#64748B", marginTop: "2px" }}>
                  Exact integer-paisa subledger: {expenseTotalPaisa.toLocaleString()} paisa
                </div>
              </div>

              <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px 14px" }}>
                <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748B", textTransform: "uppercase" }}>
                  Recorded Expense Vouchers
                </div>
                <div className="num-mono-bold" style={{ fontSize: "18px", color: "#1E3A8A", marginTop: "4px" }}>
                  {expenses.length} Entries
                </div>
                <div style={{ fontSize: "10.5px", color: "#64748B", marginTop: "2px" }}>
                  Packaging, Freight, Loading, Commission, Marketing
                </div>
              </div>
            </div>

            {filteredExpenses.length === 0 ? (
              <div style={{ padding: "30px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
                No sales expense vouchers found matching filter criteria.
              </div>
            ) : (
              <div className="table-container-dense">
                <table className="table-dense">
                  <thead>
                    <tr>
                      <th style={{ width: "45px", textAlign: "center" }}>#</th>
                      <th style={{ width: "125px" }}>Date (AD / BS)</th>
                      <th>Particular / Description</th>
                      <th style={{ width: "155px" }}>Category</th>
                      <th style={{ width: "95px", textAlign: "center" }}>Order Ref</th>
                      <th style={{ width: "105px" }}>Payment Mode</th>
                      <th style={{ textAlign: "right", width: "120px" }}>Amount (NPR)</th>
                      <th>Remarks</th>
                      {userRole === "editor" && <th style={{ width: "60px", textAlign: "center" }}>Action</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedExpenses.map((exp, idx) => {
                      const rowNum = (expensePage - 1) * ITEMS_PER_PAGE + idx + 1;
                      const nprAmount = exp.amount_paisa ? exp.amount_paisa / 100 : exp.amount || 0;
                      return (
                        <tr key={exp.id}>
                          <td style={{ textAlign: "center", color: "#64748B", fontSize: "11px" }}>{rowNum}</td>
                          <td style={{ fontSize: "12px", color: "#475569" }}>
                            {exp.expense_date_ad} <span style={{ fontSize: "11px", color: "#64748B" }}>({exp.expense_date_bs})</span>
                          </td>
                          <td style={{ fontWeight: "600", color: "#0F172A" }}>
                            {exp.particular}
                          </td>
                          <td>
                            <span style={{ fontSize: "10.5px", fontWeight: "700", background: "#EFF6FF", color: "#1E3A8A", border: "1px solid #BFDBFE", padding: "1px 6px", borderRadius: "3px" }}>
                              {exp.category}
                            </span>
                          </td>
                          <td style={{ textAlign: "center" }}>
                            {exp.sales_order_id ? (
                              <span className="num-mono" style={{ fontSize: "11px", fontWeight: "700", color: "#1E3A8A", background: "#F1F5F9", padding: "1px 5px", borderRadius: "3px" }}>
                                #{exp.sales_order_id}
                              </span>
                            ) : (
                              <span style={{ color: "#94A3B8", fontSize: "11px" }}>-</span>
                            )}
                          </td>
                          <td style={{ fontSize: "11.5px", color: "#475569" }}>
                            {exp.payment_method}
                          </td>
                          <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                            Rs. {fmtNpr(nprAmount)}
                          </td>
                          <td style={{ fontSize: "11.5px", color: "#64748B" }}>
                            {exp.remarks || "-"}
                          </td>
                          {userRole === "editor" && (
                            <td style={{ textAlign: "center" }}>
                              <button
                                type="button"
                                onClick={() => handleDeleteExpense(exp.id)}
                                style={{
                                  background: "#FFFFFF",
                                  border: "1px solid #FECACA",
                                  color: "#DC2626",
                                  padding: "2px 5px",
                                  borderRadius: "3px",
                                  fontSize: "11px",
                                  cursor: "pointer"
                                }}
                                title="Delete expense voucher"
                              >
                                <Trash2 size={12} />
                              </button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {filteredExpenses.length > ITEMS_PER_PAGE && (
                  <div className="pagination-bar">
                    <span>
                      Showing {(expensePage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(expensePage * ITEMS_PER_PAGE, filteredExpenses.length)} of {filteredExpenses.length} expense vouchers
                    </span>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <button
                        className="pagination-btn"
                        onClick={() => setExpensePage((p) => Math.max(1, p - 1))}
                        disabled={expensePage === 1}
                      >
                        Previous
                      </button>
                      <span style={{ fontSize: "12px", color: "#475569" }}>
                        Page {expensePage} of {totalExpensePages}
                      </span>
                      <button
                        className="pagination-btn"
                        onClick={() => setExpensePage((p) => Math.min(totalExpensePages, p + 1))}
                        disabled={expensePage === totalExpensePages}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* NEPAL IRD PHYSICAL TAX INVOICE (कर बिजक) PREVIEW MODAL */}
      {previewInvoice && (
        <div className="modal-overlay" role="presentation" style={{ zIndex: 9999 }}>
          <div
            className="modal-drawer"
            role="dialog"
            aria-modal="true"
            style={{
              maxWidth: "760px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "0"
            }}
          >
            {/* Action Bar */}
            <div style={{ background: "#F1F5F9", borderBottom: "1px solid #CBD5E1", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Receipt size={16} color="#1E3A8A" />
                <span style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", textTransform: "uppercase" }}>
                  {locale === "en" ? "Nepal IRD Statutory Tax Invoice" : "नेपाल सरकार कर बिजक (Nepal IRD Tax Invoice)"}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <button
                  type="button"
                  onClick={() => openPrintableInvoice(previewInvoice.id)}
                  style={{
                    background: "#1E3A8A",
                    color: "#FFFFFF",
                    border: "none",
                    padding: "4px 10px",
                    borderRadius: "3px",
                    fontSize: "12px",
                    fontWeight: "700",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    cursor: "pointer"
                  }}
                >
                  <Printer size={13} /> {locale === "en" ? "Print Official Copy" : "प्रमाणित प्रति प्रिन्ट गर्नुहोस्"}
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewInvoice(null)}
                  style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", padding: "4px" }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Printable Tax Invoice Paper Body */}
            <div style={{ padding: "24px 30px", background: "#FFFFFF", color: "#0F172A", fontFamily: "'Inter', sans-serif" }}>
              {/* Header Box */}
              <div style={{ textAlign: "center", borderBottom: "2px solid #0F172A", paddingBottom: "12px", marginBottom: "14px" }}>
                <div style={{ fontSize: "11px", fontWeight: "600", color: "#475569" }}>
                  {locale === "en"
                    ? "Government of Nepal · Inland Revenue Department"
                    : "नेपाल सरकार · आन्तरिक राजस्व विभाग (Government of Nepal · Inland Revenue Department)"}
                </div>
                <h1 style={{ fontSize: "20px", fontWeight: "800", color: "#0F172A", margin: "4px 0 2px 0", letterSpacing: "0.02em" }}>
                  {locale === "en" ? "TAX INVOICE" : "कर बिजक (TAX INVOICE)"}
                </h1>
                <div style={{ fontSize: "11px", color: "#64748B" }}>
                  {locale === "en"
                    ? "Schedule-5, Value Added Tax Rules, 2053"
                    : "अनुसूची-५, नियम २३ को उपनियम (१) सँग सम्बन्धित"}
                </div>
              </div>

              {/* Seller & Buyer Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "16px", marginBottom: "16px", fontSize: "12px" }}>
                {/* Seller Info */}
                <div style={{ border: "1px solid #CBD5E1", borderRadius: "3px", padding: "10px 12px" }}>
                  <div style={{ fontWeight: "700", fontSize: "13px", color: "#0F172A" }}>{COMPANY_NAME}</div>
                  <div style={{ color: "#475569", marginTop: "2px" }}>
                    {locale === "en" ? "Address: " : "ठेगाना (Address): "}{COMPANY_ADDRESS}
                  </div>
                  
                  {/* Seller PAN Grid */}
                  <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ fontWeight: "700", color: "#0F172A" }}>
                      {locale === "en" ? "Seller's PAN:" : "विक्रेताको स्थायी लेखा नं. (PAN):"}
                    </span>
                    <div style={{ display: "inline-flex", gap: "2px" }}>
                      {COMPANY_PAN.split("").map((digit, i) => (
                        <span key={i} style={{ width: "18px", height: "20px", border: "1px solid #1E3A8A", background: "#EFF6FF", color: "#1E3A8A", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: "800", fontFamily: "monospace", fontSize: "12px" }}>
                          {digit}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Invoice Metadata & Buyer Info */}
                <div style={{ border: "1px solid #CBD5E1", borderRadius: "3px", padding: "10px 12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ color: "#475569" }}>{locale === "en" ? "Invoice No:" : "बिजक नं. (Invoice No):"}</span>
                    <strong style={{ fontFamily: "monospace", color: "#1E3A8A" }}>{previewInvoice.invoice_number}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ color: "#475569" }}>{locale === "en" ? "Date (AD):" : "मिति (Date AD):"}</span>
                    <strong>{previewInvoice.date_ad}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span style={{ color: "#475569" }}>{locale === "en" ? "Date (BS):" : "मिति (Date BS):"}</span>
                    <strong>{previewInvoice.date_bs} BS</strong>
                  </div>

                  {/* Buyer PAN */}
                  <div style={{ marginTop: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontWeight: "700", color: "#0F172A" }}>
                      {locale === "en" ? "Buyer's PAN:" : "खरिदकर्ताको स्थायी लेखा नं. (PAN):"}
                    </span>
                    <div style={{ display: "inline-flex", gap: "2px" }}>
                      {(previewInvoice.client?.pan_number || "---------").padEnd(9, "-").slice(0, 9).split("").map((digit: string, i: number) => (
                        <span key={i} style={{ width: "16px", height: "18px", border: "1px solid #CBD5E1", background: "#F8FAFC", color: digit === "-" ? "#CBD5E1" : "#0F172A", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: "700", fontFamily: "monospace", fontSize: "11px" }}>
                          {digit}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div style={{ marginTop: "4px", fontSize: "11.5px", color: "#475569" }}>
                    {locale === "en" ? "Buyer: " : "खरिदकर्ता (Buyer): "}<strong style={{ color: "#0F172A" }}>{previewInvoice.client?.name || "Cash Customer"}</strong>
                  </div>
                </div>
              </div>

              {/* Schedule-5 Invariants & Calculations */}
              {(() => {
                const previewTaxable = previewInvoice.subtotal ?? (previewInvoice.total_amount ? Math.round((previewInvoice.total_amount / 1.13) * 100) / 100 : 0);
                const previewVat = (previewInvoice.vat_amount && previewInvoice.vat_amount > 0)
                  ? previewInvoice.vat_amount
                  : (previewInvoice.vatAmount && previewInvoice.vatAmount > 0)
                  ? previewInvoice.vatAmount
                  : Math.round(previewTaxable * 0.13 * 100) / 100;
                const previewGrandTotal = previewInvoice.total_amount || (previewTaxable + previewVat);
                const wordsNp = amountToNepaliWords(previewGrandTotal);
                const wordsEn = amountToEnglishWords(previewGrandTotal);

                return (
                  <>
                    {/* Items Table */}
                    <table style={{ width: "100%", borderCollapse: "collapse", border: "1px solid #0F172A", marginBottom: "14px", fontSize: "12px" }}>
                      <thead>
                        <tr style={{ background: "#F1F5F9", borderBottom: "1px solid #0F172A" }}>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", width: "40px", textAlign: "center" }}>{locale === "en" ? "S.N." : "क्र.सं."}</th>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", textAlign: "left" }}>{locale === "en" ? "Description / SKU" : "विवरण / वस्तु (Description)"}</th>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", width: "80px", textAlign: "center" }}>HS Code</th>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", width: "80px", textAlign: "right" }}>{locale === "en" ? "Quantity" : "परिमाण (Qty)"}</th>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", width: "95px", textAlign: "right" }}>{locale === "en" ? "Rate (Rs.)" : "दर (Rate Rs.)"}</th>
                          <th style={{ border: "1px solid #CBD5E1", padding: "6px 8px", width: "115px", textAlign: "right" }}>{locale === "en" ? "Amount (Rs.)" : "जम्मा रकम (Rs.)"}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(previewInvoice.order?.items && previewInvoice.order.items.length > 0) ? (
                          previewInvoice.order.items.map((it: any, idx: number) => {
                            const prod = products.find((p) => p.id === it.product_id);
                            return (
                              <tr key={idx} style={{ height: "32px" }}>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "center" }}>{idx + 1}</td>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontWeight: "600" }}>
                                  {prod ? `${prod.name} (${prod.code} · Size ${prod.size || "-"})` : `Product #${it.product_id}`}
                                </td>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "center", fontFamily: "monospace", fontSize: "11px" }}>
                                  {prod?.hs_code || "6403.99"}
                                </td>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace" }}>
                                  {it.quantity} pairs
                                </td>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace" }}>
                                  {fmtNpr(it.unit_price)}
                                </td>
                                <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "700" }}>
                                  {fmtNpr(it.total_price || (it.quantity * it.unit_price))}
                                </td>
                              </tr>
                            );
                          })
                        ) : (
                          <tr style={{ height: "32px" }}>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "center" }}>1</td>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontWeight: "600" }}>Wholesale Finished Footwear Dispatch</td>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "center", fontFamily: "monospace", fontSize: "11px" }}>6403.99</td>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace" }}>1 lot</td>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace" }}>{fmtNpr(previewTaxable)}</td>
                            <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "700" }}>{fmtNpr(previewTaxable)}</td>
                          </tr>
                        )}
                      </tbody>
                    </table>

                    {/* Statutory Calculation Breakdown Strip */}
                    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "14px" }}>
                      <table style={{ width: "350px", borderCollapse: "collapse", fontSize: "12px" }}>
                        <tbody>
                          <tr>
                            <td style={{ padding: "4px 8px", color: "#475569" }}>{locale === "en" ? "Taxable Subtotal:" : "जम्मा रकम (Sub-Total / Taxable Amount):"}</td>
                            <td style={{ padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "600" }}>
                              Rs. {fmtNpr(previewTaxable)}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: "4px 8px", color: "#1E3A8A", fontWeight: "600" }}>{locale === "en" ? "13% Value Added Tax:" : "१३% मूल्य अभिवृद्धि कर (13% VAT):"}</td>
                            <td style={{ padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "600", color: "#1E3A8A" }}>
                              Rs. {fmtNpr(previewVat)}
                            </td>
                          </tr>
                          <tr style={{ borderTop: "2px solid #0F172A", borderBottom: "2px solid #0F172A", background: "#F8FAFC" }}>
                            <td style={{ padding: "6px 8px", fontWeight: "800", color: "#0F172A" }}>{locale === "en" ? "Grand Total (NPR):" : "कुल जम्मा (Grand Total):"}</td>
                            <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "800", fontSize: "13px", color: "#0F172A" }}>
                              Rs. {fmtNpr(previewGrandTotal)}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: "4px 8px", color: "#059669", fontWeight: "600" }}>{locale === "en" ? "Amount Received:" : "प्राप्त रकम (Amount Received):"}</td>
                            <td style={{ padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "600", color: "#059669" }}>
                              Rs. {fmtNpr(previewInvoice.received_amount)}
                            </td>
                          </tr>
                          <tr>
                            <td style={{ padding: "4px 8px", color: "#DC2626", fontWeight: "700" }}>{locale === "en" ? "Receivable Balance Due:" : "बाँकी बक्यौता (Receivable Balance):"}</td>
                            <td style={{ padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontWeight: "700", color: "#DC2626" }}>
                              Rs. {fmtNpr(previewInvoice.receivable_amount)}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>

                    {/* Schedule-5 In Words (अक्षरमा) */}
                    <div style={{ marginTop: "10px", marginBottom: "20px", padding: "10px 14px", background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12px" }}>
                      <span style={{ fontWeight: "700", color: "#334155" }}>
                        {locale === "en" ? "In Words: " : "अक्षरमा (In Words): "}
                      </span>
                      <span style={{ fontStyle: "italic", color: "#0F172A", marginLeft: "4px" }}>
                        {locale === "en" ? wordsEn : `${wordsNp} (${wordsEn})`}
                      </span>
                    </div>
                  </>
                );
              })()}

              {/* Statutory Signature Block */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: "40px", paddingTop: "10px", fontSize: "11px", color: "#475569" }}>
                <div style={{ textAlign: "center", width: "180px", borderTop: "1px dashed #64748B", paddingTop: "4px" }}>
                  {locale === "en" ? "Buyer Signature" : "खरिदकर्ताको दस्तखत (Buyer Signature)"}
                </div>
                <div style={{ textAlign: "center", width: "180px", borderTop: "1px dashed #64748B", paddingTop: "4px" }}>
                  {locale === "en" ? "Authorized Signature" : "आधिकारिक दस्तखत (Authorized Signature)"}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Record Sale Modal Drawer with Sequential Keyboard Navigation */}
      {showOrderModal && (
        <div className="modal-overlay" role="presentation">
          <div className="modal-drawer" role="dialog" aria-modal="true" aria-labelledby="sales-drawer-title">
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShoppingBag size={16} color="#1E3A8A" />
                <h3 id="sales-drawer-title" style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Record Footwear Sale & Issue Tax Invoice
                </h3>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{ display: "flex", gap: "4px" }}>
                  <span className="kbd-hint">Ctrl+Enter ↵</span>
                  <span className="kbd-hint">Esc</span>
                </div>
                <button onClick={() => setShowOrderModal(false)} style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", marginLeft: "4px" }} aria-label="Close sales order dialog">
                  <X size={18} />
                </button>
              </div>
            </div>

            <form onSubmit={(e) => handleCreateOrder(e, false)} onKeyDown={handleFormKeyDown} style={{ display: "flex", flexDirection: "column", flex: 1 }}>
              <div className="modal-body">
                {/* Support Reference Error Banner */}
                {errorBanner && (
                  <div role="alert" style={{ background: "#FEF2F2", border: "1px solid #EF4444", borderRadius: "3px", padding: "10px 12px", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px", color: "#991B1B" }}>
                    <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
                      <AlertTriangle size={16} style={{ color: "#DC2626", flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: "700", color: "#991B1B" }}>
                          Transaction failed. Support reference: [{errorBanner.refCode || "req_unknown"}]
                        </div>
                        <div style={{ fontSize: "11.5px", color: "#B91C1C", marginTop: "2px" }}>
                          {errorBanner.message}
                        </div>
                      </div>
                    </div>
                    <button type="button" onClick={() => setErrorBanner(null)} style={{ background: "none", border: "none", color: "#DC2626", cursor: "pointer", padding: "0" }}>
                      <X size={15} />
                    </button>
                  </div>
                )}

                {/* Success Feedback Toast for Continuous Entry */}
                {successFeedback && (
                  <div role="status" aria-live="polite" style={{ background: "#ECFDF5", border: "1px solid #10B981", borderRadius: "3px", padding: "8px 12px", display: "flex", alignItems: "center", gap: "8px", color: "#065F46", fontSize: "12.5px", fontWeight: "600" }}>
                    <CheckCircle2 size={15} color="#059669" />
                    <span>{successFeedback}</span>
                  </div>
                )}

                {/* Company & Client PAN Banner */}
                <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "3px", padding: "8px 12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "#475569" }}>
                    COMPANY PAN: <strong style={{ color: "#1E3A8A", fontFamily: "monospace" }}>{COMPANY_PAN}</strong>
                  </span>
                  <span style={{ fontSize: "11px", color: "#64748B" }}>
                    Nepal 13% Statutory VAT Auto-Calculated
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "4px", background: "#FFFFFF", padding: "8px 10px", borderRadius: "3px", border: "1px solid #CBD5E1" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#0F172A", cursor: "pointer", userSelect: "none" }}>
                      <input
                        type="checkbox"
                        checked={continuousMode}
                        onChange={(e) => setContinuousMode(e.target.checked)}
                        style={{ accentColor: "#1E3A8A", cursor: "pointer" }}
                      />
                      <span style={{ fontWeight: "600" }}>Continuous Rapid Entry Mode</span>
                    </label>
                    <span style={{ fontSize: "11px", color: "#64748B" }}>
                      Hands-free line entry
                    </span>
                  </div>

                  {continuousMode && (
                    <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#475569", cursor: "pointer", userSelect: "none", marginLeft: "22px" }}>
                      <input
                        type="checkbox"
                        checked={keepClient}
                        onChange={(e) => setKeepClient(e.target.checked)}
                        style={{ accentColor: "#1E3A8A", cursor: "pointer" }}
                      />
                      <span>Retain selected client for multiple lines</span>
                    </label>
                  )}
                </div>

                {/* Immediate vs Deferred Dispatch Toggle */}
                <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "3px", padding: "8px 10px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#0F172A", cursor: "pointer", userSelect: "none" }}>
                    <input
                      type="checkbox"
                      checked={dispatchNow}
                      onChange={(e) => setDispatchNow(e.target.checked)}
                      style={{ accentColor: "#1E3A8A", cursor: "pointer" }}
                    />
                    <span style={{ fontWeight: "700" }}>Dispatch Immediately (तुरुन्तै निकासी गर्नुहोस् — Counter Sale)</span>
                  </label>
                  <div style={{ fontSize: "11px", color: "#64748B", marginLeft: "22px", marginTop: "2px" }}>
                    {dispatchNow
                      ? "Deducts physical stock immediately upon booking (Counter / Cash Sale)."
                      : "Reserves stock under Available-to-Promise (ATP) without deducting physical inventory."}
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>Client / Customer (Buyer PAN)</label>
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
                        {c.name} ({c.code}) — PAN: {c.pan_number || "N/A"}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>Footwear SKU</label>
                    {productId && (() => {
                      const p = products.find((x) => String(x.id) === productId);
                      return p ? (
                        <div style={{ display: "flex", gap: "6px", fontSize: "11px" }}>
                          <span style={{ padding: "1px 5px", background: "#EFF6FF", color: "#1E3A8A", borderRadius: "3px", fontWeight: "700", border: "1px solid #BFDBFE" }}>
                            Sz {p.size || "Std"}
                          </span>
                          <span style={{ padding: "1px 5px", background: "#F1F5F9", color: "#475569", borderRadius: "3px", border: "1px solid #CBD5E1" }}>
                            {p.color || "Black"}
                          </span>
                        </div>
                      ) : null;
                    })()}
                  </div>
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
                        {p.code} - {p.name} (Wholesale: Rs. {fmtNpr(p.unit_price)})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Dual-Unit Carton Packaging & Physical Reconciliation */}
                <div style={{ background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px 12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#334155" }}>
                      {locale === "en"
                        ? "Dual-Unit Carton Reconciliation"
                        : "कार्टुन र जोर मिलान (Dual-Unit Reconciliation)"}
                    </span>
                    <span style={{ fontSize: "10.5px", color: "#1E3A8A", fontWeight: "700", background: "#DBEAFE", padding: "1px 6px", borderRadius: "3px" }}>
                      {locale === "en" ? "1 Carton = 12 Pairs" : "१ कार्टुन = १२ जोर"}
                    </span>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
                    <div>
                      <label style={{ fontSize: "10.5px", textTransform: "uppercase", color: "#475569", fontWeight: "700", display: "block", marginBottom: "2px" }}>
                        {locale === "en" ? "Cartons (ctn)" : "कार्टुन (Cartons)"}
                      </label>
                      <input
                        type="number"
                        min="0"
                        className="input-field num-mono"
                        value={cartons}
                        onChange={(e) => {
                          const c = e.target.value;
                          setCartons(c);
                          const cVal = parseInt(c || "0", 10) || 0;
                          const lVal = parseInt(loosePairs || "0", 10) || 0;
                          setQuantity(String(cVal * 12 + lVal));
                        }}
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "10.5px", textTransform: "uppercase", color: "#475569", fontWeight: "700", display: "block", marginBottom: "2px" }}>
                        {locale === "en" ? "Loose Pairs" : "खुद्रा जोर (Loose Pairs)"}
                      </label>
                      <input
                        type="number"
                        min="0"
                        className="input-field num-mono"
                        value={loosePairs}
                        onChange={(e) => {
                          const l = e.target.value;
                          setLoosePairs(l);
                          const cVal = parseInt(cartons || "0", 10) || 0;
                          const lVal = parseInt(l || "0", 10) || 0;
                          setQuantity(String(cVal * 12 + lVal));
                        }}
                        placeholder="0"
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "10.5px", textTransform: "uppercase", color: "#475569", fontWeight: "700", display: "block", marginBottom: "2px" }}>
                        {locale === "en" ? "Total Pairs" : "जम्मा जोर (Total Pairs)"}
                      </label>
                      <input
                        ref={quantityRef}
                        type="number"
                        min="1"
                        className="input-field num-mono"
                        style={cartonMismatch ? { borderColor: "#DC2626", background: "#FEF2F2", color: "#991B1B" } : {}}
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        onKeyDown={(e) => handleKeyDown(e, unitPriceRef)}
                        required
                      />
                    </div>
                  </div>

                  {cartonMismatch && (
                    <div style={{ marginTop: "8px", padding: "6px 10px", background: "#FEE2E2", border: "1px solid #F87171", borderRadius: "3px", color: "#991B1B", fontSize: "11px", fontWeight: "600", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>⚠️ {cartonMismatchMsg}</span>
                      <button
                        type="button"
                        onClick={() => setQuantity(String(expectedPairs))}
                        style={{ fontSize: "10px", background: "#DC2626", color: "#FFFFFF", border: "none", borderRadius: "3px", padding: "3px 8px", cursor: "pointer", fontWeight: "700" }}
                      >
                        Sync to {expectedPairs} Pairs
                      </button>
                    </div>
                  )}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>Wholesale Unit Rate (Rs.)</label>
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
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>Initial Cash Received (Rs.)</label>
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
                </div>

                {/* Inline Nepal VAT & Financial Calculations Strip with Strict Paisa Arithmetic */}
                {(() => {
                  const q = Math.max(0, parseFloat(quantity) || 0);
                  const unitPricePaisa = toPaisa(unitPrice || "0");
                  const subtotalPaisa = Math.round(q * unitPricePaisa);
                  const { vatPaisa, grandTotalPaisa } = calculateVatPaisa(subtotalPaisa, 13);
                  const rcvPaisa = toPaisa(receivedAmount || "0");
                  const duePaisa = Math.max(0, grandTotalPaisa - rcvPaisa);
                  return (
                    <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "3px", padding: "8px 12px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", textAlign: "center" }}>
                      <div>
                        <div style={{ fontSize: "10px", color: "#64748B", textTransform: "uppercase", fontWeight: "700" }}>
                          {locale === "en" ? "Taxable Amount" : "करयोग्य रकम"}
                        </div>
                        <div className="num-mono-bold" style={{ fontSize: "12px", color: "#0F172A" }}>Rs. {fromPaisa(subtotalPaisa)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "10px", color: "#64748B", textTransform: "uppercase", fontWeight: "700" }}>
                          {locale === "en" ? "13% VAT" : "मूल्य अभिवृद्धि कर १३%"}
                        </div>
                        <div className="num-mono" style={{ fontSize: "12px", color: "#1E3A8A", fontWeight: "700" }}>Rs. {fromPaisa(vatPaisa)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "10px", color: "#64748B", textTransform: "uppercase", fontWeight: "700" }}>
                          {locale === "en" ? "Grand Total" : "कुल रकम"}
                        </div>
                        <div className="num-mono-bold" style={{ fontSize: "12px", color: "#1E3A8A" }}>Rs. {fromPaisa(grandTotalPaisa)}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: "10px", color: "#64748B", textTransform: "uppercase", fontWeight: "700" }}>
                          {locale === "en" ? "Balance Due" : "बाँकी बक्यौता"}
                        </div>
                        <div className="num-mono-bold" style={{ fontSize: "12px", color: duePaisa > 0 ? "#DC2626" : "#059669" }}>Rs. {fromPaisa(duePaisa)}</div>
                      </div>
                    </div>
                  );
                })()}

                <NepaliDatePicker
                  label={locale === "en" ? "Order Date" : "अर्डर मिति (Order Date)"}
                  valueAd={orderDateAd}
                  valueBs={orderDateBs}
                  onChange={({ ad, bs }) => {
                    setOrderDateAd(ad);
                    setOrderDateBs(bs);
                  }}
                  required
                />
              </div>

              <div className="modal-footer">
                <span style={{ fontSize: "11px", color: "#64748B" }}>
                  <span className="kbd-hint">Esc</span> close • <span className="kbd-hint">Ctrl+Enter</span> commit • <span className="kbd-hint">Enter</span> next
                </span>

                <div style={{ display: "flex", gap: "8px" }}>
                  <button type="button" className="btn-secondary" onClick={() => setShowOrderModal(false)}>
                    Close
                  </button>
                  {continuousMode && (
                    <button type="button" className="btn-secondary" onClick={(e) => handleCreateOrder(e, true)} disabled={submitting || cartonMismatch || enteredPairs <= 0}>
                      Save & Close
                    </button>
                  )}
                  <button
                    ref={submitButtonRef}
                    type="submit"
                    className="btn-primary"
                    disabled={submitting || cartonMismatch || enteredPairs <= 0}
                    style={{
                      background: cartonMismatch ? "#94A3B8" : "#1E3A8A",
                      borderColor: cartonMismatch ? "#94A3B8" : "#1E3A8A",
                      cursor: cartonMismatch ? "not-allowed" : "pointer"
                    }}
                  >
                    {submitting ? "Writing to Ledger..." : continuousMode ? "Commit & Next Sale ↵" : "Commit Sale & Issue Invoice"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DEFERRED DISPATCH MODAL */}
      {dispatchingOrder && (
        <div className="modal-overlay" role="presentation" style={{ zIndex: 9999 }}>
          <div
            className="modal-drawer"
            role="dialog"
            aria-modal="true"
            style={{
              maxWidth: "620px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "0"
            }}
          >
            <div style={{ background: "#F1F5F9", borderBottom: "1px solid #CBD5E1", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Truck size={17} color="#1E3A8A" />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", textTransform: "uppercase" }}>
                    Physical Warehouse Dispatch (सामान निकासी)
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748B" }}>
                    Order {dispatchingOrder.order_number} · Client #{dispatchingOrder.client_id}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDispatchingOrder(null)}
                style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", padding: "4px" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmDispatch} style={{ display: "flex", flexDirection: "column" }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px", padding: "16px" }}>
                {dispatchError && (
                  <div role="alert" style={{ background: "#FEF2F2", border: "1px solid #EF4444", borderRadius: "3px", padding: "10px 12px", display: "flex", gap: "8px", alignItems: "flex-start", color: "#991B1B", fontSize: "12px" }}>
                    <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: "1px" }} />
                    <div>{dispatchError}</div>
                  </div>
                )}

                {/* Stock Check Table */}
                {dispatchingOrder.items && dispatchingOrder.items.length > 0 && (
                  <div style={{ background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px" }}>
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase", marginBottom: "6px" }}>
                      Order Line Items & Physical Stock Check
                    </div>
                    <table style={{ width: "100%", fontSize: "11.5px", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ borderBottom: "1px solid #CBD5E1", textAlign: "left", color: "#64748B" }}>
                          <th style={{ padding: "4px" }}>Product SKU</th>
                          <th style={{ padding: "4px", textAlign: "right" }}>Req. Pairs</th>
                          <th style={{ padding: "4px", textAlign: "right" }}>Physical On-Hand</th>
                          <th style={{ padding: "4px", textAlign: "center" }}>Stock Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dispatchingOrder.items.map((it: any, idx: number) => {
                          const prod = products.find((p) => p.id === it.product_id);
                          const stock = stockBalances.find((s) => s.product_id === it.product_id);
                          const onHand = stock ? (stock.physical_stock ?? 0) : null;
                          const isShort = onHand !== null && onHand < it.quantity;
                          return (
                            <tr key={idx} style={{ borderBottom: "1px solid #F1F5F9" }}>
                              <td style={{ padding: "4px", fontWeight: "600", color: "#0F172A" }}>
                                {prod ? `${prod.code} (${prod.name})` : `SKU #${it.product_id}`}
                              </td>
                              <td style={{ padding: "4px", textAlign: "right", fontFamily: "monospace", fontWeight: "700" }}>
                                {it.quantity}
                              </td>
                              <td style={{ padding: "4px", textAlign: "right", fontFamily: "monospace", color: isShort ? "#DC2626" : "#059669", fontWeight: "700" }}>
                                {onHand !== null ? onHand : "-"}
                              </td>
                              <td style={{ padding: "4px", textAlign: "center" }}>
                                {isShort ? (
                                  <span style={{ fontSize: "10px", color: "#DC2626", background: "#FEF2F2", padding: "1px 5px", borderRadius: "2px", fontWeight: "700" }}>Insufficient</span>
                                ) : (
                                  <span style={{ fontSize: "10px", color: "#059669", background: "#ECFDF5", padding: "1px 5px", borderRadius: "2px", fontWeight: "700" }}>Available</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                <NepaliDatePicker
                  label={locale === "en" ? "Dispatch Date" : "निकासी मिति (Dispatch Date)"}
                  valueAd={dispatchDateAd}
                  valueBs={dispatchDateBs}
                  onChange={({ ad, bs }) => {
                    setDispatchDateAd(ad);
                    setDispatchDateBs(bs);
                  }}
                  required
                />

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Carrier / Transport Name
                    </label>
                    <input
                      type="text"
                      className="input-field"
                      placeholder="e.g. Sajha Transport / Local Cargo"
                      value={carrierName}
                      onChange={(e) => setCarrierName(e.target.value)}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Vehicle Number
                    </label>
                    <input
                      type="text"
                      className="input-field num-mono"
                      placeholder="e.g. BA 2 KHA 4521"
                      value={vehicleNumber}
                      onChange={(e) => setVehicleNumber(e.target.value)}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                    Dispatch Notes / Waybill Details
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Gate pass number, driver phone, carton packaging notes..."
                    value={dispatchNotes}
                    onChange={(e) => setDispatchNotes(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ padding: "12px 16px", display: "flex", justifyContent: "flex-end", gap: "8px", borderTop: "1px solid #CBD5E1" }}>
                <button type="button" className="btn-secondary" onClick={() => setDispatchingOrder(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={dispatchSubmitting}
                  style={{ background: "#1E3A8A", borderColor: "#1E3A8A", display: "inline-flex", alignItems: "center", gap: "6px" }}
                >
                  <Truck size={14} /> {dispatchSubmitting ? "Dispatching..." : "Confirm Physical Dispatch"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RECORD SALES EXPENSE MODAL */}
      {showExpenseModal && (
        <div className="modal-overlay" role="presentation" style={{ zIndex: 9999 }}>
          <div
            className="modal-drawer"
            role="dialog"
            aria-modal="true"
            style={{
              maxWidth: "520px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "0"
            }}
          >
            <div style={{ background: "#F1F5F9", borderBottom: "1px solid #CBD5E1", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Wallet size={16} color="#047857" />
                <span style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", textTransform: "uppercase" }}>
                  Record Sales Expense (बिक्री खर्च प्रविष्टि)
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowExpenseModal(false)}
                style={{ background: "none", border: "none", color: "#64748B", cursor: "pointer", padding: "4px" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateExpense} style={{ display: "flex", flexDirection: "column" }}>
              <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: "12px", padding: "16px" }}>
                {expenseError && (
                  <div role="alert" style={{ background: "#FEF2F2", border: "1px solid #EF4444", borderRadius: "3px", padding: "8px 12px", display: "flex", gap: "8px", alignItems: "flex-start", color: "#991B1B", fontSize: "12px" }}>
                    <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: "1px" }} />
                    <div>{expenseError}</div>
                  </div>
                )}

                <NepaliDatePicker
                  label={locale === "en" ? "Expense Date" : "खर्च मिति (Expense Date)"}
                  valueAd={expenseDateAd}
                  valueBs={expenseDateBs}
                  onChange={({ ad, bs }) => {
                    setExpenseDateAd(ad);
                    setExpenseDateBs(bs);
                  }}
                  required
                />

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                    Particular / Description *
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="e.g. Master carton boxes for Pokhara shipment"
                    value={expenseParticular}
                    onChange={(e) => setExpenseParticular(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Category *
                    </label>
                    <select
                      className="input-field"
                      value={expenseCategory}
                      onChange={(e) => setExpenseCategory(e.target.value)}
                      required
                    >
                      <option value="PACKAGING_MATERIAL">Packaging Material (प्याकेजिङ)</option>
                      <option value="TRANSPORT_FREIGHT">Transport & Freight (ढुवानी)</option>
                      <option value="LOADING_UNLOADING">Loading / Unloading (लोडिङ)</option>
                      <option value="SALES_COMMISSION">Sales Commission (कमिसन)</option>
                      <option value="MARKETING_PROMOTION">Marketing & Promotion (प्रचार)</option>
                      <option value="OTHER">Other Sales Expense (अन्य)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Amount (NPR) *
                    </label>
                    <input
                      type="number"
                      min="0.01"
                      step="0.01"
                      className="input-field num-mono"
                      placeholder="0.00"
                      value={expenseAmount}
                      onChange={(e) => setExpenseAmount(e.target.value)}
                      required
                    />
                    {expenseAmount && (
                      <div style={{ fontSize: "10px", color: "#64748B", marginTop: "2px" }}>
                        = {toPaisa(expenseAmount)} paisa (Exact Integer Paisa)
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Payment Method
                    </label>
                    <select
                      className="input-field"
                      value={expensePaymentMethod}
                      onChange={(e) => setExpensePaymentMethod(e.target.value)}
                    >
                      <option value="CASH">Cash (नगद)</option>
                      <option value="BANK_TRANSFER">Bank Transfer (बैंक ट्रान्सफर)</option>
                      <option value="CHEQUE">Cheque (चेक)</option>
                      <option value="CREDIT">Credit / Payable (उधारो)</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                      Link to Sales Order (Optional)
                    </label>
                    <select
                      className="input-field"
                      value={expenseOrderId}
                      onChange={(e) => setExpenseOrderId(e.target.value)}
                    >
                      <option value="">-- None / General Expense --</option>
                      {orders.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.order_number} ({o.order_date_ad})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", fontWeight: "700" }}>
                    Remarks / Voucher Note
                  </label>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Bill / receipt number, payee name..."
                    value={expenseRemarks}
                    onChange={(e) => setExpenseRemarks(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-footer" style={{ padding: "12px 16px", display: "flex", justifyContent: "flex-end", gap: "8px", borderTop: "1px solid #CBD5E1" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowExpenseModal(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={expenseSubmitting}
                  style={{ background: "#047857", borderColor: "#047857" }}
                >
                  {expenseSubmitting ? "Recording..." : "Record Expense (खर्च प्रविष्टि)"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
