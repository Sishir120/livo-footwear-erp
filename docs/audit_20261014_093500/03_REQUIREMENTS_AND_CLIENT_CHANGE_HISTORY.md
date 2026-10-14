# LIVO FOOTWEAR ERP — REQUIREMENTS & CLIENT CHANGE HISTORY

**Document Identifier:** `03_REQUIREMENTS_AND_CLIENT_CHANGE_HISTORY.md`  
**Audit Directory:** `docs/audit_20261014_093500/`  
**Audit Execution Date:** 2026-10-14 09:35:00 +05:45 (Nepal Standard Time)  
**Primary Principle:** Evidence over assumptions. Clear distinction between client requirements, technical hardening, agent recommendations, and unapproved suggestions.

---

## 1. CATEGORICAL REQUIREMENTS STRUCTURE

Requirements are segregated into nine distinct categories:
1. **Original Business Requirements (BR)** — From initial kickoff and `PRD.md` (Sept 25, 2026)
2. **Client-Requested Additions (CR)** — From client change request cycle (Oct 10–12, 2026)
3. **Technical Hardening Requirements (TH)** — Reliability, concurrency, and integrity mandates
4. **Security Requirements (SEC)** — Multi-tenancy, RBAC, input validation, and document protection
5. **Operational & Deployment Requirements (OPS)** — Backups, hosting, telemetry, and runbooks
6. **Explicit Business Decisions (BD)** — Documented choices approved by stakeholder consensus
7. **Agent Recommendations Never Approved (REC)** — Proposed technical extensions not ratified
8. **Superseded or Withdrawn Requirements (SUP)** — Earlier specs altered by later client requests
9. **Unresolved / Ambiguous Requirements (AMB)** — Open questions requiring client clarification

---

## 2. ORIGINAL BUSINESS REQUIREMENTS (BR)

### BR-01: Raw Material Procurement Recording
- **Description:** Record raw material purchases by date, supplier name, material type, quantity, rate, and total amount. Support credit and cash purchases.
- **Source & Date:** `PRD.md` §3.1 (2026-09-25).
- **Business Purpose:** Track procurement of leather, rubber, EVA sheets, buckles, glue, and thread across ~100 regular vendors.
- **Expected Workflow:** User selects supplier, chooses material, enters quantity and price, selects payment terms (Cash / Credit), and saves purchase record.
- **Relevant Modules:** `backend/app/api/v1/purchase.py`, `frontend/src/components/PurchaseView.tsx`.
- **Current Evidence:** `Purchase` table with `supplier_id`, `raw_material_id`, `quantity`, `unit_price`, `total_amount`.
- **Test Evidence:** `backend/tests/test_raw_material_ledger.py` (6 passed).
- **Current Status:** **VERIFIED COMPLETE** (Superseded in part by CR-04 for landed costs).

### BR-02: Production Tracking & Finished Goods Creation
- **Description:** Record production runs converting raw materials into finished footwear. Quantities produced must auto-update finished-goods stock and decrement raw materials.
- **Source & Date:** `PRD.md` §3.2 (2026-09-25).
- **Business Purpose:** Track factory floor productivity by date, worker count, and manufactured pairs.
- **Relevant Modules:** `backend/app/api/v1/production.py`, `frontend/src/components/ProductionView.tsx`.
- **Current Evidence:** `ProductionBatch` model, BOM proportional deduction engine, `StockMovement` creation.
- **Test Evidence:** `backend/tests/test_bom_deduction.py`, `test_stock_ledger.py`.
- **Current Status:** **VERIFIED COMPLETE**.

### BR-03: Size & Color Footwear Stock (Pairs)
- **Description:** Stock must be tracked by item number/code, color, and size (Paris Points 32–43) in pairs. Stock updates strictly from production (in) and sales (out); never manual edits.
- **Source & Date:** `PRD.md` §3.3 (2026-09-25).
- **Business Purpose:** Footwear wholesale and retail inventory management.
- **Relevant Modules:** `backend/app/models/stock.py`, `frontend/src/components/StockReportView.tsx`.
- **Current Evidence:** `Product` SKU catalog with size-curve matrix, append-only `StockMovement` ledger, `StockSnapshot` balance tables.
- **Test Evidence:** `backend/tests/test_snapshots.py`, `test_stock_movement_math.py`.
- **Current Status:** **VERIFIED COMPLETE**.

