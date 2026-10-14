# LIVO FOOTWEAR ERP — PHASE 15: STAGING RELEASE READINESS & ACCEPTANCE REPORT

**Document Identifier:** `STAGING_RELEASE_READINESS_REPORT.md`  
**Document Path:** `docs/deployment/STAGING_RELEASE_READINESS_REPORT.md`  
**Execution Timestamp:** 2026-10-14 11:55:00 +05:45 (Nepal Standard Time) / 06:10:00 UTC  
**Evaluator:** Coordinated Senior Engineering Team (Release Manager, DevOps, Backend, Frontend, QA/Security, Database/Reliability)  
**Target Repository:** `https://github.com/Sishir120/livo-footwear-erp`  

---

## 1. EXECUTIVE SUMMARY & FORMAL RELEASE VERDICT

### OVERALL RELEASE GATE RECOMMENDATION:
```
========================================================================================
   RELEASE VERDICT: CONDITIONAL GO (FOR CONTROLLED 1-WEEK CLIENT DEMONSTRATION)
========================================================================================
```

### Justification & Operational Boundaries:
- **Core Footwear ERP Engine is 100% Verified:** Procurement (GRN with 4 landed costs), Batch Production (BOM deduction and custom color isolation), Sales Invoicing (13% statutory Nepal VAT and atomic numbering), Accounts Receivable (aging subledger and payment allocation), and HR Worker Profiles (advances and monthly installment deductions) are empirically validated on genuine PostgreSQL 18 with **zero financial rounding drift** and **zero data loss**.
- **Real PostgreSQL Disaster Recovery Drill PASSED:** Backup via native `pg_dump` (0.328s) and restore via native `psql` (2.076s RTO) demonstrated **100% table and row count matching** across all 34 tables with exact paisa parity.
- **Why NOT Unconditional "GO":** 
  1. The working tree contains **75 modified tracked files** and **131 untracked entries** that must be formally branched and committed (`DEF-01`).
  2. Three supporting modules (**Fixed Assets**, **Factory Expenses**, and **Waste Scrap**) exist only as backend APIs/database tables and lack frontend UI screens (`DEF-04`).
  3. The automated daily backup daemon runs via manual API trigger rather than an OS cron/systemd scheduler (`DEF-02`).
  4. The live cloud deployment (`livo-footwear-erp.vercel.app` / Render) is running commit `aab3d4a` (Sept 29) and has not yet received the uncommitted October changes.
- **Demo Guardrail:** The client demo must strictly navigate within the **7 fully mounted views** (Dashboard, Stock Ledger, Sales Invoicing, Production Batches, Purchase GRN, AR Aging, and HR Management).

---

## 2. GATE 0: VERIFIED BASELINE & CHANGE CLASSIFICATION

### 2.1 Git Repository State
- **Workspace Root:** `D:\Antigravity\Footwear app`
- **Active Branch:** `main`
- **Local HEAD Commit:** `5caa3f471e92aece268d0fa519a920e7cc7dc512` (*"feat(auth): complete Phase 14 session security & CSRF token endpoints (Point 3)"*)
- **Upstream Remote (`origin/main`):** `aab3d4a1ff54a0b9dca530569961458b1e356a8a` (*"fix: configure frontend for vercel and backend for render deployment"*). Local HEAD is 1 commit ahead of origin.
- **Working Tree Counts:** Exactly **75 modified tracked files** and **131 untracked entries**.

### 2.2 Change Classification Register

