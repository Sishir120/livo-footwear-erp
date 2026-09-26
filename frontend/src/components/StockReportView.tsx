"use client";

import React, { useState, useEffect } from "react";
import { Boxes, Search, Filter, AlertTriangle, CheckCircle } from "lucide-react";

export function StockReportView() {
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockReport();
  }, [categoryFilter]);

  const fetchStockReport = async () => {
    setLoading(true);
    try {
      const url = categoryFilter !== "all" 
        ? `/api/v1/reports/stock?category=${encodeURIComponent(categoryFilter)}` 
        : `/api/v1/reports/stock`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setStockItems(data.items || []);
        setSummary(data.summary || null);
      }
    } catch (e) {
      console.error("Failed to fetch stock report", e);
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = stockItems.filter(item => 
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Summary KPI header */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
          <div className="glass-card" style={{ padding: "18px 20px" }}>
            <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600" }}>TOTAL PRODUCT VARIANTS</div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#f8fafc" }}>
              {summary.total_products_count} <span style={{ fontSize: "14px", color: "#94a3b8" }}>items</span>
            </div>
          </div>
          <div className="glass-card" style={{ padding: "18px 20px" }}>
            <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600" }}>TOTAL STOCK IN HAND</div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#34d399" }}>
              {summary.total_stock_pairs.toLocaleString()} <span style={{ fontSize: "14px", color: "#94a3b8" }}>pairs</span>
            </div>
          </div>
          <div className="glass-card" style={{ padding: "18px 20px" }}>
            <div style={{ color: "#94a3b8", fontSize: "12px", fontWeight: "600" }}>ESTIMATED STOCK VALUE</div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#60a5fa" }}>
              Rs. {summary.total_stock_value.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="glass-card" style={{ padding: "16px 20px", display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: "250px" }}>
          <Search size={18} color="#94a3b8" />
          <input
            type="text"
            className="input-field"
            placeholder="Search by code or product name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Filter size={18} color="#94a3b8" />
          <select
            className="input-field"
            style={{ width: "160px", cursor: "pointer" }}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="Boot">Boot</option>
            <option value="Shoe">Shoe</option>
            <option value="Slipper">Slipper</option>
            <option value="Sandal">Sandal</option>
          </select>
        </div>
      </div>

      {/* Main Stock Table */}
      <div className="glass-card" style={{ padding: "20px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
          <Boxes size={20} color="#3b82f6" /> Inventory Stock Ledger (Derived from Movements)
        </h3>

        {loading ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>Loading stock report...</div>
        ) : filteredItems.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8" }}>No products found matching criteria.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Product Name</th>
                  <th>Category</th>
                  <th>Size</th>
                  <th>Color</th>
                  <th style={{ textAlign: "right" }}>Unit Rate</th>
                  <th style={{ textAlign: "right" }}>Current Stock</th>
                  <th style={{ textAlign: "right" }}>Estimated Value</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <tr key={item.product_id}>
                    <td style={{ fontWeight: "700", color: "#3b82f6" }}>{item.code}</td>
                    <td style={{ fontWeight: "600" }}>{item.name}</td>
                    <td>{item.category || "-"}</td>
                    <td>{item.size || "-"}</td>
                    <td>{item.color || "-"}</td>
                    <td style={{ textAlign: "right" }}>Rs. {item.unit_price.toLocaleString()}</td>
                    <td style={{ textAlign: "right", fontWeight: "700", color: item.current_stock_pairs > 0 ? "#34d399" : "#f87171" }}>
                      {item.current_stock_pairs} pairs
                    </td>
                    <td style={{ textAlign: "right" }}>Rs. {item.estimated_value.toLocaleString()}</td>
                    <td>
                      <span className={`badge ${item.status === 'In Stock' ? 'badge-success' : item.status === 'Low Stock' ? 'badge-warning' : 'badge-danger'}`}>
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
