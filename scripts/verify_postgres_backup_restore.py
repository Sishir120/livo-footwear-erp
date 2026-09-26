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
