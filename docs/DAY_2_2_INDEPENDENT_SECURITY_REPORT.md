# Day 2.2 Independent Authorization Verification and Demo-Safety Report

**Evaluation Date:** 2026-10-16  
**Auditor / Verification Agent:** Antigravity Advanced Agentic Engineering  
**Target System:** LIVO Footwear ERP (FastAPI + SQLAlchemy + Next.js)  
**Evaluation Scope:** Independent verification of Day 2 & Day 2.1 RBAC, HR compensation redaction, multi-tenant company isolation, branch/warehouse scoping, role escalation, and destructive operations for a controlled, 1-week cloud demonstration.  
**Sign-Off Status:** **PASS FOR CONTROLLED DEMO** (Caveats: Not certified for production or real client data; requires Postgres in staging/cloud).

---

## 1. Executive Summary & Verification Findings

This report delivers an independent, evidence-backed evaluation of the access control posture of LIVO Footwear ERP. We audited the actual codebase, ran live adversarial tests across SQLite and embedded PostgreSQL, inspected route dependencies, and validated frontend build invariants.

### Categorized Status Matrix:

| Category | Count / Status | Notes |
| :--- | :--- | :--- |
| **Verified & Passing** | **141 routes audited, 21 adversarial tests passing** | Multi-tenant isolation verified across Auth, Branches, Warehouses, Transfers, Adjustments, Purchasing, BOM, Sales, Fixed Assets, and Expenses. |
| **Fixed & Regression-Tested** | **2 Security Defect Remediations** | 1. HR compensation zero-masking replaced with permission-aware field omission (`response_model_exclude_unset=True`).<br>2. Last active administrator lockout defense added to `PATCH /auth/users/{id}`. |
| **Partially Verified** | **Branch-level user assignment** | Multi-branch and multi-warehouse exist at the company level. Intra-company user scoping to a single branch is not implemented in the current user schema (tenant-level user model). |
| **Limitations Requiring Client Decision** | **Branch-specific RBAC roles** | Whether a store clerk or branch manager should be blocked from seeing another branch within the *same* company is an open business decision for Phase 6/7. |
| **Untested Scopes** | **General Ledger & Live Production** | Day 3 General Ledger is strictly excluded per instructions; testing used synthetic demo data only. |

---

## 2. End-to-End Verification of HR Compensation Redaction

### 2.1 Audit of Sensitive Paths
We conducted a complete audit of all endpoints capable of disclosing compensation, salary, hourly wage rates, overtime rates, and loan/advance balances:

1. **`GET /api/v1/hr/workers`**:
   - **Endpoint Guard:** `get_current_user` (Accessible by Viewer, Editor, Manager, Admin).
   - **Protection Implementation:**
     ```python
     @router.get("/workers", response_model=List[WorkerResponse], response_model_exclude_unset=True)
     ```
     When `current_user.role == "viewer"`, `redact_compensation=True` is passed to `_worker_to_response()`.
     The serializer omits `basic_rate_paisa`, `outstanding_advance_paisa`, `overtime_rate_paisa_override`, `gross_pay_paisa`, `advance_deduction_paisa`, and `net_paid_paisa` from keyword arguments.
   - **Verification:** In `test_hr_compensation_fields_strictly_absent_for_viewer`, assertions prove keys are completely absent from the returned dictionary (`"basic_rate_paisa" not in item`).
2. **`GET /api/v1/hr/workers/{id}/history`**:
   - **Endpoint Guard:** `require_editor` (Admin, Manager, Editor only).
   - **Verification:** Viewers receive **HTTP 403 Forbidden**.
3. **`GET /api/v1/hr/workers/{id}/citizenship`**:
   - **Endpoint Guard:** `require_admin` (Admin only).
   - **Verification:** Viewers, Editors, and Managers receive **HTTP 403 Forbidden**.
4. **`POST /api/v1/hr/monthly-payroll`**:
   - **Endpoint Guard:** `require_editor`.
   - **Verification:** Viewers receive **HTTP 403 Forbidden**.
5. **`GET /api/v1/reports/daily` & `GET /api/v1/reports/stock`**:
   - Audited for indirect leaks: `reports.py` returns `worker_count` (integer headcount on factory floor), not worker compensation or payroll paisa.
