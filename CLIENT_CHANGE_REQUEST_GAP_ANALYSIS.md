# CLIENT CHANGE REQUEST — PHASE 0: REQUIREMENTS VALIDATION & CODEBASE GAP ANALYSIS
**System:** Livo Footwear ERP  
**Audit Date:** 2026-10-11  
**Audit Phase:** Phase 0 (Requirements Validation & Codebase Gap Analysis)  
**Status:** COMPLETE — NO APPLICATION CODE MODIFIED (STRICT AUDIT BASELINE)

---

## 1. Executive Summary

This audit evaluates the verbal change requests from the client against the production-hardened baseline of the **Livo Footwear ERP** (Checkpoints 1–18). The existing system enforces strict multi-tenant isolation, row-level advisory locking for inventory and credit boundaries, integer paisa precision for financial transactions, append-only finished goods ledgers, and automated S3/B2 database backup routines.

### Key Audit Discoveries
1. **Existing Architecture is Robust but Asymmetric:** Finished goods inventory is strictly ledger-driven (`stock_movements`), protected by distributed advisory locks and pessimistic concurrency. However, raw material inventory is **virtual and unledgered**, calculated dynamically as `SUM(Purchase.quantity) - SUM(ProductionMaterialUsage.quantity_used)`. There is currently no raw material receiving workflow, scrap/waste tracking, or stock adjustment mechanism.
2. **Date Subsystem:** Dual-date tracking (`date_ad` and `date_bs`) is already deeply integrated across invoices, production batches, sales orders, and finished goods stock movements. However, order lifecycles lack state-based date tracking: `sales_orders` has no separate `dispatch_date`, and `purchases` has no split between `ordered_date` and `receipt_date`.
3. **Color & Production Batching:** `Product.color` is currently a catalog attribute tied to a product SKU. Allowing free-text typable colors at the production batch level without master catalog normalization threatens inventory integrity, as footwear finished goods stock tracking requires explicit variant identification (Model + Color + Size).
4. **HR & Payroll Foundation:** Core worker profile management, real-time advance tracking (ISSUED/RECOVERED), and monthly payroll calculation (hours, overtime, advance deductions, cash/bank disbursement) are already built in `backend/app/api/v1/hr.py` and `frontend/src/components/HRManagementView.tsx`. However, worker photos, addresses, citizenship document uploads, inactive dates, and dedicated profile dialogs are missing.
5. **Completely Missing Business Domains:** General Expenses, Sales Expenses, Purchase Expenses (landed costs), Fixed Assets, and Waste Materials currently have **zero implementation** in database schemas, backend APIs, or frontend components.
6. **Operating Rule Enforcement:** In accordance with Phase 0 instructions, **no application code, database migrations, or schemas have been altered**. This document establishes the authoritative gap matrix and risk-managed implementation roadmap.

---

## 2. Current Architecture Relevant to These Changes

### Backend Stack
- **Framework:** FastAPI with Python 3.12+
- **Database & ORM:** PostgreSQL 16+ (validated on 18.6), SQLAlchemy 2.0 ORM, Alembic migrations (current HEAD: `012_add_c15_indexes`).
- **Data Repositories:** TenantRepository pattern (`backend/app/db/repository.py`) enforcing `company_id` multi-tenant scoping.
- **Concurrency & Locks:** Distributed PostgreSQL advisory locks (`acquire_stock_advisory_lock`, `acquire_client_credit_lock`, `acquire_stock_mutation_lock`) and thread-level mutexes in `backend/app/core/locks.py`.
- **Financial Precision:** Integer paisa (`BigInteger`) for worker payroll/advances; `Decimal` quantized to 2 decimal places (`quantize_npr` in `backend/app/core/currency.py`) for invoicing and sales.
- **Sequence Generation:** Atomic monotonic document sequences (`generate_document_number` in `backend/app/core/sequence.py` and `allocate_next_invoice_sequence` in `backend/app/models/invoice.py`).

### Frontend Stack
- **Framework:** Next.js (App Router), React 19, TypeScript
- **State & Sync:** IndexedDB local cache (`lib/offlineDb.ts`), background offline synchronization queue (`lib/offlineQueue.ts`).
- **Date Handling:** Dual AD/BS handling via `NepaliDatePicker.tsx` and Bikram Sambat conversion tables (2000–2090 BS) in `lib/nepaliDate.ts`.
- **UI Components:** Custom modular dashboard views (`ProductionView.tsx`, `PurchaseView.tsx`, `SalesInvoiceView.tsx`, `HRManagementView.tsx`, `ProductGalleryView.tsx`).

### Current ERP Module Mapping
| Business Domain | Model File | Router File | Primary Frontend View | Current Capability |
|---|---|---|---|---|
| **Purchases / Raw Materials** | `models/purchase.py` | `api/v1/purchase.py` | `PurchaseView.tsx` | Direct purchase entries; flat supplier/material masters; no PO document lifecycle. |
| **Finished Goods Stock** | `models/stock.py`, `models/stock_snapshot.py` | `api/v1/stock.py` | `InventoryView.tsx`, `StockLedgerView.tsx` | Append-only ledger `stock_movements`; multi-warehouse; periodic snapshotting. |
| **Sales & Invoices** | `models/sales.py`, `models/invoice.py`, `models/receivable.py` | `api/v1/sales.py`, `api/v1/invoices.py` | `SalesInvoiceView.tsx` | Sales orders, payments, accounts receivable ledger, tax invoicing with atomic sequence locks. |
| **Production** | `models/production.py`, `models/bom.py` | `api/v1/production.py` | `ProductionView.tsx` | BOM recipes, continuous batch entry, size run matrix (32–43), draft sync. |
| **Product Gallery** | `models/gallery.py` | `api/v1/gallery.py` | `ProductGalleryView.tsx` | Product catalog photos with path traversal defense; linked to Product ID only. |
| **HR & Payroll** | `models/worker.py` | `api/v1/hr.py` | `HRManagementView.tsx` | Worker master, advances ledger, monthly payroll calculation, active/inactive filter. |
| **Backups** | N/A (Service-only) | N/A | Settings modal | `backup_service.py` executes pg_dump, AES encryption, S3/B2 upload; manual trigger. |
| **Expenses** | *MISSING* | *MISSING* | *MISSING* | Completely absent. |
| **Fixed Assets** | *MISSING* | *MISSING* | *MISSING* | Completely absent. |
| **Waste Materials** | *MISSING* | *MISSING* | *MISSING* | Completely absent. |

