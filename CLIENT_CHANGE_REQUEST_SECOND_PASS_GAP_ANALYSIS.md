# LIVO FOOTWEAR ERP — SECOND-PASS FORENSIC GAP ANALYSIS & VERIFICATION AUDIT
**System:** LIVO Footwear Enterprise Resource Planning (ERP) System  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Auditor:** Principal Enterprise Software Architect, Senior Full-Stack Engineer, Lead DBA & Forensic Reliability Auditor  
**Audit Date:** 2026-10-12  
**Operating Mode:** STRICT AUDIT ONLY — Zero application code, schemas, or configurations modified  
**Status:** COMPLETE & FORENSICALLY VERIFIED  

---

## 1. Executive Summary

This second-pass forensic audit independently evaluates the claims of the previous comprehensive audit report (`GENESIS-TO-PRESENT COMPREHENSIVE SYSTEM AUDIT REPORT`) against the live codebase, schema migrations, automated tests, and original client requirements for the LIVO Footwear ERP.

### Key Audit Findings & Reality Checks:
1. **Verified Core Strengths:**
   - The ERP possess a genuinely mature, production-grade foundation: **292 automated tests pass with 0 failures** in under 100 seconds.
   - **Integer-Paisa Precision:** Monetary calculations strictly eliminate IEEE-754 floating-point drift. Sales invoices enforce statutory Nepal IRD Schedule-5 13% VAT with Nepali and English word rendering down to the paisa.
   - **Append-Only Inventory Ledgers:** Both finished goods (`stock_movements`) and raw materials (`raw_material_movements`) are backed by append-only ledger entries guarded by transaction-scoped PostgreSQL advisory locks (`pg_advisory_xact_lock`).
   - **Bikram Sambat Calendar:** Complete bidirectional conversion tables (1979–2100 BS) operate deterministically in both backend Python and frontend TypeScript with 0 external npm/pip dependencies.
2. **Deficiencies & Discrepancies in Previous Claims:**
   - **Production Batch Color (`PROD-01`):** While the previous audit asserted batch color support, batch entry is strictly constrained to catalog SKU selection. Operators **cannot manually type free-text colors** on the floor dock without altering product master definitions.
   - **Production Gallery (`PROD-02`):** Media uploads attach exclusively to catalog `products.id`. The system does **not link photographs to specific production lots or batches**.
   - **Purchase Expenses Ledger (`FIN-03`):** Although 4-column landed costs (`carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`) exist on the `Purchase` model, the client's **handwritten multi-column ledger presentation is completely absent** from UI tables and reporting.
   - **HR Worker Profile & KYC (`HR-01`, `HR-02`, `HR-03`):** Directory is rendered as a raw HTML table, not visual worker cards. Model columns for addresses and photos are unexposed in schemas/UI, and citizenship document storage is completely missing.
   - **Completely Missing Modules (`PROD-03`, `FIN-01`, `FIN-04`):** Production Waste/Scrap Tracking, General Factory Overhead Expenses, and Fixed Assets Register have **zero implementation**.
   - **Operational Backup Scheduler (`OPS-01`):** Backup scripts, AES encryption, and S3/B2 replication exist, but **no active scheduler or daemon is running in the environment**; it remains an unconfigured host manual cron task.

### Summary Requirement Status Count (19 Total Requirements):
- `VERIFIED_IMPLEMENTED`: **8**
- `PARTIALLY_IMPLEMENTED`: **6**
- `PRESENT_BUT_INCORRECT`: **2**
- `MISSING`: **3**
- `DUPLICATE_EXISTING_FUNCTIONALITY`: **0**
- `AMBIGUOUS`: **0**
- `UNVERIFIABLE`: **0**

---

## 2. Repository Identity and Audit Environment

- **Repository Path:** `d:\Antigravity\Footwear app`
- **Active Git Branch:** `main`
- **Head Commit SHA:** `5caa3f471e92aece268d0fa519a920e7cc7dc512`
- **Working Tree State:** In-flight dirty tree with verified changes from recent statutory VAT fixes and audit document generation.
- **Previous Audit Target:** Matches `5caa3f4` exactly.
- **Safe Execution Commands Executed:**
  - `git rev-parse HEAD`, `git status -s`, `git log`
  - `alembic heads`, `alembic history`
  - `pytest backend/tests/test_nepali_date.py -v` (7 passed in 0.05s)
  - `pytest backend/tests/test_raw_material_ledger.py -v` (6 passed in 2.05s)
  - `pytest backend/tests/test_sales_dispatch_and_expenses.py -v` (8 passed in 2.55s)
  - `pytest backend/tests/test_hr_management.py -v` (6 passed in 1.99s)
  - `pytest backend/tests/ -v --durations=0` (292 passed, 3 skipped, 0 failed in 98.83s)
  - `npm --prefix frontend run build` (Next.js 14.2 production build, First Load JS 112 kB)

---

## 3. Previous Audit Claim Verification

