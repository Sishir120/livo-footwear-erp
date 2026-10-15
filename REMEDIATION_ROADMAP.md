# LIVO FOOTWEAR ERP — ENGINEERING REMEDIATION ROADMAP

**Document Version:** 1.0.0  
**Effective Date:** October 14, 2026  
**Auditor / Architect:** Independent Engineering Architecture & Security Team  
**Scope:** Remediation of Forensic Audit Findings, Client Gap Closure, and Production Release Preparation  
**Mode:** READ-ONLY SPECIFICATION (No application changes made in this pass)

---

## 1. ARCHITECTURAL OVERVIEW & DEPENDENCY GRAPH

The remediation plan is structured across five sequential phases (P0 to P4). Strict dependency order must be respected: security containment and database stability must precede authorization and business workflows, which in turn must precede UI completion and accounting decisions.

```mermaid
graph TD
    subgraph Phase P0: Security & Startup Containment
        P0_1[P0.1 Commit & Deploy Security Hardening] --> P0_2[P0.2 Re-verify Live Deployment Identity]
    end

    subgraph Phase P1: Core Authorization & Inventory Integrity
        P0_2 --> P1_1[P1.1 Branch-Level User Scoping & Anti-IDOR Dependency]
        P0_2 --> P1_2[P1.2 Batch-Level Sales Dispatch Traceability]
        P1_1 --> P1_3[P1.3 Multi-Branch Stock Transfer Engine & Receipt Confirmation]
    end

    subgraph Phase P2: Accounting Architecture & Missing Back-Office Workflows
        P1_3 --> P2_1[P2.1 Frontend UI for Fixed Assets, Expenses & Waste]
        P1_3 --> P2_2[P2.2 Client Accounting Alignment & General Ledger Decision]
        P2_2 --> P2_3[P2.3 Landed Cost Capitalization & Raw Material Valuation Rules]
    end

    subgraph Phase P3: Bilingual UX, In-App Guidance & Operational Reporting
        P2_1 --> P3_1[P3.1 Full Bilingual Nepali/English Localization Across All Views]
        P2_1 --> P3_2[P3.2 In-App Contextual Guidance & Searchable Manual]
        P2_1 --> P3_3[P3.3 Production Scrap & Waste Deduction Policy]
    end

    subgraph Phase P4: Production Hardening, CI/CD & Compliance
        P3_1 --> P4_1[P4.1 CI/CD Migration to Real PostgreSQL 16 Test Suite]
        P4_1 --> P4_2[P4.2 Automated Offsite Cloud Database Backup & Disaster Recovery Drill]
        P4_2 --> P4_3[P4.3 Nepal IRD CBMS E-Billing Regulatory Certification]
    end
```

---

## 2. PHASE P0: SECURITY CONTAINMENT & PREVENTING DATA LOSS

*Objective: Contain all critical vulnerabilities, eliminate credential exposure, and ensure application crashes safely on schema errors before any client demonstration.*

### Task P0.1: Commit & Deploy Pre-Release Security Hardening
- **Task Summary:** Commit the uncommitted working-tree security patches (SEC-01, SEC-02, SEC-03) that remove hardcoded demo accounts, prevent proxy IP spoofing, and enforce fail-fast database migrations.
- **Affected Files:**
  - `backend/app/config.py`
  - `backend/app/main.py`
  - `backend/app/middleware/rate_limit.py`
  - `backend/app/core/demo_seeding.py` (Untracked)
  - `backend/scripts/create_admin.py` (Untracked)
  - `frontend/src/app/login/page.tsx`
  - `README.md`
  - `render.yaml`, `.env.example`, `.env.staging.example`
- **Acceptance Criteria:**
  1. No plaintext passwords or preset credentials exist in `README.md` or any committed documentation.
  2. The frontend `/login` page renders zero preset persona buttons ("Admin Operator", "Auditor Viewer") and initializes with empty form inputs.
  3. `backend/app/main.py` fails startup (`raise RuntimeError`) immediately if `alembic upgrade head` encounters an error, rather than continuing with a warning.
  4. Automatic demo account seeding is strictly disabled by default (`ENABLE_DEMO_SEEDING=false`) and raises an alert if attempted in production.
  5. Initial administrator creation is executed via `python backend/scripts/create_admin.py` with Argon2/Bcrypt hashing.
  6. Rate limiting extracts client IP safely via RFC 7239 logic, ignoring unauthenticated `X-Forwarded-For` headers from non-trusted proxies.