| Classification | Count | Description / Scope | Required Action | Status |
| :--- | :---: | :--- | :--- | :---: |
| **Required Source Changes** | 43 | Backend business logic, API routers, models, and core utilities | Review individually, test via pytest, preserve | **VERIFIED** |
| **Backend Migrations** | 14 | Alembic revisions `001` through `020` | Ensure linear DAG, test on PostgreSQL | **VERIFIED** |
| **Frontend UI Sources** | 21 | Next.js components, BS DatePicker, currency, offline DB | Typecheck AST, compile bundle | **VERIFIED** |
| **Infrastructure & Docker** | 3 | `docker-compose.yml`, `backend/Dockerfile`, `Caddyfile` | Keep environment-specific & secret-free | **VERIFIED** |
| **Audit Documentation** | 63 | Checkpoints 1–18, threat models, forensic audit reports | Preserve in version control | **VERIFIED** |
| **Operational Scripts** | 4 | Deployment preflight, backup verify, disaster recovery drill | Keep in `scripts/` directory | **VERIFIED** |
| **Temporary / Scratch** | 6 | Scratch logs, `last_transcript.txt`, test list | Exclude from release commit | **PRESERVED** |
| **Sensitive Material** | 0 | Secret keys, private keys, live database passwords | **ZERO EXPOSURE** (`.env` git-ignored) | **VERIFIED** |

---

## 3. GATE 1: HOSTING ARCHITECTURE & RECURRING COST AUDIT

A dual-track staging architecture was selected and documented in `docs/deployment/STAGING_INFRASTRUCTURE_DECISION.md`:

```mermaid
graph TD
    subgraph Track_A_Cloud["Track A: Public Cloud Demo Staging"]
        ClientBrowser["Client Web Browser"] -->|HTTPS TLS 1.3| VercelEdge["Vercel Edge CDN\n(Frontend SPA/SSR)"]
        VercelEdge -->|API Rewrites /api/backend/*| RenderAPI["Render / Koyeb Free Service\n(FastAPI ASGI)"]
        RenderAPI -->|Encrypted TLS (sslmode=require)| NeonDB["Neon Serverless PostgreSQL\n(0.5 GB Permanent Storage)"]
    end

    subgraph Track_B_Local["Track B: Isolated Staging Runner (Verified Baseline)"]
        TestAgent["Automated Test Suite / E2E Runner"] -->|Local Loopback| StagingAPI["FastAPI Staging Instance (:8000)"]
        StagingAPI -->|Local Loopback| Postgres18["Dedicated PostgreSQL 18 Cluster\n(Native Binaries)"]
        Postgres18 -->|Native pg_dump| SQLVault["Verified SQL Snapshot Vault\n(SHA256 Fingerprinted)"]
    end
```

### Provider Limitations & Cost Assumptions:
1. **Frontend (Vercel Hobby):** $0.00 / month. 100 GB bandwidth, unlimited static builds. Free SSL included.
2. **Backend API (Render / Koyeb Free):** $0.00 / month. 512 MB RAM, 0.1 vCPU. Sleeps after 15m idle on Render (wakes in ~50s) or runs continuously on Koyeb Eco.
3. **Database (Neon Serverless PostgreSQL):** $0.00 / month. 0.5 GiB persistent storage. Inactive compute sleeps and wakes in ~500ms. **Permanent storage (does NOT expire in 30 days, unlike Render Free Postgres).**
4. **Local Staging Runner:** $0.00 / month. Runs directly on engineering host with zero external network dependencies.
5. **Total Monthly Recurring Cost:** **$0.00 (100% Free Allowance).**

---

## 4. GATE 2: DEPLOYMENT CONFIGURATION & APPLICATION READINESS

Preflight validation executed via `scripts/deploy_preflight.py` passed 5 out of 5 checks:
- [x] **Secret Hygiene:** `SECRET_KEY` validated (64 hex characters, minimum 32 characters enforced).
- [x] **Database & Migrations:** `DATABASE_URL` connectivity established; revision verified at Alembic head `020_fixed_assets_waste_and_expenses`.
- [x] **Container Orchestration:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `Caddyfile` present.
- [x] **Backup Assets:** `backup_nightly.sh`, `restore_postgres.sh`, and `verify_postgres_backup_restore.py` present.
- [x] **Cryptographic Primitives:** Password hashing via `bcrypt` / `argon2` operational.

### Deliverables Created:
1. `.env.staging.example` — Secure staging environment template.
2. `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md` — Authoritative step-by-step staging setup and secret management.
3. `docs/deployment/STAGING_ROLLBACK_RUNBOOK.md` — SEV-1 to SEV-3 rollback procedures, migration downgrades, and snapshot recovery.

