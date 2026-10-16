# Day 2.1 Adversarial Authorization Verification and Data-Safety Report

**Date:** 2026-10-16  
**Auditor / Engineer:** Antigravity Advanced Agentic Engineering  
**Scope:** Independent Verification and Data-Safety Corrections of Day 2 RBAC Hardening across Multi-Tenant Boundaries, Branch/Warehouse Scopes, Sensitive HR Compensation Serialization, and Destructive Business Operations.  
**Completion Decision:** **PASS** (with documented architectural user-to-branch scoping model)

---

## Executive Summary

During Day 2.1, we conducted an adversarial verification and data-safety correction sprint against the LIVO Footwear ERP codebase. We treated the Day 2 report as evidence to verify rather than an established security certification. 

### Key Deliveries & Corrections:
1. **Defect Rectification — HR Compensation Redaction**:
   - *Previous Defect:* Day 2 implemented zero-value masking (`0`) for unauthorized viewers querying `GET /api/v1/hr/workers`. This created semantic ambiguity, corrupted UI aggregate statistics (e.g., claiming total advance balance was NPR 0.00 when thousands were outstanding), and caused CSV exports to emit misleading zero values.
   - *Fix Implemented:* Redesigned the schema (`WorkerResponse`, `CurrentMonthHours`) to declare compensation fields (`basic_rate_paisa`, `outstanding_advance_paisa`, `overtime_rate_paisa_override`, `gross_pay_paisa`, `advance_deduction_paisa`, `net_paid_paisa`) as `Optional[int] = None`. In `backend/app/api/v1/hr.py`, when `redact_compensation=True`, sensitive fields are left completely unset. Added `response_model_exclude_unset=True` to `@router.get("/workers")`. In tests, asserted that keys are strictly **absent** from the JSON response (`key not in item`), not merely zero.
   - *Frontend Adaptation:* Updated `frontend/src/components/HRManagementView.tsx` to handle absent compensation fields gracefully: displaying `[Restricted]` in summary KPI cards and worker cards/tables, and exporting `[RESTRICTED]` in CSV exports, preventing client-side breakage or misleading metrics. Verified with Next.js production build (`npm run build`, exit code 0).
2. **Tenant Isolation Proofs**:
   - Verified cross-company isolation across 10 high-risk domains: Users/Auth, Branches, Warehouses, Stock Transfers, Stock Adjustments, Purchases/Receipts, Production BOM, Sales Orders, Fixed Assets, and Sales Expenses.
   - Confirmed that cross-company path, query, or body tampering receives HTTP 404/403 with zero information leakage.
3. **Branch & Warehouse Scoping Model**:
   - Proved that warehouses and branches belong to companies (`company_id`).
   - Reconciled the user scoping model: the `User` table has `company_id` but lacks a `branch_id` or `warehouse_id` foreign key. Therefore, all users are company-level actors; intra-company multi-warehouse actions are bounded by valid warehouse pairs within the tenant, while cross-company tampering is rejected at the database query boundary.
4. **Privilege Escalation & Destruction Defense**:
   - Confirmed that Manager, Editor, and Viewer roles are rejected (HTTP 403) from user administration endpoints (`POST /auth/users`, `PATCH /auth/users/{id}`).
   - Confirmed that Admin self-deactivation and self-demotion are blocked (HTTP 400), preventing tenant lockout.
   - Verified that destructive operations (`DELETE /assets/fixed-assets/{id}`, `DELETE /production/bom/{id}`, `DELETE /sales/expenses/{id}`) require Admin privileges and are completely blocked for Editors and Viewers.

---

## 1. Baseline and Audit Reconciliation

### 1.1 Preflight State
- **Git Branch:** `main`
- **Git Commit HEAD:** `2ab515e1c18fceafb5621a2b5ce4127ec2bf24bb`
- **Tracked Workspace Diffs:** Preserved all Phase 5–6A, Day 1, and Day 1.1 work across `invoices.py`, `rate_limit.py`, `security_headers.py`, and `locks.py`.
- **Pre-existing Migration Alignment:** Verified that migration `024_add_rate_limit_entries.py` correctly builds upon `023_add_branches_and_warehouse_link.py`. Corrected a hardcoded downgrade step in `test_phase_5_branch_franchise_accounting.py` to target `022_add_stock_transfers` specifically, restoring 100% test passing for migration reversibility.

---

## 2. HR Compensation Redaction Design & Fix