6. **Frontend Consumer Safeguards (`HRManagementView.tsx`)**:
   - Total advances KPI card checks for missing fields and displays `[Restricted]` instead of misleading `NPR 0.00`.
   - Table and card views render explicit `[Restricted]` badges.
   - CSV export outputs `"[RESTRICTED]"` for salary and loan fields.
   - Verified via Next.js production compilation: `npm run build` completed with exit code 0.

---

## 3. Endpoint Authorization Matrix Summary

A full inventory of all 141 application routes was extracted directly from the FastAPI application registry and compiled in [`docs/DAY_2_2_ENDPOINT_AUTHORIZATION_MATRIX.md`](file:///d:/Antigravity/Footwear%20app/docs/DAY_2_2_ENDPOINT_AUTHORIZATION_MATRIX.md).

### Distribution of Roles Across 141 Routes:
- **Public / Unauthenticated (10 routes):** OpenAPI specs (`/api/v1/openapi.json`), Swagger/Redoc UI (`/docs`, `/redoc`), Health probes (`/health`, `/health/live`, `/health/ready`), Authentication session endpoints (`/auth/login`, `/auth/logout`), and Prometheus metric endpoints.
- **`get_current_user` (Viewer+ - 58 routes):** Read-only listing and detail retrieval across catalog, inventory balances, sales orders, stock movements, reports, analytics, and HR worker list.
- **`require_editor` (Editor+ - 60 routes):** Standard transactional mutations (sales orders, stock transfers, dispatches, goods receipts, production batches, payroll processing, customer/supplier updates).
- **`require_manager` (Manager+ - 0 direct, subset of editor):** Defined in `deps.py` for supervisor escalations.
- **`require_admin` (Admin Only - 13 routes):** User administration (`/auth/users`), database backups (`/backup/run`), system telemetry (`/ops/telemetry`), diagnostic log download (`/diagnostics/download`), worker citizenship government documents (`/hr/workers/{id}/citizenship`), company HR settings (`/hr/settings`), and balance-sheet destructive deletions (`/assets/fixed-assets/{id}`, `/production/bom/{id}`, `/sales/expenses/{id}`).

---

## 4. Adversarial Multi-Tenant Company Isolation

We proved tenant isolation across 10 distinct functional modules by spinning up two isolated tenant companies (`Company A`, `Company B`) with distinct users, products, warehouses, workers, and clients.

### Attack Vector Verification Table:

| Target Endpoint | Adversarial Tampering Vector | Enforced Guard | HTTP Response | State Mutation? |
| :--- | :--- | :--- | :--- | :--- |
| `PATCH /api/v1/auth/users/{b}` | Admin A updates User B | `filter(User.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `GET /api/v1/branches/{b}` | User A reads Branch B | `filter(Branch.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/branches/{a}/warehouses` | User A assigns Warehouse B to Branch A | `filter(Warehouse.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `GET /api/v1/transfers/{b}` | User A inspects Transfer B | `filter(StockTransfer.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/transfers` | Source warehouse set to Warehouse B | Cross-tenant warehouse lookup | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/stock/adjustments` | Warehouse set to Warehouse B | `filter(Warehouse.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/purchase/purchases` | Supplier set to Supplier B | `filter(Supplier.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/production/bom` | Raw material set to Material B | `filter(RawMaterial.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `POST /api/v1/sales/orders` | Client set to Client B | `filter(Client.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `DELETE /api/v1/fixed-assets/{b}` | Admin A deletes Asset B | `filter(FixedAsset.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |
| `DELETE /api/v1/sales/expenses/{b}` | Admin A deletes Expense B | `filter(SalesExpense.company_id == current_user.company_id)` | **HTTP 404** | **Zero mutation** |

**Zero Data Mutation Invariant:** Verified in `test_rejected_cross_company_operations_preserve_data_invariants`. When malicious cross-tenant payloads were submitted, database counts for `StockMovement` and `SalesOrder` remained strictly unchanged.

---

## 5. Company Scope vs. Branch Scope Clarification

### 5.1 Architecture & Domain Model
1. **Tenant Model:** The top-level isolation unit is `Company` (`company_id`).
2. **Branch Model:** Added in Migration 023. Represents geographical operating locations (e.g. Kathmandu Branch, Birgunj Factory).
3. **Warehouse Model:** Each warehouse has `company_id` and an optional `branch_id`.
4. **User Model:**
   - The `users` table contains: `id`, `company_id`, `name`, `username`, `email`, `role`, `active`.
   - **The `users` table does NOT contain a `branch_id` or `warehouse_id`.**

### 5.2 Documented Scoping Rules for Demonstration
- Users belong to the **company**.
- An authenticated user has company-wide visibility across all branches and warehouses belonging to that company, bounded by their RBAC role (`admin`, `editor`, `viewer`).
- Intra-company stock transfers require distinct `source_warehouse_id` and `destination_warehouse_id` within the company. Same-warehouse transfers are rejected (**HTTP 400**).
- **Limitation / Open Decision:** If the business requires a warehouse clerk to be restricted only to Branch 1 inventory, a future migration adding `users.branch_id` or a join table `user_branches` must be introduced. For the upcoming demo, user access is accurately labeled as **Tenant-Scoped (Company-Wide)**.

---

## 6. Role Escalation and Destructive Operations

### 6.1 Vertical Privilege Escalation Defense
- Endpoints: `POST /api/v1/auth/users`, `PATCH /api/v1/auth/users/{id}`, `GET /api/v1/auth/users`
- Enforced Dependency: `require_admin`
- Non-admin attempts:
  - Manager attempting user creation: **HTTP 403 Forbidden**
  - Editor attempting user modification: **HTTP 403 Forbidden**
  - Viewer attempting user listing: **HTTP 403 Forbidden**

### 6.2 Administrator Lockout & Last-Admin Protection
In `backend/app/api/v1/auth.py`, `update_company_user` was enhanced to enforce two layers of lockout defense:
1. **Self-Lockout Defense:** An admin attempting to deactivate (`active=False`) or demote (`role!="admin"`) their own user account is rejected (**HTTP 400**).
2. **Last-Admin Protection:** If an admin attempts to deactivate or demote another admin, the system verifies `other_active_admins > 0`. If `other_active_admins == 0`, the operation is rejected with **HTTP 400 ("Cannot deactivate/demote the last active administrator in the company")**.
- Verified in `test_last_active_admin_protection_comprehensive`.

### 6.3 Destructive Business Operations
- `DELETE /api/v1/fixed-assets/{id}`: Restricts asset write-offs to `admin`.
- `DELETE /api/v1/production/bom/{id}`: Restricts recipe deletions to `admin`.
- `DELETE /api/v1/sales/expenses/{id}`: Restricts sales expense deletions to `admin`.
- In all three endpoints, Editor and Viewer requests yield **HTTP 403 Forbidden**.

---

## 7. Database Engine & Transaction Assumptions

- **SQLite In-Memory / File Engine:** Used for API unit and integration testing. Does not support table-level advisory locks or true multi-process write concurrency.
- **Embedded PostgreSQL (Port 5433):** Used in `test_phase_5_branch_franchise_accounting.py` and `test_phase_5_3_transaction_boundary.py` to prove:
  - Alembic migration reversibility (Revision 023 -> 022 rollback).
  - PostgreSQL row-level locks (`SELECT ... FOR UPDATE`).
  - Session lifecycle and savepoint rollback under failure injection.
  - Concurrency serialization during concurrent dispatches and goods receipts.
- **Cloud Demonstration Assumption:** The staging deployment must run PostgreSQL (e.g. AWS RDS or Supabase) to ensure multi-worker rate limiting and concurrency locks behave as verified in test suites.

---

## 8. Demo-Safety Gate Decision

### **Verdict: PASS FOR CONTROLLED DEMO**

**Criteria Fulfillment:**
1. ✅ **Tenant Isolation:** Zero cross-tenant data leaks across all 10 core domains.
2. ✅ **HR Redaction:** Sensitive compensation fields are strictly omitted from viewer responses.
3. ✅ **Privilege Escalation:** Admin user management is strictly guarded against non-admin roles and self-lockout.
4. ✅ **Zero Side-Effect on Rejection:** Unauthorized and cross-company requests do not partially mutate state.
5. ✅ **Regression Suite:** All 21 adversarial tests pass; full security test suites pass; frontend builds cleanly.

*Certification Disclaimer: This sign-off certifies the system for a controlled demonstration with synthetic data. It is not an enterprise security audit or production warranty.*
