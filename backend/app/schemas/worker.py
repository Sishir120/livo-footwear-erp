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


class WorkerCreate(WorkerBase):
    pass


class WorkerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    join_date: Optional[dt.date] = None
    pay_type: Optional[str] = None
    basic_rate_paisa: Optional[int] = Field(None, gt=0)
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class CurrentMonthHours(BaseModel):
    month_year: str
    total_working_hours: float = 0.0
    overtime_hours: float = 0.0
    gross_pay_paisa: int = 0
    advance_deduction_paisa: int = 0
    net_paid_paisa: int = 0
    status: str = "NONE"  # NONE, PENDING, PAID


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    worker_code: str
    name: str
    join_date: dt.date
    pay_type: str
    basic_rate_paisa: int
    phone: Optional[str] = None
    is_active: bool
    created_at: dt.datetime
    outstanding_advance_paisa: int = 0
    current_month: Optional[CurrentMonthHours] = None


class AdvanceCreate(BaseModel):
    worker_id: int
    amount_paisa: int = Field(..., gt=0, description="Advance amount in integer paisa")
    entry_type: str = Field("ISSUED", description="'ISSUED' or 'RECOVERED'")
    date: Optional[dt.date] = None
    notes: Optional[str] = Field(None, max_length=255)


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
    created_at: dt.datetime


class MonthlyPayrollRequest(BaseModel):
    worker_id: int
    month_year: str = Field(..., max_length=10, description="YYYY-MM (e.g. 2026-09)")
    total_working_hours: Optional[float] = Field(0.0, ge=0.0)
    overtime_hours: Optional[float] = Field(0.0, ge=0.0)
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
    total_working_hours: float
    overtime_hours: float
    gross_pay_paisa: int
    advance_deduction_paisa: int
    net_paid_paisa: int
    paid_date: Optional[dt.date] = None
    payment_method: Optional[str] = None
    status: str
    created_at: dt.datetime


class WorkerHistoryResponse(BaseModel):
    worker: WorkerResponse
    advances: List[AdvanceResponse]
    monthly_records: List[MonthlyRecordResponse]
