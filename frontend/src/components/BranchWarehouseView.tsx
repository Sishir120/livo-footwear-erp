"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  Store,
  Factory,
  Warehouse as WarehouseIcon,
  Plus,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertCircle,
  Link as LinkIcon,
  Unlink,
  Phone,
  Mail,
  MapPin,
  Shield,
  Layers,
  ArrowRightLeft
} from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

interface WarehouseItem {
  id: number;
  name: string;
  code: string;
  location?: string | null;
  is_active: boolean;
  branch_id?: number | null;
}

interface BranchItem {
  id: number;
  company_id: number;
  code: string;
  name: string;
  type: "HEAD_OFFICE" | "FACTORY" | "RETAIL_OUTLET" | "REGIONAL_HUB" | string;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
  warehouses_count: number;
  warehouses: WarehouseItem[];
  created_at?: string;
}

const TYPE_CONFIG: Record<string, { labelEn: string; labelNe: string; color: string; bg: string; border: string }> = {
  HEAD_OFFICE: { labelEn: "Head Office", labelNe: "केन्द्रीय कार्यालय", color: "#6B21A8", bg: "#F3E8FF", border: "#D8B4FE" },
  FACTORY: { labelEn: "Production Factory", labelNe: "उत्पादन कारखाना", color: "#065F46", bg: "#D1FAE5", border: "#A7F3D0" },
  RETAIL_OUTLET: { labelEn: "Retail Showroom", labelNe: "खुद्रा शोरुम", color: "#1E40AF", bg: "#DBEAFE", border: "#BFDBFE" },
  REGIONAL_HUB: { labelEn: "Regional Distribution Hub", labelNe: "क्षेत्रीय वितरण केन्द्र", color: "#92400E", bg: "#FEF3C7", border: "#FDE68A" }
};

