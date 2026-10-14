# LIVO Footwear ERP — Mutation & Idempotency Audit

## 1. Executive Summary

This document presents a comprehensive audit of all mutating operations across the LIVO Footwear ERP backend and frontend. Every operation that creates, updates, deletes, cancels, voids, reverses, or financially/inventory affects data has been inventoried, analyzed, and classified according to its idempotency characteristics, retry safety, and concurrency vulnerability.

---

## 2. Classification Definitions

| Classification | Meaning | Policy / Implementation |
| :--- | :--- | :--- |
| **SAFE** | Operation does not mutate state or cause side effects (e.g. read-only queries `GET`, `HEAD`). | Inherently safe on retry. |
| **IDEMPOTENT** | Executing the request multiple times produces the exact same server state as executing it once (e.g. `DELETE` where repeated deletion is a no-op or returns 404/204, or reading snapshots). | Safe to retry naturally or via idempotent state overwrite. |
| **CONDITIONALLY IDEMPOTENT** | Operation is stateful and valid once from a specific state, but rejects subsequent identical calls via explicit business guardrails (e.g. cancelling an already void invoice, or reversing an already reversed stock movement). | Must reject duplicate executions with descriptive client errors (400 Bad Request / 409 Conflict) and prevent duplicate financial/inventory reversals. |
| **NON-IDEMPOTENT** | Executing the request multiple times creates duplicate business effects (e.g. duplicate invoices, duplicate customer payments, duplicate stock card movements, duplicate batch records). | **MANDATORY**: Must be protected by server-side idempotency key architecture (`UNIQUE(company_id, idempotency_key)`), canonical payload fingerprinting, and response replay. |

---

## 3. Inventory of All Mutating Operations

### 3.1 Sales Domain

