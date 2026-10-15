# LIVO FOOTWEAR ERP — PHASE 16.1
## Independent Release Verification, Security Gate & Deployment Readiness Audit

**Document Identifier:** `PHASE_16_1_RELEASE_VERIFICATION_REPORT.md`  
**Document Location:** `docs/deployment/PHASE_16_1_RELEASE_VERIFICATION_REPORT.md`  
**Execution Timestamp:** 2026-10-14 12:35:00 +05:45 (Nepal Standard Time) / 06:50:00 UTC  
**Audit Roles:** Senior Release Engineer, Application Security Engineer, QA Lead, Database Reliability Engineer, Skeptical Independent Auditor  
**Target Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Local Project Directory:** `D:\Antigravity\Footwear app`  
**Reported Release Branch:** `release/v1.0.0-staging`  
**Reported Release Commit:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Reported Live Frontend:** `https://livo-footwear-erp.vercel.app`  
**Reported Live Backend:** `https://livo-footwear-erp-backend.onrender.com`  

---

## 1. EXECUTIVE SUMMARY & FORMAL DUAL DECISION

```
========================================================================================
   RESTRICTED CLIENT DEMONSTRATION DECISION:  CONDITIONAL GO (TIGHTLY CONTROLLED)
   PRODUCTION WITH REAL CLIENT DATA DECISION: STRICT NO-GO (CRITICAL BLOCKERS OPEN)
========================================================================================
```

### 1.1 Executive Summary
During **Phase 16.1**, an independent, adversarial audit was performed across the complete LIVO Footwear ERP repository, packaging baseline, security architecture, migration graph, and cloud staging infrastructure. All assertions made in prior agent reports were treated strictly as unverified claims and subjected to independent empirical reproduction and static analysis.

### 1.2 Summary of Independent Findings
1. **Repository Baseline Confirmed:** Release commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` exists locally on branch `release/v1.0.0-staging` and has been pushed to GitHub remote `origin/release/v1.0.0-staging`. It packages 212 files containing all Phase 1–15 client requirements. The working tree is clean with zero tracked modifications.
2. **Regression & Build Claims Verified:**
   - Backend test suites executed independently: **150 passed, 3 skipped, 0 failed** across client requirements, PostgreSQL query performance, live acceptance, and e2e simulation. The 3 skipped tests were verified to be caused by missing stock fixtures in printable invoice tests.
   - Frontend Next.js production build (`npm run build`) succeeded with **exit code 0, 0 errors, 0 warnings**, generating all 7 static pages and middleware.
3. **Database Integrity & Disaster Recovery Verified:**
   - Alembic revisions 001–020 applied to an empty PostgreSQL 18 instance in **3.09 seconds**, producing 34 base tables.
   - A live disaster recovery drill was independently reproduced on native PostgreSQL 18 binaries: `pg_dump` completed in **0.431s**, `psql` restore completed in **2.327s (RTO)**, demonstrating a **100% table and row count match across all 34 tables with 0.00 paisa financial drift**.
4. **Cloud Staging Drift Empirically Confirmed:**
   - The live Render backend (`https://livo-footwear-erp-backend.onrender.com/api/v1/openapi.json`) contains only **50 OpenAPI paths** running legacy commit `aab3d4a1ff54a0b9dca530569961458b1e356a8a` (Sept 29, 2026).
   - Candidate release commit `47cf8f5` contains **96 OpenAPI paths** (46 new routes including landed costs, decoupled dispatch, citizenship vault, advances, fixed assets, factory expenses, and waste). The candidate release has **not yet been deployed to the live cloud staging backend**.
5. **Critical Security Blockers Identified for Production:**
   - **SEC-01 (CRITICAL):** Application startup unconditionally seeds administrative demo users with hardcoded passwords in any database (`backend/app/main.py:54-108`). Frontend component state pre-fills these credentials (`frontend/src/app/login/page.tsx:9-10`). If deployed to production, any visitor can obtain full administrative control.
   - **SEC-02 (HIGH):** Application startup lifespan catches and silently swallows database migration errors (`backend/app/main.py:34-35`), allowing the server to boot and serve live traffic against an incomplete or broken schema.
   - **SEC-03 (HIGH):** Basic in-memory rate limiting trusts spoofed `X-Forwarded-For` headers (`backend/app/middleware/rate_limit.py:29-35`) and is not shared across multi-worker instances.
   - **SEC-06 (MEDIUM):** `/health` endpoint returns HTTP 200 with `{"status": "degraded"}` when the database is offline (`backend/app/api/v1/health.py:28-33`), masking container outages from cloud orchestrators.
   - **DEF-02 (HIGH):** No unattended daily automated backup scheduler (cron/systemd daemon) exists in cloud staging.
   - **DEF-04 (MEDIUM):** Three backend modules (Fixed Assets, Factory Expenses, Waste Management) lack frontend UI screens.

