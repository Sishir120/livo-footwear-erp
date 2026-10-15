# LIVO FOOTWEAR ERP — AUDIT & BASELINE REPORT
## Nepal-First UX · Bikram Sambat · Bilingual Learning System · Factory & Branch Traceability · Inventory Integrity

**Project:** LIVO Footwear ERP  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Working Directory:** `D:\Antigravity\Footwear app`  
**Current Branch:** `release/v1.0.0-staging`  
**Current HEAD SHA:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Audit Date:** 2026-10-14  
**Audit Phase:** Phase 0 (Baseline Audit and Implementation Plan)  
**Status:** COMPLETE — READ-ONLY BASELINE ESTABLISHED  

---

## 1. Executive Summary

This baseline audit evaluates the existing production-hardened **LIVO Footwear ERP** to prepare for the Master Implementation Directive:
1. **Nepal-First UX & Bikram Sambat Calendar Integration**: Establishing canonical Gregorian dates with native, bidirectional Bikram Sambat (BS) human-facing presentation.
2. **Complete Bilingual Self-Service Learning System**: Expanding beyond basic navigation translation to deliver contextual `? Help` panels, a centralized Learning Center, and complete English/Nepali operational documentation.
3. **Multi-Tier Location Hierarchy & Branch Traceability**: Extending the current single-tier warehouse model to support factory storage, production holding, dispatch transit, and multi-branch inventory with independent destination receipt confirmation.
4. **End-to-End Product & Batch Traceability**: Enabling full provenance from raw material procurement through batch production, warehouse transfers, and wholesale sales dispatch.

### Baseline Integrity Check
- **Backend Test Suite:** **369 passed**, 0 failed, 0 skipped in 129.43s (Python 3.14.7, pytest 9.1.1).
- **Frontend Type Safety:** `npx tsc --noEmit` passed with **0 errors** (TypeScript 5.4.3).
- **Alembic HEAD:** `020_fixed_assets_waste_and_expenses` + `762ea2a34ccb_convert_float_to_numeric_for_financial_` (all migrations applied).
- **Code Preservation:** Zero application source files, models, or database migrations were modified during this audit phase.

---

## 2. Current System Inventory

### 2.1 Backend Architecture
- **Framework:** FastAPI (Python 3.12+ / Python 3.14 runtime)
- **Data Access & Multi-Tenancy:** SQLAlchemy 2.0 ORM with `TenantRepository` enforcing `company_id` isolation on every query.
- **Concurrency & Advisory Locks:** PostgreSQL transaction-scoped advisory locks (`pg_advisory_xact_lock`) with deterministic 64-bit integer hashing (`hash_args_to_bigint`), falling back to process-level `threading.RLock` on SQLite test runners.
- **Financial Precision:** Integer paisa (`BigInteger`) for payroll, advances, expenses, landed costs, and fixed assets; `Decimal` with 2 decimal places (`quantize_npr`) for invoicing and statutory 13% VAT.
- **Document Numbering:** Monotonic sequences via PostgreSQL advisory locks (`allocate_next_invoice_sequence`, `generate_document_number`).