#### OP-SALES-01: Create Sales Order
* **Endpoint**: `/api/v1/sales/orders`
* **HTTP Method**: `POST`
* **Creates Data**: `SalesOrder`, `SalesItem`, and (if `delivered=True`) outbound `StockMovement`.
* **Updates Data**: Client credit balance.
* **Deletes Data**: None.
* **Financial Impact**: High (commits credit limit liability, records receivable obligation).
* **Inventory Impact**: High (if `delivered=True`, deducts finished goods inventory from warehouse).
* **Document Number**: Backend generated `SO-YYYY-XXXXX` sequence.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` via `Idempotency-Key` / `X-Idempotency-Key`.
* **Retry Behavior**: Network retries without idempotency key would create duplicate orders, double credit usage, and double stock deductions. With idempotency key, replays the original order response without side effects.
* **Concurrency Behavior**: Protected by client credit advisory lock, stock mutation locks, and idempotency key mutex.
* **Required Idempotency**: Server-side idempotency key with response replay.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-SALES-02: Create Client
* **Endpoint**: `/api/v1/sales/clients`
* **HTTP Method**: `POST`
* **Creates Data**: `Client` master data row.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Low (sets credit limit).
* **Inventory Impact**: None.
* **Document Number**: Client Code (`code`).
* **Current Idempotency Mechanism**: Database constraint `UNIQUE(company_id, code)` + `IdempotencyMiddleware`.
* **Retry Behavior**: Retry with identical code without key returns 400 IntegrityError; with idempotency key replays client record.
* **Concurrency Behavior**: DB unique constraint serializes concurrent attempts.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Medium.
* **Classification**: **NON-IDEMPOTENT**

#### OP-SALES-03: Record Sales Order Payment
* **Endpoint**: `/api/v1/sales/payments`
* **HTTP Method**: `POST`
* **Creates Data**: `Payment` record.
* **Updates Data**: `SalesOrder.received_amount`, `SalesOrder.receivable_amount`.
* **Deletes Data**: None.
* **Financial Impact**: Critical (records cash/bank inflow and decrements receivable balance).
* **Inventory Impact**: None.
* **Document Number**: Receipt reference.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Without idempotency key, double-records cash inflow and double-decrements order receivables. With key, replays original payment response.
* **Concurrency Behavior**: Protected by idempotency lock.
* **Required Idempotency**: Mandatory idempotency key.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

---

### 3.2 Invoicing Domain

#### OP-INV-01: Generate Tax Invoice
* **Endpoint**: `/api/v1/invoices`
* **HTTP Method**: `POST`
* **Creates Data**: `Invoice`, `ReceivableEntry` (statutory debit entry).
* **Updates Data**: Sequence counter in `InvoiceSequence` / `DocumentSequence`.
* **Deletes Data**: None.
* **Financial Impact**: Critical (Nepal Statutory IRD Schedule-5 VAT liability, 13% tax calculation, AR debit).
* **Inventory Impact**: None (inventory deducted at sales dispatch).
* **Document Number**: `INV-CC-XXXXX` from atomic locked sequence.
* **Current Idempotency Mechanism**: 
  1. Statutory guard: checks `Invoice.sales_order_id` for existing active VAT invoice (409 Conflict).
  2. Server-side `IdempotencyMiddleware` via `Idempotency-Key`.
* **Retry Behavior**: Safe. If `Idempotency-Key` is provided, original invoice is replayed. If omitted, duplicate VAT guard rejects with 409 Conflict.
* **Concurrency Behavior**: Protected by row-level sequence locks (`SELECT ... FOR UPDATE`) and idempotency mutex.
* **Required Idempotency**: Mandatory server-side idempotency key + statutory single-VAT invariant.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-INV-02: Cancel / Void Tax Invoice
* **Endpoint**: `/api/v1/invoices/{invoice_id}/cancel`
* **HTTP Method**: `POST`
* **Creates Data**: `ReceivableEntry` (`VOID_REVERSAL`, direction -1).
* **Updates Data**: `Invoice.is_void = True`.
* **Deletes Data**: None (statutory rule: physical deletions prohibited).
* **Financial Impact**: Critical (reverses VAT liability and accounts receivable obligation).
* **Inventory Impact**: None.
* **Document Number**: `VOID-INV-CC-XXXXX`.
* **Current Idempotency Mechanism**: Guardrail `if invoice.is_void: raise 400` + `IdempotencyMiddleware`.
* **Retry Behavior**: Re-running cancellation returns 400 Bad Request ("already cancelled/voided"), preventing duplicate AR credit reversals. With idempotency key, replays original cancellation response.
* **Concurrency Behavior**: Row lock on invoice prevents concurrent double-cancellation.
* **Required Idempotency**: Stateful guardrail + idempotency key.
* **Risk**: Critical.
* **Classification**: **CONDITIONALLY IDEMPOTENT**

---

### 3.3 Accounts Receivable Subledger

#### OP-AR-01: Record Customer AR Payment & Invoice Allocation
* **Endpoint**: `/api/v1/receivables/payments`
* **HTTP Method**: `POST`
* **Creates Data**: `ReceivableEntry` (direction -1, `PAYMENT_CASH` / `PAYMENT_BANK`), `PaymentAllocation` rows, optional legacy `Payment`.
* **Updates Data**: Invoice allocation balances.
* **Deletes Data**: None.
* **Financial Impact**: Critical (credits client account in exact paisa, clears invoice debt).
* **Inventory Impact**: None.
* **Document Number**: `RCPT-YYYY-XXXXX`.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` via `Idempotency-Key` / `X-Idempotency-Key`.
* **Retry Behavior**: Without idempotency, client balance is decremented twice. With idempotency key, cached receipt is replayed with exact original paisa allocation.
* **Concurrency Behavior**: Client credit lock (`acquire_client_credit_lock`) + idempotency mutex.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-AR-02: Toggle Receivable Entry Dispute
* **Endpoint**: `/api/v1/receivables/dispute/{entry_id}`
* **HTTP Method**: `POST`
* **Creates Data**: None.
* **Updates Data**: `ReceivableEntry.is_disputed`, `ReceivableEntry.notes`.
* **Deletes Data**: None.
* **Financial Impact**: Low (flags entry for aging exclusion; does not alter underlying accounting balance).
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: Boolean toggle or explicit state transition.
* **Retry Behavior**: Re-calling without idempotency toggles state back and forth; with idempotency key replays the toggle result.
* **Concurrency Behavior**: Transaction lock on entry.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT** (when setting explicit flag) / **NON-IDEMPOTENT** (toggle).

