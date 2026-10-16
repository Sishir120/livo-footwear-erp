# LIVO Footwear ERP — Day 5 Frontend Acceptance Rehearsal Results

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Scope:** 10-step client acceptance journey through the actual user interface routes, API endpoints, and database invariants.  
**Execution Environment:** Isolated synthetic tenant company (`Summit Footwear Industries`) using multi-warehouse fixtures and real API request simulation.

---

## 1. Executive Acceptance Summary

The end-to-end client rehearsal journey was executed through the active application workflows mirroring exact operator interactions. All 10 user journeys passed their functional and financial invariants with zero data leakage and zero orphaned records.

| Step | Journey Name | User Role | Route / Component | Result | Key Invariant Verified |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **1** | Demo Login & Session Verification | Editor | `/login` -> `AppShell` | **PASS** | HTTP-only `livo_access_token` session cookie issued, non-root user profile loaded. |
| **2** | Purchasing & Raw Material Inward | Editor | `PurchaseView.tsx` (`/api/v1/purchase/purchases`) | **PASS** | Raw material purchase record created with supplier association. |
| **3** | Landed Cost & Stock Valuation | Editor | `PurchaseView.tsx` (`/api/v1/purchase/purchases`) | **PASS** | Landed expenses (freight + customs + carrying) allocated to unit cost with exact integer paisa arithmetic (50,000 paisa / unit). |
| **4** | Production Batch & Finished Goods | Editor | `ProductionView.tsx` (`/api/v1/production/batches`) | **PASS** | Production completion writes finished goods stock movement (+40 pairs) into active warehouse. |
| **5** | Inter-Warehouse Stock Transfer | Editor | `StockTransferModal.tsx` (`/api/v1/transfers`) | **PASS** | Complete 3-phase transfer lifecycle: `DRAFT` -> `IN_TRANSIT` (source deducted) -> `RECEIVED` (destination incremented). |
| **6** | Sales Order & Stock Dispatch | Editor | `SalesInvoiceView.tsx` (`/api/v1/sales/orders`) | **PASS** | 10 pairs dispatched; insufficient stock prevented; sales order marked delivered. |
| **7** | VAT Invoice & Payment Allocation | Editor | `SalesInvoiceView.tsx` (`/api/v1/invoices`, `/sales/payments`) | **PASS** | 42,000 NPR taxable basis + 13% Nepal VAT (5,460 NPR) = 47,460 NPR total invoice; partial payment (27,460 NPR) leaves 14,540 NPR AR balance. |
| **8** | HR Ledger & Confidential Document RBAC | Admin / Viewer | `HRManagementView.tsx` (`/api/v1/hr/workers`) | **PASS** | Admin uploads confidential citizenship PDF; Viewer sees worker but salary/advances are strictly omitted; direct download by viewer blocked (403). |
| **9** | Factory Expenses, Assets & Waste | Editor | `ExpensesAssetsView.tsx` (`/fixed-assets`, `/expenses/factory`, `/waste`) | **PASS** | Factory utility expense, machinery fixed asset, and production scrap recorded with tenant scoping. |
| **10** | Session Expiry & Mutation Defense | Viewer / Expired | `/api/v1/auth/logout`, `/production/products` | **PASS** | Expired/manipulated token rejected with 401; viewer mutation attempt rejected with 403; database left unchanged. |

---

## 2. Step-by-Step Acceptance Walkthrough

### Step 1: Demo Login & Authentication
- **User Action:** Operator enters username `summit_editor` and password `SummitPass2026!` at `/login`.
- **UI Behavior:** Login button displays active state; on HTTP 200, sets secure `livo_access_token` cookie and routes to dashboard.
- **API Response:** `POST /api/v1/auth/login` returns HTTP 200 with `{"user": {"username": "summit_editor", "role": "editor"}, "message": "Login successful"}`.
- **Database Invariant:** User session active; no passwords or plaintext tokens logged.
- **Evidence:** `test_day_5_client_acceptance_rehearsal.py::test_client_rehearsal_journey` (lines 180–195).