---

## 3. Master Requirements Matrix

| ID | Client Requirement | Current Status | Evidence | Backend | Database | API | Frontend | Tests | Dependencies | Risk | Clarification Needed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **REQ-A1** | Nepali Date (BS) support across system | `PARTIALLY_IMPLEMENTED` | `NepaliDatePicker.tsx`, `lib/nepaliDate.ts`, `sales_orders.order_date_bs`, `purchases.purchase_date_bs` | Needs BS validation helper in backend | String(10) date_bs columns exist on core docs; missing on new domains | Existing APIs accept date_bs; need schemas on new endpoints | NepaliDatePicker component exists and functions | Add BS leap-year & boundary test suite | None | LOW | Confirm whether AD remains canonical in DB and BS is calculated/display. |
| **REQ-A2** | Dispatch Date on Sales / Delivery | `MISSING` | `models/sales.py` lines 30–35 only has `order_date_ad/bs` and `delivered: bool` | Needs dispatch transition logic in `sales.py` | Add `dispatch_date_ad`, `dispatch_date_bs` to `sales_orders` | New endpoint `POST /sales/orders/{id}/dispatch` | Add Dispatch Date picker and dispatch action in UI | Concurrency tests on late dispatch stock deduction | REQ-06 (Stock) | MEDIUM | Can an order be dispatched in partial shipments or always 100% full order? |
| **REQ-A3** | Purchase Order: Ordered Date vs Receipt Date | `MISSING` | `models/purchase.py` lines 45–46 only has `purchase_date_ad/bs` | Need PO workflow logic (Ordered -> Received) | Add `ordered_date_ad/bs`, `receipt_date_ad/bs`, `status` to `purchases` | Update `POST /purchase/purchases` & add receiving endpoint | Split Purchase form into PO Creation vs Material Receipt | Receipt stock update integration tests | REQ-06, REQ-07 | MEDIUM | Is PO an internal order, or does supplier invoice arrive at time of order? |
| **REQ-A4** | Sales Order: Ordered Date & Dispatch Date | `PARTIALLY_IMPLEMENTED` | `sales_orders` has `order_date_ad/bs` but lacks `dispatch_date` | Update sales order schema & state machine | Add `dispatch_date_ad/bs` to `sales_orders` | Accept `dispatch_date` in order creation or dispatch endpoint | Display Ordered Date and Dispatch Date in Sales table | Sales order lifecycle regression tests | REQ-A2, REQ-06 | LOW | Does dispatch date default to order date if delivered immediately? |
| **REQ-05** | Production Batch: Serial No, Article No, Name, Typable Color | `PRESENT_BUT_INCORRECT` | `models/production.py` `batch_number` exists; `Product.color` is static; `ProductionBatch` has no color | Decouple or map batch color to product SKU | Add `batch_serial_no`, `color` to `production_batches` | Update `ProductionBatchCreate` schema with `color` field | Add free-text/combobox color input in continuous batch dock | Test SKU mapping and casing normalization | Finished Goods Stock | HIGH | Does typing a new color create a new Product variant SKU, or is it batch-only? |
| **REQ-06** | Automatic Stock Update across transactions | `PRESENT_BUT_INCORRECT` | Finished goods updated in `sales.py` & `production.py`; Raw material stock is purely virtual | Build dedicated Raw Material ledger movement logic | New table `raw_material_movements` or unified ledger | Update purchase, production, and adjustment endpoints | Real-time stock counters across inventory views | Race condition & stock exhaustion tests under concurrency | REQ-A2, REQ-A3, REQ-07 | HIGH | Should inventory disallow negative stock strictly for raw materials? |
| **REQ-07** | Raw Material Stock Management & Alerts | `PARTIALLY_IMPLEMENTED` | `RawMaterial` model exists (`models/purchase.py`); virtual math in `check_raw_material_stock` | Build raw material balance query & adjustments | Add physical stock ledger & warehouse foreign key | Endpoint `GET /purchase/raw-materials/stock` & adjustments | Dedicated Raw Material Stock inventory tab/view | Unit tests on stock balance calculations | REQ-06 | MEDIUM | Is raw material stored in multiple warehouses or a single central storeroom? |
| **REQ-08** | Raw Material Units: kg, pcs, litre | `PARTIALLY_IMPLEMENTED` | `RawMaterial.unit: String(50)` default "kg"; no validation | Pydantic enum validator `('kg', 'pcs', 'litre')` | Add CHECK constraint or ENUM on `raw_materials.unit` | Enforce allowed units on `POST /purchase/raw-materials` | Dropdown select for unit instead of free text | Validation tests rejecting invalid units (e.g., 'bags') | None | LOW | Are unit conversions needed (e.g. grams -> kg, millilitres -> litres)? |
| **REQ-09** | Worker Listing: Picture, Name, Employee ID | `PARTIALLY_IMPLEMENTED` | `Worker` has `worker_code`, `name`; no picture (`models/worker.py`) | Return `photo_url` in `WorkerResponse` | Add `photo_url` to `workers` table | Add image upload route for worker profile picture | Render avatar thumbnail in worker table rows | Image upload & thumbnail display tests | REQ-11 | LOW | Where should worker profile photos be stored (local disk vs cloud)? |
| **REQ-10** | Worker Profile Modal with addresses, citizenship, hours | `PARTIALLY_IMPLEMENTED` | `HRManagementView.tsx` has history modal; lacks addresses, citizenship | Endpoint `GET /hr/workers/{id}/profile` | Add `temp_address`, `perm_address` to `workers` | Return profile details in worker GET response | Build WorkerProfileModal with tabs for bio, hours, docs | UI rendering and permission verification tests | REQ-09, REQ-11 | MEDIUM | Should hourly workers see monthly equivalent hours or actual floor clocking? |
| **REQ-11** | Citizenship Document Upload & Access Control | `MISSING` | `ProductImage` exists in gallery; no worker document model | Secure document upload handler with restricted access | New table `worker_documents` or worker citizenship columns | `POST /hr/workers/{id}/documents/citizenship` | Upload dropzone in Worker Profile modal | Path traversal, MIME type, and RBAC security tests | REQ-10 | HIGH | Are citizenship back and front photos uploaded separately or single file? |
| **REQ-12** | Worker Active / Inactive Workflow & History | `PARTIALLY_IMPLEMENTED` | `Worker.is_active` boolean exists; toggle button in UI; no inactive date | Soft deactivation logic recording `inactive_date` | Add `inactive_date`, `deactivation_reason` to `workers` | `POST /hr/workers/{id}/status` with confirmation payload | Confirmation dialogs; Inactive tab filter view | Verify historical payroll/advances remain intact | None | LOW | When inactivated mid-month, should final payroll settlement trigger? |
| **REQ-13** | Worker Salary Information & Ledger Details | `PARTIALLY_IMPLEMENTED` | `WorkerMonthlyRecord` and `WorkerAdvance` exist; math in `hr.py` | Standardize hourly vs monthly formula | Schema extensions for explicit payment breakdown | Endpoint returns side-by-side salary & advance ledger | Worker profile sidebar with financial statistics | Mathematical accuracy tests for overtime & advances | REQ-10 | MEDIUM | How is per-hour rate derived for salaried staff (divided by 208 hrs or custom)? |
| **REQ-14** | Production Gallery: Batch details, Article No, Color, Picture | `PRESENT_BUT_INCORRECT` | `ProductImage` links to `Product`, not `ProductionBatch`; color not returned in schema | Link images to `ProductionBatch` or enrich `Product` schema | Add `production_batch_id` to `product_images` or new model | Return article no, name, color, batch details in gallery | Display batch badge, article no, color in gallery cards | Gallery search and filter integration tests | REQ-05 | MEDIUM | Is the gallery for finished catalog items or actual factory lot batch photos? |
| **REQ-15** | General Expenses Module | `MISSING` | Zero models, routers, or components exist | Build full Expense service & repository | New table `expenses` with category, date, payment mode | Endpoints `GET, POST, DELETE /api/v1/expenses` | Build ExpensesView with summary cards and ledger | Tenant isolation, precision, and CRUD tests | None | MEDIUM | Should expenses link to financial accounts/chart of accounts? |
| **REQ-16** | Sales Expenses (S.N., Date, Particular, Amount, Remarks) | `MISSING` | Zero models or components exist | Add sales expense classification or order linkage | New table `sales_expenses` or filtered `expenses` | Endpoints for sales expense entry & reporting | Dedicated Sales Expenses tab in Sales or Expense view | Decimal precision and export tests | REQ-15 | LOW | Are sales expenses deducted from sales profit or general overhead? |
| **REQ-17** | Purchase Expenses (Carrying-in, Duty, China Exp, Insurance) | `MISSING` | Handwritten receipt format provided; no model or schema exists | Implement landed cost tracking & expense breakdown | New table `purchase_expenses` with specific cost columns | Endpoint `POST /purchase/{id}/expenses` & standalone | Dedicated Purchase Expenses table view per client format | Financial totalization tests across 4 expense columns | REQ-A3, REQ-07 | HIGH | Are purchase expenses capitalized into raw material inventory cost or expensed? |
| **REQ-18** | Fixed Assets Register (Item, Quantity, Total Amount) | `MISSING` | Zero models or components exist | Build basic Asset register service | New table `fixed_assets` with acquisition date, cost, qty | Endpoints `GET, POST, DELETE /api/v1/fixed-assets` | Build FixedAssetsView with total asset valuation card | Asset addition, calculation, and deletion tests | None | LOW | Is depreciation calculation required, or strictly a basic asset register? |
| **REQ-19** | Waste Material Management | `MISSING` | Zero scrap or waste tracking exists | Build waste logging logic deducting stock | New table `waste_records` linked to batch or raw material | Endpoint `POST /production/waste` and `GET /waste` | Build WasteManagementView with batch/material dropdown | Concurrency tests on inventory deduction from waste | REQ-06, REQ-07 | MEDIUM | Does waste scrap reduce raw material stock, finished goods, or WIP? |
| **REQ-20** | Automatic Daily Database Backup | `PARTIALLY_IMPLEMENTED` | `app/services/backup_service.py` executes pg_dump & S3 upload; no scheduler | Add automated background scheduler or systemd cron | Add backup log record table if not present | Endpoint `GET /system/backups` to inspect daily runs | Admin backup dashboard showing daily success/failure | Automated backup execution and verification test | None | MEDIUM | What is the retention policy (e.g., 30 days) and target offsite bucket? |