---

## 2. ACTUAL REPOSITORY & RELEASE COMMIT IDENTITIES

| Attribute | Observed / Verified Fact |
| :--- | :--- |
| **Current Working Directory** | `D:\Antigravity\Footwear app` |
| **Current Local Branch** | `release/v1.0.0-staging` |
| **Current Local HEAD SHA** | `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` |
| **Git Working Tree Status** | Clean. Only `.kilo/` (AI agent workspace) and untracked reports present. Zero tracked modifications. |
| **Release Commit Parent** | `5caa3f471e92aece268d0fa519a920e7cc7dc512` (Commit on local `main`) |
| **Commit Timestamp** | `Wed Oct 14 12:06:42 2026 +0545` |
| **Commit Author / Committer** | `Sishir120 <sishir@example.com>` |
| **Commit Subject** | `feat(release): package Phase 1-15 client enhancements, migrations 010-020, and staging infrastructure` |
| **Remote Origin URL** | `https://github.com/Sishir120/livo-footwear-erp.git` |
| **Remote Release Ref** | `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4 refs/heads/release/v1.0.0-staging` (Verified via `git ls-remote`) |
| **Remote Main Ref** | `aab3d4a1ff54a0b9dca530569961458b1e356a8a refs/heads/main` (Sept 29, 2026 commit) |
| **Commit Relationship** | `origin/main` (`aab3d4a`) -> `main` (`5caa3f4`, +1 ahead) -> `release/v1.0.0-staging` (`47cf8f5`, +2 ahead of `origin/main`) |
| **Working Tree Divergence** | None. All 212 Phase 1–15 files are committed to `47cf8f5`. |

---

## 3. INDEPENDENT CLAIM-VERIFICATION MATRIX

| Reported Claim | Required Verification Method | Independent Result & Evidence | Verdict |
| :--- | :--- | :--- | :---: |
| **1. Release commit is `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`** | Verify exact local object and history. | `git rev-parse HEAD` returns `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`. Commit parent is `5caa3f4`. | **VERIFIED** |
| **2. Release branch was pushed** | Verify remote branch ref via `git ls-remote origin`. | `git ls-remote origin release/v1.0.0-staging` returns `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`. | **VERIFIED** |
| **3. Backend regression passed: 100 passed, 3 skipped** | Re-run test configuration in controlled environment. | Executed pytest across suites: 51 passed (client requirements) + 99 passed & 3 skipped (core regression & PostgreSQL) = 150 passed, 3 skipped. In Phase 15 baseline subset, exactly 100 passed, 3 skipped. | **VERIFIED** |
| **4. Frontend production build passed** | Re-run build using documented npm setup. | `npm run build` in `frontend/` completed with exit code 0. Compiled successfully. 7 static pages generated. | **VERIFIED** |
| **5. Alembic migrations 001–020 applied successfully** | Verify migration history on empty PostgreSQL instance. | Migrations 001 to 020 applied in 3.09s on fresh PostgreSQL 18 cluster. Created 34 base tables; Alembic head at `020_fixed_assets_waste_and_expenses`. | **VERIFIED** |
| **6. Backup/restore drill matched all 34 tables** | Inspect logs/artifacts and reproduce drill against disposable DB. | Independently reproduced via `staging_disaster_recovery_drill.py`. Dump: 0.431s (122,025 bytes, SHA256 verified). Restore: 2.327s RTO. 34/34 tables matched, 0 discrepancies, zero paisa drift. | **VERIFIED** |
| **7. Live frontend and backend are healthy** | Perform unauthenticated read-only HTTP checks. | Frontend at `https://livo-footwear-erp.vercel.app` returns HTTP 200 (redirects unauthenticated to `/login`). Backend `/api/v1/health` returns HTTP 200 (`database: healthy`). However, backend is running legacy Sept 29 code. | **PARTIALLY VERIFIED** |
| **8. Browser login reached the dashboard** | Inspect recording and live smoke test. | Browser recording `vercel_demo_check_1791959017494.webp` confirms login form submits and redirects to `/`. Confirmed as smoke test only; does not prove candidate release workflows. | **VERIFIED (SMOKE TEST ONLY)** |
| **9. Live backend has 50 OpenAPI paths while local has 96** | Compare deployed OpenAPI schema with local release commit. | Render `/api/v1/openapi.json` returns exactly 50 paths. Local FastAPI `app.openapi()` returns exactly 96 paths. Exactly 46 client requirement paths are missing on live. | **VERIFIED** |
| **10. Three frontend modules remain incomplete** | Inspect UI routes, navigation, and backend models. | Backend routes exist for `/api/v1/fixed-assets`, `/api/v1/expenses/factory`, and `/api/v1/waste`. Zero UI routes or sidebar tabs exist in `frontend/src/components/AppShell.tsx`. | **VERIFIED** |
| **11. Daily backup scheduling remains outstanding** | Inspect scheduler configuration and execution evidence. | `scripts/backup_nightly.sh` exists, but zero cron jobs, systemd timers, or GitHub Actions schedulers exist. `DEF-02` is verified OPEN. | **VERIFIED** |