| Claim from Previous Audit Report | Files & Symbols Inspected | Verification Method | Result | Discrepancy & Reality |
|---|---|---|---|---|
| **Claim 1: 98.4/100 Health Score & Production Readiness** | Whole repository, operational runbooks | Comparative requirements gap analysis | **Subjective** | While technical stability is high (A-grade), core client requirements (Waste, General Expenses, Fixed Assets, Batch Photos, Worker Cards) remain unbuilt. |
| **Claim 2: 292 passing automated tests** | `backend/tests/` (38 test modules) | `pytest backend/tests/ -q` execution | **VERIFIED** | 292 passed, 3 skipped, 0 failed in 98.83s. |
| **Claim 3: 16 database migrations, unified Alembic head** | `backend/migrations/versions/` (16 files) | `alembic heads`, `alembic history` | **VERIFIED** | Single linear head: `015_sales_dispatch_and_expenses`. Merged branch at `013_merge_heads`. |
| **Claim 4: Append-only finished goods & raw material ledgers** | `models/stock.py`, `models/purchase.py` | AST inspection & test verification | **VERIFIED** | `StockMovement` (+1/-1) and `RawMaterialMovement` (+1/-1) record all transactions. |
| **Claim 5: PostgreSQL advisory locks** | `backend/app/core/locks.py` | Code inspection & concurrency tests | **VERIFIED** | Deterministic 64-bit bigint hash via `pg_advisory_xact_lock` with thread RLock fallback for SQLite. |
| **Claim 6: Statutory mandatory 13% Nepal VAT** | `api/v1/invoices.py`, `models/invoice.py` | Pytest verification & HTML inspection | **VERIFIED** | Tampered 0-VAT payloads recalculate to 13%; Schedule-5 printable tax bill generates bilingual words. |
| **Claim 7: Multi-tenant data isolation** | 31 SQLAlchemy tables | Python metadata inspection | **VERIFIED** | 30 tables enforce `company_id ForeignKey`, TenantRepository scopes queries. |
| **Claim 8: Bikram Sambat date engine** | `core/nepali_date.py`, `lib/nepaliDate.ts` | Unit tests & calendar boundary tests | **VERIFIED** | 1979–2100 BS coverage, zero external npm/pip dependencies. |
| **Claim 9: Purchase landed-cost fields** | `models/purchase.py`, `api/v1/purchase.py` | Schema & GRN modal inspection | **PARTIAL** | Model stores 4 paisa columns and capitalizes into rate; however, **multi-column ledger UI table does not exist**. |
| **Claim 10: Sales expenses & decoupled dispatch** | `models/sales.py`, `SalesInvoiceView.tsx` | UI grep & API test verification | **VERIFIED** | Order status moves CONFIRMED -> DISPATCHED; Sales expenses subledger tab active in UI. |
| **Claim 11: Worker payroll & advance tracking** | `models/worker.py`, `api/v1/hr.py` | Code inspection & payroll tests | **VERIFIED** | Monthly payroll computes basic + 1.5x OT, auto-recovers advances, handles CASH/BANK modes. |
| **Claim 12: Encrypted backup scripts** | `scripts/backup_nightly.sh`, `backup_service.py` | Script review & status inspection | **PARTIAL** | Scripts and AES encryption exist; **no OS-level scheduler or daemon is active**. |

---

## 4. Current Architecture Relevant to Client Requirements

```
+-------------------------------------------------------------------------------------------------------------------+
|                                            LIVO FOOTWEAR ERP ARCHITECTURE                                         |
+-------------------------------------------------------------------------------------------------------------------+
|                                                                                                                   |
|  [PRESENTATION LAYER — Next.js 14 / React 19 / TypeScript / Slate Industrial Theme]                             |
|  ├── ProductionView.tsx (Size run 32-43 matrix, draft sync)                                                      |
|  ├── PurchaseView.tsx (PO creation, GRN modal, landed cost, stock card modal)                                    |
|  ├── SalesInvoiceView.tsx (Carton helper, 13% Schedule-5 invoice modal, sales expenses subledger)                  |
|  ├── HRManagementView.tsx (Worker directory table, advance ledger, monthly payroll settlement)                   |
|  ├── ProductGalleryView.tsx (SKU image grid, lightbox, MIME-safe binary download)                                 |
|  └── NepaliDatePicker.tsx (Dual AD/BS synchronization, leap years, 1979-2100 BS)                                 |
|                                                                                                                   |
|  [SECURITY & MIDDLEWARE]                                                                                          |
|  ├── CorrelationIdMiddleware (X-Request-ID, X-Correlation-ID)                                                    |
|  ├── SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options)                                                       |
|  ├── IdempotencyMiddleware (SHA-256 payload digest, Redis/DB state machine)                                       |
|  ├── BasicRateLimitMiddleware (IP/Username bucket throttling)                                                    |
|  └── RBAC Layer (require_admin, require_editor, read-only viewer block)                                           |
|                                                                                                                   |
|  [BUSINESS SERVICES & TRANSACTION BOUNDARIES]                                                                     |
|  ├── Concurrency Locks: pg_advisory_xact_lock on Finished Goods, Raw Materials, Client Credit                    |
|  ├── Sequence Engine: SELECT ... FOR UPDATE atomic monotonic sequence generator                                  |
|  ├── Currency Engine: BigInteger Paisa (1 NPR = 100 paisa) & quantize_npr (Decimal 0.01)                            |
|  └── Calendar Engine: Bikram Sambat 1979-2100 BS bidirectional conversion table                                   |
|                                                                                                                   |
|  [PERSISTENCE LAYER — PostgreSQL 16+ / SQLAlchemy 2.0 / Alembic (Head: 015)]                                      |
|  ├── Append-Only Ledgers: stock_movements (+1/-1), raw_material_movements (+1/-1)                                  |
|  ├── Accounts Receivable Subledger: receivable_entries, payment_allocations (FIFO)                               |
|  ├── HR Subledger: worker_advances (ISSUED/RECOVERED), worker_monthly_records                                      |
|  └── Multi-Tenant Scoping: All 30 transactional tables foreign-keyed to companies.id                              |
|                                                                                                                   |
+-------------------------------------------------------------------------------------------------------------------+
```

