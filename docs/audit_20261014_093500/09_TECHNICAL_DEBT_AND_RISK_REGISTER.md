# LIVO FOOTWEAR ERP — TECHNICAL DEBT & RISK REGISTER

**Document Identifier:** `09_TECHNICAL_DEBT_AND_RISK_REGISTER.md`  
**Audit Directory:** `docs/audit_20261014_093500/`  
**Audit Execution Date:** 2026-10-14 09:35:00 +05:45 (Nepal Standard Time)  
**Classification Categories:**  
Confirmed Defect (DEF), Potential Defect (POT), Architectural Risk (ARCH), Security Risk (SEC), Data Integrity Risk (DATA), Usability Gap (UI), Operational Gap (OPS), Technical Debt (DEBT).

---

## 1. REGISTER SUMMARY & SEVERITY DISTRIBUTION

The forensic audit identified 14 technical items across the codebase:

```text
Critical Severity: 2 items  (Working tree drift, lack of automated backup daemon)
High Severity:     4 items  (Cloud desynchronization, 3 missing frontend views, uncommitted migrations)
Medium Severity:   5 items  (Missing frontend tests, Starlette deprecations, embedded postgres Windows failures)
Low Severity:      3 items  (Mocked backup artifact clutter, console warnings, demo sleep delays)
```

---

## 2. PRIORITIZED DEFECT & RISK REGISTER

### DEF-01: Working Tree Uncommitted Drift & Catastrophic Loss Exposure
- **Category:** Operational Gap / Technical Debt.
- **Severity:** **CRITICAL**.
- **Likelihood:** HIGH.
- **Business Impact:** High risk of losing 2 weeks of intensive development work (Phases 1–4B, BS datepicker, landed costs, citizenship vaults, migrations 010–020) if an accidental `git checkout`, `git clean`, or branch switch occurs.
- **Technical Impact:** 70 modified tracked files (+9,204 lines, -1,855 lines) and 44 untracked files sit exposed in the working tree.
- **Evidence:** `git status --short` output; commit HEAD `5caa3f4` dated Sept 30, 2026.
- **Affected Modules:** Whole repository.
- **Root Cause:** Sprints from Checkpoints 8 through 18 and Phases 1–4B were executed directly in the working directory without atomic commits to Git branches.
- **Remediation:** Immediately stage and commit all verified changes into a dedicated release branch: `git checkout -b release/v1.0.0-phase4b-client-ready && git add . && git commit -m "feat: complete Phase 1-4B client change requests, migrations 010-020, and hardening"`.
- **Requires Business Decision:** NO.
- **Safe to Implement Independently:** YES (Immediate priority).
- **Estimated Effort:** 15–30 minutes.

---

### DEF-02: Absence of Automated Daily Backup Daemon
- **Category:** Confirmed Defect / Operational Gap.
- **Severity:** **CRITICAL**.
- **Likelihood:** HIGH.
- **Business Impact:** High risk of total catastrophic data loss if the server hardware fails or the database is corrupted, because backups only run when manually triggered via API.
- **Technical Impact:** No cron job, systemd timer, or background task scheduler is registered in `backend/app/main.py`. The 150+ `.sql` files in `backend/backups/` are 35-byte mocked test artifacts containing `-- MOCKED PG_DUMP SQL BACKUP DATA`.
- **Evidence:** `backend/app/services/backup_service.py:88-154`; absence of any scheduler in `main.py`; inspection of `backend/backups/livo_backup_20261013_025645.sql` (35 bytes).
- **Affected Modules:** `backend/app/services/backup_service.py`, `backend/app/main.py`.
- **Root Cause:** The backup service was developed as a synchronous function intended to be called by an external cron daemon, but the daemon was never configured or deployed.
- **Remediation:** 
  1. Add a background task runner (e.g. `APScheduler` or standard `asyncio` background task) in `main.py` lifespan that invokes `run_database_backup()` at 02:00 NPT daily.
  2. For Linux VPS deployments, provide an `/etc/systemd/system/livo-backup.timer` configuration.
  3. Purge the 150+ 35-byte mock `.sql` files from `backend/backups/`.