---

## 4. Already Implemented

The following features were verified as functioning end-to-end and meeting operational standards:

1. **Dual Date Storage Foundation (BS/AD):**
   - Core tables (`sales_orders`, `invoices`, `production_batches`, `stock_movements`, `purchases`) store both `date_ad` (ISO YYYY-MM-DD) and `date_bs` (Bikram Sambat string).
   - Frontend components seamlessly leverage `NepaliDatePicker.tsx` and `lib/nepaliDate.ts` (lookup table spanning 2000–2090 BS).
2. **Finished Goods Stock Ledger:**
   - `models/stock.py` (`StockMovement` table) records append-only finished footwear inventory transactions (+1 for production/returns, -1 for sales).
   - Protected by PostgreSQL row-level advisory locks (`acquire_stock_mutation_lock`, `acquire_stock_advisory_lock`) in `backend/app/core/locks.py` preventing race conditions.
3. **Worker Advance Ledger:**
   - `models/worker.py` (`WorkerAdvance` table) accurately tracks advances issued (`ISSUED`) and recovered (`RECOVERED`).
   - `backend/app/api/v1/hr.py` calculates real-time net outstanding advance (`issued - recovered`) in `_calculate_outstanding_advance()`.
4. **Monthly Worker Payroll Calculation:**
   - `models/worker.py` (`WorkerMonthlyRecord`) tracks total working hours, overtime hours, gross pay, advance deductions, and net paid.
   - `POST /api/v1/hr/monthly-payroll` computes gross pay for salaried staff (base + 1.5x OT) and wage workers (hours * rate + 1.5x OT) and auto-generates advance recovery entries upon payment.
5. **Secure Product Image Storage:**
   - `backend/app/api/v1/gallery.py` implements secure upload, magic byte validation (`\xff\xd8\xff`, `\x89PNG`, `RIFF...WEBP`), MIME type checks, and directory traversal defense (`_safe_resolve_image_path`).

---

## 5. Partially Implemented

These features exist in some layers of the stack but have concrete gaps:

1. **Raw Material Stock:**
   - `models/purchase.py` has `RawMaterial` master with `code`, `name`, `unit`, `min_stock_alert`.
   - **Gap:** Stock is purely virtual math (`check_raw_material_stock` in `backend/app/api/v1/production.py` calculates `SUM(Purchase.quantity) - SUM(ProductionMaterialUsage.quantity_used)`). There is no raw material ledger table, no warehouse assignment, and no physical count adjustment.
