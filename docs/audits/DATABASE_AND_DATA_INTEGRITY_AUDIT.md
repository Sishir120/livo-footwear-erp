# LIVO FOOTWEAR ERP — DATABASE AND DATA INTEGRITY AUDIT

**Audit Date:** 2026-10-14  
**Auditor Roles:** Principal Database Reliability Engineer (DBRE), Lead Database Architect  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Target Branch:** `release/v1.0.0-staging`  

---

## 1. Executive Database Verdict

| Area | Status | Evidence & Risk |
|---|:---:|---|
| **Schema Definition** | **SOLID** | 36 relational tables; BigInteger paisa for financial fields; explicit unique constraints on document numbering. |
| **Migration Graph** | **RECONSTRUCTED & COHERENT** | 21 migrations; merge point at `013_merge_heads` resolves branch divergence; single current head `020_fixed_assets_waste_and_expenses`. |
| **Startup Migration Runner** | **CRITICAL DEFECT IN BASELINE** | Baseline commit `47cf8f5` catches migration errors with bare `print` and continues startup. Stamping logic was heuristic. |
| **Concurrency & Negative Stock** | **PROVEN ROBUST** | PostgreSQL advisory locks `(company_id << 32) | product_id` + process mutex prevent race conditions. |

---

## 2. Reconstructed Alembic Migration Graph

The complete graph reconstructed from `backend/migrations/versions/` comprises 21 revisions:

```text
                                [001_baseline_schema]
                                         │
                                [002_add_invoice_unique_constraint]
                                         │
                                [003_add_stock_snapshots_and_bom]
                                         │
                                [004_add_invoice_sequences]
                                         │
                                [005_stock_card_ledger]
                                         │
                                [006_receivables_subledger]
                                         │
                                [007_production_sync_engine]
                                         │
                                [008_hr_management]
                                         │
                                [009_gallery_and_analytics] (Branch Point)
                                    ┌────┴─────────────────────────────┐
                                    ▼                                  ▼
                    [762ea2a34ccb_convert_float]        [010_client_change_requests_core]
                                    │                                  │
                    [010_idempotency_records]                          │
                                    │                                  │
                    [012_add_c15_indexes]                              │
                                    └────┬─────────────────────────────┘
                                         ▼
                                [013_merge_heads] (Merge Point)
                                         │
                                [014_raw_material_ledger_and_landed_cost]
                                         │
                                [015_sales_dispatch_and_expenses]
                                         │
                                [016_production_batch_color_and_gallery_link]
                                         │
                                [017_hr_worker_citizenship]
                                         │
                                [018_hr_compensation_and_installment_engine]
                                         │
                                [019_advance_installment_recovery_engine]
                                         │
                                [020_fixed_assets_waste_and_expenses] (CURRENT HEAD)
```

### Supported Starting States & Upgrade Determinism:
1. **Fresh Database from Zero (`<base>`):**
   `alembic upgrade head` executes deterministically from an empty schema through all 21 revisions to head `020`.
2. **Legacy Checkpoint 9 Schema:**
   Upgrades through branch `762ea2a34ccb` (which drops legacy prototype journal tables safely) and merges cleanly at `013`.
3. **Downgrade Limitations:**
   Revisions `013` through `020` contain minimal or no-op downgrade methods. Reverting migrations in production requires restore from backup.

---

## 3. Analysis of Startup Migration Behavior

### [DB-01] Startup Continuation on Migration Failure (Committed Baseline Flaw)
- **Affected File:** `backend/app/main.py:16-34` (Commit `47cf8f5`)
- **Vulnerability:**
  In commit `47cf8f5`, the application lifecycle executes migrations inside a try-block that catches all exceptions:
  ```python
  try:
      ...
      command.upgrade(alembic_cfg, "head")
  except Exception as e:
      print(f"Lifespan DB setup notice: {e}")
  ```
  If a migration fails mid-way (e.g. database network timeout, lock timeout, constraint violation), the exception is swallowed and printed to stdout, and FastAPI **continues running and starts serving live web traffic on a corrupted or partial schema!**
- **Uncommitted Local Remediation:**
  Local working directory contains `AUTO_MIGRATE` toggle and explicit `raise RuntimeError` on migration failure. This change must be formally committed before production release.

### [DB-02] Heuristic Alembic Stamping
- **Affected File:** `backend/app/main.py:27-29` (Commit `47cf8f5`)
- **Risk:**
  `if "companies" in existing_tables and "alembic_version" not in existing_tables: command.stamp(alembic_cfg, "002_invoice_uq")`
  This heuristic stamped the revision without verifying whether columns added in `002` actually existed.

---

## 4. Concurrency, Row Locking, and Negative Stock Invariants

### 4.1 Stock Movement Concurrency Architecture
Footwear ERPs must strictly forbid negative inventory. In high-concurrency wholesale environments where multiple salesmen dispatch orders simultaneously, naive read-then-write creates stock corruption.

The codebase implements a two-tier defense:
1. **Process-Level Distributed Mutex:**
   `get_stock_mutex(company_id, product_id)` ensures only one thread within an application process updates a specific product variant at a time.
2. **PostgreSQL 64-Bit Transaction Advisory Lock:**
   `acquire_stock_advisory_lock(db, company_id, product_id)` calls `pg_advisory_xact_lock((company_id << 32) | product_id)`.
   Because PostgreSQL advisory locks are bound to the transaction, any concurrent transaction across any backend instance or background worker is blocked until the active transaction commits or rolls back.
3. **Pessimistic Row Lock & Snapshot Verification:**
   Inside the transaction boundary, `Product` is locked with `with_for_update()`. The current available balance is computed from the latest `StockSnapshot` plus subsequent ledger entries. If `current_balance - requested_quantity < 0`, an HTTP 422 `INSUFFICIENT_STOCK` is raised and the transaction rolls back cleanly with zero stock mutation.

### 4.2 Document Numbering Concurrency Architecture
- Invoices and Payment Receipts use `generate_document_number` (`backend/app/core/sequence.py`).
- Protected by `acquire_document_sequence_advisory_lock(db, company_id, doc_type)`.
- Enforces strictly sequential numbering (e.g. `INV-000001`, `RCPT-000001`) with zero gaps and zero duplicates, satisfying Nepal IRD tax invoice compliance.

---

## 5. Schema Data Types and Financial Precision

1. **Integer Paisa Architecture (1 NPR = 100 Paisa):**
   - Monetary values across all new subledgers (`ReceivableEntry`, `WorkerAdvance`, `WorkerMonthlyRecord`, `FactoryExpense`, `FixedAsset`) use `BigInteger` storing integer paisa.
   - Prevents floating-point precision loss and round-trip truncation.
2. **Numeric Fallback:**
   - Legacy tables (`products.unit_price`, `raw_materials.standard_cost`) use `sa.Numeric(precision=12, scale=2)`.
3. **Bikram Sambat Dual Date Architecture:**
   - Transaction tables maintain both `date_ad` (`sa.Date`, canonical index) and `date_bs` (`sa.String(10)`, YYYY-MM-DD formatted for display).
   - Ensured date-only UTC invariance, preventing midnight timezone drift.
