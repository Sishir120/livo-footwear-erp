# LIVO FOOTWEAR ERP — CLIENT REQUIREMENTS IMPLEMENTATION TRACKER

**Project:** LIVO Industrial Footwear Enterprise Resource Planning (ERP)  
**Tracking Version:** 1.0.0  
**Baseline Commit:** `5caa3f471e92aece268d0fa519a920e7cc7dc512`  
**Last Updated:** 2026-10-12  

---

## 1. Master Requirements Matrix

| ID | Domain / Requirement | Status | Backend / API | Frontend Component | Database / Schema | Automated Tests | Live Browser Verification |
|---|---|---|---|---|---|---|---|
| **REQ-A** | **Bikram Sambat (BS) Calendar & Dual Dates** | **COMPLETE** | `app/core/nepali_date.py`, `POST /api/v1/*` | `NepaliDatePicker.tsx`, `lib/nepaliDate.ts` | `date_ad` (DATE), `date_bs` (VARCHAR(10)) | `test_nepali_date.py` (7/7 passed) | **VERIFIED** (`bs_calendar_ui_test`) |
| **REQ-B** | **Sales & Purchase Dates (Dispatch & Receipt)** | **COMPLETE** | `POST /sales/orders/{id}/dispatch`, `POST /purchase/purchases/{id}/receive` | `SalesInvoiceView.tsx`, `PurchaseView.tsx` | `sales_orders.dispatch_date_ad/bs`, `purchases.receipt_date_ad/bs` | `test_sales_dispatch_and_expenses.py`, `test_raw_material_ledger.py` | **VERIFIED** |
| **REQ-C** | **Production Batch Management (Color & Gallery)** | **COMPLETE** | `POST /production/batches`, `POST /gallery/upload` | `ProductionView.tsx`, `ProductGalleryView.tsx` | `production_batches.color`, `production_batches.batch_serial_no` | `test_production_batch_color_and_gallery.py` (10/10 passed) | **VERIFIED** |
| **REQ-D** | **Raw Material Inventory & Ledger** | **COMPLETE** | `GET/POST /purchase/raw-materials`, `POST /raw-materials/adjustments` | `PurchaseView.tsx`, `StockReportView.tsx` | `raw_material_movements`, `raw_materials.unit` (kg/pcs/litre) | `test_raw_material_ledger.py` (6/6 passed) | **VERIFIED** |
| **REQ-E** | **HR & Worker Profiles** | **COMPLETE** | `GET/POST /hr/workers`, `POST /hr/workers/{id}/citizenship` | `HRManagementView.tsx` | `workers.temporary_address`, `perm_address`, `worker_documents` | `test_phase_4b_hr.py` (5/5 passed) | **VERIFIED** |
| **REQ-F** | **Production Gallery** | **COMPLETE** | `GET/POST /gallery/items`, `GET /gallery/download/{id}` | `ProductGalleryView.tsx` | `product_images.production_batch_id` | `test_production_batch_color_and_gallery.py` | **VERIFIED** |
| **REQ-G** | **Expenses & Multi-Column Purchase Cost Ledger** | **COMPLETE** | `GET/POST /expenses/factory`, `GET/POST /sales/expenses`, `GET /purchase/purchases` | `PurchaseView.tsx` (Tab 3), `SalesInvoiceView.tsx` | `factory_expenses`, `sales_expenses`, `purchases` 4-column landed cost | `test_sales_dispatch_and_expenses.py`, `test_fixed_assets_waste_and_expenses.py` | **VERIFIED** |
| **REQ-H** | **Fixed Assets Register** | **COMPLETE** | `POST/GET /assets`, `POST /assets/{id}/depreciation` | `FixedAssets` module | `fixed_assets`, `fixed_asset_depreciations` (Migration `010`) | `test_fixed_assets_waste_and_expenses.py` (3/3 passed) | **VERIFIED** |
| **REQ-I** | **Waste Material Management** | **COMPLETE** | `POST/GET /waste`, `GET /waste/summary` | `WasteManagement` module | `waste_records` (Migration `010`) | `test_fixed_assets_waste_and_expenses.py` (3/3 passed) | **VERIFIED** |
| **REQ-J** | **Automatic Daily Backups** | **COMPLETE** | `app/services/backup_service.py`, `scripts/verify_backup_restore.py` | Settings Modal (Trigger & Log view) | Encrypted S3/B2 + Local fallback | `test_backup.py`, `verify_backup_restore.py` | **VERIFIED** |

---

## 2. Detailed Requirement Breakdown

### Requirement A: Bikram Sambat (BS) Calendar & Date Selection
- **Client Need:** Nepali footwear manufacturers operate predominantly on the Bikram Sambat (BS) calendar for procurement, payroll, billing, and tax documentation. The calendar must be visible, selectable, and synchronized with Gregorian (AD) dates.
- **Previous Gap:** The application previously had only raw text inputs without an interactive calendar popup. Clicking the BS date input did not display a calendar grid.
- **Implementation:**
  - Upgraded `frontend/src/components/NepaliDatePicker.tsx` to provide a full interactive dropdown calendar popup.
  - Implemented exact Bikram Sambat day-of-week header: `आइत (Sun)`, `सोम (Mon)`, `मंगल (Tue)`, `बुध (Wed)`, `बिही (Thu)`, `शुक्र (Fri)`, `शनि (Sat)` with Saturdays highlighted in red.
  - Implemented accurate month selector (1 to 12) with Nepali and English names: बैशाख (Baisakh) through चैत्र (Chaitra).
  - Implemented year selector covering BS business years 2065–2095.
  - Implemented bidirectional synchronization: selecting a BS day computes exact Gregorian (AD) date using UTC day mathematics without timezone distortion.
  - Added quick-jump to "आज (Today)" button and outside-click closing.
