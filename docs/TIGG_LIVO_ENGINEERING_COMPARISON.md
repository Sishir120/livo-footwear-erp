# Tigg–LIVO Engineering Comparison
**Date:** 2026-10-16  
**Purpose:** Identify LIVO strengths, gaps, and prioritized improvements based on observable Tigg behavior and engineering best practices  
**Constraints:** Tigg internals are UNKNOWN. All Tigg entries are either OBSERVED (from public docs/DOM) or represent established best practice labeled separately.

> **Methodology note:** Where Tigg's implementation is UNKNOWN, the "Tigg" column describes the expected best-practice behavior for a production SaaS ERP at Tigg's market maturity. This allows meaningful comparison even without access to Tigg's source code. Claims about Tigg's own engineering are labeled accordingly.

---

## Comparison Matrix

### 1. Authentication

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| Password hashing | Best practice (UNKNOWN) | Argon2 + Bcrypt via pwdlib (VERIFIED) | **None — LIVO exceeds common standard** | None needed | None | 0 | — |
| Session token storage | UNKNOWN (cookie or localStorage) | httpOnly cookie, secure flag, SameSite=Lax (VERIFIED) | None | None | None | 0 | — |
| Brute-force protection | INFERRED: distributed rate limiting | In-memory per-process sliding window (VERIFIED) | **Works only in single-worker deployments** | Migrate to PostgreSQL-backed rate counter or Redis | Security | 1d | P1 |
| Token/session revocation | UNKNOWN | Active check in DB on every request (VERIFIED) — immediate for `active=False` | Role changes take immediate effect (re-query). Password change does not invalidate existing tokens | Add `token_version` column; increment on password change | Medium | 0.5d | P2 |
| Password reset | OBSERVED: forgot password link | **Not implemented** | No `/auth/reset` endpoint | Add email-based reset with time-limited signed URL | Medium | 1.5d | P2 |
| Multi-organization user model | OBSERVED: single user in multiple orgs | Single company per JWT session (VERIFIED) | User cannot switch orgs without re-login | Requires architecture change — not for 7-day sprint | Medium | 5+d | P3 |
| CSRF protection | UNKNOWN | SameSite=Lax cookie (VERIFIED) provides baseline | Lax allows navigation GETs; strict CSRF token not needed for SPA+cookie | Accept Lax for now | Low | 0 | — |

---

### 2. Authorization

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| Role-based access | OBSERVED: Users & Permissions module | 3 roles: viewer, editor, admin (VERIFIED) | All financial operations require only `editor` | Add financial RBAC roles (VAL-08) | High | 2-3d | P0 |
| Object-level IDOR protection | Best practice (UNKNOWN) | TenantRepository enforces company_id on every query (VERIFIED) | Strong — no IDOR on repo-layer | None | None | 0 | — |
| Branch-scoped access | INFERRED: branch/location scoping | No branch-level authorization (INFERRED — not in deps.py) | Branch editor can affect all branches via API | Add branch_id scope to session context or role assignment | High | 2d | P1 |
| Separation of duties | Best practice for financial systems | None — same role can create and approve | Accountant and CFO have identical permissions | Define `prepare` vs `approve` capabilities for journals | High | 2d | P1 |
| Admin role protection | Best practice | `require_admin` on user management, backup, telemetry (VERIFIED) | Adequate | None | None | 0 | — |

---

### 3. Client-Server Communication

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| Idempotency on mutations | Best practice | Per-request UUID key + DB-backed deduplication (VERIFIED) | Strong | None | None | 0 | — |
| Error schema consistency | Best practice | Uniform `{error, message, detail, request_id}` (VERIFIED) | Strong | None | None | 0 | — |
| 401 auto-redirect | Best practice | **Not in `api.ts`** — 401 surfaces raw error | Expired sessions cause silent UI failures | Add 401 interceptor in `api.ts` to redirect to login | Medium | 0.25d | P1 |
| Retry logic for 5xx | Best practice | None in `api.ts` | Transient errors not retried | Add exponential backoff for idempotent GETs | Low | 0.5d | P2 |
| Offline mutation queue | Uncommon best practice | Implemented via IndexedDB outbox (VERIFIED) | LIVO **exceeds** most SaaS ERPs here | None | None | 0 | — |
| Pagination | Best practice | limit/offset on all list endpoints (VERIFIED) | No cursor pagination | Acceptable for current scale | Low | 0 | — |
| Request correlation IDs | Best practice | `X-Request-ID` propagated through all responses (VERIFIED) | Strong | None | None | 0 | — |
| API versioning | Best practice | `/api/v1/` prefix (VERIFIED) | No forward compatibility mechanism | Document breakage policy | Low | 0 | — |

