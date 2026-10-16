# LIVO ERP — Day 2 Authorization Forensics & RBAC Audit

**Date:** October 16, 2026  
**Auditor:** LIVO Core Engineering & Security Team  
**Scope:** Complete forensic audit of endpoint authorization, tenant isolation, and RBAC mechanisms across all 20 API routing modules (`backend/app/api/v1/*.py`).  
**Environment Baseline:** Branch `main` @ `2ab515e`, Python 3.14.7, Next.js 14.2.35.

---

## 1. Executive Summary & Preflight Baseline

### 1.1 Workspace Integrity & Preflight State
- **Branch:** `main`
- **HEAD Commit:** `2ab515e` (*feat(database): add migration 021 for document_sequences and add resilient allocation fallback*)
- **Working Tree State:** Clean preservation of Day 1.1 fixes and pre-existing Phase 5–6A branch and franchise accounting artifacts. No files were reset, stashed, discarded, or staged.
- **Preflight `git diff --stat`:** 23 files modified (`backend/app/api/v1/invoices.py`, `rate_limit.py`, `security_headers.py`, `test_checkpoint_11_database.py`, `test_checkpoint_17_production_readiness.py`, `test_checkpoint_18_live_acceptance.py`, etc.).

### 1.2 Core Audit Takeaways
1. **Coarse-Grained 2-Tier Role Model:** The database `users` table only supports a single `role` column (`admin`, `editor`, `viewer`). While `docs/AUTHORIZATION_MATRIX.md` theoretically describes 4 roles (`ADMIN`, `MANAGER`, `OPERATOR`, `VIEWER`), the actual code in `backend/app/api/deps.py` only implements two guards: `require_editor` (accepting `editor` and `admin`) and `require_admin` (accepting only `admin`).
2. **Missing Segregation of Duties for Fiscal & Ledger Reversals:** Sensitive operations that void or reverse statutory transactions—such as canceling finalized VAT invoices, issuing credit notes, reversing stock ledger movements, and deleting fixed assets—currently only require `require_editor`. Any basic operational editor can execute financial reversals and ledger cancellations.
3. **Loophole in Downward Stock Adjustment Authorization:** `POST /api/v1/stock/adjustments` nominally requires `admin` or a supervisor token for downward adjustments (`quantity_delta < 0`). However, an explicit bypass exists: if `payload.reason_code` is set to `"RECOUNT"` or `"RECOUNT_CORRECTION"`, the supervisor verification is skipped entirely, allowing any editor to unilaterally write off warehouse inventory.
4. **Worker Compensation & Advance Exposure to Viewers:** `GET /api/v1/hr/workers` and `GET /api/v1/hr/workers/{worker_id}/history` only require `get_current_user`. Any authenticated read-only user (e.g., guest, catalog viewer, entry clerk) can view confidential salary figures, basic wage rates, gross monthly earnings, and cash advance balances for all workers.
5. **Structural Company Configuration Granted to Editors:** In `backend/app/api/v1/branches.py`, branch creation, deactivation, and warehouse-to-branch assignment are guarded by `require_editor` rather than `require_admin`, permitting non-administrative personnel to restructure organizational operating units.
6. **Robust Tenant Isolation:** On a positive note, cross-tenant isolation is rigorously enforced across nearly all endpoints via explicit `filter(Model.company_id == current_user.company_id)` or `TenantRepository` constructs. Authenticated users cannot specify or override `company_id`.

---

## 2. Global Authorization Architecture

### 2.1 Request & Authentication Flow
$$\text{HTTP Request} \longrightarrow \text{Starlette Middleware} \longrightarrow \text{FastAPI Dependency (get\_current\_user)} \longrightarrow \text{Role Guard} \longrightarrow \text{Route Handler} \longrightarrow \text{DB Query (company\_id Scoped)} \longrightarrow \text{Response}$$