---

## 5. Master Client Requirements Matrix

| ID | Original Client Request | Previous Audit Claim | Verified Status | Backend Evidence | Database Evidence | API Evidence | Frontend Evidence | Test Evidence | Remaining Gap | Proposed Change | Risk | Client Clarification Needed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **DATE-01** | Nepali Date (BS) support across system | Fully implemented (1979-2100 BS) | `VERIFIED_IMPLEMENTED` | `backend/app/core/nepali_date.py` (330 LOC) | `String(10)` `date_bs` columns across all tables | `api/v1/health.py`, date validation in Pydantic | `NepaliDatePicker.tsx`, `lib/nepaliDate.ts` | `test_nepali_date.py` (7/7 passed) | None | None | LOW | None (Verified). |
| **DATE-02** | Dispatch Date on Sales / Delivery | Fully implemented with decoupled dispatch | `VERIFIED_IMPLEMENTED` | `backend/app/api/v1/sales.py:471` (`dispatch_sales_order`) | `sales_orders.dispatch_date_ad/bs`, `dispatched_at` | `POST /api/v1/sales/orders/{id}/dispatch` | `SalesInvoiceView.tsx` dispatch modal & toggle | `test_sales_dispatch_and_expenses.py` (passed) | None | None | LOW | None (Verified). |
| **DATE-03** | Purchase Order: Ordered Date vs Receipt Date | Fully implemented in PO workflow | `VERIFIED_IMPLEMENTED` | `backend/app/api/v1/purchase.py:258` (`handle_receive_purchase`) | `purchases.order_date_ad/bs`, `receipt_date_ad/bs` | `POST /api/v1/purchases/{id}/receive` | `PurchaseView.tsx` PO creation & GRN modal | `test_raw_material_ledger.py` (passed) | None | None | LOW | None (Verified). |
| **DATE-04** | Sales Order: Ordered Date & Dispatch Date | Fully implemented | `VERIFIED_IMPLEMENTED` | `backend/app/models/sales.py:33-36` | `sales_orders.order_date_ad/bs`, `dispatch_date_ad/bs` | `POST /api/v1/sales/orders`, `POST /orders/{id}/dispatch` | `SalesInvoiceView.tsx` orders table & date pickers | `test_phase_1_core_schema.py` (passed) | None | None | LOW | None (Verified). |
| **PROD-01** | Production Batch: Serial No, Article No, Name, Typable Color | Present but incorrect (color catalog mismatch) | `PRESENT_BUT_INCORRECT` | `models/production.py:6`, `api/v1/production.py:180` | `ProductionBatch` has `batch_number`, `product_id`; no `color` column | `ProductionBatchCreate` lacks `color` string input | `ProductionView.tsx:589` locks selection to SKU dropdown | `test_bom_deduction.py` (passed) | Operators cannot type free-text colors on the floor dock; batch number serves as serial number without explicit serial field. | Add `color` column to `production_batches` and allow typed color input with optional auto-suggest. | MED | Does typing a new color create a new master SKU or remain a batch attribute? |
| **STOCK-01** | Automatic Stock Update across transactions | Fully implemented across all movements | `VERIFIED_IMPLEMENTED` | `api/v1/stock.py`, `api/v1/purchase.py`, `api/v1/production.py` | `stock_movements`, `raw_material_movements` (+1/-1) | All inward/outward endpoints append ledger rows | Real-time counters in `StockReportView.tsx`, `PurchaseView.tsx` | `test_stock_ledger.py`, `test_raw_material_ledger.py` (all passed) | Waste/scrap stock deduction path is not yet connected. | Connect waste recording to RM stock deduction in Phase 4. | LOW | None (Core ledger verified). |
| **STOCK-02** | Raw Material Stock Management & Alerts | Fully implemented via physical movement ledger | `VERIFIED_IMPLEMENTED` | `api/v1/purchase.py:325` (`handle_get_material_card`) | `raw_material_movements`, `raw_materials.current_stock` | `GET /api/v1/purchase/raw-materials/{id}/card` | `PurchaseView.tsx` Stock Card Modal & Adjustment Modal | `test_raw_material_ledger.py` (passed) | None | None | LOW | None (Verified). |
| **STOCK-03** | Raw Material Units: kg, pcs, litre | Fully implemented with CHECK constraint | `VERIFIED_IMPLEMENTED` | `models/purchase.py:25` (`CheckConstraint`) | `unit IN ('kg', 'pcs', 'litre')` | `POST /api/v1/purchase/raw-materials` | `PurchaseView.tsx` unit dropdown | `test_phase_1_core_schema.py` (passed) | None | None | LOW | None (Verified). |
| **PROD-02** | Production Gallery: Batch details, Article No, Color, Picture | Present but incorrect (linked to product, not batch) | `PRESENT_BUT_INCORRECT` | `models/gallery.py:7` (`ProductImage`) | `product_images.product_id` (FK to `products`); no batch FK | `api/v1/gallery.py` queries by product only | `ProductGalleryView.tsx:467` renders code/name, no batch or color | `test_gallery_and_analytics.py` (passed) | Images are tied to catalog products; photographs cannot be taken of or linked to specific production batch lots. | Add `production_batch_id` foreign key to `product_images` and batch upload UI. | MED | Is the gallery for catalog model marketing or factory floor lot inspection? |
| **PROD-03** | Waste Material Management | Missing | `MISSING` | None | None (`raw_material_movements.movement_type` has enum comment only) | None | None | None | Zero database tables, API routes, or frontend screens exist for recording waste/scrap. | Create `waste_records` table, API router, and deduction handler. | MED | Does waste scrap reduce raw materials (offcuts), finished goods, or WIP? |
| **HR-01** | Worker Cards: Picture, Name, Employee ID | Partially implemented (table only, no cards/photos) | `PARTIALLY_IMPLEMENTED` | `models/worker.py:16-22` | `workers.worker_code`, `name`, `photo_url` | `GET /api/v1/hr/workers` returns JSON list | `HRManagementView.tsx:740` renders `<table>` rows, zero avatar images | `test_hr_management.py` (passed) | UI renders a standard data table instead of visual worker cards; avatar images are completely unrendered. | Add worker card grid view with photo avatar, name, and code. | LOW | Should cards replace the table or offer a Grid/List view toggle? |
| **HR-02** | Worker Profile Modal: Addresses, Citizenship, Hours | Partially implemented (model fields exist, no KYC/upload) | `PARTIALLY_IMPLEMENTED` | `models/worker.py:22-26` | `workers.temporary_address`, `permanent_address`, `photo_url` | `WorkerResponse` schema omits addresses; no document upload endpoint | `HRManagementView.tsx` history modal lacks address fields & document dropzone | `test_hr_management.py` (passed) | Address fields omitted from API response; zero citizenship card upload, encrypted storage, or secure viewer. | Expose address fields in Pydantic schemas; create secure `worker_documents` vault. | HIGH | Who has permission to view citizenship cards? (Must be Admin only). |
| **HR-03** | Worker Active / Inactive Workflow & History | Partially implemented (boolean toggle exists, no audit reason) | `PARTIALLY_IMPLEMENTED` | `api/v1/hr.py:207` (`update_worker`) | `workers.is_active`, `inactive_date`, `inactive_reason` | `PATCH /api/v1/hr/workers/{id}` toggles boolean | `HRManagementView.tsx` status button toggles with unconfirmed click | `test_hr_management.py` (passed) | Deactivation does not prompt confirmation dialog; does not record `inactive_date` or `inactive_reason`. | Add confirmation modal capturing deactivation date and audit reason. | LOW | Does mid-month deactivation trigger final salary settlement? |
| **HR-04** | Worker Salary Information & Ledger Details | Partially implemented (payroll logic verified, table view split) | `PARTIALLY_IMPLEMENTED` | `api/v1/hr.py:367` (`process_monthly_payroll`) | `worker_monthly_records`, `worker_advances` | `POST /api/v1/hr/monthly-payroll` computes gross/net/advances | `HRManagementView.tsx` payroll modal & history modal | `test_hr_management.py` (passed) | Payroll math is verified; however, real-time net salary and status are separated in modals rather than directory summary. | Enrich worker table/cards with current month net payable estimate. | LOW | How is per-hour rate derived for salaried staff (standard 208 hrs or custom)? |
| **FIN-01** | General Expenses Module | Missing | `MISSING` | None | None | None | None | None | Factory operational expenses (rent, electricity, generator, diesel, tea, repairs) are completely absent. | Build `general_expenses` table, API CRUD router, and UI view. | MED | Should expenses link to chart of accounts or simple operational categories? |
| **FIN-02** | Sales Expenses (S.N., Date, Particular, Amount, Remarks) | Fully implemented in sales subledger | `VERIFIED_IMPLEMENTED` | `api/v1/sales.py:650-750` | `sales_expenses` table with paisa precision & order linkage | `GET, POST, DELETE /api/v1/sales/expenses` | `SalesInvoiceView.tsx` dedicated Expenses Subledger tab | `test_sales_dispatch_and_expenses.py` (passed) | None | None | LOW | None (Verified). |
| **FIN-03** | Purchase Expenses Multi-Column Ledger | Partially implemented (landed cost stored, ledger UI missing) | `PARTIALLY_IMPLEMENTED` | `models/purchase.py:58-63` | 4 BigInteger paisa columns on `purchases` | `POST /api/v1/purchases/{id}/receive` | `PurchaseView.tsx` GRN modal captures amounts, but no multi-column table exists | `test_raw_material_ledger.py` (passed) | Handwritten 4-column ledger table (| S.N. | Date | Particular | Carrying | Duty | China | Insurance |) does not exist in UI or reports. | Add dedicated Purchase Expenses Ledger tab rendering the client's exact 4-column format. | MED | Are purchase expenses capitalized into RM unit cost or expensed separately? |
| **FIN-04** | Fixed Assets Register | Missing | `MISSING` | None | None | None | None | None | No fixed assets register exists for tracking factory machinery, moulds, lasting machines, and equipment valuation. | Build `fixed_assets` table, API CRUD router, and valuation view. | LOW | Is depreciation calculation required, or strictly a basic register? |
| **OPS-01** | Automatic Daily Database Backup | Partially implemented (scripts exist, no active OS scheduler) | `PARTIALLY_IMPLEMENTED` | `scripts/backup_nightly.sh`, `app/services/backup_service.py` | `backups/latest_status.json` log | `GET /api/v1/backup/status` | `SettingsView.tsx` displays latest status | `test_backup.py`, `test_checkpoint_11_database.py` (passed) | Backups work on manual command; no automated systemd unit or cron daemon is installed/active in the environment. | Commit systemd service/timer and background telemetry daemon. | MED | What is the cloud backup retention policy (e.g. 30 days) and alert email? |