2. **Raw Material Units:**
   - `RawMaterial.unit` exists as `String(50)` defaulting to `"kg"`.
   - **Gap:** No backend validation restricting units to the client's mandatory set (`kg`, `pcs`, `litre`). Users can enter arbitrary strings.
3. **Worker Profile:**
   - Worker list displays code, name, phone, join date, pay type, rate, hours, advance due, and active badge.
   - **Gap:** Worker photos, temporary addresses, permanent addresses, and citizenship documents are completely absent from model and UI.
4. **Worker Active / Inactive Workflow:**
   - `Worker.is_active` boolean and filter tabs exist in `HRManagementView.tsx`.
   - **Gap:** Toggling status is an unconfirmed click. There is no `inactive_date` column, no deactivation audit reason, and no dedicated inactive worker view.
5. **Production Gallery:**
   - Product gallery allows uploading and viewing images linked to `products.id`.
   - **Gap:** Gallery items do not return or display product color, nor are they linked to specific `production_batches.id`.
6. **Automatic Daily Backup:**
   - `app/services/backup_service.py` provides complete logic for PostgreSQL pg_dump, encryption, and S3/B2 uploading.
   - **Gap:** Execution is currently manual via API; no automated daily OS cron or background task scheduler is scheduled.

---

## 6. Present but Incorrect

1. **Color Handling on Production Batches:**
   - In `models/stock.py`, `color` is a property of the `Product` SKU.
   - In `models/production.py`, `ProductionBatch` only references `product_id`.
   - **Flaw:** The client requested that Color be manually typable during batch entry. In a footwear ERP, if an operator enters a color (e.g., "Navy Blue") that differs from the catalog product's color (e.g., "Black"), the resulting finished goods stock will be misattributed to the wrong SKU unless a new SKU variant is created or color is decoupled. Free-text entry also causes casing duplication ("Black", "black", "BLACK").
2. **Sales Order Stock Deduction Timing:**
   - In `backend/app/api/v1/sales.py`, stock is deducted immediately when `delivered=True` upon order creation.
   - **Flaw:** If an order is taken for future delivery (`delivered=False`), status becomes "pending", but there is **no dispatch endpoint or dispatch document** in the backend to record the actual dispatch date and execute the inventory deduction later.
3. **Purchase Document Lifecycle:**
   - `models/purchase.py` treats `Purchase` as an instant inventory addition.
   - **Flaw:** The client requested tracking **Ordered Date** and **Receipt Date**. In real manufacturing, materials are ordered weeks before physical arrival at the factory gate. Adding stock on the ordered date inflates physical inventory before goods arrive.

---

## 7. Missing

The following requested domains have **no existing implementation** in the codebase:

1. **Dispatch Date Field & Workflow:** Neither `SalesOrder` nor `StockMovement` tracks a separate dispatch date.
2. **Purchase Order Date Split:** `Purchase` only contains `purchase_date_ad/bs`; no ordered date vs receipt date.
3. **Worker Citizenship Documents:** No model, storage directory, or API exists for uploading and securing worker citizenship identity cards.
4. **General Expenses Module:** No model, table, API router, or frontend page exists for company operating expenses.
5. **Sales Expenses Table:** No ledger or view exists for tracking sales-related expenses (`S.N.`, `Date`, `Particular`, `Amount`, `Remarks`).
6. **Purchase Expenses Table:** No ledger exists for the client's handwritten expense categories (`Carrying-in Exp`, `Import Duty Tax`, `China Carrying-in Exp`, `Insurance`).
7. **Fixed Assets Register:** No asset register exists for recording machinery, tools, vehicles, or total asset values.
8. **Waste Material Tracking:** No scrap, trim, or defective material ledger exists to write off wasted raw materials or finished goods.

---

## 8. Duplicate Existing Functionality

- **Worker Advance Management:** The client requested tracking advances, pending advances, and advance deductions. This already exists in full precision within `models/worker.py` (`WorkerAdvance`) and `api/v1/hr.py`. A new advance table must **not** be created; the existing ledger should simply be surfaced in the requested profile views.
- **Worker Hours & Payroll:** The client requested total working hours, basic salary, net salary, and salary status. These exist in `WorkerMonthlyRecord`. We must avoid duplicating these fields on the `Worker` master table.
- **Document Numbering:** Any new documents (Purchase Orders, Dispatches, Expense Vouchers, Asset Tags) must use the existing `generate_document_number()` sequence utility in `backend/app/core/sequence.py` rather than ad-hoc numbering logic.

---

## 9. Cross-Module Dependencies

### 9.1 Procurement & Inbound Supply Flow
```text
Purchase Order (Ordered Date)
       ↓
Goods Receipt (Receipt Date) ───► Purchase Expenses (Duty, Freight, Insurance)
       ↓                                    │
Raw Material Stock Ledger (+ IN) ◄──────────┘ (Optional Capitalization)
       ↓
Production Consumption (- OUT)
```

### 9.2 Manufacturing & Outbound Sales Flow
```text
Raw Material Stock Ledger (- OUT)
       ↓
Production Batch (Article No, Typable Color, Serial No)
       ├─► Production Gallery (Batch Photo + Details)
       └─► Waste Material (- Scrap / Waste write-off)
       ↓
Finished Goods Stock Ledger (+ IN)
       ↓
Sales Order (Order Date)
       ↓
Dispatch / Delivery (Dispatch Date) ───► Sales Expenses (Freight, Particulars)
       ↓
Finished Goods Stock Ledger (- OUT)
       ↓
Tax Invoice & Accounts Receivable Ledger
```

### 9.3 HR, Attendance & Payroll Flow
```text
Worker Master (Bio, Picture, Citizenship, Addresses, Active/Inactive)
       │
       ├─► Floor Production (Worker Count on Batches)
       │
       ├─► Monthly Hours Log (Total Working Hours + Overtime)
       │
       ├─► Worker Advances (+ ISSUED / - RECOVERED)
       │
       └─► Monthly Payroll Finalization
                 ↓
           Gross Pay (Hours * Rate or Monthly Base)
         - Advance Deduction (Recovered)
         ─────────────────────────────────────────
         = Net Salary Paid (CASH / BANK)
```

---

## 10. Database Impact Analysis

To satisfy all validated gaps without disrupting existing production data, the following schema migrations (`alembic`) will be needed:

### New Tables Required
1. `raw_material_movements`
   - `id`: BigInteger PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `raw_material_id`: Integer FK (`raw_materials.id`, indexed)
   - `warehouse_id`: Integer FK (`warehouses.id`)
   - `quantity`: Numeric(12, 4) NOT NULL
   - `direction`: SmallInteger (+1 or -1) NOT NULL
   - `movement_type`: String(32) ('PURCHASE_RECEIPT', 'PRODUCTION_USAGE', 'WASTE_SCRAP', 'ADJUSTMENT')
   - `source_doc_ref`: String(64)
   - `date_ad`: String(10), `date_bs`: String(10)
   - `created_at`: DateTime(timezone=True)
2. `expenses`
   - `id`: Integer PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `expense_type`: String(32) ('GENERAL', 'SALES')
   - `expense_date_ad`: String(10), `expense_date_bs`: String(10)
   - `particular`: String(255) NOT NULL
   - `amount_paisa`: BigInteger NOT NULL
   - `payment_mode`: String(32) ('CASH', 'BANK', 'CHEQUE')
   - `remarks`: Text nullable
   - `sales_order_id`: Integer FK (`sales_orders.id`, nullable)
   - `created_by`: Integer FK (`users.id`)
   - `created_at`: DateTime(timezone=True)
3. `purchase_expenses`
   - `id`: Integer PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `purchase_id`: Integer FK (`purchases.id`, nullable)
   - `expense_date_ad`: String(10), `expense_date_bs`: String(10)
   - `particular`: String(255) NOT NULL
   - `carrying_in_paisa`: BigInteger DEFAULT 0
   - `import_duty_paisa`: BigInteger DEFAULT 0
   - `china_carrying_paisa`: BigInteger DEFAULT 0
   - `insurance_paisa`: BigInteger DEFAULT 0
   - `total_paisa`: BigInteger NOT NULL
   - `remarks`: Text nullable
   - `created_at`: DateTime(timezone=True)
4. `fixed_assets`
   - `id`: Integer PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `asset_code`: String(32) NOT NULL
   - `item_name`: String(255) NOT NULL
   - `purchase_date_ad`: String(10), `purchase_date_bs`: String(10)
   - `quantity`: Integer DEFAULT 1 NOT NULL
   - `unit_cost_paisa`: BigInteger NOT NULL
   - `total_amount_paisa`: BigInteger NOT NULL
   - `location`: String(128) nullable
   - `remarks`: Text nullable
   - `created_at`: DateTime(timezone=True)
5. `waste_materials`
   - `id`: Integer PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `waste_date_ad`: String(10), `waste_date_bs`: String(10)
   - `source_type`: String(32) ('RAW_MATERIAL', 'PRODUCTION_BATCH')
   - `raw_material_id`: Integer FK (`raw_materials.id`, nullable)
   - `production_batch_id`: Integer FK (`production_batches.id`, nullable)
   - `quantity`: Numeric(12, 4) NOT NULL
   - `unit`: String(20) NOT NULL
   - `reason`: String(255) NOT NULL
   - `estimated_loss_paisa`: BigInteger DEFAULT 0
   - `created_at`: DateTime(timezone=True)
6. `worker_documents`
   - `id`: Integer PK
   - `company_id`: Integer FK (`companies.id`, indexed)
   - `worker_id`: Integer FK (`workers.id`, indexed)
   - `document_type`: String(32) ('CITIZENSHIP_FRONT', 'CITIZENSHIP_BACK', 'PHOTO')
   - `file_path`: String(512) NOT NULL
   - `file_name`: String(255) NOT NULL
   - `mime_type`: String(64) NOT NULL
   - `file_size_bytes`: Integer NOT NULL
   - `created_at`: DateTime(timezone=True)

### Alterations to Existing Tables
1. `workers`:
   - ADD `photo_url`: String(512) nullable
   - ADD `temp_address`: String(255) nullable
   - ADD `perm_address`: String(255) nullable
   - ADD `inactive_date`: Date nullable
   - ADD `deactivation_reason`: String(255) nullable
2. `sales_orders`:
   - ADD `dispatch_date_ad`: String(10) nullable
   - ADD `dispatch_date_bs`: String(10) nullable
3. `purchases`:
   - ADD `ordered_date_ad`: String(10) nullable
   - ADD `ordered_date_bs`: String(10) nullable
   - ADD `receipt_date_ad`: String(10) nullable
   - ADD `receipt_date_bs`: String(10) nullable
   - ADD `status`: String(32) DEFAULT 'received'
4. `production_batches`:
   - ADD `batch_serial_no`: String(64) nullable
   - ADD `custom_color`: String(50) nullable
5. `raw_materials`:
   - ADD CHECK constraint `chk_raw_material_unit` ON `unit IN ('kg', 'pcs', 'litre')`

---

## 11. Backend & API Impact Analysis

### New API Endpoints Required
- **Expenses Router (`/api/v1/expenses`):**
  - `GET /` — List expenses with date, type, and pagination filters.
  - `POST /` — Record general or sales expense with integer paisa validation.
  - `DELETE /{id}` — Soft delete or remove expense (Editor/Admin only).
- **Purchase Expenses Router (`/api/v1/purchase/expenses`):**
  - `GET /` — List purchase landed expenses with column breakdown.
  - `POST /` — Create 4-column purchase expense record.
- **Fixed Assets Router (`/api/v1/fixed-assets`):**
  - `GET /` — List assets with total asset valuation summary.
  - `POST /` — Register new fixed asset.
  - `DELETE /{id}` — Remove disposed asset.
- **Waste Management Router (`/api/v1/production/waste`):**
  - `GET /` — List waste/scrap logs.
  - `POST /` — Record waste with atomic stock write-off movement.
- **Worker Documents & Profile (`/api/v1/hr/workers`):**
  - `POST /{id}/documents` — Upload citizenship or profile picture with strict MIME checks.
  - `GET /{id}/documents/{doc_id}/download` — Stream secure file with tenant isolation and HR authorization.
  - `POST /{id}/status` — Transition worker active/inactive with confirmation and date.
- **Sales Dispatch (`/api/v1/sales/orders`):**
  - `POST /{id}/dispatch` — Execute deferred dispatch: updates `dispatch_date` and triggers `StockMovement(direction=-1, movement_type='SALES_OUT')`.

---

## 12. Frontend Impact Analysis