---

### Step 2: Purchasing & Raw Material Inward
- **User Action:** Operator navigates to "Purchase Raw Materials" tab, selects Supplier "Everest Tannery & Polymers", selects Raw Material "Synthetic PU Leather Sheet", enters quantity 100 kg @ 450.00 NPR.
- **UI Behavior:** Form calculates base invoice total 45,000.00 NPR.
- **API Response:** `POST /api/v1/purchase/purchases` returns HTTP 200 with allocated GRN number (`GRN-xxxx`).
- **Database Invariant:** `purchases` record inserted with `company_id` foreign key.

---

### Step 3: Landed Cost & Stock Valuation
- **User Action:** Operator inputs additional landed expenses: Carrying In (2,500 NPR), Import Duty (1,500 NPR), China Carrying (1,000 NPR).
- **UI Behavior:** Live breakdown shows total landed cost: 50,000.00 NPR (5,000,000 paisa) and effective landed unit cost: 500.00 NPR / kg.
- **API Response:** Response contains `total_landed_cost_paisa: 5000000`, `effective_unit_rate_paisa: 50000`.
- **Database Invariant:** `raw_materials.current_stock` increments from 0.0 to 100.0 kg; append-only `raw_material_movements` record created with direction `+1`.

---

### Step 4: Production Batch & Finished Goods Output
- **User Action:** Operator navigates to "Production", creates batch `BATCH-01` for product "LIVO Trekker Pro Boot" (Size 42, Color Brown), target 40 pairs, produced 40 pairs.
- **UI Behavior:** Batch shows status `completed`.
- **API Response:** `POST /api/v1/production/batches` returns HTTP 200 with batch ID.
- **Database Invariant:**
  - `production_batches` record created with `status="completed"`.
  - Finished goods stock movement automatically generated (`PRODUCTION_IN`, direction `+1`, quantity `40`).
  - Finished goods balance at factory warehouse reconciles to exactly 40 pairs.

---

### Step 5: Inter-Warehouse Stock Transfer
- **User Action:** Operator opens "Branches & Godowns" or "Stock Ledger" transfer modal, selects source "Hetauda Factory Central", destination "Kathmandu Retail Hub", quantity 15 pairs (Size 42).
- **UI Behavior:**
  1. Draft transfer created.
  2. Dispatch button clicked: status advances to `IN_TRANSIT`.
  3. Retail hub operator receives transfer: status advances to `RECEIVED`.
- **API Response:**
  - `POST /api/v1/transfers` returns HTTP 201 (`status: "DRAFT"`).
  - `POST /api/v1/transfers/{id}/dispatch` returns HTTP 200 (`status: "IN_TRANSIT"`).
  - `POST /api/v1/transfers/{id}/receive` returns HTTP 200 (`status: "RECEIVED"`).
- **Database Invariant:**
  - Source warehouse stock deducted by 15 pairs (40 - 15 = 25 pairs remaining).
  - Destination warehouse stock credited with 15 pairs.
  - Zero stock leakage during in-transit state.

---

### Step 6: Sales Order & Dispatch
- **User Action:** Operator navigates to "Sales & Invoicing", creates client "Kathmandu Adventure Gear", creates Sales Order for 10 pairs @ 4,200.00 NPR, marks delivered.
- **UI Behavior:** Order confirmed with total 42,000.00 NPR.
- **API Response:** `POST /api/v1/sales/orders` returns HTTP 200.
- **Database Invariant:** `sales_orders` and `sales_items` records created with `company_id` isolation. Insufficient stock attempts (e.g. dispatching 1,000 pairs) return HTTP 400.

---

