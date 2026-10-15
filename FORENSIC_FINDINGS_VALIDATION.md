# LIVO FOOTWEAR ERP — FORENSIC FINDINGS VALIDATION REPORT

**Audit Date:** October 14, 2026  
**Auditor Roles:** Independent Principal Software Engineer, Software Architect, Application Security Engineer, Database Reliability Engineer, DevOps Engineer, QA Lead, ERP Financial Systems Analyst  
**Audit Baseline Commit:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` (`release/v1.0.0-staging`)  
**Lineage:** `aab3d4a` -> `5caa3f4` (`main`) -> `47cf8f5` (`release/v1.0.0-staging`)  
**Repository:** [https://github.com/Sishir120/livo-footwear-erp](https://github.com/Sishir120/livo-footwear-erp)  
**Mode:** STRICT READ-ONLY VALIDATION & RECONCILIATION (Zero application code modified, zero state altered)

---

## 1. PRESERVATION OF EXISTING STATE

### 1.1 Repository Metadata
- **Current Branch:** `release/v1.0.0-staging`
- **HEAD Commit SHA:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
- **Working Tree Cleanliness:** Modified (Working tree contains uncommitted pre-release hardening and audit artifacts)
- **Tracked Files:** 395
- **Modified Tracked Files:** 23
- **Untracked Files / Directories:** 31

### 1.2 Inventory of Uncommitted Modified Tracked Files (23)
```text
.env.example                                       |   5 +
.env.staging.example                               |   5 +
.gitignore                                         |   1 +
CLIENT_CHANGE_REQUEST_GAP_ANALYSIS.md              | 830 ++++++++-------------
README.md                                          |  18 +-
backend/app/api/v1/analytics.py                    |  21 +-
backend/app/api/v1/health.py                       |   5 +-
backend/app/api/v1/receivables.py                  |   3 +-
backend/app/api/v1/sales.py                        |   5 +-
backend/app/api/v1/stock.py                        |   7 +-
backend/app/config.py                              |  31 +
backend/app/main.py                                | 116 +--
backend/app/middleware/rate_limit.py               |  84 ++-
backend/tests/test_checkpoint_15_query_regression.py|  35 +-
docs/CLIENT_CHANGE_REQUEST_GAP_ANALYSIS.md         | 830 ++++++++-------------
docs/CLIENT_PITCH_CHEATSHEET.md                    |   8 +-
docs/deployment/STAGING_DEPLOYMENT_GUIDE.md        |   2 +-
frontend/src/app/login/page.tsx                    |  52 +-
frontend/src/components/DailyReportView.tsx        |  23 +-
frontend/src/components/PartyStatementModal.tsx    |  49 +-
frontend/src/components/ProductionAnalyticsView.tsx |  13 +-
frontend/src/components/StockCardModal.tsx         |   7 +-
render.yaml                                        |   6 +
```

### 1.3 Inventory of Untracked Files (31)
- **Security & Provisioning Artifacts:**
  - `backend/app/core/demo_seeding.py`
  - `backend/scripts/create_admin.py`
  - `backend/tests/test_phase_16_2_security_remediations.py`
- **Localization & Nepali Date Artifacts:**
  - `backend/tests/test_phase_1_nepali_date_foundation.py`
- **Operational & SRE Infrastructure:**
  - `.github/workflows/scheduled_backup.yml`
  - `docs/deployment/systemd/livo-backup.service`
  - `docs/deployment/systemd/livo-backup.timer`
  - `scripts/cloud_backup.sh`
- **Gap Analysis & Audit Documentation:**
  - `CLIENT_CHANGE_REQUEST_GAP_ANALYSIS_VERIFICATION.md`
  - `FORENSIC_AUDIT_EXECUTIVE_REPORT.md`
  - `docs/architecture/LOCATION_AND_PRODUCT_TRACEABILITY_DESIGN.md`
  - `docs/audits/AI_AGENT_WORK_RECONSTRUCTION.md`
  - `docs/audits/ARCHITECTURE_AND_CODE_QUALITY_AUDIT.md`
  - `docs/audits/BUSINESS_CAPABILITY_AND_WORKFLOW_AUDIT.md`
  - `docs/audits/DATABASE_AND_DATA_INTEGRITY_AUDIT.md`
  - `docs/audits/FINANCIAL_ACCOUNTING_AND_RECONCILIATION_AUDIT.md`
  - `docs/audits/FORENSIC_AUDIT_EXECUTIVE_REPORT.md`
  - `docs/audits/NEPAL_FIRST_BILINGUAL_TRACEABILITY_BASELINE.md`
  - `docs/audits/SECURITY_AND_PRIVACY_AUDIT.md`
  - `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`
  - `docs/deployment/PHASE_16_1_RELEASE_VERIFICATION_REPORT.md`
  - `docs/deployment/PHASE_16_2_SECURITY_REMEDIATION_REPORT.md`
  - `docs/deployment/PHASE_16_3_INDEPENDENT_VERIFICATION_REPORT.md`
  - `docs/deployment/PHASE_16_4_RELEASE_CONFIGURATION_REMEDIATION_REPORT.md`
  - `docs/deployment/PHASE_16_5_INDEPENDENT_PREDEPLOYMENT_GATE_REPORT.md`
  - `docs/deployment/PHASE_16_6_STAGING_BLOCKER_REMEDIATION_REPORT.md`
  - `docs/deployment/PHASE_16_7_RELEASE_INVENTORY_AND_STAGING_ACCEPTANCE_PLAN.md`
  - `docs/deployment/PHASE_16_8_RELEASE_CANDIDATE_CONSISTENCY_REVIEW.md`
  - `docs/deployment/PHASE_16_RELEASE_EXECUTION_REPORT.md`
  - `docs/testing/TRACEABILITY_TEST_PLAN.md`
  - `docs/user-guide/HELP_COVERAGE_MATRIX.md`

### 1.4 Exact Paths of Prior Forensic Audit Deliverables
1. `docs/audits/FORENSIC_AUDIT_EXECUTIVE_REPORT.md` (and root `FORENSIC_AUDIT_EXECUTIVE_REPORT.md`)
2. `docs/audits/SECURITY_AND_PRIVACY_AUDIT.md`
3. `docs/audits/DATABASE_AND_DATA_INTEGRITY_AUDIT.md`
4. `docs/audits/FINANCIAL_ACCOUNTING_AND_RECONCILIATION_AUDIT.md`
5. `docs/audits/BUSINESS_CAPABILITY_AND_WORKFLOW_AUDIT.md`
6. `docs/audits/AI_AGENT_WORK_RECONSTRUCTION.md`
7. `docs/audits/ARCHITECTURE_AND_CODE_QUALITY_AUDIT.md`

---

## 2. VALIDATION OF FINDINGS IN ORDER

### Finding A — Public Credentials and Default Administrator Seeding
- **Finding ID:** `VULN-01` / `VULN-02`
- **Previous Conclusion:** Hardcoded default credentials committed in README; unconditional user seeding on startup; interactive login preset buttons on Vercel frontend.
- **Validation Result:** **CONFIRMED in Baseline Commit `47cf8f5`; PARTIALLY REMEDIATED (UNCOMMITTED) in Local Working Tree.**
- **Source Evidence:**
  - *Committed Baseline (`47cf8f5`):*
    - `README.md:22-35`: Explicitly published `admin_demo` / `LivoAdmin2026!` and `viewer_demo` / `LivoViewer2026!`.
    - `backend/app/main.py:53-112`: Lifespan unconditionally seeded `admin_demo`, `viewer_demo`, `editor_admin`, `viewer_user` with hardcoded bcrypt hashes whenever missing.
    - `frontend/src/app/login/page.tsx:8-9,44-55`: Form pre-filled with `admin_demo` / `LivoAdmin2026!` and rendered clickable "Admin Operator" and "Auditor Viewer" preset buttons.
  - *Uncommitted Working Tree:*
    - `backend/app/config.py:50-58`: Added `ENVIRONMENT` and `ENABLE_DEMO_SEEDING` settings.
    - `backend/app/main.py:79`: Replaced inline seeding with `seed_demo_users_if_enabled(db, company)`.
    - `backend/app/core/demo_seeding.py` (Untracked): Gated seeding behind `if not settings.ENABLE_DEMO_SEEDING: return` and blocked in production.
    - `frontend/src/app/login/page.tsx:8-9`: Removed default state and removed preset buttons.
    - `README.md:22-35`: Replaced credential table with `create_admin.py` CLI instructions.
- **Live Infrastructure Verification:**
  - Frontend (`https://livo-footwear-erp.vercel.app/login`): Verified via browser rendering that the deployed bundle STILL serves the clickable "Admin Operator" preset button and pre-fills credentials.
  - Backend (`https://livo-footwear-erp-backend.onrender.com`): Health check returns `{"status":"ok"}` without commit hash; if running `47cf8f5`, it executed default seeding on boot.