---

### 4. Caching

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| Backend query cache | Best practice (for dashboards) | None (VERIFIED) | Dashboard/report queries hit DB on every request | Profile slow queries first, add caching only if measured | Data consistency risk | 1d | P2 |
| Cache tenant isolation | Best practice | N/A — no cache exists | N/A | Enforce company_id in cache key if cache added | Critical | 0 | — |
| HTTP caching headers | Best practice | Not set (INFERRED) | Fine for authenticated API; static assets may benefit | Add cache headers for static media endpoints | Low | 0.25d | P3 |
| Frontend query caching | Common best practice | None observed | UI re-fetches on every navigation | Accept for now; add react-query post-evaluation | Low | 2d | P3 |

---

### 5. Database Transactions and Concurrency

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| PostgreSQL advisory locks | Best practice | 7 lock categories, transaction-scoped (VERIFIED) | **Exceeds common SaaS implementations** | None | None | 0 | — |
| Race condition protection on stock | Best practice | Hash-based lock key per (company, warehouse, product, size) (VERIFIED) | Strong | None | None | 0 | — |
| Migration coordination on startup | Best practice | Advisory lock across containers (VERIFIED) | Strong | None | None | 0 | — |
| Transaction rollback on error | Best practice | Session lifecycle handles rollback (VERIFIED) | Gap: suppressed exceptions can leave partial state | Add explicit rollback in error handlers | High | 0.5d | P1 |
| Paisa integer precision | Nepal statutory requirement | Integer paisa math throughout (VERIFIED) | Strong — no floating point | None | None | 0 | — |
| WAL mode for SQLite | Best practice for dev | WAL + busy_timeout=30000 + FK enforcement (VERIFIED) | Strong | None | None | 0 | — |

---

### 6. Security Headers and Hardening

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| X-Frame-Options: DENY | Best practice | Set (VERIFIED) | None | None | None | 0 | — |
| X-Content-Type-Options: nosniff | Best practice | Set (VERIFIED) | None | None | None | 0 | — |
| Strict-Transport-Security | Best practice | Set in production (VERIFIED) | None | None | None | 0 | — |
| Content-Security-Policy | Best practice | **Not set** | XSS attack vectors not mitigated at browser level | Add restrictive CSP header for API responses | High | 0.5d | P1 |
| Referrer-Policy | Best practice | Set (VERIFIED) | None | None | None | 0 | — |
| Permissions-Policy | Best practice | Set with geolocation/camera/mic/payment denied (VERIFIED) | None | None | None | 0 | — |

---

### 7. Observability and Resilience

| Capability | Tigg (Evidence) | LIVO Implementation | LIVO Gap | Proposed Fix | Risk | Effort | Priority |
|---|---|---|---|---|---|---|---|
| Structured logging | Best practice | Correlation IDs propagated (VERIFIED); log format UNVERIFIED | Add JSON log format confirmed | Configure JSON logging handler in uvicorn | Low | 0.25d | P2 |
| Health checks | Best practice | `/health`, `/health/live` (VERIFIED) | Missing readiness probe (`/health/ready`) | Add ready check (migration + DB connected) | Low | 0.25d | P2 |
| Audit trail | Best practice | Endpoint + status captured; field values NOT captured (VERIFIED) | Insufficient for financial audit | Add before/after JSON to AuditLog.details | High | 1d | P1 |
| Error taxonomy | Best practice | `error_taxonomy.py` maps HTTP status to error codes (VERIFIED) | Strong | None | None | 0 | — |
| Background job queue | Best practice for async operations | **None implemented** | Long-running operations block HTTP workers | Accept limitation; document in architecture | Medium | 4+d | P3 |
| Circuit breakers | Best practice | None | Not critical at current scale | Defer | Low | 3+d | P3 |

