# LIVO FOOTWEAR ERP — MASTER EVIDENCE INDEX & CITATION REGISTER

**Document Identifier:** `11_EVIDENCE_INDEX.md`  
**Audit Directory:** `docs/audit_20261014_093500/`  
**Audit Execution Date:** 2026-10-14 09:35:00 +05:45 (Nepal Standard Time)  
**Standardized Epistemic Labels:**  
- **`[FACT]`** — Directly established by recovered source code, database catalog, Git commit, or task execution log.
- **`[INFERENCE]`** — Reasoned conclusion derived from identified code patterns, timestamps, or system behavior.
- **`[RECOMMENDATION]`** — Proposed architectural, operational, or business action.
- **`[UNKNOWN]`** — Historical record or evidence is incomplete or inaccessible.

---

## 1. REPOSITORY & CODE ARTIFACT EVIDENCE

| Evidence ID | Repository File Path | Code Symbol / Entity | Line Range | Commit SHA / State | Epistemic Status & Proven Fact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EV-CODE-01** | `backend/app/main.py` | `lifespan(app)` | L18–L36 | Uncommitted / `5caa3f4` | **`[FACT]`** Alembic auto-upgrade to HEAD runs at startup; catches exceptions without crashing process. |
| **EV-CODE-02** | `backend/app/main.py` | Default Seeding | L38–L100 | Uncommitted / `5caa3f4` | **`[FACT]`** Automatically seeds tenant company `LIVO` and demo users `admin_demo`, `viewer_demo`, `editor_admin`, `viewer_user`. |
| **EV-CODE-03** | `backend/app/db/repository.py` | `TenantRepository` | L8–L84 | Tracked / `181697a` | **`[FACT]`** Enforces `company_id` on all queries; strips `company_id` on update payloads to prevent tenant hijacking. |
| **EV-CODE-04** | `backend/app/api/deps.py` | `get_current_user` | L20–L60 | Tracked / `5caa3f4` | **`[FACT]`** Authenticates via `livo_access_token` cookie or Bearer header; verifies user active status and company ID. |
| **EV-CODE-05** | `backend/app/api/deps.py` | `require_editor`, `require_admin` | L62–L82 | Tracked / `5caa3f4` | **`[FACT]`** Rejects `viewer` role with HTTP 403 Forbidden on all mutating endpoints. |
| **EV-CODE-06** | `backend/app/core/nepali_date.py` | `ad_to_bs`, `bs_to_ad` | L1–L150 | Untracked (Phase 1) | **`[FACT]`** Zero-dependency deterministic algorithmic conversion between Gregorian AD and Bikram Sambat BS (2065–2095 BS). |
| **EV-CODE-07** | `frontend/src/components/NepaliDatePicker.tsx` | `NepaliDatePicker` | L1–L777 | Untracked (Phase 1) | **`[FACT]`** Interactive dropdown calendar popup with day-of-week headers, Saturday highlight, and bidirectional AD sync. |
| **EV-CODE-08** | `backend/app/api/v1/sales.py` | `dispatch_sales_order` | L470–L600 | Uncommitted / `5caa3f4` | **`[FACT]`** Decouples order from dispatch; acquires advisory locks; verifies physical stock; appends StockMovement (-1). |
| **EV-CODE-09** | `backend/app/api/v1/purchase.py` | `handle_receive_purchase` | L258–L335 | Uncommitted / `5caa3f4` | **`[FACT]`** Decouples PO from GRN; locks raw material; calculates 4-column landed costs; capitalizes into effective unit rate. |
| **EV-CODE-10** | `backend/app/api/v1/invoices.py` | `create_invoice` | L110–L160 | Uncommitted / `5caa3f4` | **`[FACT]`** Enforces mandatory 13% statutory Nepal VAT; prevents duplicate VAT invoices for same order. |
| **EV-CODE-11** | `backend/app/api/v1/hr.py` | `_reconcile_worker_advances` | L109–L180 | Uncommitted / `5caa3f4` | **`[FACT]`** Reconciles total issued vs recovered; handles linked parent/child recoveries and legacy unlinked FIFO pools. |
| **EV-CODE-12** | `backend/app/api/v1/gallery.py` | `upload_product_image` | L37–L140 | Uncommitted / `5caa3f4` | **`[FACT]`** Validates product batch match; verifies JPEG/PNG/WEBP binary header magic bytes; blocks executable stems. |
| **EV-CODE-13** | `backend/app/middleware/idempotency.py`| `IdempotencyMiddleware` | L25–L60 | Untracked (C8) | **`[FACT]`** Enforces exactly-once execution for mutating requests with `Idempotency-Key`; uses advisory locks and payload hash. |
| **EV-CODE-14** | `frontend/src/lib/offlineQueue.ts` | Mutation Outbox | L1–L60 | Uncommitted / `5caa3f4` | **`[FACT]`** IndexedDB v2 outbox queue with exponential backoff and auth-expiration pause safety. |
| **EV-CODE-15** | `backend/app/services/backup_service.py`| `run_database_backup` | L88–L154 | Uncommitted / `5caa3f4` | **`[FACT]`** Backup execution routine exists, but is invoked only via manual API call; zero automated cron daemon exists. |
| **EV-CODE-16** | `frontend/src/components/AppShell.tsx` | `navItems` Navigation | L121–L132 | Uncommitted / `5caa3f4` | **`[FACT]`** Fixed Assets, Factory Expenses, and Waste Management are absent from frontend navigation. |