- **Business Impact:** Critical. External unauthenticated attackers can authenticate with full administrative privileges to any instance deployed from commit `47cf8f5`.
- **Remediation Direction:** Commit the uncommitted working-tree changes (`demo_seeding.py`, `create_admin.py`, sanitized `main.py`, sanitized `login/page.tsx`, sanitized `README.md`); trigger a clean redeployment to Vercel and Render.
- **Regression Test:** Execute `pytest backend/tests/test_phase_16_2_security_remediations.py::test_demo_seeding_disabled_by_default` (Asserts 0 users seeded when `ENABLE_DEMO_SEEDING=false`).
- **Dependencies:** None (P0 Blocker).
- **Release Impact:** **CLIENT DEMO BLOCKER & PRODUCTION BLOCKER.**

---

### Finding B — Branch-Level Authorization and IDOR
- **Finding ID:** `VULN-04`
- **Previous Conclusion:** Complete absence of branch/location multi-tenant authorization; cross-branch IDOR.
- **Validation Result:** **CONFIRMED & NUANCED.**
  - *Company-Level Tenancy:* **ENFORCED.** All database tables and API queries filter by `current_user.company_id`. An attacker from Company A CANNOT access Company B's records.
  - *Branch / Warehouse Tenancy:* **COMPLETELY ABSENT.** Within Company A, users have no assigned `warehouse_id` or `branch_id`. Any user with `editor` or `admin` role can read, mutate, adjust, or dispatch inventory across ANY branch or warehouse within the company simply by supplying an arbitrary `warehouse_id`.

