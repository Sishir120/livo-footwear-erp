"use client";

import React, { useState, useEffect } from "react";
import {
  Trophy,
  Award,
  Medal,
  Users,
  ShoppingBag,
  Download,
  RefreshCw,
  Search,
  Filter,
  DollarSign,
  TrendingUp,
  CreditCard,
  CheckCircle2,
  AlertTriangle
} from "lucide-react";
import { fromPaisa, TABULAR_NUMS_STYLE } from "@/lib/currency";
import { useLocale } from "@/context/LocaleContext";
import { ProductionAnalyticsView } from "./ProductionAnalyticsView";

interface TopProduct {
  rank: number;
  product_id: number;
  code: string;
  name: string;
  category: string | null;
  total_pairs_sold: number;
  total_revenue_paisa: number;
  order_count: number;
}

interface TopCustomer {
  serial_no: number;
  client_id: number;
  client_code: string;
  name: string;
  pan_number: string | null;
  total_orders: number;
  total_pairs: number;
  total_revenue_paisa: number;
  total_received_paisa: number;
  outstanding_receivable_paisa: number;
  reliability_score: number;
}

interface LeaderboardsViewProps {
  userRole?: string;
}

export function LeaderboardsView({ userRole }: LeaderboardsViewProps) {
  const { isNepali, t } = useLocale();

  const [activeTab, setActiveTab] = useState<"products" | "customers" | "ratios">("products");
  const [loading, setLoading] = useState(true);
  const [topProducts, setTopProducts] = useState<TopProduct[]>([]);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [prodRes, custRes] = await Promise.all([
        fetch("/api/v1/analytics/top-products"),
        fetch("/api/v1/analytics/top-customers")
      ]);

      if (prodRes.ok) {
        const prodData = await prodRes.json();
        setTopProducts(prodData);
      }
      if (custRes.ok) {
        const custData = await custRes.json();
        setTopCustomers(custData);
      }
    } catch (e) {
      console.error("Failed to fetch leaderboard data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filtered Products
  const filteredProducts = topProducts.filter((p) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      p.code.toLowerCase().includes(term) ||
      p.name.toLowerCase().includes(term) ||
      (p.category && p.category.toLowerCase().includes(term))
    );
  });

  // Filtered Customers
  const filteredCustomers = topCustomers.filter((c) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      c.client_code.toLowerCase().includes(term) ||
      c.name.toLowerCase().includes(term) ||
      (c.pan_number && c.pan_number.toLowerCase().includes(term))
    );
  });

  // Export CSV for Products
  const handleExportProductsCSV = () => {
    if (!filteredProducts.length) return;
    const headers = ["Rank", "SKU Code", "Product Name", "Category", "Pairs Sold", "Total Revenue NPR", "Order Count"];
    const rows = filteredProducts.map((p) => [
      p.rank,
      `"${p.code}"`,
      `"${p.name}"`,
      `"${p.category || ""}"`,
      p.total_pairs_sold,
      fromPaisa(p.total_revenue_paisa, false),
      p.order_count
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Top_Selling_Products_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export CSV for Customers
  const handleExportCustomersCSV = () => {
    if (!filteredCustomers.length) return;
    const headers = [
      "Serial No",
      "Client Code",
      "Client Name",
      "PAN / Contact",
      "Total Orders",
      "Pairs Bought",
      "Total Invoiced NPR",
      "Cash Received NPR",
      "Outstanding NPR",
      "Reliability %"
    ];
    const rows = filteredCustomers.map((c) => [
      c.serial_no,
      `"${c.client_code}"`,
      `"${c.name}"`,
      `"${c.pan_number || ""}"`,
      c.total_orders,
      c.total_pairs,
      fromPaisa(c.total_revenue_paisa, false),
      fromPaisa(c.total_received_paisa, false),
      fromPaisa(c.outstanding_receivable_paisa, false),
      c.reliability_score
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Top_Customer_Rankings_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Rank badge styling helper
  const getRankBadge = (rank: number) => {
    if (rank === 1) {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "#FEF3C7", color: "#92400E", padding: "3px 8px", borderRadius: "12px", fontWeight: "700", fontSize: "11px" }}>
          <Trophy size={13} color="#D97706" /> #1 GOLD
        </span>
      );
    }
    if (rank === 2) {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "#F1F5F9", color: "#475569", padding: "3px 8px", borderRadius: "12px", fontWeight: "700", fontSize: "11px" }}>
          <Medal size={13} color="#64748B" /> #2 SILVER
        </span>
      );
    }
    if (rank === 3) {
      return (
        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", background: "#FFEDD5", color: "#9A3412", padding: "3px 8px", borderRadius: "12px", fontWeight: "700", fontSize: "11px" }}>
          <Award size={13} color="#C2410C" /> #3 BRONZE
        </span>
      );
    }
    return (
      <span style={{ fontWeight: "700", color: "#64748B", ...TABULAR_NUMS_STYLE, padding: "3px 8px" }}>
        #{rank}
      </span>
    );
  };

  return (
    <div style={{ padding: "24px 32px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
              {t("leaderboards_title")}
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#FEF3C7",
                color: "#B45309",
                padding: "2px 8px",
                borderRadius: "3px"
              }}
            >
              {isNepali ? "बिक्री तथा ग्राहक वरीयता" : "SALES PERFORMANCE LEADERBOARDS"}
            </span>
          </div>
          <p style={{ fontSize: "12.5px", color: "#475569", marginTop: "4px", margin: 0 }}>
            {t("leaderboards_desc")}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={fetchData}
            disabled={loading}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{isNepali ? "ताजा गर्नुहोस्" : "Refresh"}</span>
          </button>

          <button
            onClick={activeTab === "products" ? handleExportProductsCSV : handleExportCustomersCSV}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Download size={13} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Primary Sub-Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #CBD5E1", marginBottom: "20px", gap: "4px" }}>
        <button
          onClick={() => {
            setActiveTab("products");
            setSearchTerm("");
          }}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeTab === "products" ? "2px solid #1E3A8A" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "products" ? "#1E3A8A" : "#64748B",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <ShoppingBag size={16} />
          <span>{t("top_products_tab")}</span>
          <span style={{ fontSize: "11px", background: activeTab === "products" ? "#DBEAFE" : "#E2E8F0", padding: "1px 6px", borderRadius: "10px" }}>
            {topProducts.length}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab("customers");
            setSearchTerm("");
          }}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeTab === "customers" ? "2px solid #1E3A8A" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "customers" ? "#1E3A8A" : "#64748B",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <Users size={16} />
          <span>{t("top_customers_tab")}</span>
          <span style={{ fontSize: "11px", background: activeTab === "customers" ? "#DBEAFE" : "#E2E8F0", padding: "1px 6px", borderRadius: "10px" }}>
            {topCustomers.length}
          </span>
        </button>

        <button
          onClick={() => {
            setActiveTab("ratios");
            setSearchTerm("");
          }}
          style={{
            padding: "10px 18px",
            fontSize: "13px",
            fontWeight: "700",
            border: "none",
            borderBottom: activeTab === "ratios" ? "2px solid #1E3A8A" : "2px solid transparent",
            background: "transparent",
            color: activeTab === "ratios" ? "#1E3A8A" : "#64748B",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <TrendingUp size={16} />
          <span>{t("production_ratios_tab")}</span>
        </button>
      </div>

      {/* Search Input Bar (only for product/customer tables) */}
      {activeTab !== "ratios" && (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", padding: "12px 16px", marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: "13px", fontWeight: "600", color: "#334155" }}>
            {activeTab === "products"
              ? (isNepali ? "सबैभन्दा धेरै बिक्री भएका जुत्ता मोडलहरू:" : "Ranked Best-Selling Footwear SKUs:")
              : (isNepali ? "उच्च कारोबार तथा अर्डर गर्ने थोक ग्राहकहरू:" : "Serial Ranking of High-Volume Wholesale Buyers:")}
          </div>

        <div style={{ position: "relative", minWidth: "260px" }}>
          <Search size={14} color="#94A3B8" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            placeholder={activeTab === "products" ? "Search product code or name..." : "Search client name or code..."}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 10px 6px 32px",
              fontSize: "12.5px",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              outline: "none",
              color: "#0F172A"
            }}
          />
        </div>
      </div>
      )}

      {/* TAB A: TOP SELLING PRODUCTS */}
      {activeTab === "products" && (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px 14px", fontWeight: "600", width: "130px" }}>{t("rank_no")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>SKU Code</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>Product Name</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>Category</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("pairs_sold")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("revenue")} (NPR)</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("orders_count")}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: "30px", textAlign: "center", color: "#64748B" }}>
                    <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                    <div>Loading top products ranking...</div>
                  </td>
                </tr>
              ) : filteredProducts.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
                    <ShoppingBag size={32} style={{ margin: "0 auto 8px", opacity: 0.5 }} />
                    <div>No product sales records logged yet</div>
                  </td>
                </tr>
              ) : (
                filteredProducts.map((prod) => (
                  <tr key={prod.product_id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={{ padding: "10px 14px" }}>
                      {getRankBadge(prod.rank)}
                    </td>
                    <td style={{ padding: "10px 14px", fontWeight: "700", color: "#1E3A8A", ...TABULAR_NUMS_STYLE }}>
                      {prod.code}
                    </td>
                    <td style={{ padding: "10px 14px", fontWeight: "600", color: "#0F172A" }}>
                      {prod.name}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "600", background: "#F1F5F9", color: "#475569", padding: "2px 7px", borderRadius: "3px" }}>
                        {prod.category || "Unassigned"}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                      {prod.total_pairs_sold.toLocaleString()} <span style={{ fontSize: "11px", fontWeight: "400", color: "#64748B" }}>pairs</span>
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "700", color: "#047857", ...TABULAR_NUMS_STYLE }}>
                      NPR {fromPaisa(prod.total_revenue_paisa)}
                    </td>
                    <td style={{ padding: "10px 14px", textAlign: "right", color: "#475569", ...TABULAR_NUMS_STYLE }}>
                      {prod.order_count}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB B: TOP CUSTOMERS RANKING */}
      {activeTab === "customers" && (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px 14px", fontWeight: "600", width: "90px" }}>{t("serial_no")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>Client Code</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>Buyer / Company Name</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>PAN / Contact</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Total Orders</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Pairs Bought</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Total Revenue</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Received</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Due Balance</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "center" }}>{t("reliability_rate")}</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={10} style={{ padding: "30px", textAlign: "center", color: "#64748B" }}>
                    <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                    <div>Loading customer rankings...</div>
                  </td>
                </tr>
              ) : filteredCustomers.length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
                    <Users size={32} style={{ margin: "0 auto 8px", opacity: 0.5 }} />
                    <div>No wholesale customer accounts recorded</div>
                  </td>
                </tr>
              ) : (
                filteredCustomers.map((cust) => {
                  const relColor = cust.reliability_score >= 90 ? "#15803D" : (cust.reliability_score >= 70 ? "#B45309" : "#DC2626");
                  const relBg = cust.reliability_score >= 90 ? "#DCFCE7" : (cust.reliability_score >= 70 ? "#FEF3C7" : "#FEE2E2");

                  return (
                    <tr key={cust.client_id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                      <td style={{ padding: "10px 14px", fontWeight: "700", color: "#1E3A8A", ...TABULAR_NUMS_STYLE }}>
                        #{cust.serial_no}
                      </td>
                      <td style={{ padding: "10px 14px", fontWeight: "600", color: "#475569", ...TABULAR_NUMS_STYLE }}>
                        {cust.client_code}
                      </td>
                      <td style={{ padding: "10px 14px", fontWeight: "600", color: "#0F172A" }}>
                        {cust.name}
                      </td>
                      <td style={{ padding: "10px 14px", color: "#64748B" }}>
                        {cust.pan_number || "-"}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                        {cust.total_orders}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "600", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                        {cust.total_pairs.toLocaleString()}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                        NPR {fromPaisa(cust.total_revenue_paisa)}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right", color: "#059669", ...TABULAR_NUMS_STYLE }}>
                        NPR {fromPaisa(cust.total_received_paisa)}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>
                        {cust.outstanding_receivable_paisa > 0 ? (
                          <span style={{ color: "#DC2626", fontWeight: "600" }}>
                            NPR {fromPaisa(cust.outstanding_receivable_paisa)}
                          </span>
                        ) : (
                          <span style={{ color: "#64748B" }}>0.00</span>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "center" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: "700",
                            padding: "2px 8px",
                            borderRadius: "10px",
                            background: relBg,
                            color: relColor,
                            ...TABULAR_NUMS_STYLE
                          }}
                        >
                          {cust.reliability_score.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* TAB C: PRODUCTION & WORKER RATIOS */}
      {activeTab === "ratios" && (
        <ProductionAnalyticsView userRole={userRole} />
      )}
    </div>
  );
}
