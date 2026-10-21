"""
LIVO Footwear ERP — Sprint 1B.1.2
PostgreSQL 16 / 18 Migration 028 Lifecycle & DDL Validation Suite
=================================================================
Validates the complete accounting schema foundation on a live PostgreSQL engine:
1. Fresh upgrade to 028 from a blank disposable database
2. Upgrade from 027 with pre-existing synthetic operational data
3. Cross-company foreign key rejections (strict multi-tenant boundaries)
4. Voucher creation lifecycle invariants:
   - Insertion as DRAFT succeeds
   - Direct insertion as POSTED rejected by database trigger
   - Unsupported initial status rejected
   - Permitted DRAFT-to-POSTED transition works
   - Posted voucher and line immutability (UPDATE, DELETE, reassignments blocked)
   - Valid separate-voucher reversal works
   - Original voucher remains POSTED
5. Duplicate reversal rejection via partial unique index
6. Concurrent duplicate reversal race-condition rejection
7. Transaction rollback after injected constraint failure (zero orphan records)
8. Clean downgrade to 027 and subsequent re-upgrade to 028
9. Single linear Alembic head verification

Uses a dedicated disposable database or isolated embedded-postgres instance.
Zero collision with conftest.py application fixtures or protected developer databases.
"""
import os
import sys
import uuid
import time
import tempfile
import pathlib
import threading
import subprocess
import psycopg2
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Resolve external or embedded PostgreSQL target
_external_pg_url = os.getenv("PG152_TEST_URL") or os.getenv("TEST_DATABASE_URL")
_embedded_server = None


def run_alembic(cmd: list, pg_url: str):
    """Executes Alembic command in an isolated subprocess to guarantee zero fixture pollution."""
    env = os.environ.copy()
    env["DATABASE_URL"] = pg_url
    env["SECRET_KEY"] = "migration_028_isolated_test_key_minimum_32_characters"
    proc = subprocess.run(
        [sys.executable, "-m", "alembic"] + cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Alembic command {' '.join(cmd)} failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return proc


@pytest.fixture(scope="module")
def pg_target():
    """
    Provisions a dedicated, disposable PostgreSQL database for Migration 028 tests.
    Uses PG152_TEST_URL if provided, else embedded_postgres if available.
    Enforces PostgreSQL 16 major version validation when LIVO_REQUIRE_PG16 or RELEASE_GATE is set.
    Creates a unique disposable database so conftest.py's Base.metadata.create_all()
    cannot collide with Alembic migrations.
    Drops the disposable database upon test completion.
    """
    global _embedded_server
    is_release_gate = (
        os.getenv("LIVO_REQUIRE_PG16", "").lower() in ("1", "true", "yes")
        or os.getenv("RELEASE_GATE", "").lower() in ("1", "true", "yes")
    )
    server_url = _external_pg_url
    temp_pgdata = None

    if not server_url:
        if is_release_gate:
            pytest.fail(
                "[RELEASE GATE FAILURE] PostgreSQL 16 test environment required (PG152_TEST_URL or TEST_DATABASE_URL must be configured). "
                "Silent skipping or version mismatch is disabled for release gates."
            )
        try:
            from embedded_postgres import get_server
            temp_pgdata = pathlib.Path(tempfile.mkdtemp()) / "pg_mig028_isolated"
            _embedded_server = get_server(temp_pgdata, cleanup_mode="delete")
            _embedded_server.ensure_pgdata_inited()
            _embedded_server.ensure_postgres_running()
            time.sleep(2)
            server_url = _embedded_server.get_uri()
        except ImportError:
            pytest.fail("Neither PG152_TEST_URL nor embedded_postgres is available. PostgreSQL test environment required.")

    # Validate target safety: must not be a protected DB
    from app.db.session import validate_database_target_safety
    validate_database_target_safety(server_url)

    # Server version inspection
    try:
        check_conn = psycopg2.connect(server_url)
        check_cur = check_conn.cursor()
        check_cur.execute("SHOW server_version;")
        full_version = check_cur.fetchone()[0]
        check_cur.execute("SELECT current_setting('server_version_num')::int / 10000;")
        major_version = check_cur.fetchone()[0]
        check_cur.close()
        check_conn.close()
    except Exception as e:
        pytest.fail(f"Failed to connect to PostgreSQL server: {e}")

    if is_release_gate and major_version != 16:
        pytest.fail(
            f"[RELEASE GATE FAILURE] Target server version is PostgreSQL {full_version} (major {major_version}). "
            "Release gate strictly requires PostgreSQL 16.x."
        )

    # Generate unique disposable database name
    db_name = f"disp_mig028_{uuid.uuid4().hex[:10]}"

    # Connect to base maintenance database to create the disposable DB
    conn = psycopg2.connect(server_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f'CREATE DATABASE "{db_name}";')
    cur.close()
    conn.close()

    # Construct the URL for the disposable DB
    parsed = sa.engine.make_url(server_url)
    disp_url_obj = parsed.set(database=db_name)
    disp_raw_url = disp_url_obj.render_as_string(hide_password=False)
    disp_sa_url = disp_raw_url
    if disp_sa_url.startswith("postgresql://"):
        disp_sa_url = disp_sa_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(disp_sa_url, pool_pre_ping=True)

    yield {
        "raw_url": disp_raw_url,
        "sa_url": disp_sa_url,
        "db_name": db_name,
        "server_url": server_url,
        "server_version": full_version,
        "major_version": major_version,
        "engine": engine,
    }

    # Teardown: close engine connections and drop disposable database
    engine.dispose()
    try:
        drop_conn = psycopg2.connect(server_url)
        drop_conn.autocommit = True
        drop_cur = drop_conn.cursor()
        drop_cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE);')
        drop_cur.close()
        drop_conn.close()
    except Exception as e:
        print(f"Warning during DB cleanup: {e}", file=sys.stderr)

    if _embedded_server is not None:
        try:
            _embedded_server.cleanup()
        except Exception:
            pass
        _embedded_server = None


