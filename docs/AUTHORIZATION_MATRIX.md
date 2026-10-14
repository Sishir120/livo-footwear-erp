# LIVO FOOTWEAR ERP — AUTHORIZATION & ENDPOINT ACCESS CONTROL MATRIX

**Document Version:** 1.0.0 (Checkpoint 16 Adversarial Security Audit)  
**Standard:** NIST SP 800-53 AC-3 (Access Enforcement) / OWASP API Security Top 10 2023  
**Scope:** Complete inventory of all 69 API endpoints across all 15 routing modules in `backend/app/api/v1/`.

---

## 1. Methodology & Tracing Model

Every endpoint is evaluated against the complete request execution lifecycle:
$$\text{HTTP Request} \longrightarrow \text{FastAPI Dependency} \longrightarrow \text{Authentication (JWT / Bearer)} \longrightarrow \text{Role Enforcement (RBAC)} \longrightarrow \text{Tenant Scoping (Company ID)} \longrightarrow \text{Object Ownership (IDOR / BOLA check)} \longrightarrow \text{Mutation / Query}$$

### Roles Recognized:
- **`ADMIN`**: Full administrative privileges over tenant domain, settings, backup, HR payroll, and financials.
- **`MANAGER`**: Operational management over inventory, production, sales, clients, and receivables.
- **`OPERATOR`**: Execution role (stock movements, production orders, attendance recording).
- **`VIEWER`**: Read-only inspection across non-sensitive operational records.
- **`PUBLIC` / `UNAUTHENTICATED`**: Unauthenticated public endpoints (login, registration, health check, public telemetry ping).

---

## 2. Global Authorization Architecture

1. **Authentication:** Bearer token passed in `Authorization: Bearer <JWT>` validated via `get_current_user` in `backend/app/core/security.py`. Rejects expired, tampered, or missing company/user claims.
2. **Tenant Isolation:** Enforced at the repository and query layer via `Model.company_id == current_user.company_id`. No endpoint allows an authenticated user to specify or override `company_id`.
3. **Role Enforcement:** Handled declaratively via `require_role(["ADMIN", ...])` dependency or programmatically inside route handlers.
4. **Standard Rejection Codes:**
   - **401 Unauthorized**: Missing, malformed, or expired Bearer token.
   - **403 Forbidden**: Valid token, but caller role has insufficient permissions or is attempting cross-tenant access.
   - **404 Not Found**: Standard defensive response for BOLA/IDOR object lookups to prevent cross-tenant enumeration.
   - **422 Unprocessable Entity**: Invalid schema or data constraint violation.

---

## 3. Complete Endpoint Inventory (69 Endpoints)

### 3.1 Authentication & Profile (`/api/v1/auth`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 1 | POST | `/api/v1/auth/login` | None | Public | N/A | User credential | `password` | None (Token issue) | `401 Unauthorized` |
| 2 | POST | `/api/v1/auth/refresh` | Bearer | Any valid | Tenant-bound | Token subject | `refresh_token` | None (Token refresh) | `401 Unauthorized` |
| 3 | POST | `/api/v1/auth/logout` | Bearer | Any valid | Tenant-bound | Active session | None | Session invalidation | `401 Unauthorized` |
| 4 | GET | `/api/v1/auth/me` | Bearer | Any valid | Tenant-bound | Current user | Email, role, company | Read-only | `401 Unauthorized` |
| 5 | POST | `/api/v1/auth/register` | None | Public | Creates tenant | New tenant user | Password, email | Inserts Company & User | `400 / 422` |

### 3.2 Companies (`/api/v1/companies`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 6 | GET | `/api/v1/companies/current` | Bearer | Any valid | `current_user.company_id` | Own Company | Settings, plan | Read-only | `401 Unauthorized` |

