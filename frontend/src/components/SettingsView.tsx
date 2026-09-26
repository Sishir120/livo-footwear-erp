"use client";

import React, { useState, useEffect } from "react";
import { Download, ShieldCheck, Database, Server, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";

export function SettingsView() {
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [backupStatus, setBackupStatus] = useState<any>(null);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);

  const fetchBackupStatus = () => {
    fetch("/api/v1/backup/status")
      .then((res) => res.json())
      .then((data) => setBackupStatus(data))
      .catch((err) => console.error(err));
  };

  useEffect(() => {
    fetch("/api/v1/health")
      .then((res) => res.json())
      .then((data) => setHealthInfo(data))
      .catch((err) => console.error(err));

    fetchBackupStatus();
  }, []);

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
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <h2 style={{ fontSize: "20px", fontWeight: "700" }}>System Settings & Diagnostics</h2>

      {/* Database Backup & Disaster Recovery Section */}
      <div className="glass-card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
          <Database size={20} color="#3b82f6" /> Database Backup & Storage Destination (Backblaze B2 / R2)
        </h3>
        <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "16px", maxWidth: "700px" }}>
          Automated nightly pg_dump backups with cloud storage replication per ARCHITECTURE.md §9. Failures are tracked and surfaced here.
        </p>

        {backupStatus && backupStatus.status === "failed" && (
          <div style={{ background: "rgba(244, 63, 94, 0.15)", border: "1px solid #f43f5e", color: "#fda4af", padding: "12px 16px", borderRadius: "8px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
            <AlertTriangle size={20} color="#f43f5e" />
            <div>
              <strong>Backup Failure Detected:</strong> {backupStatus.error_message || "Database dump or upload failed."}
            </div>
          </div>
        )}

        {backupStatus && backupStatus.status === "success" && (
          <div style={{ background: "rgba(52, 211, 153, 0.15)", border: "1px solid #34d399", color: "#6ee7b7", padding: "12px 16px", borderRadius: "8px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle size={20} color="#34d399" />
            <div>
              <strong>Latest Backup Successful:</strong> {backupStatus.file_name} ({Math.round((backupStatus.file_size_bytes || 0) / 1024)} KB) — {backupStatus.storage_destination}
            </div>
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "20px" }}>
          <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>Last Backup Status</div>
            <div style={{ fontSize: "16px", fontWeight: "700", marginTop: "4px", color: backupStatus?.status === "success" ? "#34d399" : backupStatus?.status === "failed" ? "#f43f5e" : "#94a3b8" }}>
              {backupStatus?.status ? backupStatus.status.toUpperCase() : "NO BACKUP RUN YET"}
            </div>
          </div>

          <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>Timestamp (UTC)</div>
            <div style={{ fontSize: "14px", fontWeight: "600", marginTop: "4px" }}>
              {backupStatus?.timestamp ? new Date(backupStatus.timestamp).toLocaleString() : "N/A"}
            </div>
          </div>

          <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>Destination</div>
            <div style={{ fontSize: "14px", fontWeight: "600", marginTop: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {backupStatus?.storage_destination || "Local / Cloud B2"}
            </div>
          </div>
        </div>

        {backupMessage && (
          <div style={{ marginBottom: "16px", fontSize: "14px", color: backupMessage.includes("failed") ? "#f43f5e" : "#34d399" }}>
            {backupMessage}
          </div>
        )}

        <button className="btn-primary" onClick={handleRunBackup} disabled={isBackingUp} style={{ padding: "10px 20px" }}>
          <RefreshCw size={16} className={isBackingUp ? "animate-spin" : ""} /> {isBackingUp ? "Running Backup..." : "Run Manual Database Backup Now"}
        </button>
      </div>

      {/* System Status Card */}
      <div className="glass-card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "16px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
          <Server size={20} color="#3b82f6" /> Application & Database Self-Check Status
        </h3>

        {healthInfo ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "12px", color: "#94a3b8" }}>Software Name</div>
              <div style={{ fontSize: "16px", fontWeight: "700", marginTop: "4px" }}>{healthInfo.app_name}</div>
            </div>

            <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "12px", color: "#94a3b8" }}>Version</div>
              <div style={{ fontSize: "16px", fontWeight: "700", marginTop: "4px", color: "#3b82f6" }}>v{healthInfo.version}</div>
            </div>

            <div style={{ background: "rgba(15, 23, 42, 0.5)", padding: "16px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
              <div style={{ fontSize: "12px", color: "#94a3b8" }}>PostgreSQL Self-Check</div>
              <div style={{ fontSize: "16px", fontWeight: "700", marginTop: "4px", color: healthInfo.database === "healthy" ? "#34d399" : "#f43f5e" }}>
                {healthInfo.database.toUpperCase()}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ color: "#94a3b8" }}>Loading self-check diagnostics...</div>
        )}
      </div>

      {/* Diagnostics Download Section */}
      <div className="glass-card" style={{ padding: "24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px", color: "#f8fafc", display: "flex", alignItems: "center", gap: "8px" }}>
          <ShieldCheck size={20} color="#34d399" /> One-Click Support Diagnostics
        </h3>
        <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "20px", maxWidth: "600px" }}>
          If you encounter any unexpected behavior, click the button below to generate a zip file containing system diagnostics, structured JSON logs, and DB self-check results to send to technical support.
        </p>

        <button className="btn-primary" onClick={handleDownloadDiagnostics} style={{ padding: "12px 24px" }}>
          <Download size={18} /> Send Diagnostics (Download ZIP Bundle)
        </button>
      </div>
    </div>
  );
}