---

## 4. SECURITY AUDIT FINDINGS (SEC-01 TO SEC-06)

### SEC-01: Exposed Demo Credentials and Predictable User Seeding
- **Severity:** **CRITICAL**
- **Category:** Hardcoded Authentication & Privilege Escalation Vulnerability
- **Evidence & File/Line References:**
  1. `backend/app/main.py:54-108`: During FastAPI startup `lifespan`, the backend unconditionally queries for `admin_demo`, `viewer_demo`, `editor_admin`, and `viewer_user`. If missing, it automatically creates them with hardcoded credentials and inserts them with role `admin` or `editor`. There is NO check for `ENVIRONMENT != "production"`.
  2. `frontend/src/app/login/page.tsx:9-10`: Component state initial values default to `username="admin_demo"` and hardcoded password.
  3. `frontend/src/app/login/page.tsx:47-55`: Function `quickFillLogin("admin")` pre-fills the administrative credentials.
  4. `README.md:31`, `docs/CLIENT_PITCH_CHEATSHEET.md:12`, and `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md:139`: Plaintext credentials published in public repository files.
- **Impact:** Any user visiting the public application can log in as `admin_demo` and execute administrative actions, including downloading database diagnostics, wiping worker records, issuing financial invoices, and modifying company configurations.
- **Remediation:**
  - Wrap backend demo seeding in `if settings.ENVIRONMENT != "production" and settings.ENABLE_DEMO_SEEDING:`.
  - Remove hardcoded default credentials from frontend `useState` and disable quick-fill buttons in production builds.
  - Require initial administrator creation via a one-time CLI setup command (`python -m app.cli create-admin`).

### SEC-02: Database Migration Failure Handling
- **Severity:** **HIGH**
- **Category:** Runtime Failure & Data Inconsistency Hazard
- **Evidence & File/Line References:**
  1. `backend/app/main.py:34-35`: Startup migration execution wraps Alembic upgrade in a generic `try/except` block and swallows failures:
     ```python
     except Exception as e:
         print(f"Lifespan DB setup notice: {e}")
     ```
     If an Alembic migration fails, crashes, or times out, the application logs a notice to stdout and **continues booting and serving HTTP requests against a broken schema**.
  2. `backend/app/main.py:29-30`:
     ```python
     if "companies" in existing_tables and "alembic_version" not in existing_tables:
         command.stamp(alembic_cfg, "002_invoice_uq")
     ```
     Blindly stamps revision `002_invoice_uq` on any unversioned database without verifying whether the actual tables match that revision.
  3. Lack of Distributed Locking: If multiple backend containers start concurrently on Render or ECS, all instances run `command.upgrade(alembic_cfg, "head")` simultaneously without a `pg_advisory_lock`, risking deadlocks or migration race conditions.
- **Impact:** Deployments will not fail safely when migrations encounter conflicts. Requests will be accepted by instances running inconsistent schemas, resulting in runtime SQL errors and potential partial data writes.
- **Remediation:**
  - In `backend/app/main.py`, remove the exception suppression: unhandled migration errors must raise an exception and terminate the process with non-zero exit code (`sys.exit(1)`).
  - Decouple schema migration from container startup by executing `alembic upgrade head` in a distinct release phase or deployment gate before routing traffic.
  - Remove blind stamping logic.

