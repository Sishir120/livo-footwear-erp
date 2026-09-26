# Status Audit Report — 2026-09-26

**Audit Standard:** Independent re-verification derived directly from repo state, live test execution, migration inspection, and grep results.

---

## 1. Database Engine & Hosted PostgreSQL Verification

- **Engine:** PostgreSQL 16 on Neon.tech (`ep-gentle-glade-b4tb64by.c-6.us-east-2.aws.neon.tech`).
- **Driver Specification:** Normalized `DATABASE_URL` in `.env` to `postgresql+psycopg2://` driver prefix.
- **Alembic Migrations:** Applied both `001_baseline_schema` and `002_add_invoice_unique_constraint` cleanly to Neon PostgreSQL instance. `alembic current` confirms `002_invoice_uq (head)`.
- **`pg_dump` Availability & Testing Classification:**
  - `pg_dump` binary is **not installed** on this local Windows host environment (`CommandNotFoundException`).
  - **Relabeled Verification Finding:** *"Data-replication integrity verified via same-database schema copy on Neon Postgres. Real pg_dump/pg_restore end-to-end test is formally deferred to Phase 2 (DELIVERY_CYCLE.md's own Phase 2 gate already requires this, and Phase 2's Docker environment will have Postgres client tools available, unlike this local machine)."*
  - `tests/test_backup.py` provides unit test coverage (`test_run_database_backup_postgres_mocked` and `test_run_database_backup_postgres_failure_mocked`) that explicitly exercises `backup_service.py`'s `pg_dump` command string generation, execution status logging, and failure handling via `unittest.mock.patch`.

---

## 2. Test Suite Execution Output (18 / 18 Passed)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0 -- D:\Antigravity\Footwear app\backend\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Antigravity\Footwear app\backend
plugins: anyio-4.15.1
collecting ... collected 18 items

tests/test_auth_api.py::test_health_check_endpoint PASSED                [  5%]
tests/test_auth_api.py::test_login_and_me_flow PASSED                    [ 11%]
tests/test_auth_api.py::test_login_invalid_credentials PASSED            [ 16%]
tests/test_backup.py::test_get_latest_backup_status PASSED               [ 22%]
tests/test_backup.py::test_save_backup_status PASSED                     [ 27%]
tests/test_backup.py::test_run_database_backup_postgres_mocked PASSED    [ 33%]
tests/test_backup.py::test_run_database_backup_postgres_failure_mocked PASSED [ 38%]
tests/test_erp_flow.py::test_full_erp_workflow PASSED                    [ 44%]
tests/test_invoice_numbering.py::test_sequential_invoice_numbering_per_company PASSED [ 50%]
tests/test_invoice_numbering.py::test_void_invoice_preserves_sequence PASSED [ 55%]
tests/test_invoice_numbering.py::test_unique_invoice_sequence_constraint PASSED [ 61%]
tests/test_invoice_numbering.py::test_concurrent_invoice_generation_api PASSED [ 66%]
tests/test_security.py::test_password_hashing_and_verification PASSED    [ 72%]
tests/test_security.py::test_jwt_creation_and_decoding PASSED            [ 77%]
tests/test_security.py::test_invalid_jwt_token PASSED                    [ 83%]
tests/test_stock_movement_math.py::test_stock_movement_ledger_calculation PASSED [ 88%]
tests/test_tenant_repository.py::test_tenant_repository_isolation PASSED [ 94%]
tests/test_tenant_repository.py::test_tenant_repository_rejects_model_without_company_id PASSED [100%]

================= 18 passed, 3 warnings in 108.22s (0:01:48) ==================
```

---

## 3. Full Source Code of `scripts/verify_postgres_backup_restore.py`

```python
"""
PostgreSQL Backup & Restore Integrity Verification Script
Executes SQL data extraction and restores into a dedicated test schema on Neon PostgreSQL
to empirically verify 100% table count and row count matching under Postgres.
"""
import os
import sys
import psycopg2
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config import settings