---

### 3.4 Purchasing & Materials Domain

#### OP-PUR-01: Create Purchase
* **Endpoint**: `/api/v1/purchase/purchases`
* **HTTP Method**: `POST`
* **Creates Data**: `Purchase` record, inward `StockMovement` for raw material.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: High (creates accounts payable liability to supplier).
* **Inventory Impact**: High (increments raw material inventory).
* **Document Number**: Auto-generated sequence / invoice reference.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Network retry without key creates duplicate material receipt and duplicate payable balance. With key, returns original purchase record.
* **Concurrency Behavior**: Stock mutation locks + idempotency lock.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: High.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PUR-02: Create Supplier
* **Endpoint**: `/api/v1/purchase/suppliers`
* **HTTP Method**: `POST`
* **Creates Data**: `Supplier` record.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Low.
* **Inventory Impact**: None.
* **Document Number**: Supplier Code.
* **Current Idempotency Mechanism**: `UNIQUE(company_id, code)` + `IdempotencyMiddleware`.
* **Retry Behavior**: Duplicate code rejected by DB constraint.
* **Concurrency Behavior**: DB unique constraint serializes concurrent attempts.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PUR-03: Create Raw Material
* **Endpoint**: `/api/v1/purchase/raw-materials`
* **HTTP Method**: `POST`
* **Creates Data**: `RawMaterial` record.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Low.
* **Inventory Impact**: None.
* **Document Number**: Material Code (`RM-...`).
* **Current Idempotency Mechanism**: `UNIQUE(company_id, code)` + `IdempotencyMiddleware`.
* **Retry Behavior**: Rejects duplicate code with 400.
* **Concurrency Behavior**: DB unique constraint.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **NON-IDEMPOTENT**

---

### 3.5 Inventory & Stock Domain

#### OP-STK-01: Append Stock Ledger Movement
* **Endpoint**: `/api/v1/stock/movements`
* **HTTP Method**: `POST`
* **Creates Data**: `StockMovement` ledger entry.
* **Updates Data**: None (append-only ledger).
* **Deletes Data**: None.
* **Financial Impact**: High (affects inventory valuation).
* **Inventory Impact**: Critical (changes physical warehouse inventory card balance).
* **Document Number**: `source_doc_ref`.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` + advisory stock locking.
* **Retry Behavior**: Without idempotency, duplicate movement shifts stock twice. With key, replays original movement.
* **Concurrency Behavior**: Advisory stock lock `acquire_stock_mutation_lock` + row locks on product variant.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-STK-02: Create Stock Adjustment
* **Endpoint**: `/api/v1/stock/adjustments`
* **HTTP Method**: `POST`
* **Creates Data**: `StockMovement` (`ADJUSTMENT_IN` / `ADJUSTMENT_OUT`).
* **Updates Data**: None (append-only ledger).
* **Deletes Data**: None.
* **Financial Impact**: High (records inventory shrinkage or surplus).
* **Inventory Impact**: Critical (alters warehouse variant balance).
* **Document Number**: `ADJ-YYYY-XXXXX`.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` + zero-floor balance check + advisory locking.
* **Retry Behavior**: Without key, adjusts stock delta a second time. With key, replays movement.
* **Concurrency Behavior**: Serialized by `acquire_stock_advisory_lock` and zero-floor invariant.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-STK-03: Reverse Stock Movement
* **Endpoint**: `/api/v1/stock/reversals/{movement_id}`
* **HTTP Method**: `POST`
* **Creates Data**: `StockMovement` (`VOID_REVERSAL`, with `reversal_of_id`).
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: High (restores prior inventory valuation).
* **Inventory Impact**: Critical (inverts previous stock direction).
* **Document Number**: `REV-YYYY-XXXXX`.
* **Current Idempotency Mechanism**: 
  1. Stateful invariant: `already_reversed` check prevents reversing a movement more than once (400 Bad Request).
  2. `IdempotencyMiddleware`.
* **Retry Behavior**: Second attempt rejected with 400 ("Stock movement has already been reversed"). Replays cached response if idempotency key is provided.
* **Concurrency Behavior**: Serialized by stock lock and idempotency mutex.
* **Required Idempotency**: Conditional guardrail + idempotency key.
* **Risk**: Critical.
* **Classification**: **CONDITIONALLY IDEMPOTENT**

