from decimal import Decimal

import datetime as dt
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class WorkerBase(BaseModel):
    worker_code: str = Field(..., max_length=32, description="Unique worker code, e.g. EMP-101")
    name: str = Field(..., max_length=128, description="Worker full name")
    join_date: Optional[dt.date] = None
    pay_type: str = Field(..., description="'SALARY' for monthly or 'WAGE' for hourly/rate")
    basic_rate_paisa: int = Field(..., gt=0, description="Monthly basic salary or hourly wage in integer paisa")
    phone: Optional[str] = Field(None, max_length=32)
    is_active: bool = Field(True, description="Whether worker is currently active")
    temporary_address: Optional[str] = Field(None, max_length=255, description="Temporary or local address")
    permanent_address: Optional[str] = Field(None, max_length=255, description="Permanent address")
    photo_url: Optional[str] = Field(None, max_length=512, description="Worker profile photograph URL")
    standard_monthly_hours_override: Optional[Decimal] = Field(None, gt=0, le=744, description="Worker override for standard monthly hours (0 < hours <= 744)")
    overtime_rate_paisa_override: Optional[int] = Field(None, gt=0, description="Worker override for fixed hourly overtime rate in integer paisa")


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    join_date: Optional[dt.date] = None
    pay_type: Optional[str] = None
    basic_rate_paisa: Optional[int] = Field(None, gt=0)
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    temporary_address: Optional[str] = Field(None, max_length=255)
    permanent_address: Optional[str] = Field(None, max_length=255)
    photo_url: Optional[str] = Field(None, max_length=512)
    inactive_date: Optional[dt.date] = None
    inactive_reason: Optional[str] = Field(None, max_length=255)
    standard_monthly_hours_override: Optional[Decimal] = Field(None, gt=0, le=744)
    overtime_rate_paisa_override: Optional[int] = Field(None, gt=0)


class WorkerStatusUpdate(BaseModel):
    is_active: bool
    inactive_reason: Optional[str] = Field(None, max_length=255)
    inactive_date: Optional[dt.date] = None


class CitizenshipDocResponse(BaseModel):
    has_citizenship_doc: bool
    citizenship_doc_name: Optional[str] = None
    uploaded_at: Optional[dt.datetime] = None


class CurrentMonthHours(BaseModel):
    month_year: str
    total_working_hours: Decimal = Decimal("0.0")
    overtime_hours: Decimal = Decimal("0.0")
    gross_pay_paisa: Optional[int] = None
    advance_deduction_paisa: Optional[int] = None
    net_paid_paisa: Optional[int] = None
    status: str = "NONE"  # NONE, PENDING, PAID


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    worker_code: str
    name: str
    join_date: dt.date
    pay_type: str
    basic_rate_paisa: Optional[int] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    temporary_address: Optional[str] = None
    permanent_address: Optional[str] = None
    is_active: bool
    inactive_date: Optional[dt.date] = None
    inactive_reason: Optional[str] = None
    has_citizenship_doc: bool = False
    citizenship_doc_name: Optional[str] = None
    standard_monthly_hours_override: Optional[Decimal] = None
    overtime_rate_paisa_override: Optional[int] = None
    created_at: dt.datetime
    outstanding_advance_paisa: Optional[int] = None
    current_month: Optional[CurrentMonthHours] = None


class AdvanceCreate(BaseModel):
    worker_id: int
    amount_paisa: int = Field(..., gt=0, description="Advance amount in integer paisa")
    entry_type: str = Field("ISSUED", description="'ISSUED' or 'RECOVERED'")
    date: Optional[dt.date] = None
    notes: Optional[str] = Field(None, max_length=255)
    installment_amount_paisa: Optional[int] = Field(None, gt=0, description="Fixed monthly installment in integer paisa (for ISSUED advances)")
    parent_advance_id: Optional[int] = Field(None, description="Target parent advance ID if direct cash repayment (for RECOVERED advances)")


class AdvanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    worker_id: int
    amount_paisa: int
    entry_type: str
    date: dt.date
    notes: Optional[str] = None
    actor_id: int
    installment_amount_paisa: Optional[int] = None
    parent_advance_id: Optional[int] = None
    monthly_record_id: Optional[int] = None
    remaining_principal_paisa: Optional[int] = None
    allocations: Optional[List["AdvanceResponse"]] = None
    created_at: dt.datetime


class MonthlyPayrollRequest(BaseModel):
    worker_id: int
    month_year: str = Field(..., max_length=10, description="YYYY-MM (e.g. 2026-09)")
    total_working_hours: Optional[Decimal] = Field(0.0, ge=0.0)
    overtime_hours: Optional[Decimal] = Field(0.0, ge=0.0)
    gross_pay_paisa: Optional[int] = Field(None, ge=0, description="Optional override; auto-calculated if None")
    advance_deduction_paisa: Optional[int] = Field(None, ge=0, description="Optional override; auto-deducted if None")
    mark_as_paid: bool = Field(False, description="Set to True to record as finalized payment")
    paid_date: Optional[dt.date] = None
    payment_method: Optional[str] = Field("CASH", description="'CASH' or 'BANK'")


class MonthlyRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    worker_id: int
    month_year: str
    total_working_hours: Decimal
    overtime_hours: Decimal
    gross_pay_paisa: int
    advance_deduction_paisa: int
    net_paid_paisa: int
    paid_date: Optional[dt.date] = None
    payment_method: Optional[str] = None
    status: str

    # Calculation snapshots
    basic_rate_paisa_snapshot: Optional[int] = None
    standard_hours_snapshot: Optional[Decimal] = None
    overtime_multiplier_snapshot: Optional[Decimal] = None
    overtime_rate_paisa_snapshot: Optional[int] = None
    regular_pay_paisa: Optional[int] = None
    overtime_pay_paisa: Optional[int] = None
    ceiling_pct_snapshot: Optional[int] = None

    created_at: dt.datetime


class WorkerHistoryResponse(BaseModel):
    worker: WorkerResponse
    advances: List[AdvanceResponse]
    monthly_records: List[MonthlyRecordResponse]


class HRSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    company_id: int
    standard_monthly_hours: Decimal
    overtime_multiplier: Decimal
    max_advance_deduction_pct: Optional[int] = 50
    updated_at: Optional[dt.datetime] = None
    updated_by_id: Optional[int] = None


class HRSettingsUpdate(BaseModel):
    standard_monthly_hours: Decimal = Field(..., gt=0, le=744, description="Standard monthly hours (0 < hours <= 744)")
    overtime_multiplier: Decimal = Field(..., ge=Decimal("1.0"), le=Decimal("5.0"), description="Overtime multiplier (1.0 to 5.0)")
    max_advance_deduction_pct: Optional[int] = Field(50, ge=1, le=50, description="Ordinary deduction ceiling percentage (1 to 50%)")