---

## 2. DATABASE & MIGRATION EVIDENCE

| Evidence ID | Artifact Path | Specific Entity / Detail | Revision ID / Status | Epistemic Status & Proven Fact |
| :--- | :--- | :--- | :--- | :--- |
| **EV-DB-01** | `backend/migrations/versions/010_client_change_requests_core.py` | Revision 010 (Core) | `010_client_change_requests_core` | **`[FACT]`** Extended `raw_materials.unit`, `sales_orders.dispatch_date_ad/bs`, `purchases.receipt_date_ad/bs`. |
| **EV-DB-02** | `backend/migrations/versions/013_merge_heads.py` | Revision 013 (Merge) | `013_merge_heads` | **`[FACT]`** Successfully merged branch head `012_add_c15_indexes` and `010_client_change_requests_core`. |
| **EV-DB-03** | `backend/migrations/versions/020_fixed_assets_waste_and_expenses.py`| Revision 020 (Head) | `020_fixed_assets_waste_and_expenses` | **`[FACT]`** Created `fixed_assets`, `waste_records`, `factory_expenses` tables. Linear DAG terminus. |
| **EV-DB-04** | `backend/livo_dev.db` | `alembic_version` Table | Value: `020_fixed_assets_waste_and_expenses` | **`[FACT]`** Local SQLite database catalog is upgraded to the latest migration revision 020. |
| **EV-DB-05** | `backend/livo_dev.db` | Catalog Tables | 36 Relational Tables | **`[FACT]`** 36 tables exist in SQLite master catalog matching SQLAlchemy models. |
| **EV-DB-06** | `backend/backups/livo_backup_20261013_025645.sql` | Backup File | Size: 35 bytes | **`[FACT]`** File contains `-- MOCKED PG_DUMP SQL BACKUP DATA`, proving test suite writes mock dumps. |

---

## 3. TASK LOGS & TEST EXECUTION EVIDENCE

| Evidence ID | Task Log Path | Exact Command Line | Exit Code & Metrics | Epistemic Status & Proven Fact |
| :--- | :--- | :--- | :--- | :--- |
| **EV-TASK-01** | `task-13956.log` (5,118 bytes) | `backend\venv\Scripts\pytest backend/tests/ -q` | Code 0: `354 passed, 3 skipped, 357 warnings in 81.37s` | **`[FACT]`** The complete backend test suite passed with 354 successful tests on 2026-10-13 07:57:45 +05:45. |
| **EV-TASK-02** | `task-13181.log` (49,955 bytes) | `backend\venv\Scripts\pytest backend/tests/` (Including PG) | `6 failed, 304 passed, 3 skipped, 41 errors` | **`[FACT]`** PostgreSQL tests threw setup errors when run without active PostgreSQL instance on Windows. |
| **EV-TASK-03** | `task-12280.log` (8,354 bytes) | `pytest backend/tests/test_adversarial_security_sprint.py` | Code 0: `54 passed in 9.24s` | **`[FACT]`** Adversarial fuzz testing and boundary checks passed completely during 72-hour security sprint. |
| **EV-TASK-04** | `task-9652.log` (757 bytes) | `pytest backend/tests/test_backup.py` | Code 0: `3 passed in 6.69s` | **`[FACT]`** Backup service functions and restore logic passed in isolation with mock subprocess. |
| **EV-TASK-05** | `task-9634.log` (1,681 bytes) | `pytest backend/tests/test_nepali_date.py` | Code 0: `14 passed in 10.31s` | **`[FACT]`** Bikram Sambat leap year math and bidirectional conversion passed all assertions. |
| **EV-TASK-06** | Current Turn Command | `npx tsc --noEmit` (frontend) | Code 0: Clean compilation | **`[FACT]`** Frontend TypeScript codebase compiles with zero type errors on 2026-10-14. |