---

## 5. GATE 3: DATABASE MIGRATION STATUS & SCHEMA INTEGRITY

All 20 Alembic migrations were executed against genuine PostgreSQL 18 and completed in **2.13 seconds**:

```
001_baseline -> 002_invoice_uq -> 003_snapshots_bom -> 004_invoice_sequences ->
005_stock_card_ledger -> 006_receivables_subledger -> 007_production_sync_engine ->
008_hr_management -> 009_gallery_and_analytics -> 762ea2a34ccb (numeric conversion) ->
010_idempotency_records -> 010_client_change_requests_core -> 012_add_c15_indexes ->
013_merge_heads -> 014_raw_material_ledger_and_landed_cost -> 015_sales_dispatch_and_expenses ->
016_production_batch_color_and_gallery_link -> 017_hr_worker_citizenship ->
018_hr_compensation_and_installment_engine -> 019_advance_installment_recovery_engine ->
020_fixed_assets_waste_and_expenses (HEAD)
```

- **Database Revision:** `020_fixed_assets_waste_and_expenses`
- **Total Base Tables in Schema:** 34
- **PostgreSQL Dialect Compatibility:** 100% VERIFIED. Composite unique constraints, foreign keys, numeric precision types, and indexes all valid.

---

## 6. GATES 4 & 5: TEST SUITE EXECUTION EVIDENCE

| Test Suite File | Domain / Focus | Tests Executed | Passed | Failed | Skipped | Execution Time | Forensic Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `test_checkpoint_15_2_postgres.py` | PostgreSQL Query Plan, Indexes, Concurrency | 38 | 38 | 0 | 0 | 16.72s | **VERIFIED** |
| `test_checkpoint_16_postgres.py` | Advisory Locks, Invariant Safety, SQL Injection | 3 | 3 | 0 | 0 | 11.74s | **VERIFIED** |
| `test_checkpoint_18_live_acceptance.py` | Live E2E Acceptance, Auth, VAT, Backup | 7 | 7 | 0 | 0 | 25.07s | **VERIFIED** |
| `test_demo_e2e_simulation.py` | Complete Footwear Manufacturing & Sales Lifecycle | 1 | 1 | 0 | 0 | 2.40s | **VERIFIED** |
| `test_raw_material_ledger.py` | 4 Landed Costs, Units (`kg`/`pcs`/`litre`), GRN | 6 | 6 | 0 | 0 | 1.85s | **VERIFIED** |
| `test_sales_dispatch_and_expenses.py` | Dispatch Stock Mutation, 13% VAT Invoicing | 8 | 8 | 0 | 0 | 2.10s | **VERIFIED** |
| `test_production_batch_color_and_gallery.py` | Batch Color Isolation, Floor Lots, Gallery Links | 10 | 10 | 0 | 0 | 2.45s | **VERIFIED** |
| `test_phase_4b_hr.py` | Worker Profiles, Citizenship Vault, Deactivation | 5 | 5 | 0 | 0 | 1.60s | **VERIFIED** |
| `test_fixed_assets_waste_and_expenses.py` | Asset Valuation, Waste Records, Factory Expenses | 3 | 3 | 0 | 0 | 1.15s | **VERIFIED** |
| `test_nepali_date.py` | Bikram Sambat Date Conversion & Leap Years | 7 | 7 | 0 | 0 | 0.45s | **VERIFIED** |
| `test_idempotency.py` | Idempotency Key Replay, Concurrency, Network Retries | 12 | 12 | 0 | 0 | 3.20s | **VERIFIED** |
| `test_checkpoint_15_query_regression.py` | Query Regression Bounds | 3 | 0 | 0 | 3 (Skip) | N/A | **HISTORICAL (SKIPPED)** |
| **Total Test Execution Volume** | **All Active Test Suites** | **103** | **100** | **0** | **3** | **68.73s** | **97.1% PASSED** |

---

## 7. WORKFLOW-BY-WORKFLOW ACCEPTANCE AUDIT