- **Verification Tests:**
  - `pytest backend/tests/test_phase_16_2_security_remediations.py` (all tests passing).
  - Manual curl: Send 10 requests with spoofed `X-Forwarded-For: 1.2.3.4` from a single client; assert HTTP 429 Too Many Requests triggers.
- **Dependencies:** None.
- **Completion Condition:** Git commit created on `release/v1.0.0-staging`; push to GitHub; automatic Vercel and Render deployments succeed; live login page renders clean form.

### Task P0.2: Re-Verify Live Deployment Identity & Health Telemetry
- **Task Summary:** Verify that the live public endpoints on Render and Vercel are running the exact commit containing the P0.1 fixes.
- **Affected Files:**
  - `backend/app/api/v1/health.py`
- **Acceptance Criteria:**
  1. `GET /api/v1/health` and `GET /api/v1/health/ready` return `"commit": "<full_sha>"`.
  2. The reported commit SHA on Render matches the git commit from Task P0.1.
  3. The Vercel frontend bundle hash corresponds to the clean build.
- **Verification Tests:**
  - `curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health | grep commit`
- **Dependencies:** Task P0.1.
- **Completion Condition:** Live backend and frontend independently proven to run the hardened commit.

---

## 3. PHASE P1: CORE AUTHORIZATION, DATABASE RELIABILITY & INVENTORY INTEGRITY

*Objective: Enforce location-scoped multi-tenancy, eliminate intra-company IDOR, restore product batch pedigree, and establish the multi-branch stock transfer workflow.*

### Task P1.1: Branch-Level User Scoping & Anti-IDOR Authorization
- **Task Summary:** Scope non-admin users to specific factory warehouses/branches and enforce server-side validation on all location-specific routes.
- **Affected Files:**
  - `backend/app/models/user.py`
  - `backend/alembic/versions/021_add_user_branch_scoping.py` (New migration)
  - `backend/app/api/deps.py`
  - `backend/app/api/v1/stock.py`, `sales.py`, `production.py`, `hr.py`
- **Acceptance Criteria:**
  1. `users` table includes nullable `assigned_warehouse_id` (ForeignKey to `warehouses.id`). NULL indicates global corporate admin.
  2. JWT token claims include `assigned_warehouse_id`.
  3. Dependency `require_warehouse_access(target_warehouse_id)` verifies that `current_user.assigned_warehouse_id == target_warehouse_id` (unless `current_user.role == "admin"`).
  4. Endpoints `POST /api/v1/stock/movements`, `POST /api/v1/stock/adjustments`, `POST /api/v1/sales/orders/{id}/dispatch`, and `POST /api/v1/production/orders` reject unauthorized warehouse IDs with HTTP 403 Forbidden.
- **Verification Tests:**
  - Create test user assigned to Warehouse 1; attempt to dispatch stock from Warehouse 2; assert HTTP 403 Forbidden.
  - Global admin user attempts operation on Warehouse 2; assert HTTP 200 OK.
- **Dependencies:** Task P0.1.
- **Completion Condition:** All location-scoped API routes enforce branch ownership; dedicated IDOR test suite passing.

### Task P1.2: Batch-Level Sales Dispatch Traceability
- **Task Summary:** Link outgoing sales dispatches to specific manufacturing production batches to establish complete end-to-end footwear pedigree from raw materials to customer.
- **Affected Files:**
  - `backend/app/models/sales.py` (`SalesItem`)
  - `backend/app/models/stock.py` (`StockMovement`)
  - `backend/alembic/versions/022_add_batch_id_to_sales_and_movements.py` (New migration)
  - `backend/app/schemas/sales.py`
  - `backend/app/api/v1/sales.py` (`dispatch_sales_order`)
  - `frontend/src/components/SalesView.tsx` (Dispatch modal batch selector)
- **Acceptance Criteria:**
  1. `sales_items` and `stock_movements` include nullable `batch_id` (ForeignKey to `production_batches.id`).
  2. Dispatch payload schema accepts `batch_id` per item, or automatically selects active batches via FIFO when unassigned.
  3. Dispatch deducts physical stock specifically from the specified batch and records `batch_id` on the negative `StockMovement`.
  4. Printable invoice and customer dispatch notes display the batch number alongside the article code and size.
- **Verification Tests:**
  - Create Batch A (100 pairs) and Batch B (100 pairs); dispatch 50 pairs specifying Batch B; assert Batch B remaining stock is 50, Batch A remaining stock is 100, and invoice line references Batch B.
- **Dependencies:** Task P1.1.
- **Completion Condition:** Traceability query `GET /api/v1/analytics/traceability/{batch_number}` returns raw material PO -> production work order -> warehouse movement -> sales dispatch -> customer invoice.