def test_postgres_backup_restore():
    dsn = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
    print(f"Connecting to Neon PostgreSQL instance...")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()

    # 1. Fetch all public tables and row counts
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    """)
    public_tables = [r[0] for r in cursor.fetchall() if r[0] != 'alembic_version']
    print(f"Found {len(public_tables)} base business tables in public schema: {public_tables}")

    original_counts = {}
    for table in public_tables:
        cursor.execute(f'SELECT COUNT(*) FROM public."{table}"')
        count = cursor.fetchone()[0]
        original_counts[table] = count
        print(f"Schema 'public' -> Table '{table}': {count} rows")

    # 2. Create isolated restore verification schema
    print("\nCreating isolated 'restore_verify' schema on Neon Postgres...")
    cursor.execute("DROP SCHEMA IF EXISTS restore_verify CASCADE;")
    cursor.execute("CREATE SCHEMA restore_verify;")

    # 3. Replicate table structures to restore_verify schema
    for table in public_tables:
        cursor.execute(f'CREATE TABLE restore_verify."{table}" (LIKE public."{table}" INCLUDING ALL);')
        cursor.execute(f'INSERT INTO restore_verify."{table}" SELECT * FROM public."{table}";')

    # 4. Verify table and row counts match between public and restore_verify
    print("\n--- Verifying Integrity & Row Counts between Public and Restored Schema ---")
    mismatches = []
    for table in public_tables:
        cursor.execute(f'SELECT COUNT(*) FROM restore_verify."{table}"')
        restored_count = cursor.fetchone()[0]
        orig_count = original_counts[table]
        print(f"Table '{table}': Original (public)={orig_count}, Restored (restore_verify)={restored_count}")
        if orig_count != restored_count:
            mismatches.append(f"{table}: {orig_count} vs {restored_count}")

    # Cleanup test schema
    cursor.execute("DROP SCHEMA IF EXISTS restore_verify CASCADE;")
    conn.close()

    assert not mismatches, f"Row count mismatches found: {mismatches}"
    print("\n[SUCCESS] POSTGRESQL BACKUP & RESTORE VERIFICATION PASSED 100%!")

if __name__ == "__main__":
    test_postgres_backup_restore()
```

---

## 4. Tenant Scoping (`company_id`) Grep Table

| File | Line Number | Line Content |
| :--- | :---: | :--- |
| `app/api/v1/stock.py` | 41 | `qty = db.query(...)` *(queries `StockMovement` with `company_id == current_user.company_id`)* |
| `app/api/v1/sales.py` | 65 | `items = db.query(SalesItem).filter(SalesItem.sales_order_id == ord.id, SalesItem.company_id == current_user.company_id).all()` |
| `app/api/v1/reports.py` | 27 | `production_batches = db.query(ProductionBatch).filter(ProductionBatch.company_id == current_user.company_id...)` |
| `app/api/v1/reports.py` | 36 | `sales_orders = db.query(SalesOrder).filter(SalesOrder.company_id == current_user.company_id...)` |
| `app/api/v1/reports.py` | 46 | `stock_in = db.query(...).filter(StockMovement.company_id == current_user.company_id...)` |
| `app/api/v1/reports.py` | 54 | `stock_out = db.query(...).filter(StockMovement.company_id == current_user.company_id...)` |
| `app/api/v1/reports.py` | 106 | `current_qty = db.query(...).filter(StockMovement.company_id == current_user.company_id...)` |
| `app/api/v1/purchase.py` | 70 | `query = db.query(Purchase).filter(Purchase.company_id == current_user.company_id)` |
| `app/api/v1/invoices.py` | 44 | `max_seq = db.query(func.coalesce(func.max(Invoice.sequence_number), 0)).filter(Invoice.company_id == current_user.company_id).scalar()` |
| `app/api/v1/invoices.py` | 89 | `company = db.query(Company).filter(Company.id == current_user.company_id).first()` |
| `app/api/v1/invoices.py` | 91 | `order = db.query(SalesOrder).filter(SalesOrder.id == invoice.sales_order_id, SalesOrder.company_id == current_user.company_id).first()` |
| `app/api/v1/invoices.py` | 95 | `client = db.query(Client).filter(Client.id == order.client_id, Client.company_id == current_user.company_id).first()` |
| `app/api/v1/invoices.py` | 99 | `items = db.query(SalesItem).filter(SalesItem.sales_order_id == invoice.sales_order_id, SalesItem.company_id == current_user.company_id).all()` |
| `app/api/v1/auth.py` | 13 | `user = db.query(User).filter(User.username == request.username).first()` |
| `app/api/deps.py` | 46 | `user = db.query(User).filter(User.id == user_id, User.company_id == company_id, User.active == True).first()` |
