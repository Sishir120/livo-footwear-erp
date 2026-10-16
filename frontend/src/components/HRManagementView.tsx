"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  Search,
  Plus,
  RefreshCw,
  Download,
  Calendar,
  Clock,
  CreditCard,
  FileText,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  X,
  Phone,
  ArrowUpRight,
  ArrowDownLeft,
  DollarSign,
  TrendingUp,
  SlidersHorizontal,
  ChevronRight,
  Camera,
  Shield,
  ShieldCheck,
  LayoutGrid,
  List,
  MapPin,
  UserCheck,
  UserX,
  Upload,
  Trash2,
  Eye
} from "lucide-react";
import { fromPaisa, toPaisa, TABULAR_NUMS_STYLE } from "@/lib/currency";
import { useLocale } from "@/context/LocaleContext";
import { NepaliDatePicker } from "./NepaliDatePicker";
import { getTodayAd } from "@/lib/nepaliDate";

interface HRManagementViewProps {
  userRole: string;
}

interface CurrentMonthHours {
  month_year: string;
  total_working_hours: number;
  overtime_hours: number;
  gross_pay_paisa: number;
  advance_deduction_paisa: number;
  net_paid_paisa: number;
  status: string;
}

interface Worker {
  id: number;
  worker_code: string;
  name: string;
  join_date: string;
  pay_type: "SALARY" | "WAGE";
  basic_rate_paisa?: number;
  phone: string | null;
  photo_url?: string | null;
  temporary_address?: string | null;
  permanent_address?: string | null;
  is_active: boolean;
  inactive_date?: string | null;
  inactive_reason?: string | null;
  has_citizenship_doc?: boolean;
  citizenship_doc_name?: string | null;
  created_at: string;
  outstanding_advance_paisa?: number;
  current_month?: CurrentMonthHours | null;
}

interface AdvanceRecord {
  id: number;
  worker_id: number;
  amount_paisa: number;
  entry_type: "ISSUED" | "RECOVERED";
  date: string;
  notes: string | null;
  actor_id: number;
  actor_name?: string | null;
  created_at: string;
}

interface MonthlyRecord {
  id: number;
  worker_id: number;
  month_year: string;
  total_working_hours: number;
  overtime_hours: number;
  gross_pay_paisa: number;
  advance_deduction_paisa: number;
  net_paid_paisa: number;
  paid_date: string | null;
  payment_method: string | null;
  status: string;
  created_at: string;
}