### Task P1.3: Multi-Branch Stock Transfer Engine & Destination Confirmation
- **Task Summary:** Implement inter-branch stock transfers with an in-transit virtual holding state and mandatory physical confirmation by destination personnel.
- **Affected Files:**
  - `backend/app/models/stock.py` (`StockTransfer`, `StockTransferItem`)
  - `backend/alembic/versions/023_add_stock_transfers.py` (New migration)
  - `backend/app/api/v1/transfers.py` (New router)
  - `frontend/src/components/StockTransfersView.tsx` (New component)
  - `frontend/src/components/AppShell.tsx` (Navigation link)
- **Acceptance Criteria:**
  1. `StockTransfer` lifecycle states: `DRAFT` -> `DISPATCHED` (In-Transit) -> `RECEIVED` -> `DISCREPANCY_FLAGGED`.
  2. Initiating dispatch deducts inventory from Source Warehouse and places it in an `IN_TRANSIT` virtual location.
  3. Destination branch personnel must inspect and input actual received quantities:
     - Full receipt matches transfer: status `RECEIVED`, stock added to Destination Warehouse.
     - Partial receipt / transit damage: records discrepancy note, logs transit loss, updates stock only by verified received count.
  4. Source and Destination warehouse cannot be identical.
- **Verification Tests:**
  - Initiate transfer of 50 pairs from Factory WH to Pokhara Branch WH; verify Factory balance decreases by 50, Pokhara balance remains unchanged, and In-Transit balance is 50.
  - Destination user confirms receipt of 48 pairs (2 damaged); verify Pokhara balance increases by 48, 2 pairs logged as transit loss, transfer status marked `DISCREPANCY_FLAGGED`.
- **Dependencies:** Task P1.1.
- **Completion Condition:** Complete transfer workflow verified end-to-end via automated API and UI tests.

---

## 4. PHASE P2: ACCOUNTING ARCHITECTURE & MISSING BUSINESS WORKFLOWS

*Objective: Provide user interfaces for existing headless backend services and establish a definitive, reconciled accounting framework.*

### Task P2.1: Frontend UI for Fixed Assets, Factory Expenses & Waste Management
- **Task Summary:** Build Next.js App Router views and AppShell sidebar links to expose the existing backend APIs for `/assets`, `/expenses`, and `/waste`.
- **Affected Files:**
  - `frontend/src/components/FixedAssetsView.tsx` (New)
  - `frontend/src/components/FactoryExpensesView.tsx` (New)
  - `frontend/src/components/WasteManagementView.tsx` (New)
  - `frontend/src/components/AppShell.tsx`
  - `frontend/src/app/(dashboard)/assets/page.tsx` (New)
  - `frontend/src/app/(dashboard)/expenses/page.tsx` (New)
  - `frontend/src/app/(dashboard)/waste/page.tsx` (New)
- **Acceptance Criteria:**
  1. Fixed Assets view allows registering factory machinery, equipment cost, purchase date (BS/AD), and calculates monthly straight-line depreciation.
  2. Factory Expenses view allows logging operating costs (rent, electricity, generator fuel, maintenance, tea/canteen) categorized by department with cash/bank payment method.
  3. Waste Management view allows factory floor managers to record scrap leather (kg), rubber trim, and defective outsoles linked to production batches.
  4. AppShell navigation includes dedicated tabs with role-based visibility.
- **Verification Tests:**
  - Automated Playwright/Cypress UI tests navigating to `/assets`, `/expenses`, and `/waste`, creating sample records, and asserting correct table rendering and summary metrics.
- **Dependencies:** Task P0.1.
- **Completion Condition:** All three modules fully accessible and operational in the web application.

### Task P2.2: Client Accounting Scope Alignment & General Ledger Decision
- **Task Summary:** Formally align with client stakeholders on whether LIVO ERP requires an embedded double-entry General Ledger (GL) or an external accounting bridge (Tally / QuickBooks).
- **Execution Strategy:**
  - **Option A (Certified Subledger Model - Recommended):** Certify LIVO ERP as an *Operational Footwear Manufacturing ERP with Subledgers* (AR Ledger, Landed Costs, Tax Invoices, Payroll Advances) and implement an automated XML/JSON export bridge for Tally Prime.
  - **Option B (Full Embedded GL):** Design and implement Chart of Accounts, Journal Entries, Balanced Posting Rules, Trial Balance, P&L, and Balance Sheet in LIVO ERP.
