# LIVO FOOTWEAR ERP — BUSINESS CAPABILITY AND WORKFLOW AUDIT

**Audit Date:** 2026-10-14  
**Auditor Roles:** Principal Logistics/ERP Architect, Supply Chain Systems Lead  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Target Branch:** `release/v1.0.0-staging`  

---

## 1. Executive Workflow Verdict

The LIVO Footwear ERP implements strong domain-specific operational workflows within individual manufacturing silos, but suffers from **traceability disconnections between silos** and **missing inter-location logistics workflows**:

1. **Procurement & Production:** Strongly connected via proportional BOM raw material deduction.
2. **Production to Finished Goods:** Connected; batch completion records inward movement into finished warehouse.
3. **Finished Goods to Sales Dispatch:** **DISCONNECTED FROM BATCH IDENTITY.** Dispatches relieve inventory by SKU/size, but do not record which batch was shipped.
4. **Inter-Location Transfers:** **COMPLETELY MISSING.** Moving stock between factory and branches requires manual inventory adjustments.
5. **Destination Confirmation:** **MISSING.** No two-step transfer or independent receipt confirmation exists.

---

## 2. End-to-End Business Lifecycle Transition Map

```text
[1. Supplier Purchase Order]
       │
       ▼ (Implemented & Verified: Decoupled order vs receipt date)
[2. Goods Receipt Note (GRN)]
       │
       ▼ (Implemented & Verified: 4-column landed costs capitalized into unit rate)
[3. Raw Material Inventory Ledger (kg, pcs, litre)]
       │
       ▼ (Implemented & Verified: Proportional BOM formula deduction)
[4. Production Batch Assembly (Batch #, Size, Color, Media Gallery)]
       │
       ▼ (Implemented & Verified: StockMovement +1 recorded with ref_id=batch.id)
[5. Finished Goods Warehouse (Paris Points 32-43)]
       │
       ├────────────────────────────────────────┐
       ▼                                        ▼
[6. Inter-Location Transfer]            [8. Wholesale Sales Order Entry]
       │                                        │
       ▼ (MISSING WORKFLOW)                     ▼ (Implemented & Verified: Decoupled order vs dispatch date)
[7. In-Transit / Destination Receipt]   [9. Physical Sales Dispatch]
                                                │
                                                ▼ (Implemented & Verified: StockMovement -1 deducted ONLY on dispatch)
                                        [10. Tax Invoice Generation (13% VAT)]
                                                │
                                                ▼ (Implemented & Verified: Debits Client AR Subledger)
                                        [11. Customer Payment Receipt & Multi-Invoice Allocation]
```

---

## 3. Inventory Invariants & Rule Verification

| Invariant / Rule | System Enforcement Mechanism | Test Evidence | Verdict |
|---|---|---|:---:|
| **Zero Negative Stock** | Advisory lock + mutex + row-level balance check before outbound movement. Raises HTTP 422 if balance < requested. | `test_checkpoint_16_business_security.py` | **PROVEN** |
| **No Double Consumption of Materials** | BOM deduction executed inside serialized batch creation transaction. | `test_bom_deduction.py` | **PROVEN** |
| **No Silent Creation / Deletion** | Stock exists ONLY as the mathematical sum of append-only `StockMovement` records. No mutable `stock_qty` column. | `test_stock_ledger.py` | **PROVEN** |
| **Decoupled Sales Dispatch** | Sales order entry does NOT reduce stock; stock deducted ONLY upon explicit dispatch action. | `test_sales_dispatch_and_expenses.py` | **PROVEN** |
| **Decoupled Purchase Inwarding** | Purchase order does NOT increase stock; stock added ONLY upon explicit Goods Receipt (GRN). | `test_raw_material_ledger.py` | **PROVEN** |
| **Idempotent Web Requests** | `IdempotencyMiddleware` caches responses for 24h by `X-Idempotency-Key` + SHA-256 body hash. Replays prevent duplicate writes. | `test_idempotency.py` | **PROVEN** |
| **Sequential Invoice Numbers** | Document sequence advisory lock guarantees gap-free, non-colliding invoice numbering under concurrent requests. | `test_document_numbering_concurrency.py`| **PROVEN** |
| **Batch Traceability on Dispatch** | Sales dispatches currently record only `product_id` and `size`. `batch_id` is NOT recorded. | Code inspection `api/v1/sales.py:590-605` | **FAILED (GAP)** |
| **Location Transfer State Machine** | Zero models or routes exist for `DRAFT -> DISPATCHED -> IN_TRANSIT -> RECEIVED`. | Code search across `api/v1/` | **FAILED (GAP)** |
| **Independent Destination Receipt**| No transfer verification screen or discrepancy logging exists. | None | **FAILED (GAP)** |
| **Unit-Level Serial Tracking** | Product inventory tracked strictly at size level. No serial tracking tables exist. | Model inspection `models/stock.py` | **FAILED (GAP)** |