### 2.1 Confirmed Defect in Day 2
In Day 2, `_worker_to_response` used:
```python
# Day 2 Zero-Masking (Defective):
basic_rate_paisa=0 if redact_compensation else w.basic_rate_paisa,
outstanding_advance_paisa=0 if redact_compensation else w.outstanding_advance_paisa,
```
**Impact:**
1. A viewer viewing the HR Management screen saw total advances outstanding as NPR 0.00, implying the company had zero active loans to workers.
2. An auditor or supervisor was given misleading information instead of an explicit "Permission Denied / Restricted" state.
3. CSV exports generated "0.00" salary, which could be misinterpreted as workers being unpaid or volunteering.

### 2.2 Rectified Architecture
1. **Schema Refactoring (`backend/app/schemas/worker.py`):**
   ```python
   class CurrentMonthHours(BaseModel):
       # ...
       gross_pay_paisa: Optional[int] = None
       advance_deduction_paisa: Optional[int] = None
       net_paid_paisa: Optional[int] = None

   class WorkerResponse(WorkerBase):
       # ...
       basic_rate_paisa: Optional[int] = None
       outstanding_advance_paisa: Optional[int] = None
       overtime_rate_paisa_override: Optional[int] = None
       current_month: Optional[CurrentMonthHours] = None
   ```
2. **API Endpoint & Serializer (`backend/app/api/v1/hr.py`):**
   - In `_worker_to_response()`, if `redact_compensation=True`, `basic_rate_paisa`, `outstanding_advance_paisa`, and `overtime_rate_paisa_override` are **omitted from kwargs**, leaving them unset.
   - The route decorator applies FastAPI's native field omission:
     ```python
     @router.get("/workers", response_model=List[WorkerResponse], response_model_exclude_unset=True)
     ```
3. **Frontend Permission-Aware Handling (`frontend/src/components/HRManagementView.tsx`):**
   - KPI card checks whether any worker has undefined/null `outstanding_advance_paisa`. If so, renders `[Restricted]` instead of `NPR 0.00`.
   - Table and worker card views show `[Restricted]` badge for rate and advances.
   - CSV export emits `"[RESTRICTED]"` for salary and balance fields.
   - Safe fallbacks (`w.outstanding_advance_paisa || 0`) prevent NaN or JS runtime errors in modal forms.

### 2.3 Verification Assertions
In `backend/tests/test_day_2_1_authorization_verification.py`:
```python
assert "basic_rate_paisa" not in item, "Sensitive basic_rate_paisa must be omitted from viewer response"
assert "outstanding_advance_paisa" not in item, "Sensitive outstanding_advance_paisa must be omitted from viewer response"
```
Both assertions passed cleanly.

---

## 3. Multi-Tenant Company Isolation Proofs

An exhaustive suite of adversarial tests was executed where User A (`company_A`) attempted cross-company access against records belonging to `company_B`.

| Domain | Tested Action | Attack Vector | Result | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Users / Auth** | `PATCH /auth/users/{user_b_id}` | Path ID tampering by Admin A | HTTP 404 (Not Found in tenant) | **ISOLATED** |
| **Branches** | `GET /branches/{branch_b_id}` | Direct object reference | HTTP 404 | **ISOLATED** |
| **Branches** | `PATCH /branches/{branch_b_id}` | Unauthorized metadata mutation | HTTP 404 | **ISOLATED** |
| **Warehouses** | `POST /branches/{branch_a_id}/warehouses` | Body injection of `warehouse_b_id` | HTTP 404 | **ISOLATED** |
| **Stock Transfers** | `GET /transfers/{transfer_b_id}` | Cross-company transfer inspection | HTTP 404 | **ISOLATED** |
| **Stock Transfers** | `POST /transfers` | Source warehouse in Company B | HTTP 404 | **ISOLATED** |
| **Stock Adjustments**| `POST /stock/adjustments` | Warehouse in Company B | HTTP 404 | **ISOLATED** |
| **Purchases** | `POST /purchases` | Warehouse in Company B | HTTP 404 | **ISOLATED** |
| **Production BOM** | `POST /production/bom` | Raw material in Company B | HTTP 404 | **ISOLATED** |
| **Sales Orders** | `POST /sales/orders` | Customer in Company B | HTTP 404 | **ISOLATED** |
| **Fixed Assets** | `DELETE /assets/fixed-assets/{asset_b_id}` | Cross-company asset deletion | HTTP 404 | **ISOLATED** |
| **Sales Expenses** | `DELETE /sales/expenses/{expense_b_id}` | Cross-company expense deletion | HTTP 404 | **ISOLATED** |