- **Requires Business Decision:** YES (Client must provide cloud backup credentials per BQ-07).
- **Safe to Implement Independently:** Yes for local scheduling; cloud sync requires credentials.
- **Estimated Effort:** 2–4 hours.

---

### DEF-03: Live Cloud Deployment Desynchronization
- **Category:** Confirmed Defect / Operational Gap.
- **Severity:** **HIGH**.
- **Likelihood:** CERTAIN (100% on live URL).
- **Business Impact:** If a client or stakeholder opens `https://livo-footwear-erp.vercel.app`, they cannot test any of the October client requirements (worker citizenship documents, BS datepicker, landed costs, advance recovery). Endpoints return `HTTP 404`.
- **Technical Impact:** Vercel frontend and Render backend are running commit `aab3d4a` (Sept 29). The cloud database is at migration `009`.
- **Evidence:** `docs/VERCEL_DEMO_FORENSIC_AUDIT.md` §1.2 ("DEF-03: Cloud Desynchronization"); live network response inspection.
- **Affected Modules:** Deployment pipelines, Render Web Service, Vercel Edge.
- **Root Cause:** Development occurred exclusively in the local offline workspace; commits and pushes were suspended during adversarial testing.
- **Remediation:** Once DEF-01 is committed, push the release branch to GitHub origin and trigger a synchronized deployment on Render and Vercel. Execute `alembic upgrade head` on the cloud database.
- **Requires Business Decision:** NO.
- **Safe to Implement Independently:** YES (Once committed).
- **Estimated Effort:** 1–2 hours.

---

### DEF-04: Missing Frontend UI for Fixed Assets, Factory Expenses & Waste Scrap
- **Category:** Missing Functionality / Usability Gap.
- **Severity:** **HIGH**.
- **Likelihood:** CERTAIN (100% in UI).
- **Business Impact:** Client specifically requested Fixed Assets, Factory Expenses, and Waste Management (REQ-G, REQ-H, REQ-I). Client will perceive these features as completely missing despite full backend implementation.
- **Technical Impact:** Three backend routers (`assets.py`, `factory_expenses.py`, `waste.py`) and database tables (`fixed_assets`, `factory_expenses`, `waste_records`) exist with zero frontend connectivity.
- **Evidence:** Audit of `frontend/src/components/AppShell.tsx:120-132`; absence of any asset or waste components in `frontend/src/components/`.
- **Affected Modules:** `frontend/src/components/AppShell.tsx`, `frontend/src/components/*`.
- **Root Cause:** Backend endpoints were implemented during Phase 4B recovery sprints, but development was interrupted by the compaction loop incident before frontend components were authored.
- **Remediation:** Create three lightweight, high-density React components:
  1. `FixedAssetsView.tsx` (Asset tags, acquisition dates, purchase costs, depreciation status).
  2. `FactoryExpensesView.tsx` (Daily overhead vouchers, category filters, totals).
  3. `WasteScrapView.tsx` (Offcut scrap logging, disposal methods, scrap revenue).
  Mount them into `AppShell.tsx` navigation.
- **Requires Business Decision:** YES (Client must confirm UI placement per BQ-02).
- **Safe to Implement Independently:** Yes, using standard default placement.
- **Estimated Effort:** 4–6 hours.

---