- **Authentication Method:** First-party `httpOnly` cookie (`livo_access_token`) decoded via `decode_access_token` in `backend/app/core/security.py`. Fallback Bearer header inspection is provided for API testing.
- **Claims Extracted:** `user_id`, `company_id`, `role`, `sub` (username).
- **User Validation:** Checks `User.active == True` and matching `User.company_id == token.company_id`.

### 2.2 Existing Dependencies in `backend/app/api/deps.py`
| Dependency | Check Logic | Allowed Roles | Rejection Behavior |
|---|---|---|---|
| `get_current_user` | Validates session cookie or Bearer token; queries active user in DB | `admin`, `editor`, `viewer` | `401 Unauthorized` |
| `require_editor` | `current_user.role in ("editor", "admin")` | `editor`, `admin` | `403 Forbidden` |
| `require_admin` | `current_user.role == "admin"` | `admin` | `403 Forbidden` |

---

## 3. Comprehensive Endpoint Inventory & Access Control Matrix

### Module 1: Authentication & User Administration (`/api/v1/auth`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `POST /auth/login` | None | Public | N/A | Route / DB | Read (verify password) | `test_day_1_hardening.py` | Low (Public authentication endpoint) |
| `POST /auth/logout` | None | Any | N/A | Route | Cookie eviction | `test_auth.py` | Low |
| `GET /auth/me` | Session | Any valid | Tenant-bound | Route (`current_user`) | Read | `test_auth.py` | Low |
| `GET /auth/users` | Session | `admin` | `company_id == current_user.company_id` | Route / DB query | Read | `test_phase_16_2_security_remediations.py` | Low (Admin only, tenant isolated) |
| `POST /auth/users` | Session | `admin` | Inserts with `current_user.company_id` | Route / DB insert | Create | `test_phase_16_2_security_remediations.py` | Low (Admin only, tenant locked) |
| `PATCH /auth/users/{user_id}` | Session | `admin` | `company_id == current_user.company_id` | Route / DB query | Update | `test_auth.py` | **Medium (VULN-02):** Admin can deactivate or demote self, potentially locking out the tenant if sole admin |

---

### Module 2: Branches & Divisions (`/api/v1/branches`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /branches` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_branches.py` | Low |
| `POST /branches` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create | `test_branches.py` | **Medium:** Branch creation should be restricted to `admin` |
| `GET /branches/{id}` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_branches.py` | Low |
| `PUT /branches/{id}` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Update | `test_branches.py` | **Medium:** Branch editing should be restricted to `admin` |
| `PATCH /branches/{id}/toggle-active` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Update | `test_branches.py` | **High:** Operating branch deactivation should require `admin` |
| `POST /branches/{id}/warehouses` | Session | `editor` | Both branch & warehouse checked for `company_id` | DB Query | Update / Link | `test_branches.py` | **Medium:** Warehouse assignment to branches should require `admin` |
| `DELETE /branches/{id}/warehouses/{id}` | Session | `editor` | Both branch & warehouse checked for `company_id` | DB Query | Update / Unlink | `test_branches.py` | **Medium:** Warehouse unlinking should require `admin` |

---

### Module 3: Stock Transfers (`/api/v1/transfers`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /transfers` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_stock_transfers.py` | Low |
| `POST /transfers` | Session | `editor` | Source/dest warehouses checked for tenant | Route / DB insert | Create (Draft) | `test_stock_transfers.py` | Low |
| `GET /transfers/{id}` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_stock_transfers.py` | Low |
| `POST /transfers/{id}/dispatch` | Session | `editor` | Row-locked, source stock checked | Route / Service | Mutate (Stock Deduct) | `test_stock_transfers.py` | Low (Checks on-hand balance) |
| `POST /transfers/{id}/receive` | Session | `editor` | Row-locked, over-receipt prevented | Route / Service | Mutate (Stock Add) | `test_stock_transfers.py` | **Medium (VULN-06):** No segregation of duties; dispatcher can immediately confirm receipt without independent verification |
| `POST /transfers/{id}/cancel` | Session | `editor` | Status must be DRAFT, tenant isolated | Route / Service | Mutate (Cancel) | `test_stock_transfers.py` | Low |