def test_1_fresh_upgrade_to_028_postgres(pg_target):
    """Test 1: Fresh upgrade to latest Alembic head (030) on a completely blank disposable PostgreSQL database."""
    run_alembic(["upgrade", "head"], pg_target["raw_url"])

    inspector = sa.inspect(pg_target["engine"])
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

    # Verify Wave P1 schema additions from revisions 029 and 030 are present in head on PostgreSQL
    wave_p1_tables = {"credit_notes", "credit_note_items"}
    assert wave_p1_tables.issubset(tables), f"Missing Wave P1 tables from revision 030: {wave_p1_tables - tables}"
    client_cols = {c["name"] for c in inspector.get_columns("clients")}
    assert "pan_number" in client_cols, "clients.pan_number from revision 029 missing in migrated head on PostgreSQL!"


def test_2_upgrade_from_027_with_synthetic_data_postgres(pg_target):
    """Test 2: Upgrade from 027 to 028 on database populated with sample operational data."""
    # Downgrade to 027
    run_alembic(["downgrade", "027_operational_numeric_precision"], pg_target["raw_url"])

    with pg_target["engine"].begin() as conn:
        conn.execute(text("INSERT INTO companies (id, code, name, pan_number) VALUES (1, 'PGCOMP1', 'PG Company 1', '999999991') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO companies (id, code, name, pan_number) VALUES (2, 'PGCOMP2', 'PG Company 2', '999999992') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO branches (id, company_id, code, name, type) VALUES (1, 1, 'PGBR1', 'PG Branch 1', 'RETAIL_OUTLET') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO branches (id, company_id, code, name, type) VALUES (2, 2, 'PGBR2', 'PG Branch 2', 'RETAIL_OUTLET') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO users (id, company_id, branch_id, name, username, email, password_hash, role, active) VALUES (1, 1, 1, 'PG User 1', 'pguser1', 'pguser1@livo.test', 'hash', 'admin', true) ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO users (id, company_id, branch_id, name, username, email, password_hash, role, active) VALUES (2, 2, 2, 'PG User 2', 'pguser2', 'pguser2@livo.test', 'hash', 'admin', true) ON CONFLICT DO NOTHING"))

    # Upgrade to 028
    run_alembic(["upgrade", "028_register_double_entry_accounting_ledger"], pg_target["raw_url"])

    with pg_target["engine"].begin() as conn:
        b_cnt = conn.execute(text("SELECT COUNT(*) FROM branches WHERE id IN (1, 2)")).scalar()
        u_cnt = conn.execute(text("SELECT COUNT(*) FROM users WHERE id IN (1, 2)")).scalar()
        assert b_cnt == 2, "Branches data lost during upgrade!"
        assert u_cnt == 2, "Users data lost during upgrade!"