### DEF-05: Complete Absence of Frontend Test Suites
- **Category:** Technical Debt / QA Gap.
- **Severity:** **MEDIUM**.
- **Likelihood:** HIGH.
- **Business Impact:** Regressions in complex UI forms (like the 777-line `NepaliDatePicker` or the multi-tab `PurchaseView`) can only be caught via manual click-testing.
- **Technical Impact:** `frontend/package.json` contains no `test` script; `frontend/src/` contains 0 unit or component test files.
- **Evidence:** Inspection of `frontend/package.json:5-10`; file scan of `frontend/src/`.
- **Affected Modules:** `frontend/src/components/*`.
- **Root Cause:** Early development prioritized speed of visual MVP delivery over frontend Jest/Vitest setup.
- **Remediation:** Install `@testing-library/react` and Vitest; author automated unit tests for `NepaliDatePicker.tsx`, `offlineQueue.ts`, and financial formatting utilities (`toPaisa`, `fmtNpr`).
- **Requires Business Decision:** NO.
- **Safe to Implement Independently:** YES.
- **Estimated Effort:** 4–8 hours.

---

### DEF-06: Windows Execution Errors in PostgreSQL Embedded Test Harness
- **Category:** Technical Debt / CI Gap.
- **Severity:** **MEDIUM**.
- **Likelihood:** HIGH on Windows developer machines.
- **Business Impact:** Developers running the full backend test suite on Windows may see 41 setup errors if PostgreSQL tests are included without a live PostgreSQL database running.
- **Technical Impact:** `test_checkpoint_15_2_postgres.py` relies on `embedded-postgres` binary execution, which fails to bind sockets or initialize clusters on certain Windows host permissions.
- **Evidence:** Task log `task-13181.log` (41 setup errors).
- **Affected Modules:** `backend/tests/test_checkpoint_15_2_postgres.py`, `test_checkpoint_16_postgres.py`.
- **Root Cause:** Architectural dependency on embedded binary clusters rather than standard test database containers.
- **Remediation:** Add a pytest guard fixture: if `PG152_TEST_URL` is unset and the operating system is Windows, skip embedded postgres tests with a clear diagnostic message (`pytest.skip("PostgreSQL live URL not configured; skipping PG integration test")`).
- **Requires Business Decision:** NO.
- **Safe to Implement Independently:** YES.
- **Estimated Effort:** 1 hour.

---

### DEF-07: Deprecation Warnings Across Test Suites
- **Category:** Technical Debt.
- **Severity:** **LOW**.
- **Likelihood:** CERTAIN (357 warnings per run).
- **Business Impact:** Clutters test outputs; future Python/FastAPI upgrades will break if deprecated symbols are removed.
- **Technical Impact:**
  - `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
  - `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`
  - `PytestCollectionWarning: cannot collect test class 'Base' because it has a __init__ constructor.`
- **Evidence:** Pytest summary in `task-13956.log`.
- **Affected Modules:** `backend/tests/*`, `backend/app/api/v1/*`.
- **Remediation:** Replace `HTTP_422_UNPROCESSABLE_ENTITY` with `HTTP_422_UNPROCESSABLE_CONTENT`; set `__test__ = False` on SQLAlchemy `Base` in `test_tenant_repository.py`.
- **Requires Business Decision:** NO.
- **Safe to Implement Independently:** YES.
- **Estimated Effort:** 1–2 hours.

---

### DEF-08: Render Free-Tier Backend Container Sleep Delay
- **Category:** Usability / Operational Gap.
- **Severity:** **LOW**.
- **Likelihood:** HIGH during demonstrations.
- **Business Impact:** During a live client demo, the initial page load on `livo-footwear-erp.vercel.app` hangs for 45–60 seconds while the free Render backend spins up from sleep, giving an impression of slowness.
- **Technical Impact:** Render free web services spin down after 15 minutes of inactivity.
- **Evidence:** Documented in `docs/VERCEL_DEMO_FORENSIC_AUDIT.md` §1.2 ("DEF-04").
- **Remediation:** Upgrade Render service to Starter ($7/month) or migrate to a persistent VPS for live client demonstration.
- **Requires Business Decision:** YES (Hosting cost sign-off per BQ-08).
- **Estimated Effort:** 30 minutes.