### Modifications to Existing Views
1. **`HRManagementView.tsx`:**
   - Add worker thumbnail column next to Worker Code.
   - Convert table row click to open a comprehensive **Worker Profile Modal** displaying:
     - Worker Avatar, Name, Employee ID, Phone.
     - Temporary Address & Permanent Address.
     - Citizenship Front/Back preview with zoom modal.
     - Working hours KPI, Basic salary, Hourly rate, Advance due, Net salary status.
   - Replace active/inactive toggle with a modal confirmation asking for `inactive_date` and confirmation.
   - Add dedicated "Inactive Workers" tab with reactivation confirmation.
2. **`ProductionView.tsx`:**
   - Update continuous batch entry dock to support `Color` input (with auto-suggest from existing product colors plus free-text capability).
   - Display `Serial No.` alongside `Batch No.`.
3. **`PurchaseView.tsx`:**
   - Split single date input into `Ordered Date` and `Receipt Date` with dual BS/AD pickers.
   - Enforce unit selection dropdown (`kg`, `pcs`, `litre`).
4. **`ProductGalleryView.tsx`:**
   - Update cards to display `Article No.`, `Product Name`, and `Color`.
   - Add filter by Color.
5. **`SalesInvoiceView.tsx`:**
   - Add `Dispatch Date` field to order entry.
   - For pending orders, add a prominent "Dispatch Order" action button that prompts for dispatch date and confirms stock reduction.

### New Frontend Views / Tabs Required
1. **Expenses View (`components/ExpensesView.tsx`):**
   - General Expenses table.
   - Sales Expenses table (`S.N.`, `Date`, `Particular`, `Amount`, `Remarks`).
   - Summary cards: Total General Expenses, Total Sales Expenses, Month-to-date.
2. **Purchase Expenses View (`components/PurchaseExpensesView.tsx`):**
   - Custom table replicating the client's handwritten format:
     `S.N. | Date | Particular | Carrying-in Exp. | Import Duty Tax | China Carrying-in Exp. | Insurance | Total`
3. **Fixed Assets View (`components/FixedAssetsView.tsx`):**
   - Asset inventory table: `S.N. | Asset Code | Item Name | Date | Quantity | Unit Cost | Total Amount | Location`
   - Top KPI card: Total Capital Assets Valuation.
4. **Waste Material View (`components/WasteMaterialView.tsx`):**
   - Waste logging form and table: `Date | Material / Batch | Quantity | Unit | Reason | Est. Loss`.

---

## 13. Security Considerations

1. **Citizenship Documents are Sensitive PII:**
   - Storing citizenship images requires high security.
   - Files must be stored in a dedicated directory outside the public web root (`static/uploads/private/workers/`).
   - Access to `/api/v1/hr/workers/{id}/documents/...` must be strictly restricted to authenticated users with `role IN ('admin', 'editor')`. Viewers or unauthenticated callers must receive 403 Forbidden.
   - All file downloads must use `_safe_resolve_image_path()` to prevent path traversal attacks.
   - Uploads must strictly validate magic header bytes (JPEG `\xff\xd8\xff`, PNG `\x89PNG`, WEBP) and enforce a 5MB size limit.
2. **Multi-Tenant Scoping:**
   - Every new table (`expenses`, `purchase_expenses`, `fixed_assets`, `waste_materials`, `worker_documents`, `raw_material_movements`) must have an indexed `company_id` column and enforce `TenantRepository` scoping.
3. **Financial Precision Protection:**
   - All newly introduced expense, asset, and payroll amount fields must use integer paisa (`BigInteger`) or quantized Decimal to prevent floating-point rounding exploits.

---

## 14. Financial & Accounting Considerations

1. **Purchase Expenses — Inventory Capitalization vs. Period Expensing:**
   - **Critical Accounting Decision:** Does the client want the 4 purchase expense categories (`Carrying-in`, `Import Duty`, `China Carrying-in`, `Insurance`) added to the raw material's valuation (landed cost), or booked as general factory operating expenses?
   - If capitalized, raw material unit cost becomes:  
     $$\text{Landed Unit Cost} = \text{Purchase Price} + \frac{\text{Total Purchase Expenses}}{\text{Purchased Quantity}}$$
   - This directly alters the manufacturing cost of goods sold (COGS) and inventory valuation reports.
2. **Advance Deduction Timing:**
   - When payroll is finalized and marked as `PAID`, the auto-recovery of advances must remain atomic within the database transaction to prevent double recovery or phantom balances.
3. **Fixed Assets Depreciation:**
   - The client requested items and total amounts. Depreciation was not verbally requested. We recommend keeping it as a pure asset cost register unless depreciation accounting is explicitly requested.

---

## 15. Inventory Integrity Considerations

1. **Transitioning Raw Materials to an Immutable Ledger:**
   - Currently, raw material available stock is dynamically calculated from purchases minus production usages.
   - Moving to a dedicated `raw_material_movements` ledger guarantees auditability, supports stock write-offs (waste), and enables physical inventory count adjustments.
   - Existing purchase and production data must be preserved and accurately backfilled into the initial ledger state.
2. **Color Normalization on Footwear SKUs:**
   - Allowing free-text typable colors in production batches introduces the risk of orphan stock.
   - **Recommended Architecture:** When a user types a new color during batch creation, the system should either:
     1. Automatically prompt to create/bind a new product SKU variant with that color, OR
     2. Treat color as an informational batch lot attribute while tracking stock under the parent footwear model, OR
     3. Normalize the color string (e.g. trim and Title Case: "black" -> "Black") and verify against catalog variants.
3. **Deferred Sales Dispatch:**
   - Allowing orders to be created with `delivered=False` requires locking inventory when dispatch occurs.
   - If stock is not reserved at order time, an order may fail to dispatch later due to insufficient stock. The client must clarify if orders should allocate/reserve stock upon creation.

---

## 16. Backup & Infrastructure Considerations

1. **Current Status:** `backend/app/services/backup_service.py` executes pg_dump, encrypts via AES-GCM, and uploads to S3/Backblaze B2.
2. **Gap:** Currently requires manual invocation.
3. **Recommended Implementation:**
   - Deploy an OS-level cron job or Docker container sidecar running daily at 02:00 AM NPT:
     ```bash
     0 2 * * * curl -X POST http://localhost:8000/api/v1/system/backup -H "Authorization: Bearer ${BACKUP_TOKEN}"
     ```
   - Retain 7 daily snapshots, 4 weekly snapshots, and 12 monthly snapshots.
   - Store backup logs in database table `backup_logs` to display status on the admin dashboard.

---