#### OP-STK-04: Materialize Stock Snapshots
* **Endpoint**: `/api/v1/stock/snapshots`
* **HTTP Method**: `POST`
* **Creates Data**: `StockSnapshot` rows.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: None (performance acceleration cache for ledger summation).
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` + date-based checkpoint verification.
* **Retry Behavior**: Re-running produces identical snapshot values.
* **Concurrency Behavior**: Single-worker execution.
* **Required Idempotency**: Safe/idempotent calculation.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT**

---

### 3.6 Production Domain

#### OP-PROD-01: Create Production Batch
* **Endpoint**: `/api/v1/production/batches`
* **HTTP Method**: `POST`
* **Creates Data**: `ProductionBatch`, `ProductionMaterialUsage`, positive finished goods `StockMovement`, negative raw material `StockMovement` (BOM deduction).
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: High (capitalizes raw materials into finished goods).
* **Inventory Impact**: Critical (simultaneously decrements raw materials and increments finished footwear pairs).
* **Document Number**: `PROD-YYYY-XXXXX`.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Without idempotency, doubles material consumption and doubles manufactured stock. With key, replays batch creation.
* **Concurrency Behavior**: Advisory stock locks on all BOM items + batch mutex.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PROD-02: Reconcile Offline Production Draft
* **Endpoint**: `/api/v1/production/sync/draft`
* **HTTP Method**: `POST`
* **Creates Data**: `ProductionBatch`, `ProductionSyncLog`, `StockMovement` entries.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: High.
* **Inventory Impact**: Critical.
* **Document Number**: Server-allocated batch number.
* **Current Idempotency Mechanism**: Dedicated database-backed `ProductionSyncLog` with `UniqueConstraint("company_id", "idempotency_key")`, SHA-256 payload hash verification, and advisory locking.
* **Retry Behavior**: Replaying with identical key returns `{"sync_status": "ALREADY_ACCEPTED", "batch_id": ...}` without duplicating movements. Replaying with different payload returns 409 Conflict.
* **Concurrency Behavior**: PostgreSQL advisory lock + in-process thread mutex.
* **Required Idempotency**: Native protocol-level idempotency key.
* **Risk**: Critical.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PROD-03: Create Product
* **Endpoint**: `/api/v1/production/products`
* **HTTP Method**: `POST`
* **Creates Data**: `Product` row.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Low.
* **Inventory Impact**: None.
* **Document Number**: Product Code.
* **Current Idempotency Mechanism**: `UNIQUE(company_id, code)` + `IdempotencyMiddleware`.
* **Retry Behavior**: Rejects duplicate code.
* **Concurrency Behavior**: DB unique constraint.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PROD-04: Create Bill of Materials Item
* **Endpoint**: `/api/v1/production/bom`
* **HTTP Method**: `POST`
* **Creates Data**: `BillOfMaterials` row.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Medium (determines consumption cost).
* **Inventory Impact**: None directly.
* **Document Number**: None.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Without key, duplicate BOM item row is inserted. With key, cached BOM item is replayed.
* **Concurrency Behavior**: Idempotency mutex.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Medium.
* **Classification**: **NON-IDEMPOTENT**

#### OP-PROD-05: Delete Bill of Materials Item
* **Endpoint**: `/api/v1/production/bom/{bom_id}`
* **HTTP Method**: `DELETE`
* **Creates Data**: None.
* **Updates Data**: None.
* **Deletes Data**: `BillOfMaterials` row.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware` + deletion check.
* **Retry Behavior**: Second DELETE returns 404 (item already removed) or replayed 200.
* **Concurrency Behavior**: Single-row deletion.
* **Required Idempotency**: Naturally idempotent.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT**

---

### 3.7 HR & Payroll Domain