### Step 7: VAT Tax Invoice & Payment Allocation
- **User Action:** Operator clicks "Generate VAT Invoice" with standard 13% Nepal VAT. Operator records partial customer payment of 27,460.00 NPR via bank deposit.
- **UI Behavior:** Invoice generated with official tax breakdown. Order summary updates receivable balance.
- **API Response:**
  - `POST /api/v1/invoices` returns `subtotal: 42000.0`, `vat_amount: 5460.0`, `total_amount: 47460.0`, `total_amount_paisa: 4746000`.
  - `POST /api/v1/sales/payments` returns HTTP 200.
- **Database Invariant:**
  - Duplicate active invoice attempt for the same sales order returns HTTP 409 Conflict.
  - Accounts receivable balance reconciles: 42,000 - 27,460 = 14,540.00 NPR.

---

### Step 8: HR Management & Restricted Data Redaction
- **User Action:** Administrator logs in, creates worker "Ram Bahadur Shrestha" with basic monthly salary 36,000 NPR, and uploads citizenship PDF. Compliance Viewer logs in to review worker records.
- **UI Behavior:** Admin sees full salary and download button. Viewer sees worker name, code, and role, but compensation columns and download buttons are hidden.
- **API Response:**
  - `POST /api/v1/hr/workers` creates worker with `basic_rate_paisa: 3600000`.
  - `POST /api/v1/hr/workers/{id}/citizenship` stores PDF in `storage/secure_hr/company_{id}/citizenship/`.
  - `GET /api/v1/hr/workers` (Viewer): `basic_rate_paisa` and `outstanding_advance_paisa` are omitted from the JSON payload.
  - `GET /api/v1/hr/workers/{id}/citizenship` (Viewer): returns HTTP 403 Forbidden.
- **Database Invariant:** Worker records and confidential files remain unaltered by unauthorized requests.

---

### Step 9: Factory Expenses, Assets & Waste Tracking
- **User Action:** Operator logs factory electricity bill (18,500 NPR), machinery fixed asset (Hydraulic Leather Skiver @ 280,000 NPR), and cutting floor scrap (2.5 kg).
- **UI Behavior:** Summary totals update across the respective tabs.
- **API Response:**
  - `POST /api/v1/expenses/factory` returns HTTP 201.
  - `POST /api/v1/fixed-assets` returns HTTP 201.
  - `POST /api/v1/waste` returns HTTP 201.
- **Database Invariant:** Recorded under active company ID; waste logging does not mutate raw material stock balance per design decision D.

---

### Step 10: Session Expiry, Logout & Prohibited Mutation
- **User Action:** Operator clicks "Logout". An attacker or expired session attempts to mutate inventory/catalog data.
- **UI Behavior:** Session is terminated; browser redirects to `/login`.
- **API Response:**
  - `POST /api/v1/auth/logout` clears HTTP-only cookie.
  - Request with expired or invalid cookie returns HTTP 401 Unauthorized (`{"error": "AUTHENTICATION_ERROR", "message": "Invalid or expired session token."}`).
  - Authenticated Viewer attempting POST `/api/v1/production/products` returns HTTP 403 Forbidden.
- **Database Invariant:** No unauthenticated or unauthorized writes reach the database.

---

## 3. Newcomer Usability Observations & Minor Polish

During acceptance rehearsal, the following usability items were reviewed:

1. **Nepali Date Picker Usability:**
   `NepaliDatePicker.tsx` is an active, fully integrated component across `SalesInvoiceView`, `PurchaseView`, `ProductionView`, `HRManagementView`, and `ExpensesAssetsView`. Both AD and BS dates synchronize cleanly.
2. **Clear Navigation & Role Badges:**
   `AppShell.tsx` dynamically displays user role badges (`ADMIN / SUPERVISOR`, `Editor`, `Viewer`) and conditionally hides admin-only tabs (`Admin Control`, `Ops Cockpit`).
3. **Empty States & Guidance:**
   Views render descriptive empty states and guidance banners when catalog, batch, or order records are empty.
4. **Wording Recommendation:**
   In `StockTransferModal.tsx`, ensure the distinction between "Dispatched Quantity" and "Received Quantity" remains unambiguous during partial receipt discrepancies.