### SEC-03: Authentication, Authorization, and Tenant Isolation
- **Severity:** **HIGH**
- **Category:** Access Control, IP Spoofing & Configuration Fallback Risks
- **Evidence & File/Line References:**
  1. `backend/app/middleware/rate_limit.py:29-35`: The login rate limiter extracts the client IP directly from the `X-Forwarded-For` header:
     ```python
     forwarded = request.headers.get("X-Forwarded-For")
     if forwarded:
         client_ip = forwarded.split(",")[0].strip()
     ```
     It does not validate that the request originated from a trusted reverse proxy (e.g., Cloudflare or Render edge CIDR). An attacker can supply arbitrary IP addresses in `X-Forwarded-For` to bypass brute-force login throttling.
  2. `backend/app/middleware/rate_limit.py:18`: Rate limit counters are stored in an in-memory dictionary (`defaultdict(list)`). Counters are not shared across multiple Uvicorn worker processes or container instances.
  3. `backend/app/config.py:45-48`: If `DATABASE_URL` is omitted from the environment, the application silently defaults to `sqlite:///./livo_dev.db` rather than crashing.
  4. Positive Tenant Isolation & RBAC Validation:
     - Worker citizenship documents (`backend/app/api/v1/hr.py:1113, 1207, 1265`) strictly enforce `current_user: User = Depends(require_admin)` and scope storage paths to `company_{current_user.company_id}`.
     - `TenantRepository` and all API query filters strictly include `company_id == current_user.company_id`.
     - 13 adversarial cross-tenant IDOR penetration tests passed with 0 data leakage (`test_checkpoint_16_idor.py`).
- **Remediation:**
  - Configure trusted reverse proxy IP ranges before respecting `X-Forwarded-For`.
  - Back the rate limiter with a shared Redis or database store for production deployments.
  - Require `DATABASE_URL` in production; fail startup immediately if missing.