export function HRManagementView({ userRole }: HRManagementViewProps) {
  const { isNepali, t } = useLocale();
  const isViewer = userRole === "viewer";

  const [loading, setLoading] = useState(true);
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<"active" | "inactive" | "all">("active");
  const [payTypeFilter, setPayTypeFilter] = useState<"ALL" | "SALARY" | "WAGE">("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  // Modals state
  const [showAddWorkerModal, setShowAddWorkerModal] = useState(false);
  const [showAdvanceModal, setShowAdvanceModal] = useState(false);
  const [showPayrollModal, setShowPayrollModal] = useState(false);
  const [selectedWorkerForHistory, setSelectedWorkerForHistory] = useState<Worker | null>(null);

  // View Mode
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");

  // Status transition confirmation modal state
  const [statusWorker, setStatusWorker] = useState<Worker | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [statusInactiveDate, setStatusInactiveDate] = useState(() => getTodayAd());
  const [submittingStatus, setSubmittingStatus] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  // Worker Photo modal state
  const [photoWorker, setPhotoWorker] = useState<Worker | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [submittingPhoto, setSubmittingPhoto] = useState(false);
  const [photoError, setPhotoError] = useState<string | null>(null);

  // Confidential Citizenship Document modal state (Admin only)
  const [citWorker, setCitWorker] = useState<Worker | null>(null);
  const [citFile, setCitFile] = useState<File | null>(null);
  const [submittingCit, setSubmittingCit] = useState(false);
  const [citError, setCitError] = useState<string | null>(null);

  // Add Worker Form State
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newJoinDate, setNewJoinDate] = useState(() => getTodayAd());
  const [newPayType, setNewPayType] = useState<"SALARY" | "WAGE">("SALARY");
  const [newRateNpr, setNewRateNpr] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newTempAddress, setNewTempAddress] = useState("");
  const [newPermAddress, setNewPermAddress] = useState("");
  const [submittingWorker, setSubmittingWorker] = useState(false);
  const [workerFormError, setWorkerFormError] = useState<string | null>(null);

  // Advance Form State
  const [advanceWorkerId, setAdvanceWorkerId] = useState<number | "">("");
  const [advanceType, setAdvanceType] = useState<"ISSUED" | "RECOVERED">("ISSUED");
  const [advanceAmountNpr, setAdvanceAmountNpr] = useState("");
  const [advanceDate, setAdvanceDate] = useState(() => getTodayAd());
  const [advanceNotes, setAdvanceNotes] = useState("");
  const [submittingAdvance, setSubmittingAdvance] = useState(false);
  const [advanceFormError, setAdvanceFormError] = useState<string | null>(null);

  // Payroll Form State
  const [payrollWorkerId, setPayrollWorkerId] = useState<number | "">("");
  const [payrollMonthYear, setPayrollMonthYear] = useState(() => {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    return `${d.getFullYear()}-${mm}`;
  });
  const [payrollHours, setPayrollHours] = useState<string>("0");
  const [payrollOtHours, setPayrollOtHours] = useState<string>("0");
  const [payrollAdvanceDeductionNpr, setPayrollAdvanceDeductionNpr] = useState<string>("");
  const [payrollPaymentMethod, setPayrollPaymentMethod] = useState<"CASH" | "BANK">("CASH");
  const [payrollMarkPaid, setPayrollMarkPaid] = useState(true);
  const [submittingPayroll, setSubmittingPayroll] = useState(false);
  const [payrollFormError, setPayrollFormError] = useState<string | null>(null);

  // History Drawer State
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyAdvances, setHistoryAdvances] = useState<AdvanceRecord[]>([]);
  const [historyMonthly, setHistoryMonthly] = useState<MonthlyRecord[]>([]);
  const [historyOutstandingPaisa, setHistoryOutstandingPaisa] = useState(0);

  // Fetch Workers Directory
  const fetchWorkers = async () => {
    setLoading(true);
    setError(null);
    try {
      let url = `/api/v1/hr/workers?status=${statusFilter}`;
      if (payTypeFilter !== "ALL") {
        url += `&pay_type=${payTypeFilter}`;
      }
      if (searchTerm.trim()) {
        url += `&search=${encodeURIComponent(searchTerm.trim())}`;
      }
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(`Failed to load workers: ${res.statusText}`);
      }
      const data = await res.json();
      setWorkers(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch workers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
  }, [statusFilter, payTypeFilter]);

  // Load Worker History
  const openWorkerHistory = async (worker: Worker) => {
    setSelectedWorkerForHistory(worker);
    setHistoryLoading(true);
    try {
      const res = await fetch(`/api/v1/hr/workers/${worker.id}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistoryAdvances(data.advances || []);
        setHistoryMonthly(data.monthly_records || []);
        setHistoryOutstandingPaisa(data.outstanding_advance_paisa || 0);
      }
    } catch (err) {
      console.error("Failed to load worker history", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Helpers
  const getInitials = (name: string) => {
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const getAvatarColor = (nameOrId: string | number) => {
    const str = String(nameOrId || "W");
    const colors = [
      "#2563EB", "#7C3AED", "#DB2777", "#D97706", "#059669",
      "#0891B2", "#4F46E5", "#EA580C", "#0D9488", "#475569"
    ];
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    return colors[Math.abs(hash) % colors.length];
  };

  const openStatusModal = (worker: Worker) => {
    if (isViewer) return;
    setStatusWorker(worker);
    setStatusReason("");
    setStatusInactiveDate(getTodayAd());
    setStatusError(null);
  };

  const openPhotoModal = (worker: Worker) => {
    if (isViewer) return;
    setPhotoWorker(worker);
    setPhotoFile(null);
    setPhotoError(null);
  };

  const openCitizenshipModal = (worker: Worker) => {
    if (userRole !== "admin") return;
    setCitWorker(worker);
    setCitFile(null);
    setCitError(null);
  };

  // Status Confirmation Submission
  const handleConfirmStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer || !statusWorker) return;
    setStatusError(null);
    setSubmittingStatus(true);
    try {
      const res = await fetch(`/api/v1/hr/workers/${statusWorker.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_active: !statusWorker.is_active,
          inactive_reason: !statusWorker.is_active ? (statusReason.trim() || "Deactivated") : null,
          inactive_date: !statusWorker.is_active ? statusInactiveDate : null
        })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to update worker status");
      }
      setStatusWorker(null);
      fetchWorkers();
    } catch (err: any) {
      setStatusError(err.message || "Failed to update status");
    } finally {
      setSubmittingStatus(false);
    }
  };

  // Photo Upload Submission
  const handleUploadPhoto = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer || !photoWorker || !photoFile) return;
    setPhotoError(null);
    setSubmittingPhoto(true);
    try {
      const formData = new FormData();
      formData.append("file", photoFile);
      const res = await fetch(`/api/v1/hr/workers/${photoWorker.id}/photo`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload photograph");
      }
      setPhotoWorker(null);
      setPhotoFile(null);
      fetchWorkers();
    } catch (err: any) {
      setPhotoError(err.message || "Failed to upload photo");
    } finally {
      setSubmittingPhoto(false);
    }
  };

  // Photo Delete
  const handleDeletePhoto = async () => {
    if (isViewer || !photoWorker) return;
    if (!window.confirm(isNepali ? "के तपाईं यो फोटो मेटाउन निश्चित हुनुहुन्छ?" : "Are you sure you want to remove this photograph?")) return;
    setSubmittingPhoto(true);
    try {
      const res = await fetch(`/api/v1/hr/workers/${photoWorker.id}/photo`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error("Failed to delete photograph");
      setPhotoWorker(null);
      setPhotoFile(null);
      fetchWorkers();
    } catch (err: any) {
      setPhotoError(err.message || "Failed to delete photo");
    } finally {
      setSubmittingPhoto(false);
    }
  };

  // Citizenship Upload Submission
  const handleUploadCitizenship = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userRole !== "admin" || !citWorker || !citFile) return;
    setCitError(null);
    setSubmittingCit(true);
    try {
      const formData = new FormData();
      formData.append("file", citFile);
      const res = await fetch(`/api/v1/hr/workers/${citWorker.id}/citizenship`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload citizenship document");
      }
      setCitWorker(null);
      setCitFile(null);
      fetchWorkers();
    } catch (err: any) {
      setCitError(err.message || "Failed to upload citizenship document");
    } finally {
      setSubmittingCit(false);
    }
  };

  // Citizenship Delete
  const handleDeleteCitizenship = async () => {
    if (userRole !== "admin" || !citWorker) return;
    if (!window.confirm(isNepali ? "के तपाईं नागरिकता कागजात मेटाउन निश्चित हुनुहुन्छ?" : "Are you sure you want to permanently delete this citizenship document?")) return;
    setSubmittingCit(true);
    try {
      const res = await fetch(`/api/v1/hr/workers/${citWorker.id}/citizenship`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error("Failed to delete citizenship document");
      setCitWorker(null);
      setCitFile(null);
      fetchWorkers();
    } catch (err: any) {
      setCitError(err.message || "Failed to delete citizenship document");
    } finally {
      setSubmittingCit(false);
    }
  };

  // Submit Add Worker
  const handleCreateWorker = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;
    setWorkerFormError(null);
    setSubmittingWorker(true);

    try {
      const ratePaisa = toPaisa(newRateNpr);
      if (ratePaisa <= 0) {
        throw new Error(isNepali ? "कृपया मान्य तलब वा ज्याला दर प्रविष्ट गर्नुहोस्" : "Please enter a valid basic rate > 0");
      }

      const res = await fetch("/api/v1/hr/workers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          worker_code: newCode.trim().toUpperCase(),
          name: newName.trim(),
          join_date: newJoinDate,
          pay_type: newPayType,
          basic_rate_paisa: ratePaisa,
          phone: newPhone.trim() || null,
          temporary_address: newTempAddress.trim() || null,
          permanent_address: newPermAddress.trim() || null
        })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to create worker profile");
      }

      setShowAddWorkerModal(false);
      setNewCode("");
      setNewName("");
      setNewRateNpr("");
      setNewPhone("");
      setNewTempAddress("");
      setNewPermAddress("");
      fetchWorkers();
    } catch (err: any) {
      setWorkerFormError(err.message || "Failed to create worker");
    } finally {
      setSubmittingWorker(false);
    }
  };

  // Submit Advance
  const handleRecordAdvance = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;
    setAdvanceFormError(null);
    setSubmittingAdvance(true);

    try {
      if (!advanceWorkerId) {
        throw new Error(isNepali ? "कृपया कामदार छान्नुहोस्" : "Please select a worker");
      }
      const amountPaisa = toPaisa(advanceAmountNpr);
      if (amountPaisa <= 0) {
        throw new Error(isNepali ? "कृपया मान्य पेश्की रकम प्रविष्ट गर्नुहोस्" : "Please enter a valid amount > 0");
      }

      const res = await fetch("/api/v1/hr/advances", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          worker_id: Number(advanceWorkerId),
          amount_paisa: amountPaisa,
          entry_type: advanceType,
          date: advanceDate,
          notes: advanceNotes.trim() || null
        })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to record advance");
      }

      setShowAdvanceModal(false);
      setAdvanceAmountNpr("");
      setAdvanceNotes("");
      fetchWorkers();
      if (selectedWorkerForHistory && selectedWorkerForHistory.id === advanceWorkerId) {
        openWorkerHistory(selectedWorkerForHistory);
      }
    } catch (err: any) {
      setAdvanceFormError(err.message || "Failed to record advance");
    } finally {
      setSubmittingAdvance(false);
    }
  };

  // Submit Monthly Payroll
  const handleRecordPayroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isViewer) return;
    setPayrollFormError(null);
    setSubmittingPayroll(true);

    try {
      if (!payrollWorkerId) {
        throw new Error(isNepali ? "कृपया कामदार छान्नुहोस्" : "Please select a worker");
      }

      const twh = parseFloat(payrollHours) || 0;
      const ot = parseFloat(payrollOtHours) || 0;
      const advDeductionPaisa = payrollAdvanceDeductionNpr !== "" ? toPaisa(payrollAdvanceDeductionNpr) : null;

      const res = await fetch("/api/v1/hr/monthly-payroll", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          worker_id: Number(payrollWorkerId),
          month_year: payrollMonthYear,
          total_working_hours: twh,
          overtime_hours: ot,
          advance_deduction_paisa: advDeductionPaisa,
          payment_method: payrollPaymentMethod,
          mark_as_paid: payrollMarkPaid
        })
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to process payroll");
      }

      setShowPayrollModal(false);
      fetchWorkers();
      if (selectedWorkerForHistory && selectedWorkerForHistory.id === payrollWorkerId) {
        openWorkerHistory(selectedWorkerForHistory);
      }
    } catch (err: any) {
      setPayrollFormError(err.message || "Failed to process payroll");
    } finally {
      setSubmittingPayroll(false);
    }
  };

  // Quick Open Payroll for Specific Worker
  const openPayrollForWorker = (worker: Worker) => {
    setPayrollWorkerId(worker.id);
    setPayrollHours(String(worker.current_month?.total_working_hours || (worker.pay_type === "SALARY" ? 208 : 0)));
    setPayrollOtHours(String(worker.current_month?.overtime_hours || 0));
    setPayrollAdvanceDeductionNpr(fromPaisa(worker.outstanding_advance_paisa || 0, false));
    setPayrollFormError(null);
    setShowPayrollModal(true);
  };

  // Quick Open Advance for Specific Worker
  const openAdvanceForWorker = (worker: Worker) => {
    setAdvanceWorkerId(worker.id);
    setAdvanceType("ISSUED");
    setAdvanceAmountNpr("");
    setAdvanceNotes("");
    setAdvanceFormError(null);
    setShowAdvanceModal(true);
  };

  // Real-time Payroll Calculation Preview in Modal
  const selectedPayrollWorker = workers.find((w) => w.id === payrollWorkerId);
  const previewGrossPaisa = (() => {
    if (!selectedPayrollWorker) return 0;
    const twh = parseFloat(payrollHours) || 0;
    const ot = parseFloat(payrollOtHours) || 0;
    if (selectedPayrollWorker.pay_type === "SALARY") {
      const basic = selectedPayrollWorker.basic_rate_paisa || 0;
      const hourlyOTRate = (basic / 208) * 1.5;
      return Math.round(basic + (ot * hourlyOTRate));
    } else {
      const hourly = selectedPayrollWorker.basic_rate_paisa || 0;
      return Math.round((twh * hourly) + (ot * hourly * 1.5));
    }
  })();

  const previewAdvanceDeductionPaisa = (() => {
    if (!selectedPayrollWorker) return 0;
    const workerAdv = selectedPayrollWorker.outstanding_advance_paisa || 0;
    if (payrollAdvanceDeductionNpr === "") {
      return Math.min(previewGrossPaisa, workerAdv);
    }
    return Math.min(toPaisa(payrollAdvanceDeductionNpr), workerAdv);
  })();

  const previewNetPaidPaisa = Math.max(0, previewGrossPaisa - previewAdvanceDeductionPaisa);

  // Aggregated KPI Stats
  const activeCount = workers.filter((w) => w.is_active).length;
  const totalAdvancesPaisa = workers.reduce((sum, w) => sum + (w.outstanding_advance_paisa || 0), 0);
  const totalHoursThisMonth = workers.reduce((sum, w) => sum + (Number(w.current_month?.total_working_hours) || 0), 0);
  const totalOtHoursThisMonth = workers.reduce((sum, w) => sum + (Number(w.current_month?.overtime_hours) || 0), 0);
  const salariedCount = workers.filter((w) => w.pay_type === "SALARY").length;
  const wageCount = workers.filter((w) => w.pay_type === "WAGE").length;

  // Filtered workers for search
  const filteredWorkers = workers.filter((w) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      w.worker_code.toLowerCase().includes(term) ||
      w.name.toLowerCase().includes(term) ||
      (w.phone && w.phone.includes(term))
    );
  });

  const handleExportCSV = () => {
    if (!filteredWorkers.length) return;
    const headers = [
      "Worker Code",
      "Name",
      "Join Date",
      "Pay Type",
      "Basic Rate NPR",
      "Total Hours (TWH)",
      "Overtime (OT)",
      "Advance Due NPR",
      "Status",
      "Phone"
    ];
    const rows = filteredWorkers.map((w) => [
      `"${w.worker_code}"`,
      `"${w.name}"`,
      w.join_date,
      w.pay_type,
      w.basic_rate_paisa !== undefined ? fromPaisa(w.basic_rate_paisa, false) : "[RESTRICTED]",
      w.current_month?.total_working_hours || 0,
      w.current_month?.overtime_hours || 0,
      w.outstanding_advance_paisa !== undefined ? fromPaisa(w.outstanding_advance_paisa, false) : "[RESTRICTED]",
      w.is_active ? "ACTIVE" : "INACTIVE",
      `"${w.phone || ""}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Worker_HR_Ledger_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ padding: "24px 32px", maxWidth: "1600px", margin: "0 auto" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "20px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
              {t("hr_title")}
            </h1>
            <span
              style={{
                fontSize: "11px",
                fontWeight: "700",
                background: "#E0E7FF",
                color: "#1E3A8A",
                padding: "2px 8px",
                borderRadius: "3px"
              }}
            >
              {isNepali ? "५०+ कामदार व्यवस्थापन" : "50+ FACTORY WORKERS"}
            </span>
          </div>
          <p style={{ fontSize: "12.5px", color: "#475569", marginTop: "4px", margin: 0 }}>
            {t("hr_desc")}
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={fetchWorkers}
            disabled={loading}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
            title="Refresh Worker List"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            <span>{isNepali ? "ताजा गर्नुहोस्" : "Refresh"}</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="pagination-btn"
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Download size={13} />
            <span>Export CSV</span>
          </button>

          {/* Mutation Buttons - Hidden in Viewer Role */}
          {!isViewer && (
            <>
              <button
                onClick={() => {
                  setAdvanceWorkerId("");
                  setAdvanceType("ISSUED");
                  setAdvanceAmountNpr("");
                  setAdvanceNotes("");
                  setAdvanceFormError(null);
                  setShowAdvanceModal(true);
                }}
                style={{
                  background: "#475569",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  fontSize: "12.5px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
              >
                <DollarSign size={14} />
                <span>{t("give_advance")}</span>
              </button>

              <button
                onClick={() => {
                  if (workers.length > 0) {
                    setPayrollWorkerId(workers[0].id);
                  }
                  setPayrollFormError(null);
                  setShowPayrollModal(true);
                }}
                style={{
                  background: "#047857",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  fontSize: "12.5px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
              >
                <Clock size={14} />
                <span>{t("record_payroll")}</span>
              </button>

              <button
                onClick={() => {
                  setWorkerFormError(null);
                  setShowAddWorkerModal(true);
                }}
                style={{
                  background: "#1E3A8A",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: "4px",
                  fontSize: "12.5px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
              >
                <Plus size={14} />
                <span>{t("add_worker")}</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "14px", marginBottom: "20px" }}>
        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {isNepali ? "कुल सक्रिय कामदार" : "ACTIVE WORKERS"}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#0F172A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {activeCount} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>/ {workers.length}</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {salariedCount} {isNepali ? "मासिक" : "Salaried"} • {wageCount} {isNepali ? "ज्याला" : "Wage"}
          </div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#B45309", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {t("outstanding_advance")}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: isViewer ? "#64748B" : (totalAdvancesPaisa > 0 ? "#DC2626" : "#059669"), marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {isViewer ? "[Restricted]" : `NPR ${fromPaisa(totalAdvancesPaisa)}`}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "तलब भुक्तानीमा स्वतः कट्टा हुने" : "Auto-deducted during payroll"}
          </div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#2563EB", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {isNepali ? "हालको महिना कुल काम घण्टा" : "CURRENT MONTH HOURS (TWH)"}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#1E3A8A", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {totalHoursThisMonth.toFixed(1)} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>hrs</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "कारखाना नियमित घण्टा" : "Floor production hours"}
          </div>
        </div>

        <div className="stat-card" style={{ background: "#FFFFFF", padding: "14px 18px", border: "1px solid #E2E8F0", borderRadius: "6px" }}>
          <div style={{ fontSize: "11px", fontWeight: "600", color: "#7C3AED", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {isNepali ? "हालको महिना ओभरटाइम" : "CURRENT MONTH OVERTIME (OT)"}
          </div>
          <div style={{ fontSize: "22px", fontWeight: "700", color: "#7C3AED", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            {totalOtHoursThisMonth.toFixed(1)} <span style={{ fontSize: "13px", fontWeight: "400", color: "#64748B" }}>hrs</span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "3px" }}>
            {isNepali ? "१.५ गुणा अतिरिक्त भुक्तानी दर" : "Calculated at 1.5x basic rate"}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", padding: "12px 16px", marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Status Tabs */}
          <div style={{ display: "flex", border: "1px solid #CBD5E1", borderRadius: "4px", overflow: "hidden" }}>
            <button
              onClick={() => setStatusFilter("active")}
              style={{
                padding: "6px 14px",
                fontSize: "12px",
                fontWeight: "600",
                background: statusFilter === "active" ? "#1E3A8A" : "#FFFFFF",
                color: statusFilter === "active" ? "#FFFFFF" : "#475569",
                border: "none",
                cursor: "pointer"
              }}
            >
              {t("active")}
            </button>
            <button
              onClick={() => setStatusFilter("inactive")}
              style={{
                padding: "6px 14px",
                fontSize: "12px",
                fontWeight: "600",
                background: statusFilter === "inactive" ? "#1E3A8A" : "#FFFFFF",
                color: statusFilter === "inactive" ? "#FFFFFF" : "#475569",
                border: "none",
                borderLeft: "1px solid #CBD5E1",
                borderRight: "1px solid #CBD5E1",
                cursor: "pointer"
              }}
            >
              {t("inactive")}
            </button>
            <button
              onClick={() => setStatusFilter("all")}
              style={{
                padding: "6px 14px",
                fontSize: "12px",
                fontWeight: "600",
                background: statusFilter === "all" ? "#1E3A8A" : "#FFFFFF",
                color: statusFilter === "all" ? "#FFFFFF" : "#475569",
                border: "none",
                cursor: "pointer"
              }}
            >
              {t("all")}
            </button>
          </div>

          {/* Pay Type Filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "12px", color: "#64748B", fontWeight: "500" }}>{t("pay_type")}:</span>
            <select
              value={payTypeFilter}
              onChange={(e) => setPayTypeFilter(e.target.value as any)}
              style={{
                padding: "5px 10px",
                fontSize: "12px",
                borderRadius: "4px",
                border: "1px solid #CBD5E1",
                background: "#FFFFFF",
                color: "#0F172A",
                outline: "none"
              }}
            >
              <option value="ALL">{t("all")}</option>
              <option value="SALARY">{t("salary_type")}</option>
              <option value="WAGE">{t("wage_type")}</option>
            </select>
          </div>
        </div>

        {/* Right side: View Mode Toggle & Search Input */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* View Mode Toggle: Cards vs Table */}
          <div style={{ display: "flex", border: "1px solid #CBD5E1", borderRadius: "4px", overflow: "hidden" }}>
            <button
              type="button"
              onClick={() => setViewMode("cards")}
              title="Worker Cards View"
              style={{
                padding: "6px 11px",
                fontSize: "12px",
                fontWeight: "600",
                background: viewMode === "cards" ? "#1E3A8A" : "#FFFFFF",
                color: viewMode === "cards" ? "#FFFFFF" : "#475569",
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              <LayoutGrid size={13} />
              <span>{isNepali ? "कार्ड" : "Cards"}</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              title="Worker Table View"
              style={{
                padding: "6px 11px",
                fontSize: "12px",
                fontWeight: "600",
                background: viewMode === "table" ? "#1E3A8A" : "#FFFFFF",
                color: viewMode === "table" ? "#FFFFFF" : "#475569",
                border: "none",
                borderLeft: "1px solid #CBD5E1",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "4px"
              }}
            >
              <List size={13} />
              <span>{isNepali ? "तालिका" : "Table"}</span>
            </button>
          </div>

          {/* Search Input */}
          <div style={{ position: "relative", minWidth: "240px" }}>
            <Search size={14} color="#94A3B8" style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              placeholder={isNepali ? "नाम, कोड वा फोन खोज्नुहोस्..." : "Search code, name, phone..."}
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
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "10px 14px", borderRadius: "6px", color: "#B91C1C", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "40px", textAlign: "center", color: "#64748B" }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 10px" }} />
          <div style={{ fontWeight: "600" }}>Loading worker profiles & payroll ledger...</div>
        </div>
      ) : filteredWorkers.length === 0 ? (
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "40px", textAlign: "center", color: "#64748B" }}>
          <Users size={36} style={{ margin: "0 auto 10px", opacity: 0.5 }} />
          <div style={{ fontWeight: "700", fontSize: "15px", color: "#0F172A" }}>No workers found</div>
          <div style={{ fontSize: "12px", marginTop: "4px" }}>
            {searchTerm ? "Try adjusting your search or filters" : "Add your first factory worker profile"}
          </div>
        </div>
      ) : viewMode === "cards" ? (
        /* ==================================================================== */
        /* WORKER CARDS GRID VIEW                                               */
        /* ==================================================================== */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px" }}>
          {filteredWorkers.map((worker) => {
            const hasAdvance = (worker.outstanding_advance_paisa || 0) > 0;
            const initials = getInitials(worker.name);
            const avatarBg = getAvatarColor(worker.name);

            return (
              <div
                key={worker.id}
                style={{
                  background: "#FFFFFF",
                  border: `1px solid ${worker.is_active ? "#E2E8F0" : "#CBD5E1"}`,
                  borderRadius: "8px",
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                  opacity: worker.is_active ? 1 : 0.82,
                  transition: "all 0.15s ease"
                }}
              >
                {/* Header: Avatar, Worker Code, Name, Status */}
                <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                  {/* Photo or Initials Avatar */}
                  <div
                    style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "50%",
                      overflow: "hidden",
                      flexShrink: 0,
                      background: avatarBg,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#FFFFFF",
                      fontWeight: "700",
                      fontSize: "16px",
                      border: "2px solid #E2E8F0"
                    }}
                  >
                    {worker.photo_url ? (
                      <img
                        src={worker.photo_url}
                        alt={worker.name}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={(e) => {
                          (e.target as any).style.display = "none";
                        }}
                      />
                    ) : (
                      <span>{initials}</span>
                    )}
                  </div>

                  {/* Worker Identity */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: "700",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          background: "#EFF6FF",
                          color: "#1E40AF",
                          ...TABULAR_NUMS_STYLE
                        }}
                      >
                        {worker.worker_code}
                      </span>
                      <span
                        style={{
                          fontSize: "10.5px",
                          fontWeight: "700",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background: worker.is_active ? "#DCFCE7" : "#FEE2E2",
                          color: worker.is_active ? "#15803D" : "#991B1B",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px"
                        }}
                      >
                        <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: worker.is_active ? "#15803D" : "#991B1B" }} />
                        {worker.is_active ? t("active") : t("inactive")}
                      </span>
                    </div>

                    <h4 style={{ margin: "4px 0 2px 0", fontSize: "14px", fontWeight: "700", color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {worker.name}
                    </h4>

                    {worker.phone && (
                      <div style={{ fontSize: "11.5px", color: "#64748B", display: "flex", alignItems: "center", gap: "4px" }}>
                        <Phone size={11} />
                        <span>{worker.phone}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Deactivation Banner if inactive */}
                {!worker.is_active && (
                  <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "4px", padding: "6px 8px", fontSize: "11px", color: "#991B1B" }}>
                    <div style={{ fontWeight: "600" }}>
                      Inactive Date: {worker.inactive_date || "Recorded"}
                    </div>
                    {worker.inactive_reason && (
                      <div style={{ fontSize: "10.5px", marginTop: "2px", opacity: 0.9 }}>
                        Reason: {worker.inactive_reason}
                      </div>
                    )}
                  </div>
                )}

                {/* Compensation & Working Hours */}
                <div style={{ background: "#F8FAFC", borderRadius: "6px", padding: "10px", fontSize: "12px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <div style={{ fontSize: "10.5px", color: "#64748B", fontWeight: "500" }}>{t("pay_type")} & Rate</div>
                    <div style={{ fontWeight: "700", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                      {worker.basic_rate_paisa !== undefined && worker.basic_rate_paisa !== null ? (
                        <>
                          NPR {fromPaisa(worker.basic_rate_paisa)}
                          <span style={{ fontSize: "10px", color: "#64748B", fontWeight: "400", marginLeft: "2px" }}>
                            {worker.pay_type === "SALARY" ? "/mo" : "/hr"}
                          </span>
                        </>
                      ) : (
                        <span style={{ fontSize: "11px", color: "#94A3B8", fontStyle: "italic" }}>[Restricted]</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <div style={{ fontSize: "10.5px", color: "#64748B", fontWeight: "500" }}>Current Month Hours</div>
                    <div style={{ fontWeight: "600", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                      {Number(worker.current_month?.total_working_hours || 0).toFixed(1)} hrs
                      {worker.current_month && Number(worker.current_month.overtime_hours || 0) > 0 && (
                        <span style={{ color: "#7C3AED", fontWeight: "700", marginLeft: "4px" }}>
                          (+{Number(worker.current_month.overtime_hours || 0).toFixed(1)} OT)
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Addresses */}
                  {(worker.temporary_address || worker.permanent_address) && (
                    <div style={{ gridColumn: "span 2", borderTop: "1px solid #E2E8F0", paddingTop: "6px", marginTop: "2px" }}>
                      <div style={{ fontSize: "10.5px", color: "#64748B", display: "flex", alignItems: "center", gap: "4px" }}>
                        <MapPin size={11} color="#64748B" />
                        <span>
                          {worker.temporary_address ? `Temp: ${worker.temporary_address}` : ""}
                          {worker.temporary_address && worker.permanent_address ? " • " : ""}
                          {worker.permanent_address ? `Perm: ${worker.permanent_address}` : ""}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Advance Due & Citizenship Document Status */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px", fontSize: "11px" }}>
                  <div>
                    {worker.outstanding_advance_paisa !== undefined && worker.outstanding_advance_paisa !== null ? (
                      hasAdvance ? (
                        <span style={{ background: "#FEF2F2", color: "#DC2626", border: "1px solid #FCA5A5", padding: "2px 6px", borderRadius: "4px", fontWeight: "700", ...TABULAR_NUMS_STYLE }}>
                          Adv Due: NPR {fromPaisa(worker.outstanding_advance_paisa)}
                        </span>
                      ) : (
                        <span style={{ color: "#059669", fontWeight: "500" }}>Adv Due: NPR 0.00</span>
                      )
                    ) : (
                      <span style={{ color: "#94A3B8", fontStyle: "italic" }}>Adv: [Restricted]</span>
                    )}
                  </div>

                  {userRole === "admin" && (
                    <div>
                      {worker.has_citizenship_doc ? (
                        <span style={{ display: "flex", alignItems: "center", gap: "3px", color: "#15803D", fontWeight: "600", fontSize: "11px" }}>
                          <ShieldCheck size={12} color="#15803D" />
                          <span>Citizenship Verified</span>
                        </span>
                      ) : (
                        <span style={{ display: "flex", alignItems: "center", gap: "3px", color: "#94A3B8", fontSize: "11px" }}>
                          <Shield size={12} color="#94A3B8" />
                          <span>No Citizenship Doc</span>
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div style={{ borderTop: "1px solid #E2E8F0", paddingTop: "10px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px", marginTop: "auto" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    <button
                      onClick={() => openWorkerHistory(worker)}
                      title="View Profile & Ledger History"
                      style={{
                        background: "#F1F5F9",
                        border: "1px solid #CBD5E1",
                        borderRadius: "4px",
                        padding: "4px 8px",
                        fontSize: "11px",
                        color: "#1E293B",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        gap: "3px"
                      }}
                    >
                      <FileText size={11} />
                      <span>Ledger</span>
                    </button>

                    {!isViewer && (
                      <button
                        onClick={() => openPhotoModal(worker)}
                        title="Upload / Change Worker Photograph"
                        style={{
                          background: "#F8FAFC",
                          border: "1px solid #CBD5E1",
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontSize: "11px",
                          color: "#475569",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px"
                        }}
                      >
                        <Camera size={11} />
                        <span>Photo</span>
                      </button>
                    )}

                    {userRole === "admin" && (
                      <button
                        onClick={() => openCitizenshipModal(worker)}
                        title="Manage Confidential Citizenship Document"
                        style={{
                          background: worker.has_citizenship_doc ? "#F0FDF4" : "#F8FAFC",
                          border: `1px solid ${worker.has_citizenship_doc ? "#BBF7D0" : "#CBD5E1"}`,
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontSize: "11px",
                          color: worker.has_citizenship_doc ? "#166534" : "#475569",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "3px"
                        }}
                      >
                        <Shield size={11} />
                        <span>Doc</span>
                      </button>
                    )}
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                    {!isViewer && worker.is_active && (
                      <>
                        <button
                          onClick={() => openAdvanceForWorker(worker)}
                          title="Give Advance"
                          style={{
                            background: "#FFFBEB",
                            border: "1px solid #FDE68A",
                            borderRadius: "4px",
                            padding: "4px 7px",
                            fontSize: "11px",
                            color: "#B45309",
                            cursor: "pointer"
                          }}
                        >
                          Adv
                        </button>
                        <button
                          onClick={() => openPayrollForWorker(worker)}
                          title="Process Payroll"
                          style={{
                            background: "#ECFDF5",
                            border: "1px solid #A7F3D0",
                            borderRadius: "4px",
                            padding: "4px 7px",
                            fontSize: "11px",
                            color: "#047857",
                            cursor: "pointer"
                          }}
                        >
                          Pay
                        </button>
                      </>
                    )}

                    {!isViewer && (
                      <button
                        onClick={() => openStatusModal(worker)}
                        title={worker.is_active ? "Deactivate Worker" : "Reactivate Worker"}
                        style={{
                          background: worker.is_active ? "#FEF2F2" : "#F0FDF4",
                          border: `1px solid ${worker.is_active ? "#FECACA" : "#BBF7D0"}`,
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontSize: "11px",
                          fontWeight: "600",
                          color: worker.is_active ? "#DC2626" : "#16A34A",
                          cursor: "pointer"
                        }}
                      >
                        {worker.is_active ? "Deactivate" : "Activate"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* ==================================================================== */
        /* WORKER DATA TABLE VIEW                                               */
        /* ==================================================================== */
        <div style={{ background: "#FFFFFF", border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: "12.5px" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>{t("worker_code")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>{t("worker_name")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>{t("join_date")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600" }}>{t("pay_type")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("basic_rate")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("twh")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("overtime")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>{t("advance_due")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "center" }}>{t("worker_status")}</th>
                <th style={{ padding: "10px 14px", fontWeight: "600", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredWorkers.map((worker) => {
                const hasAdvance = (worker.outstanding_advance_paisa || 0) > 0;
                const initials = getInitials(worker.name);
                const avatarBg = getAvatarColor(worker.name);

                return (
                  <tr
                    key={worker.id}
                    style={{
                      borderBottom: "1px solid #F1F5F9",
                      background: worker.is_active ? "#FFFFFF" : "#F8FAFC",
                      opacity: worker.is_active ? 1 : 0.75
                    }}
                  >
                    {/* Worker Code */}
                    <td style={{ padding: "10px 14px", fontWeight: "700", color: "#1E3A8A", ...TABULAR_NUMS_STYLE }}>
                      {worker.worker_code}
                    </td>

                    {/* Name, Avatar & Contact */}
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div
                          style={{
                            width: "32px",
                            height: "32px",
                            borderRadius: "50%",
                            overflow: "hidden",
                            flexShrink: 0,
                            background: avatarBg,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#FFFFFF",
                            fontWeight: "700",
                            fontSize: "12px",
                            border: "1px solid #CBD5E1"
                          }}
                        >
                          {worker.photo_url ? (
                            <img
                              src={worker.photo_url}
                              alt={worker.name}
                              style={{ width: "100%", height: "100%", objectFit: "cover" }}
                              onError={(e) => {
                                (e.target as any).style.display = "none";
                              }}
                            />
                          ) : (
                            <span>{initials}</span>
                          )}
                        </div>
                        <div>
                          <div style={{ fontWeight: "600", color: "#0F172A" }}>{worker.name}</div>
                          {worker.phone && (
                            <div style={{ fontSize: "11px", color: "#64748B", display: "flex", alignItems: "center", gap: "4px", marginTop: "2px" }}>
                              <Phone size={10} />
                              <span>{worker.phone}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Join Date */}
                    <td style={{ padding: "10px 14px", color: "#475569", ...TABULAR_NUMS_STYLE }}>
                      {worker.join_date}
                    </td>

                    {/* Pay Type */}
                    <td style={{ padding: "10px 14px" }}>
                      <span
                        style={{
                          fontSize: "11px",
                          fontWeight: "700",
                          padding: "2px 7px",
                          borderRadius: "3px",
                          background: worker.pay_type === "SALARY" ? "#DBEAFE" : "#FFEDD5",
                          color: worker.pay_type === "SALARY" ? "#1E40AF" : "#9A3412"
                        }}
                      >
                        {worker.pay_type === "SALARY" ? t("salary_type") : t("wage_type")}
                      </span>
                    </td>

                    {/* Basic Rate */}
                    <td style={{ padding: "10px 14px", textAlign: "right", fontWeight: "600", color: "#0F172A", ...TABULAR_NUMS_STYLE }}>
                      {worker.basic_rate_paisa !== undefined && worker.basic_rate_paisa !== null ? (
                        <>
                          NPR {fromPaisa(worker.basic_rate_paisa)}
                          <span style={{ fontSize: "10.5px", color: "#64748B", fontWeight: "400", marginLeft: "4px" }}>
                            {worker.pay_type === "SALARY" ? "/mo" : "/hr"}
                          </span>
                        </>
                      ) : (
                        <span style={{ color: "#94A3B8", fontStyle: "italic", fontSize: "12px" }}>[Restricted]</span>
                      )}
                    </td>

                    {/* Current Month TWH */}
                    <td style={{ padding: "10px 14px", textAlign: "right", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                      {worker.current_month ? Number(worker.current_month.total_working_hours || 0).toFixed(1) : "0.0"} hrs
                    </td>

                    {/* Current Month OT */}
                    <td style={{ padding: "10px 14px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>
                      {worker.current_month && Number(worker.current_month.overtime_hours || 0) > 0 ? (
                        <span style={{ fontWeight: "700", color: "#7C3AED" }}>
                          +{Number(worker.current_month.overtime_hours || 0).toFixed(1)} hrs
                        </span>
                      ) : (
                        <span style={{ color: "#94A3B8" }}>0.0 hrs</span>
                      )}
                    </td>

                    {/* Outstanding Advance */}
                    <td style={{ padding: "10px 14px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>
                      {worker.outstanding_advance_paisa !== undefined && worker.outstanding_advance_paisa !== null ? (
                        hasAdvance ? (
                          <span
                            style={{
                              fontWeight: "700",
                              color: "#DC2626",
                              background: "#FEF2F2",
                              border: "1px solid #FCA5A5",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontSize: "11.5px"
                            }}
                          >
                            NPR {fromPaisa(worker.outstanding_advance_paisa)}
                          </span>
                        ) : (
                          <span style={{ color: "#059669", fontWeight: "500" }}>NPR 0.00</span>
                        )
                      ) : (
                        <span style={{ color: "#94A3B8", fontStyle: "italic", fontSize: "12px" }}>[Restricted]</span>
                      )}
                    </td>

                    {/* Active Status Badge */}
                    <td style={{ padding: "10px 14px", textAlign: "center" }}>
                      <span
                        style={{
                          fontSize: "10.5px",
                          fontWeight: "700",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          background: worker.is_active ? "#DCFCE7" : "#E2E8F0",
                          color: worker.is_active ? "#15803D" : "#475569"
                        }}
                      >
                        {worker.is_active ? t("active") : t("inactive")}
                      </span>
                    </td>

                    {/* Actions */}
                    <td style={{ padding: "10px 14px", textAlign: "right" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" }}>
                        {/* History / Ledger Button */}
                        <button
                          onClick={() => openWorkerHistory(worker)}
                          title="View Profile & Ledger History"
                          style={{
                            background: "#F1F5F9",
                            border: "1px solid #CBD5E1",
                            borderRadius: "4px",
                            padding: "4px 8px",
                            fontSize: "11.5px",
                            color: "#1E293B",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px"
                          }}
                        >
                          <FileText size={12} />
                          <span>{isNepali ? "लेजर" : "Ledger"}</span>
                        </button>

                        {/* Pay Salary & Advance Buttons - Hidden for Viewer */}
                        {!isViewer && (
                          <>
                            <button
                              onClick={() => openPhotoModal(worker)}
                              title="Photo"
                              style={{
                                background: "#F8FAFC",
                                border: "1px solid #CBD5E1",
                                borderRadius: "4px",
                                padding: "4px 6px",
                                fontSize: "11.5px",
                                color: "#475569",
                                cursor: "pointer"
                              }}
                            >
                              <Camera size={12} />
                            </button>

                            {userRole === "admin" && (
                              <button
                                onClick={() => openCitizenshipModal(worker)}
                                title="Citizenship Document"
                                style={{
                                  background: worker.has_citizenship_doc ? "#F0FDF4" : "#F8FAFC",
                                  border: `1px solid ${worker.has_citizenship_doc ? "#BBF7D0" : "#CBD5E1"}`,
                                  borderRadius: "4px",
                                  padding: "4px 6px",
                                  fontSize: "11.5px",
                                  color: worker.has_citizenship_doc ? "#166534" : "#475569",
                                  cursor: "pointer"
                                }}
                              >
                                <Shield size={12} />
                              </button>
                            )}

                            {worker.is_active && (
                              <>
                                <button
                                  onClick={() => openAdvanceForWorker(worker)}
                                  title="Give Advance"
                                  style={{
                                    background: "#FFFBEB",
                                    border: "1px solid #FDE68A",
                                    borderRadius: "4px",
                                    padding: "4px 8px",
                                    fontSize: "11.5px",
                                    color: "#B45309",
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "3px"
                                  }}
                                >
                                  <DollarSign size={12} />
                                  <span>{isNepali ? "पेश्की" : "Advance"}</span>
                                </button>

                                <button
                                  onClick={() => openPayrollForWorker(worker)}
                                  title="Log Hours & Pay"
                                  style={{
                                    background: "#ECFDF5",
                                    border: "1px solid #A7F3D0",
                                    borderRadius: "4px",
                                    padding: "4px 8px",
                                    fontSize: "11.5px",
                                    color: "#047857",
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "3px"
                                  }}
                                >
                                  <Clock size={12} />
                                  <span>{isNepali ? "तलब" : "Pay"}</span>
                                </button>
                              </>
                            )}

                            {/* Active/Inactive Toggle Button */}
                            <button
                              onClick={() => openStatusModal(worker)}
                              title={worker.is_active ? "Deactivate Worker" : "Reactivate Worker"}
                              style={{
                                background: "transparent",
                                border: "none",
                                cursor: "pointer",
                                padding: "4px",
                                color: worker.is_active ? "#EF4444" : "#10B981"
                              }}
                            >
                              {worker.is_active ? <XCircle size={15} color="#EF4444" /> : <CheckCircle2 size={15} color="#10B981" />}
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* MODAL 1: ADD WORKER */}
      {showAddWorkerModal && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "500px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
              overflow: "hidden"
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Users size={18} color="#1E3A8A" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {t("add_worker")}
                </h3>
              </div>
              <button onClick={() => setShowAddWorkerModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateWorker} style={{ padding: "20px" }}>
              {workerFormError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {workerFormError}
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("worker_code")} *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. EMP-101, WKR-042"
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>

                <div>
                  <NepaliDatePicker
                    compact
                    label={`${t("join_date")} *`}
                    valueAd={newJoinDate}
                    onChange={({ ad }) => setNewJoinDate(ad)}
                    required
                  />
                </div>
              </div>

              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {t("worker_name")} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Full legal worker name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("pay_type")} *
                  </label>
                  <select
                    value={newPayType}
                    onChange={(e) => setNewPayType(e.target.value as any)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", outline: "none" }}
                  >
                    <option value="SALARY">{t("salary_type")}</option>
                    <option value="WAGE">{t("wage_type")}</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {newPayType === "SALARY" ? (isNepali ? "मासिक तलब (रु.)" : "Monthly Salary (NPR)") : (isNepali ? "घण्टा ज्याला दर (रु.)" : "Hourly Wage (NPR)")} *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    placeholder={newPayType === "SALARY" ? "25000" : "150"}
                    value={newRateNpr}
                    onChange={(e) => setNewRateNpr(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  {t("phone_number")}
                </label>
                <input
                  type="tel"
                  placeholder="e.g. 9841000000"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "18px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {isNepali ? "अस्थायी ठेगाना" : "Temporary Address"}
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Ward 4, Balaju, Kathmandu"
                    value={newTempAddress}
                    onChange={(e) => setNewTempAddress(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {isNepali ? "स्थायी ठेगाना" : "Permanent Address"}
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Hetauda-4, Makwanpur"
                    value={newPermAddress}
                    onChange={(e) => setNewPermAddress(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddWorkerModal(false)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={submittingWorker}
                  style={{ padding: "7px 18px", border: "none", borderRadius: "4px", background: "#1E3A8A", color: "#FFFFFF", fontSize: "12.5px", fontWeight: "600", cursor: "pointer" }}
                >
                  {submittingWorker ? "Saving..." : t("commit_record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: RECORD ADVANCE */}
      {showAdvanceModal && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "500px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
              overflow: "hidden"
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <DollarSign size={18} color="#B45309" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {t("give_advance")} (Worker Advance)
                </h3>
              </div>
              <button onClick={() => setShowAdvanceModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleRecordAdvance} style={{ padding: "20px" }}>
              {advanceFormError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {advanceFormError}
                </div>
              )}

              {/* Worker Selector */}
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Select Worker *
                </label>
                <select
                  required
                  value={advanceWorkerId}
                  onChange={(e) => setAdvanceWorkerId(Number(e.target.value))}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", outline: "none" }}
                >
                  <option value="">-- Choose Worker --</option>
                  {workers.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.worker_code} - {w.name} (Due: NPR {fromPaisa(w.outstanding_advance_paisa || 0)})
                    </option>
                  ))}
                </select>
              </div>

              {/* Entry Type */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Advance Action *
                  </label>
                  <select
                    value={advanceType}
                    onChange={(e) => setAdvanceType(e.target.value as any)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", outline: "none" }}
                  >
                    <option value="ISSUED">{t("entry_issued")} (+ Give Advance)</option>
                    <option value="RECOVERED">{t("entry_recovered")} (- Recover / Repay)</option>
                  </select>
                </div>

                <div>
                  <NepaliDatePicker
                    compact
                    label="Date (मिति) *"
                    valueAd={advanceDate}
                    onChange={({ ad }) => setAdvanceDate(ad)}
                    required
                  />
                </div>
              </div>

              {/* Amount */}
              <div style={{ marginBottom: "12px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Amount (NPR) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  placeholder="e.g. 5000"
                  value={advanceAmountNpr}
                  onChange={(e) => setAdvanceAmountNpr(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              {/* Notes */}
              <div style={{ marginBottom: "18px" }}>
                <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Notes / Receipt / Purpose
                </label>
                <input
                  type="text"
                  placeholder="e.g. Festival advance, medical need, receipt #104"
                  value={advanceNotes}
                  onChange={(e) => setAdvanceNotes(e.target.value)}
                  style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                />
              </div>

              {/* Live Preview of Advance Impact */}
              {advanceWorkerId && advanceAmountNpr && (
                <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
                  <div style={{ color: "#64748B" }}>Ledger Impact Preview:</div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px" }}>
                    <span>Current Advance Due:</span>
                    <span style={{ fontWeight: "700", ...TABULAR_NUMS_STYLE }}>
                      NPR {fromPaisa(workers.find((w) => w.id === advanceWorkerId)?.outstanding_advance_paisa || 0)}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: "2px", color: advanceType === "ISSUED" ? "#DC2626" : "#059669" }}>
                    <span>{advanceType === "ISSUED" ? "+ Issuing:" : "- Recovering:"}</span>
                    <span style={{ fontWeight: "700", ...TABULAR_NUMS_STYLE }}>
                      NPR {fromPaisa(toPaisa(advanceAmountNpr))}
                    </span>
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAdvanceModal(false)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={submittingAdvance}
                  style={{ padding: "7px 18px", border: "none", borderRadius: "4px", background: "#B45309", color: "#FFFFFF", fontSize: "12.5px", fontWeight: "600", cursor: "pointer" }}
                >
                  {submittingAdvance ? "Recording..." : t("commit_record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: LOG HOURS & PAYROLL */}
      {showPayrollModal && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "560px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
              overflow: "hidden"
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Clock size={18} color="#047857" />
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {t("record_payroll")} (Monthly Hours & Wage)
                </h3>
              </div>
              <button onClick={() => setShowPayrollModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleRecordPayroll} style={{ padding: "20px" }}>
              {payrollFormError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {payrollFormError}
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Worker *
                  </label>
                  <select
                    required
                    value={payrollWorkerId}
                    onChange={(e) => {
                      const id = Number(e.target.value);
                      setPayrollWorkerId(id);
                      const w = workers.find((item) => item.id === id);
                      if (w) {
                        setPayrollHours(String(w.current_month?.total_working_hours || (w.pay_type === "SALARY" ? 208 : 0)));
                        setPayrollOtHours(String(w.current_month?.overtime_hours || 0));
                        setPayrollAdvanceDeductionNpr(fromPaisa(w.outstanding_advance_paisa || 0, false));
                      }
                    }}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", outline: "none" }}
                  >
                    <option value="">-- Select Worker --</option>
                    {workers.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.worker_code} - {w.name} ({w.pay_type})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Month / Period *
                  </label>
                  <input
                    type="month"
                    required
                    value={payrollMonthYear}
                    onChange={(e) => setPayrollMonthYear(e.target.value)}
                    style={{ width: "100%", padding: "6px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                </div>
              </div>

              {/* Hours Inputs */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("twh")} *
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    required
                    value={payrollHours}
                    onChange={(e) => setPayrollHours(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                  <span style={{ fontSize: "11px", color: "#64748B" }}>
                    {selectedPayrollWorker?.pay_type === "SALARY" ? "Standard monthly: 208 hrs" : "Hourly production log"}
                  </span>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("overtime")} (hrs)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={payrollOtHours}
                    onChange={(e) => setPayrollOtHours(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                  <span style={{ fontSize: "11px", color: "#64748B" }}>Paid at 1.5x basic rate</span>
                </div>
              </div>

              {/* Advance Deduction & Payment Method */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("advance_deduction")} (NPR)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="0.00"
                    value={payrollAdvanceDeductionNpr}
                    onChange={(e) => setPayrollAdvanceDeductionNpr(e.target.value)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                  />
                  <span style={{ fontSize: "11px", color: "#64748B" }}>
                    Max available: NPR {fromPaisa(selectedPayrollWorker?.outstanding_advance_paisa || 0)}
                  </span>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("payment_method")}
                  </label>
                  <select
                    value={payrollPaymentMethod}
                    onChange={(e) => setPayrollPaymentMethod(e.target.value as any)}
                    style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", outline: "none" }}
                  >
                    <option value="CASH">{t("cash")}</option>
                    <option value="BANK">{t("bank")}</option>
                  </select>
                </div>
              </div>

              {/* Real-time Calculation Summary Box */}
              <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", padding: "12px 16px", borderRadius: "6px", marginBottom: "16px" }}>
                <div style={{ fontSize: "12px", fontWeight: "700", color: "#334155", borderBottom: "1px solid #E2E8F0", paddingBottom: "6px", marginBottom: "8px" }}>
                  Payroll Calculation Breakdown:
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                  <span>{t("gross_pay")}:</span>
                  <span style={{ fontWeight: "600", ...TABULAR_NUMS_STYLE }}>NPR {fromPaisa(previewGrossPaisa)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px", color: "#DC2626" }}>
                  <span>{t("advance_deduction")}:</span>
                  <span style={{ fontWeight: "600", ...TABULAR_NUMS_STYLE }}>- NPR {fromPaisa(previewAdvanceDeductionPaisa)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "14px", fontWeight: "700", color: "#047857", borderTop: "1px solid #E2E8F0", paddingTop: "6px" }}>
                  <span>{t("net_paid")}:</span>
                  <span style={{ ...TABULAR_NUMS_STYLE }}>NPR {fromPaisa(previewNetPaidPaisa)}</span>
                </div>
              </div>

              {/* Checkbox: Mark as Paid immediately */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "18px" }}>
                <input
                  type="checkbox"
                  id="markAsPaidCheck"
                  checked={payrollMarkPaid}
                  onChange={(e) => setPayrollMarkPaid(e.target.checked)}
                  style={{ width: "16px", height: "16px", cursor: "pointer" }}
                />
                <label htmlFor="markAsPaidCheck" style={{ fontSize: "12.5px", color: "#334155", cursor: "pointer" }}>
                  {isNepali
                    ? "तुरुन्त भुक्तानी भएको जनाउनुहोस् (पेश्की खातामा स्वतः असुली दर्ता हुनेछ)"
                    : "Mark as Paid immediately (Automatically logs recovery in advance ledger)"}
                </label>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowPayrollModal(false)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={submittingPayroll}
                  style={{ padding: "7px 18px", border: "none", borderRadius: "4px", background: "#047857", color: "#FFFFFF", fontSize: "12.5px", fontWeight: "600", cursor: "pointer" }}
                >
                  {submittingPayroll ? "Processing..." : t("commit_record")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DRAWER / MODAL 4: WORKER PROFILE & HISTORY LEDGER */}
      {selectedWorkerForHistory && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            zIndex: 1000
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              width: "100%",
              maxWidth: "760px",
              height: "100%",
              boxShadow: "-10px 0 25px -5px rgba(0, 0, 0, 0.15)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden"
            }}
          >
            {/* Header */}
            <div style={{ padding: "20px 24px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#F8FAFC" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px", fontWeight: "700", color: "#0F172A" }}>
                    {selectedWorkerForHistory.name}
                  </span>
                  <span style={{ fontSize: "12px", fontWeight: "700", color: "#1E3A8A", background: "#DBEAFE", padding: "2px 8px", borderRadius: "3px", ...TABULAR_NUMS_STYLE }}>
                    {selectedWorkerForHistory.worker_code}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "#64748B", marginTop: "3px" }}>
                  {t("join_date")}: {selectedWorkerForHistory.join_date} • {selectedWorkerForHistory.pay_type === "SALARY" ? t("salary_type") : t("wage_type")} ({selectedWorkerForHistory.basic_rate_paisa !== undefined ? `NPR ${fromPaisa(selectedWorkerForHistory.basic_rate_paisa)}` : "[Restricted]"})
                </div>
              </div>
              <button
                onClick={() => setSelectedWorkerForHistory(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B", padding: "6px" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Sub-header with prominent advance badge and quick actions */}
            <div style={{ padding: "16px 24px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center", background: "#FFFFFF", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{ fontSize: "12px", color: "#475569", fontWeight: "600" }}>{t("outstanding_advance")}:</div>
                <div
                  style={{
                    fontSize: "16px",
                    fontWeight: "700",
                    color: historyOutstandingPaisa > 0 ? "#DC2626" : "#059669",
                    background: historyOutstandingPaisa > 0 ? "#FEF2F2" : "#ECFDF5",
                    border: `1px solid ${historyOutstandingPaisa > 0 ? "#FCA5A5" : "#A7F3D0"}`,
                    padding: "4px 12px",
                    borderRadius: "4px",
                    ...TABULAR_NUMS_STYLE
                  }}
                >
                  {isNepali ? `पेश्की बाँकी: NPR ${fromPaisa(historyOutstandingPaisa)}` : `Advance Due: NPR ${fromPaisa(historyOutstandingPaisa)}`}
                </div>
              </div>

              {!isViewer && (
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => openAdvanceForWorker(selectedWorkerForHistory)}
                    style={{
                      background: "#B45309",
                      color: "#FFFFFF",
                      border: "none",
                      padding: "6px 12px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px"
                    }}
                  >
                    <DollarSign size={13} />
                    <span>{t("give_advance")}</span>
                  </button>

                  <button
                    onClick={() => openPayrollForWorker(selectedWorkerForHistory)}
                    style={{
                      background: "#047857",
                      color: "#FFFFFF",
                      border: "none",
                      padding: "6px 12px",
                      borderRadius: "4px",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px"
                    }}
                  >
                    <Clock size={13} />
                    <span>{t("record_payroll")}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Body: Two Scrollable Sections */}
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
              {historyLoading ? (
                <div style={{ textAlign: "center", padding: "40px", color: "#64748B" }}>
                  <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 10px" }} />
                  <div>Loading worker ledger history...</div>
                </div>
              ) : (
                <>
                  {/* Worker Identity & Profile Details Card */}
                  <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", borderRadius: "8px", padding: "16px", marginBottom: "24px" }}>
                    <div style={{ display: "flex", gap: "16px", alignItems: "flex-start", flexWrap: "wrap" }}>
                      <div
                        style={{
                          width: "72px",
                          height: "72px",
                          borderRadius: "50%",
                          overflow: "hidden",
                          border: "2px solid #CBD5E1",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          background: getAvatarColor(selectedWorkerForHistory.id),
                          color: "#FFFFFF",
                          fontSize: "24px",
                          fontWeight: "700",
                          flexShrink: 0
                        }}
                      >
                        {selectedWorkerForHistory.photo_url ? (
                          <img
                            src={selectedWorkerForHistory.photo_url}
                            alt={selectedWorkerForHistory.name}
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                        ) : (
                          getInitials(selectedWorkerForHistory.name)
                        )}
                      </div>

                      <div style={{ flex: 1, minWidth: "240px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "2px 8px",
                              borderRadius: "12px",
                              fontSize: "11px",
                              fontWeight: "700",
                              background: selectedWorkerForHistory.is_active ? "#DCFCE7" : "#FEE2E2",
                              color: selectedWorkerForHistory.is_active ? "#15803D" : "#B91C1C"
                            }}
                          >
                            {selectedWorkerForHistory.is_active ? (
                              <>
                                <CheckCircle2 size={12} />
                                <span>{isNepali ? "सक्रिय" : "ACTIVE"}</span>
                              </>
                            ) : (
                              <>
                                <XCircle size={12} />
                                <span>{isNepali ? "निष्क्रिय" : "INACTIVE"}</span>
                              </>
                            )}
                          </span>

                          {!selectedWorkerForHistory.is_active && selectedWorkerForHistory.inactive_date && (
                            <span style={{ fontSize: "11px", color: "#64748B" }}>
                              Since: {selectedWorkerForHistory.inactive_date} {selectedWorkerForHistory.inactive_reason ? `(${selectedWorkerForHistory.inactive_reason})` : ""}
                            </span>
                          )}

                          {!isViewer && (
                            <button
                              onClick={() => openStatusModal(selectedWorkerForHistory)}
                              style={{
                                background: "none",
                                border: "none",
                                color: selectedWorkerForHistory.is_active ? "#DC2626" : "#059669",
                                fontSize: "11px",
                                fontWeight: "600",
                                cursor: "pointer",
                                textDecoration: "underline",
                                marginLeft: "auto"
                              }}
                            >
                              {selectedWorkerForHistory.is_active ? "Deactivate" : "Reactivate"}
                            </button>
                          )}
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px", marginTop: "8px" }}>
                          <div>
                            <span style={{ color: "#64748B" }}>Phone: </span>
                            <span style={{ fontWeight: "600", color: "#334155" }}>{selectedWorkerForHistory.phone || "—"}</span>
                          </div>
                          <div>
                            <span style={{ color: "#64748B" }}>Temp Address: </span>
                            <span style={{ fontWeight: "600", color: "#334155" }}>{selectedWorkerForHistory.temporary_address || "—"}</span>
                          </div>
                          <div style={{ gridColumn: "span 2" }}>
                            <span style={{ color: "#64748B" }}>Permanent Address: </span>
                            <span style={{ fontWeight: "600", color: "#334155" }}>{selectedWorkerForHistory.permanent_address || "—"}</span>
                          </div>
                        </div>

                        {/* Quick actions for Photo & Confidential Citizenship Doc */}
                        <div style={{ display: "flex", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
                          {!isViewer && (
                            <button
                              onClick={() => openPhotoModal(selectedWorkerForHistory)}
                              style={{
                                background: "#FFFFFF",
                                border: "1px solid #CBD5E1",
                                padding: "4px 10px",
                                borderRadius: "4px",
                                fontSize: "11px",
                                fontWeight: "600",
                                color: "#334155",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px"
                              }}
                            >
                              <Camera size={12} color="#1E3A8A" />
                              <span>{selectedWorkerForHistory.photo_url ? "Change Photo" : "Upload Photo"}</span>
                            </button>
                          )}

                          {userRole === "admin" && (
                            <button
                              onClick={() => openCitizenshipModal(selectedWorkerForHistory)}
                              style={{
                                background: selectedWorkerForHistory.has_citizenship_doc ? "#F0FDF4" : "#FEF3C7",
                                border: `1px solid ${selectedWorkerForHistory.has_citizenship_doc ? "#BBF7D0" : "#FDE68A"}`,
                                padding: "4px 10px",
                                borderRadius: "4px",
                                fontSize: "11px",
                                fontWeight: "600",
                                color: selectedWorkerForHistory.has_citizenship_doc ? "#166534" : "#92400E",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px"
                              }}
                            >
                              <ShieldCheck size={12} />
                              <span>
                                {selectedWorkerForHistory.has_citizenship_doc ? "Citizenship: Verified" : "Citizenship: Missing"}
                              </span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Section 1: Monthly Payroll Records */}
                  <div style={{ marginBottom: "28px" }}>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Clock size={16} color="#047857" />
                      <span>{t("payroll_history")}</span>
                    </div>

                    {historyMonthly.length === 0 ? (
                      <div style={{ background: "#F8FAFC", padding: "16px", borderRadius: "6px", textAlign: "center", color: "#64748B", fontSize: "12px" }}>
                        No monthly payroll logs recorded yet.
                      </div>
                    ) : (
                      <div style={{ border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                          <thead>
                            <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                              <th style={{ padding: "8px 10px" }}>Month</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>TWH</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>OT</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>{t("gross_pay")}</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>{t("advance_deduction")}</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>{t("net_paid")}</th>
                              <th style={{ padding: "8px 10px", textAlign: "center" }}>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {historyMonthly.map((m) => (
                              <tr key={m.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                                <td style={{ padding: "8px 10px", fontWeight: "600", ...TABULAR_NUMS_STYLE }}>{m.month_year}</td>
                                <td style={{ padding: "8px 10px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>{Number(m.total_working_hours || 0).toFixed(1)}</td>
                                <td style={{ padding: "8px 10px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>{Number(m.overtime_hours || 0).toFixed(1)}</td>
                                <td style={{ padding: "8px 10px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>NPR {fromPaisa(m.gross_pay_paisa)}</td>
                                <td style={{ padding: "8px 10px", textAlign: "right", color: "#DC2626", ...TABULAR_NUMS_STYLE }}>
                                  - NPR {fromPaisa(m.advance_deduction_paisa)}
                                </td>
                                <td style={{ padding: "8px 10px", textAlign: "right", fontWeight: "700", color: "#047857", ...TABULAR_NUMS_STYLE }}>
                                  NPR {fromPaisa(m.net_paid_paisa)}
                                </td>
                                <td style={{ padding: "8px 10px", textAlign: "center" }}>
                                  <span
                                    style={{
                                      fontSize: "10px",
                                      fontWeight: "700",
                                      padding: "2px 6px",
                                      borderRadius: "3px",
                                      background: m.status === "PAID" ? "#DCFCE7" : "#FEF3C7",
                                      color: m.status === "PAID" ? "#15803D" : "#B45309"
                                    }}
                                  >
                                    {m.status === "PAID" ? t("status_paid") : t("status_pending")}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Section 2: Advance Transactions History */}
                  <div>
                    <div style={{ fontSize: "14px", fontWeight: "700", color: "#0F172A", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <DollarSign size={16} color="#B45309" />
                      <span>{t("advance_history")}</span>
                    </div>

                    {historyAdvances.length === 0 ? (
                      <div style={{ background: "#F8FAFC", padding: "16px", borderRadius: "6px", textAlign: "center", color: "#64748B", fontSize: "12px" }}>
                        No advance records logged for this worker.
                      </div>
                    ) : (
                      <div style={{ border: "1px solid #E2E8F0", borderRadius: "6px", overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                          <thead>
                            <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0", textAlign: "left", color: "#475569" }}>
                              <th style={{ padding: "8px 10px" }}>Date</th>
                              <th style={{ padding: "8px 10px" }}>Type</th>
                              <th style={{ padding: "8px 10px", textAlign: "right" }}>Amount</th>
                              <th style={{ padding: "8px 10px" }}>Notes / Voucher</th>
                              <th style={{ padding: "8px 10px" }}>Recorded By</th>
                            </tr>
                          </thead>
                          <tbody>
                            {historyAdvances.map((adv) => (
                              <tr key={adv.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                                <td style={{ padding: "8px 10px", color: "#475569", ...TABULAR_NUMS_STYLE }}>{adv.date}</td>
                                <td style={{ padding: "8px 10px" }}>
                                  <span
                                    style={{
                                      fontSize: "10px",
                                      fontWeight: "700",
                                      padding: "2px 6px",
                                      borderRadius: "3px",
                                      background: adv.entry_type === "ISSUED" ? "#FEE2E2" : "#DCFCE7",
                                      color: adv.entry_type === "ISSUED" ? "#B91C1C" : "#15803D"
                                    }}
                                  >
                                    {adv.entry_type === "ISSUED" ? t("entry_issued") : t("entry_recovered")}
                                  </span>
                                </td>
                                <td style={{ padding: "8px 10px", textAlign: "right", fontWeight: "600", color: adv.entry_type === "ISSUED" ? "#B91C1C" : "#15803D", ...TABULAR_NUMS_STYLE }}>
                                  {adv.entry_type === "ISSUED" ? "+" : "-"} NPR {fromPaisa(adv.amount_paisa)}
                                </td>
                                <td style={{ padding: "8px 10px", color: "#475569" }}>{adv.notes || "-"}</td>
                                <td style={{ padding: "8px 10px", color: "#64748B", fontSize: "11px" }}>{adv.actor_name || `User #${adv.actor_id}`}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div style={{ padding: "14px 24px", borderTop: "1px solid #E2E8F0", display: "flex", justifyContent: "flex-end", background: "#F8FAFC" }}>
              <button
                onClick={() => setSelectedWorkerForHistory(null)}
                style={{ padding: "7px 16px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
              >
                {t("close")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 5: STATUS TRANSITION CONFIRMATION (ACTIVATE / DEACTIVATE) */}
      {statusWorker && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "480px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
              overflow: "hidden"
            }}
          >
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid #E2E8F0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: statusWorker.is_active ? "#FEF2F2" : "#ECFDF5"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {statusWorker.is_active ? (
                  <AlertTriangle size={18} color="#DC2626" />
                ) : (
                  <CheckCircle2 size={18} color="#059669" />
                )}
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: statusWorker.is_active ? "#991B1B" : "#065F46", margin: 0 }}>
                  {statusWorker.is_active
                    ? (isNepali ? "कामदार निष्क्रिय बनाउने पुष्टि" : "Confirm Worker Deactivation")
                    : (isNepali ? "कामदार पुनः सक्रिय बनाउने पुष्टि" : "Confirm Worker Reactivation")}
                </h3>
              </div>
              <button
                onClick={() => setStatusWorker(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmStatus} style={{ padding: "20px" }}>
              {statusError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {statusError}
                </div>
              )}

              <div style={{ marginBottom: "16px", fontSize: "13px", color: "#334155", lineHeight: 1.5 }}>
                <p style={{ margin: "0 0 8px 0" }}>
                  <strong>{statusWorker.name}</strong> ({statusWorker.worker_code})
                </p>
                {statusWorker.is_active ? (
                  <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", padding: "10px 12px", borderRadius: "6px", fontSize: "12px", color: "#92400E" }}>
                    <p style={{ margin: "0 0 6px 0", fontWeight: "600" }}>
                      {isNepali ? "⚠️ ध्यान दिनुहोस्:" : "⚠️ Important Lifecycle Guardrails:"}
                    </p>
                    <ul style={{ margin: 0, paddingLeft: "18px" }}>
                      <li>{isNepali ? "नयाँ पेश्की दिन रोकिनेछ।" : "Worker will be blocked from receiving new cash advances."}</li>
                      <li>{isNepali ? "नयाँ तलब गणनामा समावेश गरिने छैन।" : "Worker will be blocked from new monthly payroll runs."}</li>
                      <li>
                        {isNepali
                          ? `बाँकी पेश्की (रु. ${fromPaisa(statusWorker.outstanding_advance_paisa || 0)}) तथा सम्पूर्ण पुरानो इतिहास सुरक्षित रहनेछ।`
                          : `Outstanding advance (NPR ${fromPaisa(statusWorker.outstanding_advance_paisa || 0)}) and full audit history remain intact.`}
                      </li>
                    </ul>
                  </div>
                ) : (
                  <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", padding: "10px 12px", borderRadius: "6px", fontSize: "12px", color: "#166534" }}>
                    <p style={{ margin: 0 }}>
                      {isNepali
                        ? "पुनः सक्रिय गरेपछि कामदारलाई पुनः पेश्की तथा तलब गणना गर्न सकिनेछ। पुरानो पेश्की बाँकी कायमै रहनेछ।"
                        : "Reactivating will restore eligibility for new advances and monthly payroll calculations. Outstanding advances remain preserved."}
                    </p>
                  </div>
                )}
              </div>

              {statusWorker.is_active && (
                <>
                  <div style={{ marginBottom: "12px" }}>
                    <NepaliDatePicker
                      compact
                      label={isNepali ? "निष्क्रिय मिति *" : "Effective Inactive Date *"}
                      valueAd={statusInactiveDate}
                      onChange={({ ad }) => setStatusInactiveDate(ad)}
                      required
                    />
                  </div>

                  <div style={{ marginBottom: "16px" }}>
                    <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                      {isNepali ? "निष्क्रिय कारण" : "Deactivation Reason / Notes"}
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Resigned, End of seasonal contract, Left for village"
                      value={statusReason}
                      onChange={(e) => setStatusReason(e.target.value)}
                      style={{ width: "100%", padding: "7px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
                    />
                  </div>
                </>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setStatusWorker(null)}
                  style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                >
                  {t("close")}
                </button>
                <button
                  type="submit"
                  disabled={submittingStatus}
                  style={{
                    padding: "7px 18px",
                    border: "none",
                    borderRadius: "4px",
                    background: statusWorker.is_active ? "#DC2626" : "#059669",
                    color: "#FFFFFF",
                    fontSize: "12.5px",
                    fontWeight: "600",
                    cursor: "pointer"
                  }}
                >
                  {submittingStatus
                    ? "Updating..."
                    : statusWorker.is_active
                    ? (isNepali ? "निष्क्रिय गर्नुहोस्" : "Confirm Deactivation")
                    : (isNepali ? "सक्रिय गर्नुहोस्" : "Confirm Reactivation")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 6: WORKER PHOTOGRAPH MANAGEMENT */}
      {photoWorker && !isViewer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "460px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
              overflow: "hidden"
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: "1px solid #E2E8F0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Camera size={18} color="#1E3A8A" />
                <h3 style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A", margin: 0 }}>
                  {isNepali ? "कामदार फोटो व्यवस्थापन" : "Worker Photograph"}
                </h3>
              </div>
              <button onClick={() => setPhotoWorker(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748B" }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: "20px" }}>
              {photoError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {photoError}
                </div>
              )}

              <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "20px" }}>
                <div
                  style={{
                    width: "72px",
                    height: "72px",
                    borderRadius: "50%",
                    overflow: "hidden",
                    border: "2px solid #E2E8F0",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: getAvatarColor(photoWorker.id),
                    color: "#FFFFFF",
                    fontSize: "22px",
                    fontWeight: "700",
                    flexShrink: 0
                  }}
                >
                  {photoWorker.photo_url ? (
                    <img
                      src={photoWorker.photo_url}
                      alt={photoWorker.name}
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                  ) : (
                    getInitials(photoWorker.name)
                  )}
                </div>
                <div>
                  <div style={{ fontSize: "15px", fontWeight: "700", color: "#0F172A" }}>{photoWorker.name}</div>
                  <div style={{ fontSize: "12px", color: "#64748B", ...TABULAR_NUMS_STYLE }}>{photoWorker.worker_code}</div>
                  {photoWorker.photo_url && (
                    <button
                      type="button"
                      onClick={handleDeletePhoto}
                      disabled={submittingPhoto}
                      style={{
                        marginTop: "6px",
                        background: "#FEF2F2",
                        border: "1px solid #FCA5A5",
                        color: "#DC2626",
                        fontSize: "11px",
                        fontWeight: "600",
                        padding: "3px 8px",
                        borderRadius: "4px",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px"
                      }}
                    >
                      <Trash2 size={12} />
                      <span>{isNepali ? "फोटो हटाउनुहोस्" : "Remove Photo"}</span>
                    </button>
                  )}
                </div>
              </div>

              <form onSubmit={handleUploadPhoto}>
                <div style={{ marginBottom: "14px" }}>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {isNepali ? "नयाँ फोटो चयन गर्नुहोस् (JPEG, PNG, WebP — अधिकतम २ MB)" : "Select New Photo (JPEG, PNG, WebP — Max 2MB)"}
                  </label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    required
                    onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
                    style={{ width: "100%", fontSize: "12px", padding: "6px", border: "1px solid #CBD5E1", borderRadius: "4px" }}
                  />
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    {isNepali ? "फाइल सामग्री प्रमाणीकरण गरी सुरक्षित भण्डारण गरिनेछ।" : "File magic bytes and format are strictly validated on server."}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setPhotoWorker(null)}
                    style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                  >
                    {t("close")}
                  </button>
                  <button
                    type="submit"
                    disabled={submittingPhoto || !photoFile}
                    style={{
                      padding: "7px 18px",
                      border: "none",
                      borderRadius: "4px",
                      background: "#1E3A8A",
                      color: "#FFFFFF",
                      fontSize: "12.5px",
                      fontWeight: "600",
                      cursor: (submittingPhoto || !photoFile) ? "not-allowed" : "pointer"
                    }}
                  >
                    {submittingPhoto ? "Uploading..." : (isNepali ? "फोटो अपलोड गर्नुहोस्" : "Upload Photo")}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 7: CONFIDENTIAL CITIZENSHIP DOCUMENT (ADMIN ONLY) */}
      {citWorker && userRole === "admin" && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(2px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "16px"
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: "8px",
              width: "100%",
              maxWidth: "500px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
              overflow: "hidden"
            }}
          >
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid #E2E8F0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "#0F172A",
                color: "#FFFFFF"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldCheck size={18} color="#38BDF8" />
                <h3 style={{ fontSize: "15px", fontWeight: "700", margin: 0 }}>
                  {isNepali ? "गोप्य नागरिकता कागजात (प्रशासक मात्र)" : "Confidential Citizenship Document (Admin Only)"}
                </h3>
              </div>
              <button onClick={() => setCitWorker(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "#94A3B8" }}>
                <X size={18} />
              </button>
            </div>

            <div style={{ padding: "20px" }}>
              {citError && (
                <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "8px 12px", borderRadius: "4px", color: "#B91C1C", marginBottom: "14px", fontSize: "12.5px" }}>
                  {citError}
                </div>
              )}

              <div style={{ background: "#F8FAFC", border: "1px solid #E2E8F0", padding: "12px 14px", borderRadius: "6px", marginBottom: "16px", fontSize: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ color: "#64748B" }}>Worker:</span>
                  <span style={{ fontWeight: "700", color: "#0F172A" }}>{citWorker.name} ({citWorker.worker_code})</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "#64748B" }}>Security:</span>
                  <span style={{ fontWeight: "600", color: "#0369A1" }}>Tenant-Isolated Private Storage (Non-Public)</span>
                </div>
              </div>

              {citWorker.has_citizenship_doc ? (
                <div style={{ background: "#ECFDF5", border: "1px solid #A7F3D0", padding: "14px", borderRadius: "6px", marginBottom: "18px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                    <FileText size={16} color="#059669" />
                    <span style={{ fontSize: "12.5px", fontWeight: "700", color: "#065F46" }}>
                      {citWorker.citizenship_doc_name || "Citizenship Document On File"}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                    <a
                      href={`/api/v1/hr/workers/${citWorker.id}/citizenship`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        background: "#047857",
                        color: "#FFFFFF",
                        padding: "6px 12px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        textDecoration: "none",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px"
                      }}
                    >
                      <Download size={13} />
                      <span>{isNepali ? "कागजात हेर्नुहोस् / डाउनलोड" : "View / Download"}</span>
                    </a>
                    <button
                      type="button"
                      onClick={handleDeleteCitizenship}
                      disabled={submittingCit}
                      style={{
                        background: "#FFFFFF",
                        border: "1px solid #FCA5A5",
                        color: "#DC2626",
                        padding: "6px 12px",
                        borderRadius: "4px",
                        fontSize: "12px",
                        fontWeight: "600",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px"
                      }}
                    >
                      <Trash2 size={13} />
                      <span>{isNepali ? "कागजात मेटाउनुहोस्" : "Delete Document"}</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ background: "#FFFBEB", border: "1px solid #FDE68A", padding: "12px", borderRadius: "6px", marginBottom: "18px", fontSize: "12px", color: "#92400E" }}>
                  {isNepali ? "यस कामदारको नागरिकता कागजात अपलोड गरिएको छैन।" : "No citizenship document on file for this worker."}
                </div>
              )}

              <form onSubmit={handleUploadCitizenship}>
                <div style={{ marginBottom: "14px" }}>
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {citWorker.has_citizenship_doc
                      ? (isNepali ? "कागजात प्रतिस्थापन गर्नुहोस् (PDF, JPEG, PNG — अधिकतम ५ MB)" : "Replace Document (PDF, JPEG, PNG — Max 5MB)")
                      : (isNepali ? "नागरिकता कागजात अपलोड गर्नुहोस् (PDF, JPEG, PNG — अधिकतम ५ MB)" : "Upload Citizenship Document (PDF, JPEG, PNG — Max 5MB)")}
                  </label>
                  <input
                    type="file"
                    accept=".pdf,image/jpeg,image/png,image/webp"
                    required
                    onChange={(e) => setCitFile(e.target.files?.[0] || null)}
                    style={{ width: "100%", fontSize: "12px", padding: "6px", border: "1px solid #CBD5E1", borderRadius: "4px" }}
                  />
                  <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
                    {isNepali ? "प्रशासक प्रमाणीकरण आवश्यक छ। सार्वजनिक URL बाट पहुँच सम्भव छैन।" : "Strict Admin RBAC enforced. Stored outside webroot with private headers."}
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                  <button
                    type="button"
                    onClick={() => setCitWorker(null)}
                    style={{ padding: "7px 14px", border: "1px solid #CBD5E1", borderRadius: "4px", background: "#FFFFFF", color: "#475569", fontSize: "12.5px", cursor: "pointer" }}
                  >
                    {t("close")}
                  </button>
                  <button
                    type="submit"
                    disabled={submittingCit || !citFile}
                    style={{
                      padding: "7px 18px",
                      border: "none",
                      borderRadius: "4px",
                      background: "#0F172A",
                      color: "#FFFFFF",
                      fontSize: "12.5px",
                      fontWeight: "600",
                      cursor: (submittingCit || !citFile) ? "not-allowed" : "pointer"
                    }}
                  >
                    {submittingCit ? "Uploading..." : (citWorker.has_citizenship_doc ? (isNepali ? "प्रतिस्थापन गर्नुहोस्" : "Replace Document") : (isNepali ? "अपलोड गर्नुहोस्" : "Upload Securely"))}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