- **Acceptance Criteria:**
  1. Written and signed Architecture Decision Record (ADR) from client executive stakeholders.
  2. If Option A: Tally Prime XML export endpoint implemented and verified against standard Nepal Tally chart of accounts.
  3. If Option B: Alembic migration creating `chart_of_accounts`, `journal_entries`, `journal_lines` with transactional posting triggers on purchase, production, and sales.
- **Verification Tests:**
  - Option A: Import generated XML into Tally Prime 4.0; assert vouchers balance perfectly.
  - Option B: Verify Trial Balance debit sum equals credit sum across 100 simulated operations.
- **Dependencies:** Task P0.1.
- **Completion Condition:** Client-approved accounting architecture in production.

### Task P2.3: Landed Cost Capitalization & Valuation Standards
- **Task Summary:** Reconcile raw material purchase landed costs (freight, customs, insurance) with inventory valuation and specify finished goods valuation method (Weighted Average Cost vs Standard Cost).
- **Affected Files:**
  - `backend/app/api/v1/purchase.py`
  - `backend/app/api/v1/reports.py`
  - `backend/app/models/purchase.py`
- **Acceptance Criteria:**
  1. Landed costs (freight, customs duty, insurance) allocated proportionately across received raw material lines.
  2. Inventory valuation report reflects capitalized landed costs rather than basic supplier invoice price.
  3. Finished goods stock report calculates valuation using BOM actual material cost + allocated piece-rate labor.
- **Verification Tests:**
  - Purchase 100 kg leather @ NPR 500/kg with NPR 10,000 freight; verify raw material valuation records unit cost as NPR 600/kg.
- **Dependencies:** Task P2.2.
- **Completion Condition:** Inventory valuation verified and reconciled with subledger entries.

---

## 5. PHASE P3: BILINGUAL UX, IN-APP GUIDANCE & OPERATIONAL REPORTING

*Objective: Deliver a Nepal-first user experience with complete English/Nepali localization, embedded contextual help, and refined floor reporting.*

### Task P3.1: Complete Bilingual UI Localization
- **Task Summary:** Translate all user interface strings, form labels, tooltips, validation messages, and server error messages into natural Nepali (Devanagari script) with instant English/Nepali toggle.
- **Affected Files:**
  - `frontend/src/context/LocaleContext.tsx`
  - `frontend/src/locales/ne.json`, `en.json`
  - All form components in `frontend/src/components/`
- **Acceptance Criteria:**
  1. Zero hardcoded English strings in operational forms, tables, and modal headers.
  2. Number displays format cleanly in Nepali format (Lakhs / Crores: `12,34,567.00`).
  3. Bikram Sambat dates format in Nepali Devanagari numerals upon locale selection.
- **Verification Tests:**
  - Switch language to Nepali; verify all navigation tabs, button text, table headers, and error toasts render in fluent Nepali.
- **Dependencies:** Task P2.1.
- **Completion Condition:** Full UI localization audited and accepted by native Nepali operator.

### Task P3.2: In-App Contextual Help & Searchable User Manual
- **Task Summary:** Embed interactive contextual help tooltips on complex manufacturing fields and provide a searchable, bilingual operations manual directly inside the AppShell.
- **Affected Files:**
  - `frontend/src/components/HelpTooltip.tsx` (New)
  - `frontend/src/components/HelpManualModal.tsx` (New)
  - `docs/user-guide/OPERATIONS_MANUAL_NE.md`, `OPERATIONS_MANUAL_EN.md`
- **Acceptance Criteria:**
  1. Every major input field (e.g. Landed Cost Distribution, Piece-Rate Operation Code, BS Date Range) has a clickable help icon explaining footwear manufacturing best practices.
  2. AppShell header includes a "Help / सहायता" button opening a searchable manual covering: Inwarding, Cutting & Stitching, Lasting, Dispatch, and Party Reconciliation.
- **Verification Tests:**
  - Search manual for "चालानी" (Dispatch); assert returns dispatch step-by-step instructions.
- **Dependencies:** Task P3.1.
- **Completion Condition:** Searchable manual fully operational in frontend.

### Task P3.3: Production Scrap & Waste Deduction Policy
- **Task Summary:** Enforce clear business rules on whether logged factory scrap/waste deducts raw material inventory, work-in-progress, or records as non-inventoried floor loss.
- **Affected Files:**
  - `backend/app/api/v1/waste.py`
  - `backend/app/models/waste.py`
- **Acceptance Criteria:**
  1. Logging defective/scrap material creates a corresponding `StockMovement` (-1 direction, `movement_type='WASTE_SCRAP'`) if linked to raw materials.
  2. Scrap recovery sales (selling scrap rubber or leather trimmings to recycling buyers) records recovery revenue in operational subledger.