### BR-04: Sales Orders & Printable IRD Tax Invoices
- **Description:** Record wholesale sales orders with customer name, PAN, items, rates, and payment methods. Generate printable invoices/challans with sequential, immutable invoice numbers.
- **Source & Date:** `PRD.md` §3.4 (2026-09-25).
- **Business Purpose:** Wholesale footwear billing, dispatch documentation, and Nepal tax compliance.
- **Relevant Modules:** `backend/app/api/v1/sales.py`, `invoices.py`, `frontend/src/components/SalesInvoiceView.tsx`.
- **Current Evidence:** `SalesOrder`, `SalesItem`, `Invoice`, `InvoiceSequence` tables; printable A4 tax invoice template with PAN.
- **Test Evidence:** `backend/tests/test_invoice_numbering.py`, `test_sales_dispatch_and_expenses.py`.
- **Current Status:** **VERIFIED COMPLETE**.

### BR-05: Accounts Receivable Tracking & Party Aging
- **Description:** Track received vs. receivable balances per client. Payment methods: cash, bank, cheque.
- **Source & Date:** `PRD.md` §3.4 (2026-09-25).
- **Business Purpose:** Monitor customer credit risk and overdue wholesale balances.
- **Relevant Modules:** `backend/app/api/v1/receivables.py`, `frontend/src/components/PartyAgingView.tsx`.
- **Current Evidence:** Append-only `ReceivableEntry` subledger, payment allocation matrix, 4 aging buckets (0–30, 31–60, 61–90, 90+ days).
- **Test Evidence:** `backend/tests/test_receivables.py` (6 passed).
- **Current Status:** **VERIFIED COMPLETE**.

### BR-06: Daily Factory Report & Stock Report (Top Client Priority)
- **Description:** The client explicitly declared the Daily Report (production, sales, and stock movements for a given day) and the Stock Report as the #1 and #2 success criteria.
- **Source & Date:** `PRD.md` §3.7 & §7 (2026-09-25).
- **Relevant Modules:** `backend/app/api/v1/reports.py`, `frontend/src/components/AppShell.tsx` (Dashboard View).
- **Current Evidence:** `GET /api/v1/reports/daily` endpoint aggregating daily floor velocity, cash realization ratio, and finished pairs.
- **Test Evidence:** `backend/tests/test_erp_flow.py`.
- **Current Status:** **VERIFIED COMPLETE**.

---

## 3. CLIENT-REQUESTED ADDITIONS (CR)

Between October 10 and October 12, 2026, the client introduced 10 operational enhancements following early reviews:

### CR-01: Interactive Bikram Sambat (BS) Calendar Dropdown
- **Description:** The date picker must display a full Bikram Sambat calendar grid (years 2065–2095 BS) with Nepali month and day-of-week headers (`आइत` through `शनि`, with Saturday in red), auto-converting to Gregorian AD dates without timezone shifts.
- **Source & Date:** Transcript `171235dc` Step 153 (2026-10-10); `CLIENT_CHANGE_REQUEST_GAP_ANALYSIS.md`.
- **Implementation:** `frontend/src/components/NepaliDatePicker.tsx` (777 lines); `backend/app/core/nepali_date.py`.
- **Status:** **VERIFIED COMPLETE** (Verified in recorded browser session `bs_calendar_ui_test`).

### CR-02: Decoupled Sales Order Date vs. Physical Dispatch Date
- **Description:** Distinguish between when a wholesale order is taken and when shoes physically leave the factory warehouse. Physical inventory must not decrement upon order creation, but only when dispatched.
- **Source & Date:** Transcript `1849f93e` Step 10016 (2026-10-11).
- **Implementation:** Added `dispatch_date_ad/bs` to `SalesOrder`; added `POST /api/v1/sales/orders/{id}/dispatch` endpoint with inventory advisory locks.
- **Status:** **VERIFIED COMPLETE**.

### CR-03: Decoupled Purchase Order Date vs. Goods Receipt (GRN) Date
- **Description:** Distinguish between PO issuance and physical raw material delivery. Material stock must increment only upon Goods Receipt Note (GRN) confirmation.
- **Source & Date:** Transcript `1849f93e` Step 9779 (2026-10-11).
- **Implementation:** Added `receipt_date_ad/bs` and `grn_number` to `Purchase`; added `POST /api/v1/purchases/{id}/receive`.
- **Status:** **VERIFIED COMPLETE**.