### 3.3 Clients & B2B Customers (`/api/v1/clients`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 7 | GET | `/api/v1/clients/` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant list | Credit limit, phone | Read-only | `401 / 403` |
| 8 | POST | `/api/v1/clients/` | Bearer | `OPERATOR`+ | `current_user.company_id` | New client | Credit limit, PAN/VAT | Insert Client | `401 / 403` |
| 9 | GET | `/api/v1/clients/{client_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific client | Credit limit, balance | Read-only | `401 / 403 / 404` |
| 10 | PUT | `/api/v1/clients/{client_id}` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific client | Credit limit, status | Update Client | `401 / 403 / 404` |
| 11 | DELETE | `/api/v1/clients/{client_id}` | Bearer | `ADMIN` | `current_user.company_id` | Specific client | Client record | Soft/hard delete | `401 / 403 / 404` |

### 3.4 Products & Catalog (`/api/v1/products`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 12 | GET | `/api/v1/products/` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant catalog | Cost price, margins | Read-only | `401 / 403` |
| 13 | POST | `/api/v1/products/` | Bearer | `OPERATOR`+ | `current_user.company_id` | New product | Base price, cost | Insert Product & BOM | `401 / 403` |
| 14 | GET | `/api/v1/products/{product_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific product | Margins, bill of materials | Read-only | `401 / 403 / 404` |
| 15 | PUT | `/api/v1/products/{product_id}` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific product | Pricing, active status | Update Product | `401 / 403 / 404` |
| 16 | DELETE | `/api/v1/products/{product_id}` | Bearer | `ADMIN` | `current_user.company_id` | Specific product | Entire SKU | Delete Product | `401 / 403 / 404` |

### 3.5 Stock & Inventory (`/api/v1/stock`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 17 | GET | `/api/v1/stock/` | Bearer | `VIEWER`+ | `current_user.company_id` | Stock balances | Inventory valuation | Read-only | `401 / 403` |
| 18 | GET | `/api/v1/stock/movements` | Bearer | `VIEWER`+ | `current_user.company_id` | Movement logs | Unit costs, movement history | Read-only | `401 / 403` |
| 19 | GET | `/api/v1/stock/summary` | Bearer | `VIEWER`+ | `current_user.company_id` | Stock summary | Aggregate balances | Read-only | `401 / 403` |
| 20 | POST | `/api/v1/stock/movements` | Bearer | `OPERATOR`+ | `current_user.company_id` | Product & Warehouse | Stock quantities | Mutate Stock Balance | `401 / 403 / 404` |
| 21 | POST | `/api/v1/stock/adjustments` | Bearer | `MANAGER`+ | `current_user.company_id` | Target warehouse & SKU | Audit delta | Mutate Stock Balance | `401 / 403 / 404` |
| 22 | GET | `/api/v1/stock/valuation` | Bearer | `MANAGER`+ | `current_user.company_id` | Company valuation | Total stock value | Read-only | `401 / 403` |
| 23 | GET | `/api/v1/stock/reorder-alerts`| Bearer | `VIEWER`+ | `current_user.company_id` | Reorder list | Stock shortages | Read-only | `401 / 403` |

### 3.6 Sales Orders (`/api/v1/sales`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 24 | GET | `/api/v1/sales/` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant orders | Financial totals, discount | Read-only | `401 / 403` |
| 25 | POST | `/api/v1/sales/` | Bearer | `OPERATOR`+ | `current_user.company_id` | Client & Items | Prices, credit checks | Insert Sales Order | `401 / 403 / 404` |
| 26 | GET | `/api/v1/sales/{order_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific order | Customer order items | Read-only | `401 / 403 / 404` |
| 27 | PATCH | `/api/v1/sales/{order_id}/status` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific order | Workflow state | Order status transition | `401 / 403 / 404` |

### 3.7 Invoices & Billing (`/api/v1/invoices`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 28 | GET | `/api/v1/invoices/` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant invoices | Tax amounts, totals | Read-only | `401 / 403` |
| 29 | POST | `/api/v1/invoices/` | Bearer | `OPERATOR`+ | `current_user.company_id` | Sales order & Client | Financial balances | Finalize Invoice & AR | `401 / 403 / 404` |
| 30 | GET | `/api/v1/invoices/{invoice_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific invoice | Fiscal numbers, totals | Read-only | `401 / 403 / 404` |
| 31 | PATCH | `/api/v1/invoices/{invoice_id}/status` | Bearer | `MANAGER`+ | `current_user.company_id` | Specific invoice | Status, payment state | Invoice status update | `401 / 403 / 404` |
| 32 | GET | `/api/v1/invoices/{invoice_id}/printable` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific invoice | Full tax invoice PDF/HTML | Read-only | `401 / 403 / 404` |

### 3.8 Accounts Receivable (`/api/v1/receivables`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 33 | GET | `/api/v1/receivables/aging-summary` | Bearer | `VIEWER`+ | `current_user.company_id` | Company AR | Aging buckets (30/60/90) | Read-only | `401 / 403` |
| 34 | GET | `/api/v1/receivables/clients/{client_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific client | Unpaid invoices, credit | Read-only | `401 / 403 / 404` |
| 35 | GET | `/api/v1/receivables/payments` | Bearer | `VIEWER`+ | `current_user.company_id` | Payment records | Bank refs, amounts | Read-only | `401 / 403` |
| 36 | POST | `/api/v1/receivables/payments` | Bearer | `OPERATOR`+ | `current_user.company_id` | Client & Invoices | Amount received | Mutates AR & Balances | `401 / 403 / 404` |

### 3.9 Production & Manufacturing (`/api/v1/production`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 37 | GET | `/api/v1/production/` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant production | Batch quantities | Read-only | `401 / 403` |
| 38 | POST | `/api/v1/production/` | Bearer | `OPERATOR`+ | `current_user.company_id` | Target product SKU | BOM deductions | Insert Production Order | `401 / 403 / 404` |
| 39 | GET | `/api/v1/production/{order_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific order | Batch recipe & notes | Read-only | `401 / 403 / 404` |
| 40 | PATCH | `/api/v1/production/{order_id}/status` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific order | Status lifecycle | Update stage | `401 / 403 / 404` |
| 41 | POST | `/api/v1/production/{order_id}/complete` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific order | Finished goods output | Mutates Raw & Finished Stock | `401 / 403 / 404` |
| 42 | POST | `/api/v1/production/drafts/sync` | Bearer | `OPERATOR`+ | `current_user.company_id` | Offline batch array | Offline draft actions | Bulk Production Sync | `401 / 403 / 404` |
| 43 | GET | `/api/v1/production/drafts/templates` | Bearer | `VIEWER`+ | `current_user.company_id` | Offline templates | BOM templates | Read-only | `401 / 403` |

### 3.10 Audit Logs (`/api/v1/audit`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 44 | GET | `/api/v1/audit/logs` | Bearer | `ADMIN` / `MANAGER` | `current_user.company_id` | Tenant audit logs | IP, user IDs, old/new diff | Read-only | `401 / 403` |
| 45 | GET | `/api/v1/audit/stats` | Bearer | `ADMIN` / `MANAGER` | `current_user.company_id` | Tenant aggregates | Total activities | Read-only | `401 / 403` |
| 46 | GET | `/api/v1/audit/history/{entity_type}/{entity_id}` | Bearer | `ADMIN` / `MANAGER` | `current_user.company_id` | Specific entity | Mutation lifecycle | Read-only | `401 / 403 / 404` |

### 3.11 Database Backup & DR (`/api/v1/backup`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 47 | GET | `/api/v1/backup/status` | Bearer | `ADMIN` | System/Tenant | Backup catalog | Snapshot sizes, timestamps | Read-only | `401 / 403` |
| 48 | POST | `/api/v1/backup/manual` | Bearer | `ADMIN` | System/Tenant | System DB dump | Backup filenames | Triggers SQL dump | `401 / 403` |
| 49 | POST | `/api/v1/backup/restore` | Bearer | `ADMIN` | System/Tenant | System DB restore | Schema & tables | Restores Database | `401 / 403` |

### 3.12 Operations & Telemetry (`/api/v1/ops`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 50 | GET | `/api/v1/ops/health` | None | Public | Global | Health probe | DB connectivity | Read-only | N/A |
| 51 | GET | `/api/v1/ops/metrics` | Bearer | `ADMIN` | System | Process metrics | Memory, CPU, DB pool | Read-only | `401 / 403` |
| 52 | GET | `/api/v1/ops/errors` | Bearer | `ADMIN` | System | Error tracker | Exceptions, route errors | Read-only | `401 / 403` |
| 53 | GET | `/api/v1/ops/slow-queries` | Bearer | `ADMIN` | System | DB telemetry | Query plans, execution ms | Read-only | `401 / 403` |

### 3.13 Product Media Gallery (`/api/v1/gallery`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 54 | GET | `/api/v1/gallery/product/{product_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific product | Image URLs, metadata | Read-only | `401 / 403 / 404` |
| 55 | POST | `/api/v1/gallery/product/{product_id}/upload` | Bearer | `OPERATOR`+ | `current_user.company_id` | Specific product | File binary | Saves file to disk & DB | `401 / 403 / 404` |
| 56 | GET | `/api/v1/gallery/image/{image_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific image | Image file stream | Read-only | `401 / 403 / 404` |
| 57 | DELETE | `/api/v1/gallery/image/{image_id}` | Bearer | `ADMIN` | `current_user.company_id` | Specific image | File path | Unlinks file & DB record | `401 / 403 / 404` |

### 3.14 HR & Payroll (`/api/v1/hr`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 58 | GET | `/api/v1/hr/workers` | Bearer | `VIEWER`+ | `current_user.company_id` | Tenant workers | Base salary, phone, bank | Read-only | `401 / 403` |
| 59 | POST | `/api/v1/hr/workers` | Bearer | `MANAGER`+ | `current_user.company_id` | New worker | Compensation rate | Insert Worker | `401 / 403` |
| 60 | GET | `/api/v1/hr/workers/{worker_id}` | Bearer | `VIEWER`+ | `current_user.company_id` | Specific worker | Full salary details | Read-only | `401 / 403 / 404` |
| 61 | PUT | `/api/v1/hr/workers/{worker_id}` | Bearer | `MANAGER`+ | `current_user.company_id` | Specific worker | Wage changes | Update Worker | `401 / 403 / 404` |
| 62 | POST | `/api/v1/hr/attendance` | Bearer | `OPERATOR`+ | `current_user.company_id` | Worker attendance | Hours worked, overtime | Insert Attendance | `401 / 403 / 404` |
| 63 | GET | `/api/v1/hr/attendance` | Bearer | `VIEWER`+ | `current_user.company_id` | Attendance logs | Worker timesheets | Read-only | `401 / 403` |
| 64 | GET | `/api/v1/hr/payroll/summary` | Bearer | `ADMIN` / `MANAGER` | `current_user.company_id` | Monthly payroll | Total disbursed salaries | Read-only | `401 / 403` |
| 65 | POST | `/api/v1/hr/payroll/process` | Bearer | `ADMIN` | `current_user.company_id` | Period payroll | Financial payouts | Finalizes Payroll Ledger | `401 / 403` |

### 3.15 Offline Synchronization (`/api/v1/sync`)

| # | Method | Route | Auth Req | Required Role | Tenant Scope | Object Scope | Sensitive Fields | Mutation Capability | Expected Unauthorized Response |
|---|---|---|---|---|---|---|---|---|---|
| 66 | GET | `/api/v1/sync/pull` | Bearer | `VIEWER`+ | `current_user.company_id` | Delta changes | Master entity snapshot | Read-only | `401 / 403` |
| 67 | POST | `/api/v1/sync/push` | Bearer | `OPERATOR`+ | `current_user.company_id` | Offline events | Action mutations | Replays Offline Mutations | `401 / 403` |
| 68 | GET | `/api/v1/sync/status` | Bearer | `VIEWER`+ | `current_user.company_id` | Sync status | Last sequence numbers | Read-only | `401 / 403` |
| 69 | POST | `/api/v1/sync/reconciliation`| Bearer | `MANAGER`+ | `current_user.company_id` | Conflict queue | Overwrite resolutions | Applies Conflict Decisions| `401 / 403` |

---

## 4. Bypasses Audited & Remediations Applied

1. **Warehouse Hardcoded IDs & Cross-Tenant Substitution (VULN-01):**
   - *Previous Risk:* `POST /api/v1/stock/adjustments` and `POST /api/v1/stock/movements` defaulted to `warehouse_id=1` or accepted a `payload.warehouse_id` without checking if `Warehouse.company_id == current_user.company_id`.
   - *Mitigation:* Explicit query lookup `db.query(Warehouse).filter(Warehouse.id == warehouse_id, Warehouse.company_id == current_user.company_id).first()` raises HTTP 404/403 if foreign or non-existent. Auto-provisions or retrieves caller company's default warehouse if omitted.
2. **Offline Production Sync Warehouse IDOR (VULN-02):**
   - *Previous Risk:* `POST /api/v1/production/drafts/sync` allowed specifying any `warehouse_id` in offline draft payloads.
   - *Mitigation:* Server enforces caller tenant warehouse ownership for every item processed in batch sync.
3. **Gallery Media Path Traversal (VULN-03):**
   - *Previous Risk:* `GET /api/v1/gallery/image/{image_id}` and `DELETE /api/v1/gallery/image/{image_id}` checked tenant ID on DB record, but file system retrieval relied on stored filename without path boundary checking.
   - *Mitigation:* Uses `os.path.commonpath([UPLOAD_DIR, resolved_path]) == UPLOAD_DIR` to prevent filesystem traversal via forged filenames or symlinks.
4. **Receivables Allocation IDOR (VULN-04):**
   - *Previous Risk:* `POST /api/v1/receivables/payments` silently skipped allocations targeting invoices belonging to another company or client.
   - *Mitigation:* Explicitly validates every allocation invoice against `Invoice.company_id == current_user.company_id` and `Invoice.client_id == payment.client_id`, raising HTTP 422 if mismatched or foreign.
