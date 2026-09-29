"use client";

import React, { useState, useEffect } from "react";
import {
  Building2,
  Sliders,
  Percent,
  HardDrive,
  Database,
  Server,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Save,
  Trash2,
  ShieldCheck,
  Check
} from "lucide-react";
import { clearOfflineQueue } from "@/lib/offlineQueue";
import { useLocale } from "@/context/LocaleContext";

export function SettingsView() {
  const { locale } = useLocale();
  // Factory Configuration State
  const [companyName, setCompanyName] = useState("Livo Footwear Industries Pvt. Ltd.");
  const [panNumber] = useState("609823412"); // Read-only statutory identifier
  const [factoryAddress, setFactoryAddress] = useState("Pokhara-09, Kaski, Nepal");

  const [standardCurve, setStandardCurve] = useState("Paris Points (Sizes 32–43)");
  const [cartonMultiplier, setCartonMultiplier] = useState("12");
  const [coreSizeAlert, setCoreSizeAlert] = useState("39, 40, 41");

  const [vatRate, setVatRate] = useState("13% (Nepal IRD Schedule-5)");
  const [paymentTerms, setPaymentTerms] = useState("30 Days Net");
  const [defaultCreditLimit, setDefaultCreditLimit] = useState("500,000.00");

  const [savedNotice, setSavedNotice] = useState(false);
  const [cacheNotice, setCacheNotice] = useState<string | null>(null);

  // Operational Diagnostics & Backup State
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [backupStatus, setBackupStatus] = useState<any>(null);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);

  useEffect(() => {
    // Load persisted settings if any
    try {
      const stored = localStorage.getItem("livo_factory_settings");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.companyName) setCompanyName(parsed.companyName);
        if (parsed.factoryAddress) setFactoryAddress(parsed.factoryAddress);
        if (parsed.standardCurve) setStandardCurve(parsed.standardCurve);
        if (parsed.cartonMultiplier) setCartonMultiplier(parsed.cartonMultiplier);
        if (parsed.coreSizeAlert) setCoreSizeAlert(parsed.coreSizeAlert);
        if (parsed.vatRate) setVatRate(parsed.vatRate);
        if (parsed.paymentTerms) setPaymentTerms(parsed.paymentTerms);
        if (parsed.defaultCreditLimit) setDefaultCreditLimit(parsed.defaultCreditLimit);
      }
    } catch (e) {
      console.error(e);
    }

    fetch("/api/v1/health")
      .then((res) => res.json())
      .then((data) => setHealthInfo(data))
      .catch((err) => console.error(err));

    fetchBackupStatus();
  }, []);

  const fetchBackupStatus = () => {
    fetch("/api/v1/backup/status")
      .then((res) => res.json())
      .then((data) => setBackupStatus(data))
      .catch((err) => console.error(err));
  };

  const handleSaveSettings = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        companyName,
        factoryAddress,
        standardCurve,
        cartonMultiplier,
        coreSizeAlert,
        vatRate,
        paymentTerms,
        defaultCreditLimit
      };
      localStorage.setItem("livo_factory_settings", JSON.stringify(payload));
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 3500);
    } catch (err) {
      console.error(err);
    }
  };

  const handleClearCache = async () => {
    try {
      await clearOfflineQueue();
      setCacheNotice(
        locale === "en"
          ? "Local draft cache cleared successfully."
          : "स्थानीय ड्राफ्ट र क्यास सफा गरियो (Local draft cache cleared)"
      );
      setTimeout(() => setCacheNotice(null), 4000);
    } catch (err: any) {
      setCacheNotice(`Failed to clear cache: ${err.message}`);
      setTimeout(() => setCacheNotice(null), 4000);
    }
  };

  const handleRunBackup = async () => {
    setIsBackingUp(true);
    setBackupMessage(null);
    try {
      const res = await fetch("/api/v1/backup/run", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setBackupMessage("Database backup completed successfully.");
      } else {
        setBackupMessage(`Backup failed: ${data.detail || "Unknown error"}`);
      }
      fetchBackupStatus();
    } catch (err: any) {
      setBackupMessage(`Backup failed: ${err.message}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleDownloadDiagnostics = () => {
    window.location.href = "/api/v1/diagnostics/download";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: "1100px", margin: "0 auto" }}>
      {/* Header & Save Action Bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", letterSpacing: "-0.01em" }}>
            {locale === "en" ? "System Settings & Factory Policy" : "प्रणाली सेटिङ तथा कारखाना विन्यास (System Settings & Factory Config)"}
          </h1>
          <p style={{ fontSize: "13px", color: "#475569", marginTop: "2px" }}>
            Industrial paper parameter configuration, statutory terms, offline sync storage, and cloud disaster recovery.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {savedNotice && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: "#DCFCE7",
                color: "#166534",
                border: "1px solid #BBF7D0",
                padding: "6px 12px",
                borderRadius: "4px",
                fontSize: "12.5px",
                fontWeight: "600",
                animation: "fadeIn 0.2s ease"
              }}
            >
              <Check size={16} /> {locale === "en" ? "Settings Saved" : "परिवर्तन सुरक्षित भयो (Settings Saved)"}
            </span>
          )}
          <button
            type="button"
            id="btn-save-settings"
            onClick={handleSaveSettings}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#1E3A8A",
              color: "#FFFFFF",
              border: "1px solid #1E3A8A",
              borderRadius: "4px",
              padding: "8px 16px",
              fontSize: "13px",
              fontWeight: "600",
              cursor: "pointer",
              transition: "background-color 0.15s ease"
            }}
          >
            <Save size={15} /> {locale === "en" ? "Save Settings" : "सुरक्षित गर्नुहोस् (Save Settings)"}
          </button>
        </div>
      </div>

      {/* Main Settings Card: Two-Column Definition Layout */}
      <form onSubmit={handleSaveSettings} className="glass-card" style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "8px", boxShadow: "0 1px 3px rgba(15, 23, 42, 0.05)", overflow: "hidden" }}>
        
        {/* Section 1: Company & Plant */}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "24px", padding: "24px", borderBottom: "1px solid #CBD5E1" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <Building2 size={18} color="#1E3A8A" />
              <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Company & Factory Profile" : "कम्पनी तथा कारखाना विवरण (Company Profile)"}
              </h3>
            </div>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748B" }}>
              Company & Manufacturing Plant
            </div>
            <p style={{ fontSize: "12px", color: "#475569", marginTop: "8px", lineHeight: "1.4" }}>
              Permanent statutory registration, factory location, and official business entity credentials for invoice generation.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                {locale === "en" ? "Company Legal Name" : "कम्पनीको नाम (Company Legal Name)"}
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Permanent Account Number (PAN)
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <input
                    type="text"
                    value={panNumber}
                    readOnly
                    className="num-mono-bold"
                    style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#F1F5F9", color: "#1E3A8A" }}
                  />
                  <span style={{ fontSize: "11px", fontWeight: "700", background: "#EFF6FF", color: "#1E3A8A", border: "1px solid #BFDBFE", padding: "4px 8px", borderRadius: "4px", whiteSpace: "nowrap" }}>
                    IRD VERIFIED
                  </span>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Factory Plant Address" : "कारखाना ठेगाना (Factory Plant Address)"}
                </label>
                <input
                  type="text"
                  value={factoryAddress}
                  onChange={(e) => setFactoryAddress(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Sizing & Packaging Rules */}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "24px", padding: "24px", borderBottom: "1px solid #CBD5E1" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <Sliders size={18} color="#1E3A8A" />
              <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Sizing & Packaging Policy" : "साइज तथा प्याकिङ नीति (Sizing Policy)"}
              </h3>
            </div>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748B" }}>
              Sizing & Packaging Invariants
            </div>
            <p style={{ fontSize: "12px", color: "#475569", marginTop: "8px", lineHeight: "1.4" }}>
              Continental Paris Points sizing assortment, standard wholesale master carton multiplier, and core production alert thresholds.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                {locale === "en" ? "Standard Sizing Curve" : "साइज मानक (Standard Sizing Curve)"}
              </label>
              <input
                type="text"
                value={standardCurve}
                onChange={(e) => setStandardCurve(e.target.value)}
                style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Master Carton Multiplier" : "कार्टन गुणक (Master Carton Multiplier)"}
                </label>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <input
                    type="number"
                    value={cartonMultiplier}
                    onChange={(e) => setCartonMultiplier(e.target.value)}
                    className="num-mono"
                    style={{ width: "80px", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                  />
                  <span style={{ fontSize: "12.5px", color: "#475569" }}>
                    {locale === "en" ? "Pairs per Carton (12 Pairs = 1 Carton)" : "जोडी प्रति कार्टन (12 Pairs = 1 Carton)"}
                  </span>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Core Size Alert Thresholds" : "मुख्य साइजहरू (Core Size Alert Thresholds)"}
                </label>
                <input
                  type="text"
                  value={coreSizeAlert}
                  onChange={(e) => setCoreSizeAlert(e.target.value)}
                  className="num-mono"
                  style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Tax & Statutory Terms */}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "24px", padding: "24px", borderBottom: "1px solid #CBD5E1" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <Percent size={18} color="#1E3A8A" />
              <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Tax & Credit Policy" : "कर तथा वित्तीय नीति (Tax Policy)"}
              </h3>
            </div>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748B" }}>
              Tax & Statutory Terms
            </div>
            <p style={{ fontSize: "12px", color: "#475569", marginTop: "8px", lineHeight: "1.4" }}>
              Value Added Tax compliance rules for Nepal Inland Revenue Department (IRD), settlement aging terms, and default customer credit boundaries.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Value Added Tax (VAT) Rate
                </label>
                <input
                  type="text"
                  value={vatRate}
                  onChange={(e) => setVatRate(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {locale === "en" ? "Standard Credit Terms" : "भुक्तानी अवधि (Standard Credit Terms)"}
                </label>
                <input
                  type="text"
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                  style={{ width: "100%", padding: "8px 12px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                {locale === "en" ? "Default Customer Credit Ceiling (NPR)" : "सुरुवाती बक्यौता सीमा (Default Credit Ceiling - NPR)"}
              </label>
              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: "10px", top: "8px", fontSize: "12.5px", color: "#64748B" }}>
                  NPR
                </span>
                <input
                  type="text"
                  value={defaultCreditLimit}
                  onChange={(e) => setDefaultCreditLimit(e.target.value)}
                  className="num-mono"
                  style={{ width: "100%", padding: "8px 12px 8px 48px", fontSize: "13px", borderRadius: "4px", border: "1px solid #CBD5E1", background: "#FFFFFF", color: "#0F172A" }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Offline Storage & Sync */}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(240px, 1fr) 2fr", gap: "24px", padding: "24px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
              <HardDrive size={18} color="#1E3A8A" />
              <h3 style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A" }}>
                {locale === "en" ? "Sync & Local Device Cache" : "सिंक तथा स्थानीय क्यास (Sync & Local Cache)"}
              </h3>
            </div>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748B" }}>
              Offline Storage & Terminal Sync
            </div>
            <p style={{ fontSize: "12px", color: "#475569", marginTop: "8px", lineHeight: "1.4" }}>
              Client-side IndexedDB outbox queue status for continuous offline factory data entry and manual cache management.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "4px" }}>
              <div>
                <div style={{ fontSize: "12px", fontWeight: "600", color: "#64748B" }}>
                  IndexedDB Storage Status
                </div>
                <div style={{ fontSize: "13.5px", fontWeight: "700", color: "#0F172A", marginTop: "2px" }} className="num-mono">
                  livo_factory_offline_v1 (Active)
                </div>
              </div>
              <span style={{ fontSize: "11px", fontWeight: "700", background: "#DCFCE7", color: "#166534", border: "1px solid #BBF7D0", padding: "4px 8px", borderRadius: "4px" }}>
                HEALTHY
              </span>
            </div>

            {cacheNotice && (
              <div style={{ fontSize: "12.5px", color: "#047857", background: "#F0FDF4", border: "1px solid #BBF7D0", padding: "8px 12px", borderRadius: "4px" }}>
                {cacheNotice}
              </div>
            )}

            <div>
              <button
                type="button"
                onClick={handleClearCache}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#FFFFFF",
                  border: "1px solid #CBD5E1",
                  color: "#B45309",
                  padding: "8px 14px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "600",
                  cursor: "pointer",
                  transition: "background 0.15s ease"
                }}
              >
                <Trash2 size={14} /> {locale === "en" ? "Clear Local Outbox Drafts" : "Clear Local Outbox Drafts (क्यास खाली गर्नुहोस्)"}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Operational Section: Database Backup & Disaster Recovery */}
      <div className="glass-card" style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(15, 23, 42, 0.05)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", display: "flex", alignItems: "center", gap: "8px" }}>
              <Database size={18} color="#1E3A8A" />
              Database Backup & Cloud Replication (Backblaze B2 / R2)
            </h3>
            <p style={{ color: "#475569", fontSize: "13px", marginTop: "4px" }}>
              Automated nightly pg_dump snapshots with multi-cloud replication. Target RPO: ≤ 60m | Target RTO: ≤ 15m.
            </p>
          </div>

          <button
            type="button"
            id="btn-run-manual-backup"
            onClick={handleRunBackup}
            disabled={isBackingUp}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#FFFFFF",
              color: "#1E3A8A",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "8px 14px",
              fontSize: "12.5px",
              fontWeight: "600",
              cursor: isBackingUp ? "not-allowed" : "pointer"
            }}
          >
            <RefreshCw size={14} className={isBackingUp ? "animate-spin" : ""} />
            {isBackingUp ? "Running Backup..." : "Run Manual Database Backup Now"}
          </button>
        </div>

        {backupStatus && backupStatus.status === "failed" && (
          <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", color: "#991B1B", padding: "12px 16px", borderRadius: "4px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertTriangle size={18} color="#DC2626" />
            <div style={{ fontSize: "13px" }}>
              <strong>Backup Failure:</strong> {backupStatus.error_message || "Database dump or upload failed."}
            </div>
          </div>
        )}

        {backupStatus && backupStatus.status === "success" && (
          <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", color: "#166534", padding: "12px 16px", borderRadius: "4px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle2 size={18} color="#16A34A" />
            <div style={{ fontSize: "13px" }}>
              <strong>Latest Snapshot Verified:</strong> {backupStatus.file_name} ({Math.round((backupStatus.file_size_bytes || 0) / 1024)} KB) — {backupStatus.storage_destination}
            </div>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
          <div style={{ background: "#F8FAFC", padding: "14px", borderRadius: "4px", border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>Last Backup Status</div>
            <div style={{ fontSize: "14px", fontWeight: "700", marginTop: "4px", color: backupStatus?.status === "success" ? "#047857" : backupStatus?.status === "failed" ? "#BE123C" : "#64748B" }}>
              {backupStatus?.status ? backupStatus.status.toUpperCase() : "NO BACKUP RUN YET"}
            </div>
          </div>

          <div style={{ background: "#F8FAFC", padding: "14px", borderRadius: "4px", border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>Timestamp (UTC)</div>
            <div style={{ fontSize: "13px", fontWeight: "600", marginTop: "4px", color: "#0F172A" }} className="num-mono">
              {backupStatus?.timestamp ? new Date(backupStatus.timestamp).toLocaleString() : "N/A"}
            </div>
          </div>

          <div style={{ background: "#F8FAFC", padding: "14px", borderRadius: "4px", border: "1px solid #E2E8F0" }}>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase" }}>Destination</div>
            <div style={{ fontSize: "13px", fontWeight: "600", marginTop: "4px", color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {backupStatus?.storage_destination || "Local / Cloud B2"}
            </div>
          </div>
        </div>

        {backupMessage && (
          <div style={{ marginTop: "12px", fontSize: "13px", color: backupMessage.includes("failed") ? "#BE123C" : "#047857" }}>
            {backupMessage}
          </div>
        )}
      </div>

      {/* Diagnostics Download Section */}
      <div className="glass-card" style={{ background: "#FFFFFF", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "24px", boxShadow: "0 1px 3px rgba(15, 23, 42, 0.05)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", display: "flex", alignItems: "center", gap: "8px" }}>
              <ShieldCheck size={18} color="#047857" />
              {locale === "en" ? "One-Click Support Diagnostics" : "One-Click Support Diagnostics (प्रणाली निरीक्षण तथा सहयोग)"}
            </h3>
            <p style={{ color: "#475569", fontSize: "13px", marginTop: "4px", maxWidth: "680px" }}>
              Exports encrypted ZIP bundle containing structured JSON logs, database self-check results, and runtime memory profiles for technical support.
            </p>
          </div>

          <button
            type="button"
            id="btn-download-diagnostics"
            onClick={handleDownloadDiagnostics}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "#FFFFFF",
              color: "#0F172A",
              border: "1px solid #CBD5E1",
              borderRadius: "4px",
              padding: "8px 14px",
              fontSize: "12.5px",
              fontWeight: "600",
              cursor: "pointer"
            }}
          >
            <Download size={15} /> Send Diagnostics (Download ZIP)
          </button>
        </div>
      </div>
    </div>
  );
}