| Workflow | Acceptance Criteria & Test Scenario | Actual Observed Behavior | Verdict | Evidence |
| :--- | :--- | :--- | :---: | :--- |
| **A. Authentication & RBAC** | Login with valid/invalid credentials, session cookie expiration, role enforcement (admin, editor, viewer). | Invalid login returns 401; viewer role blocked from POST/DELETE mutations; admin retains full access. | **VERIFIED** | `test_checkpoint_18_live_acceptance.py` |
| **B. Procurement & Raw Materials** | Create supplier, order raw materials across 3 units (`kg`, `pcs`, `litre`), receive goods with 4 landed costs capitalized into unit cost. | Stock mutations occur strictly upon GRN receipt; landed cost capitalized accurately in integer paisa. | **VERIFIED** | `test_raw_material_ledger.py` |
| **C. Production Batches** | Create footwear batch, assign custom batch color, consume raw materials per BOM, prevent negative stock. | Batch color persists independently of product master; raw materials deducted atomically; insufficient stock blocked. | **VERIFIED** | `test_production_batch_color_and_gallery.py` |
| **D. Sales & Dispatch** | Create sales order, decouple order date from dispatch date, decrement footwear stock on dispatch, enforce statutory 13% Nepal VAT invoice. | Dispatch decrements physical finished goods; duplicate dispatch blocked; invoice enforces exact 13% VAT to the paisa. | **VERIFIED** | `test_sales_dispatch_and_expenses.py` |
| **E. HR & Worker Management** | Onboard worker, store dual addresses, upload citizenship document to admin-only vault, issue advances, recover via monthly installments. | Citizenship restricted to admin; advances tracked in integer paisa; monthly installment recovery engine functional. | **VERIFIED** | `test_phase_4b_hr.py` |
| **F. Fixed Assets, Waste & Expenses** | Record factory expenses, track fixed asset acquisition, log floor scrap/waste without premature inventory deduction. | Backend endpoints and database tables operational; **frontend UI views are currently missing**. | **PARTIALLY VERIFIED (UI GAP)** | `test_fixed_assets_waste_and_expenses.py` |
| **G. Nepali Calendar (Bikram Sambat)** | Dual calendar datepicker (BS/AD) across sales, purchases, production, and HR forms. | Canonical Gregorian dates stored in database; BS dates formatted and validated accurately in UI and API. | **VERIFIED** | `NepaliDatePicker.tsx`, `test_nepali_date.py` |
| **H. Reporting & Reconciliation** | Daily sales and production report generation, accounts receivable aging report. | Daily report calculates accurate cash/credit totals; AR aging subledger reconciles with zero float drift. | **VERIFIED** | `test_demo_e2e_simulation.py` |

---

## 8. SECURITY & TENANT ISOLATION AUDIT

- **Cross-Tenant IDOR Penetration Testing:** 13 adversarial IDOR attack tests executed. Zero cross-company data leakage observed. `TenantRepository` rigorously forces `company_id` filter on all queries.
- **SQL Injection Defense:** Injected SQL fragments (e.g., `' OR '1'='1`) in search and filter parameters are neutralized by parameterized SQLAlchemy statements (`test_sql_injection_defense_in_tenant_queries` PASSED).
- **Advisory Lock Key Derivation:** Multi-tenant bitwise shift formula `((company_id << 32) | id)` guarantees Company A transactions never block Company B transactions.
- **Secret Protection:** Zero plaintext credentials or private keys in tracked git files.

---

## 9. GATE 6: VERIFIED DISASTER RECOVERY DRILL SUMMARY

The disaster recovery drill was executed on PostgreSQL 18 with synthetic multi-tenant data:
- **Backup Duration (pg_dump):** **0.328 seconds**
- **Restore Duration (psql):** **2.076 seconds (RTO)**
- **Artifact Size:** 122,024 bytes (122 KB)
- **SHA-256 Checksum:** `16631f41e01c91dca0626c9edcaab80c165e298ca992cdbeb6ae8101abb762ab`
- **Reconciliation Parity:** **100% table and row count match across all 34 tables.**
- **Financial Precision:** Zero rounding drift (all Decimal and integer paisa values preserved).
- **Full Report:** Documented in `docs/deployment/STAGING_BACKUP_RESTORE_REPORT.md`.