#### OP-HR-01: Create Worker
* **Endpoint**: `/api/v1/hr/workers`
* **HTTP Method**: `POST`
* **Creates Data**: `Worker` record.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: Medium (establishes wage/salary rates).
* **Inventory Impact**: None.
* **Document Number**: Worker Code (`worker_code`).
* **Current Idempotency Mechanism**: `UniqueConstraint("company_id", "worker_code")` + `IdempotencyMiddleware`.
* **Retry Behavior**: Rejects duplicate code with 400. Replays with idempotency key.
* **Concurrency Behavior**: DB unique constraint.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Medium.
* **Classification**: **NON-IDEMPOTENT**

#### OP-HR-02: Update Worker Details
* **Endpoint**: `/api/v1/hr/workers/{worker_id}`
* **HTTP Method**: `PATCH`
* **Creates Data**: None.
* **Updates Data**: `Worker` details (salary, department, active status).
* **Deletes Data**: None.
* **Financial Impact**: Medium.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: State update + `IdempotencyMiddleware`.
* **Retry Behavior**: Setting fields to identical values is naturally idempotent; with idempotency key returns exact replayed result.
* **Concurrency Behavior**: Row lock on worker.
* **Required Idempotency**: Naturally idempotent update.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT**

#### OP-HR-03: Record Employee Advance
* **Endpoint**: `/api/v1/hr/advances`
* **HTTP Method**: `POST`
* **Creates Data**: `WorkerAdvance` record.
* **Updates Data**: Worker balance.
* **Deletes Data**: None.
* **Financial Impact**: High (cash outlay to worker, salary deduction asset).
* **Inventory Impact**: None.
* **Document Number**: Advance ID / Receipt.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Retrying without key issues a second advance, doubling employee debt and cash outlay. With key, returns original advance.
* **Concurrency Behavior**: Serialized by worker mutex and idempotency lock.
* **Required Idempotency**: Mandatory server-side idempotency.
* **Risk**: High.
* **Classification**: **NON-IDEMPOTENT**

#### OP-HR-04: Process Monthly Payroll
* **Endpoint**: `/api/v1/hr/monthly-payroll`
* **HTTP Method**: `POST`
* **Creates Data**: `WorkerMonthlyRecord` entries.
* **Updates Data**: Clears outstanding advances.
* **Deletes Data**: None.
* **Financial Impact**: Critical (salary disbursement, advance recovery).
* **Inventory Impact**: None.
* **Document Number**: Payroll record sequence.
* **Current Idempotency Mechanism**: 
  1. Guardrail: checks if monthly record already exists for `(worker_id, year, month)` (400 Bad Request).
  2. `IdempotencyMiddleware`.
* **Retry Behavior**: Rejected if already computed for month; replayed if key is supplied.
* **Concurrency Behavior**: Worker payroll lock.
* **Required Idempotency**: Conditional guardrail + idempotency key.
* **Risk**: Critical.
* **Classification**: **CONDITIONALLY IDEMPOTENT**

---

### 3.8 Product Gallery & Analytics

#### OP-GAL-01: Upload Product Image
* **Endpoint**: `/api/v1/gallery/upload/{product_id}`
* **HTTP Method**: `POST`
* **Creates Data**: `ProductImage` database record, stored file on disk/storage.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: Image UUID.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: File content hash prevents duplicate storage; idempotency key replays upload metadata.
* **Concurrency Behavior**: Single-file storage.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **NON-IDEMPOTENT**

#### OP-GAL-02: Delete Product Image
* **Endpoint**: `/api/v1/gallery/{image_id}`
* **HTTP Method**: `DELETE`
* **Creates Data**: None.
* **Updates Data**: None.
* **Deletes Data**: `ProductImage` database record and disk file.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: Natural deletion idempotency (returns 204 or 404).
* **Retry Behavior**: Repeating deletion returns 404 Not Found.
* **Concurrency Behavior**: Safe.
* **Required Idempotency**: Naturally idempotent.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT**

#### OP-ANA-01: Record Daily Factory Log
* **Endpoint**: `/api/v1/analytics/daily-logs`
* **HTTP Method**: `POST`
* **Creates Data**: `DailyFactoryLog` row.
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: Log ID.
* **Current Idempotency Mechanism**: `IdempotencyMiddleware`.
* **Retry Behavior**: Without key creates duplicate log entries; with key replays recorded log.
* **Concurrency Behavior**: Safe.
* **Required Idempotency**: Idempotency key supported.
* **Risk**: Low.
* **Classification**: **NON-IDEMPOTENT**