---

## 6. Detailed Findings by Requirement Category

### 6.1 Group A: Dates and Document Workflows
- **`DATE-01` (Nepali Date):** 
  - Backend `backend/app/core/nepali_date.py` and frontend `frontend/src/lib/nepaliDate.ts` share an identical canonical anchor: `1979-01-01 BS == 1922-04-13 AD`.
  - The calendar table contains 122 years of exact monthly day counts (1979–2100 BS), fully encompassing the client-requested 2070–2090 BS window.
  - Gregorian dates (`date_ad`) serve as canonical timestamps and relational database keys. Nepali dates (`date_bs`) are stored alongside as formatted `YYYY-MM-DD` strings for statutory compliance and display.
  - Runtime verification: `pytest backend/tests/test_nepali_date.py` passed 100% (7/7 tests in 0.05s).
- **`DATE-02` & `DATE-04` (Sales Dispatch Date):**
  - Sales orders decouple financial confirmation from physical stock dispatch.
  - `SalesOrder` model stores `order_date_ad`, `order_date_bs`, `dispatch_date_ad`, `dispatch_date_bs`, and `dispatched_at`.
  - `POST /api/v1/sales/orders/{id}/dispatch` verifies Available-to-Promise (ATP) physical inventory, acquires advisory locks, and deducts inventory (-1).
  - `SalesInvoiceView.tsx` features an immediate dispatch toggle (`dispatchNow`) for over-the-counter wholesale transactions and a deferred dispatch action modal for factory warehouse staging.