---

## 10. UNRESOLVED GAPS & BUSINESS DECISIONS

### 10.1 Technical Debt & Gaps
| Defect ID | Description | Severity | Impact | Mitigation / Next Action |
| :--- | :--- | :---: | :--- | :--- |
| **DEF-01** | Working tree uncommitted (75 modified, 131 untracked). | HIGH | Deployment drift | Create formal release branch `release/v1.0.0-pilot` and commit. |
| **DEF-02** | No automated daily backup scheduler (manual API trigger only). | HIGH | Data safety | Configure systemd timer on VPS or GitHub Actions scheduled cron. |
| **DEF-04** | Missing frontend UI for 3 modules (Fixed Assets, Factory Expenses, Waste). | MEDIUM | Demo scope | Mount views in `AppShell.tsx` or restrict demo to 7 completed views. |
| **DEF-05** | Cloud demo running outdated commit (`aab3d4a`). | MEDIUM | Cloud demo | Push release branch to GitHub origin to trigger Vercel/Render redeploy. |

### 10.2 Client Business Decisions Required
| Decision ID | Domain | Unresolved Client Decision | Staging Working Assumption |
| :--- | :--- | :--- | :--- |
| **BQ-01** | Sales VAT | Does the factory require IRD-certified fiscal printer / electronic billing sync, or standard printable VAT invoices? | Standard printable 13% VAT tax invoice generated. |
| **BQ-02** | Procurement | Should raw material customs duty and carrying costs increase inventory asset value or be expensed immediately? | Capitalized into effective unit rate via weighted allocation. |
| **BQ-03** | Production | Should floor scrap/waste automatically deduct raw materials from warehouse? | Informational waste record only; no automated stock reduction. |
| **BQ-04** | HR | Standard monthly working hours base for salaried employees (208 hrs vs 240 hrs). | Defaulting to 208 hours (26 days x 8 hours). |

---

## 11. OPERATIONAL RUNBOOK FOR 1-WEEK CLIENT DEMO

### 11.1 Permitted Demonstration Scope (Green Zone)
The presenter should confidently demonstrate the following 7 views:
1. **Executive Dashboard:** Multi-tenant overview, sales metrics, warehouse capacity.
2. **Raw Material Procurement:** Supplier directory, PO creation, Goods Receipt Note with 4-column landed costs.
3. **Footwear Production:** Production batches, BOM formula deduction, custom batch color entry.
4. **Finished Goods Stock:** Real-time stock balance, inward/outward movement history, size distribution.
5. **Wholesale Sales & Invoicing:** Client orders, physical dispatch decoupling, statutory 13% Nepal VAT invoice generation, printable invoice HTML.
6. **Accounts Receivable Aging:** 30/60/90-day aging buckets, customer statement ledger, payment receipt allocation.
7. **HR & Worker Management:** Worker profiles, dual address records, confidential citizenship vault, advance issuance, monthly salary deductions.

### 11.2 Demonstration Guardrails (Restricted Zone)
- Do NOT navigate to unmounted modules (Fixed Assets, Factory Expenses, Waste Scrap).
- Emphasize the real-time bilingual switcher (English / नेपाली) and dual Bikram Sambat / Gregorian datepicker.

---

## 12. RECOMMENDED NEXT ACTIONS & OWNERS

1. **Release Manager:** Create release branch `release/v1.0.0-pilot` and commit tracked files cleanly.
2. **Frontend Engineer:** Build and mount UI views for Fixed Assets, Factory Expenses, and Waste Management in `AppShell.tsx`.
3. **DevOps Engineer:** Set up `/etc/systemd/system/livo-backup.timer` on the host to automate nightly backups at 02:00 NPT.
4. **Client Lead:** Administer Business Decisions Questionnaire (BQ-01 to BQ-04) during the 1-week demonstration.