### 2.2 Database Entities & Relationships
| Entity / Model | Database Table | Primary Keys & Foreign Keys | Key Attributes & Capabilities |
|---|---|---|---|
| **Company** | `companies` | `id` (PK) | Tenant root: `name`, `code`, `created_at`. |
| **User** | `users` | `id` (PK), `company_id` (FK) | RBAC roles: `admin`, `editor`, `viewer`; failed attempt counters, lockout timestamps. |
| **Warehouse** | `warehouses` | `id` (PK), `company_id` (FK) | Single-tier location: `name`, `code`, `location`, `is_active`. (No parent location or hierarchy). |
| **Product** | `products` | `id` (PK), `company_id` (FK) | Footwear article: `code`, `name`, `category`, `size`, `color`, `unit_price`. (No direct stock column). |
| **StockMovement** | `stock_movements` | `id` (PK), `company_id`, `product_id`, `warehouse_id`, `actor_id` (FKs) | Append-only finished goods ledger: `direction` (+1/-1), `quantity`, `movement_type`, `ref_type`, `ref_id`, `date_ad`, `date_bs`. |
| **StockSnapshot** | `stock_snapshots` | `id` (PK), `company_id`, `product_id` (FKs) | Periodic balance snapshots: `snapshot_date`, `balance`, `last_movement_id`. |
| **ProductionBatch** | `production_batches` | `id` (PK), `company_id`, `product_id`, `warehouse_id` (FKs) | Assembly run: `batch_number`, `produced_quantity`, `line`, `shift`, `worker_count`, `color`, `status`. |
| **RawMaterial** | `raw_materials` | `id` (PK), `company_id` (FK) | Material master: `code`, `name`, `unit` (`kg`, `pcs`, `litre`), `current_stock`, `reorder_level`. |
| **Purchase** | `purchases` | `id` (PK), `company_id`, `supplier_id`, `raw_material_id` (FKs) | PO & Receiving: `quantity`, `unit_price`, `order_date_ad/bs`, `receipt_date_ad/bs`, 4 landed cost paisa columns. |
| **RawMaterialMovement** | `raw_material_movements` | `id` (PK), `company_id`, `raw_material_id` (FKs) | Append-only raw materials ledger: `direction`, `quantity`, `unit_cost_paisa`, `movement_type`, `reference_voucher`. |
| **SalesOrder** | `sales_orders` | `id` (PK), `company_id`, `client_id` (FKs) | Wholesale orders: `order_number`, `order_date_ad/bs`, `dispatch_date_ad/bs`, `delivered`, `carrier_name`. |
| **Invoice** | `invoices` | `id` (PK), `company_id`, `sales_order_id` (FKs) | Statutory 13% VAT tax invoice: `invoice_number`, `fiscal_year`, `taxable_amount_paisa`, `vat_amount_paisa`. |
| **Worker / Payroll** | `workers`, `worker_monthly_records`, `worker_advances` | `id` (PK), `company_id` (FK) | HR ledger: `worker_code`, temporary/permanent addresses, citizenship document, integer paisa advances. |
| **FixedAsset** | `fixed_assets` | `id` (PK), `company_id` (FK) | Headless backend: acquisition cost paisa, code, category, location. |
| **WasteRecord** | `waste_records` | `id` (PK), `company_id` (FK) | Headless backend: scrap logging for materials and rejected shoes. |
| **FactoryExpense** | `factory_expenses` | `id` (PK), `company_id` (FK) | Headless backend: operating expenses subledger. |

### 2.3 Frontend Architecture
- **Framework:** Next.js 14.1 (App Router), React 18, TypeScript 5.4.
- **Dynamic Views:** Code-split modular views loaded conditionally in `frontend/src/app/page.tsx`:
  - `DailyReportView.tsx` (Dashboard & daily operations summary)
  - `StockReportView.tsx` (Stock ledger, physical balances, warehouse picker)
  - `SalesInvoiceView.tsx` (Sales orders, dispatch modal, sequential tax invoices, sales expenses)
  - `PartyAgingView.tsx` (Accounts receivable aging analysis)
  - `ProductionView.tsx` (Production batch entry, BOM issuance, catalog combobox)
  - `PurchaseView.tsx` (PO creation, goods receipt, 4-column landed costs ledger, raw materials ledger)
  - `HRManagementView.tsx` (Worker cards/table, profile drawer, citizenship vault, advance ledger)
  - `ProductGalleryView.tsx` (Product & batch photos, bilingual cards)
  - `LeaderboardsView.tsx` (Top products, client rankings, worker ratios)
  - `SettingsView.tsx` (System diagnostics, manual backup trigger)
  - `OpsCockpitView.tsx` (Admin telemetry and system alerts)
- **Offline Sync & Caching:** IndexedDB outbox queue (`lib/offlineQueue.ts`, `lib/offlineDb.ts`) with service worker support.

---

## 3. Current Feature Status Matrix