### CR-04: Multi-Column Landed Cost Breakdown for Raw Materials
- **Description:** Track four specific purchase cost components: Carrying-in, Import Duty/Tax, China Carrying-in, and Insurance. Capitalize these costs into the effective unit rate of raw materials.
- **Source & Date:** Transcript `1849f93e` Step 9779 (2026-10-11).
- **Implementation:** 4 paisa columns in `purchases` table; integer math capitalization; dedicated Tab 3 in `PurchaseView.tsx`.
- **Status:** **VERIFIED COMPLETE**.

### CR-05: Raw Material Units of Measurement (`kg`, `pcs`, `litre`)
- **Description:** Enforce standard physical measurement units for raw materials with positive decimal precision and zero-floor balance protection.
- **Source & Date:** Transcript `1849f93e` Step 9448 (2026-10-11).
- **Implementation:** Enum constraint `('kg', 'pcs', 'litre')` on `raw_materials.unit`; append-only `raw_material_movements` ledger.
- **Status:** **VERIFIED COMPLETE**.

### CR-06: Custom Floor Lot Dye Colors in Production
- **Description:** Factory operators dye batches in custom or seasonal colors. Operators must type custom color strings without polluting master catalog SKUs.
- **Source & Date:** Transcript `1849f93e` Step 11275 (2026-10-12).
- **Implementation:** Added `color` column to `production_batches`; continuous keyboard entry dock with autocomplete.
- **Status:** **VERIFIED COMPLETE**.

### CR-07: Production Gallery Batch Association
- **Description:** Photographs taken of finished footwear batches must link directly to the specific production lot, article number, and color.
- **Source & Date:** Transcript `1849f93e` Step 11275 (2026-10-12).
- **Implementation:** Added `production_batch_id` foreign key to `product_images`; multi-tenant image upload endpoint.
- **Status:** **VERIFIED COMPLETE**.

### CR-08: Complete Worker Profiles & Secure Citizenship Document Vault
- **Description:** Worker directory must store temporary/permanent addresses, profile photos, active/inactive dates, and secure citizenship documents accessible only by Admins.
- **Source & Date:** Transcript `1849f93e` Step 11576 (2026-10-12).
- **Implementation:** Extended `workers` table; created `worker_documents` table with magic-byte validation and Admin-only RBAC.
- **Status:** **VERIFIED COMPLETE**.

### CR-09: Worker Advance Installment Recovery Engine
- **Description:** Automatically deduct worker advances from monthly payroll via fixed monthly installments or FIFO repayment allocation.
- **Source & Date:** Transcript `1849f93e` Step 12144 (2026-10-12).
- **Implementation:** Extended `worker_advances` with `parent_advance_id`, `monthly_installment_paisa`; built deterministic recovery engine.
- **Status:** **VERIFIED COMPLETE**.

### CR-10: Operating Expenses, Fixed Assets & Waste Scrap
- **Description:** Track Sales Logistics Expenses, General Factory Expenses, Fixed Assets Register with depreciation, and Production Scrap/Waste.
- **Source & Date:** Transcript `1849f93e` Step 13380 (2026-10-12).
- **Implementation:**
  - Sales Expenses: Backend + Frontend complete in `SalesInvoiceView.tsx`.
  - Factory Expenses: Backend complete (`/api/v1/expenses/factory`), **Frontend UI MISSING**.
  - Fixed Assets: Backend complete (`/api/v1/assets`), **Frontend UI MISSING**.
  - Waste Scrap: Backend complete (`/api/v1/waste`), **Frontend UI MISSING**.
- **Status:** **PARTIALLY COMPLETE (BACKEND ONLY FOR ASSETS, SCRAP & FACTORY EXPENSES)**.

---

## 4. TECHNICAL HARDENING & SECURITY REQUIREMENTS

