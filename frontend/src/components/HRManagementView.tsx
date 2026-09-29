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
  CheckCircle2,
  XCircle,
  X,
  Phone,
  ArrowUpRight,
  ArrowDownLeft,
  DollarSign,
  TrendingUp,
  SlidersHorizontal,
  ChevronRight
} from "lucide-react";
import { fromPaisa, toPaisa, TABULAR_NUMS_STYLE } from "@/lib/currency";
import { useLocale } from "@/context/LocaleContext";

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
  basic_rate_paisa: number;
  phone: string | null;
  is_active: boolean;
  created_at: string;
  outstanding_advance_paisa: number;
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

  // Add Worker Form State
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newJoinDate, setNewJoinDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [newPayType, setNewPayType] = useState<"SALARY" | "WAGE">("SALARY");
  const [newRateNpr, setNewRateNpr] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [submittingWorker, setSubmittingWorker] = useState(false);
  const [workerFormError, setWorkerFormError] = useState<string | null>(null);

  // Advance Form State
  const [advanceWorkerId, setAdvanceWorkerId] = useState<number | "">("");
  const [advanceType, setAdvanceType] = useState<"ISSUED" | "RECOVERED">("ISSUED");
  const [advanceAmountNpr, setAdvanceAmountNpr] = useState("");
  const [advanceDate, setAdvanceDate] = useState(() => new Date().toISOString().split("T")[0]);
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

  // Toggle Worker Active / Inactive
  const handleToggleStatus = async (worker: Worker) => {
    if (isViewer) return;
    try {
      const res = await fetch(`/api/v1/hr/workers/${worker.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: !worker.is_active })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(err.detail || "Failed to update status");
        return;
      }
      fetchWorkers();
    } catch (e: any) {
      alert(e.message || "Network error updating status");
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
          phone: newPhone.trim() || null
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
    setPayrollAdvanceDeductionNpr(fromPaisa(worker.outstanding_advance_paisa, false));
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
      const basic = selectedPayrollWorker.basic_rate_paisa;
      const hourlyOTRate = (basic / 208) * 1.5;
      return Math.round(basic + (ot * hourlyOTRate));
    } else {
      const hourly = selectedPayrollWorker.basic_rate_paisa;
      return Math.round((twh * hourly) + (ot * hourly * 1.5));
    }
  })();

  const previewAdvanceDeductionPaisa = (() => {
    if (!selectedPayrollWorker) return 0;
    if (payrollAdvanceDeductionNpr === "") {
      return Math.min(previewGrossPaisa, selectedPayrollWorker.outstanding_advance_paisa);
    }
    return Math.min(toPaisa(payrollAdvanceDeductionNpr), selectedPayrollWorker.outstanding_advance_paisa);
  })();

  const previewNetPaidPaisa = Math.max(0, previewGrossPaisa - previewAdvanceDeductionPaisa);

  // Aggregated KPI Stats
  const activeCount = workers.filter((w) => w.is_active).length;
  const totalAdvancesPaisa = workers.reduce((sum, w) => sum + (w.outstanding_advance_paisa || 0), 0);
  const totalHoursThisMonth = workers.reduce((sum, w) => sum + (w.current_month?.total_working_hours || 0), 0);
  const totalOtHoursThisMonth = workers.reduce((sum, w) => sum + (w.current_month?.overtime_hours || 0), 0);
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
      fromPaisa(w.basic_rate_paisa, false),
      w.current_month?.total_working_hours || 0,
      w.current_month?.overtime_hours || 0,
      fromPaisa(w.outstanding_advance_paisa, false),
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
          <div style={{ fontSize: "22px", fontWeight: "700", color: totalAdvancesPaisa > 0 ? "#DC2626" : "#059669", marginTop: "4px", ...TABULAR_NUMS_STYLE }}>
            NPR {fromPaisa(totalAdvancesPaisa)}
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

        {/* Search Input */}
        <div style={{ position: "relative", minWidth: "260px" }}>
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

      {/* Error Banner */}
      {error && (
        <div style={{ background: "#FEF2F2", border: "1px solid #FCA5A5", padding: "10px 14px", borderRadius: "6px", color: "#B91C1C", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Worker Directory Table */}
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
            {loading ? (
              <tr>
                <td colSpan={10} style={{ padding: "30px", textAlign: "center", color: "#64748B" }}>
                  <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px" }} />
                  <div>Loading worker profiles & payroll ledger...</div>
                </td>
              </tr>
            ) : filteredWorkers.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ padding: "40px", textAlign: "center", color: "#64748B" }}>
                  <Users size={32} style={{ margin: "0 auto 8px", opacity: 0.5 }} />
                  <div style={{ fontWeight: "600" }}>No workers found</div>
                  <div style={{ fontSize: "11px", marginTop: "4px" }}>
                    {searchTerm ? "Try adjusting your search criteria" : "Add your first factory worker profile"}
                  </div>
                </td>
              </tr>
            ) : (
              filteredWorkers.map((worker) => {
                const hasAdvance = worker.outstanding_advance_paisa > 0;
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

                    {/* Name & Phone */}
                    <td style={{ padding: "10px 14px" }}>
                      <div style={{ fontWeight: "600", color: "#0F172A" }}>{worker.name}</div>
                      {worker.phone && (
                        <div style={{ fontSize: "11px", color: "#64748B", display: "flex", alignItems: "center", gap: "4px", marginTop: "2px" }}>
                          <Phone size={10} />
                          <span>{worker.phone}</span>
                        </div>
                      )}
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
                      NPR {fromPaisa(worker.basic_rate_paisa)}
                      <span style={{ fontSize: "10.5px", color: "#64748B", fontWeight: "400", marginLeft: "4px" }}>
                        {worker.pay_type === "SALARY" ? "/mo" : "/hr"}
                      </span>
                    </td>

                    {/* Current Month TWH */}
                    <td style={{ padding: "10px 14px", textAlign: "right", color: "#334155", ...TABULAR_NUMS_STYLE }}>
                      {worker.current_month ? worker.current_month.total_working_hours.toFixed(1) : "0.0"} hrs
                    </td>

                    {/* Current Month OT */}
                    <td style={{ padding: "10px 14px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>
                      {worker.current_month && worker.current_month.overtime_hours > 0 ? (
                        <span style={{ fontWeight: "700", color: "#7C3AED" }}>
                          +{worker.current_month.overtime_hours.toFixed(1)} hrs
                        </span>
                      ) : (
                        <span style={{ color: "#94A3B8" }}>0.0 hrs</span>
                      )}
                    </td>

                    {/* Outstanding Advance */}
                    <td style={{ padding: "10px 14px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>
                      {hasAdvance ? (
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

                            {/* Active/Inactive Toggle Button */}
                            <button
                              onClick={() => handleToggleStatus(worker)}
                              title={worker.is_active ? "Mark Inactive" : "Mark Active"}
                              style={{
                                background: "transparent",
                                border: "none",
                                cursor: "pointer",
                                padding: "4px",
                                color: worker.is_active ? "#94A3B8" : "#10B981"
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
              })
            )}
          </tbody>
        </table>
      </div>

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
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    {t("join_date")} *
                  </label>
                  <input
                    type="date"
                    required
                    value={newJoinDate}
                    onChange={(e) => setNewJoinDate(e.target.value)}
                    style={{ width: "100%", padding: "6px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
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

              <div style={{ marginBottom: "18px" }}>
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
                      {w.worker_code} - {w.name} (Due: NPR {fromPaisa(w.outstanding_advance_paisa)})
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
                  <label style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                    Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={advanceDate}
                    onChange={(e) => setAdvanceDate(e.target.value)}
                    style={{ width: "100%", padding: "6px 10px", fontSize: "12.5px", border: "1px solid #CBD5E1", borderRadius: "4px", outline: "none" }}
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
                        setPayrollAdvanceDeductionNpr(fromPaisa(w.outstanding_advance_paisa, false));
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
                  {t("join_date")}: {selectedWorkerForHistory.join_date} • {selectedWorkerForHistory.pay_type === "SALARY" ? t("salary_type") : t("wage_type")} (NPR {fromPaisa(selectedWorkerForHistory.basic_rate_paisa)})
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
                                <td style={{ padding: "8px 10px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>{m.total_working_hours.toFixed(1)}</td>
                                <td style={{ padding: "8px 10px", textAlign: "right", ...TABULAR_NUMS_STYLE }}>{m.overtime_hours.toFixed(1)}</td>
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
    </div>
  );
}
