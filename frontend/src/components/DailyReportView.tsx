"use client";

import React, { useState, useEffect } from "react";
import { Calendar, Factory, ShoppingBag, ArrowUpRight, ArrowDownLeft, Users, CreditCard } from "lucide-react";

export function DailyReportView() {
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Date Filter Bar */}
      <div className="glass-card" style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Calendar size={20} color="#3b82f6" />
          <span style={{ fontWeight: "600", fontSize: "15px" }}>Select Daily Report Date (AD):</span>
        </div>
        <input
          type="date"
          className="input-field"
          style={{ width: "200px" }}
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
        />
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>Loading daily statistics...</div>
      ) : reportData ? (
        <>
          {/* Top KPI Cards Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            {/* Production Pairs */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span style={{ color: "#94a3b8", fontSize: "13px", fontWeight: "600" }}>PRODUCTION</span>
                <Factory size={20} color="#34d399" />
              </div>
              <div style={{ fontSize: "28px", fontWeight: "700", color: "#f8fafc" }}>
                {reportData.production.total_pairs_produced} <span style={{ fontSize: "14px", fontWeight: "400", color: "#94a3b8" }}>pairs</span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "6px", display: "flex", alignItems: "center", gap: "4px" }}>
                <Users size={12} /> {reportData.production.worker_count} active workers
              </div>
            </div>

            {/* Total Sales Amount */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span style={{ color: "#94a3b8", fontSize: "13px", fontWeight: "600" }}>SALES REVENUE</span>
                <ShoppingBag size={20} color="#60a5fa" />
              </div>
              <div style={{ fontSize: "28px", fontWeight: "700", color: "#f8fafc" }}>
                Rs. {reportData.sales.total_sales_amount.toLocaleString()}
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "6px" }}>
                {reportData.sales.order_count} orders created today
              </div>
            </div>

            {/* Received vs Receivable */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span style={{ color: "#94a3b8", fontSize: "13px", fontWeight: "600" }}>CASH RECEIVED</span>
                <CreditCard size={20} color="#fbbf24" />
              </div>
              <div style={{ fontSize: "24px", fontWeight: "700", color: "#34d399" }}>
                Rs. {reportData.sales.total_received_amount.toLocaleString()}
              </div>
              <div style={{ fontSize: "12px", color: "#f87171", marginTop: "6px" }}>
                Receivable Balance: Rs. {reportData.sales.total_receivable_amount.toLocaleString()}
              </div>
            </div>

            {/* Net Stock Movement */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <span style={{ color: "#94a3b8", fontSize: "13px", fontWeight: "600" }}>NET STOCK CHANGE</span>
                {reportData.stock_movement_summary.net_change_pairs >= 0 ? (
                  <ArrowUpRight size={20} color="#34d399" />
                ) : (
                  <ArrowDownLeft size={20} color="#f87171" />
                )}
              </div>
              <div style={{ fontSize: "28px", fontWeight: "700", color: reportData.stock_movement_summary.net_change_pairs >= 0 ? "#34d399" : "#f87171" }}>
                {reportData.stock_movement_summary.net_change_pairs > 0 ? `+${reportData.stock_movement_summary.net_change_pairs}` : reportData.stock_movement_summary.net_change_pairs} <span style={{ fontSize: "14px", fontWeight: "400", color: "#94a3b8" }}>pairs</span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b", marginTop: "6px" }}>
                In: +{reportData.stock_movement_summary.total_stock_in_pairs} | Out: -{reportData.stock_movement_summary.total_stock_out_pairs}
              </div>
            </div>
          </div>

          {/* Batches Table */}
          <div className="glass-card" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc" }}>
              Today's Production Batches
            </h3>
            {reportData.production.batches.length === 0 ? (
              <div style={{ color: "#94a3b8", fontSize: "14px" }}>No production batches recorded for this date.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Batch Number</th>
                      <th>Product ID</th>
                      <th>Target Qty</th>
                      <th>Produced Qty</th>
                      <th>Workers</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reportData.production.batches.map((b: any) => (
                      <tr key={b.id}>
                        <td style={{ fontWeight: "600" }}>{b.batch_number}</td>
                        <td>#{b.product_id}</td>
                        <td>{b.target_quantity} pairs</td>
                        <td style={{ color: "#34d399", fontWeight: "600" }}>{b.produced_quantity} pairs</td>
                        <td>{b.worker_count}</td>
                        <td><span className="badge badge-success">{b.status}</span></td>
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