---

### Module 4: Stock & Inventory (`/api/v1/stock`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /stock/movements` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_stock.py` | Low |
| `POST /stock/movements` | Session | `editor` | Product & warehouse verified for tenant | Route / DB insert | Create (Mutate) | `test_stock.py` | Low |
| `GET /stock/balance` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_stock.py` | Low |
| `GET /stock/ledger` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_stock.py` | Low |
| `POST /stock/adjustments` | Session | `editor` | Product & warehouse verified for tenant | Route / Service | Create (Ledger Adjust) | `test_checkpoint_16_business_security.py` | **CRITICAL (VULN-01):** Negative adjustments bypass admin/supervisor checks if `reason_code='RECOUNT'`. Positive adjustments require no supervisor token |
| `POST /stock/reversals/{movement_id}` | Session | `editor` | Verified for tenant, zero-floor checked | Route / Service | Reverse (Ledger Reversal) | `test_checkpoint_16_business_security.py` | **HIGH (VULN-05):** Inventory ledger reversal should require `admin` authorization |

---

### Module 5: Invoices & Statutory Billing (`/api/v1/invoices`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /invoices` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_vat_compliance_and_calculation.py` | Low |
| `POST /invoices` | Session | `editor` | Sales order & client verified for tenant | Route / DB insert | Create (Draft) | `test_vat_compliance_and_calculation.py` | Low |
| `GET /invoices/{id}` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_vat_compliance_and_calculation.py` | Low |
| `POST /invoices/{id}/finalize` | Session | `editor` | Row-locked, tenant scoped | Route / Service | Post (Issue Tax Invoice) | `test_invoice_immutability_and_credit_notes.py` | Low (Generates sequential number and AR debit) |
| `POST /invoices/{id}/credit-note` | Session | `editor` | Row-locked, creditable ceiling checked | Route / Service | Reverse / Adjust | `test_invoice_immutability_and_credit_notes.py` | **HIGH (VULN-05):** Statutory Schedule-10 credit note reduces taxable sales and customer debt; should require `admin` |
| `POST /invoices/{id}/cancel` | Session | `editor` | Row-locked, void reversal posted to AR | Route / Service | Reverse (Void Invoice) | `test_invoice_immutability_and_credit_notes.py` | **HIGH (VULN-05):** Voiding finalized tax invoices reverses accounting entries; should require `admin` |

---

### Module 6: HR & Payroll Management (`/api/v1/hr`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /hr/workers` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_hr.py` | **HIGH (VULN-04):** Viewers can see worker basic rates, monthly earnings, and advance balances |
| `POST /hr/workers` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create | `test_hr.py` | Medium: Creating worker profiles should be restricted to `admin` |
| `PATCH /hr/workers/{id}` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Update | `test_hr.py` | Medium: Updating wage rates/salaries should require `admin` |
| `PATCH /hr/workers/{id}/status` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Update | `test_hr.py` | Low |
| `POST /hr/advances` | Session | `editor` | Worker checked, balance verified | Route / Service | Create (Disburse Advance) | `test_hr.py` | Medium: Disbursing cash advances is a financial mutation |
| `GET /hr/workers/{id}/history` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_hr.py` | **HIGH (VULN-04):** Viewers can inspect full compensation and advance ledger history |
| `POST /hr/monthly-payroll` | Session | `editor` | Row-locked, advance recovered | Route / Service | Post (Finalize Payroll) | `test_hr.py` | **HIGH:** Finalizing and paying monthly payroll should require `admin` |
| `GET /hr/settings` | Session | `admin` | `company_id == current_user.company_id` | DB Query | Read | `test_hr.py` | Low (Properly restricted to Admin) |
| `PUT /hr/settings` | Session | `admin` | `company_id == current_user.company_id` | DB Query | Update | `test_hr.py` | Low (Properly restricted to Admin) |
| `POST /hr/workers/{id}/citizenship` | Session | `admin` | `company_id == current_user.company_id` | Route / Storage | Upload Document | `test_hr.py` | Low (Properly restricted to Admin) |
| `GET /hr/workers/{id}/citizenship` | Session | `admin` | Path traversal checked, tenant scoped | Route / Storage | Read Document | `test_hr.py` | Low (Properly restricted to Admin) |
| `DELETE /hr/workers/{id}/citizenship` | Session | `admin` | Path traversal checked, tenant scoped | Route / Storage | Delete Document | `test_hr.py` | Low (Properly restricted to Admin) |

