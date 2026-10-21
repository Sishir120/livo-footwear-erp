"""
LIVO Footwear ERP — Sprint 1B.1
Isolated Validation Suite for Migration 028 (DDL Only)
======================================================
Validates all 11 required authorization points in isolated, disposable environments.
Under NO circumstances will this script connect to or modify livo_dev.db or backend/livo_dev.db.
"""
import os
import sys
import tempfile
import pathlib
import hashlib
from decimal import Decimal
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text, event
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory

# Ensure backend directory is in sys.path
BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

INITIAL_DEV_DB_HASH = "B7D90AD92BF216B40710AAB03B022BBC0ABE3D7E459B73B5E2A7863C0E361226"
INITIAL_BACKEND_DEV_DB_HASH = "81F47191CBEBC8D1B03729E659CE679C9FF27A54F0359CBA146AF846A1390A7E"


def get_file_sha256(filepath: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def make_alembic_config(db_url: str) -> Config:
    ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def test_validation_point_10_single_alembic_head():
    """Point 10: Single Alembic head verification."""
    ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 head, got: {heads}"
    assert heads[0] == "030_wave_p1_sales_invoicing_remediation", f"Unexpected head: {heads[0]}"


def test_validation_points_1_through_9():
    """
    Executes Points 1 through 9 sequentially on disposable isolated database:
    1. Fresh upgrade to revision 028
    2. Upgrade from revision 027 with synthetic operational data
    3. Cross-company foreign-key rejection
    4. Duplicate reversal rejection
    5. Rejection of updates and deletes to posted vouchers and entries
    6. Valid draft editing and valid reversal behavior
    7. Atomic rollback after an injected failure
    8. Downgrade to revision 027
    9. Upgrade again after downgrade
    """
    # Create disposable SQLite database file in a temp directory
    temp_dir = tempfile.mkdtemp()
    temp_db_path = pathlib.Path(temp_dir) / "disposable_test_028.db"
    db_url = f"sqlite:///{temp_db_path.as_posix()}"

    os.environ["DATABASE_URL"] = db_url
    alembic_cfg = make_alembic_config(db_url)

    # -------------------------------------------------------------------------
    # POINT 1: Fresh upgrade to revision 028 on a completely blank database
    # -------------------------------------------------------------------------
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names())
    required_tables = {
        "branches",
        "account_groups",
        "ledger_accounts",
        "accounting_periods",
        "journal_vouchers",
        "journal_entries",
    }
    assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

    # Verify Wave P1 schema additions from revisions 029 and 030 are present in head
    wave_p1_tables = {"credit_notes", "credit_note_items"}
    assert wave_p1_tables.issubset(tables), f"Missing Wave P1 tables from revision 030: {wave_p1_tables - tables}"
    client_cols = {c["name"] for c in inspector.get_columns("clients")}
    assert "pan_number" in client_cols, "clients.pan_number from revision 029 missing in migrated head!"

    # Verify branches has uq_branches_company_id
    uqs = [uq["name"] for uq in inspector.get_unique_constraints("branches")]
    assert "uq_branches_company_id" in uqs or any("company_id" in uq.get("column_names", []) and "id" in uq.get("column_names", []) for uq in inspector.get_unique_constraints("branches"))

    engine.dispose()
    if temp_db_path.exists():
        temp_db_path.unlink()

    # -------------------------------------------------------------------------
    # POINT 2: Upgrade from revision 027 with synthetic operational data
    # -------------------------------------------------------------------------
    command.upgrade(alembic_cfg, "027_operational_numeric_precision")
    engine = create_engine(db_url)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma2(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with engine.begin() as conn:
        # Insert 2 companies
        conn.execute(text("INSERT INTO companies (id, code, name, pan_number) VALUES (1, 'COMP1', 'Company 1', '111111111')"))
        conn.execute(text("INSERT INTO companies (id, code, name, pan_number) VALUES (2, 'COMP2', 'Company 2', '222222222')"))
        # Insert branches
        conn.execute(text("INSERT INTO branches (id, company_id, code, name, type) VALUES (1, 1, 'BR1', 'Branch 1', 'RETAIL_OUTLET')"))
        conn.execute(text("INSERT INTO branches (id, company_id, code, name, type) VALUES (2, 2, 'BR2', 'Branch 2', 'RETAIL_OUTLET')"))
        # Insert users
        conn.execute(text("INSERT INTO users (id, company_id, branch_id, name, username, email, password_hash, role, active) VALUES (1, 1, 1, 'Admin 1', 'admin1', 'admin1@livo.test', 'hash', 'admin', 1)"))
        conn.execute(text("INSERT INTO users (id, company_id, branch_id, name, username, email, password_hash, role, active) VALUES (2, 2, 2, 'Admin 2', 'admin2', 'admin2@livo.test', 'hash', 'admin', 1)"))

    # Upgrade from 027 to 028
    command.upgrade(alembic_cfg, "028_register_double_entry_accounting_ledger")

    with engine.begin() as conn:
        branch_count = conn.execute(text("SELECT COUNT(*) FROM branches")).scalar()
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        assert branch_count == 2
        assert user_count == 2

    # -------------------------------------------------------------------------
    # POINT 3: Cross-company foreign-key rejection for tenant-scoped relationships
    # -------------------------------------------------------------------------
    with engine.begin() as conn:
        # Create valid groups and periods in Company 1 and Company 2
        conn.execute(text("INSERT INTO account_groups (id, company_id, code, name, group_type, level) VALUES (1, 1, '1000', 'Assets 1', 'ASSET', 1)"))
        conn.execute(text("INSERT INTO account_groups (id, company_id, code, name, group_type, level) VALUES (2, 2, '1000', 'Assets 2', 'ASSET', 1)"))

        conn.execute(text("INSERT INTO accounting_periods (id, company_id, fiscal_year, period_number, period_name, start_date_ad, end_date_ad, start_date_bs, end_date_bs) VALUES (1, 1, '2082/83', 1, 'Shrawan', '2025-07-16', '2025-08-16', '2082-04-01', '2082-04-32')"))
        conn.execute(text("INSERT INTO accounting_periods (id, company_id, fiscal_year, period_number, period_name, start_date_ad, end_date_ad, start_date_bs, end_date_bs) VALUES (2, 2, '2082/83', 1, 'Shrawan', '2025-07-16', '2025-08-16', '2082-04-01', '2082-04-32')"))

        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (1, 1, 1, '1110', 'Cash 1', 'DEBIT')"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (2, 1, 1, '1120', 'Bank 1', 'DEBIT')"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (3, 2, 2, '1110', 'Cash 2', 'DEBIT')"))

    # Test cross-company branch reference on ledger_accounts (Company 1 referencing Branch 2)
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO ledger_accounts (id, company_id, branch_id, group_id, code, name, normal_balance) VALUES (99, 1, 2, 1, '1999', 'Bad Account', 'DEBIT')"))
    assert "FOREIGN KEY" in str(excinfo.value).upper() or "INTEGRITY" in str(excinfo.value).upper()

    # Test cross-company group reference on ledger_accounts (Company 1 referencing Group 2)
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (98, 1, 2, '1998', 'Bad Account 2', 'DEBIT')"))
    assert "FOREIGN KEY" in str(excinfo.value).upper() or "INTEGRITY" in str(excinfo.value).upper()

    # -------------------------------------------------------------------------
    # POINT 4: Duplicate reversal rejection via partial unique index
    # -------------------------------------------------------------------------
    with engine.begin() as conn:
        # Insert initial voucher as DRAFT, add entries, then transition to POSTED
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
            VALUES (100, 1, 'JV-00100', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 1000.00, 1000.00, 1)
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (1, 1, 100, 1, 1, 1000.00, 0.00)
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (2, 1, 100, 2, 2, 0.00, 1000.00)
        """))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 100"))

        # First reversal succeeds (create as DRAFT, then post)
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
            VALUES (101, 1, 'REV-00100', 'REVERSAL', 'DRAFT', '2025-07-21', '2082-04-06', 1000.00, 1000.00, 1, 100, 1)
        """))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 101"))

    # Second reversal for the same original voucher MUST be rejected
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
                VALUES (102, 1, 'REV-00100-DUP', 'REVERSAL', 'DRAFT', '2025-07-22', '2082-04-07', 1000.00, 1000.00, 1, 100, 1)
            """))
    assert "UNIQUE" in str(excinfo.value).upper() or "UQ_JV_REVERSAL_OF" in str(excinfo.value).upper()

    # -------------------------------------------------------------------------
    # POINT 5: Rejection of updates and deletes to posted vouchers and entries
    # -------------------------------------------------------------------------
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE journal_vouchers SET total_debit_base = 999.00 WHERE id = 100"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM journal_vouchers WHERE id = 100"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE journal_entries SET debit_amount_base = 999.00 WHERE id = 1"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM journal_entries WHERE id = 1"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    # -------------------------------------------------------------------------
    # POINT 6: Valid draft editing and valid reversal behavior
    # -------------------------------------------------------------------------
    with engine.begin() as conn:
        # Create a DRAFT voucher
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, narration, created_by_id)
            VALUES (200, 1, 'JV-DRAFT-1', 'JOURNAL', 'DRAFT', '2025-07-25', '2082-04-10', 500.00, 500.00, 'Original Narration', 1)
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base, narration)
            VALUES (201, 1, 200, 1, 1, 500.00, 0.00, 'Line 1 Original')
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base, narration)
            VALUES (202, 1, 200, 2, 2, 0.00, 500.00, 'Line 2 Original')
        """))

        # Edit draft voucher header
        conn.execute(text("UPDATE journal_vouchers SET narration = 'Updated Draft Narration' WHERE id = 200"))
        # Edit draft line item
        conn.execute(text("UPDATE journal_entries SET narration = 'Updated Line 1' WHERE id = 201"))

        # Verify edits took effect
        narr = conn.execute(text("SELECT narration FROM journal_vouchers WHERE id = 200")).scalar()
        assert narr == "Updated Draft Narration"
        line_narr = conn.execute(text("SELECT narration FROM journal_entries WHERE id = 201")).scalar()
        assert line_narr == "Updated Line 1"

        # Now post the voucher
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 200"))

    # Now that it's POSTED, verify it is immediately frozen
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE journal_vouchers SET narration = 'Tamper Attempt' WHERE id = 200"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    # -------------------------------------------------------------------------
    # POINT 7: Atomic rollback after an injected failure
    # -------------------------------------------------------------------------
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (500, 1, 'JV-ROLLBACK-TEST', 'JOURNAL', 'DRAFT', '2025-07-26', '2082-04-11', 200.00, 200.00, 1)
            """))
            # Injected violation: line violating debit XOR credit constraint (both > 0)
            conn.execute(text("""
                INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
                VALUES (501, 1, 500, 1, 1, 200.00, 200.00)
            """))
    except Exception:
        pass  # Expected rollback

    with engine.begin() as conn:
        rb_check = conn.execute(text("SELECT COUNT(*) FROM journal_vouchers WHERE id = 500")).scalar()
        assert rb_check == 0, "Transaction did not roll back atomically!"

    # -------------------------------------------------------------------------
    # POINT 8: Downgrade to revision 027
    # -------------------------------------------------------------------------
    command.downgrade(alembic_cfg, "027_operational_numeric_precision")

    inspector = sa.inspect(engine)
    post_dg_tables = set(inspector.get_table_names())
    assert "journal_entries" not in post_dg_tables
    assert "journal_vouchers" not in post_dg_tables
    assert "accounting_periods" not in post_dg_tables
    assert "ledger_accounts" not in post_dg_tables
    assert "account_groups" not in post_dg_tables

    with engine.begin() as conn:
        current_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert current_rev == "027_operational_numeric_precision"

    # -------------------------------------------------------------------------
    # POINT 9: Upgrade again after downgrade
    # -------------------------------------------------------------------------
    command.upgrade(alembic_cfg, "028_register_double_entry_accounting_ledger")

    inspector = sa.inspect(engine)
    reup_tables = set(inspector.get_table_names())
    assert required_tables.issubset(reup_tables)

    with engine.begin() as conn:
        current_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert current_rev == "028_register_double_entry_accounting_ledger"

    engine.dispose()
    if temp_db_path.exists():
        temp_db_path.unlink()


def check_protected_database_preservation(root_db_path: pathlib.Path, backend_db_path: pathlib.Path):
    """
    Evaluates preservation of protected developer databases:
    - If both exist (local workspace), verifies size and SHA-256 hash against baseline.
    - If neither exists (clean CI environment where untracked files are not checked out),
      explicitly skips with a reportable explanation.
    - If exactly one exists (anomalous partial state), fails explicitly.
    """
    root_exists = root_db_path.exists()
    backend_exists = backend_db_path.exists()

    if not root_exists and not backend_exists:
        pytest.skip(
            "[CI ENVIRONMENT] Protected developer databases (livo_dev.db, backend/livo_dev.db) "
            "are untracked and do not exist in clean checkout. Local file hash validation skipped."
        )

    if root_exists != backend_exists:
        pytest.fail(
            f"[ANOMALOUS DATABASE STATE] Expected both protected developer databases to be present or both absent. "
            f"Found: root_db={root_exists}, backend_db={backend_exists}."
        )

    dev_db_hash = get_file_sha256(root_db_path)
    backend_dev_db_hash = get_file_sha256(backend_db_path)

    assert dev_db_hash == INITIAL_DEV_DB_HASH, f"livo_dev.db hash changed! {dev_db_hash} != {INITIAL_DEV_DB_HASH}"
    assert backend_dev_db_hash == INITIAL_BACKEND_DEV_DB_HASH, f"backend/livo_dev.db hash changed! {backend_dev_db_hash} != {INITIAL_BACKEND_DEV_DB_HASH}"
    assert root_db_path.stat().st_size == 19320832, "livo_dev.db file size changed!"
    assert backend_db_path.stat().st_size == 11980800, "backend/livo_dev.db file size changed!"


def test_validation_point_11_protected_databases_unmutated():
    """Point 11: Confirmation that no protected database was opened for writing or modified."""
    dev_db = WORKSPACE_ROOT / "livo_dev.db"
    backend_dev_db = BACKEND_DIR / "livo_dev.db"
    check_protected_database_preservation(dev_db, backend_dev_db)


def test_validation_point_11_ci_absence_handling(tmp_path):
    """Focused test verifying CI absence correctly skips with reportable message."""
    missing_root = tmp_path / "absent_root.db"
    missing_backend = tmp_path / "absent_backend.db"
    with pytest.raises(pytest.skip.Exception) as exc_info:
        check_protected_database_preservation(missing_root, missing_backend)
    assert "[CI ENVIRONMENT]" in str(exc_info.value)


def test_validation_point_11_partial_anomaly_fails(tmp_path):
    """Focused test verifying anomalous single-database existence fails."""
    existing_root = tmp_path / "partial_root.db"
    existing_root.write_bytes(b"dummy")
    missing_backend = tmp_path / "absent_backend.db"
    with pytest.raises(pytest.fail.Exception) as exc_info:
        check_protected_database_preservation(existing_root, missing_backend)
    assert "[ANOMALOUS DATABASE STATE]" in str(exc_info.value)



def test_voucher_creation_lifecycle_invariants():
    """
    Sprint 1B.1.2: Enforce the voucher creation lifecycle invariants:
    1. Inserting a voucher as DRAFT succeeds when all other required data is valid.
    2. Direct insertion as POSTED fails.
    3. Inserting with another unsupported initial status fails.
    4. A valid DRAFT-to-POSTED transition still works.
    5. Updating or deleting a posted voucher still fails.
    6. Updating, deleting, or reassigning entries belonging to a posted voucher still fails.
    7. A valid separate-voucher reversal still works.
    8. Duplicate reversal protection remains intact.
    """
    temp_dir = tempfile.mkdtemp()
    temp_db_path = pathlib.Path(temp_dir) / "disposable_lifecycle_test.db"
    db_url = f"sqlite:///{temp_db_path.as_posix()}"
    alembic_cfg = make_alembic_config(db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with engine.begin() as conn:
        conn.execute(text("INSERT INTO companies (id, code, name, pan_number) VALUES (1, 'COMP1', 'Company 1', '111111111')"))
        conn.execute(text("INSERT INTO users (id, company_id, name, username, email, password_hash, role, active) VALUES (1, 1, 'Admin 1', 'admin1', 'admin1@livo.test', 'hash', 'admin', 1)"))
        conn.execute(text("INSERT INTO account_groups (id, company_id, code, name, group_type, level) VALUES (1, 1, '1000', 'Assets 1', 'ASSET', 1)"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (1, 1, 1, '1110', 'Cash 1', 'DEBIT')"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (2, 1, 1, '1120', 'Bank 1', 'DEBIT')"))

    # Invariant 1: Inserting a voucher as DRAFT succeeds
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
            VALUES (10, 1, 'JV-DRAFT-OK', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
        """))
        v_status = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 10")).scalar()
        assert v_status == "DRAFT"

    # Invariant 2: Direct insertion as POSTED fails
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (11, 1, 'JV-POSTED-FAIL', 'JOURNAL', 'POSTED', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
            """))
    assert "DRAFT" in str(excinfo.value).upper()

    # Invariant 3: Inserting with another unsupported initial status fails
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (12, 1, 'JV-BAD-STATUS', 'JOURNAL', 'PENDING', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
            """))
    assert "CHECK" in str(excinfo.value).upper() or "DRAFT" in str(excinfo.value).upper()

    # Invariant 4: A valid DRAFT-to-POSTED transition still works
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (101, 1, 10, 1, 1, 500.00, 0.00)
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (102, 1, 10, 2, 2, 0.00, 500.00)
        """))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 10"))
        posted_status = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 10")).scalar()
        assert posted_status == "POSTED"

    # Invariant 5: Updating or deleting a posted voucher still fails
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE journal_vouchers SET total_debit_base = 999.00 WHERE id = 10"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM journal_vouchers WHERE id = 10"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    # Invariant 6: Updating, deleting, or reassigning entries belonging to a posted voucher still fails
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("UPDATE journal_entries SET debit_amount_base = 999.00 WHERE id = 101"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM journal_entries WHERE id = 101"))
    assert "IMMUTABLE" in str(excinfo.value).upper()

    # Invariant 7: A valid separate-voucher reversal still works
    with engine.begin() as conn:
        # Reversal voucher created as DRAFT
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
            VALUES (20, 1, 'REV-10', 'REVERSAL', 'DRAFT', '2025-07-21', '2082-04-06', 500.00, 500.00, 1, 10, 1)
        """))
        # Inverted lines
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (201, 1, 20, 1, 1, 0.00, 500.00)
        """))
        conn.execute(text("""
            INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base)
            VALUES (202, 1, 20, 2, 2, 500.00, 0.00)
        """))
        # Post the reversal
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 20"))
        rev_status = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 20")).scalar()
        orig_status = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 10")).scalar()
        assert rev_status == "POSTED"
        assert orig_status == "POSTED"  # Original remains POSTED, not mutated

    # Invariant 8: Duplicate reversal protection remains intact
    with pytest.raises(Exception) as excinfo:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
                VALUES (21, 1, 'REV-10-DUP', 'REVERSAL', 'DRAFT', '2025-07-22', '2082-04-07', 500.00, 500.00, 1, 10, 1)
            """))
    assert "UNIQUE" in str(excinfo.value).upper() or "UQ_JV_REVERSAL_OF" in str(excinfo.value).upper()

    engine.dispose()
    if temp_db_path.exists():
        temp_db_path.unlink()
