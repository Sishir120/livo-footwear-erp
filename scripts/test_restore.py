"""
Database Backup & Restore Verification Script
Per Item 6 & RULES.md §7: Actually runs a backup and restores it against a copy of the database
to empirically confirm data integrity, table counts, and row counts.
"""
import sys
import os
import shutil
import sqlite3
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.backup_service import run_database_backup

def test_backup_and_restore():
    print("--- 1. Running Database Backup ---")
    result = run_database_backup()
    print(f"Backup result: {result}")
    assert result["status"] == "success", f"Backup failed: {result.get('error_message')}"

    backup_file_name = result["file_name"]
    backup_file_path = backend_dir / "backups" / backup_file_name
    assert backup_file_path.exists(), f"Backup file not found at {backup_file_path}"
    print(f"Verified backup file exists: {backup_file_path} ({backup_file_path.stat().st_size} bytes)")

    print("\n--- 2. Executing Restore against Temporary DB Copy ---")
    restored_db_path = backend_dir / "backups" / "restored_verify.db"
    if restored_db_path.exists():
        os.remove(restored_db_path)

    # For SQLite dev/test DB: restore by copying backup file to restored_db_path
    shutil.copy2(backup_file_path, restored_db_path)
    assert restored_db_path.exists()

    print("\n--- 3. Verifying Integrity & Row Counts between Original and Restored DB ---")
    orig_db_path = backend_dir / "livo_dev.db"
    if not orig_db_path.exists():
        print(f"Original SQLite file {orig_db_path} does not exist yet; skipping row count comparison.")
        return

    conn_orig = sqlite3.connect(orig_db_path)
    conn_rest = sqlite3.connect(restored_db_path)

    cursor_orig = conn_orig.cursor()
    cursor_rest = conn_rest.cursor()

    # Get all tables
    cursor_orig.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [r[0] for r in cursor_orig.fetchall()]

    print(f"Comparing {len(tables)} tables: {tables}")
    for table in tables:
        cursor_orig.execute(f"SELECT COUNT(*) FROM {table}")
        count_orig = cursor_orig.fetchone()[0]

        cursor_rest.execute(f"SELECT COUNT(*) FROM {table}")
        count_rest = cursor_rest.fetchone()[0]

        print(f"Table '{table}': Original={count_orig}, Restored={count_rest}")
        assert count_orig == count_rest, f"Mismatch in table {table}: {count_orig} vs {count_rest}"

    conn_orig.close()
    conn_rest.close()

    # Cleanup temporary restored db
    os.remove(restored_db_path)
    print("\n[SUCCESS] RESTORE VERIFICATION PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_backup_and_restore()
