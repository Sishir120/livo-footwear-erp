# LIVO FOOTWEAR ERP — MIGRATION STRATEGY & LIFECYCLE GUIDE
**Checkpoint 11 — Database Integrity, Migrations, Backups & Disaster Recovery**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Migration System Architecture

LIVO Footwear ERP manages all database schema evolutions using [Alembic](https://alembic.sqlalchemy.org/) under SQLAlchemy. 

### 1.1 Configuration Files
* **Configuration:** [`backend/alembic.ini`](file:///d:/Antigravity/Footwear%20app/backend/alembic.ini)
* **Environment Runner:** [`backend/migrations/env.py`](file:///d:/Antigravity/Footwear%20app/backend/migrations/env.py)
* **Version Scripts:** [`backend/migrations/versions/`](file:///d:/Antigravity/Footwear%20app/backend/migrations/versions/)
* **Target Metadata:** Bound to `Base.metadata` from [`app.db.session`](file:///d:/Antigravity/Footwear%20app/backend/app/db/session.py).

### 1.2 Multi-Dialect Support & Batch Mode
Different SQL engines handle schema alterations (DDL) differently:
* **PostgreSQL:** Fully supports transactional DDL. Tables, columns, and constraints can be altered atomically inside a single `BEGIN ... COMMIT` block.
* **SQLite:** Does not support direct `ALTER TABLE ... ALTER COLUMN` syntax. To support seamless development, testing, and migration verification across both engines:
  1. `render_as_batch=True` is enabled in `backend/migrations/env.py` for both online and offline contexts.
  2. DDL scripts inspect `conn.dialect.name` to execute engine-specific syntax safely (e.g. `ALTER COLUMN TYPE NUMERIC` is scoped to PostgreSQL).
  3. Migration `010_idempotency_records` checks existing table reflection prior to running `create_table`, guaranteeing idempotent execution.

---

## 2. Linear Migration History (Verified Single-Head)

The repository maintains a strictly linear, uninterrupted migration graph with zero branching or split heads:

```
<base>
  │
  ▼
001_baseline (Baseline ERP schema: companies, users, products, sales, warehouses)
  │
  ▼
002_invoice_uq (Invoice number & sequence uniqueness per company)
  │
  ▼
003_snapshots_bom (Stock snapshots and Bill of Materials models)
  │
  ▼
004_invoice_sequences (Atomic invoice sequence allocation table)
  │
  ▼
005_stock_card_ledger (Append-only stock ledger & movement types)
  │
  ▼
006_receivables_subledger (Accounts receivable double-entry ledger & payment allocations)
  │
  ▼
007_production_sync_engine (Offline sync queue & device reconciliation)
  │
  ▼
008_hr_management (Workers, attendance, wage calculations & payouts)
  │
  ▼
009_gallery_and_analytics (Product gallery assets and analytics aggregates)
  │
  ▼
762ea2a34ccb (Precision upgrade: numeric migration for monetary & quantitative columns)
  │
  ▼
010_idempotency_records (HEAD: Server-side idempotency records table & tenant sync index)
```

### 2.1 Verification Evidence
Running standard Alembic inspection commands confirms exact linearity:
```bash
$ python -m alembic heads
010_idempotency_records (head)

$ python -m alembic current
010_idempotency_records (head)
```

---

## 3. Zero-Downtime Deployment & Expand/Contract Pattern

In production deployments, the database schema and running application instances must remain mutually compatible at all times. Destructive schema changes must NEVER be deployed simultaneously with application code.

### 3.1 The 4-Phase Expand/Contract Lifecycle

```
[Phase 1: EXPAND]
  - Add new column as NULLABLE or with database-level DEFAULT.
  - Add new indexes or new tables.
  - Deploy migration to production database.
  - Both old and new application code continue running without error.

[Phase 2: DUAL WRITE]
  - Deploy application code that reads from old column and writes to BOTH old and new columns.
  - Monitor error rates and application telemetry.

[Phase 3: DATA BACKFILL]
  - Run background script or chunked batch UPDATE to migrate historical records from old column to new column.
  - Verify 100% row count and value reconciliation.

[Phase 4: CONTRACT]
  - Switch application reads to the new column exclusively.
  - Deploy migration to alter column to NOT NULL if required.
  - Remove deprecated old column in a subsequent scheduled release.
```

---

## 4. Migration Rollback & Downgrade Strategy

1. **Reversible Schema Operations:**
   * Adding tables, adding nullable columns, adding indexes, or adding non-enforcing views can be reversed cleanly via standard Alembic `downgrade()`.
2. **Irreversible Data Operations:**
   * Column drops, table drops, or one-way cryptographic hashing operations are intentionally marked irreversible.
   * **Mandatory Policy:** Before executing any migration that transforms, aggregates, or alters column storage, a full database snapshot must be executed via `run_database_backup()`.
   * If a migration fails mid-way, PostgreSQL rolls back the DDL transaction automatically, leaving the database at the prior revision.

---

## 5. Deployment Pre-Flight Checklist

Before applying any migration to production:
1. `alembic check` / `alembic heads` confirms exactly ONE head.
2. Verified against an isolated disposable database via:
   ```bash
   python backend/scripts/verify_backup_restore.py
   ```
3. Full test suite executes cleanly:
   ```bash
   python -m pytest backend/tests/test_checkpoint_11_database.py
   ```
4. Production backup snapshot taken and confirmed in cloud storage.