---

## 4. Requirements-to-Code Implementation Matrix

| Client Requirement | Backend Implementation | Database Schema | Frontend UI | Verified Status |
|---|---|---|---|:---:|
| **Bikram Sambat (BS) Dates** | `core/nepali_date.py` (Deterministic BS 1979–2100 engine) | Dual `date_ad` + `date_bs` across transaction tables | `NepaliDatePicker.tsx` integrated in Sales, Purchase, Production, HR, Daily Report, Analytics | **VERIFIED_COMPLETE** |
| **Decoupled Sales Dates** | `order_date_ad/bs` vs `dispatch_date_ad/bs` in `api/v1/sales.py` | Decoupled columns in `sales_orders` | Dual date pickers in `SalesInvoiceView.tsx` | **VERIFIED_COMPLETE** |
| **Decoupled Purchase Dates**| `order_date_ad/bs` vs `receipt_date_ad/bs` in `api/v1/purchase.py`| Decoupled columns in `purchase_orders` | Dual date pickers in `PurchaseView.tsx` | **VERIFIED_COMPLETE** |
| **4-Column Landed Costs** | Apportionment & capitalization in `api/v1/purchase.py` | 4 paisa columns in `purchase_orders` | Landed cost section in `PurchaseView.tsx` | **VERIFIED_COMPLETE** |
| **Raw Material Units** | `kg`, `pcs`, `metre`, `litre` in `api/v1/purchase.py` | `unit` column in `raw_materials` | Unit selector in `PurchaseView.tsx` | **VERIFIED_COMPLETE** |
| **Custom Batch Colors** | Typable freeform color in `api/v1/production.py` | `color` column in `production_batches` | Color input in `ProductionView.tsx` | **VERIFIED_COMPLETE** |
| **Product Media Gallery** | Upload, reorder, delete in `api/v1/gallery.py` | `product_images` table | `ProductGalleryView.tsx` | **VERIFIED_COMPLETE** |
| **Worker Advance Recovery** | FIFO installment deduction engine in `api/v1/hr.py` | `worker_advances`, `worker_monthly_records` | `HRManagementView.tsx` | **VERIFIED_COMPLETE** |
| **Citizenship Vault** | Confidential file upload in `api/v1/hr.py` | `citizenship_doc_path` in `workers` | Upload & preview in `HRManagementView.tsx` | **VERIFIED_COMPLETE** |
| **Fixed Assets Subledger** | Asset registry & depreciation in `api/v1/assets.py` | `fixed_assets`, `asset_depreciations` | **MISSING (No UI component)** | **PARTIAL (API only)** |
| **Factory Operating Expenses**| Expense voucher logging in `api/v1/factory_expenses.py`| `factory_expenses` | **MISSING (No UI component)** | **PARTIAL (API only)** |
| **Scrap & Waste Logging** | Scrap & reject tracking in `api/v1/waste.py` | `waste_records` | **MISSING (No UI component)** | **PARTIAL (API only)** |
| **Location Hierarchy** | Flat `warehouses` only | Flat `warehouses` only | Simple warehouse dropdown in StockCard | **PARTIAL (Flat only)** |
| **Inter-Branch Transfers** | None | None | None | **MISSING** |
| **Destination Receipt Check**| None | None | None | **MISSING** |
| **Unit Serial Tracking** | None | None | None | **MISSING** |
| **End-to-End Traceability**| None | None | None | **MISSING** |
| **Contextual Help System** | None | None | None | **MISSING** |
| **Bilingual User Manual** | None | None | None | **MISSING** |