---

### Module 7: Purchases & Raw Materials (`/api/v1/purchase`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /purchase/suppliers` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_purchase.py` | Low |
| `POST /purchase/suppliers` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create | `test_purchase.py` | Low |
| `GET /purchase/raw-materials` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_purchase.py` | Low |
| `POST /purchase/raw-materials` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create | `test_purchase.py` | Low |
| `GET /purchase/purchases` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_purchase.py` | Low |
| `POST /purchase/purchases` | Session | `editor` | Supplier & items verified for tenant | Route / DB insert | Create (Purchase PO) | `test_purchase.py` | Low |
| `POST /purchase/purchases/{id}/receive` | Session | `editor` | Row-locked, raw stock added | Route / Service | Mutate (Goods Receipt) | `test_purchase.py` | Low |
| `POST /purchase/materials/{id}/adjust` | Session | `editor` | Material verified, balance adjusted | Route / Service | Mutate (Raw Stock Adjust) | `test_purchase.py` | **Medium:** Raw material stock adjustment should require supervisor or admin |

---

### Module 8: Accounts Receivable (`/api/v1/receivables`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /receivables/aging` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_checkpoint_15_query_regression.py` | Low |
| `GET /receivables/statement/{id}` | Session | Any valid | Client verified for tenant | DB Query | Read | `test_receivables.py` | Low |
| `POST /receivables/payments` | Session | `editor` | Allocations verified for tenant & client | Route / Service | Create (Post Payment) | `test_checkpoint_16_business_security.py` | Low (Allocation IDOR defense verified) |
| `POST /receivables/dispute/{id}` | Session | `editor` | Entry verified for tenant | DB Query | Update (Toggle Dispute) | `test_receivables.py` | Low |

---

### Module 9: Production & Manufacturing (`/api/v1/production`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /production/products` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_production.py` | Low |
| `POST /production/products` | Session | `editor` | Product code uniqueness in tenant | Route / DB insert | Create | `test_production.py` | Low |
| `GET /production/bom` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_production.py` | Low |
| `POST /production/bom` | Session | `editor` | Product & raw material in tenant | Route / DB insert | Create | `test_production.py` | Low |
| `DELETE /production/bom/{id}` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Delete | `test_production.py` | **Medium:** BOM recipe deletion should require `admin` |
| `GET /production/batches` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_production.py` | Low |
| `POST /production/batches` | Session | `editor` | BOM & raw materials checked, deducted | Route / Service | Mutate (Issue & Produce) | `test_production.py` | Low |
| `POST /production/sync/draft` | Session | `editor` | Batch sync payload verified for tenant | Route / Service | Bulk Sync | `test_production.py` | Low |

---

### Module 10: Sales & Expenses (`/api/v1/sales`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /sales/clients` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_sales.py` | Low |
| `POST /sales/clients` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create | `test_sales.py` | Low |
| `GET /sales/orders` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_sales.py` | Low |
| `POST /sales/orders` | Session | `editor` | Client & stock availability verified | Route / Service | Create Order | `test_sales.py` | Low |
| `POST /sales/orders/{id}/dispatch` | Session | `editor` | Stock deducted, order marked DISPATCHED | Route / Service | Mutate (Dispatch) | `test_sales.py` | Low |
| `POST /sales/expenses` | Session | `editor` | `company_id = current_user.company_id` | Route / DB insert | Create Expense | `test_sales.py` | Low |
| `GET /sales/expenses` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_sales.py` | Low |
| `DELETE /sales/expenses/{id}` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Delete | `test_sales.py` | **Medium:** Deleting expense records should require `admin` |