---

## LIVO's Strongest Existing Engineering Decisions

1. **Argon2 password hashing** — industry-leading, exceeds most competitors
2. **PostgreSQL advisory locks with 7 lock categories** — prevents race conditions across horizontally scaled workers in production
3. **Idempotency middleware with DB-backed deduplication** — production-grade exactly-once execution
4. **`TenantRepository` pattern** — compile-time enforcement of company_id scoping
5. **httpOnly cookie with secure flag + SameSite** — correct cookie security posture
6. **Secret key enforcement at startup** — no running app on empty secret
7. **Migration advisory lock** — safe multi-container deployment
8. **Integer-paisa financial arithmetic** — no floating-point rounding errors
9. **Offline mutation queue with IndexedDB outbox** — uncommon capability even in established ERPs
10. **Structured error taxonomy** — consistent, machine-parseable error codes

---

## Verdict: LIVO vs. Expected Best Practice for Client Evaluation

| Domain | Assessment |
|---|---|
| Authentication | **B+** — Strong password hashing and cookies; lacks password reset and per-worker rate limiting |
| Authorization | **C** — Tenant isolation is excellent; role granularity is insufficient for financial workflows |
| Client-Server | **A-** — Best-in-class idempotency and offline support; needs 401 auto-redirect |
| Caching | **B** — Correctly absent; no premature optimization risk |
| Transactions | **A** — Advisory locking is genuinely sophisticated |
| Security Headers | **B** — Missing CSP; all other headers correct |
| Observability | **B-** — Correlation IDs present; audit log field-level data absent |
| **Overall** | **B+ (production-adequate for core workflows)** |

---

## Detailed Functional Module Comparison (Tigg vs LIVO Codebase)

### 1. Chart of Accounts (COA) & General Ledger Structure
- **Tigg Standard:** 5-tier hierarchical account tree (Assets, Liabilities, Equity, Income, Expenses) with parent-child nesting and system-locked control accounts.
- **LIVO Local Codebase:**
  - Designed in `docs/accounting/PHASE_6A_GENERAL_LEDGER_SYSTEM_SPEC.md` with standard 5-digit account code architecture (`10000` to `59999`).
  - Not yet migrated into PostgreSQL tables (deferred to Phase 6B per implementation gate).
  - **LIVO Advantage:** Tailored for footwear manufacturing inventory accounts (Raw Materials, WIP Footwear, Finished Goods, Consignment Stock).
  - **Action Required:** Retain Phase 6A design gate; implement once Phase 6A.2 blockers (VAL-01, VAL-02) are resolved.

### 2. Journal Entries & Posting Validation
- **Tigg Standard:** Vouchers follow `Draft` -> `Approved` -> `Voided`. Validates $\sum DR = \sum CR$. Immutable once approved.
- **LIVO Local Codebase:**
  - LIVO Phase 6A spec specifies atomic balance validation in integer paisa (`abs(sum_dr - sum_cr) == 0`).
  - Idempotency middleware (`backend/app/middleware/idempotency.py`) provides backend deduplication.
  - **Gap Identified (VAL-01):** Missing explicit `GLEventAction` enum to prevent idempotency key collisions across different event types on the same entity.

### 3. Day Book & Account Ledgers
- **Tigg Standard:** Day book displays all chronological financial vouchers across all accounts.
- **LIVO Local Codebase:**
  - `backend/app/api/v1/reports.py` provides `/reports/daily` aggregating daily production batches, sales orders, and stock movements.
  - Operational inventory day book is provided via `StockMovement` ledger (`backend/app/models/stock.py`).
  - GL day book will be exposed in Phase 6B once GL entries are active.