| Domain / Feature | Status | Codebase Evidence | Findings & Architectural Gaps |
|---|:---:|---|---|
| **Nepali Date Engine** | `VERIFIED_COMPLETE` | `core/nepali_date.py`, `test_nepali_date.py` | Full BS 1979–2100 conversion engine. Dual date storage across transaction tables. |
| **Date UI Picker** | `VERIFIED_COMPLETE` | `components/NepaliDatePicker.tsx` | Interactive BS calendar grid with bilingual labels. Emits `{ ad, bs }` synchronously. |
| **Stock Ledger (Finished)** | `VERIFIED_COMPLETE` | `models/stock.py`, `api/v1/stock.py` | Append-only `StockMovement` ledger with advisory locking and zero negative stock enforcement. |
| **Stock Ledger (Raw Materials)**| `VERIFIED_COMPLETE` | `models/purchase.py`, `api/v1/purchase.py` | Append-only `RawMaterialMovement` ledger with unit cost capitalization. |
| **Production Batching** | `VERIFIED_COMPLETE` | `models/production.py`, `ProductionView.tsx` | Batch serial generation, custom typable colors, automatic BOM raw material deduction. |
| **Sales Deferred Dispatch** | `VERIFIED_COMPLETE` | `models/sales.py`, `SalesInvoiceView.tsx` | Separate order and dispatch dates. Stock deducted only upon physical dispatch. |
| **Landed Cost Breakdown** | `VERIFIED_COMPLETE` | `models/purchase.py`, `PurchaseView.tsx` | 4-column landed costs capitalized into unit rate. Matches client handwritten layout. |
| **HR & Payroll Ledger** | `VERIFIED_COMPLETE` | `models/worker.py`, `HRManagementView.tsx` | Worker profiles, addresses, confidential citizenship vault, FIFO advance recovery. |
| **Location Hierarchy** | `MISSING` | `models/stock.py:24` (`Warehouse`) | Only flat `Warehouse` table exists. Zero support for factory stores, racks, bins, or branches. |
| **Inter-Location Transfers** | `MISSING` | `models/stock.py:45` (Enum only) | Enum values `TRANSFER_IN` / `TRANSFER_OUT` exist, but zero transfer models, APIs, or UI exist. |
| **Destination Receipt Confirmation**| `MISSING` | None | No two-step transfer workflow. No tracking of in-transit inventory or transfer discrepancies. |
| **Unit Serial Tracking** | `MISSING` | None | Product inventory is tracked strictly at article/size level. Zero serial/unit tables exist. |
| **End-to-End Traceability Screen**| `MISSING` | None | No unified view to trace a batch across procurement, production, storage, transfer, and sale. |
| **Contextual Help Framework** | `MISSING` | None | No `? Help` modal, drawer, or field-level guidance components exist anywhere in the UI. |
| **Bilingual Learning Center** | `MISSING` | None | No searchable Help Center, beginner guide, or organized `docs/user-guide/` manuals. |
| **Full UI Bilingual Coverage** | `PARTIAL` | `context/LocaleContext.tsx` | ~150 navigation and header keys translated. Forms, tables, buttons, and errors remain English. |
| **Fixed Assets Screen** | `PARTIAL` | `models/asset.py`, `api/v1/assets.py` | Complete backend service with integer paisa. Zero frontend UI. |
| **Factory Expenses Screen** | `PARTIAL` | `models/sales.py`, `api/v1/factory_expenses.py`| Complete backend service. Zero frontend UI. |
| **Waste & Scrap Screen** | `PARTIAL` | `models/waste.py`, `api/v1/waste.py` | Complete backend service. Zero frontend UI. |
| **Automated Backups** | `VERIFIED_COMPLETE` | `scripts/cloud_backup.sh`, `.github/workflows/`| Nightly 01:45 NST GitHub Actions cron + in-app manual trigger in Settings. |

---

## 4. Architectural Gaps & Risks