| ID | Specification | Inception Point | Implementation Reference | Audit Status |
| :--- | :--- | :--- | :--- | :---: |
| **TH-01** | **Pessimistic Row Locking & Mutexes:** Prevent race conditions in stock and sequence generation. | Commit `6b7b94a` (Sept 28) | `app/core/locks.py`, `with_for_update()` | **VERIFIED** |
| **TH-02** | **Integer Paisa / Decimal Currency Math:** Eliminate binary floating-point roundoff errors in balances. | Commit `6b7b94a` (Sept 28) | `app/core/currency.py`, `quantize_npr` | **VERIFIED** |
| **TH-03** | **Idempotent Request Execution:** Deduplicate retry storms via unique UUID keys. | Checkpoint 8 (Oct 1) | `app/middleware/idempotency.py` | **VERIFIED** |
| **TH-04** | **Offline Mutation Outbox Queue:** Allow offline operation with IndexedDB queue and replay. | Checkpoint 9 (Oct 1) | `frontend/src/lib/offlineQueue.ts` | **VERIFIED** |
| **SEC-01** | **Strict Multi-Tenant Scoping:** Enforce `company_id` on 100% of queries and mutations. | Checkpoint 10 (Oct 1) | `app/db/repository.py` (`TenantRepository`) | **VERIFIED** |
| **SEC-02** | **Role-Based Access Control (RBAC):** Reject viewers from mutating endpoints with HTTP 403. | Checkpoint 10 (Oct 1) | `app/api/deps.py` (`require_editor`, `require_admin`) | **VERIFIED** |
| **SEC-03** | **File Upload Header Magic-Byte Verification:** Block executable payloads disguised as JPEG/PNG/PDF. | Phase 4B (Oct 12) | `app/api/v1/hr.py`, `app/api/v1/gallery.py` | **VERIFIED** |

---

## 5. OPERATIONAL & DEPLOYMENT REQUIREMENTS

| ID | Requirement | Target State | Current Implementation Reality | Status |
| :--- | :--- | :--- | :--- | :---: |
| **OPS-01** | **Automated Daily Backups:** Unattended encrypted backups to cloud storage. | Systemd cron daemon | Manual API endpoint (`POST /backup/run`); zero automated daemon | **INCOMPLETE / DEFECT** |
| **OPS-02** | **Disaster Recovery Restore:** Verified database restoration drill. | Automated script | `scripts/verify_backup_restore.py` tested for SQLite | **VERIFIED (SQLITE ONLY)** |
| **OPS-03** | **TLS & Reverse Proxy:** Auto-renewing HTTPS with security headers. | Caddy v2 container | `Caddyfile` fully authored; pending external domain DNS | **READY FOR DNS** |
| **OPS-04** | **Container Non-Root Security:** Containers run under dedicated non-root UID. | UID 10001 (`livo`) | Dockerfiles enforce `USER livo` / `USER nodejs` | **VERIFIED** |

---

## 6. EXPLICIT BUSINESS DECISIONS (BD)

- **BD-01: Dual Gregorian/Bikram Sambat Storage:** System stores Gregorian UTC dates internally in database `date_ad` columns, and stores Bikram Sambat strings (`YYYY-MM-DD`) in `date_bs` columns. Approved to ensure interoperability.
- **BD-02: Decoupled Dispatch Stock Decrement:** Finished footwear stock is decremented strictly upon warehouse dispatch, not order booking. Approved to prevent phantom stock shortages.
- **BD-03: Capitalized Landed Cost Accounting:** Import duty, freight, and insurance are capitalized into raw material valuation rather than expensed immediately. Approved for accurate unit COGS.
- **BD-04: Mandatory Statutory 13% Nepal VAT:** Default VAT on footwear invoices is 13%, with tax exemption allowed only with registered statutory documentation. Approved October 12.

---

## 7. UNAPPROVED AGENT RECOMMENDATIONS (REC)

The following proposals were authored by AI agents during planning sprints but **have not been approved by the client**:
- **REC-01: Chart of Accounts / Double-Entry General Ledger:** An agent recommended expanding factory expenses into a full double-entry accounting engine with debit/credit balance sheets. *Status: Unapproved recommendation; out of scope.*
- **REC-02: Barcode Thermal Printing Hardware Integration:** Proposed direct ESC/POS hardware USB drivers for citizen thermal printers. *Status: Unapproved recommendation; client only requested browser printing.*
- **REC-03: Worker Biometric Fingerprint Clock-in Device Integration:** Proposed ZKTeco biometric device SDK polling. *Status: Unapproved recommendation; manual daily logs suffice.*

---

## 8. UNRESOLVED & AMBIGUOUS REQUIREMENTS (AMB)

These questions remain open and require explicit stakeholder clarification:
1. **AMB-01 (Factory Expenses UI Placement):** Should General Factory Expenses have its own dedicated top-level sidebar tab or reside under Settings?
2. **AMB-02 (Fixed Asset Depreciation Posting):** Does the client prefer straight-line or diminishing-value depreciation, and at what frequency (monthly vs. end-of-fiscal-year)?
3. **AMB-03 (Scrap Revenue Allocation):** Does scrap/waste sales revenue offset raw material expenses or credit general other income?
