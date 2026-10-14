# Document Numbering Audit

## 1. Invoice Number (`Invoice.invoice_number`)
- **Entity**: `Invoice`
- **Field**: `invoice_number`, `sequence_number`
- **Generation mechanism**: Backend `allocate_next_invoice_sequence(db, company_id)` using `InvoiceSequence` table and `SELECT ... FOR UPDATE` (Row-level lock).
- **Database constraint**: `UNIQUE(company_id, sequence_number)` exists. MISSING: `UNIQUE(company_id, invoice_number)`.
- **Scope**: Unique per company.
- **Concurrency behavior**: Safe (uses `with_for_update()`).
- **Retry behavior**: A retry will generate a new invoice number unless idempotency is implemented (currently not).
- **Transaction behavior**: If transaction fails, sequence is rolled back (which is good).
- **Offline behavior**: Not applicable (online only).
- **Current risk**: Low for generation, but missing unique constraint on the formatted string.
- **Required fix**: Add `UniqueConstraint("company_id", "invoice_number")`.

## 2. Sales Order Number (`SalesOrder.order_number`)
- **Entity**: `SalesOrder`
- **Field**: `order_number`
- **Generation mechanism**: Frontend uses unsafe `SO-${Date.now().toString().slice(-4)}` and passes to API.
- **Database constraint**: Missing.
- **Scope**: Unique per company.
- **Concurrency behavior**: HIGHLY UNSAFE. Multiple users or fast clicks can generate collisions.
- **Retry behavior**: Retry will reuse the same ID (since generated on client) but without DB constraint, could create duplicate orders.
- **Transaction behavior**: Unsafe.
- **Offline behavior**: Unsafe.
- **Current risk**: High.
- **Required fix**: Implement `SalesOrderSequence` in backend using row-level locking. Add `UniqueConstraint("company_id", "order_number")`. Use idempotency key for retries.

## 3. Production Batch Number (`ProductionBatch.batch_number`)
- **Entity**: `ProductionBatch`
- **Field**: `batch_number`
- **Generation mechanism**: Client generated string (or frontend UUID) passed in API payload.
- **Database constraint**: Missing.
- **Scope**: Unique per company.
- **Concurrency behavior**: Unsafe.
- **Retry behavior**: Currently uses `idempotency_key` in the `ProductionDraftSyncRequest` which is good for sync, but `batch_number` itself is unprotected.
- **Transaction behavior**: Unsafe.
- **Offline behavior**: Sync request uses UUID idempotency, but relies on client batch number.
- **Current risk**: High.
- **Required fix**: Implement `ProductionBatchSequence` in backend. Add `UniqueConstraint("company_id", "batch_number")`. Backend should map `idempotency_key` to a server-generated `batch_number`.

## 4. Stock Adjustment Reference (`StockMovement.source_doc_ref`)
- **Entity**: `StockMovement`
- **Field**: `source_doc_ref`
- **Generation mechanism**: Backend API uses `f"ADJ-{datetime.now().strftime('%y%m%d%H%M%S')}"`.
- **Database constraint**: Missing.
- **Scope**: Unique per company.
- **Concurrency behavior**: UNSAFE. Concurrent requests within the same second will get the exact same `ADJ-` number.
- **Retry behavior**: Generates new number on retry.
- **Transaction behavior**: N/A
- **Offline behavior**: N/A
- **Current risk**: High.
- **Required fix**: Implement `StockAdjustmentSequence`. Add unique constraint.

## 5. Payment Receipt Reference (`ReceivableEntry.source_doc_ref`)
- **Entity**: `ReceivableEntry`
- **Field**: `source_doc_ref`
- **Generation mechanism**: Backend API uses `f"RCPT-{datetime.now().strftime('%y%m%d%H%M%S')}"`.
- **Database constraint**: Missing.
- **Scope**: Unique per company.
- **Concurrency behavior**: UNSAFE. Concurrent requests within the same second will collide.
- **Retry behavior**: Generates new number on retry.
- **Transaction behavior**: N/A
- **Offline behavior**: N/A
- **Current risk**: High.
- **Required fix**: Implement `ReceiptSequence`. Add unique constraint.

## 6. Master Data Codes (Client, Supplier, Product, RawMaterial, Warehouse)
- **Entity**: `Client`, `Supplier`, `Product`, `RawMaterial`, `Warehouse`
- **Field**: `code`
- **Generation mechanism**: User inputted via API.
- **Database constraint**: Missing `UNIQUE(company_id, code)` across all of them.
- **Scope**: Unique per company.
- **Concurrency behavior**: Race condition can allow duplicates.
- **Retry behavior**: Can create duplicates.
- **Transaction behavior**: N/A
- **Offline behavior**: N/A
- **Current risk**: High (Data corruption risk).
- **Required fix**: Add `UniqueConstraint("company_id", "code")` to all master data models.

## 7. Worker Code (`Worker.worker_code`)
- **Entity**: `Worker`
- **Field**: `worker_code`
- **Generation mechanism**: User inputted.
- **Database constraint**: EXISTS (`uq_company_worker_code`).
- **Scope**: Unique per company.
- **Concurrency behavior**: Safe (DB will reject).
- **Retry behavior**: Safe (DB will reject).
- **Transaction behavior**: Safe.
- **Offline behavior**: N/A
- **Current risk**: Low.
- **Required fix**: None needed for constraint, but API should handle `IntegrityError` gracefully.