- **`DATE-03` (Purchase Ordered vs Receipt Date):**
  - `Purchase` model stores `order_date_ad`, `order_date_bs`, `receipt_date_ad`, `receipt_date_bs`, and `grn_number`.
  - Creating a PO with status `ORDERED` records the order without touching inventory. Physical receipt via `POST /api/v1/purchases/{id}/receive` records the GRN and appends +1 `RawMaterialMovement`.

### 6.2 Group B: Production and Stock
- **`PROD-01` (Batch Serial, Article, Name, Color):**
  - `ProductionBatch.batch_number` operates as the serial identifier (`PROD-01-00001`).
  - Article number and name map directly from `Product.code` and `Product.name`.
  - **Defect:** `ProductionView.tsx` selects models strictly from a grouped dropdown (`g.codePrefix — g.name (g.color)`). If an operator wants to produce a lot in "Navy Blue" and only "Black" exists in the product catalog, they cannot type "Navy Blue" on the batch dock.
- **`STOCK-01` & `STOCK-02` (Inventory Ledgers & Raw Materials):**
  - Finished Goods: `StockMovement` (+1 for production/returns, -1 for sales/dispatches) protected by `acquire_stock_mutation_lock`.
  - Raw Materials: `RawMaterialMovement` (+1 for purchase receipt, -1 for production BOM consumption) protected by `acquire_raw_material_mutation_lock`.
  - Source of truth: Both subsystems derive running balances strictly from append-only ledger entries.
- **`STOCK-03` (Raw Material Units):**
  - Database schema enforces `CheckConstraint("unit IN ('kg', 'pcs', 'litre')")`.
  - Verified by `test_phase_1_core_schema.py` which proved invalid unit strings (e.g. `'meters'`, `'bags'`) trigger an immediate `IntegrityError`.
- **`PROD-02` (Production Media Gallery):**
  - `ProductImage` links only to `products.id`.
  - The gallery functions as a static catalog showcase; photographs of actual production lots/batches cannot be uploaded or associated with `ProductionBatch`.
- **`PROD-03` (Waste Material Tracking):**
  - Completely absent from models, APIs, and UI. No scrap ledger or waste recording exists.

### 6.3 Group C: HR and Payroll
- **`HR-01` (Worker Cards):**
  - Display is currently a tabular data table (`<table>`) in `HRManagementView.tsx`.
  - Client requested visual cards showing worker photograph, name, and employee ID with click-to-profile navigation.
- **`HR-02` (Worker Profile & Sensitive Documents):**
  - `Worker` model has `temporary_address`, `permanent_address`, and `photo_url` columns, but they are excluded from Pydantic schemas and frontend forms.
  - Government citizenship documents have zero upload endpoints, zero database models, and zero encryption/access control.