#### Route-by-Route Inventory of Location/Branch-Scoped Endpoints

| HTTP Method & Route | Auth Dependency | Role Auth | Branch/Location Validation | Query Scoping | Affected Model & Operation | Source File & Line Range | Isolated Test for Cross-Branch Access |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `POST /api/v1/stock/movements` | `get_current_user` | `require_editor` | **NONE** (Only validates warehouse belongs to company) | `company_id` | `StockMovement` (Create raw/FG movement) | [stock.py:104-175](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/stock.py#L104-L175) | Authenticate as Operator of Branch 1; POST movement with `warehouse_id=2`; assert succeeds (200 OK instead of 403). |
| `POST /api/v1/stock/adjustments` | `get_current_user` | `require_editor` | **NONE** (Only validates warehouse belongs to company) | `company_id` | `StockMovement` (Write-off/Adjustment) | [stock.py:683-718](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/stock.py#L683-L718) | Authenticate as Operator of Branch 1; adjust stock in `warehouse_id=2`; assert succeeds. |
| `GET /api/v1/stock/balances` | `get_current_user` | Any role | **NONE** (Allows optional `warehouse_id` query param) | `company_id` | `StockMovement` (Read balances) | [stock.py:519-565](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/stock.py#L519-L565) | Authenticate as Viewer of Branch 1; query `?warehouse_id=2`; assert returns Branch 2 balances. |
| `GET /api/v1/stock/warehouses/{id}` | `get_current_user` | Any role | **NONE** (Only validates `wh.company_id`) | `company_id` | `Warehouse` (Read warehouse metadata) | [stock.py:497-508](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/stock.py#L497-L508) | Query warehouse metadata of another branch; assert returns 200. |
| `POST /api/v1/sales/orders/{id}/dispatch` | `get_current_user` | `require_editor` | **NONE** (Resolves lowest active warehouse in company) | `company_id` | `SalesOrder`, `StockMovement` (Dispatch goods) | [sales.py:569-603](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/sales.py#L569-L603) | Operator dispatches stock belonging to another branch warehouse; assert succeeds. |
| `POST /api/v1/production/orders` | `get_current_user` | `require_editor` | **NONE** (Accepts `warehouse_id: int = Field(1, gt=0)`) | `company_id` | `ProductionOrder`, `ProductionBatch` | [production.py:285-368](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/production.py#L285-L368) | Create production batch targeting remote branch warehouse; assert succeeds. |
| `POST /api/v1/purchasing/receipts` | `get_current_user` | `require_editor` | **NONE** (Accepts `warehouse_id` in GRN payload) | `company_id` | `RawMaterialStockMovement` | [purchase.py:180-230](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/purchase.py#L180-L230) | Receive raw materials into remote warehouse without check; assert succeeds. |
| `GET /api/v1/hr/workers` | `get_current_user` | Any role | **NONE** (Worker has no factory branch field) | `company_id` | `Worker` (Read payroll & profiles) | [hr.py:85-115](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/hr.py#L85-L115) | Branch 1 manager views worker salaries of Branch 2; assert returns all workers. |
| `POST /api/v1/hr/advances` | `get_current_user` | `require_editor` | **NONE** | `company_id` | `WorkerAdvance` (Issue cash advance) | [hr.py:380-420](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/hr.py#L380-L420) | Branch 1 operator issues advance to Branch 2 worker; assert succeeds. |

- **Business Impact:** High. In a multi-factory or factory-and-retail-branch deployment, floor operators from Branch A can modify stock balances, view payroll, or dispatch orders belonging to Branch B.
- **Remediation Direction:** Add `assigned_warehouse_id` / `assigned_branch_id` (nullable for global admin) to the `User` model; add a FastAPI dependency `require_branch_access(target_warehouse_id)` verifying that non-admin users only operate within their assigned location.
- **Regression Test:** Create User A (assigned to Warehouse 1) and attempt to dispatch inventory or record stock movements in Warehouse 2; assert HTTP 403 Forbidden.
- **Dependencies:** Schema update to `User` table (new Alembic migration).
- **Release Impact:** **PRODUCTION BLOCKER.** (For a single-factory supervised demo, can be accepted with explicit disclosure).

---

### Finding C — Migration Failure and Revision Stamping
- **Finding ID:** `DB-01`
- **Previous Conclusion:** Application startup conditionally stamps revision without proving schema equivalence; startup catches migration exceptions and continues serving traffic on inconsistent schema; no cross-instance locking.
- **Validation Result:** **CONFIRMED in Baseline Commit `47cf8f5`; PARTIALLY REMEDIATED (UNCOMMITTED) in Local Working Tree.**
- **Source Evidence:**
  - *Committed Baseline (`47cf8f5` - `backend/app/main.py:16-29`):*
    ```python
    try:
        ...
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if "companies" in existing_tables and "alembic_version" not in existing_tables:
            command.stamp(alembic_cfg, "002_invoice_uq")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Lifespan DB setup notice: {e}")
    ```
    - **Failure Swallowing:** If `command.upgrade` raises any exception (e.g. database connection drop, lock timeout, SQL syntax error in migration), it prints `Lifespan DB setup notice: ...` and resumes normal startup. The container remains healthy and begins serving API requests on an un-migrated schema.
    - **Arbitrary Revision Stamping:** If `companies` exists but `alembic_version` is absent, it blindly stamps `002_invoice_uq` without inspecting whether columns from `003` through `020` are present.
    - **No Process Locking:** Multiple instances starting concurrently run `command.upgrade` simultaneously against the same PostgreSQL database, risking duplicate DDL execution and deadlocks.
  - *Uncommitted Working Tree (`backend/app/main.py:26-47`):*
    - Wraps migration in `_migration_lock = threading.Lock()`.
    - Removed `command.stamp(alembic_cfg, "002_invoice_uq")`.
    - Added `try... except Exception as e: logger.critical(...); raise RuntimeError(...)` to fail startup immediately.
    - Added `AUTO_MIGRATE: bool` toggle to allow disabling runtime migrations in favor of CI/CD pre-deployment release commands.
- **Business Impact:** High. Serves user transactions on corrupted or half-migrated database schemas, leading to HTTP 500 crashes and unrecoverable data integrity violations.
- **Remediation Direction:** Commit the fail-fast startup logic; recommend running migrations in deployment release steps (`alembic upgrade head` before container spin-up) rather than inside application lifespan.
- **Regression Test:** Create a broken dummy migration in an isolated environment and run application startup; assert process exits with non-zero exit code (`RuntimeError`).
- **Dependencies:** None.
- **Release Impact:** **PRODUCTION BLOCKER.**

---

### Finding D — Financial Accounting Completeness
- **Finding ID:** `FIN-01`
- **Previous Conclusion:** System is an Operational ERP with Subledgers, NOT a double-entry General Ledger accounting system.
- **Validation Result:** **CONFIRMED 100%.**
- **Evidence Matrix:**

| Financial Accounting Capability | Status in Codebase | Source File & Evidence Reference | Description of Actual Implementation |
| :--- | :---: | :--- | :--- |
| **Chart of Accounts** | **NOT FOUND** | Entire active tree searched; 0 matches. | No account classes (Asset, Liability, Equity, Revenue, Expense) or account code models exist. |
| **Journal Entries & Lines** | **NOT FOUND** | `alembic/versions/762ea2a34ccb:28-35` | Legacy journal tables (`journal_entries`, `journal_lines`, `accounts`) were **explicitly dropped**. Unscoped prototype in `_unscoped/` is dead code. |
| **Debit/Credit Balancing** | **NOT FOUND** | `models/sales.py:165-200` | Only exists as `debit_paisa` / `credit_paisa` columns in `customer_ledger_entries` for AR party statement; not a balanced dual-entry mechanism. |
| **Posting & Reversals** | **PARTIAL** | `sales.py:640`, `invoices.py:220` | Operational voids exist (void invoice, cancel order, void stock movement), but zero general ledger journal posting or reversal rules exist. |
| **Accounting Periods & Closing** | **NOT FOUND** | Entire active tree searched; 0 matches. | No fiscal year model, no period close, and no period lock controls exist. Transactions can be recorded on any date without period enforcement. |
| **Trial Balance** | **NOT FOUND** | Only exists in unmounted `_unscoped/tally-export/` | Cannot generate a trial balance because no general ledger accounts exist. |
| **General Ledger Report** | **NOT FOUND** | `api/v1/reports.py:15-161` | `/api/v1/reports` only contains `/daily` (counts) and `/stock` (catalog quantities). Zero GL reports. |
| **Profit & Loss Statement** | **NOT FOUND** | Entire active tree searched; 0 matches. | No P&L computation across revenues and expenses. |
| **Balance Sheet** | **NOT FOUND** | Entire active tree searched; 0 matches. | No Balance Sheet computation. |
| **Cash-Flow Reporting** | **NOT FOUND** | Entire active tree searched; 0 matches. | No cash-flow statement generation. |
| **Bank Reconciliation** | **NOT FOUND** | Entire active tree searched; 0 matches. | Payment method field accepts strings `"CASH"` / `"BANK"`, but no bank statement import or reconciliation ledger exists. |
| **Inventory Valuation & COGS** | **PARTIAL** | `reports.py:149`, `purchase.py:210` | Valuation is calculated on-the-fly as `current_stock * unit_price` (sales price, not FIFO/weighted-average cost). Landed costs are tracked on raw materials, but COGS is never debited on sales dispatch. |

- **Business Impact:** High. Client stakeholders expecting a replacement for accounting software (e.g. Tally) will find statutory financial statements completely absent.
- **Remediation Direction:** Formally reclassify system as an "Operational Footwear Manufacturing & Inventory ERP with Specialized Subledgers" and build an external accounting sync bridge (Tally/QuickBooks), OR engineer a full double-entry GL ledger.
- **Regression Test:** N/A (Module does not exist).
- **Dependencies:** Business alignment with client on accounting scope.
- **Release Impact:** **CLIENT EXPECTATION BLOCKER / PRODUCTION BLOCKER FOR STATUTORY ACCOUNTING.**

---

### Finding E — Inventory and Transfer Integrity
- **Finding ID:** `BIZ-01` / `BIZ-02`
- **Previous Conclusion:** Batch creation works, but sales dispatch severs batch linkage; inter-branch transfers are completely missing from API/models.
- **Validation Result:** **CONFIRMED 100%.**
- **Detailed Component Verification:**
  1. **Batch Creation & Finished Goods Receipt:** **VERIFIED.** In `backend/app/api/v1/production.py:480-530`, completing a `ProductionOrder` generates a `ProductionBatch` record with batch number, SKU, size, color, produced pairs, date AD, and date BS, and atomically inserts a `StockMovement` (+1 direction, `PRODUCTION_IN`).
  2. **Batch Linkage During Sales Dispatch:** **REFUTED / ABSENT.** In `backend/app/models/sales.py:95-110`, `SalesItem` has only `product_id` and `quantity`. When `dispatch_sales_order` runs ([sales.py:586-603](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/sales.py#L586-L603)), the outgoing `StockMovement` records `product_id` and `size`, but has NO `batch_id`. The system cannot trace which production batch was shipped to a client.
  3. **Stock Movement & Balance Consistency:** **VERIFIED.** Append-only `StockMovement` ledger strictly enforces zero-negative-stock validation before any dispatch or adjustment. Mutex / advisory locks prevent race conditions during deduction.
  4. **Location Transfers & In-Transit Quantities:** **COMPLETELY ABSENT.** There is no `stock_transfers` table, no transfer API router, no in-transit warehouse state, and no destination receipt confirmation screen in either frontend or backend.
  5. **Duplicate Request Protection:** **VERIFIED.** Idempotency keys are supported via `idempotency_records` table on key endpoints.
- **Business Impact:** High. Inability to execute targeted batch recalls upon discovering shoe defects; inability to transfer stock between factory warehouse and branch stores with auditable in-transit custody.
- **Remediation Direction:**
  - Add `batch_id` foreign key to `sales_items` and `stock_movements`.
  - Create a dedicated `StockTransfer` model with states: `DRAFT` -> `DISPATCHED_IN_TRANSIT` -> `RECEIVED_CONFIRMED` -> `DISCREPANCY_RECONCILED`.
- **Regression Test:** Execute sales dispatch with batch selection; assert `stock_movements.batch_id` matches selected batch. Execute branch transfer; assert stock leaves Source Warehouse, sits in In-Transit, and is added to Destination Warehouse only upon destination confirmation.
- **Dependencies:** Database migration for `batch_id` and `stock_transfers`.
- **Release Impact:** **PRODUCTION BLOCKER FOR MULTI-BRANCH MANUFACTURING.**

---

### Finding F — Test Evidence Baseline
- **Finding ID:** `TEST-01`
- **Previous Conclusion:** 375 tests passing in ~130s; frontend TypeScript compilation passes; heavy reliance on SQLite; Postgres concurrency untested in CI.
- **Validation Result:** **CONFIRMED & INDEPENDENTLY REPRODUCED.**
- **Exact Reproduction Execution:**
  - **Command:** `backend\venv\Scripts\python.exe -m pytest backend/tests -rs -q`
  - **Exit Code:** `0`
  - **Duration:** 128.23s (0:02:08)
  - **Passed Tests:** 374
  - **Skipped Tests:** 2
    - `backend/tests/test_checkpoint_15_query_regression.py:392: Invoice creation failed (likely insufficient stock)`
    - `backend/tests/test_checkpoint_15_query_regression.py:412: Invoice creation failed`
  - **Warnings:** 356 (FastAPI / Starlette deprecation warnings regarding `HTTP_422_UNPROCESSABLE_ENTITY` and TestClient cookie persistence)
  - **Frontend Build Verification:**
    - **Command:** `npx tsc --noEmit` in `frontend/`
    - **Exit Code:** `0` (Zero TypeScript compilation errors)
- **Database Backend Limitation:**
  - 46 of the 48 test files execute strictly against SQLite (`sqlite:///./livo_dev.db` or temporary SQLite files).
  - PostgreSQL advisory locking (`pg_advisory_xact_lock`), JSONB operator queries, and multi-threaded row-level lock contention under high write volume remain unverified in CI because CI environments default to SQLite.
- **Business Impact:** Medium. Code works reliably on developer machines, but production-specific PostgreSQL deadlocks or concurrency bottlenecks could surface under heavy multi-user load.
- **Remediation Direction:** Configure CI/CD pipeline (GitHub Actions) with a Postgres service container running the test suite with `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/livo_test`.
- **Regression Test:** Run full pytest suite against real PostgreSQL 16 container.
- **Dependencies:** GitHub Actions workflow update.
- **Release Impact:** **PRODUCTION HARDENING REQUIREMENT.**

---

## 3. WORKING-TREE RECONCILIATION

The repository working tree currently contains 23 modified tracked files and 31 untracked files. Through forensic analysis of git diffs, file timestamps, and implementation comments, these changes are categorized into five distinct functional groups:

### Category 1: Security Hardening & Provisioning (Pre-Release Phase 16.2 / 16.10)
*Status: Uncommitted modifications and untracked scripts that MUST be preserved and committed.*
- `backend/app/config.py`: Adds `ENVIRONMENT`, `ENABLE_DEMO_SEEDING`, `TRUSTED_PROXIES`.
- `backend/app/main.py`: Removes hardcoded users, fails fast on migration errors, gates seeding.
- `backend/app/middleware/rate_limit.py`: RFC 7239 compliant client IP extraction with trusted CIDR proxy checking.
- `backend/app/core/demo_seeding.py` (Untracked): Opt-in demo seeding logic forbidden in production.
- `backend/scripts/create_admin.py` (Untracked): Interactive CLI admin account creation utility.
- `backend/tests/test_phase_16_2_security_remediations.py` (Untracked): Automated tests for SEC-01, SEC-02, SEC-03.
- `README.md`: Sanitized to remove plaintext credentials and document CLI setup.
- `frontend/src/app/login/page.tsx`: Removed preset login buttons and hardcoded form values.
- `.env.example`, `.env.staging.example`, `render.yaml`: Updated environment variables.

### Category 2: Nepal-First & Bikram Sambat UI Enhancements (Master Directive Phase 1)
*Status: Uncommitted functional improvements that MUST be preserved.*
- `backend/app/api/v1/analytics.py`: Uses `ad_to_bs_str` from `app.core.nepali_date`.
- `backend/app/api/v1/health.py`: Exposes `commit` hash on health and readiness endpoints.
- `backend/app/api/v1/receivables.py`: Populates canonical BS date on AR payment receipts.
- `backend/app/api/v1/sales.py`: Populates canonical BS date on sales dispatches.
- `backend/app/api/v1/stock.py`: Populates canonical BS date on movements and adjustments.
- `backend/tests/test_phase_1_nepali_date_foundation.py` (Untracked): Unit tests for BS dates.
- `frontend/src/components/DailyReportView.tsx`: BS date picker integration.
- `frontend/src/components/PartyStatementModal.tsx`: Displays both BS and AD dates for voucher ref, particulars, and due dates.
- `frontend/src/components/ProductionAnalyticsView.tsx`: NepaliDatePicker integration for shift dates.
- `frontend/src/components/StockCardModal.tsx`: Prominently displays BS date with AD secondary.

### Category 3: Forensic Audit Deliverables (Current Audit)
*Status: New documentation files in `docs/audits/` and root; preserved.*
- `FORENSIC_AUDIT_EXECUTIVE_REPORT.md` (root and `docs/audits/`)
- `docs/audits/SECURITY_AND_PRIVACY_AUDIT.md`
- `docs/audits/DATABASE_AND_DATA_INTEGRITY_AUDIT.md`
- `docs/audits/FINANCIAL_ACCOUNTING_AND_RECONCILIATION_AUDIT.md`
- `docs/audits/BUSINESS_CAPABILITY_AND_WORKFLOW_AUDIT.md`
- `docs/audits/AI_AGENT_WORK_RECONSTRUCTION.md`
- `docs/audits/ARCHITECTURE_AND_CODE_QUALITY_AUDIT.md`
- `FORENSIC_FINDINGS_VALIDATION.md` (this report)
- `REMEDIATION_ROADMAP.md`

### Category 4: Operational SRE & Backup Infrastructure
*Status: Untracked scripts and systemd units for cloud backup automation.*
- `.github/workflows/scheduled_backup.yml`
- `docs/deployment/systemd/livo-backup.service`
- `docs/deployment/systemd/livo-backup.timer`
- `scripts/cloud_backup.sh`
- `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`

### Category 5: Gap Analysis Documentation Updates
*Status: Documentation updates reconciling client change requests.*
- `CLIENT_CHANGE_REQUEST_GAP_ANALYSIS.md` (Modified)
- `CLIENT_CHANGE_REQUEST_GAP_ANALYSIS_VERIFICATION.md` (Untracked)
- `docs/CLIENT_CHANGE_REQUEST_GAP_ANALYSIS.md` (Modified)

---

## 4. SUMMARY OF VALIDATION STATUS

| Finding | Description | Baseline Commit (`47cf8f5`) | Local Working Tree | Release Gate Assessment |
| :--- | :--- | :---: | :---: | :--- |
| **Finding A** | Public Credentials & Default Seeding | **VULNERABLE** | **PATCHED (UNCOMMITTED)** | Blocked until working tree is committed & deployed. |
| **Finding B** | Branch-Level Authorization (IDOR) | **VULNERABLE** | **VULNERABLE** | Production Blocker; requires new branch tenancy model. |
| **Finding C** | Startup Migration Failure Swallowing | **VULNERABLE** | **PATCHED (UNCOMMITTED)** | Blocked until working tree is committed & deployed. |
| **Finding D** | Absence of General Ledger Accounting | **CONFIRMED** | **CONFIRMED** | Operational ERP with subledgers only; requires formal client sign-off. |
| **Finding E** | Severed Batch Traceability & Missing Transfers | **CONFIRMED** | **CONFIRMED** | Production Blocker for multi-branch traceability. |
| **Finding F** | Test Baseline & SQLite Dependency | **CONFIRMED** | **CONFIRMED** | 374 passed, 2 skipped; Postgres CI required. |