export function BranchWarehouseView() {
  const { locale } = useLocale();
  const [branches, setBranches] = useState<BranchItem[]>([]);
  const [unassignedWarehouses, setUnassignedWarehouses] = useState<WarehouseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");

  // Create Branch Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("RETAIL_OUTLET");
  const [newAddress, setNewAddress] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Warehouse Assignment Modal
  const [assignTargetBranch, setAssignTargetBranch] = useState<BranchItem | null>(null);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<number | "">("");

  const fetchBranchesAndWarehouses = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [brRes, whRes] = await Promise.all([
        fetch("/api/v1/branches"),
        fetch("/api/v1/stock/warehouses")
      ]);

      if (!brRes.ok) throw new Error(`HTTP ${brRes.status} loading branches`);
      if (!whRes.ok) throw new Error(`HTTP ${whRes.status} loading warehouses`);

      const brData: BranchItem[] = await brRes.json();
      const whData: WarehouseItem[] = await whRes.json();

      setBranches(brData);

      // Identify warehouses not assigned to any branch
      const unassigned = whData.filter((w) => !w.branch_id);
      setUnassignedWarehouses(unassigned);
    } catch (err: any) {
      setErrorMsg(err.message || "Network error loading branch architecture data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBranchesAndWarehouses();
  }, []);

  const handleCreateBranch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newName.trim()) {
      setErrorMsg(locale === "en" ? "Code and Name are required." : "शाखा कोड र नाम आवश्यक छन्।");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/branches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: newCode.trim().toUpperCase(),
          name: newName.trim(),
          type: newType,
          address: newAddress.trim() || null,
          phone: newPhone.trim() || null,
          email: newEmail.trim() || null
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create branch");
      }

      setSuccessMsg(locale === "en" ? `Branch '${data.name}' created successfully.` : `शाखा '${data.name}' सफलतापूर्वक सिर्जना गरियो।`);
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowCreateModal(false);
      setNewCode("");
      setNewName("");
      setNewAddress("");
      setNewPhone("");
      setNewEmail("");
      fetchBranchesAndWarehouses();
    } catch (err: any) {
      setErrorMsg(err.message || "Error creating branch");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (branch: BranchItem) => {
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/v1/branches/${branch.id}/toggle-active`, {
        method: "PATCH"
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update branch status");
      }
      setSuccessMsg(
        branch.is_active
          ? (locale === "en" ? `Branch '${branch.name}' deactivated.` : `शाखा '${branch.name}' निष्क्रिय गरियो।`)
          : (locale === "en" ? `Branch '${branch.name}' activated.` : `शाखा '${branch.name}' सक्रिय गरियो।`)
      );
      setTimeout(() => setSuccessMsg(null), 4000);
      fetchBranchesAndWarehouses();
    } catch (err: any) {
      setErrorMsg(err.message || "Error toggling branch status");
    }
  };

  const handleAssignWarehouse = async () => {
    if (!assignTargetBranch || !selectedWarehouseId) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/v1/branches/${assignTargetBranch.id}/warehouses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ warehouse_id: Number(selectedWarehouseId) })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to assign warehouse");
      }
      setSuccessMsg(locale === "en" ? `Warehouse assigned to branch '${assignTargetBranch.name}'.` : `गोदाम शाखा '${assignTargetBranch.name}' मा आबद्ध गरियो।`);
      setTimeout(() => setSuccessMsg(null), 4000);
      setAssignTargetBranch(null);
      setSelectedWarehouseId("");
      fetchBranchesAndWarehouses();
    } catch (err: any) {
      setErrorMsg(err.message || "Error assigning warehouse");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUnlinkWarehouse = async (branchId: number, warehouseId: number, whName: string) => {
    if (!confirm(locale === "en" ? `Unlink warehouse '${whName}' from this branch?` : `के तपाईं '${whName}' गोदामलाई यो शाखाबाट हटाउन चाहनुहुन्छ?`)) return;
    try {
      const res = await fetch(`/api/v1/branches/${branchId}/warehouses/${warehouseId}`, {
        method: "DELETE"
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to unlink warehouse");
      }
      setSuccessMsg(locale === "en" ? `Warehouse '${whName}' unlinked.` : `गोदाम '${whName}' शाखाबाट अलग गरियो।`);
      setTimeout(() => setSuccessMsg(null), 4000);
      fetchBranchesAndWarehouses();
    } catch (err: any) {
      setErrorMsg(err.message || "Error unlinking warehouse");
    }
  };

  // Metrics
  const totalBranches = branches.length;
  const activeShowrooms = branches.filter((b) => b.type === "RETAIL_OUTLET" && b.is_active).length;
  const activeFactories = branches.filter((b) => b.type === "FACTORY" && b.is_active).length;
  const totalWarehousesLinked = branches.reduce((acc, b) => acc + (b.warehouses?.length || 0), 0);

  const filteredBranches = branches.filter((b) => {
    const matchesSearch =
      b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      b.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (b.address && b.address.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesType = typeFilter === "ALL" || b.type === typeFilter;
    return matchesSearch && matchesType;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", background: "#1E3A8A", color: "#FFFFFF", borderRadius: "6px" }}>
              <Building2 size={20} />
            </span>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "-0.01em" }}>
              {locale === "en" ? "Branch & Warehouse Management" : "शाखा तथा गोदाम व्यवस्थापन (Branch & Warehouse Management)"}
            </h1>
            <span style={{ fontSize: "11px", fontWeight: "700", background: "#EFF6FF", color: "#1E3A8A", border: "1px solid #BFDBFE", padding: "2px 8px", borderRadius: "4px" }}>
              MULTI-LOCATION
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            {locale === "en"
              ? "Configure factories, regional showrooms, and distribution hubs. Link physical storage warehouses to operating units."
              : "उत्पादन कारखाना, खुद्रा शोरुम तथा वितरण हब विन्यास गर्नुहोस् र भौतिक गोदामहरूलाई सम्बन्धित शाखामा आबद्ध गर्नुहोस्।"}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchBranchesAndWarehouses}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 12px",
              background: "#FFFFFF",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              fontSize: "12.5px",
              fontWeight: "600",
              color: "#334155",
              cursor: "pointer"
            }}
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            {locale === "en" ? "Refresh" : "ताजा गर्नुहोस्"}
          </button>
          <button
            type="button"
            id="btn-add-branch"
            onClick={() => setShowCreateModal(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              background: "#1E3A8A",
              color: "#FFFFFF",
              border: "1px solid #1E3A8A",
              borderRadius: "4px",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
            }}
          >
            <Plus size={16} />
            {locale === "en" ? "+ Add New Branch" : "+ नयाँ शाखा थप्नुहोस्"}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", color: "#166534", padding: "10px 14px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <CheckCircle2 size={16} color="#16A34A" /> {successMsg}
        </div>
      )}
      {errorMsg && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", color: "#991B1B", padding: "10px 14px", borderRadius: "4px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <AlertCircle size={16} color="#DC2626" /> {errorMsg}
        </div>
      )}

      {/* Metrics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #1E3A8A", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ fontSize: "12px", color: "#64748B", fontWeight: "600", textTransform: "uppercase" }}>
            {locale === "en" ? "Total Operating Branches" : "कुल सञ्चालित शाखाहरू"}
          </div>
          <div style={{ fontSize: "24px", fontWeight: "800", color: "#0F172A", marginTop: "4px" }}>
            {totalBranches}
          </div>
        </div>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #2563EB", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ fontSize: "12px", color: "#64748B", fontWeight: "600", textTransform: "uppercase" }}>
            {locale === "en" ? "Active Showrooms" : "सक्रिय खुद्रा शोरुमहरू"}
          </div>
          <div style={{ fontSize: "24px", fontWeight: "800", color: "#2563EB", marginTop: "4px" }}>
            {activeShowrooms}
          </div>
        </div>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #059669", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ fontSize: "12px", color: "#64748B", fontWeight: "600", textTransform: "uppercase" }}>
            {locale === "en" ? "Production Factories" : "उत्पादन कारखानाहरू"}
          </div>
          <div style={{ fontSize: "24px", fontWeight: "800", color: "#059669", marginTop: "4px" }}>
            {activeFactories}
          </div>
        </div>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #7C3AED", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ fontSize: "12px", color: "#64748B", fontWeight: "600", textTransform: "uppercase" }}>
            {locale === "en" ? "Warehouses Linked" : "शाखामा आबद्ध गोदामहरू"}
          </div>
          <div style={{ fontSize: "24px", fontWeight: "800", color: "#7C3AED", marginTop: "4px" }}>
            {totalWarehousesLinked}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", background: "#FFFFFF", padding: "12px 16px", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "240px", position: "relative" }}>
          <Search size={16} style={{ position: "absolute", left: "10px", color: "#94A3B8" }} />
          <input
            type="text"
            placeholder={locale === "en" ? "Search branch by code, name, or city..." : "शाखा कोड, नाम वा ठेगाना खोज्नुहोस्..."}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: "100%", padding: "7px 10px 7px 32px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "12px", color: "#475569", fontWeight: "600" }}>{locale === "en" ? "Type:" : "प्रकार:"}</span>
          {["ALL", "HEAD_OFFICE", "FACTORY", "RETAIL_OUTLET", "REGIONAL_HUB"].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTypeFilter(t)}
              style={{
                padding: "5px 10px",
                fontSize: "11px",
                fontWeight: "600",
                borderRadius: "3px",
                border: "1px solid",
                borderColor: typeFilter === t ? "#1E3A8A" : "#CBD5E1",
                background: typeFilter === t ? "#EFF6FF" : "#FFFFFF",
                color: typeFilter === t ? "#1E3A8A" : "#475569",
                cursor: "pointer"
              }}
            >
              {t === "ALL" ? (locale === "en" ? "ALL" : "सबै") : (locale === "en" ? TYPE_CONFIG[t]?.labelEn : TYPE_CONFIG[t]?.labelNe)}
            </button>
          ))}
        </div>
      </div>

      {/* Branch Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "16px" }}>
        {loading ? (
          <div style={{ gridColumn: "1 / -1", padding: "40px", textAlign: "center", color: "#64748B", background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
            <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 8px" }} />
            {locale === "en" ? "Loading branches and warehouse mappings..." : "शाखा र गोदाम संरचना लोड हुँदैछ..."}
          </div>
        ) : filteredBranches.length === 0 ? (
          <div style={{ gridColumn: "1 / -1", padding: "40px", textAlign: "center", color: "#64748B", background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
            <Building2 size={32} style={{ margin: "0 auto 8px", color: "#94A3B8" }} />
            <p style={{ fontWeight: "600", color: "#334155" }}>
              {locale === "en" ? "No branches found." : "कुनै शाखा फेला परेन।"}
            </p>
            <p style={{ fontSize: "12px", color: "#64748B", marginTop: "4px" }}>
              {locale === "en" ? "Click '+ Add New Branch' above to register your first branch." : "माथिको '+ नयाँ शाखा थप्नुहोस्' बटन थिचेर शाखा थप्नुहोस्।"}
            </p>
          </div>
        ) : (
          filteredBranches.map((b) => {
            const typeMeta = TYPE_CONFIG[b.type] || { labelEn: b.type, labelNe: b.type, color: "#475569", bg: "#F1F5F9", border: "#CBD5E1" };
            return (
              <div
                key={b.id}
                style={{
                  background: "#FFFFFF",
                  borderRadius: "6px",
                  border: "1px solid #CBD5E1",
                  boxShadow: "0 1px 3px rgba(15,23,42,0.05)",
                  display: "flex",
                  flexDirection: "column",
                  overflow: "hidden"
                }}
              >
                {/* Branch Card Top Header */}
                <div style={{ padding: "14px 16px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "800", color: "#1E3A8A", background: "#EFF6FF", border: "1px solid #BFDBFE", padding: "2px 6px", borderRadius: "3px", letterSpacing: "0.03em" }}>
                        {b.code}
                      </span>
                      <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                        {b.name}
                      </h3>
                    </div>
                    <div style={{ marginTop: "6px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: typeMeta.color, background: typeMeta.bg, border: `1px solid ${typeMeta.border}`, padding: "2px 8px", borderRadius: "10px" }}>
                        {locale === "en" ? typeMeta.labelEn : typeMeta.labelNe}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleToggleActive(b)}
                    style={{
                      padding: "3px 8px",
                      fontSize: "11px",
                      fontWeight: "700",
                      borderRadius: "12px",
                      border: "1px solid",
                      borderColor: b.is_active ? "#BBF7D0" : "#FCA5A5",
                      background: b.is_active ? "#F0FDF4" : "#FEF2F2",
                      color: b.is_active ? "#15803D" : "#B91C1C",
                      cursor: "pointer"
                    }}
                    title={locale === "en" ? "Click to toggle active status" : "स्थिति परिवर्तन गर्न थिच्नुहोस्"}
                  >
                    {b.is_active ? (locale === "en" ? "ACTIVE" : "सक्रिय") : (locale === "en" ? "INACTIVE" : "निष्क्रिय")}
                  </button>
                </div>

                {/* Branch Contact Info */}
                <div style={{ padding: "12px 16px", fontSize: "12px", color: "#475569", display: "flex", flexDirection: "column", gap: "6px", borderBottom: "1px solid #F1F5F9" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <MapPin size={14} color="#64748B" />
                    <span>{b.address || (locale === "en" ? "No address specified" : "ठेगाना उल्लेख छैन")}</span>
                  </div>
                  {b.phone && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Phone size={14} color="#64748B" />
                      <span>{b.phone}</span>
                    </div>
                  )}
                  {b.email && (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <Mail size={14} color="#64748B" />
                      <span>{b.email}</span>
                    </div>
                  )}
                </div>

                {/* Linked Warehouses Section */}
                <div style={{ padding: "12px 16px", flex: 1, background: "#F8FAFC" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <span style={{ fontSize: "11.5px", fontWeight: "700", color: "#334155", display: "flex", alignItems: "center", gap: "5px" }}>
                      <WarehouseIcon size={14} color="#64748B" />
                      {locale === "en" ? "Linked Warehouses" : "आबद्ध गोदामहरू"} ({b.warehouses?.length || 0})
                    </span>
                    {b.is_active && (
                      <button
                        type="button"
                        onClick={() => {
                          setAssignTargetBranch(b);
                          setSelectedWarehouseId("");
                        }}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#1E3A8A",
                          fontSize: "11.5px",
                          fontWeight: "700",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px"
                        }}
                      >
                        <Plus size={12} /> {locale === "en" ? "Link Warehouse" : "गोदाम जोड्नुहोस्"}
                      </button>
                    )}
                  </div>

                  {b.warehouses && b.warehouses.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {b.warehouses.map((w) => (
                        <div
                          key={w.id}
                          style={{
                            background: "#FFFFFF",
                            border: "1px solid #E2E8F0",
                            borderRadius: "4px",
                            padding: "6px 10px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            fontSize: "12px"
                          }}
                        >
                          <div>
                            <span style={{ fontWeight: "700", color: "#1E293B" }}>{w.name}</span>
                            <span style={{ fontSize: "10.5px", color: "#64748B", marginLeft: "6px" }}>({w.code})</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleUnlinkWarehouse(b.id, w.id, w.name)}
                            style={{
                              background: "none",
                              border: "none",
                              color: "#DC2626",
                              cursor: "pointer",
                              padding: "2px",
                              display: "inline-flex",
                              alignItems: "center"
                            }}
                            title={locale === "en" ? "Unlink from branch" : "शाखाबाट अलग गर्नुहोस्"}
                          >
                            <Unlink size={13} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: "11.5px", color: "#94A3B8", fontStyle: "italic", padding: "6px 0" }}>
                      {locale === "en" ? "No storage warehouses linked yet." : "हाल कुनै गोदाम आबद्ध छैन।"}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Add Branch */}
      {showCreateModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "480px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)", overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC" }}>
              <h2 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <Building2 size={18} color="#1E3A8A" />
                {locale === "en" ? "Register New Branch Location" : "नयाँ शाखा विन्यास फारम"}
              </h2>
              <button onClick={() => setShowCreateModal(false)} style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#64748B" }}>
                &times;
              </button>
            </div>

            <form onSubmit={handleCreateBranch} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Branch Code *" : "शाखा कोड (Branch Code) *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. BR-KTM-01"
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
                <span style={{ fontSize: "11px", color: "#64748B" }}>Unique uppercase identifier across this company.</span>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Branch Name *" : "शाखा नाम (Branch Name) *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Kathmandu Main Showroom"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Operating Type *" : "सञ्चालन प्रकार (Operating Type) *"}
                </label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", outline: "none" }}
                >
                  <option value="RETAIL_OUTLET">Retail Showroom (खुद्रा शोरुम)</option>
                  <option value="FACTORY">Production Factory (कारखाना)</option>
                  <option value="HEAD_OFFICE">Head Office (केन्द्रीय कार्यालय)</option>
                  <option value="REGIONAL_HUB">Regional Distribution Hub (क्षेत्रीय हब)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Address / City" : "ठेगाना / सहर"}
                </label>
                <input
                  type="text"
                  placeholder="e.g. New Road, Kathmandu"
                  value={newAddress}
                  onChange={(e) => setNewAddress(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Contact Phone" : "सम्पर्क फोन"}
                  </label>
                  <input
                    type="text"
                    placeholder="01-4XXXXXX"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                    {locale === "en" ? "Branch Email" : "इमेल"}
                  </label>
                  <input
                    type="email"
                    placeholder="branch@livo.com.np"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                    style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: "8px 14px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12.5px", cursor: "pointer", color: "#475569" }}
                >
                  {locale === "en" ? "Cancel" : "रद्द गर्नुहोस्"}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{ padding: "8px 18px", background: "#1E3A8A", border: "1px solid #1E3A8A", borderRadius: "4px", fontSize: "12.5px", fontWeight: "700", color: "#FFFFFF", cursor: "pointer" }}
                >
                  {isSubmitting ? (locale === "en" ? "Saving..." : "सुरक्षित गरिँदै...") : (locale === "en" ? "Create Branch" : "शाखा सिर्जना गर्नुहोस्")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Assign Warehouse to Branch */}
      {assignTargetBranch && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "440px", boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)", overflow: "hidden" }}>
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC" }}>
              <h2 style={{ fontSize: "14.5px", fontWeight: "700", color: "#0F172A", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <LinkIcon size={16} color="#1E3A8A" />
                {locale === "en" ? `Link Warehouse to ${assignTargetBranch.name}` : `${assignTargetBranch.name} मा गोदाम आबद्ध गर्नुहोस्`}
              </h2>
              <button onClick={() => setAssignTargetBranch(null)} style={{ background: "none", border: "none", fontSize: "18px", cursor: "pointer", color: "#64748B" }}>
                &times;
              </button>
            </div>

            <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <p style={{ fontSize: "12.5px", color: "#475569" }}>
                {locale === "en"
                  ? "Select an existing storage warehouse to attribute its physical inventory to this branch."
                  : "यो शाखामा भौतिक मौज्दात गणना गर्न उपलब्ध गोदाम छनोट गर्नुहोस्।"}
              </p>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "700", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Available Warehouses" : "उपलब्ध गोदामहरू"}
                </label>
                <select
                  value={selectedWarehouseId}
                  onChange={(e) => setSelectedWarehouseId(e.target.value ? Number(e.target.value) : "")}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", outline: "none" }}
                >
                  <option value="">{locale === "en" ? "-- Choose a Warehouse --" : "-- गोदाम छनोट गर्नुहोस् --"}</option>
                  {unassignedWarehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.code}) {w.location ? `— ${w.location}` : ""}
                    </option>
                  ))}
                </select>
              </div>

              {unassignedWarehouses.length === 0 && (
                <div style={{ fontSize: "12px", color: "#64748B", background: "#F1F5F9", padding: "8px 12px", borderRadius: "4px" }}>
                  {locale === "en"
                    ? "All company warehouses are currently assigned to branches."
                    : "कम्पनीका सबै गोदामहरू हाल शाखाहरूमा आबद्ध भइसकेका छन्।"}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setAssignTargetBranch(null)}
                  style={{ padding: "8px 14px", background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "4px", fontSize: "12.5px", cursor: "pointer", color: "#475569" }}
                >
                  {locale === "en" ? "Cancel" : "रद्द गर्नुहोस्"}
                </button>
                <button
                  type="button"
                  disabled={!selectedWarehouseId || isSubmitting}
                  onClick={handleAssignWarehouse}
                  style={{ padding: "8px 18px", background: selectedWarehouseId ? "#1E3A8A" : "#94A3B8", border: "none", borderRadius: "4px", fontSize: "12.5px", fontWeight: "700", color: "#FFFFFF", cursor: selectedWarehouseId ? "pointer" : "not-allowed" }}
                >
                  {isSubmitting ? (locale === "en" ? "Assigning..." : "जोडिँदै...") : (locale === "en" ? "Confirm Link" : "आबद्ध गर्नुहोस्")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