---

## 4. TRANSCRIPT & AI AGENT SESSION EVIDENCE

| Evidence ID | Transcript Conversation ID | Step Index | Timestamp (UTC) | Description of Recorded Action |
| :--- | :--- | :--- | :--- | :--- |
| **EV-TR-01** | `c93f97bb-7954-4d43-b42b-64ef583ff6ee` | Step 5 | 2026-09-25 11:33:41 | User initiates project with PRD.md; requests English interface and Tally Prime inspiration. |
| **EV-TR-02** | `7dd57806-2f21-4cd0-b7e9-a6db6cb5fe9d` | Step 0 | 2026-10-01 12:03:38 | Checkpoint 8 initiated: Idempotency, duplicate operations, and retry safety. |
| **EV-TR-03** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 8147 | 2026-10-02 09:51:40 | Checkpoint 16 initiated: Multi-tenant isolation adversarial penetration testing. |
| **EV-TR-04** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 9166 | 2026-10-02 15:04:47 | Checkpoint 18 initiated: Production deployment, live validation & client acceptance. |
| **EV-TR-05** | `171235dc-bafc-4da5-8b3e-698949d80c90` | Step 0 | 2026-10-10 11:41:39 | User introduces client change requests; mandates requirements-to-codebase gap analysis. |
| **EV-TR-06** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 12843 | 2026-10-12 12:12:52 | User authorizes Vercel demo forensic audit and DOM browser subagent execution. |
| **EV-TR-07** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 14121 | 2026-10-13 02:51:36 | User prompts: `# LIVO ERP — Final Release Gate and Client Demo Readiness Audit`. |
| **EV-TR-08** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 14144 | 2026-10-13 02:56:52 | Agent launches full 357 backend test suite (`pytest backend/tests/ -q`). |
| **EV-TR-09** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Step 14145 | 2026-10-13 03:05:01 | Context compacted; `transcript.jsonl` step marked `CLEARED`. |
| **EV-TR-10** | `1849f93e-c4c7-4ece-b3df-2d5c85fa991d` | Steps 14146–23405 | 2026-10-13 03:05:02 to 14:54:22 | Agent loops for 9,259 steps attempting to read its own growing transcript file until halted. |

---

## 5. DOCUMENTATION & REPORT ARTIFACT EVIDENCE

| Evidence ID | Document Path | Section / Claim | Evaluated Truth Value |
| :--- | :--- | :--- | :--- |
| **EV-DOC-01** | `docs/CHECKPOINT_18_REPORT.md` | §1: Deployment Environment, §3: Migration Head | **`[FACT]`** Accurately reflects state on Oct 2, 2026; **`[OUTDATED]`** relative to Oct 14 state. |
| **EV-DOC-02** | `CLIENT_REQUIREMENTS_IMPLEMENTATION_TRACKER.md`| §1: Requirements Matrix | **`[PARTIALLY_CONFIRMED]`** REQ-A through REQ-G verified; **`[CONTRADICTED]`** for REQ-H/I (No UI) and REQ-J (No Cron). |
| **EV-DOC-03** | `docs/VERCEL_DEMO_FORENSIC_AUDIT.md` | §1.2: Cloud Desynchronization (DEF-03) | **`[FACT]`** Accurately identifies that Vercel/Render is running commit `aab3d4a` (Sept 29). |
| **EV-DOC-04** | `docs/FINANCIAL_PRECISION_REVIEW.md` | Integer Paisa Engine & Quantization | **`[FACT]`** Corroborated by active code in `currency.py`, `sales.py`, `invoices.py`, `hr.py`. |
| **EV-DOC-05** | `PRD.md` | §3.7 & §7: Stated Top Client Priorities | **`[FACT]`** Client named Daily Report and Stock Report as #1 and #2 success criteria. |