### 4. Sales Orders, Invoices, Receipts, and Returns
- **Tigg Standard:** Quotation -> SO -> Invoice -> Credit Note -> Payment Allocation.
- **LIVO Local Codebase:**
  - Verified in `backend/app/models/sales.py`, `invoice.py`, `credit_note.py`, and `backend/app/api/v1/invoices.py`.
  - **LIVO Superiority in Manufacturing:**
    - Footwear size-curve breakdowns directly on `SalesItem` (e.g. sizes 39–44).
    - Deferred dispatch tracking (`dispatched_at`, `carrier_name`, `vehicle_number`, `dispatched_by_id`).
    - High-concurrency sequence allocation: `allocate_next_invoice_sequence()` uses row-level `SELECT ... FOR UPDATE` on `InvoiceSequence` (`invoices.py:71-104`), eliminating race conditions under heavy load.
    - Full server-side integer paisa VAT engine (`compute_invoice_amounts`) supporting both `VAT_EXCLUSIVE` and `VAT_INCLUSIVE` pricing.

### 5. Purchase Transactions & Landed Cost Allocation
- **Tigg Standard:** Purchase Bill with "Additional Cost Feature" allocating customs/freight to line item valuation.
- **LIVO Local Codebase:**
  - Verified in `backend/app/models/purchase.py` and `backend/app/api/v1/purchase.py`.
  - **LIVO Manufacturing Specialization:**
    - `Purchase` model explicitly includes fine-grained landed cost columns: `carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`, `total_landed_cost_paisa`, and `effective_unit_rate_paisa` (`purchase.py:57-64`).
    - Raw material inventory movements (`RawMaterialMovement`) capture exact unit cost snapshots and BOM issue consumption (`purchase.py:77-100`).
    - Goods Receipt Note (GRN) tracking with `grn_number` and `received_by_id`.

### 6. Stock Ledger, Stock Adjustments, and Warehouse Transfers
- **Tigg Standard:** Multi-warehouse inventory, adjustments with expense heads, and transfer vouchers.
- **LIVO Local Codebase:**
  - Verified in `backend/app/models/stock.py`, `stock_transfer.py`, and `backend/app/core/locks.py`.
  - **LIVO Architectural Excellence:**
    - **Strictly Append-Only:** `Product` model has NO `stock_qty` caching column (`stock.py:22`); stock balances are mathematically derived from `StockMovement` entries to prevent silent drift.
    - **Advisory Locking:** `acquire_stock_lock()` in `locks.py` uses 64-bit PostgreSQL transaction advisory locks keyed by `(company_id, warehouse_id, product_id, size)`, making concurrent over-allocation impossible across distributed workers.

### 7. Roles & Permissions Architecture
- **Tigg Standard:** Dedicated Users & Permissions module with multi-tenant invitations and functional role definitions.
- **LIVO Local Codebase:**
  - `backend/app/models/user.py` and `backend/app/api/deps.py`.
  - **Critical Gap (H-02 / VAL-08):** LIVO currently implements only 3 coarse roles: `viewer`, `editor`, `admin`. All financial and inventory mutations require only `editor`.
  - **Action Required:** Expand RBAC to include `accountant`, `inventory_manager`, and `production_manager`, and separate `prepare` vs `approve` permissions for journal postings (`H-02`, `H-07`).

### 8. Date Handling: Bikram Sambat (BS) & Gregorian (AD)
- **Tigg Standard:** Native BS calendar datepickers and reports.
- **LIVO Local Codebase:**
  - All LIVO operational models (`Invoice`, `SalesOrder`, `Purchase`, `StockMovement`, `ProductionBatch`) already store dual dates: `date_ad` (ISO YYYY-MM-DD) and `date_bs` (String YYYY-MM-DD).
  - **UX Gap:** Frontend currently relies on manual BS string entry or ISO fallback; needs a shared Nepali datepicker component to prevent formatting discrepancies.

### 9. Reports, Pagination, Filters, and Statutory IRD Tax Registers
- **Tigg Standard:** Pre-formatted Nepal IRD Annex 5 (Sales Register), Annex 8 (Purchase Register), and VAT return summaries.
- **LIVO Local Codebase:**
  - `backend/app/api/v1/invoices.py` and `reports.py` provide bounded pagination (`limit`, `offset`), printable HTML invoices with QR/PAN compliance, and sales summaries.
  - **Gap:** Standalone Annex 5 and Annex 8 statutory register export endpoints need to be added to `reports.py`.