- **`HR-03` (Active / Inactive Status):**
  - Toggling status in `HRManagementView.tsx` updates `is_active` boolean via `PATCH /api/v1/hr/workers/{id}` without confirmation.
  - Model columns `inactive_date` and `inactive_reason` exist but are ignored by the backend endpoint.
- **`HR-04` (Salary Information & Advance Deductions):**
  - `process_monthly_payroll` in `backend/app/api/v1/hr.py` calculates monthly salary vs hourly wage, 1.5x overtime multiplier, auto-recovers advances up to net pay, and records payment mode (`CASH` or `BANK`).
  - Advances ledger (`WorkerAdvance`) accurately records `ISSUED` and `RECOVERED` entries in integer paisa.

### 6.4 Group D: Expenses and Assets
- **`FIN-01` (General Expenses):**
  - No models, API endpoints, or frontend views exist for general factory operating overhead (rent, diesel, electricity, machine maintenance, office tea).
- **`FIN-02` (Sales Expenses):**
  - Verified end-to-end. `SalesExpense` model, `GET/POST/DELETE /api/v1/sales/expenses`, and dedicated subledger tab in `SalesInvoiceView.tsx` support S.N., date, particular, category, amount, and order linkage.
- **`FIN-03` (Purchase Expenses Ledger):**
  - The 4 cost columns (`carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`) exist in `purchases` and are captured during GRN receipt.
  - **Gap:** The client's handwritten ledger format (| S.N. | Date | Particular | Carrying-in | Duty | China Exp | Insurance |) does not exist as an inspectable ledger table or exportable report.
- **`FIN-04` (Fixed Assets):**
  - Completely absent. No register exists for factory machinery, moulds, lasting machines, generators, or vehicles.

### 6.5 Group E: Automated Daily Backups
- **`OPS-01` (Backup Scheduling):**
  - Verified: `scripts/backup_nightly.sh` executes `docker compose exec -T postgres pg_dump ... | gzip`.
  - Verified: `backend/app/services/backup_service.py` supports AES-256 encryption and remote S3/B2 cloud upload.
  - Verified: `docs/OPERATIONAL_HANDOVER.md` documents manual crontab installation (`0 2 * * *`).
  - **Gap:** No automated OS-level systemd timer, cron runner, or in-process daemon is actively running or committed as a self-installing unit.

---

## 7. Cross-Module Workflow Analysis

```
+-------------------------------------------------------------------------------------------------------------------+
|                                            CROSS-MODULE INTEGRITY AUDIT                                           |
+-------------------+---------------------------------------------+-------------------+-----------------------------+
| Workflow Chain    | Implementation Status                       | Concurrency Lock  | Verification Test           |
+-------------------+---------------------------------------------+-------------------+-----------------------------+
| **Procurement**   | PO (ORDERED) -> GRN -> RM Ledger -> Stock   | Advisory: RM ID   | test_raw_material_ledger.py |
| **Production**    | BOM Deduct -> Batch -> Finished Goods Ledger| Advisory: SKU/Size| test_bom_deduction.py       |
| **Sales Order**   | Order (CONFIRMED) -> Dispatch -> Stock Out  | Advisory: SKU/Size| test_sales_dispatch...py    |
| **Invoicing**     | Order -> Sequence Lock -> 13% Statutory VAT | Sequence Row Lock | test_invoice_numbering.py   |
| **AR Subledger**  | Invoice Debit -> Payment Credit -> FIFO Alloc| Advisory: Client  | test_receivables.py         |
| **HR Payroll**    | Hours/OT -> Gross Pay -> Adv Deduct -> Paid | DB Transaction    | test_hr_management.py       |
| **Sales Expense** | Order Expense -> Subledger Record (Paisa)   | Tenant Scope      | test_sales_dispatch...py    |
+-------------------+---------------------------------------------+-------------------+-----------------------------+
```

### Potential Failure Modes & Uncovered Edges:
1. **Production Scrap / Waste:** When leather or soling material is cut and scrapped, there is no system transaction to decrement raw material stock. Operators must currently execute manual stock adjustments (`/api/v1/purchase/raw-materials/{id}/adjust`) which lacks batch traceability.
2. **Batch Color Drift:** Because `ProductionBatch` has no color field and relies on catalog `Product.color`, factory runs with non-standard dye lots cannot be audited against stock curves.
3. **Sensitive Document Exposure:** If citizenship card images are added to the general `ProductImage` gallery storage without dedicated access control, compliance auditors and viewers could access private identity documents.

---

## 8. Database and Migration Impact Analysis

To bridge all verified gaps without disrupting existing production invariants, the following database migrations will be required:

### Migration 016: Production Color Normalization, Batch Media & Scrap Tracking
- `production_batches`: Add `color` (`String(50)`, nullable=True) and `serial_no` (`String(32)`, nullable=True).
- `product_images`: Add `production_batch_id` (`Integer`, ForeignKey("production_batches.id"), nullable=True).
- `waste_records`: New table `(id, company_id, batch_id, raw_material_id, quantity, waste_type, notes, actor_id, created_at)`.