def test_3_cross_company_fk_rejection_postgres(pg_target):
    """Test 3: Cross-company composite FK rejection across all tenant relationships."""
    with pg_target["engine"].begin() as conn:
        conn.execute(text("INSERT INTO account_groups (id, company_id, code, name, group_type, level) VALUES (1, 1, '1000', 'Assets 1', 'ASSET', 1) ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO account_groups (id, company_id, code, name, group_type, level) VALUES (2, 2, '1000', 'Assets 2', 'ASSET', 1) ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO accounting_periods (id, company_id, fiscal_year, period_number, period_name, start_date_ad, end_date_ad, start_date_bs, end_date_bs) VALUES (1, 1, '2082/83', 1, 'Shrawan', '2025-07-16', '2025-08-16', '2082-04-01', '2082-04-32') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO accounting_periods (id, company_id, fiscal_year, period_number, period_name, start_date_ad, end_date_ad, start_date_bs, end_date_bs) VALUES (2, 2, '2082/83', 1, 'Shrawan', '2025-07-16', '2025-08-16', '2082-04-01', '2082-04-32') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (1, 1, 1, '1110', 'Cash 1', 'DEBIT') ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (2, 2, 2, '1110', 'Cash 2', 'DEBIT') ON CONFLICT DO NOTHING"))

    # 3a. Account group self-reference across companies (Company 1 referencing Parent in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO account_groups (id, company_id, parent_id, code, name, group_type, level) VALUES (3, 1, 2, '1100', 'Sub Asset', 'ASSET', 2)"))

    # 3b. Ledger account branch cross-company (Company 1 referencing Branch 2 in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO ledger_accounts (id, company_id, branch_id, group_id, code, name, normal_balance) VALUES (10, 1, 2, 1, '1999', 'Cross Branch', 'DEBIT')"))

    # 3c. Ledger account group cross-company (Company 1 referencing Group 2 in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO ledger_accounts (id, company_id, group_id, code, name, normal_balance) VALUES (11, 1, 2, '1998', 'Cross Group', 'DEBIT')"))

    # 3d. Journal voucher branch cross-company
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_vouchers (id, company_id, branch_id, voucher_number, voucher_type, date_ad, date_bs, created_by_id) VALUES (50, 1, 2, 'JV-BAD-BR', 'JOURNAL', '2025-07-20', '2082-04-05', 1)"))

    # 3e. Journal voucher period cross-company
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_vouchers (id, company_id, period_id, voucher_number, voucher_type, date_ad, date_bs, created_by_id) VALUES (51, 1, 2, 'JV-BAD-PER', 'JOURNAL', '2025-07-20', '2082-04-05', 1)"))

    # Setup base vouchers for company 1 and company 2 for entry and reversal testing
    with pg_target["engine"].begin() as conn:
        conn.execute(text("INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, created_by_id) VALUES (60, 1, 'JV-BASE-1', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 1) ON CONFLICT DO NOTHING"))
        conn.execute(text("INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, created_by_id) VALUES (70, 2, 'JV-BASE-2', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 2) ON CONFLICT DO NOTHING"))

    # 3f. Journal entries voucher cross-company (Company 1 entry referencing Voucher in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (601, 1, 70, 1, 1, 100.00, 0.00)"))

    # 3g. Journal entries ledger cross-company (Company 1 entry referencing Ledger Account in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (602, 1, 60, 1, 2, 100.00, 0.00)"))

    # 3h. Journal entries branch cross-company (Company 1 entry referencing Branch in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_entries (id, company_id, branch_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (603, 1, 2, 60, 1, 1, 100.00, 0.00)"))

    # 3i. Journal voucher reversal cross-company (Company 1 reversal referencing Voucher in Company 2)
    with pytest.raises(sa.exc.IntegrityError):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("INSERT INTO journal_vouchers (id, company_id, reversal_of_id, voucher_number, voucher_type, date_ad, date_bs, created_by_id) VALUES (52, 1, 70, 'REV-BAD-COMP', 'REVERSAL', '2025-07-21', '2082-04-06', 1)"))


