# LIVO Footwear ERP — Day 4: Failure, Concurrency, and Retry Results

**Audit Date:** 2026-10-16  
**Auditor:** Antigravity Engineering (Resilience & Concurrency Testing)  
**Database Engine:** PostgreSQL 16.x (`embedded_postgres` on dynamic port) + SQLite concurrency harnesses  
**Overall Status:** **PASSED (ALL INVARIANTS CONSERVED UNDER CONCURRENCY & FAILURE)**

---

## 1. Executive Summary

This report presents empirical findings from executing failure injection, race condition, network retry, and transactional boundary tests across LIVO Footwear ERP.

All tests were executed against isolated disposable databases using multi-threaded execution harnesses (`ThreadPoolExecutor`) and simulated failure hooks.

---

## 2. Test Execution & Results Matrix

| Failure / Concurrency Scenario | Test Harness File | Mechanism Tested | Expected Invariant | Persisted Outcome | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Client Retry After Network Timeout** | `test_idempotency.py` | `IdempotencyMiddleware` via `X-Idempotency-Key` | 0 duplicate records; return cached response | Exact 1 record persisted; subsequent request receives cached response | **PASSED** |
| **Concurrent Duplicate Requests (50 Threads)** | `test_idempotency.py` | PostgreSQL row lock & lease state machine | 1 execution succeeds; 49 receive cached/locked response | Exactly 1 database mutation; 0 duplicate movements or invoices | **PASSED** |
| **Concurrent Stock Dispatch (Race Condition)** | `test_concurrency_race.py`, `test_phase_5_3_transaction_boundary.py` | `acquire_stock_mutation_lock` advisory lock | Stock never goes negative; requests serialized | Initial dispatches succeed up to on-hand quantity; remainder rejected with 400 | **PASSED** |
| **Concurrent Dispatches on Transfer** | `test_phase_5_3_transaction_boundary.py` | `acquire_stock_transfer_lock` | Exactly 1 dispatch succeeds | 1 thread transitions transfer to `IN_TRANSIT`; second thread rejected with 400 | **PASSED** |
| **Concurrent Receipts on In-Transit Transfer** | `test_phase_5_3_transaction_boundary.py` | Transfer row lock + item lock | Total received $\le$ dispatched | Received quantities strictly capped at dispatched; over-receipt rejected | **PASSED** |
| **Receipt Racing Transfer Cancellation** | `test_phase_5_3_transaction_boundary.py` | Serialization under transfer lock | No stock duplication or disappearance | Either receipt succeeds first (cancellation rejected) or cancellation succeeds (receipt rejected) | **PASSED** |
| **Concurrent Credit Notes Against Invoice** | `test_phase_5_3_transaction_boundary.py` | Invoice row lock + ceiling check | Total credit $\le$ invoice total | Simultaneous credit notes serialize; sum never exceeds original invoice | **PASSED** |
| **Crash / Failure After Source Stock Deduction** | `test_phase_5_3_transaction_boundary.py` | Atomic SQLAlchemy transaction boundary | All-or-nothing rollback | Source stock deduction and transfer status transition roll back completely | **PASSED** |
| **Crash / Failure During Destination Receipt** | `test_phase_5_3_transaction_boundary.py` | Atomic transaction boundary | All-or-nothing rollback | Destination inventory addition and status roll back completely | **PASSED** |
| **Stale Lease Recovery on Crashed Worker** | `test_idempotency.py` | 60-second lease timeout in `IdempotencyRecord` | Stale locks expire, allowing retry | After lease expiration, subsequent retry safely executes | **PASSED** |
| **Stale Frontend Submitting Depleted Stock** | `test_checkpoint_18_live_acceptance.py` | Pre-commit on-hand stock validation | Rejection without partial writes | Returns 400 Insufficient Stock; inventory balances untouched | **PASSED** |
| **Expired Auth & Cross-Company Access** | `test_day_2_rbac_hardening.py`, `test_checkpoint_18_live_acceptance.py` | JWT expiration & tenant scoping filter | 401/403 rejection; 0 mutations | Access denied; zero records created or modified | **PASSED** |
| **Database Disconnect During Transaction** | `test_checkpoint_11_database.py` | Connection pool health probe & transaction rollback | Incomplete writes discarded | Engine catches disconnection, cleans up pool, discards dirty state | **PASSED** |
| **Startup Migration Failure (SEC-02)** | `test_checkpoint_18_live_acceptance.py`, `app/main.py` | Lifespan fail-fast abort | Immediate process crash | Raises `RuntimeError`; never serves traffic on broken schema | **PASSED** |
| **Interrupted Backup Job** | `test_day_3_restore_drill.py`, `test_day_4_file_and_database_recovery.py` | Atomic staging `.tmp` $\rightarrow$ final path | No corrupted files left in inventory | Partial `.tmp` file unlinked; status marked `"failed"` | **PASSED** |
| **Corrupted SQL Dump on Restore** | `test_day_3_restore_drill.py` | `psql -v ON_ERROR_STOP=1` | Exit with error; status `"failed"` | Subprocess returns code 3; restore halts immediately | **PASSED** |

---

## 3. Concurrency Protection Architecture

LIVO Footwear ERP enforces concurrency safety across three distinct architectural layers:

1. **PostgreSQL Advisory Locks (`app/core/locks.py`):**
   - Stock mutation locks (`acquire_stock_mutation_lock`): Serializes inventory changes on a specific `(company_id, warehouse_id, product_id, size)`.
   - Transfer locks (`acquire_stock_transfer_lock`): Serializes dispatches and receipts on a specific `transfer_id`.
   - Migration coordination lock (`pg_advisory_lock(8877665544332211)`): Coordinates multi-replica container startups.
2. **Row-Level Database Locks (`with_for_update()`):**
   - Worker rows locked during advance issuance and repayment to enforce strict FIFO ledger consistency.
   - Transfer rows and items locked during dispatch and receipt transitions.
   - Sales order and invoice rows locked during payment allocations.
3. **Application Idempotency Middleware (`app/middleware/idempotency.py`):**
   - Traverses incoming requests for `X-Idempotency-Key`.
   - Enforces single execution lease; concurrent identical requests await the leader or receive the cached response.
   - Rejects identical keys with mismatched payloads (HTTP 409 Conflict).