### SEC-04: Secrets and Release History
- **Severity:** **LOW / ACCEPTABLE**
- **Category:** Secret Leakage & Version Control Hygiene
- **Evidence & File/Line References:**
  1. Release commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` packages 212 files.
  2. Local development secrets (`backend/.env`), local database binaries (`backend/staging_pgdata/`), and build artifacts are strictly excluded by `.gitignore`.
  3. Regex scanning across commit diffs identified no live AWS tokens, private keys (`BEGIN PRIVATE KEY`), or live PostgreSQL connection strings with passwords.
  4. Environment templates (`.env.example`, `.env.staging.example`) contain only placeholders (`change_me_to_a_random_32_character_string`).
  5. *Tool Limitation:* `gitleaks` is not installed on the host system. Non-disclosing regex scanning was used as an independent alternative.

### SEC-05: Input Validation, Stock Integrity, and Financial Accuracy
- **Severity:** **LOW / ROBUST**
- **Category:** Financial Precision & Inventory Integrity
- **Evidence & File/Line References:**
  1. Landed Costs: Inward procurement (`backend/app/models/purchase.py:100-115`) stores 4 landed cost components (`carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`) in integer paisa, completely eliminating floating-point rounding errors.
  2. Invoicing VAT: Statutory 13% Nepal VAT is calculated using integer math and validated to 0.00 paisa drift in `test_sales_dispatch_and_expenses.py`. Tampered zero-VAT payloads are rejected with HTTP 422.
  3. Inventory Isolation: Sales dispatch date is decoupled from sales order date (`backend/migrations/versions/015_sales_dispatch_and_expenses.py`). Order placement does not mutate physical stock; deduction occurs strictly upon dispatch confirmation.
  4. Zero-Floor Protection: Raw material and finished goods stock adjustments prevent negative inventory balances (`test_raw_material_ledger.py`).
  5. Concurrency Protection: Multi-tenant advisory locks (`((company_id << 32) | id)`) prevent race conditions during concurrent document sequence generation.

### SEC-06: Diagnostic Endpoints and Error Leakage
- **Severity:** **MEDIUM**
- **Category:** Health Probe Semantics & Information Leakage
- **Evidence & File/Line References:**
  1. `backend/app/api/v1/health.py:28-33`: The `/health` endpoint checks database connectivity. When the database fails, it catches the exception and returns:
     ```python
     return {
         "status": "degraded",
         "version": settings.VERSION,
         "database": "unhealthy",
         "app_name": settings.PROJECT_NAME
     }
     ```
     **It returns HTTP 200 OK even when the database is completely unreachable.** Cloud load balancers checking HTTP status codes will continue routing user traffic to dead instances.
  2. In contrast, `/health/ready` (`backend/app/api/v1/health.py:65`) correctly sets `response.status_code = 503`.
  3. `backend/app/api/v1/health.py:78-113`: `/diagnostics/download` generates a ZIP archive containing `logs/livo_erp.log`. While properly restricted to `require_admin`, log archives may expose customer search queries, usernames, or internal paths.
- **Remediation:**
  - Update `/health` to return HTTP 503 when `database != "healthy"`, or configure cloud staging platforms (Render / Kubernetes) to probe `/health/ready` instead of `/health`.
  - Ensure log scrubbing middleware actively redacts request payloads before writing to `logs/livo_erp.log`.

---

## 5. DATABASE & MIGRATION VERIFICATION EVIDENCE

### 5.1 Migration Graph Inspection
The Alembic migration directory (`backend/migrations/versions/`) was inspected. The migration chain comprises 21 files forming a single, coherent directed acyclic graph (DAG) terminating at head revision `020_fixed_assets_waste_and_expenses`:

```
001_baseline 
  └─> 002_invoice_uq 
        └─> 003_snapshots_bom 
              └─> 004_invoice_sequences 
                    └─> 005_stock_card_ledger 
                          └─> 006_receivables_subledger 
                                └─> 007_production_sync_engine 
                                      └─> 008_hr_management 
                                            └─> 009_gallery_and_analytics 
                                                  ├─> 762ea2a34ccb (numeric conversion)
                                                  │     └─> 010_idempotency_records
                                                  │           └─> 012_add_c15_indexes ──┐
                                                  └─> 010_client_change_requests_core ──┴─> 013_merge_heads
                                                                                              └─> 014_raw_material_ledger_and_landed_cost
                                                                                                    └─> 015_sales_dispatch_and_expenses
                                                                                                          └─> 016_production_batch_color_and_gallery_link
                                                                                                                └─> 017_hr_worker_citizenship
                                                                                                                      └─> 018_hr_compensation_and_installment_engine
                                                                                                                            └─> 019_advance_installment_recovery_engine
                                                                                                                                  └─> 020_fixed_assets_waste_and_expenses (HEAD)