### 4.1 Location & Transfer Gaps
1. **Flat Storage Model:** The existing `warehouses` table cannot represent a footwear manufacturing plant's physical layout:
   - Factory Raw Material Store (leather, outsoles, adhesives, eyelets)
   - Cutting & Stitching WIP
   - Assembly & Lasting Production Floor
   - Finished Goods Central Store (racks, bins)
   - Wholesale Dispatch Area
   - Multiple Branch Showrooms (e.g., Kathmandu, Pokhara, Butwal)
2. **Transfer Blindspot:** Currently, moving finished shoes from Factory to Branch requires a manual negative adjustment at the factory and a positive adjustment at the branch. This creates:
   - Lack of in-transit visibility (goods in transit vanish or appear in two places at once).
   - No independent destination receipt confirmation (branches cannot verify actual vs dispatched pairs).
   - Inability to record transit shrinkage, damage, or short-shipments.

### 4.2 Traceability Gaps
1. **Batch Provenance Disconnect:** When `ProductionBatch` is created, it writes a `StockMovement` with `ref_type='production', ref_id=batch.id`. However, subsequent sales dispatches or adjustments do **not** record `batch_id`. Once goods enter the warehouse, batch identity is severed from downstream transactions.
2. **Missing Serial Tracking:** High-value leather boots and specialized safety footwear have no individual serial number tracking.

### 4.3 Bilingual & Guidance Gaps
1. **Fragmented Vernacular:** English and Nepali terms are currently intermingled (e.g., "Carrying-in Exp (ढुवानी खर्च)").
2. **Lack of Operational Guidance:** Novice factory workers and storekeepers have no in-app documentation explaining critical concepts such as:
   - Why creating a PO does not increase stock until Goods Receipt (GRN).
   - Why sales orders must be explicitly Dispatched before stock decreases.
   - How salary advances are automatically recovered via FIFO installments.

---

## 5. Implementation Sequence & Dependency Map

To upgrade the ERP without destabilizing hardened systems, work must proceed in strictly dependency-ordered phases:

```text
Phase 1: Nepal-First Date Architecture Foundation
    ├── Preserve Gregorian canonical DB timestamps.
    └── Ensure bidirectional AD/BS conversions across all modules.

Phase 2: Complete English/Nepali Self-Service Guidance & Translation
    ├── Build shared contextual Help modal/drawer component.
    ├── Establish centralized translation dictionary with 100% UI coverage.
    └── Generate bilingual user manuals in docs/user-guide/ENGLISH/ & NEPALI/.

Phase 3: Location Hierarchy & Inventory Identity Extension
    ├── Extend location model: Organization → Factory → Warehouse → Zone → Rack/Bin → Branch.
    ├── Implement agreed tracking policy: Batch-level (size/color) + optional serial tracking.
    └── Add in-transit and damaged stock ledger states.

Phase 4: Multi-Location Transfers with Independent Destination Receipt
    ├── Build transfer state machine: DRAFT → DISPATCHED → IN_TRANSIT → RECEIVED.
    ├── Implement atomic source deduction and in-transit addition under advisory lock.
    ├── Build destination receipt verification with discrepancy logging.
    └── Provide complete transfer UI (Create, Dispatch, In-Transit, Receive).

Phase 5: Product & Batch Traceability Screen
    ├── Trace batch journey from raw material purchase to production and dispatch.
    └── Deliver unified Traceability View with filters by article, batch, and location.

Phase 6: Stock Adjustments & Exception Workflows
    ├── Provide dual physical-count and delta adjustment workflows.
    └── Enforce supervisor approvals and auditable discrepancy logging.

Phase 7: Administration, Roles & UI Completeness
    ├── Deliver screens for Fixed Assets, Factory Expenses, and Waste Management.
    └── Harden Admin Control Center and location-scoped permissions.

Phase 8: Full-Stack Regression, Concurrency & Acceptance
    └── Execute complete 369+ backend test suite and 15-step realistic footwear E2E scenario.
```

---

## 6. Audit Sign-Off

The baseline audit is **COMPLETE**. The codebase baseline is established, verified, and ready for Phase 1 architectural design and implementation.