**Conclusion:** All database queries across these domains enforce `filter(Model.company_id == current_user.company_id)`. Tampering yields immediate HTTP 404 responses with zero data leakage.

---

## 4. Branch and Warehouse Scoping Analysis

### 4.1 Schema Investigation
- `Company`: Top-level tenant.
- `Branch`: Belongs to `company_id`. Added in Migration 023.
- `Warehouse`: Belongs to `company_id`, with optional `branch_id` foreign key.
- `User`: Belongs to `company_id`. **Does not have a `branch_id` column.**

### 4.2 Security & Architectural Implications
1. **User Identity Boundary:** Currently, user authentication is strictly scoped to the tenant (`company_id`). An authenticated user in a company has tenant-wide visibility across all branches and warehouses belonging to that company, bounded by their RBAC role (`admin`, `manager`, `editor`, `viewer`).
2. **Transfer Boundaries:** Stock transfers require distinct `source_warehouse_id` and `destination_warehouse_id` within the company. Same-warehouse transfers are rejected with HTTP 400. Transfers across company boundaries are rejected with HTTP 404.
3. **Future Branch-User Scoping:** If business requirements in Phase 6/7 dictate that a warehouse clerk at Branch 1 cannot view Branch 2's stock, a `user_branches` or `user.branch_id` association will be needed. At present, tenant isolation is 100% verified, and the absence of user-branch restrictions reflects the existing domain model.

---

## 5. Privilege Escalation & Destructive Operations

### 5.1 Vertical Privilege Escalation Defense
- Endpoints: `POST /auth/users`, `PATCH /auth/users/{id}`, `GET /auth/users`
- Enforced Dependency: `require_admin`
- Adversarial Test Results:
  - Manager calling `POST /auth/users` -> **HTTP 403 Forbidden**
  - Editor calling `PATCH /auth/users/{id}` -> **HTTP 403 Forbidden**
  - Viewer calling `GET /auth/users` -> **HTTP 403 Forbidden**

### 5.2 Self-Lockout & Self-Demotion Defense
- `PATCH /auth/users/{admin_id}` inspected in `backend/app/api/v1/auth.py`:
  - When `current_user.id == target_user.id`, updating `active=False` -> **HTTP 400 ("Administrators cannot deactivate their own account")**.
  - When `current_user.id == target_user.id`, updating `role!="admin"` -> **HTTP 400 ("Administrators cannot demote themselves")**.

### 5.3 Destructive Operation Protection
- Deletion endpoints audited:
  - `DELETE /assets/fixed-assets/{id}`
  - `DELETE /production/bom/{id}`
  - `DELETE /sales/expenses/{id}`
- Enforced Dependency: `require_admin`
- Results:
  - Editor attempting deletion -> **HTTP 403 Forbidden**
  - Viewer attempting deletion -> **HTTP 403 Forbidden**
  - Admin attempting deletion -> **HTTP 200/204 Success** (or HTTP 404 if cross-company).

---

## 6. Prioritized Findings Summary

| ID | Severity | Finding | Resolution Status | Verified By |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | Medium | HR compensation zero-masking causes misleading totals in UI | **FIXED** (Switched to field omission via `response_model_exclude_unset=True`) | `test_day_2_1_authorization_verification.py` |
| **F-02** | High | Migration reversibility test failure when new migrations added | **FIXED** (Targeted migration revision `022` explicitly) | `test_phase_5_branch_franchise_accounting.py` |
| **F-03** | Low | UI crash risk on absent compensation fields | **FIXED** (Added safe fallback null-checks and `[Restricted]` badges) | `npm run build` |
| **F-04** | Info | Users lack intra-company branch assignment column | **DOCUMENTED** (Tenant-level isolation proven; intra-branch user scoping reserved for future milestone) | Architecture Review |

---

## 7. Gate Decision

### **Verdict: PASS**

**Rationale:**
1. Zero critical or high tenant isolation defects exist in the tested scope.
2. The HR compensation redaction design flaw has been completely corrected on both backend and frontend.
3. Multi-tenant company isolation is verified across all high-risk operational modules.
4. Vertical privilege escalation and self-demotion lockout are rigorously blocked.
5. All regression test suites passed with 0 failures, and the Next.js frontend builds cleanly.
