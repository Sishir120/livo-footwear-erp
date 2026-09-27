"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Boxes,
  Search,
  Filter,
  AlertTriangle,
  CheckCircle,
  Download,
  BarChart3,
  Layers,
  ArrowUpDown,
  RefreshCw,
  Info
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

const CATEGORY_COLORS: Record<string, string> = {
  Boot: "#3b82f6",
  Shoe: "#10b981",
  Slipper: "#f59e0b",
  Sandal: "#8b5cf6",
  Other: "#64748b"
};

const PARIS_POINTS = [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43];

export function StockReportView() {
  const { t } = useLocale();
  const [stockItems, setStockItems] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"matrix" | "detailed">("matrix");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockReport();
  }, [categoryFilter]);

  const fetchStockReport = async () => {
    setLoading(true);
    try {
      const url =
        categoryFilter !== "all"
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

  // Filtered Items
  const filteredItems = useMemo(() => {
    return stockItems.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.color || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(item.size || "").includes(searchQuery);

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "in_stock" && item.current_stock_pairs > 50) ||
        (statusFilter === "low_stock" && item.current_stock_pairs > 0 && item.current_stock_pairs <= 50) ||
        (statusFilter === "out_of_stock" && item.current_stock_pairs <= 0);

      return matchesSearch && matchesStatus;
    });
  }, [stockItems, searchQuery, statusFilter]);

  // High-Density Sizing Matrix Aggregation (Paris Points 32-43)
  const matrixRows = useMemo(() => {
    const map = new Map<string, {
      key: string;
      modelName: string;
      codePrefix: string;
      category: string;
      color: string;
      unit_price: number;
      sizes: Record<number, number>;
      totalPairs: number;
      totalValuation: number;
    }>();

    for (const item of filteredItems) {
      const modelKey = `${item.name}__${item.category}__${item.color || ""}`;
      let row = map.get(modelKey);
      if (!row) {
        row = {
          key: modelKey,
          modelName: item.name,
          codePrefix: item.code.includes("-") ? item.code.split("-").slice(0, 2).join("-") : item.code,
          category: item.category || "-",
          color: item.color || "-",
          unit_price: item.unit_price || 0,
          sizes: {},
          totalPairs: 0,
          totalValuation: 0
        };
        map.set(modelKey, row);
      }
      const sz = Number(item.size);
      if (!isNaN(sz)) {
        row.sizes[sz] = (row.sizes[sz] || 0) + (item.current_stock_pairs || 0);
      }
      row.totalPairs += item.current_stock_pairs || 0;
      row.totalValuation += item.estimated_value || 0;
    }

    return Array.from(map.values());
  }, [filteredItems]);

  // Low stock count
  const lowStockItems = useMemo(() => {
    return stockItems.filter((item) => item.current_stock_pairs <= 50);
  }, [stockItems]);

  // Chart 1: Stock by Category
  const categoryChartData = useMemo(() => {
    const map = new Map<string, { pairs: number; value: number }>();
    for (const item of stockItems) {
      const cat = item.category || "Uncategorized";
      const current = map.get(cat) || { pairs: 0, value: 0 };
      current.pairs += item.current_stock_pairs || 0;
      current.value += item.estimated_value || 0;
      map.set(cat, current);
    }
    return Array.from(map.entries()).map(([name, data]) => ({
      name,
      pairs: data.pairs,
      valueK: Math.round(data.value / 1000)
    }));
  }, [stockItems]);

  // Chart 2: Size Breakdown with safe mobile label spacing
  const sizeChartData = useMemo(() => {
    const map = new Map<string, number>();
    for (const item of stockItems) {
      const sz = item.size ? `Sz ${item.size}` : "N/A";
      map.set(sz, (map.get(sz) || 0) + (item.current_stock_pairs || 0));
    }
    return Array.from(map.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([size, pairs]) => ({ size, pairs }));
  }, [stockItems]);

  // CSV Export
  const handleExportCSV = () => {
    if (!filteredItems.length) return;
    const headers = [
      "Product Code",
      "Model Name",
      "Category",
      "Size",
      "Color",
      "Unit Price (NPR)",
      "Stock in Hand (Pairs)",
      "Valuation (NPR)",
      "Inventory Status"
    ];
    const rows = filteredItems.map((item) => [
      item.code,
      item.name,
      item.category || "-",
      item.size || "-",
      item.color || "-",
      item.unit_price,
      item.current_stock_pairs,
      item.estimated_value,
      item.status
    ]);
    exportToCSV("Stock_Ledger_Valuation", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Summary KPI Header */}
      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
          <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #3b82f6" }}>
            <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>
              ACTIVE PRODUCT VARIANTS
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#f8fafc" }} className="num-mono-bold">
              {summary.total_products_count}{" "}
              <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: "400" }}>SKUs</span>
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>Across all shoe categories</div>
          </div>

          <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #10b981" }}>
            <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>
              TOTAL INVENTORY QUANTITY
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#10b981" }} className="num-mono-bold">
              {summary.total_stock_pairs.toLocaleString()}{" "}
              <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: "400" }}>pairs</span>
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>Verified append-only stock ledger</div>
          </div>

          <div className="glass-card" style={{ padding: "16px 18px", borderLeft: "3px solid #8b5cf6" }}>
            <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>
              TOTAL INVENTORY VALUATION
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: "#8b5cf6" }} className="num-mono-bold">
              Rs. {summary.total_stock_value.toLocaleString()}
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>Estimated wholesale market valuation</div>
          </div>

          <div className="glass-card" style={{ padding: "16px 18px", borderLeft: lowStockItems.length > 0 ? "3px solid #f59e0b" : "3px solid #10b981" }}>
            <div style={{ color: "#94a3b8", fontSize: "11px", fontWeight: "700", letterSpacing: "0.05em" }}>
              LOW-STOCK REORDER ALERTS
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", marginTop: "4px", color: lowStockItems.length > 0 ? "#fbbf24" : "#10b981" }} className="num-mono-bold">
              {lowStockItems.length}{" "}
              <span style={{ fontSize: "13px", color: "#94a3b8", fontWeight: "400" }}>SKUs</span>
            </div>
            <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px" }}>
              {lowStockItems.length > 0 ? "Under 50 pairs threshold" : "All SKUs comfortably stocked"}
            </div>
          </div>
        </div>
      )}

      {/* Visual Analytics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
        {/* Category Breakdown Bar Chart */}
        <div className="glass-card" style={{ padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <BarChart3 size={16} color="#3b82f6" />
              <span style={{ fontSize: "13px", fontWeight: "700", color: "#f8fafc", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Stock by Shoe Category
              </span>
            </div>
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>Total Pairs in Warehouse</span>
          </div>

          <div style={{ width: "100%", height: "200px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.15)", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(val: any) => [`${val} pairs`, "Quantity"]}
                />
                <Bar dataKey="pairs" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Size Distribution */}
        <div className="glass-card" style={{ padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="#10b981" />
              <span style={{ fontSize: "13px", fontWeight: "700", color: "#f8fafc", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Inventory Size Curve Distribution
              </span>
            </div>
            <span style={{ fontSize: "11px", color: "#94a3b8" }}>Size Curve (Paris Points)</span>
          </div>

          <div style={{ width: "100%", height: "200px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sizeChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="size" stroke="#94a3b8" fontSize={10} tickLine={false} interval="preserveStartEnd" />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: "#0f172a", borderColor: "rgba(255,255,255,0.15)", borderRadius: "4px", fontSize: "12px" }}
                  formatter={(val: any) => [`${val} pairs`, "In Stock"]}
                />
                <Bar dataKey="pairs" fill="#10b981" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Filter, Quick Search and View Mode Switcher */}
      <div className="glass-card" style={{ padding: "12px 16px", display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "220px", background: "#090d16", padding: "6px 10px", borderRadius: "4px", border: "1px solid #1e293b" }}>
          <Search size={15} color="#94a3b8" />
          <input
            type="text"
            placeholder="Search SKU, shoe model, color, or batch code..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ background: "none", border: "none", color: "#f8fafc", fontSize: "12.5px", outline: "none", width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {/* View Mode Toggle */}
          <div style={{ display: "inline-flex", background: "#090d16", padding: "2px", borderRadius: "4px", border: "1px solid #1e293b" }}>
            <button
              type="button"
              onClick={() => setViewMode("matrix")}
              style={{
                padding: "4px 10px",
                fontSize: "12px",
                fontWeight: "600",
                borderRadius: "3px",
                border: "none",
                cursor: "pointer",
                background: viewMode === "matrix" ? "#2563eb" : "transparent",
                color: viewMode === "matrix" ? "#ffffff" : "#94a3b8"
              }}
            >
              Sizing Matrix (32–43)
            </button>
            <button
              type="button"
              onClick={() => setViewMode("detailed")}
              style={{
                padding: "4px 10px",
                fontSize: "12px",
                fontWeight: "600",
                borderRadius: "3px",
                border: "none",
                cursor: "pointer",
                background: viewMode === "detailed" ? "#2563eb" : "transparent",
                color: viewMode === "detailed" ? "#ffffff" : "#94a3b8"
              }}
            >
              Detailed SKU Ledger
            </button>
          </div>

          {/* Category Filter */}
          <select
            className="input-field"
            style={{ width: "130px", padding: "5px 8px", fontSize: "12px", cursor: "pointer" }}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            <option value="all">All Categories</option>
            <option value="Boot">Boot</option>
            <option value="Shoe">Shoe</option>
            <option value="Slipper">Slipper</option>
            <option value="Sandal">Sandal</option>
          </select>

          {/* Status Filter */}
          <select
            className="input-field"
            style={{ width: "125px", padding: "5px 8px", fontSize: "12px", cursor: "pointer" }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Status</option>
            <option value="in_stock">In Stock (&gt;50)</option>
            <option value="low_stock">Low Stock (≤50)</option>
            <option value="out_of_stock">Depleted (0)</option>
          </select>

          {/* CSV Export Button */}
          <button onClick={handleExportCSV} className="btn-export" disabled={!filteredItems.length}>
            <Download size={13} /> Export CSV
          </button>
        </div>
      </div>

      {/* Main High-Density Stock Table */}
      <div className="glass-card" style={{ padding: "14px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Boxes size={16} color="#3b82f6" />
            <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#f8fafc" }}>
              {viewMode === "matrix"
                ? `Finished Footwear Sizing Matrix (${matrixRows.length} Product Models)`
                : `Warehouse Stock Ledger (${filteredItems.length} SKUs Listed)`}
            </h3>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", display: "flex", alignItems: "center", gap: "4px" }}>
            <Info size={11} /> Paris Points 32–43 • Append-only ledger math
          </div>
        </div>

        {loading ? (
          <div style={{ padding: "50px", textAlign: "center", color: "#94a3b8" }}>
            <RefreshCw size={22} className="animate-spin" style={{ margin: "0 auto 10px" }} />
            <div>Reconciling real-time inventory ledger...</div>
          </div>
        ) : filteredItems.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#94a3b8", fontSize: "13px" }}>
            No product inventory records match the selected filter criteria.
          </div>
        ) : viewMode === "matrix" ? (
          /* SIZING MATRIX GRID (Paris Points 32-43) */
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th className="sticky-col-left-1" style={{ width: "90px" }}>SKU</th>
                  <th className="sticky-col-left-2" style={{ minWidth: "160px" }}>Model Name</th>
                  <th style={{ width: "80px" }}>Category</th>
                  <th style={{ width: "80px" }}>Color</th>
                  {PARIS_POINTS.map((sz) => (
                    <th key={sz} style={{ width: "42px", textAlign: "center", background: "#0b1324" }}>
                      {sz}
                    </th>
                  ))}
                  <th style={{ textAlign: "right", width: "100px" }}>Rate</th>
                  <th style={{ textAlign: "right", width: "110px" }}>Total Pairs</th>
                  <th style={{ textAlign: "right", width: "120px" }}>Valuation</th>
                  <th style={{ width: "95px", textAlign: "center" }}>Health</th>
                </tr>
              </thead>
              <tbody>
                {matrixRows.map((row) => {
                  const isDepleted = row.totalPairs <= 0;
                  const isLow = row.totalPairs > 0 && row.totalPairs <= 50;
                  return (
                    <tr key={row.key}>
                      <td className="sticky-col-left-1 num-mono" style={{ fontWeight: "700", color: "#3b82f6" }}>
                        {row.codePrefix}
                      </td>
                      <td className="sticky-col-left-2" style={{ fontWeight: "600", color: "#f8fafc" }}>
                        {row.modelName}
                      </td>
                      <td>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>{row.category}</span>
                      </td>
                      <td style={{ color: "#94a3b8", fontSize: "11px" }}>{row.color}</td>
                      {PARIS_POINTS.map((sz) => {
                        const count = row.sizes[sz] || 0;
                        return (
                          <td
                            key={sz}
                            className={`matrix-cell ${count > 0 ? "has-stock" : "zero-stock"}`}
                          >
                            {count > 0 ? count : "-"}
                          </td>
                        );
                      })}
                      <td style={{ textAlign: "right" }} className="num-mono">
                        Rs. {row.unit_price?.toLocaleString()}
                      </td>
                      <td
                        style={{
                          textAlign: "right",
                          fontWeight: "700",
                          color: isDepleted ? "#f43f5e" : isLow ? "#fbbf24" : "#10b981"
                        }}
                        className="num-mono-bold"
                      >
                        {row.totalPairs.toLocaleString()}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "600" }} className="num-mono">
                        Rs. {row.totalValuation.toLocaleString()}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {isDepleted ? (
                          <span className="badge badge-danger">Out</span>
                        ) : isLow ? (
                          <span className="badge badge-warning">Low</span>
                        ) : (
                          <span className="badge badge-success">OK</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          /* DETAILED SKU LEDGER */
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th style={{ width: "100px" }}>SKU Code</th>
                  <th>Footwear Description</th>
                  <th style={{ width: "90px" }}>Category</th>
                  <th style={{ width: "60px", textAlign: "center" }}>Size</th>
                  <th style={{ width: "90px" }}>Color</th>
                  <th style={{ textAlign: "right", width: "110px" }}>Unit Price</th>
                  <th style={{ textAlign: "right", width: "120px" }}>Current Stock</th>
                  <th style={{ textAlign: "right", width: "130px" }}>Valuation</th>
                  <th style={{ width: "110px", textAlign: "center" }}>Stock Health</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isLow = item.current_stock_pairs > 0 && item.current_stock_pairs <= 50;
                  const isDepleted = item.current_stock_pairs <= 0;
                  return (
                    <tr key={item.product_id}>
                      <td style={{ fontWeight: "700", color: "#3b82f6" }} className="num-mono">
                        {item.code}
                      </td>
                      <td style={{ fontWeight: "600" }}>{item.name}</td>
                      <td>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>{item.category || "-"}</span>
                      </td>
                      <td style={{ textAlign: "center" }} className="num-mono">
                        {item.size || "-"}
                      </td>
                      <td style={{ color: "#94a3b8", fontSize: "11px" }}>{item.color || "-"}</td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        Rs. {item.unit_price?.toLocaleString()}
                      </td>
                      <td
                        style={{
                          textAlign: "right",
                          fontWeight: "700",
                          color: isDepleted ? "#f43f5e" : isLow ? "#fbbf24" : "#10b981"
                        }}
                        className="num-mono-bold"
                      >
                        {item.current_stock_pairs?.toLocaleString()} {t("pairs")}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "600" }} className="num-mono">
                        Rs. {item.estimated_value?.toLocaleString()}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {isDepleted ? (
                          <span className="badge badge-danger">{t("out_of_stock")}</span>
                        ) : isLow ? (
                          <span className="badge badge-low-stock">
                            <AlertTriangle size={11} style={{ marginRight: "3px" }} /> {t("low_stock")}
                          </span>
                        ) : (
                          <span className="badge badge-success">
                            <CheckCircle size={11} style={{ marginRight: "3px" }} /> {t("healthy")}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
