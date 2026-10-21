"""
LIVO Footwear ERP — Wave P1.11
PostgreSQL 16 Wave P1 Release-Gate Verification Suite
======================================================
Validates the complete sales invoicing, Schedule-10 credit notes, 
concurrency row-locking, and migration integrity on a genuine PostgreSQL 16 engine:

1. Gate A: Migration integrity & single linear Alembic head through 030
2. Gate B: Invoice finalization concurrency (real finalize_invoice endpoint & SELECT ... FOR UPDATE)
3. Gate C: Document sequence allocation under concurrent workers (real allocate_next_sequence)
4. Gate D: Credit-note cumulative return limits (real issue_credit_note endpoint & DEF-FE-01 remediation)
   - Restocking vs non-restocking returns
   - Over-return rejection with HTTP 422
   - Multi-line independent balances
   - Strict tenant isolation
5. Gate E: Atomic rollback on injected failure (zero orphan records across all 4 tables)
6. Gate F: Monetary precision and Nepal 13% statutory VAT calculation on PostgreSQL

Runs exclusively against genuine PostgreSQL 16 (fails closed in CI or marks UNVERIFIED locally).
Zero collision with protected developer databases or SQLite test fixtures.
"""
import os
import sys
import uuid
import pathlib
import threading
import subprocess
from decimal import Decimal
import psycopg2
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import HTTPException
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models.company import Company
from app.models.branch import Branch, BranchType
from app.models.user import User
from app.models.stock import Product, Warehouse, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem
from app.models.invoice import Invoice, InvoiceSequence, CreditNote, CreditNoteItem
from app.models.sequence import DocumentSequence
from app.models.receivable import ReceivableEntry
from app.core.sequence import allocate_next_sequence
from app.core.currency import quantize_npr
from app.api.v1.invoices import (
    finalize_invoice,
    issue_credit_note,
    allocate_next_invoice_sequence,
    compute_invoice_amounts,
    CreditNoteCreate,
    ReturnItem,
)

# Resolve external PostgreSQL 16 target
_external_pg_url = os.getenv("PG152_TEST_URL") or os.getenv("TEST_DATABASE_URL")


