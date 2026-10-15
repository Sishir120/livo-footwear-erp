"use client";

import React, { useState, useEffect } from "react";
import {
  Shield,
  UserCheck,
  UserX,
  UserPlus,
  Search,
  Lock,
  Mail,
  User as UserIcon,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  KeyRound,
  ShieldCheck,
  ShieldAlert,
  Info
} from "lucide-react";
import { useLocale } from "@/context/LocaleContext";

interface CompanyUser {
  id: number;
  company_id: number;
  name: string;
  username: string;
  email?: string | null;
  role: "admin" | "editor" | "viewer" | string;
  active: boolean;
  created_at?: string;
}

export function AdminControlView() {
  const { locale } = useLocale();
  const [users, setUsers] = useState<CompanyUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");

  // Create User Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<"admin" | "editor" | "viewer">("editor");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit Role/Status Modal
  const [editingUser, setEditingUser] = useState<CompanyUser | null>(null);
  const [editRole, setEditRole] = useState<string>("");
  const [editActive, setEditActive] = useState<boolean>(true);

  const fetchUsers = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/auth/users");
      if (!res.ok) {
        if (res.status === 403) {
          setErrorMsg(locale === "en" ? "Access Denied: Administrator role required." : "पहुँच अस्वीकृत: प्रशासक (Admin) अधिकार आवश्यक छ।");
        } else {
          setErrorMsg(locale === "en" ? `Failed to load users: HTTP ${res.status}` : `प्रयोगकर्ता सूची लोड हुन सकेन: HTTP ${res.status}`);
        }
        return;
      }
      const data: CompanyUser[] = await res.json();
      setUsers(data);
    } catch (err: any) {
      setErrorMsg(err.message || "Network error loading users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newName.trim() || !newPassword.trim()) {
      setErrorMsg(locale === "en" ? "Please fill in all required fields." : "कृपया आवश्यक सबै विवरण भर्नुहोस्।");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/auth/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: newUsername.trim(),
          name: newName.trim(),
          email: newEmail.trim() || null,
          password: newPassword,
          role: newRole
        })
      });

      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Failed to create user");
        return;
      }

      setSuccessMsg(locale === "en" ? `User '${data.username}' created successfully!` : `प्रयोगकर्ता '${data.username}' सफलतापूर्वक सिर्जना भयो!`);
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowCreateModal(false);
      setNewUsername("");
      setNewName("");
      setNewEmail("");
      setNewPassword("");
      setNewRole("editor");
      fetchUsers();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create user");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (user: CompanyUser) => {
    try {
      const res = await fetch(`/api/v1/auth/users/${user.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !user.active })
      });
      if (res.ok) {
        setSuccessMsg(
          user.active
            ? (locale === "en" ? `User '${user.username}' deactivated.` : `प्रयोगकर्ता '${user.username}' निष्क्रिय गरियो।`)
            : (locale === "en" ? `User '${user.username}' activated.` : `प्रयोगकर्ता '${user.username}' सक्रिय गरियो।`)
        );
        setTimeout(() => setSuccessMsg(null), 4000);
        fetchUsers();
      } else {
        const data = await res.json();
        setErrorMsg(data.detail || "Failed to update status");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Error updating user status");
    }
  };

  const handleUpdateRole = async () => {
    if (!editingUser) return;
    try {
      const res = await fetch(`/api/v1/auth/users/${editingUser.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: editRole, active: editActive })
      });
      if (res.ok) {
        setSuccessMsg(locale === "en" ? `Permissions updated for '${editingUser.username}'.` : `प्रयोगकर्ता '${editingUser.username}' को अधिकार अद्यावधिक गरियो।`);
        setTimeout(() => setSuccessMsg(null), 4000);
        setEditingUser(null);
        fetchUsers();
      } else {
        const data = await res.json();
        setErrorMsg(data.detail || "Failed to update user");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Error updating user");
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (u.email && u.email.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesRole = roleFilter === "ALL" || u.role.toLowerCase() === roleFilter.toLowerCase();
    return matchesSearch && matchesRole;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", maxWidth: "1280px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", background: "#1E3A8A", color: "#FFFFFF", borderRadius: "6px" }}>
              <Shield size={20} />
            </span>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "-0.01em" }}>
              {locale === "en" ? "Admin Control Center — User & Access Management" : "प्रशासक नियन्त्रण कक्ष (Admin Control Center) — प्रयोगकर्ता व्यवस्थापन"}
            </h1>
            <span style={{ fontSize: "11px", fontWeight: "700", background: "#EFF6FF", color: "#1E3A8A", border: "1px solid #BFDBFE", padding: "2px 8px", borderRadius: "4px" }}>
              RBAC PROTECTED
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "#475569" }}>
            {locale === "en"
              ? "Provision enterprise user accounts, manage role permissions, and enforce tenant security boundaries."
              : "कारखाना प्रयोगकर्ता खाता सिर्जना गर्नुहोस्, भूमिका अधिकार (Admin, Editor, Viewer) विन्यास गर्नुहोस् र सुरक्षा नियन्त्रण गर्नुहोस्।"}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchUsers}
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
            id="btn-add-user"
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
            <UserPlus size={16} />
            {locale === "en" ? "+ Add New User" : "+ नयाँ प्रयोगकर्ता थप्नुहोस्"}
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

      {/* Role Access Matrix Summary Card */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #1E3A8A", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", fontSize: "13px", color: "#1E3A8A" }}>
            <ShieldAlert size={16} /> ADMINISTRATOR (प्रशासक)
          </div>
          <p style={{ fontSize: "12px", color: "#475569", marginTop: "4px", lineHeight: "1.4" }}>
            Full system control: create/manage users, database backups, audit telemetry, diagnostic bundles, and policy parameters.
          </p>
        </div>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #047857", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", fontSize: "13px", color: "#047857" }}>
            <ShieldCheck size={16} /> FACTORY EDITOR (सञ्चालनकर्ता)
          </div>
          <p style={{ fontSize: "12px", color: "#475569", marginTop: "4px", lineHeight: "1.4" }}>
            Floor operations: create POs, goods receipts, sales orders, physical dispatches, worker payroll, and assembly runs.
          </p>
        </div>
        <div style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderLeft: "4px solid #0284C7", padding: "14px 16px", borderRadius: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: "700", fontSize: "13px", color: "#0284C7" }}>
            <Info size={16} /> AUDITOR VIEWER (निरीक्षक)
          </div>
          <p style={{ fontSize: "12px", color: "#475569", marginTop: "4px", lineHeight: "1.4" }}>
            Read-only compliance: inspection of stock ledgers, financial aging, tax invoices, production logs, and statements.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", background: "#FFFFFF", padding: "12px 16px", borderRadius: "4px", border: "1px solid #CBD5E1" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flex: 1, minWidth: "240px", position: "relative" }}>
          <Search size={16} style={{ position: "absolute", left: "10px", color: "#94A3B8" }} />
          <input
            type="text"
            placeholder={locale === "en" ? "Search users by name, username, or email..." : "नाम, प्रयोगकर्ता वा इमेल खोज्नुहोस्..."}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: "100%", padding: "7px 10px 7px 32px", fontSize: "12.5px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "12px", color: "#475569", fontWeight: "600" }}>{locale === "en" ? "Role:" : "भूमिका:"}</span>
          {["ALL", "admin", "editor", "viewer"].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRoleFilter(r)}
              style={{
                padding: "5px 10px",
                fontSize: "11.5px",
                fontWeight: "600",
                borderRadius: "3px",
                border: "1px solid",
                borderColor: roleFilter === r ? "#1E3A8A" : "#CBD5E1",
                background: roleFilter === r ? "#EFF6FF" : "#FFFFFF",
                color: roleFilter === r ? "#1E3A8A" : "#475569",
                cursor: "pointer"
              }}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <div style={{ background: "#FFFFFF", borderRadius: "4px", border: "1px solid #CBD5E1", overflow: "hidden", boxShadow: "0 1px 3px rgba(15,23,42,0.04)" }}>
        <table className="table-dense" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
          <thead>
            <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #CBD5E1", textAlign: "left", color: "#475569" }}>
              <th style={{ padding: "10px 14px", width: "60px" }}>ID</th>
              <th style={{ padding: "10px 14px" }}>{locale === "en" ? "Full Name" : "पूरा नाम"}</th>
              <th style={{ padding: "10px 14px" }}>{locale === "en" ? "Username" : "प्रयोगकर्ता नाम"}</th>
              <th style={{ padding: "10px 14px" }}>{locale === "en" ? "Email Address" : "इमेल"}</th>
              <th style={{ padding: "10px 14px", width: "120px" }}>{locale === "en" ? "Role" : "भूमिका"}</th>
              <th style={{ padding: "10px 14px", width: "100px" }}>{locale === "en" ? "Status" : "स्थिति"}</th>
              <th style={{ padding: "10px 14px", textAlign: "right", width: "180px" }}>{locale === "en" ? "Actions" : "कार्यहरू"}</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ padding: "28px", textAlign: "center", color: "#64748B" }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                  {locale === "en" ? "Loading company users..." : "प्रयोगकर्ताहरू लोड हुँदैछन्..."}
                </td>
              </tr>
            ) : filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ padding: "28px", textAlign: "center", color: "#64748B" }}>
                  {locale === "en" ? "No users found matching query." : "कुनै प्रयोगकर्ता भेटिएन।"}
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr key={u.id} style={{ borderBottom: "1px solid #F1F5F9", background: u.active ? "#FFFFFF" : "#F8FAFC" }}>
                  <td className="num-mono" style={{ padding: "10px 14px", color: "#64748B" }}>#{u.id}</td>
                  <td style={{ padding: "10px 14px", fontWeight: "600", color: "#0F172A" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div style={{ width: "26px", height: "26px", borderRadius: "50%", background: "#EFF6FF", color: "#1E3A8A", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: "700" }}>
                        {u.name.slice(0, 2).toUpperCase()}
                      </div>
                      {u.name}
                    </div>
                  </td>
                  <td className="num-mono" style={{ padding: "10px 14px", color: "#1E3A8A", fontWeight: "500" }}>{u.username}</td>
                  <td style={{ padding: "10px 14px", color: "#475569" }}>{u.email || "—"}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "3px 8px",
                        borderRadius: "3px",
                        fontSize: "11px",
                        fontWeight: "700",
                        textTransform: "uppercase",
                        background: u.role === "admin" ? "#FEF2F2" : u.role === "editor" ? "#F0FDF4" : "#F0F9FF",
                        color: u.role === "admin" ? "#991B1B" : u.role === "editor" ? "#166534" : "#0369A1",
                        border: "1px solid",
                        borderColor: u.role === "admin" ? "#FECACA" : u.role === "editor" ? "#BBF7D0" : "#BAE6FD"
                      }}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: "2px 6px",
                        borderRadius: "3px",
                        fontSize: "11px",
                        fontWeight: "600",
                        background: u.active ? "#DCFCE7" : "#F1F5F9",
                        color: u.active ? "#15803D" : "#64748B"
                      }}
                    >
                      {u.active ? <CheckCircle2 size={11} /> : <UserX size={11} />}
                      {u.active ? (locale === "en" ? "Active" : "सक्रिय") : (locale === "en" ? "Inactive" : "निष्क्रिय")}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "right" }}>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingUser(u);
                          setEditRole(u.role);
                          setEditActive(u.active);
                        }}
                        style={{
                          padding: "4px 8px",
                          fontSize: "11px",
                          fontWeight: "600",
                          background: "#FFFFFF",
                          border: "1px solid #CBD5E1",
                          borderRadius: "3px",
                          color: "#1E3A8A",
                          cursor: "pointer"
                        }}
                      >
                        {locale === "en" ? "Edit Role" : "भूमिका फेर्नुहोस्"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleActive(u)}
                        style={{
                          padding: "4px 8px",
                          fontSize: "11px",
                          fontWeight: "600",
                          background: "#FFFFFF",
                          border: "1px solid",
                          borderColor: u.active ? "#FCA5A5" : "#86EFAC",
                          color: u.active ? "#BE123C" : "#15803D",
                          borderRadius: "3px",
                          cursor: "pointer"
                        }}
                      >
                        {u.active ? (locale === "en" ? "Deactivate" : "निष्क्रिय") : (locale === "en" ? "Activate" : "सक्रिय")}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal: Create User */}
      {showCreateModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "460px", padding: "24px", boxShadow: "0 10px 25px rgba(0,0,0,0.15)", border: "1px solid #CBD5E1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <UserPlus size={18} color="#1E3A8A" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A" }}>
                  {locale === "en" ? "Add Company User" : "नयाँ कम्पनी प्रयोगकर्ता थप्नुहोस्"}
                </h3>
              </div>
              <button type="button" onClick={() => setShowCreateModal(false)} style={{ background: "none", border: "none", fontSize: "18px", color: "#64748B", cursor: "pointer" }}>✕</button>
            </div>

            <form onSubmit={handleCreateUser} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Full Name *" : "पूरा नाम *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Shrestha"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Username (Login ID) *" : "प्रयोगकर्ता नाम (लगइन आईडी) *"}
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. ramesh_op"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Email Address (Optional)" : "इमेल (ऐच्छिक)"}
                </label>
                <input
                  type="email"
                  placeholder="e.g. ramesh@livogroup.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Initial Password *" : "प्रारम्भिक पासवर्ड *"}
                </label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 8 characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Role & Access Scope *" : "भूमिका तथा अधिकार *"}
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as any)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", outline: "none", background: "#FFFFFF" }}
                >
                  <option value="editor">Editor — Factory Floor Operations (PO, Sales, Production, HR)</option>
                  <option value="viewer">Viewer — Read-Only Auditor (Ledgers, Aging, Reports)</option>
                  <option value="admin">Admin — Executive Supervisor (Full Security & Settings)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: "8px 14px", fontSize: "13px", fontWeight: "600", background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", color: "#475569", cursor: "pointer" }}
                >
                  {locale === "en" ? "Cancel" : "रद्द गर्नुहोस्"}
                </button>
                <button
                  type="submit"
                  id="btn-submit-user"
                  disabled={isSubmitting}
                  style={{ padding: "8px 18px", fontSize: "13px", fontWeight: "600", background: "#1E3A8A", border: "none", borderRadius: "4px", color: "#FFFFFF", cursor: isSubmitting ? "not-allowed" : "pointer" }}
                >
                  {isSubmitting ? (locale === "en" ? "Creating..." : "बनाउँदैछ...") : (locale === "en" ? "Create Account" : "खाता सिर्जना गर्नुहोस्")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit User Role/Status */}
      {editingUser && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "16px" }}>
          <div style={{ background: "#FFFFFF", borderRadius: "6px", width: "100%", maxWidth: "420px", padding: "24px", boxShadow: "0 10px 25px rgba(0,0,0,0.15)", border: "1px solid #CBD5E1" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #E2E8F0", paddingBottom: "12px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? `Modify Access: ${editingUser.name}` : `अधिकार परिमार्जन: ${editingUser.name}`}
              </h3>
              <button type="button" onClick={() => setEditingUser(null)} style={{ background: "none", border: "none", fontSize: "18px", color: "#64748B", cursor: "pointer" }}>✕</button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Assigned Role" : "तोकिएको भूमिका"}
                </label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF" }}
                >
                  <option value="admin">Admin (प्रशासक)</option>
                  <option value="editor">Editor (सञ्चालक)</option>
                  <option value="viewer">Viewer (निरीक्षक)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Account Status" : "खाता स्थिति"}
                </label>
                <div style={{ display: "flex", gap: "10px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", cursor: "pointer" }}>
                    <input
                      type="radio"
                      name="status"
                      checked={editActive === true}
                      onChange={() => setEditActive(true)}
                    />
                    {locale === "en" ? "Active (Can Login)" : "सक्रिय (लगइन गर्न पाउने)"}
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", cursor: "pointer" }}>
                    <input
                      type="radio"
                      name="status"
                      checked={editActive === false}
                      onChange={() => setEditActive(false)}
                    />
                    {locale === "en" ? "Inactive (Disabled)" : "निष्क्रिय (लगइन रोक्ने)"}
                  </label>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  style={{ padding: "8px 14px", fontSize: "13px", fontWeight: "600", background: "#F1F5F9", border: "1px solid #CBD5E1", borderRadius: "4px", color: "#475569", cursor: "pointer" }}
                >
                  {locale === "en" ? "Cancel" : "रद्द"}
                </button>
                <button
                  type="button"
                  onClick={handleUpdateRole}
                  style={{ padding: "8px 18px", fontSize: "13px", fontWeight: "600", background: "#1E3A8A", border: "none", borderRadius: "4px", color: "#FFFFFF", cursor: "pointer" }}
                >
                  {locale === "en" ? "Save Changes" : "सुरक्षित गर्नुहोस्"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
