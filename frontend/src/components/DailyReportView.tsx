"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Calendar,
  Factory,
  ShoppingBag,
  ArrowUpRight,
  ArrowDownLeft,
  Users,
  CreditCard,
  Download,
  Search,
  BarChart2,
  TrendingUp,
  PieChart as PieIcon,
  RefreshCw,
  Clock
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { exportToCSV } from "../utils/csvExport";
import { useLocale } from "../context/LocaleContext";

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"];

export function DailyReportView() {
  const { t } = useLocale();
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [reportData, setReportData] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [batchSearch, setBatchSearch] = useState<string>("");
  const [orderSearch, setOrderSearch] = useState<string>("");

  useEffect(() => {
    // Pre-load reference dictionaries for names
    Promise.all([
      fetch("/api/v1/production/products").then((r) => (r.ok ? r.json() : [])),
      fetch("/api/v1/sales/clients").then((r) => (r.ok ? r.json() : []))
    ])
      .then(([prods, clis]) => {
        setProducts(prods || []);
        setClients(clis || []);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    fetchReport(selectedDate);
  }, [selectedDate]);

  const fetchReport = async (date: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/reports/daily?date_ad=${date}`);
      if (res.ok) {
        const data = await res.json();
        setReportData(data);
      }
    } catch (e) {
      console.error("Failed to load daily report", e);
    } finally {
      setLoading(false);
    }
  };

  const getProductName = (id: number) => {
    const p = products.find((x) => x.id === id);
    return p ? `${p.code} (${p.name})` : `Product #${id}`;
  };

  const getClientName = (id: number) => {
    const c = clients.find((x) => x.id === id);
    return c ? `${c.name} (${c.code})` : `Client #${id}`;
  };

  // Filtered Batches
  const filteredBatches = useMemo(() => {
    if (!reportData?.production?.batches) return [];
    if (!batchSearch.trim()) return reportData.production.batches;
    const q = batchSearch.toLowerCase();
    return reportData.production.batches.filter((b: any) => {
      const name = getProductName(b.product_id).toLowerCase();
      const num = (b.batch_number || "").toLowerCase();
      return name.includes(q) || num.includes(q);
    });
  }, [reportData, batchSearch, products]);

  // Filtered Orders
  const filteredOrders = useMemo(() => {
    if (!reportData?.sales?.orders) return [];
    if (!orderSearch.trim()) return reportData.sales.orders;
    const q = orderSearch.toLowerCase();
    return reportData.sales.orders.filter((o: any) => {
      const name = getClientName(o.client_id).toLowerCase();
      const num = (o.order_number || "").toLowerCase();
      return name.includes(q) || num.includes(q);
    });
  }, [reportData, orderSearch, clients]);

  // Chart Data 1: Production by Product
  const productionChartData = useMemo(() => {
    if (!reportData?.production?.batches?.length) return [];
    const map = new Map<string, number>();
    for (const b of reportData.production.batches) {
      const p = products.find((x) => x.id === b.product_id);
      const label = p ? p.code : `ID #${b.product_id}`;
      map.set(label, (map.get(label) || 0) + (b.produced_quantity || 0));
    }
    return Array.from(map.entries()).map(([name, pairs]) => ({
      name,
      pairs
    }));
  }, [reportData, products]);

  // Chart Data 2: Sales vs Production Comparison
  const volumeComparisonData = useMemo(() => {
    if (!reportData) return [];
    return [
      {
        metric: "Factory Volume",
        Produced: reportData.production.total_pairs_produced,
        Dispatched: reportData.stock_movement_summary.total_stock_out_pairs
      }
    ];
  }, [reportData]);

  // Chart Data 3: Financial Cash vs Receivable breakdown
  const financialBreakdownData = useMemo(() => {
    if (!reportData?.sales) return [];
    const rcv = reportData.sales.total_received_amount || 0;
    const bal = reportData.sales.total_receivable_amount || 0;
    if (rcv === 0 && bal === 0) return [];
    return [
      { name: "Cash Received", value: rcv, color: "#10b981" },
      { name: "Receivable Balance", value: bal, color: "#f43f5e" }
    ];
  }, [reportData]);

  // CSV Exporters
  const handleExportBatches = () => {
    if (!filteredBatches.length) return;
    const headers = ["Batch Number", "Product", "Target Pairs", "Produced Pairs", "Worker Count", "Status", "Date AD"];
    const rows = filteredBatches.map((b: any) => [
      b.batch_number,
      getProductName(b.product_id),
      b.target_quantity,
      b.produced_quantity,
      b.worker_count,
      b.status,
      selectedDate
    ]);
    exportToCSV(`Production_Batches_${selectedDate}`, headers, rows);
  };

  const handleExportOrders = () => {
    if (!filteredOrders.length) return;
    const headers = ["Order Number", "Client Name", "Date AD", "Date BS", "Total Amount (NPR)", "Received (NPR)", "Receivable (NPR)", "Status"];
    const rows = filteredOrders.map((o: any) => [
      o.order_number,
      getClientName(o.client_id),
      o.order_date_ad,
      o.order_date_bs,
      o.total_amount,
      o.received_amount,
      o.receivable_amount,
      o.status
    ]);
    exportToCSV(`Sales_Orders_${selectedDate}`, headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Controls Bar */}
      <div className="glass-card" style={{ padding: "14px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ background: "rgba(59, 130, 246, 0.15)", padding: "8px", borderRadius: "8px" }}>
            <Calendar size={18} color="#3b82f6" />
          </div>
          <div>
            <div style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.06em", color: "#94a3b8", fontWeight: "700" }}>Daily Operational Report</div>
            <div style={{ fontWeight: "700", fontSize: "15px", color: "#f8fafc" }}>Date Scope (AD): {selectedDate}</div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <input
            type="date"
            className="input-field"
            style={{ width: "170px", padding: "6px 12px", fontSize: "13px" }}
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />
          <button
            onClick={() => fetchReport(selectedDate)}
            className="btn-secondary"
            style={{ padding: "7px 12px", fontSize: "13px" }}
            title="Refresh statistics"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: "60px", textAlign: "center", color: "#94a3b8" }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px" }} />
          <div>Aggregating daily factory analytics & movements...</div>
        </div>
      ) : reportData ? (
        <>
          {/* Executive KPI Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
            {/* KPI 1: Production */}
            <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #10b981" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>{t("production_output").toUpperCase()}</span>
                <Factory size={18} color="#10b981" />
              </div>
              <div style={{ fontSize: "26px", fontWeight: "700", color: "#f8fafc" }} className="num-mono-bold">
                {reportData.production.total_pairs_produced.toLocaleString()}{" "}
                <span style={{ fontSize: "13px", fontWeight: "400", color: "#94a3b8" }}>{t("pairs")}</span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px", display: "flex", alignItems: "center", gap: "6px" }}>
                <Users size={12} /> {reportData.production.worker_count} {t("active_workers")} | {reportData.production.batch_count} {t("production_batches")}
              </div>
            </div>

            {/* KPI 2: Sales Revenue */}
            <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #3b82f6" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>{t("gross_sales").toUpperCase()}</span>
                <ShoppingBag size={18} color="#3b82f6" />
              </div>
              <div style={{ fontSize: "24px", fontWeight: "700", color: "#f8fafc" }} className="num-mono-bold">
                Rs. {reportData.sales.total_sales_amount.toLocaleString()}
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
                {reportData.sales.order_count} client orders booked
              </div>
            </div>

            {/* KPI 3: Cash Realization */}
            <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #f59e0b" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>{t("cash_received").toUpperCase()}</span>
                <CreditCard size={18} color="#f59e0b" />
              </div>
              <div style={{ fontSize: "24px", fontWeight: "700", color: "#10b981" }} className="num-mono-bold">
                Rs. {reportData.sales.total_received_amount.toLocaleString()}
              </div>
              <div style={{ fontSize: "12px", color: reportData.sales.total_receivable_amount > 0 ? "#f87171" : "#64748b", marginTop: "4px" }}>
                {t("accounts_receivable")}: Rs. {reportData.sales.total_receivable_amount.toLocaleString()}
              </div>
            </div>

            {/* KPI 4: Net Stock Movement */}
            <div className="glass-card" style={{ padding: "16px 18px", borderLeft: reportData.stock_movement_summary.net_change_pairs >= 0 ? "3px solid #10b981" : "3px solid #f43f5e" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>NET STOCK DELTA</span>
                {reportData.stock_movement_summary.net_change_pairs >= 0 ? (
                  <ArrowUpRight size={18} color="#10b981" />
                ) : (
                  <ArrowDownLeft size={18} color="#f43f5e" />
                )}
              </div>
              <div
                style={{
                  fontSize: "26px",
                  fontWeight: "700",
                  color: reportData.stock_movement_summary.net_change_pairs >= 0 ? "#10b981" : "#f87171"
                }}
                className="num-mono-bold"
              >
                {reportData.stock_movement_summary.net_change_pairs > 0
                  ? `+${reportData.stock_movement_summary.net_change_pairs}`
                  : reportData.stock_movement_summary.net_change_pairs}{" "}
                <span style={{ fontSize: "13px", fontWeight: "400", color: "#94a3b8" }}>pairs</span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }} className="num-mono">
                +In: {reportData.stock_movement_summary.total_stock_in_pairs} | -Out: {reportData.stock_movement_summary.total_stock_out_pairs}
              </div>
            </div>
          </div>

          {/* Visual Analytics Row */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            {/* Chart 1: Production by Model */}
            <div className="glass-card" style={{ padding: "18px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <BarChart2 size={16} color="#3b82f6" />
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "#f8fafc", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    Production Output by Model
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "#94a3b8" }}>Pairs Produced</span>
              </div>

              {productionChartData.length === 0 ? (
                <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                  No batch outputs on this date.
                </div>
              ) : (
                <div style={{ width: "100%", height: "200px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={productionChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                      <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                        formatter={(val: any) => [`${val} pairs`, "Output"]}
                      />
                      <Bar dataKey="pairs" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Chart 2: Daily Volume Comparison */}
            <div className="glass-card" style={{ padding: "18px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <TrendingUp size={16} color="#10b981" />
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "#f8fafc", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    Produced vs Dispatched
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "#94a3b8" }}>Daily Pairs</span>
              </div>

              <div style={{ width: "100%", height: "200px" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={volumeComparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="metric" stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                    <Bar dataKey="Produced" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Dispatched" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 3: Cash Realization Ratio */}
            <div className="glass-card" style={{ padding: "18px 20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <PieIcon size={16} color="#f59e0b" />
                  <span style={{ fontSize: "13px", fontWeight: "700", color: "#f8fafc", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                    Cash Realization Ratio
                  </span>
                </div>
                <span style={{ fontSize: "11px", color: "#94a3b8" }}>NPR</span>
              </div>

              {financialBreakdownData.length === 0 ? (
                <div style={{ height: "180px", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                  No sales booked today.
                </div>
              ) : (
                <div style={{ width: "100%", height: "200px" }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={financialBreakdownData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={75}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {financialBreakdownData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                        formatter={(val: any) => [`Rs. ${Number(val).toLocaleString()}`, "Amount"]}
                      />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* Section 1: Production Batches Table */}
          <div className="glass-card" style={{ padding: "18px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Factory size={18} color="#10b981" />
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
                  Today's Finished Production Batches ({filteredBatches.length})
                </h3>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(15, 23, 42, 0.6)", padding: "4px 10px", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                  <Search size={14} color="#94a3b8" />
                  <input
                    type="text"
                    placeholder="Search batch or model..."
                    value={batchSearch}
                    onChange={(e) => setBatchSearch(e.target.value)}
                    style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "12px", outline: "none", width: "160px" }}
                  />
                </div>
                <button onClick={handleExportBatches} className="btn-export" disabled={!filteredBatches.length}>
                  <Download size={13} /> Export CSV
                </button>
              </div>
            </div>

            {filteredBatches.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                No production batches recorded for this date.
              </div>
            ) : (
              <div className="table-container-dense">
                <table className="table-dense">
                  <thead>
                    <tr>
                      <th style={{ width: "140px" }}>Batch Number</th>
                      <th>Product Description</th>
                      <th style={{ textAlign: "right", width: "110px" }}>Target</th>
                      <th style={{ textAlign: "right", width: "120px" }}>Produced</th>
                      <th style={{ textAlign: "right", width: "90px" }}>Workers</th>
                      <th style={{ width: "110px" }}>Status</th>
                      <th style={{ width: "120px" }}>Ledger Impact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredBatches.map((b: any) => (
                      <tr key={b.id}>
                        <td style={{ fontWeight: "700", color: "#3b82f6" }} className="num-mono">
                          {b.batch_number}
                        </td>
                        <td style={{ fontWeight: "500" }}>{getProductName(b.product_id)}</td>
                        <td style={{ textAlign: "right" }} className="num-mono">
                          {b.target_quantity} prs
                        </td>
                        <td style={{ textAlign: "right", color: "#10b981", fontWeight: "700" }} className="num-mono-bold">
                          {b.produced_quantity} pairs
                        </td>
                        <td style={{ textAlign: "right" }} className="num-mono">
                          {b.worker_count}
                        </td>
                        <td>
                          <span className="badge badge-success">{b.status}</span>
                        </td>
                        <td>
                          <span className="badge badge-info num-mono">+{b.produced_quantity} IN</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Section 2: Sales Orders Table */}
          <div className="glass-card" style={{ padding: "18px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShoppingBag size={18} color="#3b82f6" />
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#f8fafc" }}>
                  Today's Sales Bookings & Dispatches ({filteredOrders.length})
                </h3>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", background: "rgba(15, 23, 42, 0.6)", padding: "4px 10px", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                  <Search size={14} color="#94a3b8" />
                  <input
                    type="text"
                    placeholder="Search order or client..."
                    value={orderSearch}
                    onChange={(e) => setOrderSearch(e.target.value)}
                    style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "12px", outline: "none", width: "160px" }}
                  />
                </div>
                <button onClick={handleExportOrders} className="btn-export" disabled={!filteredOrders.length}>
                  <Download size={13} /> Export CSV
                </button>
              </div>
            </div>

            {filteredOrders.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
                No client sales orders recorded for this date.
              </div>
            ) : (
              <div className="table-container-dense">
                <table className="table-dense">
                  <thead>
                    <tr>
                      <th style={{ width: "140px" }}>Order Number</th>
                      <th>Client / Buyer</th>
                      <th style={{ width: "130px" }}>Date (AD/BS)</th>
                      <th style={{ textAlign: "right", width: "130px" }}>Total Amount</th>
                      <th style={{ textAlign: "right", width: "120px" }}>Cash Received</th>
                      <th style={{ textAlign: "right", width: "130px" }}>Receivable</th>
                      <th style={{ width: "110px" }}>Dispatch</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredOrders.map((o: any) => (
                      <tr key={o.id}>
                        <td style={{ fontWeight: "700", color: "#3b82f6" }} className="num-mono">
                          {o.order_number}
                        </td>
                        <td style={{ fontWeight: "600" }}>{getClientName(o.client_id)}</td>
                        <td style={{ fontSize: "12px", color: "#94a3b8" }}>
                          {o.order_date_ad} <span style={{ fontSize: "11px" }}>({o.order_date_bs} BS)</span>
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
                        <td>
                          <span className={`badge ${o.delivered ? "badge-success" : "badge-warning"}`}>
                            {o.delivered ? "Dispatched" : "Pending"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