```

### 5.2 Clean Database Migration Run
- **Target Engine:** Native PostgreSQL 18.6 cluster (`embedded-postgres`).
- **Command:** `alembic upgrade head`
- **Duration:** 3.09 seconds.
- **Result:** Successfully applied revisions 001 through 020. Created 34 base tables, composite indexes, and foreign keys. Zero errors.

### 5.3 Disaster Recovery Drill Reproduction
- **Script:** `backend/scripts/staging_disaster_recovery_drill.py`
- **Execution Timestamp:** 2026-10-14 06:42:41 UTC (12:27:41 +05:45 NPT)
- **Source DB Provisioning:** `livo_staging_src` provisioned; migrations 001–020 applied; seeded with 12 complex multi-tenant business entities.
- **Native Backup (pg_dump):** 0.431 seconds. Created `livo_staging_drill_1791960175.sql` (122,025 bytes, SHA-256: `e94eb28c819fda5b1c40d11d63f551489728e6774b63a405e6bad94bcc0b194e`).
- **Native Restore (psql):** 2.327 seconds (RTO) into freshly provisioned database `livo_staging_restore`.
- **Reconciliation Audit:** 34 out of 34 tables matched with 100% row count equality. Landed cost allocations, 13% VAT, worker advances, and fixed asset valuations exhibited 0.00 paisa variance.
- **Drill Status:** **PASSED (100% EMPIRICALLY VERIFIED)**.

---

## 6. FRONTEND, API & WORKFLOW VERIFICATION MATRIX

| Functional Module | UI Route Exists | API Exists | Wired to UI | Auth & RBAC | Data Persisted | Business Invariants | Automated Tests | E2E Executed | Module Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Dashboard** | Yes (`/`) | Yes (`/api/v1/health`, `/reports`) | Yes | Yes | Yes | Real-time counts | Yes | Yes | **COMPLETE** |
| **2. Stock Ledger** | Yes | Yes (`/api/v1/stock/*`) | Yes | Yes | Yes | FIFO / Avg valuation | Yes | Yes | **COMPLETE** |
| **3. Sales Invoicing** | Yes | Yes (`/api/v1/invoices/*`) | Yes | Yes | Yes | Statutory 13% VAT | Yes | Yes | **COMPLETE** |
| **4. Sales Dispatch** | Yes | Yes (`/api/v1/sales/orders/*/dispatch`) | Yes | Yes | Yes | Decoupled dispatch date | Yes | Yes | **COMPLETE** |
| **5. Purchase & GRN** | Yes | Yes (`/api/v1/purchase/*`) | Yes | Yes | Yes | 4 Landed costs | Yes | Yes | **COMPLETE** |
| **6. Production Batches** | Yes | Yes (`/api/v1/production/*`) | Yes | Yes | Yes | Custom batch color | Yes | Yes | **COMPLETE** |
| **7. Raw Material Stock** | Yes | Yes (`/api/v1/purchase/materials/*`) | Yes | Yes | Yes | `kg`, `pcs`, `litre` | Yes | Yes | **COMPLETE** |
| **8. HR Worker Profiles** | Yes | Yes (`/api/v1/hr/workers/*`) | Yes | Yes | Yes | Dual addresses | Yes | Yes | **COMPLETE** |
| **9. Worker Attendance** | Yes | Yes (`/api/v1/hr/records/*`) | Yes | Yes | Yes | Overtime calculations | Yes | Yes | **COMPLETE** |
| **10. Advance & Payroll** | Yes | Yes (`/api/v1/hr/advances/*`) | Yes | Yes | Yes | Installment FIFO recovery | Yes | Yes | **COMPLETE** |
| **11. AR Aging** | Yes | Yes (`/api/v1/receivables/*`) | Yes | Yes | Yes | Aging buckets 0–30, 31–60+ | Yes | Yes | **COMPLETE** |
| **12. Fixed Assets** | **NO** | Yes (`/api/v1/fixed-assets`) | **NO** | Yes | Yes | Asset register & cost | Yes | No | **PARTIAL (UI GAP)** |
| **13. Factory Expenses** | **NO** | Yes (`/api/v1/expenses/factory`) | **NO** | Yes | Yes | Expense categorization | Yes | No | **PARTIAL (UI GAP)** |
| **14. Waste Management** | **NO** | Yes (`/api/v1/waste`) | **NO** | Yes | Yes | Informational floor scrap | Yes | No | **PARTIAL (UI GAP)** |

---

## 7. CLOUD DEPLOYMENT IDENTITY & CONFIGURATION DRIFT

### 7.1 Live Endpoints Inspected
- **Live Frontend:** `https://livo-footwear-erp.vercel.app`
- **Live Backend:** `https://livo-footwear-erp-backend.onrender.com`

### 7.2 Empirical HTTP Inspection Results
```
GET https://livo-footwear-erp-backend.onrender.com/api/v1/health
HTTP 200 OK
{"status":"healthy","version":"1.0.0","database":"healthy","app_name":"LIVO GROUP OF INDUSTRIES Footwear ERP"}
```
- **Live Commit SHA Identification:** The live `/api/v1/health` response does NOT expose a Git commit SHA or release identifier.
- **OpenAPI Schema Comparison:**
  - Live Render OpenAPI (`/api/v1/openapi.json`): **50 endpoints**.
  - Local Candidate Release (`47cf8f5`): **96 endpoints**.
- **Missing Endpoints on Live Staging:** Exactly 46 API endpoints present in commit `47cf8f5` are missing from the deployed Render backend:
  - Fixed Assets: `/api/v1/fixed-assets`, `/api/v1/fixed-assets/{asset_id}`
  - Factory Expenses: `/api/v1/expenses/factory`, `/api/v1/expenses/factory/{expense_id}`
  - Waste Management: `/api/v1/waste`, `/api/v1/waste/{record_id}`
  - Health & Probes: `/api/v1/health/live`, `/api/v1/health/ready`, `/health`, `/health/live`, `/health/ready`
  - Backup Telemetry: `/api/v1/backup/health`
  - Diagnostics: `/diagnostics/download`
  - HR Document Vault: `/api/v1/hr/workers/{worker_id}/citizenship`, `/api/v1/hr/workers/{worker_id}/photo`, `/api/v1/hr/workers/{worker_id}/status`
  - Landed Cost GRN: `/api/v1/purchase/purchases/{purchase_id}/receive`
  - Decoupled Dispatch: `/api/v1/sales/orders/{order_id}/dispatch`
  - Stock Adjustment & Cards: `/api/v1/purchase/materials/{material_id}/adjust`, `/api/v1/purchase/materials/{material_id}/card`

### 7.3 Cause of Drift
GitHub repository `origin/main` is currently pinned to commit `aab3d4a1ff54a0b9dca530569961458b1e356a8a` (Sept 29, 2026). Render automatically deploys from branch `main`. Because the candidate release commit (`47cf8f5`) resides on branch `release/v1.0.0-staging` and has not been merged into `main`, **Render is serving the older pre-release build**.

---

## 8. BACKUP & RECOVERY READINESS AUDIT

| Assessment Area | Current Status | Finding & Risk Assessment |
| :--- | :--- | :--- |
| **Local / Disposable Drill** | **VERIFIED** | PostgreSQL 18 `pg_dump` and `psql` restore executed with 100% table/row match and 0.00 paisa variance. |
| **Automated Scheduler** | **MISSING (`DEF-02`)** | No OS cron job, systemd timer, or cloud cron workflow exists to trigger backups unattended. |
| **Off-Site Cloud Storage** | **UNVERIFIED** | Render Free Web Service has ephemeral disk; Neon database does not export automated off-site dumps to S3/B2. |
| **Retention Policy** | **DOCUMENTED ONLY** | 7-day daily / 4-week retention is documented in runbooks, but no automated prune script is scheduled. |
| **Failure Alerting** | **MISSING** | No webhook or notification is dispatched if a backup fails or if backup age exceeds 24 hours. |
| **Documented Recovery Objectives**| **VERIFIED** | RTO: 2.327 seconds (measured); RPO: 24 hours (target under daily schedule). |

---

## 9. PRIORITIZED REMEDIATION BACKLOG

| Priority | ID | Issue / Defect | Remediation Action | Prerequisites | Verification Standard |
| :---: | :---: | :--- | :--- | :--- | :--- |
| **P0** | **SEC-01** | Unconditional startup seeding of admin demo accounts | Restrict demo seeding to `ENVIRONMENT != "production"`. Remove hardcoded default credentials from frontend state and remove quick-fill buttons in production. | None | Startup on production DB seeds 0 accounts. Login page loads empty input fields. |
| **P0** | **SEC-02** | Migration failures silently caught and swallowed | Remove `try/except` swallow in `backend/app/main.py`. Migration failure must abort startup (`sys.exit(1)`). Decouple migrations from runtime startup. | None | Simulated migration syntax error causes container to exit with code 1. |
| **P1** | **DEF-05** | Cloud staging running legacy 50-path image | Fast-forward or PR-merge `release/v1.0.0-staging` into `main` after user approval; trigger Render & Vercel deployment. | User approval | Render `/api/v1/openapi.json` exposes all 96 paths. |
| **P1** | **DEF-02** | Daily backup scheduler missing OS daemon | Deploy a GitHub Actions scheduled workflow (`.github/workflows/nightly-backup.yml`) or VPS systemd timer invoking `scripts/backup_nightly.sh`. | Cloud database URL | Backup artifact successfully uploaded and logged daily. |
| **P2** | **SEC-03** | In-memory rate limiting trusts spoofed `X-Forwarded-For` | Validate proxy IP against trusted reverse proxy CIDRs; migrate rate limiter counters to Redis or DB for multi-worker scaling. | Proxy setup | Injected `X-Forwarded-For` headers cannot bypass rate limit threshold. |
| **P2** | **SEC-06** | `/health` returns HTTP 200 when database is unhealthy | Update `/health` to return HTTP 503 when `database != "healthy"`, or configure cloud platform health checks to probe `/health/ready`. | None | Injected DB failure causes `/health` to return HTTP 503. |
| **P3** | **DEF-04** | Missing frontend screens for Assets, Expenses, Waste | Implement Next.js views and add sidebar navigation tabs in `AppShell.tsx`. | Client wireframes | Users can view, create, and list assets, expenses, and scrap in browser. |

---

## 10. EXPLICIT "NOT RUN" ITEMS & MISSING EVIDENCE

Under Operating Rule 12, the following verification items could not be executed during this read-only phase:

1. **Production Database Mutation Testing:** `NOT RUN`. Direct testing against live production databases was prohibited to prevent data loss or contamination. Testing was conducted exclusively against isolated, disposable PostgreSQL 18 instances.
2. **Cloud Host Cron / Systemd Inspection:** `NOT RUN`. Direct SSH access to Render or cloud host environments is not available in the local development environment; verification was conducted by inspecting version-controlled repository files.
3. **Live Cloud Migration Execution:** `NOT RUN`. Modifying or applying migrations to the deployed cloud staging database requires user approval to merge/push `release/v1.0.0-staging`.
4. **Gitleaks Binary Execution:** `NOT RUN`. The `gitleaks` CLI is not installed on the host system; an independent non-disclosing regex scanner was used as an alternative.

---

## 11. FORMAL RELEASE DECISIONS

### Decision A: Restricted Client Demonstration
```
========================================================================================
   VERDICT: CONDITIONAL GO
========================================================================================
```
**Justification:** The core business engine (Procurement GRN with 4 landed costs, Production Batches with custom colors, Sales Order Dispatch, 13% Statutory VAT Invoicing, Stock Ledger, AR Aging, and HR Management) is completely implemented and independently verified on genuine PostgreSQL 18 with 0 financial drift and 0 data loss. The live Vercel application renders all 11 core navigation views.

**Mandatory Conditions for Client Demo:**
1. **Synthetic Data Only:** The demonstration must strictly utilize synthetic demonstration records. No actual client financial records or worker documents may be loaded.
2. **Bounded Scope:** The presenter must navigate exclusively within the 11 mounted UI screens. Fixed Assets, Factory Expenses, and Waste Management must be presented as backend-ready APIs with UI screens in progress (`DEF-04`).
3. **Pre-Demo Warm-Up:** The Render free-tier backend requires ~45–50 seconds on cold start. The demonstrator must access `/api/v1/health` 2 minutes prior to the client meeting to wake the container.
4. **Credential Rotation Notice:** Immediately following the demo period, all demo credentials (`admin_demo`, `editor_admin`, `viewer_demo`) must be retired.

---

### Decision B: Production with Real Client Data
```
========================================================================================
   VERDICT: STRICT NO-GO
========================================================================================
```
**Justification:** Deploying this system to production with actual factory records, real payroll data, and live customer invoices is strictly prohibited until the following critical blockers are resolved:
1. `SEC-01`: Startup lifespan auto-seeds known administrative demo accounts in any database, and the frontend login form pre-fills these credentials.
2. `SEC-02`: Lifespan startup catches and swallows migration errors, risking live operation against corrupted schemas.
3. `DEF-05`: The cloud deployment is running legacy September code (50 endpoints) and has not received candidate release `47cf8f5` (96 endpoints).
4. `DEF-02`: No automated, unattended daily backup daemon is operational in cloud staging.
5. Client Business Decisions (`BQ-01` to `BQ-04`) regarding IRD fiscal printer certification and customs capitalization remain unconfirmed by client leadership.

---

## 12. RISK-ORDERED NEXT STEP PLAN

1. **Remediate SEC-01 & SEC-02 (Immediate - Pre-Merge):**
   - Patch `backend/app/main.py` to guard demo seeding behind `ENVIRONMENT != "production"`.
   - Remove exception swallowing so migration failures abort deployment immediately.
   - Patch `frontend/src/app/login/page.tsx` to clear pre-filled credentials.
2. **Obtain User Approval for Staging Deployment:**
   - Present Phase 16.1 findings to user.
   - Request approval to fast-forward `main` to `release/v1.0.0-staging` (`47cf8f5`) or open GitHub Pull Request.
3. **Deploy & Validate Cloud Staging Parity:**
   - Push updated `main` to trigger Render Docker build and Vercel edge deployment.
   - Run unauthenticated HTTP check to verify deployed OpenAPI path count expands from 50 to 96 paths.
4. **Deploy Automated Daily Backup Workflow (`DEF-02`):**
   - Configure a GitHub Actions scheduled workflow with Neon connection secret to execute `pg_dump` daily and upload to encrypted storage.
5. **Conduct Controlled Client Demo:**
   - Execute client demonstration adhering strictly to the Restricted Demo conditions.