## 17. Testing Impact Analysis

Any proposed implementation must maintain the existing test suite (266 passed tests) and introduce new test suites across:

1. **Unit Tests:**
   - Nepali Date BS leap-year, month boundary, and converter tests.
   - Hourly wage and salaried overtime computation tests.
   - Purchase expense totalization and landed cost math tests.
   - Raw material unit enum validation tests (`kg`, `pcs`, `litre`).
2. **Integration Tests:**
   - Multi-tenant isolation tests for `/api/v1/expenses`, `/api/v1/fixed-assets`, `/api/v1/purchase/expenses`, and `/api/v1/production/waste`.
   - Deferred sales dispatch: verify stock movements (-1 OUT) are created only upon dispatch execution.
   - Purchase receipt: verify stock movements (+1 IN) are created only upon goods arrival.
   - Worker document upload, MIME check, and 5MB size limit validation.
3. **Concurrency & Race Condition Tests:**
   - Concurrent sales dispatches exhausting stock.
   - Concurrent worker advance issuance and payroll deductions.
4. **Security Tests:**
   - Path traversal defense on worker citizenship downloads.
   - Role-based authorization tests preventing viewers from accessing citizenship images or expenses.

---

## 18. Client Clarifications Required

Before implementing any code or migrations, the following items must be confirmed with the client:

1. **Purchase Expenses Capitalization:**
   > *Should Carrying-in Exp, Import Duty Tax, China Carrying-in Exp, and Insurance be added to the raw material's purchase cost (landed cost) to increase inventory valuation, or should they remain separate expense records?*
2. **Production Batch Color Entry:**
   > *When a color is manually typed in a production batch (e.g. "Royal Blue"), should it automatically register as a new product color variant in your shoe catalog, or is it only a label for that specific batch?*
3. **Sales Order Stock Reservation:**
   > *When a sales order is created with a future dispatch date, should stock be reserved immediately (preventing other orders from taking it), or should stock only be checked and deducted on the day of dispatch?*
4. **Raw Material Units & Conversion:**
   > *Are raw material purchases strictly recorded in `kg`, `pcs`, and `litre`, or will you ever receive materials in grams or rolls that require automatic unit conversion?*
5. **Fixed Assets Depreciation:**
   > *Do you need monthly depreciation calculated on your fixed assets (machinery, tools), or do you only need a register of what items you own and their purchase amounts?*
6. **Worker Profile Photos & Citizenship Storage:**
   > *Will worker citizenship pictures be uploaded as two separate photos (Front and Back), or as a single document/PDF?*
7. **Waste Material Scope:**
   > *Does waste material represent scrap raw materials (e.g. leather offcuts, glue spillage), defective finished shoes, or both?*

---

## 19. Recommended Implementation Order

To avoid circular dependencies, changes must be rolled out in this specific sequence:

```text
Phase 1: Date & Metadata Foundations
  └── Extend Sales & Purchase schemas with Ordered/Receipt/Dispatch dates.
  └── Add Raw Material Unit validation ('kg', 'pcs', 'litre').

Phase 2: Inbound Supply & Raw Material Ledger
  └── Implement dedicated Raw Material stock ledger.
  └── Build PO Receipt workflow and stock update (+ IN).
  └── Build Purchase Expenses (Carrying-in, Duty, China Exp, Insurance).

Phase 3: Outbound Sales & Dispatch
  └── Build Sales Dispatch endpoint and stock deduction (- OUT).
  └── Build Sales Expenses table.

Phase 4: Manufacturing, Color & Waste
  └── Enhance Production Batch with serial number and normalized color.
  └── Build Waste Material tracking with inventory deductions.
  └── Link Production Gallery to color and batch details.

Phase 5: HR, Worker Profile & Documents
  └── Add worker photos, addresses, and inactive dates.
  └── Build secure citizenship document upload with RBAC.
  └── Build comprehensive Worker Profile modal and Inactive view.

Phase 6: General Expenses & Fixed Assets
  └── Build General Expenses module.
  └── Build Fixed Assets register and valuation summary.

Phase 7: Infrastructure & Automated Daily Backup
  └── Configure daily scheduled backup runner and monitoring dashboard.

Phase 8: End-to-End Verification & Client UAT
  └── Execute complete regression test suite and client workflow drills.
```

---

## 20. Risks

1. **Risk of Inventory Divergence (High):**
   - Splitting purchase order date from receipt date, and sales order date from dispatch date, changes the exact timestamp when stock moves. If staff enter dispatches retroactively without date safeguards, historical stock snapshots could become inconsistent.
2. **Risk of Color Variant Duplication (Medium):**
   - Free-text color input will lead to variations like "Black", "black", "BLACK", "Charcoal Black". If not normalized, inventory reports will split single shoes across multiple SKUs.
3. **Risk of Sensitive Document Exposure (High):**
   - Worker citizenship documents are legally protected personal identity data. Failing to enforce strict RBAC and directory traversal protections could expose identity documents.
4. **Risk of Accounting Misstatement (Medium):**
   - Improperly handling the 4 purchase expense categories could either understate raw material inventory asset values or distort profit-and-loss statements.

---

## 21. Files and Modules That Will Need Modification

### Backend Files
- `backend/app/models/worker.py` (add photo, addresses, inactive_date)
- `backend/app/models/purchase.py` (add ordered/receipt dates, status; unit validation)
- `backend/app/models/sales.py` (add dispatch_date_ad/bs)
- `backend/app/models/production.py` (add batch_serial_no, custom_color)
- `backend/app/models/gallery.py` (add production_batch_id, color linkage)
- `backend/app/models/expense.py` (*NEW* — general, sales, purchase expenses)
- `backend/app/models/asset.py` (*NEW* — fixed assets)
- `backend/app/models/waste.py` (*NEW* — waste materials)
- `backend/app/models/raw_material_movement.py` (*NEW* — raw material ledger)
- `backend/app/api/v1/hr.py` (add profile, document upload, status endpoints)
- `backend/app/api/v1/purchase.py` (add receipt workflow, purchase expenses)
- `backend/app/api/v1/sales.py` (add dispatch endpoint)
- `backend/app/api/v1/production.py` (update batch creation, add waste logging)
- `backend/app/api/v1/gallery.py` (return color and batch info)
- `backend/app/api/v1/expenses.py` (*NEW* router)
- `backend/app/api/v1/assets.py` (*NEW* router)
- `alembic/versions/` (*NEW* migration scripts)