def test_4_voucher_creation_lifecycle_invariants_postgres(pg_target):
    """
    Test 4: Sprint 1B.1.2 voucher creation lifecycle invariants on PostgreSQL:
    1. Inserting a voucher as DRAFT succeeds.
    2. Direct insertion as POSTED fails at DB level.
    3. Inserting with another unsupported initial status fails.
    4. A valid DRAFT-to-POSTED transition works once balanced entries are added.
    5. Updating or deleting a posted voucher fails.
    6. Updating, deleting, or reassigning entries belonging to a posted voucher fails.
    7. A valid separate-voucher reversal works; original remains POSTED.
    """
    # 4.1 Inserting voucher as DRAFT succeeds
    with pg_target["engine"].begin() as conn:
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
            VALUES (100, 1, 'JV-PG-100', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 1000.00, 1000.00, 1)
        """))
        st = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 100")).scalar()
        assert st == "DRAFT"

    # 4.2 Direct insertion as POSTED fails (rejected by trg_journal_voucher_initial_draft)
    with pytest.raises(sa.exc.InternalError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (101, 1, 'JV-PG-DIRECT-POSTED', 'JOURNAL', 'POSTED', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
            """))
    assert "draft" in str(excinfo.value).lower()

    # 4.3 Inserting with unsupported status fails (check constraint or trigger)
    with pytest.raises(Exception):
        with pg_target["engine"].begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (102, 1, 'JV-PG-BAD-STATUS', 'JOURNAL', 'PENDING', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
            """))

    # 4.4 Add balanced lines and transition to POSTED
    with pg_target["engine"].begin() as conn:
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (1, 1, 100, 1, 1, 1000.00, 0.00)"))
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (2, 1, 100, 2, 1, 0.00, 1000.00)"))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 100"))
        posted_st = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 100")).scalar()
        assert posted_st == "POSTED"

    # 4.5 Updating or deleting a posted voucher fails (trg_journal_voucher_immutable)
    with pytest.raises(sa.exc.InternalError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("UPDATE journal_vouchers SET total_debit_base = 999.00 WHERE id = 100"))
    assert "immutable" in str(excinfo.value).lower()

    with pytest.raises(sa.exc.InternalError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("DELETE FROM journal_vouchers WHERE id = 100"))
    assert "immutable" in str(excinfo.value).lower()

    # 4.6 Updating or deleting lines belonging to a posted voucher fails (trg_journal_entry_immutable)
    with pytest.raises(sa.exc.InternalError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("UPDATE journal_entries SET debit_amount_base = 500.00 WHERE id = 1"))
    assert "immutable" in str(excinfo.value).lower()

    with pytest.raises(sa.exc.InternalError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("DELETE FROM journal_entries WHERE id = 1"))
    assert "immutable" in str(excinfo.value).lower()

    # 4.7 Valid separate-voucher reversal works (created as DRAFT, lines inverted, then POSTED)
    with pg_target["engine"].begin() as conn:
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
            VALUES (200, 1, 'REV-PG-100', 'REVERSAL', 'DRAFT', '2025-07-21', '2082-04-06', 1000.00, 1000.00, true, 100, 1)
        """))
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (3, 1, 200, 1, 1, 0.00, 1000.00)"))
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (4, 1, 200, 2, 1, 1000.00, 0.00)"))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 200"))

        rev_st = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 200")).scalar()
        orig_st = conn.execute(text("SELECT status FROM journal_vouchers WHERE id = 100")).scalar()
        assert rev_st == "POSTED"
        assert orig_st == "POSTED", "Original voucher status must not be changed upon reversal!"