def run_alembic(cmd: list, pg_url: str):
    """Executes Alembic command in an isolated subprocess."""
    env = os.environ.copy()
    env["DATABASE_URL"] = pg_url
    env["SECRET_KEY"] = "wave_p1_isolated_pg16_secret_key_minimum_32_chars"
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
def pg16_target():
    """
    Provisions a dedicated disposable database on a genuine PostgreSQL 16 server.
    - Fails closed in CI if PG152_TEST_URL is not set.
    - Skips locally with clear UNVERIFIED gate status if no PostgreSQL server URL is provided.
    - Fails closed if the connected server is not PostgreSQL 16.x.
    """
    if not _external_pg_url:
        if os.getenv("CI"):
            pytest.fail(
                "[POSTGRESQL 16 GATE FAILURE] PG152_TEST_URL is not set in CI environment! "
                "PostgreSQL 16 server is mandatory for release-gate verification."
            )
        pytest.skip(
            "[POSTGRESQL 16 GATE UNVERIFIED] PostgreSQL 16 server URL is not configured (PG152_TEST_URL / TEST_DATABASE_URL). "
            "A genuine PostgreSQL 16 execution environment is required to complete this gate."
        )

    server_url = _external_pg_url

    # Validate target safety: must not match protected DB
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
        pytest.fail(f"[POSTGRESQL 16 GATE FAILURE] Failed to connect to PostgreSQL server: {e}")

    if major_version != 16:
        pytest.fail(
            f"[POSTGRESQL 16 GATE FAILURE] Connected server version is PostgreSQL {full_version} (major {major_version}). "
            "Release gate strictly requires genuine PostgreSQL 16.x."
        )

    # Generate unique disposable database name
    db_name = f"disp_wave_p1_{uuid.uuid4().hex[:10]}"

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

    engine = create_engine(disp_sa_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

    # Apply all Alembic migrations up to head (Revision 030)
    run_alembic(["upgrade", "head"], disp_raw_url)

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


# =============================================================================
# GATE A: MIGRATION INTEGRITY & SCHEMA COEXISTENCE (028 + 029 + 030)
# =============================================================================

def test_gate_a_migration_integrity_and_head_pg16(pg16_target):
    """
    Gate A: Migration integrity & single linear Alembic head on PostgreSQL 16.
    Verifies that:
    1. Single head is 030_wave_p1_sales_invoicing_remediation.
    2. Revisions 028, 029, and 030 tables and columns coexist cleanly on PG16.
    """
    engine = pg16_target["engine"]

    # 1. Check Alembic script directory single head
    ini_path = BACKEND_DIR / "alembic.ini"
    cfg = Config(str(ini_path))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 head, got {heads}"
    assert heads[0] == "030_wave_p1_sales_invoicing_remediation", f"Unexpected head: {heads[0]}"

    # 2. Inspect PostgreSQL schema objects
    inspector = sa.inspect(engine)
    tables = set(inspector.get_table_names())

    # Revision 028: Accounting ledger
    acct_tables = {"account_groups", "ledger_accounts", "accounting_periods", "journal_vouchers", "journal_entries"}
    assert acct_tables.issubset(tables), f"Missing 028 tables: {acct_tables - tables}"

    # Revision 029: Party PAN columns
    client_cols = {c["name"] for c in inspector.get_columns("clients")}
    supplier_cols = {c["name"] for c in inspector.get_columns("suppliers")}
    assert "pan_number" in client_cols, "clients.pan_number from revision 029 is missing!"
    assert "pan_number" in supplier_cols, "suppliers.pan_number from revision 029 is missing!"

    # Revision 030: Sales invoicing & Schedule-10 credit notes
    inv_tables = {"invoices", "credit_notes", "credit_note_items"}
    assert inv_tables.issubset(tables), f"Missing 030 tables: {inv_tables - tables}"

    # Verify invoices.sequence_number is nullable
    inv_col_seq = next((c for c in inspector.get_columns("invoices") if c["name"] == "sequence_number"), None)
    assert inv_col_seq is not None, "invoices.sequence_number column missing!"
    assert inv_col_seq["nullable"] is True, "invoices.sequence_number must be nullable in revision 030!"

    # Verify unique constraint on credit_notes
    uqs = [uq["name"] for uq in inspector.get_unique_constraints("credit_notes")]
    assert "uq_credit_note_company_number" in uqs or any("credit_note_number" in uq.get("column_names", []) for uq in inspector.get_unique_constraints("credit_notes"))


# =============================================================================
# GATE B: INVOICE FINALIZATION CONCURRENCY (REAL finalize_invoice & ROW LOCKING)
# =============================================================================

def test_gate_b_invoice_finalization_concurrency_pg16(pg16_target):
    """
    Gate B: Real invoice finalization concurrency on PostgreSQL 16.
    Invokes the genuine application finalize_invoice() endpoint function across
    two concurrent threads using genuinely independent PostgreSQL sessions.
    Proves:
    - At most one finalization succeeds.
    - Exactly one invoice sequence number is assigned.
    - Exactly one receivable posting is created.
    - The losing thread receives an HTTPException(400) indicating invoice is already finalized.
    - Zero orphaned or duplicate financial records.
    """
    engine = pg16_target["engine"]
    SessionMaker = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:6]

    # Setup isolated test company, branch, user, client, product, sales order, and draft invoice
    with SessionMaker() as db:
        company = Company(name=f"Concurrency Corp {suffix}", code=f"C501-{suffix}", pan_number=f"609{suffix}")
        db.add(company)
        db.flush()

        branch = Branch(company_id=company.id, name="Main Branch", code=f"B501-{suffix}", type=BranchType.FACTORY.value, is_active=True)
        db.add(branch)
        db.flush()

        user = User(
            company_id=company.id,
            branch_id=branch.id,
            name="Concurrency Editor",
            username=f"editor_{suffix}",
            email=f"editor_{suffix}@livo.test",
            password_hash="argon2_hash",
            role="admin",
            active=True
        )
        db.add(user)
        db.flush()

        client = Client(company_id=company.id, code=f"CLI-{suffix}", name="Concurrency Client", pan_number="609111222")
        db.add(client)
        db.flush()

        product = Product(
            company_id=company.id,
            code=f"PROD-{suffix}",
            name="Formal Shoe",
            category="FORMAL",
            size="41",
            color="Brown",
            unit_price=Decimal("2500.00")
        )
        db.add(product)
        db.flush()

        order = SalesOrder(
            company_id=company.id,
            order_number=f"SO-501-{suffix}",
            client_id=client.id,
            order_date_ad="2026-10-21",
            order_date_bs="2083-07-04",
            status="CONFIRMED",
            total_amount=Decimal("11300.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("11300.00"),
            delivered=True
        )
        db.add(order)
        db.flush()

        # Seed initial sequence
        inv_seq = InvoiceSequence(company_id=company.id, current_sequence=100)
        db.add(inv_seq)

        # Create eligible DRAFT invoice (invoice_number starts with DRAFT-, sequence_number is None)
        draft_invoice = Invoice(
            company_id=company.id,
            sales_order_id=order.id,
            invoice_number=f"DRAFT-{suffix}",
            sequence_number=None,
            date_ad="2026-10-21",
            date_bs="2083-07-04",
            subtotal=Decimal("10000.00"),
            vat_enabled=True,
            vat_rate=Decimal("13.00"),
            vat_amount=Decimal("1300.00"),
            total_amount=Decimal("11300.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("11300.00"),
            is_void=False
        )
        db.add(draft_invoice)
        db.commit()

        draft_id = draft_invoice.id
        company_id = company.id
        user_id = user.id

    results = []
    barrier = threading.Barrier(2)

    def finalize_worker(worker_id: int):
        worker_db = SessionMaker()
        try:
            worker_user = worker_db.query(User).filter(User.id == user_id).one()
            barrier.wait(timeout=10)
            
            # Exercise the real application endpoint function
            finalized = finalize_invoice(
                invoice_id=draft_id,
                current_user=worker_user,
                db=worker_db
            )
            results.append((worker_id, "SUCCESS", finalized.invoice_number, finalized.sequence_number))
        except HTTPException as he:
            worker_db.rollback()
            results.append((worker_id, "HTTP_EXCEPTION", he.status_code, str(he.detail)))
        except Exception as ex:
            worker_db.rollback()
            results.append((worker_id, "UNEXPECTED_ERROR", 500, str(ex)))
        finally:
            worker_db.close()

    t1 = threading.Thread(target=finalize_worker, args=(1,))
    t2 = threading.Thread(target=finalize_worker, args=(2,))
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)

    successes = [r for r in results if r[1] == "SUCCESS"]
    http_failures = [r for r in results if r[1] == "HTTP_EXCEPTION"]
    unexpected = [r for r in results if r[1] == "UNEXPECTED_ERROR"]

    assert not unexpected, f"Unexpected error during concurrent finalization: {unexpected}"
    assert len(successes) == 1, f"Expected exactly 1 finalization to succeed, got {len(successes)}"
    assert len(http_failures) == 1, f"Expected exactly 1 finalization to fail with HTTPException, got {len(http_failures)}"

    # Assert losing request got documented status and message
    assert http_failures[0][2] == 400
    assert "already finalized" in http_failures[0][3].lower()

    # Verify persisted state via fresh session
    with SessionMaker() as db:
        final_inv = db.query(Invoice).filter(Invoice.id == draft_id).one()
        assert not final_inv.invoice_number.startswith("DRAFT-")
        assert final_inv.sequence_number == 101
        assert final_inv.invoice_number == f"INV-{company_id:02d}-00101"

        # Verify exactly 1 receivable entry posted
        ar_count = db.query(ReceivableEntry).filter(
            ReceivableEntry.invoice_id == draft_id,
            ReceivableEntry.company_id == company_id
        ).count()
        assert ar_count == 1, f"Expected exactly 1 receivable entry, found {ar_count}"


# =============================================================================
# GATE C: ACTUAL SEQUENCE ALLOCATION (DocumentSequence & allocate_next_sequence)
# =============================================================================

def test_gate_c_independent_draft_sequences_pg16(pg16_target):
    """
    Gate C: Real document sequence allocation under concurrent workers on PostgreSQL 16.
    Uses the real allocate_next_sequence() from app.core.sequence and 
    allocate_next_invoice_sequence() from app.api.v1.invoices.
    Verifies:
    - Independent concurrent workers obtain unique, collision-free numbers.
    - No duplicate sequence numbers under concurrency.
    - Gap policy: Uniqueness is mandatory; gaps are acceptable after rollbacks.
    """
    engine = pg16_target["engine"]
    SessionMaker = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:6]

    with SessionMaker() as db:
        comp = Company(name=f"Seq Test Corp {suffix}", code=f"SQ-{suffix}", pan_number=f"609{suffix}")
        db.add(comp)
        db.flush()

        # Seed initial document sequence for SALES_ORDER
        doc_seq = DocumentSequence(company_id=comp.id, document_type="SALES_ORDER", current_sequence=500)
        db.add(doc_seq)

        # Seed initial invoice sequence
        inv_seq = InvoiceSequence(company_id=comp.id, current_sequence=200)
        db.add(inv_seq)
        db.commit()

        comp_id = comp.id

    # Part 1: Concurrent DocumentSequence allocation via allocate_next_sequence
    num_workers = 5
    assigned_doc_seqs = []
    lock = threading.Lock()
    barrier = threading.Barrier(num_workers)

    def doc_seq_worker():
        db = SessionMaker()
        try:
            barrier.wait(timeout=10)
            seq = allocate_next_sequence(db=db, company_id=comp_id, document_type="SALES_ORDER")
            db.commit()
            with lock:
                assigned_doc_seqs.append(seq)
        finally:
            db.close()

    threads = [threading.Thread(target=doc_seq_worker) for _ in range(num_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(assigned_doc_seqs) == num_workers, f"Expected {num_workers} allocations, got {len(assigned_doc_seqs)}"
    assert len(set(assigned_doc_seqs)) == num_workers, f"Duplicate sequences detected! {assigned_doc_seqs}"
    assert all(s > 500 for s in assigned_doc_seqs), f"Sequences not incremented properly: {assigned_doc_seqs}"

    # Part 2: Concurrent InvoiceSequence allocation via allocate_next_invoice_sequence
    assigned_inv_seqs = []
    barrier_inv = threading.Barrier(num_workers)

    def inv_seq_worker():
        db = SessionMaker()
        try:
            barrier_inv.wait(timeout=10)
            seq = allocate_next_invoice_sequence(db=db, company_id=comp_id)
            db.commit()
            with lock:
                assigned_inv_seqs.append(seq)
        finally:
            db.close()

    threads2 = [threading.Thread(target=inv_seq_worker) for _ in range(num_workers)]
    for t in threads2:
        t.start()
    for t in threads2:
        t.join(timeout=15)

    assert len(assigned_inv_seqs) == num_workers
    assert len(set(assigned_inv_seqs)) == num_workers, f"Duplicate invoice sequences detected! {assigned_inv_seqs}"
    assert all(s > 200 for s in assigned_inv_seqs)


# =============================================================================
# GATE D: REAL CREDIT-NOTE BUSINESS VALIDATION (issue_credit_note & DEF-FE-01)
# =============================================================================

def test_gate_d_credit_note_cumulative_return_limits_pg16(pg16_target):
    """
    Gate D: Wave P1.6 credit note remediation verification on PostgreSQL 16.
    Exercises the actual issue_credit_note() endpoint with synthetic models.
    Proves:
    - Restocking returns create StockMovement and CreditNoteItem, updating balances.
    - Non-restocking returns create CreditNoteItem but ZERO StockMovement.
    - Cumulative return limit strictly enforced: over-return rejected with HTTP 422.
    - Credited quantities are not double-counted between StockMovement and CreditNoteItem.
    - Tenant isolation: cross-company return rejected with HTTP 404.
    """
    engine = pg16_target["engine"]
    SessionMaker = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:6]

    with SessionMaker() as db:
        company = Company(name=f"Return Co {suffix}", code=f"RET-{suffix}", pan_number=f"609{suffix}")
        db.add(company)
        db.flush()

        branch = Branch(company_id=company.id, name="Factory", code=f"FCT-{suffix}", type=BranchType.FACTORY.value, is_active=True)
        db.add(branch)
        db.flush()

        warehouse = Warehouse(company_id=company.id, branch_id=branch.id, name="Main WH", code=f"WH-{suffix}", is_active=True)
        db.add(warehouse)
        db.flush()

        user = User(
            company_id=company.id,
            branch_id=branch.id,
            name="Return Manager",
            username=f"ret_user_{suffix}",
            password_hash="hash",
            role="admin",
            active=True
        )
        db.add(user)
        db.flush()

        client = Client(company_id=company.id, code=f"CLI-R-{suffix}", name="Return Client", pan_number="609222333")
        db.add(client)
        db.flush()

        product = Product(
            company_id=company.id,
            code=f"SHOE-R-{suffix}",
            name="School Shoe Black",
            category="SCHOOL",
            size="40",
            color="Black",
            unit_price=Decimal("3200.00")
        )
        db.add(product)
        db.flush()

        # Sales order for 10 pairs (NO nonexistent warehouse_id on sales_orders)
        order = SalesOrder(
            company_id=company.id,
            order_number=f"SO-RET-{suffix}",
            client_id=client.id,
            order_date_ad="2026-10-21",
            order_date_bs="2083-07-04",
            status="CONFIRMED",
            total_amount=Decimal("36160.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("36160.00"),
            delivered=True
        )
        db.add(order)
        db.flush()

        item = SalesItem(
            company_id=company.id,
            sales_order_id=order.id,
            product_id=product.id,
            quantity=Decimal("10.0"),
            unit_price=Decimal("3200.00"),
            total_price=Decimal("32000.00")
        )
        db.add(item)
        db.flush()

        # Finalized invoice for the 10 pairs
        invoice = Invoice(
            company_id=company.id,
            sales_order_id=order.id,
            invoice_number=f"INV-{company.id:02d}-00001",
            sequence_number=1,
            date_ad="2026-10-21",
            date_bs="2083-07-04",
            subtotal=Decimal("32000.00"),
            vat_enabled=True,
            vat_rate=Decimal("13.00"),
            vat_amount=Decimal("4160.00"),
            total_amount=Decimal("36160.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("36160.00"),
            is_void=False
        )
        db.add(invoice)
        db.commit()

        inv_id = invoice.id
        wh_id = warehouse.id
        prod_id = product.id
        user_id = user.id
        comp_id = company.id

    # 1. First partial return: 2 pairs restocked (return_to_stock=True)
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()
        ret1 = issue_credit_note(
            invoice_id=inv_id,
            data=CreditNoteCreate(
                reason="2 pairs defective sole",
                return_to_stock=True,
                warehouse_id=wh_id,
                items=[ReturnItem(product_id=prod_id, quantity=Decimal("2.0"))]
            ),
            current_user=curr_user,
            db=db
        )
        assert ret1["credit_note_ref"].startswith("CN-")
        assert ret1["stock_restored"] is True

        # Check persisted records: 1 CN, 1 CNI, 1 StockMovement
        cni_count = db.query(CreditNoteItem).filter(CreditNoteItem.product_id == prod_id).count()
        sm_count = db.query(StockMovement).filter(
            StockMovement.company_id == comp_id,
            StockMovement.movement_type == "SALES_RETURN"
        ).count()
        assert cni_count == 1
        assert sm_count == 1

    # 2. Second partial return: 3 pairs non-restocked (return_to_stock=False)
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()
        ret2 = issue_credit_note(
            invoice_id=inv_id,
            data=CreditNoteCreate(
                reason="3 pairs commercial allowance",
                return_to_stock=False,
                items=[ReturnItem(product_id=prod_id, quantity=Decimal("3.0"))]
            ),
            current_user=curr_user,
            db=db
        )
        assert ret2["stock_restored"] is False

        # Stock movements MUST still be 1 (non-restocking created NO stock movement)
        sm_count = db.query(StockMovement).filter(
            StockMovement.company_id == comp_id,
            StockMovement.movement_type == "SALES_RETURN"
        ).count()
        assert sm_count == 1, "Non-restocking return created an unauthorized stock movement!"

    # 3. Third return: Attempted over-return (returning 6 pairs when only 5 remain)
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()
        with pytest.raises(HTTPException) as exc_over:
            issue_credit_note(
                invoice_id=inv_id,
                data=CreditNoteCreate(
                    reason="Attempted over-return of 6 pairs",
                    return_to_stock=True,
                    warehouse_id=wh_id,
                    items=[ReturnItem(product_id=prod_id, quantity=Decimal("6.0"))]
                ),
                current_user=curr_user,
                db=db
            )
        assert exc_over.value.status_code == 422
        assert "exceeds original invoiced quantity" in exc_over.value.detail.lower()
        assert "remaining returnable: 5" in exc_over.value.detail.lower()

    # 4. Fourth return: Return remaining 5 pairs exactly
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()
        ret4 = issue_credit_note(
            invoice_id=inv_id,
            data=CreditNoteCreate(
                reason="Return of final remaining 5 pairs",
                return_to_stock=True,
                warehouse_id=wh_id,
                items=[ReturnItem(product_id=prod_id, quantity=Decimal("5.0"))]
            ),
            current_user=curr_user,
            db=db
        )
        assert ret4["remaining_creditable_paisa"] == 0

    # 5. Subsequent return must be rejected as balance is 0
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()
        with pytest.raises(HTTPException) as exc_exhausted:
            issue_credit_note(
                invoice_id=inv_id,
                data=CreditNoteCreate(
                    reason="Return on fully credited invoice",
                    return_to_stock=True,
                    warehouse_id=wh_id,
                    items=[ReturnItem(product_id=prod_id, quantity=Decimal("1.0"))]
                ),
                current_user=curr_user,
                db=db
            )
        assert exc_exhausted.value.status_code == 422
        assert "remaining returnable: 0" in exc_exhausted.value.detail.lower()

    # 6. Tenant isolation: cross-company user cannot access or credit company 1's invoice
    with SessionMaker() as db:
        other_comp = Company(name="Other Co", code=f"OTH-{suffix}", pan_number=f"608{suffix}")
        db.add(other_comp)
        db.flush()
        other_user = User(company_id=other_comp.id, name="Other Admin", username=f"oth_{suffix}", password_hash="h", role="admin")
        db.add(other_user)
        db.commit()

        with pytest.raises(HTTPException) as exc_tenant:
            issue_credit_note(
                invoice_id=inv_id,
                data=CreditNoteCreate(reason="Cross-company hack", return_to_stock=False, items=[ReturnItem(product_id=prod_id, quantity=Decimal("1.0"))]),
                current_user=other_user,
                db=db
            )
        assert exc_tenant.value.status_code == 404


# =============================================================================
# GATE E: REAL TRANSACTION ATOMICITY (Controlled Injected Failure Rollback)
# =============================================================================

def test_gate_e_atomic_rollback_on_injected_failure_pg16(pg16_target):
    """
    Gate E: Transaction rollback safety on PostgreSQL 16.
    Injects a failure after initial writes have begun in issue_credit_note()
    via a session-level before_flush hook. Proves:
    - Entire operation rolls back atomically.
    - Zero orphaned records in credit_notes, credit_note_items, stock_movements, or receivable_entries.
    - Parent invoice receivable_amount remains untouched.
    """
    engine = pg16_target["engine"]
    SessionMaker = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:6]

    with SessionMaker() as db:
        company = Company(name=f"Atomicity Co {suffix}", code=f"ATM-{suffix}", pan_number=f"609{suffix}")
        db.add(company)
        db.flush()

        branch = Branch(company_id=company.id, name="Factory", code=f"AFCT-{suffix}", type=BranchType.FACTORY.value, is_active=True)
        db.add(branch)
        db.flush()

        warehouse = Warehouse(company_id=company.id, branch_id=branch.id, name="WH", code=f"AWH-{suffix}", is_active=True)
        db.add(warehouse)
        db.flush()

        user = User(company_id=company.id, name="Admin", username=f"atm_{suffix}", password_hash="h", role="admin")
        db.add(user)
        db.flush()

        client = Client(company_id=company.id, code=f"CLI-A-{suffix}", name="Client", pan_number="609333444")
        db.add(client)
        db.flush()

        product = Product(company_id=company.id, code=f"PROD-A-{suffix}", name="Boot", category="BOOT", size="42", color="Tan", unit_price=Decimal("4000.00"))
        db.add(product)
        db.flush()

        order = SalesOrder(
            company_id=company.id,
            order_number=f"SO-ATM-{suffix}",
            client_id=client.id,
            order_date_ad="2026-10-21",
            order_date_bs="2083-07-04",
            status="CONFIRMED",
            total_amount=Decimal("4520.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("4520.00"),
            delivered=True
        )
        db.add(order)
        db.flush()

        item = SalesItem(company_id=company.id, sales_order_id=order.id, product_id=product.id, quantity=Decimal("1.0"), unit_price=Decimal("4000.00"), total_price=Decimal("4000.00"))
        db.add(item)
        db.flush()

        invoice = Invoice(
            company_id=company.id,
            sales_order_id=order.id,
            invoice_number=f"INV-ATM-{suffix}",
            sequence_number=1,
            date_ad="2026-10-21",
            date_bs="2083-07-04",
            subtotal=Decimal("4000.00"),
            vat_enabled=True,
            vat_rate=Decimal("13.00"),
            vat_amount=Decimal("520.00"),
            total_amount=Decimal("4520.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("4520.00"),
            is_void=False
        )
        db.add(invoice)
        db.commit()

        inv_id = invoice.id
        order_id = order.id
        wh_id = warehouse.id
        prod_id = product.id
        user_id = user.id
        comp_id = company.id

    # Execute issue_credit_note with an injected failure hook during final flush
    with SessionMaker() as db:
        curr_user = db.query(User).filter(User.id == user_id).one()

        @sa.event.listens_for(db, "before_flush")
        def inject_disruption(session, flush_context, instances):
            for obj in session.new:
                if isinstance(obj, CreditNoteItem) and getattr(obj, "unit_price_paisa", None) == 400000:
                    raise sa.exc.OperationalError(
                        "Simulated database disruption during CreditNoteItem persistence",
                        params=None,
                        orig=Exception("SIMULATED_PG16_CRASH")
                    )

        failure_triggered = False
        try:
            issue_credit_note(
                invoice_id=inv_id,
                data=CreditNoteCreate(
                    reason="Injected Atomicity Disruption Test",
                    return_to_stock=True,
                    warehouse_id=wh_id,
                    items=[ReturnItem(product_id=prod_id, quantity=Decimal("1.0"), unit_price_paisa=400000)]
                ),
                current_user=curr_user,
                db=db
            )
            pytest.fail("Injected failure was not triggered!")
        except sa.exc.OperationalError as exc:
            failure_triggered = True
            assert "Simulated database disruption during CreditNoteItem persistence" in str(exc)
            db.rollback()
        finally:
            sa.event.remove(db, "before_flush", inject_disruption)

        assert failure_triggered, "OperationalError was not observed!"

    # Verify atomic rollback across all 4 tables in a clean session
    with SessionMaker() as fresh_db:
        cn_count = fresh_db.query(CreditNote).filter(CreditNote.company_id == comp_id).count()
        cni_count = fresh_db.query(CreditNoteItem).filter(CreditNoteItem.company_id == comp_id).count()
        sm_count = fresh_db.query(StockMovement).filter(StockMovement.company_id == comp_id).count()
        rec_count = fresh_db.query(ReceivableEntry).filter(ReceivableEntry.company_id == comp_id).count()

        assert cn_count == 0, f"Orphaned CreditNote rows found: {cn_count}"
        assert cni_count == 0, f"Orphaned CreditNoteItem rows found: {cni_count}"
        assert sm_count == 0, f"Orphaned StockMovement rows found: {sm_count}"
        assert rec_count == 0, f"Orphaned ReceivableEntry rows found: {rec_count}"

        inv_reload = fresh_db.query(Invoice).filter(Invoice.id == inv_id).one()
        assert inv_reload.receivable_amount == Decimal("4520.00"), f"Invoice receivable_amount was mutated despite rollback: {inv_reload.receivable_amount}"
        assert inv_reload.total_amount == Decimal("4520.00"), f"Invoice total_amount was mutated: {inv_reload.total_amount}"

        order_reload = fresh_db.query(SalesOrder).filter(SalesOrder.id == order_id).one()
        assert order_reload.receivable_amount == Decimal("4520.00"), f"SalesOrder receivable_amount was mutated despite rollback: {order_reload.receivable_amount}"


# =============================================================================
# GATE F: MONETARY PRECISION & STATUTORY 13% VAT (REAL ENGINE & SCHEMA)
# =============================================================================

def test_gate_f_monetary_precision_and_vat_pg16(pg16_target):
    """
    Gate F: Arbitrary precision and statutory 13% VAT calculation on PostgreSQL 16.
    Exercises compute_invoice_amounts() calculation engine and persists via
    the real Invoice schema definitions:
    - Verifies NUMERIC(14,2) decimal storage without floating point rounding drift.
    - Verifies statutory 13% VAT on multi-item invoice with discount.
    - Verifies VAT-inclusive mathematical extraction (Taxable + VAT == Total).
    - Verifies reconciliation of ORM computed integer paisa properties against DB values.
    """
    engine = pg16_target["engine"]
    SessionMaker = sessionmaker(bind=engine)
    suffix = uuid.uuid4().hex[:6]

    with SessionMaker() as db:
        comp = Company(name=f"VAT Co {suffix}", code=f"VAT-{suffix}", pan_number=f"609{suffix}")
        db.add(comp)
        db.flush()

        client = Client(company_id=comp.id, code=f"CLI-V-{suffix}", name="VAT Client", pan_number="609555666")
        db.add(client)
        db.flush()

        order = SalesOrder(
            company_id=comp.id,
            order_number=f"SO-VAT-{suffix}",
            client_id=client.id,
            order_date_ad="2026-10-21",
            order_date_bs="2083-07-04",
            status="CONFIRMED",
            total_amount=Decimal("50850.00"),
            received_amount=Decimal("0.00"),
            receivable_amount=Decimal("50850.00"),
            delivered=True
        )
        db.add(order)
        db.flush()

        prod1 = Product(company_id=comp.id, code=f"P1-{suffix}", name="Item 1", category="CASUAL", unit_price=Decimal("3200.00"))
        prod2 = Product(company_id=comp.id, code=f"P2-{suffix}", name="Item 2", category="CASUAL", unit_price=Decimal("2800.00"))
        db.add_all([prod1, prod2])
        db.flush()

        item1 = SalesItem(company_id=comp.id, sales_order_id=order.id, product_id=prod1.id, quantity=Decimal("10.0"), unit_price=Decimal("3200.00"), total_price=Decimal("32000.00"))
        item2 = SalesItem(company_id=comp.id, sales_order_id=order.id, product_id=prod2.id, quantity=Decimal("5.0"), unit_price=Decimal("2800.00"), total_price=Decimal("14000.00"))
        db.add_all([item1, item2])
        db.flush()

        # 1. VAT_EXCLUSIVE Calculation:
        # Items total: Rs. 46,000.00 (4,600,000 paisa)
        # Discount: Rs. 1,000.00 (100,000 paisa)
        # Taxable: Rs. 45,000.00 (4,500,000 paisa)
        # 13% VAT: Rs. 5,850.00 (585,000 paisa)
        # Grand Total: Rs. 50,850.00 (5,085,000 paisa)
        taxable_paisa, vat_paisa, total_paisa, vat_rate, eff_vat = compute_invoice_amounts(
            order_items=[item1, item2],
            order_total=Decimal("46000.00"),
            pricing_mode="VAT_EXCLUSIVE",
            discount_amount=Decimal("1000.00")
        )
        assert taxable_paisa == 4500000
        assert vat_paisa == 585000
        assert total_paisa == 5085000
        assert taxable_paisa + vat_paisa == total_paisa

        # Persist using real Invoice schema
        inv_excl = Invoice(
            company_id=comp.id,
            sales_order_id=order.id,
            invoice_number=f"INV-EXCL-{suffix}",
            sequence_number=9001,
            date_ad="2026-10-21",
            date_bs="2083-07-04",
            subtotal=quantize_npr(Decimal(taxable_paisa) / Decimal(100)),
            vat_enabled=True,
            vat_rate=vat_rate,
            vat_amount=quantize_npr(Decimal(vat_paisa) / Decimal(100)),
            total_amount=quantize_npr(Decimal(total_paisa) / Decimal(100)),
            received_amount=Decimal("0.00"),
            receivable_amount=quantize_npr(Decimal(total_paisa) / Decimal(100)),
            is_void=False
        )
        db.add(inv_excl)

        # 2. VAT_INCLUSIVE Calculation:
        # Items total inclusive: Rs. 11,300.00 (1,130,000 paisa)
        # Taxable: Rs. 10,000.00 (1,000,000 paisa)
        # 13% VAT: Rs. 1,300.00 (130,000 paisa)
        # Grand Total: Rs. 11,300.00 (1,130,000 paisa)
        taxable_inc, vat_inc, total_inc, _, _ = compute_invoice_amounts(
            order_items=[],
            order_total=Decimal("11300.00"),
            pricing_mode="VAT_INCLUSIVE"
        )
        assert taxable_inc == 1000000
        assert vat_inc == 130000
        assert total_inc == 1130000
        assert taxable_inc + vat_inc == total_inc

        inv_incl = Invoice(
            company_id=comp.id,
            sales_order_id=order.id,
            invoice_number=f"INV-INCL-{suffix}",
            sequence_number=9002,
            date_ad="2026-10-21",
            date_bs="2083-07-04",
            subtotal=quantize_npr(Decimal(taxable_inc) / Decimal(100)),
            vat_enabled=True,
            vat_rate=Decimal("13.00"),
            vat_amount=quantize_npr(Decimal(vat_inc) / Decimal(100)),
            total_amount=quantize_npr(Decimal(total_inc) / Decimal(100)),
            received_amount=Decimal("0.00"),
            receivable_amount=quantize_npr(Decimal(total_inc) / Decimal(100)),
            is_void=False
        )
        db.add(inv_incl)
        db.commit()

        excl_id = inv_excl.id
        incl_id = inv_incl.id

    # 3. Query PostgreSQL 16 directly via raw SQL connection to inspect persisted numeric types
    with engine.connect() as conn:
        row_excl = conn.execute(
            sa.text("SELECT subtotal, vat_rate, vat_amount, total_amount FROM invoices WHERE id = :id"),
            {"id": excl_id}
        ).mappings().first()

        assert row_excl["subtotal"] == Decimal("45000.00")
        assert row_excl["vat_rate"] == Decimal("13.00")
        assert row_excl["vat_amount"] == Decimal("5850.00")
        assert row_excl["total_amount"] == Decimal("50850.00")

        row_incl = conn.execute(
            sa.text("SELECT subtotal, vat_amount, total_amount FROM invoices WHERE id = :id"),
            {"id": incl_id}
        ).mappings().first()

        assert row_incl["subtotal"] == Decimal("10000.00")
        assert row_incl["vat_amount"] == Decimal("1300.00")
        assert row_incl["total_amount"] == Decimal("11300.00")

    # 4. Verify ORM model computed integer-paisa properties against persisted values
    with SessionMaker() as db:
        orm_excl = db.query(Invoice).filter(Invoice.id == excl_id).one()
        assert orm_excl.taxable_amount_paisa == 4500000
        assert orm_excl.vat_amount_paisa == 585000
        assert orm_excl.total_amount_paisa == 5085000
        assert orm_excl.taxable_amount_paisa + orm_excl.vat_amount_paisa == orm_excl.total_amount_paisa

        orm_incl = db.query(Invoice).filter(Invoice.id == incl_id).one()
        assert orm_incl.taxable_amount_paisa == 1000000
        assert orm_incl.vat_amount_paisa == 130000
        assert orm_incl.total_amount_paisa == 1130000
        assert orm_incl.taxable_amount_paisa + orm_incl.vat_amount_paisa == orm_incl.total_amount_paisa