### Frontend Files
- `frontend/src/components/HRManagementView.tsx` (worker profile modal, avatar, inactive workflow)
- `frontend/src/components/PurchaseView.tsx` (ordered vs receipt dates, unit select)
- `frontend/src/components/ProductionView.tsx` (typable color, serial number)
- `frontend/src/components/SalesInvoiceView.tsx` (dispatch date, dispatch action button)
- `frontend/src/components/ProductGalleryView.tsx` (display color and batch metadata)
- `frontend/src/components/ExpensesView.tsx` (*NEW* component)
- `frontend/src/components/PurchaseExpensesView.tsx` (*NEW* component)
- `frontend/src/components/FixedAssetsView.tsx` (*NEW* component)
- `frontend/src/components/WasteMaterialView.tsx` (*NEW* component)
- `frontend/src/components/DashboardLayout.tsx` (add navigation items for Expenses, Assets, Waste)

---

## 22. Proposed Implementation Phases

### Phase 1: Data Model & Date Foundation
- Add Alembic migration for date fields (`dispatch_date` on sales, `ordered_date`/`receipt_date` on purchase).
- Enforce unit validation on `RawMaterial` (`kg`, `pcs`, `litre`).
- Verify no regressions against existing 266 tests.

### Phase 2: Purchase, Raw Material Ledger & Purchase Expenses
- Create `raw_material_movements` ledger table.
- Implement Goods Receipt endpoint triggering raw material stock addition (+ IN).
- Implement Purchase Expenses table and API adhering to the client's 4-column format.

### Phase 3: Sales, Dispatch & Sales Expenses
- Implement Sales Order Dispatch endpoint triggering finished goods stock deduction (- OUT) on dispatch date.
- Implement Sales Expenses table and API.

### Phase 4: Production Batch, Waste & Gallery
- Add serial number and normalized color handling to `ProductionBatch`.
- Implement Waste Material tracking deducting raw materials or batch output.
- Update Product Gallery schema to return color and production batch details.

### Phase 5: HR, Worker Profile & Documents
- Add photo, addresses, and inactive date to `Worker`.
- Implement secure citizenship upload and retrieval endpoints with RBAC.
- Build interactive Worker Profile Modal and dedicated Inactive Workers view in frontend.

### Phase 6: General Expenses & Fixed Assets
- Implement General Expenses CRUD with integer paisa precision.
- Implement Fixed Assets register and total valuation summary.
- Add frontend views and integrate into main navigation.

### Phase 7: Infrastructure & Automated Daily Backup
- Configure scheduled daily backup cron job.
- Expose backup audit logs in system dashboard.

### Phase 8: Verification, Security Audit & Client Acceptance
- Run full automated test suite with new tests for all added endpoints.
- Conduct simulated client lifecycle drill across procurement, production, sales, payroll, and expenses.

---

## 23. Final Executive Summary Table (Section 28)

| Requirement | Status | Effort | Risk | Dependencies | Client Clarification |
|---|---|---|---|---|---|
| **Nepali Date** | `PARTIALLY_IMPLEMENTED` | Low | Low | None | Confirm AD canonical DB storage, BS display. |
| **Dispatch Date** | `MISSING` | Medium | Medium | REQ-06 | Partial shipments or full dispatch only? |
| **Purchase Ordered/Receipt Date** | `MISSING` | Medium | Medium | REQ-06, REQ-07 | Is PO issued in advance of supplier billing? |
| **Sales Ordered/Dispatch Date** | `PARTIALLY_IMPLEMENTED` | Low | Low | REQ-06 | Does dispatch date default to order date? |
| **Production Batch Fields** | `PRESENT_BUT_INCORRECT` | Medium | High | Finished Stock | Does typable color create a new SKU variant? |
| **Automatic Stock Update** | `PRESENT_BUT_INCORRECT` | High | High | REQ-A2, REQ-A3 | Should negative stock be strictly blocked? |
| **Raw Material Stock** | `PARTIALLY_IMPLEMENTED` | High | Medium | REQ-06 | Single storeroom or multiple warehouses? |
| **Raw Material Units** | `PARTIALLY_IMPLEMENTED` | Low | Low | None | Are unit conversions needed (e.g. g -> kg)? |
| **Worker Profile** | `PARTIALLY_IMPLEMENTED` | Medium | Medium | REQ-09, REQ-11 | Display monthly equivalent or floor hours? |
| **Worker Documents** | `MISSING` | Medium | High | REQ-10 | Single document or separate Front/Back photos? |
| **Worker Active/Inactive** | `PARTIALLY_IMPLEMENTED` | Low | Low | None | Does deactivation trigger final salary settlement? |
| **Worker Salary Data** | `PARTIALLY_IMPLEMENTED` | Medium | Medium | REQ-10 | How is per-hour rate derived for salaried staff? |
| **Production Gallery** | `PRESENT_BUT_INCORRECT` | Medium | Low | REQ-05 | Show catalog shoe or actual factory lot photo? |
| **General Expenses** | `MISSING` | Medium | Medium | None | Link expenses to chart of accounts? |
| **Sales Expenses** | `MISSING` | Low | Low | REQ-15 | Deduct from sales margin or general overhead? |
| **Purchase Expenses** | `MISSING` | High | High | REQ-A3, REQ-07 | Capitalize into inventory or period expense? |
| **Fixed Assets** | `MISSING` | Low | Low | None | Is depreciation calculation required? |
| **Waste Material** | `MISSING` | Medium | Medium | REQ-06, REQ-07 | Does waste reduce raw materials, WIP, or shoes? |
| **Daily Backup** | `PARTIALLY_IMPLEMENTED` | Low | Low | None | Confirm retention days and target cloud bucket. |

---

### Recommended Implementation Sequence
```text
Phase 1 — Data Model & Date Foundation (Low Risk, Schema Setup)
Phase 2 — Inbound Purchase / Raw Material Ledger / Purchase Expenses (Inventory & Landed Cost)
Phase 3 — Outbound Sales / Dispatch / Sales Expenses (Revenue & Stock Out)
Phase 4 — Production / Normalized Color / Waste / Gallery (Manufacturing Floor)
Phase 5 — HR / Worker Profile / Documents / Inactive Workflow (Staff & Payroll)
Phase 6 — General Expenses / Fixed Assets (Financial Overhead & Assets)
Phase 7 — Backup / Infrastructure Automation (SRE & Operations)
Phase 8 — Regression / Security / Client Acceptance Testing (Quality Gates)
```