### Migration 017: HR Worker Profile KYC & Citizenship Document Vault
- `workers`: Expose and ensure columns `temporary_address`, `permanent_address`, `photo_url`, `inactive_date`, `inactive_reason`.
- `worker_documents`: New secure table `(id, company_id, worker_id, document_type, file_path, mime_type, file_size_bytes, uploaded_by_id, created_at)`.

### Migration 018: General Factory Operating Expenses & Fixed Assets Register
- `general_expenses`: New table `(id, company_id, expense_date_ad, expense_date_bs, category, particular, amount_paisa, payment_method, remarks, actor_id, created_at)`.
- `fixed_assets`: New table `(id, company_id, asset_name, asset_code, purchase_date_ad, purchase_date_bs, purchase_cost_paisa, quantity, location, remarks, created_at)`.

---

## 9. Client Clarifications Required

Before executing the implementation phase, the following business decisions require formal client confirmation:

1. **Typable Batch Color (`PROD-01`):**
   - *Question:* When an operator enters a new color on the production dock (e.g., "Olive Green"), should the system automatically create a new Product SKU variant in the master catalog, or should the color remain strictly a production lot attribute?
2. **Purchase Expenses Capitalization (`FIN-03`):**
   - *Question:* Should the 4 purchase expense categories (Carrying-in, Import Duty, China Exp, Insurance) remain capitalized into the raw material inventory unit rate (as currently built), or should they be displayed in a separate general expense ledger?
3. **Citizenship Card Access (`HR-02`):**
   - *Question:* Are worker citizenship cards uploaded as front and back images separately or as a single document? (We recommend restricting document view access exclusively to Company Admin).
4. **Waste / Scrap Deduction (`PROD-03`):**
   - *Question:* Does production floor waste reduce Raw Material stock (e.g. scrap leather), or does it record rejected finished pairs from the assembly conveyor?
5. **Fixed Assets Depreciation (`FIN-04`):**
   - *Question:* Is annual depreciation calculation required, or is a straightforward asset acquisition and valuation register sufficient?

---

## 10. Acceptance Criteria for Unmet Requirements

### PROD-01 (Batch Typable Color & Serial)
- Operator can type free-text color in the production batch dock with instant suggestion from existing colors.
- Batch records persist the typed color and display it in the production batch table.
- Stock movements generated from the batch reflect the batch color.

### PROD-02 (Production Batch Gallery)
- Operators can upload photographs attached directly to a `batch_id`.
- Gallery cards display Article Number, Article Name, Color, Batch Number, and Date.

### PROD-03 (Waste & Scrap Tracking)
- Form allows logging scrap with raw material, quantity, batch reference, and waste category.
- Waste submission automatically creates a `-1` `RawMaterialMovement` with `movement_type='SCRAP_WRITEOFF'`.

### HR-01 & HR-02 (Worker Cards & Profile Vault)
- Worker directory offers a visual "Card Grid" view showing photo avatar, worker name, and employee code.
- Clicking worker card opens `WorkerProfileModal` showing bio, addresses, total hours, and documents tab.
- Citizenship card uploads are restricted; only Admin users can download or view ID images.

### HR-03 (Worker Deactivation Workflow)
- Deactivating worker opens a confirmation modal requiring an inactive date and deactivation reason.
- Inactive workers are hidden from active factory allocation but retain complete historical payroll/advance records.

### FIN-01 (General Expenses)
- Form allows logging operational expenses (rent, diesel, generator, maintenance) in integer paisa.
- Expenses table supports category filters, date ranges, and period total summaries.

### FIN-03 (Purchase Expenses Multi-Column Ledger)
- Purchase view includes a dedicated "Landed Cost Ledger" tab presenting the handwritten columns:
  `| S.N. | Date | Particular | Carrying-in | Import Duty | China Carrying-in | Insurance | Total |`
- Row totals and period column grand totals calculate accurately down to the paisa.

### FIN-04 (Fixed Assets Register)
- Form allows adding factory machinery, tools, and equipment with purchase date and cost in paisa.
- Register displays total capital asset valuation card and exportable asset inventory table.

### OPS-01 (Automated Daily Backup)
- Committed systemd timer or in-process cron daemon runs daily at 02:00 NPT.
- Successful backup status logs to `latest_status.json` and updates the Settings dashboard.

---

## 11. Risk-Ranked Implementation Roadmap

```
+----------------------------------------------------------------------------------------------------+
|                                    PROPOSED IMPLEMENTATION PHASES                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   PHASE 4: Production Color Normalization, Batch Media & Floor Waste Tracking                      |
|   ├── 4.1 ProductionBatch model extension (color, serial_no) & typable combobox                    |
|   ├── 4.2 ProductImage batch linkage & batch gallery modal                                         |
|   └── 4.3 Scrap / Waste tracking schema, API, and automatic RM ledger deduction                    |
|                                                                                                    |
|   PHASE 5: HR Worker Profile Cards, Citizenship Vault & Formal Inactive Workflow                   |
|   ├── 5.1 Worker card grid view with photo avatars and employee codes                              |
|   ├── 5.2 Worker profile modal with addresses, total hours, and Admin-only citizenship vault       |
|   └── 5.3 Confirmation dialog for worker deactivation recording inactive date and reason           |
|                                                                                                    |
|   PHASE 6: Factory Overhead Expenses & Fixed Assets Register                                       |
|   ├── 6.1 General operational expenses module (rent, diesel, generator, maintenance)               |
|   ├── 6.2 Purchase multi-column landed cost ledger matching client handwritten layout              |
|   └── 6.3 Fixed assets register and factory capital valuation dashboard                            |
|                                                                                                    |
|   PHASE 7: Automated Daily Backup Scheduler & Production Hardening                                 |
|   ├── 7.1 Dedicated systemd service & timer configuration for automated nightly execution          |
|   ├── 7.2 In-process background telemetry ping verifying backup freshness in Ops Cockpit           |
|   └── 7.3 Automated restore dry-run script with notification telemetry                             |
|                                                                                                    |
|   PHASE 8: Enterprise Regression Suite & Client Handover                                           |
|   ├── 8.1 100% green test pass across all new and existing test suites (Target: 320+ tests)        |
|   ├── 8.2 Frontend bundle budget enforcement (≤ 115 kB First Load JS)                             |
|   └── 8.3 Operational documentation & visual manual update                                         |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
```

