"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Factory,
  CheckCircle2,
  Search,
  Download,
  X,
  Printer,
  ChevronRight,
  Keyboard,
  Layers,
  AlertCircle
} from "lucide-react";
import { exportToCSV } from "../utils/csvExport";
import { ThermalLabelModal, BoxLabelData } from "./ThermalLabelModal";
import { apiFetch } from "../lib/api";

const SIZES = [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43] as const;

export function ProductionView({ userRole }: { userRole?: string }) {
  const [products, setProducts] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [productFilter, setProductFilter] = useState("all");

  // Docked Continuous Batch Entry State
  const [batchSeq, setBatchSeq] = useState<number>(() => {
    return Math.floor(1000 + Math.random() * 9000);
  });
  const [batchPrefix, setBatchPrefix] = useState("BATCH");
  const [selectedModelKey, setSelectedModelKey] = useState<string>("");
  const [productionLine, setProductionLine] = useState("Line 1 (मुख्य एसेम्बली)");
  const [productionShift, setProductionShift] = useState("Shift 1 (बिहानी 06:00 - 14:00)");
  const [workerCount, setWorkerCount] = useState("4");
  const [dateAd, setDateAd] = useState(new Date().toISOString().split("T")[0]);
  const [dateBs, setDateBs] = useState("2083-06-09");
  
  // Horizontal size quantities map: size -> quantity string (default "0")
  const [sizeQuantities, setSizeQuantities] = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {};
    SIZES.forEach((s) => { init[s] = "0"; });
    return init;
  });

  const [submitting, setSubmitting] = useState(false);
  const [successFeedback, setSuccessFeedback] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [showLabelModal, setShowLabelModal] = useState(false);
  const [currentLabelData, setCurrentLabelData] = useState<BoxLabelData>({
    productName: "LIVO FOOTWEAR",
    sku: "",
    size: "41",
    batchNumber: "",
  });

  // Sequential Refs for keyboard cycling across sizes 32 through 43
  const sizeInputRefs = useRef<{ [key: number]: HTMLInputElement | null }>({});
  const modelSelectRef = useRef<HTMLSelectElement>(null);
  const workerInputRef = useRef<HTMLInputElement>(null);

  // Deterministic focus on initial view mount -> Auto-focus Size 32 with text auto-selected
  useEffect(() => {
    if (userRole === "editor") {
      const timer = setTimeout(() => {
        const el = sizeInputRefs.current[32];
        if (el) {
          el.focus();
          el.select();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [userRole]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prodRes, batchRes] = await Promise.all([
        fetch("/api/v1/production/products"),
        fetch("/api/v1/production/batches")
      ]);
      if (prodRes.ok) {
        const prodData = await prodRes.json();
        setProducts(prodData);
        if (prodData.length > 0 && !selectedModelKey) {
          // Select first available footwear model
          const first = prodData[0];
          setSelectedModelKey(`${first.name}__${first.color || "Standard"}`);
        }
      }
      if (batchRes.ok) setBatches(await batchRes.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Group products by base model (name + color) to resolve sizes 32-43
  const modelGroups = useMemo(() => {
    const map = new Map<string, {
      key: string;
      name: string;
      codePrefix: string;
      color: string;
      productsBySize: Record<string, any>;
    }>();

    for (const p of products) {
      const key = `${p.name}__${p.color || "Standard"}`;
      let g = map.get(key);
      if (!g) {
        g = {
          key,
          name: p.name,
          codePrefix: p.code ? p.code.split("-")[0] : "SHOE",
          color: p.color || "Standard",
          productsBySize: {}
        };
        map.set(key, g);
      }
      if (p.size) {
        g.productsBySize[String(p.size)] = p;
      }
    }
    return Array.from(map.values());
  }, [products]);

  // Current selected group
  const activeGroup = useMemo(() => {
    return modelGroups.find((g) => g.key === selectedModelKey) || modelGroups[0] || null;
  }, [modelGroups, selectedModelKey]);

  // Whole-pairs-only validation: every non-empty size string must be purely non-negative digits /^\d+$/
  const hasInvalidSizeInput = useMemo(() => {
    return SIZES.some((sz) => {
      const raw = sizeQuantities[sz];
      if (!raw || raw === "" || raw === "0") return false;
      return !/^\d+$/.test(raw.trim());
    });
  }, [sizeQuantities]);

  // Calculate total batch pairs entered across the unbroken horizontal row
  const totalBatchPairs = useMemo(() => {
    return SIZES.reduce((sum, sz) => {
      const raw = sizeQuantities[sz];
      if (!raw || !/^\d+$/.test(raw.trim())) return sum;
      const q = parseInt(raw.trim(), 10);
      return sum + (isNaN(q) ? 0 : q);
    }, 0);
  }, [sizeQuantities]);

  const getProduct = (id: number) => {
    return products.find((p) => p.id === id);
  };

  // Client-Side Input Sanitization & Focus/Blur Handlers
  const handleSizeChange = (sz: number, val: string) => {
    setSizeQuantities((prev) => ({ ...prev, [sz]: val }));
  };

  const handleSizeFocus = (sz: number, e: React.FocusEvent<HTMLInputElement>) => {
    // Clear on focus for quick overwrite if currently "0"
    if (sizeQuantities[sz] === "0" || sizeQuantities[sz] === "") {
      setSizeQuantities((prev) => ({ ...prev, [sz]: "" }));
    }
    e.target.select();
  };

  const handleSizeBlur = (sz: number) => {
    // Render empty or non-digit fields as 0 on blur
    const raw = sizeQuantities[sz];
    if (!raw || raw.trim() === "" || !/^\d+$/.test(raw.trim())) {
      setSizeQuantities((prev) => ({ ...prev, [sz]: "0" }));
    }
  };

  // Traversal across horizontal size inputs:
  // Tab or Enter cycles 32 -> 43; Shift+Tab moves backward 43 -> 32; Ctrl+Enter commits
  const handleSizeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, currentSize: number) => {
    // 1. Immediate Batch Submission from any field on Ctrl+Enter or Cmd+Enter
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleCommitBatch();
      return;
    }

    // 2. Block keystrokes for '-', '.', scientific notation 'e'/'E', and '+'
    if (["-", ".", "e", "E", "+"].includes(e.key)) {
      e.preventDefault();
      return;
    }

    const currentIndex = SIZES.indexOf(currentSize as any);

    // 3. Shift+Tab: move focus backward (43 -> 42 -> ... -> 32) and auto-select
    if (e.key === "Tab" && e.shiftKey) {
      if (currentIndex > 0) {
        e.preventDefault();
        const prevSize = SIZES[currentIndex - 1];
        const el = sizeInputRefs.current[prevSize];
        el?.focus();
        el?.select();
      }
      return;
    }

    // 4. Tab or Enter (without Ctrl): validate, auto-select next input, move forward (32 -> 33 -> ... -> 43)
    if ((e.key === "Tab" && !e.shiftKey) || e.key === "Enter") {
      if (currentIndex >= 0 && currentIndex < SIZES.length - 1) {
        e.preventDefault();
        const nextSize = SIZES[currentIndex + 1];
        const el = sizeInputRefs.current[nextSize];
        el?.focus();
        el?.select();
      } else if (e.key === "Enter" && currentIndex === SIZES.length - 1) {
        // Last size (43) + Enter triggers batch submission
        e.preventDefault();
        handleCommitBatch();
      }
      return;
    }
  };

  const handleGlobalCtrlEnter = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleCommitBatch();
    }
  };

  // Commit Batch & Cycle
  const handleCommitBatch = async () => {
    if (userRole !== "editor" || submitting) return;

    if (hasInvalidSizeInput) {
      setErrorMessage("कृपया पूर्ण जोर संख्या मात्र राख्नुहोस् (Whole pairs only)");
      return;
    }

    // Check if at least one size has quantity > 0
    const activeEntries = SIZES.map((sz) => {
      const raw = sizeQuantities[sz];
      const q = raw && /^\d+$/.test(raw.trim()) ? parseInt(raw.trim(), 10) : 0;
      return { size: sz, qty: q };
    }).filter((item) => item.qty > 0);

    if (activeEntries.length === 0) {
      setErrorMessage("Enter pairs in at least one size column before committing.");
      setTimeout(() => setErrorMessage(""), 3500);
      return;
    }

    if (!activeGroup) {
      setErrorMessage("Select a footwear model before committing batch.");
      return;
    }

    setSubmitting(true);
    setErrorMessage("");

    try {
      const currentBatchNumber = `${batchPrefix}-${batchSeq}`;
      let createdCount = 0;
      let lastProductId: number | null = null;
      let lastSizeStr = "41";

      for (const item of activeEntries) {
        let matchedProduct = activeGroup.productsBySize[String(item.size)];

        // If product SKU for this size does not exist yet, create it on-demand
        if (!matchedProduct) {
          const skuCode = `${activeGroup.codePrefix}-${item.size}`;
          const createRes = await apiFetch("/api/v1/production/products", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              code: skuCode,
              name: activeGroup.name,
              category: "Shoe",
              size: String(item.size),
              color: activeGroup.color,
              unit_price: 3200.0
            })
          });

          if (createRes.ok) {
            matchedProduct = await createRes.json();
            // Update local state cache
            setProducts((prev) => [...prev, matchedProduct]);
          } else {
            // Fallback: pick any existing product from group
            matchedProduct = Object.values(activeGroup.productsBySize)[0];
          }
        }

        if (matchedProduct) {
          const specificBatchNumber = activeEntries.length === 1 
            ? currentBatchNumber 
            : `${currentBatchNumber}-${item.size}`;

          const res = await apiFetch("/api/v1/production/batches", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              batch_number: specificBatchNumber,
              product_id: matchedProduct.id,
              target_quantity: item.qty,
              produced_quantity: item.qty,
              worker_count: parseInt(workerCount) || 1,
              date_ad: dateAd,
              date_bs: dateBs,
              notes: `Line: ${productionLine} | Shift: ${productionShift} | Workers: ${workerCount}`
            })
          });

          if (res.ok) {
            createdCount++;
            lastProductId = matchedProduct.id;
            lastSizeStr = String(item.size);
          } else {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Failed to record size ${item.size}`);
          }
        }
      }

      // Ephemeral 2-second confirmation: "ब्याच सुरक्षित भयो (Batch BATCH-XXXX Recorded)"
      setSuccessFeedback(`ब्याच सुरक्षित भयो (Batch ${currentBatchNumber} Recorded)`);
      setTimeout(() => setSuccessFeedback(""), 2000);

      // Setup thermal label data for the committed batch
      if (lastProductId) {
        const prod = getProduct(lastProductId) || Object.values(activeGroup.productsBySize)[0];
        setCurrentLabelData({
          productName: prod?.name || activeGroup.name,
          sku: prod?.code || currentBatchNumber,
          size: lastSizeStr,
          color: prod?.color || activeGroup.color,
          batchNumber: currentBatchNumber,
          dateStr: dateAd,
        });
      }

      // Automatically increment sequence number and clear ONLY the 12 size quantity inputs
      // Model, Line, Shift, Workers, Date are preserved intact!
      setBatchSeq((prev) => prev + 1);
      const resetMap: Record<number, string> = {};
      SIZES.forEach((s) => { resetMap[s] = "0"; });
      setSizeQuantities(resetMap);

      // Programmatically return focus to Size 32 with text auto-selected, ready for next entry
      setTimeout(() => {
        const el = sizeInputRefs.current[32];
        if (el) {
          el.focus();
          el.select();
        }
      }, 50);

      loadData();
    } catch (e: any) {
      // Preserve all entered numbers intact, display exact server error message with retry shortcut
      const errMsg = e?.message || "Error saving production batch";
      setErrorMessage(`${errMsg} — पुनः प्रयास गर्न Ctrl+Enter थिच्नुहोस् (Press Ctrl+Enter to retry)`);
    } finally {
      setSubmitting(false);
    }
  };

  // Filtered Batches
  const filteredBatches = useMemo(() => {
    return batches.filter((b) => {
      const p = getProduct(b.product_id);
      const prodName = p ? `${p.name} ${p.code}`.toLowerCase() : "";
      const q = searchQuery.toLowerCase();

      const matchesSearch =
        b.batch_number.toLowerCase().includes(q) ||
        prodName.includes(q) ||
        b.date_ad.includes(q) ||
        b.date_bs.includes(q);

      const matchesProduct =
        productFilter === "all" || String(b.product_id) === productFilter;

      return matchesSearch && matchesProduct;
    });
  }, [batches, products, searchQuery, productFilter]);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 12;
  const totalPages = Math.ceil(filteredBatches.length / ITEMS_PER_PAGE) || 1;

  const paginatedBatches = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredBatches.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredBatches, currentPage]);

  // CSV Exporter
  const handleExportCSV = () => {
    if (!filteredBatches.length) return;
    const headers = [
      "Batch Number",
      "Date AD",
      "Date BS",
      "Product SKU",
      "Product Name",
      "Size",
      "Color",
      "Target Pairs",
      "Produced Pairs",
      "Active Workers",
      "Status",
      "Stock Inward Movement"
    ];
    const rows = filteredBatches.map((b) => {
      const p = getProduct(b.product_id);
      return [
        b.batch_number,
        b.date_ad,
        b.date_bs,
        p?.code || `ID #${b.product_id}`,
        p?.name || "Product",
        p?.size || "-",
        p?.color || "-",
        b.target_quantity,
        b.produced_quantity,
        b.worker_count,
        b.status,
        `+${b.produced_quantity} pairs`
      ];
    });
    exportToCSV("Production_Batches_Ledger", headers, rows);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }} onKeyDown={handleGlobalCtrlEnter}>
      {/* Title & Status Strip */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0, letterSpacing: "-0.01em" }}>
            Production Batches → Stock Ledger
          </h2>
          <div style={{ fontSize: "12px", color: "#475569", marginTop: "2px" }}>
            Real-time continuous size-break entry. Output auto-appends to finished stock movements.
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "11px", fontWeight: "600", color: "#475569", background: "#FFFFFF", border: "1px solid #CBD5E1", padding: "4px 8px", borderRadius: "3px" }}>
            <kbd style={{ fontFamily: "inherit", fontWeight: "700", color: "#1E3A8A" }}>Tab / Enter</kbd> Traverse Sizes
          </span>
          <span style={{ fontSize: "11px", fontWeight: "600", color: "#475569", background: "#FFFFFF", border: "1px solid #CBD5E1", padding: "4px 8px", borderRadius: "3px" }}>
            <kbd style={{ fontFamily: "inherit", fontWeight: "700", color: "#1E3A8A" }}>Ctrl+Enter</kbd> Commit Batch
          </span>
        </div>
      </div>

      {/* DOCKED CONTINUOUS BATCH ENTRY PANEL (High-Contrast Industrial Ergonomics) */}
      {userRole === "editor" && (
        <div
          style={{
            background: "#FFFFFF",
            border: "2px solid #1E3A8A",
            borderRadius: "4px",
            padding: "14px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "12px"
          }}
        >
          {/* Header Metadata Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", borderBottom: "1px solid #E2E8F0", paddingBottom: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Factory size={16} color="#1E3A8A" />
                <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", color: "#1E3A8A", letterSpacing: "0.04em" }}>
                  Continuous Batch Entry
                </span>
              </div>

              {/* Batch Sequence Display & Prefix */}
              <div style={{ display: "flex", alignItems: "center", gap: "4px", background: "#F8FAFC", border: "1px solid #CBD5E1", borderRadius: "3px", padding: "2px 8px" }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "#475569" }}>BATCH:</span>
                <input
                  type="text"
                  value={batchPrefix}
                  onChange={(e) => setBatchPrefix(e.target.value.toUpperCase())}
                  style={{ width: "55px", border: "none", background: "none", fontSize: "12px", fontWeight: "700", color: "#0F172A", fontFamily: "monospace", outline: "none" }}
                  title="Batch Prefix"
                />
                <span style={{ color: "#94A3B8" }}>-</span>
                <input
                  type="number"
                  value={batchSeq}
                  onChange={(e) => setBatchSeq(parseInt(e.target.value) || 0)}
                  style={{ width: "65px", border: "none", background: "none", fontSize: "12px", fontWeight: "700", color: "#1E3A8A", fontFamily: "monospace", outline: "none" }}
                  title="Batch Sequence Number"
                />
              </div>

              {/* Footwear Model Dropdown */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <label style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>Model:</label>
                <select
                  ref={modelSelectRef}
                  value={selectedModelKey}
                  onChange={(e) => setSelectedModelKey(e.target.value)}
                  onKeyDown={handleGlobalCtrlEnter}
                  style={{
                    background: "#FFFFFF",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    padding: "4px 8px",
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "#0F172A",
                    minWidth: "190px",
                    cursor: "pointer"
                  }}
                >
                  {modelGroups.map((g) => (
                    <option key={g.key} value={g.key}>
                      {g.codePrefix} — {g.name} ({g.color})
                    </option>
                  ))}
                </select>
              </div>

              {/* Assembly Line Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <label style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>Line:</label>
                <select
                  value={productionLine}
                  onChange={(e) => setProductionLine(e.target.value)}
                  onKeyDown={handleGlobalCtrlEnter}
                  style={{
                    background: "#FFFFFF",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    padding: "4px 6px",
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "#0F172A",
                    cursor: "pointer"
                  }}
                >
                  <option value="Line 1">Line 1 (मुख्य)</option>
                  <option value="Line 2">Line 2 (दोस्रो)</option>
                  <option value="Line 3">Line 3 (सोल)</option>
                </select>
              </div>

              {/* Shift Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <label style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>Shift:</label>
                <select
                  value={productionShift}
                  onChange={(e) => setProductionShift(e.target.value)}
                  onKeyDown={handleGlobalCtrlEnter}
                  style={{
                    background: "#FFFFFF",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    padding: "4px 6px",
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "#0F172A",
                    cursor: "pointer"
                  }}
                >
                  <option value="Shift 1">Shift 1 (बिहानी)</option>
                  <option value="Shift 2">Shift 2 (दिउँसो)</option>
                  <option value="Shift 3">Shift 3 (रात्री)</option>
                </select>
              </div>

              {/* Workers Count */}
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <label style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>Workers:</label>
                <input
                  ref={workerInputRef}
                  type="number"
                  value={workerCount}
                  onChange={(e) => setWorkerCount(e.target.value)}
                  onKeyDown={handleGlobalCtrlEnter}
                  style={{
                    width: "48px",
                    background: "#FFFFFF",
                    border: "1px solid #CBD5E1",
                    borderRadius: "3px",
                    padding: "4px 6px",
                    fontSize: "12px",
                    fontWeight: "600",
                    color: "#0F172A",
                    textAlign: "center"
                  }}
                  min="1"
                />
              </div>
            </div>

            {/* Date Display */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "#475569" }}>
              <span>AD: <strong style={{ color: "#0F172A" }}>{dateAd}</strong></span>
              <span>•</span>
              <span>BS: <strong style={{ color: "#0F172A" }}>{dateBs}</strong></span>
            </div>
          </div>

          {/* Feedback & Error messages */}
          {successFeedback && (
            <div role="status" style={{ background: "#ECFDF5", border: "1px solid #10B981", borderRadius: "3px", padding: "6px 12px", color: "#065F46", fontSize: "12px", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}>
              <CheckCircle2 size={14} color="#059669" />
              <span>{successFeedback}</span>
            </div>
          )}

          {errorMessage && (
            <div role="alert" style={{ background: "#FEF2F2", border: "1px solid #EF4444", borderRadius: "3px", padding: "6px 12px", color: "#991B1B", fontSize: "12px", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}>
              <AlertCircle size={14} color="#DC2626" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Whole Pairs Error Hint if operator pasted non-integers */}
          {hasInvalidSizeInput && (
            <div role="alert" style={{ background: "#FEF2F2", border: "1px solid #EF4444", borderRadius: "3px", padding: "6px 12px", color: "#991B1B", fontSize: "12px", fontWeight: "600", display: "flex", alignItems: "center", gap: "6px" }}>
              <AlertCircle size={14} color="#DC2626" />
              <span>कृपया पूर्ण जोर संख्या मात्र राख्नुहोस् (Whole pairs only)</span>
            </div>
          )}

          {/* UNBROKEN HORIZONTAL SIZE ENTRY ROW (Sizes 32 through 43) */}
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", border: "1px solid #CBD5E1" }}>
              <thead>
                <tr style={{ background: "#F1F5F9", height: "30px" }}>
                  <th style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontSize: "11px", fontWeight: "700", color: "#475569", width: "150px", textAlign: "left" }}>
                    जुत्ता साइज (Sizes 32–43)
                  </th>
                  {SIZES.map((sz) => (
                    <th key={sz} style={{ border: "1px solid #CBD5E1", padding: "4px 2px", fontSize: "12px", fontWeight: "700", color: "#0F172A", textAlign: "center", minWidth: "48px" }}>
                      {sz}
                    </th>
                  ))}
                  <th style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontSize: "11px", fontWeight: "700", color: "#1E3A8A", width: "110px", textAlign: "right" }}>
                    TOTAL PAIRS
                  </th>
                  <th style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontSize: "11px", fontWeight: "700", color: "#475569", width: "140px", textAlign: "center" }}>
                    ACTION
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ background: "#FFFFFF", height: "38px" }}>
                  <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", fontSize: "11px", fontWeight: "700", color: "#0F172A" }}>
                    Produced Qty
                  </td>
                  {SIZES.map((sz) => {
                    const rawVal = sizeQuantities[sz] ?? "0";
                    const isInvalid = rawVal !== "" && rawVal !== "0" && !/^\d+$/.test(rawVal.trim());
                    const isFilled = rawVal !== "" && rawVal !== "0" && !isInvalid;
                    return (
                      <td key={sz} style={{ border: "1px solid #CBD5E1", padding: "2px", textAlign: "center" }}>
                        <input
                          ref={(el) => { sizeInputRefs.current[sz] = el; }}
                          type="text"
                          inputMode="numeric"
                          pattern="[0-9]*"
                          value={rawVal}
                          onChange={(e) => handleSizeChange(sz, e.target.value)}
                          onFocus={(e) => handleSizeFocus(sz, e)}
                          onBlur={() => handleSizeBlur(sz)}
                          onKeyDown={(e) => handleSizeKeyDown(e, sz)}
                          style={{
                            width: "100%",
                            height: "32px",
                            border: isInvalid ? "2px solid #DC2626" : "none",
                            background: isInvalid ? "#FEF2F2" : isFilled ? "#EFF6FF" : "#FFFFFF",
                            color: isInvalid ? "#DC2626" : isFilled ? "#1E3A8A" : "#0F172A",
                            fontWeight: isFilled ? "700" : "500",
                            fontFamily: "'Fira Code', 'Roboto Mono', ui-monospace, monospace",
                            fontVariantNumeric: "tabular-nums",
                            fontSize: "13px",
                            textAlign: "center",
                            outline: "none"
                          }}
                        />
                      </td>
                    );
                  })}
                  <td style={{ border: "1px solid #CBD5E1", padding: "4px 8px", textAlign: "right", fontFamily: "monospace", fontVariantNumeric: "tabular-nums", fontWeight: "700", fontSize: "13px", color: totalBatchPairs > 0 ? "#1E3A8A" : "#64748B" }}>
                    {totalBatchPairs} prs
                  </td>
                  <td style={{ border: "1px solid #CBD5E1", padding: "3px 6px", textAlign: "center" }}>
                    <button
                      type="button"
                      onClick={handleCommitBatch}
                      disabled={submitting || totalBatchPairs === 0 || hasInvalidSizeInput}
                      style={{
                        width: "100%",
                        height: "30px",
                        background: submitting || totalBatchPairs === 0 || hasInvalidSizeInput ? "#94A3B8" : "#1E3A8A",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: "3px",
                        fontSize: "11px",
                        fontWeight: "700",
                        cursor: submitting || totalBatchPairs === 0 || hasInvalidSizeInput ? "not-allowed" : "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px"
                      }}
                    >
                      {submitting ? (
                        <>
                          <span
                            style={{
                              width: "12px",
                              height: "12px",
                              border: "2px solid #FFFFFF",
                              borderTopColor: "transparent",
                              borderRadius: "50%",
                              display: "inline-block",
                              animation: "spin 0.6s linear infinite"
                            }}
                          />
                          <span>सुरक्षित गर्दै...</span>
                        </>
                      ) : (
                        <>Commit <kbd style={{ fontFamily: "inherit", opacity: 0.85 }}>↵</kbd></>
                      )}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Filter and Quick Search Bar */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "10px 14px", display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "220px", background: "#F8FAFC", padding: "4px 10px", borderRadius: "3px", border: "1px solid #CBD5E1" }}>
          <Search size={14} color="#64748B" />
          <input
            type="text"
            placeholder="Search batch number, model, date..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ background: "none", border: "none", color: "#0F172A", fontSize: "12px", outline: "none", width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "11px", color: "#475569", fontWeight: "700", textTransform: "uppercase" }}>Filter SKU:</span>
            <select
              style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "3px", width: "180px", padding: "4px 8px", fontSize: "12px", color: "#0F172A", cursor: "pointer" }}
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
            >
              <option value="all">All Finished SKUs ({products.length})</option>
              {products.map((p) => (
                <option key={p.id} value={String(p.id)}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </div>

          <button onClick={handleExportCSV} className="btn-export" disabled={!filteredBatches.length}>
            <Download size={13} /> Export to CSV
          </button>
        </div>
      </div>

      {/* Production Batches Ledger Table */}
      <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", padding: "14px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Factory size={16} color="#1E3A8A" />
            <h3 style={{ fontSize: "13px", fontWeight: "700", color: "#0F172A", margin: 0, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Production Batches Ledger ({filteredBatches.length} Records)
            </h3>
          </div>
          <span style={{ fontSize: "11px", color: "#64748B" }}>Strict append-only physical output</span>
        </div>

        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>Loading production ledger...</div>
        ) : filteredBatches.length === 0 ? (
          <div style={{ padding: "30px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
            No production batches found matching filter criteria.
          </div>
        ) : (
          <div className="table-container-dense">
            <table className="table-dense">
              <thead>
                <tr>
                  <th className="sticky-col-left-1" style={{ width: "130px" }}>Batch Number</th>
                  <th className="sticky-col-left-2" style={{ minWidth: "160px" }}>Footwear Model</th>
                  <th style={{ width: "120px" }}>Date (AD / BS)</th>
                  <th style={{ width: "55px", textAlign: "center" }}>Size</th>
                  <th style={{ width: "75px" }}>Color</th>
                  <th style={{ textAlign: "right", width: "90px" }}>Target</th>
                  <th style={{ textAlign: "right", width: "105px" }}>Produced</th>
                  <th style={{ textAlign: "right", width: "70px" }}>Workers</th>
                  <th style={{ width: "115px", textAlign: "center" }}>Stock Impact</th>
                  <th style={{ width: "85px", textAlign: "center" }}>Status</th>
                  <th style={{ width: "75px", textAlign: "center" }}>Label</th>
                </tr>
              </thead>
              <tbody>
                {paginatedBatches.map((b) => {
                  const p = getProduct(b.product_id);
                  return (
                    <tr key={b.id}>
                      <td className="sticky-col-left-1 num-mono" style={{ fontWeight: "700", color: "#1E3A8A" }}>
                        {b.batch_number}
                      </td>
                      <td className="sticky-col-left-2" style={{ fontWeight: "600", color: "#0F172A" }}>
                        {p ? `${p.code} - ${p.name}` : `Product #${b.product_id}`}
                      </td>
                      <td style={{ fontSize: "12px", color: "#475569" }}>
                        {b.date_ad} <span style={{ fontSize: "11px", color: "#64748B" }}>({b.date_bs})</span>
                      </td>
                      <td style={{ textAlign: "center" }} className="num-mono">
                        <span style={{ padding: "1px 5px", background: "#EFF6FF", color: "#1E3A8A", borderRadius: "3px", fontWeight: "700", fontSize: "11px", border: "1px solid #BFDBFE" }}>
                          {p?.size || "-"}
                        </span>
                      </td>
                      <td style={{ color: "#475569", fontSize: "11px" }}>{p?.color || "-"}</td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        {b.target_quantity} prs
                      </td>
                      <td style={{ textAlign: "right", fontWeight: "700", color: "#0F172A" }} className="num-mono-bold">
                        {b.produced_quantity} pairs
                      </td>
                      <td style={{ textAlign: "right" }} className="num-mono">
                        {b.worker_count}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className="badge badge-success num-mono">
                          +{b.produced_quantity} IN
                        </span>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <span className="badge badge-info">{b.status || "Completed"}</span>
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button
                          type="button"
                          onClick={() => {
                            setCurrentLabelData({
                              productName: p?.name || "LIVO FOOTWEAR",
                              sku: p?.code || b.batch_number,
                              size: p?.size || "41",
                              color: p?.color || "-",
                              batchNumber: b.batch_number,
                              dateStr: b.date_ad,
                            });
                            setShowLabelModal(true);
                          }}
                          style={{
                            background: "#FFFFFF",
                            border: "1px solid #CBD5E1",
                            color: "#475569",
                            padding: "2px 6px",
                            borderRadius: "3px",
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                            fontSize: "11px"
                          }}
                          title="Print 2x1 Thermal Box Label"
                        >
                          <Printer size={11} /> Label
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredBatches.length > ITEMS_PER_PAGE && (
              <div className="pagination-bar" role="navigation" aria-label="Production batch pagination">
                <span>
                  Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1}–{Math.min(currentPage * ITEMS_PER_PAGE, filteredBatches.length)} of {filteredBatches.length} production batches
                </span>
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    aria-label="Previous page of batches"
                  >
                    Previous
                  </button>
                  <span style={{ fontSize: "12px", color: "#475569" }}>
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    className="pagination-btn"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    aria-label="Next page of batches"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 2x1 Thermal Box Label Print Modal */}
      <ThermalLabelModal
        isOpen={showLabelModal}
        onClose={() => setShowLabelModal(false)}
        labelData={currentLabelData}
      />
    </div>
  );
}