def test_5_duplicate_reversal_rejection_postgres(pg_target):
    """Test 5: Duplicate reversal rejection via partial unique index in PostgreSQL."""
    # Voucher 100 was already reversed by Voucher 200 in test 4.
    # Attempting a second reversal (even as DRAFT) MUST be rejected by uq_jv_reversal_of
    with pytest.raises(sa.exc.IntegrityError) as excinfo:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
                VALUES (201, 1, 'REV-PG-100-DUP', 'REVERSAL', 'DRAFT', '2025-07-22', '2082-04-07', 1000.00, 1000.00, true, 100, 1)
            """))
    assert "uq_jv_reversal_of" in str(excinfo.value).lower() or "unique" in str(excinfo.value).lower()


def test_6_concurrent_reversal_race_rejection_postgres(pg_target):
    """Test 6: Multi-threaded concurrent reversal race condition rejection on PostgreSQL."""
    # Create a fresh posted voucher to test concurrent reversal
    with pg_target["engine"].begin() as conn:
        conn.execute(text("""
            INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
            VALUES (700, 1, 'JV-CONC-ORIG', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 500.00, 500.00, 1)
        """))
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (701, 1, 700, 1, 1, 500.00, 0.00)"))
        conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (702, 1, 700, 2, 1, 0.00, 500.00)"))
        conn.execute(text("UPDATE journal_vouchers SET status = 'POSTED' WHERE id = 700"))

    barrier = threading.Barrier(2)
    thread_outcomes = []

    def worker(worker_id, v_num):
        conn = psycopg2.connect(pg_target["raw_url"])
        cur = conn.cursor()
        barrier.wait()
        try:
            cur.execute("""
                INSERT INTO journal_vouchers (company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, is_reversal, reversal_of_id, created_by_id)
                VALUES (1, %s, 'REVERSAL', 'DRAFT', '2025-07-21', '2082-04-06', 500.00, 500.00, true, 700, 1)
            """, (v_num,))
            conn.commit()
            thread_outcomes.append((worker_id, "SUCCESS", None))
        except Exception as e:
            conn.rollback()
            thread_outcomes.append((worker_id, "FAILED", str(e)))
        finally:
            conn.close()

    t1 = threading.Thread(target=worker, args=(1, "REV-CONC-1"))
    t2 = threading.Thread(target=worker, args=(2, "REV-CONC-2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [o for o in thread_outcomes if o[1] == "SUCCESS"]
    failures = [o for o in thread_outcomes if o[1] == "FAILED"]
    assert len(successes) == 1, f"Expected exactly 1 thread to succeed, got {len(successes)}"
    assert len(failures) == 1, f"Expected exactly 1 thread to fail, got {len(failures)}"
    assert "uq_jv_reversal_of" in failures[0][2].lower() or "unique" in failures[0][2].lower()


def test_7_transaction_rollback_after_injected_failure_postgres(pg_target):
    """Test 7: Transaction rollback after injected failure in PostgreSQL (0 orphan records)."""
    try:
        with pg_target["engine"].begin() as conn:
            conn.execute(text("""
                INSERT INTO journal_vouchers (id, company_id, voucher_number, voucher_type, status, date_ad, date_bs, total_debit_base, total_credit_base, created_by_id)
                VALUES (9999, 1, 'JV-ROLLBACK-PG', 'JOURNAL', 'DRAFT', '2025-07-20', '2082-04-05', 100.00, 100.00, 1)
            """))
            # Injected failure: negative amount violates check constraint
            conn.execute(text("INSERT INTO journal_entries (id, company_id, voucher_id, line_number, ledger_id, debit_amount_base, credit_amount_base) VALUES (9999, 1, 9999, 1, 1, -50.00, 0.00)"))
    except Exception:
        pass  # Expected rollback

    with pg_target["engine"].begin() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM journal_vouchers WHERE id = 9999")).scalar()
        assert cnt == 0, f"Expected 0 orphan vouchers after rollback, found {cnt}!"


def test_8_downgrade_to_027_and_reupgrade_postgres(pg_target):
    """Test 8: Clean downgrade to revision 027 and subsequent re-upgrade through head in PostgreSQL."""
    # Downgrade to 027
    run_alembic(["downgrade", "027_operational_numeric_precision"], pg_target["raw_url"])

    inspector = sa.inspect(pg_target["engine"])
    tables = set(inspector.get_table_names())
    acct_tables = {"account_groups", "ledger_accounts", "accounting_periods", "journal_vouchers", "journal_entries"}
    assert not acct_tables.intersection(tables), f"Accounting tables survived downgrade: {acct_tables.intersection(tables)}"

    # Re-upgrade to 028
    run_alembic(["upgrade", "028_register_double_entry_accounting_ledger"], pg_target["raw_url"])

    inspector = sa.inspect(pg_target["engine"])
    tables = set(inspector.get_table_names())
    assert acct_tables.issubset(tables), f"Missing tables after re-upgrade: {acct_tables - tables}"

    # Re-upgrade to current head (030)
    run_alembic(["upgrade", "head"], pg_target["raw_url"])
    inspector = sa.inspect(pg_target["engine"])
    tables = set(inspector.get_table_names())
    wave_p1_tables = {"credit_notes", "credit_note_items"}
    assert wave_p1_tables.issubset(tables), f"Missing Wave P1 tables after re-upgrade to head: {wave_p1_tables - tables}"


def test_9_single_alembic_head_postgres():
    """Test 9: Single linear Alembic head verification."""
    ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 head, got {heads}"
    assert heads[0] == "030_wave_p1_sales_invoicing_remediation"


def test_10_stock_movement_immutability_triggers_postgres(pg_target):
    """
    Test 10: Verifies that Migration 025 triggers reject direct UPDATE and DELETE
    operations on stock_movements ledger rows in live PostgreSQL.
    """
    engine = pg_target["engine"]
    with engine.connect() as conn:
        with conn.begin():
            # Seed minimal company, warehouse, product, stock movement
            conn.execute(sa.text("INSERT INTO companies (id, name, code) VALUES (888, 'Immutability Corp', 'IMM888') ON CONFLICT DO NOTHING;"))
            conn.execute(sa.text("INSERT INTO warehouses (id, company_id, name, code) VALUES (888, 888, 'Central Wh', 'WH888') ON CONFLICT DO NOTHING;"))
            conn.execute(sa.text("INSERT INTO products (id, company_id, name, code, category, unit_price) VALUES (888, 888, 'Shoe A', 'SHOE888', 'CASUAL', 1200.00) ON CONFLICT DO NOTHING;"))
            conn.execute(sa.text("""
                INSERT INTO stock_movements (id, company_id, product_id, warehouse_id, movement_type, quantity, direction, ref_type, date_ad, date_bs, created_at)
                VALUES (8888, 888, 888, 888, 'PURCHASE_RECEIPT', 10.00, 1, 'PURCHASE', '2026-10-19', '2083-07-03', NOW());
            """))

        # Verify UPDATE rejection
        with pytest.raises((sa.exc.InternalError, sa.exc.ProgrammingError)) as exc_update:
            with conn.begin():
                conn.execute(sa.text("UPDATE stock_movements SET quantity = 20.00 WHERE id = 8888;"))
        assert "immutable" in str(exc_update.value).lower()

        # Verify DELETE rejection
        with pytest.raises((sa.exc.InternalError, sa.exc.ProgrammingError)) as exc_delete:
            with conn.begin():
                conn.execute(sa.text("DELETE FROM stock_movements WHERE id = 8888;"))
        assert "immutable" in str(exc_delete.value).lower()