---

### Module 11: Fixed Assets Register (`/api/v1/fixed-assets`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /fixed-assets` | Session | Any valid | `company_id == current_user.company_id` | DB Query | Read | `test_assets.py` | Low |
| `POST /fixed-assets` | Session | `editor` | Asset code uniqueness in tenant | Route / DB insert | Create Asset | `test_assets.py` | Low |
| `DELETE /fixed-assets/{id}` | Session | `editor` | `company_id == current_user.company_id` | DB Query | Delete Asset | `test_assets.py` | **HIGH (VULN-05):** Capital asset deletion removes balance-sheet value; must require `admin` |

---

### Module 12: Fixed Asset & Operating Telemetry (`/api/v1/ops` & `/api/v1/backup`)
| Route & Method | Auth Req | Role Required | Scope Check | Enforcement Layer | Operation | Evidence in Tests | Severity & Finding |
|---|---|---|---|---|---|---|---|
| `GET /ops/telemetry` | Session | `admin` | `company_id == current_user.company_id` | DB Query | Read System Health | `test_ops.py` | Low (Properly restricted) |
| `GET /backup/status` | Session | Any valid | Global / Tenant | Service | Read Backup Status | `test_backup.py` | Low |
| `GET /backup/health` | Session | Any valid | Global / Tenant | Service | Read Backup Health | `test_backup.py` | Low |
| `POST /backup/run` | Session | `admin` | System DB Dump | Service | Create DB Dump | `test_backup.py` | Low (Properly restricted to Admin) |

---

## 4. Confirmed Critical & High-Risk Authorization Gaps

1. **VULN-01 (Critical): Stock Adjustment Downward Write-Off Bypass via RECOUNT:**
   - *Location:* `backend/app/api/v1/stock.py:667-668`
   - *Vulnerability:* The condition `if not is_recount and current_user.role != "admin"` allows any editor to reduce stock without supervisor token or admin role simply by setting `reason_code = "RECOUNT"`. Furthermore, upward stock adjustments have zero admin authorization.
2. **VULN-02 (Medium): Self-Demotion and Self-Lockout in User Management:**
   - *Location:* `backend/app/api/v1/auth.py:119-152`
   - *Vulnerability:* An administrator can deactivate their own account or downgrade their own role to viewer, creating a tenant lockout if no other active administrator exists.
3. **VULN-04 (High): Worker Compensation Data Exposed to Unprivileged Viewers:**
   - *Location:* `backend/app/api/v1/hr.py:217` & `backend/app/api/v1/hr.py:624`
   - *Vulnerability:* `GET /api/v1/hr/workers` and `GET /api/v1/hr/workers/{id}/history` require only `get_current_user`. Viewers can inspect base salaries, overtime rates, and advance balances.
4. **VULN-05 (High): Reversals, Credit Notes, and Asset Deletions Permitted to Editors:**
   - *Location:* `backend/app/api/v1/invoices.py:432` (`credit-note`), `invoices.py:521` (`cancel`), `stock.py:737` (`reversals`), `assets.py:125` (`delete`).
   - *Vulnerability:* Operational editors can cancel finalized tax invoices, issue credit notes, reverse stock ledger movements, and delete fixed capital assets without managerial or administrative oversight.
5. **VULN-06 (Medium): Branch Structural Configuration Allowed by Editors:**
   - *Location:* `backend/app/api/v1/branches.py:68, 123, 173, 214, 251`
   - *Vulnerability:* Non-administrative editors can create branches, toggle operating status, and link/unlink warehouses.