- **Verification Tests:**
  - Record 15 kg leather scrap from Batch 101; assert raw material leather stock decreases by 15 kg with reason `WASTE_SCRAP`.
- **Dependencies:** Task P2.1.
- **Completion Condition:** Scrap accounting rules verified in automated test suite.

---

## 6. PHASE P4: PRODUCTION HARDENING, CI/CD & REGULATORY COMPLIANCE

*Objective: Implement enterprise-grade reliability, PostgreSQL concurrency verification, automated disaster recovery, and statutory tax compliance.*

### Task P4.1: CI/CD Migration to Real PostgreSQL 16 Test Suite
- **Task Summary:** Configure GitHub Actions to execute the complete automated test suite against a dedicated PostgreSQL 16 service container instead of SQLite.
- **Affected Files:**
  - `.github/workflows/backend_test.yml` (New or updated)
  - `backend/tests/conftest.py`
- **Acceptance Criteria:**
  1. CI pipeline spins up `postgres:16-alpine`.
  2. Runs `alembic upgrade head` cleanly against PostgreSQL.
  3. All 375+ tests pass with zero errors.
  4. Real PostgreSQL advisory locks (`(company_id << 32) | product_id`) and `FOR UPDATE` sequence locks execute under 50 concurrent simulated worker threads without deadlock.
- **Verification Tests:**
  - Parallel test run with 50 threads dispatching inventory from a single product; assert zero negative stock and zero lock acquisition timeouts.
- **Dependencies:** Task P0.1.
- **Completion Condition:** GitHub Actions workflow green on pull requests against PostgreSQL.

### Task P4.2: Automated Offsite Cloud Database Backups & Restoration Drill
- **Task Summary:** Operationalize daily automated database backups with encryption, offsite replication (AWS S3 / Cloudflare R2), and automated restoration drills.
- **Affected Files:**
  - `.github/workflows/scheduled_backup.yml`
  - `scripts/cloud_backup.sh`
  - `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`
- **Acceptance Criteria:**
  1. Nightly cron executes `pg_dump` with gzip compression and SHA-256 checksum generation.
  2. Backup archive uploaded to private, lifecycle-managed S3 bucket (30-day retention).
  3. Weekly automated test restores the latest backup into an isolated container and validates table row counts.
  4. Failure notifications sent via webhook (Slack / Discord / Email).
- **Verification Tests:**
  - Trigger backup manually; download artifact; restore into fresh PostgreSQL instance; assert all tables and records match live counts.
- **Dependencies:** Task P0.1.
- **Completion Condition:** Automated backup verified with documented restoration drill evidence.

### Task P4.3: Nepal Inland Revenue Department (IRD) CBMS Certification
- **Task Summary:** Prepare tax invoicing module for legal compliance with Nepal IRD Central Billing Monitoring System (CBMS) real-time API.
- **Affected Files:**
  - `backend/app/api/v1/invoices.py`
  - `backend/app/models/invoice.py`
  - `backend/app/services/cbms_service.py` (New)
- **Acceptance Criteria:**
  1. Generates IRD-compliant fiscal invoice structure (Seller PAN, Buyer PAN, Taxable Amount, 13% VAT, Fiscal Year, Bill Date in BS).
  2. Real-time JSON payload transmission to IRD CBMS API with retry queue for offline network resilience.
  3. Stores IRD synchronization status and approval code on each invoice.
- **Verification Tests:**
  - Test sandbox transmission to IRD test endpoint; assert 200 OK receipt and valid fiscal verification response.
- **Dependencies:** Task P2.2.
- **Completion Condition:** IRD CBMS integration certified or staged for tax auditor review.

---

## 7. MILESTONE GATES & ACCEPTANCE CRITERIA

| Milestone | Target State | Mandatory Evidence Required to Open Gate |
| :--- | :--- | :--- |
| **Gate 0: Security Gate** | Secure Sandbox Deployment | Clean commit of P0 fixes; Vercel & Render redeployed; zero default credentials in docs or UI; rate limit verified. |
| **Gate 1: Client Demo Gate** | Supervised Client Walkthrough | Gate 0 passed; synthetic data loaded; BS date picker working; core procurement -> manufacturing -> dispatch demonstrated. |
| **Gate 2: Branch Trial Gate** | Single Factory / Branch Pilot | Phase P1 completed (anti-IDOR branch scoping, batch dispatch, stock transfers); zero cross-branch tampering possible. |
| **Gate 3: Production Release Gate** | Live Company Operations | Phases P2, P3, P4 completed; real PostgreSQL CI passing; offsite backups verified; client accounting decision executed. |