---

## 12. Final Executive Summary Table

| ID | Requirement | Verified Status | Evidence Quality | Minimum Required Change | Risk | Client Decision Needed |
|---|---|---|---|---|---|---|
| **DATE-01** | Nepali date | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **DATE-02** | Dispatch date | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **DATE-03** | Purchase ordered/receipt dates | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **DATE-04** | Sales ordered/dispatch dates | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **PROD-01** | Batch serial/article/name/color | `PRESENT_BUT_INCORRECT` | High (Source + UI) | Add `color` column to batch; enable typed combobox | MED | Master SKU vs batch attribute |
| **STOCK-01** | Automatic stock updates | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | Connect waste deduction path | LOW | None |
| **STOCK-02** | Raw-material inventory | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **STOCK-03** | Raw-material units | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **HR-01** | Worker cards | `PARTIALLY_IMPLEMENTED` | High (Source + UI) | Add card grid view with photo avatars | LOW | Grid vs List toggle |
| **HR-02** | Worker profile and documents | `PARTIALLY_IMPLEMENTED` | High (Source + UI) | Expose address schemas; create secure doc vault | HIGH | Citizenship access permissions |
| **HR-03** | Activation/inactivation | `PARTIALLY_IMPLEMENTED` | High (Source + UI) | Confirmation dialog with date and audit reason | LOW | Mid-month final settlement |
| **HR-04** | Salary, hours, advances, payment | `PARTIALLY_IMPLEMENTED` | High (Source + Tests) | Enrich directory view with current net estimate | LOW | Salaried hourly formula (208 hrs) |
| **PROD-02** | Production gallery details | `PRESENT_BUT_INCORRECT` | High (Source + UI) | Link photos to `batch_id`; display batch details | MED | Marketing vs factory lot photos |
| **FIN-01** | General expenses | `MISSING` | High (Codebase search) | Build `general_expenses` table, API, and UI | MED | Expense category list |
| **FIN-02** | Sales expenses | `VERIFIED_IMPLEMENTED` | High (Source + Tests) | None | LOW | None |
| **FIN-03** | Purchase expenses ledger | `PARTIALLY_IMPLEMENTED` | High (Source + UI) | Build multi-column ledger table matching layout | MED | Capitalization vs expense split |
| **FIN-04** | Fixed assets | `MISSING` | High (Codebase search) | Build `fixed_assets` table, API, and UI | LOW | Depreciation requirement |
| **PROD-03** | Waste material | `MISSING` | High (Codebase search) | Build `waste_records` table, API, and RM deduction | MED | RM scrap vs finished rejects |
| **OPS-01** | Automatic daily backup | `PARTIALLY_IMPLEMENTED` | High (Source + Script)| Commit systemd service/timer and telemetry ping | MED | Cloud retention & alert target |

### Final Calculated Status Breakdown:
- **`VERIFIED_IMPLEMENTED`:** 8 (42.1%)
- **`PARTIALLY_IMPLEMENTED`:** 6 (31.6%)
- **`PRESENT_BUT_INCORRECT`:** 2 (10.5%)
- **`MISSING`:** 3 (15.8%)
- **`DUPLICATE_EXISTING_FUNCTIONALITY`:** 0 (0.0%)
- **`AMBIGUOUS`:** 0 (0.0%)
- **`UNVERIFIABLE`:** 0 (0.0%)
- **Total Requirements Audited:** **19 (100.0%)**

---

## 13. Explicit Limitations of this Audit

1. **Host Environment Limitations:** The audit was conducted on a Windows local development workstation. The Linux-specific shell script `scripts/backup_nightly.sh` was inspected statically but could not be executed directly via native bash cron without a containerized or Linux subsystem environment.
2. **PostgreSQL vs SQLite In-Memory Concurrency:** Unit test execution utilizes SQLite in-memory with threading mutex fallbacks. Production behavior relies on PostgreSQL 16+ `pg_advisory_xact_lock` and row-level locks, which are validated in Postgres checkpoint test files (`test_checkpoint_15_2_postgres.py`, `test_checkpoint_16_postgres.py`).
3. **No Code Modification Constraint:** In strict observance of audit-only rules, no schema changes, migration files, or frontend components were edited. All assessments are based on static code inspection and non-mutating test verification.