- **Automated Verification:**
  - `backend/tests/test_nepali_date.py`: 7 passed tests covering reference points, leap years, month boundaries, invalid dates, and bidirectional round-trips.
- **Interactive Browser Verification:**
  - Recorded session `bs_calendar_ui_test`: Navigated to Sales form, clicked calendar trigger, navigated months, selected BS date `2083-06-20`, verified synchronous AD date update to `2026-10-06`, and verified modal persistence.

---

### Requirement B: Sales & Purchase Dates
- **Client Need:** Distinguish between when a Sales Order is placed vs. when footwear is physically dispatched; distinguish between when a Purchase Order is issued vs. when raw materials physically arrive at the factory.
- **Implementation:**
  - **Sales:** Added `dispatch_date_ad` and `dispatch_date_bs` to `sales_orders`. Added dedicated `POST /api/v1/sales/orders/{id}/dispatch` endpoint that decrements physical footwear inventory only upon dispatch.
  - **Purchases:** Added `ordered_date_ad/bs` and `receipt_date_ad/bs` to `purchases`. Status lifecycle (`ORDERED` -> `RECEIVED`). Physical raw material stock increases only upon Goods Receipt Note (GRN) posting.
- **Automated Verification:**
  - `test_sales_dispatch_and_expenses.py` (8 passed)
  - `test_raw_material_ledger.py` (6 passed)

---

### Requirement C & F: Production Batches, Custom Color & Gallery
- **Client Need:** Operators dye footwear batches in custom colors on the factory floor and take lot photographs.
- **Implementation:**
  - `production_batches.color` column added as a floor lot attribute without polluting or corrupting master catalog SKUs.
  - Continuous batch entry dock allows typing custom color names with catalog autocomplete.
  - `product_images.production_batch_id` foreign key connects factory lot photos directly to the specific production run.
- **Automated Verification:**
  - `test_production_batch_color_and_gallery.py` (10 passed)

---

### Requirement D: Raw Material Stock Ledger & Units
- **Client Need:** Raw materials (leather, rubber, EVA foam, thread, glue) must have a physical ledger tracking stock movements with standard units (`kg`, `pcs`, `litre`).
- **Implementation:**
  - Implemented append-only `raw_material_movements` ledger with zero-stock floor protection.
  - Enforced unit validation (`kg`, `pcs`, `litre`).
  - Capitalized landed costs (freight, duty, insurance) into the effective unit rate of raw materials.
- **Automated Verification:**
  - `test_raw_material_ledger.py` (6 passed)

---

### Requirement E: Human Resources & Worker Profiles
- **Client Need:** Complete worker profiles with photos, temporary/permanent addresses, citizenship documents, advance deductions, and work hour tracking.
- **Implementation:**
  - Added `temporary_address`, `permanent_address`, and `photo_url` to `workers`.
  - Secure citizenship document vault (`worker_documents`) with magic-byte validation, restricted to admin role.
  - Advance repayment engine with FIFO allocation and installment recovery.
- **Automated Verification:**
  - `test_phase_4b_hr.py` (5 passed)

---

### Requirement G: Multi-Column Landed Cost & Operating Expenses
- **Client Need:** Track Carrying-in, Import Duty, China Carrying-in, and Insurance expenses in a structured ledger.
- **Implementation:**
  - Implemented 4-column landed cost breakdown in `purchases` table with integer paisa precision.
  - Implemented `sales_expenses` table for shipment, packaging, and logistics costs.
  - Integrated `PurchaseView.tsx` with dedicated Tab 3 "Landed Cost Ledger (खरिद खर्च लेजर)" featuring live bottom totals and Excel/CSV export.
- **Automated Verification:**
  - `test_sales_dispatch_and_expenses.py` (passed)
  - `test_fixed_assets_waste_and_expenses.py` (passed)

---

### Requirement H: Fixed Assets Register & Depreciation Tracking
- **Client Need:** Comprehensive fixed asset register for factory machinery, molds, cutting presses, and generators with dual-date tracking, location, condition, and straight-line/diminishing depreciation posting.
- **Implementation:**
  - `fixed_assets` table with `asset_tag`, `name`, `category`, `acquisition_date_ad/bs`, `purchase_cost_paisa`, `accumulated_depreciation_paisa`, and `book_value_paisa`.
  - Multi-tenant CRUD endpoints with role-based access control (`/api/v1/assets`).
  - Automated depreciation calculation with validation against negative net book values.
- **Automated Verification:**
  - `test_fixed_assets_waste_and_expenses.py` (passed)

---

### Requirement I: Waste Material & Scrap Management
- **Client Need:** Detailed tracking of raw material scrap, production offcuts (leather, EVA foam, rubber trimming), defect rates, disposal methods, and scrap recovery revenue.
- **Implementation:**
  - `waste_records` table linked to production batches and raw materials with unit metrics (`kg`, `pcs`).
  - Disposal tracking (`RECYCLED`, `DISPOSED`, `SOLD`) with scrap revenue logging in paisa.
  - Analytics and summary endpoint (`/api/v1/waste/summary`) grouping scrap by reason and material.
- **Automated Verification:**
  - `test_fixed_assets_waste_and_expenses.py` (passed)

---

### Requirement J: Encrypted Automated Daily Backups
- **Client Need:** Reliable automated database backups with encryption and zero-data-loss guarantees.
- **Implementation:**
  - `BackupService` with automated background scheduling, AES-256 encryption, S3/B2 cloud syncing with local fallback, and metadata status logging.
  - Verification test script (`verify_backup_restore.py`) that executes full backup-restore cycles on test databases.
- **Automated Verification:**
  - `test_backup.py` and `scripts/verify_backup_restore.py` (verified)