---

### 3.9 System, Auth & Operations

#### OP-AUTH-01: Login
* **Endpoint**: `/api/v1/auth/login`
* **HTTP Method**: `POST`
* **Creates Data**: None (issues JWT cookie).
* **Updates Data**: None.
* **Deletes Data**: None.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: Rate limited (`BasicRateLimitMiddleware`).
* **Retry Behavior**: Issues new session token.
* **Concurrency Behavior**: Rate limited per IP.
* **Required Idempotency**: Not applicable (credentials exchange).
* **Risk**: Low.
* **Classification**: **IDEMPOTENT** (session renewal)

#### OP-AUTH-02: Logout
* **Endpoint**: `/api/v1/auth/logout`
* **HTTP Method**: `POST`
* **Creates Data**: None.
* **Updates Data**: Clears HTTP cookie.
* **Deletes Data**: None.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: Natural idempotency.
* **Retry Behavior**: Clearing an already cleared cookie is completely safe.
* **Concurrency Behavior**: Safe.
* **Required Idempotency**: Naturally idempotent.
* **Risk**: None.
* **Classification**: **IDEMPOTENT**

#### OP-SYS-01: Trigger Backup
* **Endpoint**: `/api/v1/backup/run`
* **HTTP Method**: `POST`
* **Creates Data**: SQLite / Postgres dump file, `latest_status.json`.
* **Updates Data**: Backup status metadata.
* **Deletes Data**: None.
* **Financial Impact**: None.
* **Inventory Impact**: None.
* **Document Number**: None.
* **Current Idempotency Mechanism**: Single-process lock prevents concurrent backup execution.
* **Retry Behavior**: Overwrites backup or runs fresh snapshot.
* **Concurrency Behavior**: Guarded by in-flight backup mutex.
* **Required Idempotency**: Naturally serialized.
* **Risk**: Low.
* **Classification**: **IDEMPOTENT**

---

## 4. Summary Matrix of High-Risk Mutations

| Operation | Endpoint | Impact | Risk Level | Protection Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **Sales Order Creation** | `POST /api/v1/sales/orders` | Financial & Stock | **CRITICAL** | Idempotency Key, Stock Locks, Credit Lock |
| **Invoice Generation** | `POST /api/v1/invoices` | Statutory VAT, AR | **CRITICAL** | Idempotency Key, Single-VAT Invariant, Sequence Lock |
| **Invoice Cancellation** | `POST /api/v1/invoices/{id}/cancel` | AR Subledger Reversal | **CRITICAL** | `is_void` Guardrail, Idempotency Key |
| **AR Payment Receipt** | `POST /api/v1/receivables/payments` | Cash & Customer Balance | **CRITICAL** | Idempotency Key, Paisa Allocation Lock |
| **Stock Ledger Movement** | `POST /api/v1/stock/movements` | Physical Card Balance | **CRITICAL** | Idempotency Key, Advisory Variant Lock |
| **Stock Adjustment** | `POST /api/v1/stock/adjustments` | Physical Card Balance | **CRITICAL** | Idempotency Key, Zero-Floor Check |
| **Stock Reversal** | `POST /api/v1/stock/reversals/{id}` | Physical Card Balance | **CRITICAL** | `already_reversed` Invariant, Idempotency Key |
| **Production Batch** | `POST /api/v1/production/batches` | Stock & BOM Consumption | **CRITICAL** | Idempotency Key, Multi-Item Stock Locks |
| **Offline Production Sync** | `POST /api/v1/production/sync/draft` | Stock & Batch Records | **CRITICAL** | ProductionSyncLog, Payload Hash, Advisory Lock |
| **Employee Advance** | `POST /api/v1/hr/advances` | Cash Outlay & Debt | **HIGH** | Idempotency Key, Worker Lock |
| **Monthly Payroll** | `POST /api/v1/hr/monthly-payroll` | Salary & Advance Recovery | **HIGH** | `(worker, year, month)` Invariant, Idempotency Key |
| **Purchase Order** | `POST /api/v1/purchase/purchases` | AP Liability & Materials | **HIGH** | Idempotency Key, Stock Locks |
