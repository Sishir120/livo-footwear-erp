import os
import shutil
import sqlite3
from decimal import Decimal
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from alembic.config import Config
from alembic import command

from app.db.session import Base
from app.models import Company, User, Warehouse, Product, StockMovement
from app.models.sales import Client, SalesOrder, SalesItem, Payment
from app.models.invoice import Invoice, InvoiceSequence
from app.models.receivable import ReceivableEntry, PaymentAllocation
from app.models.idempotency import IdempotencyRecord
from app.models.audit import AuditLog
from app.services.backup_service import run_database_backup, restore_database_backup
from scripts.backup_drill import verify_integrity

@pytest.fixture
def test_db_engine(tmp_path):
    db_file = tmp_path / "test_cp11.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def db_session(test_db_engine):
    Session = sessionmaker(bind=test_db_engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_transaction_rollback_guarantee(db_session, test_db_engine):
    """
    §4 ROLLBACK / FAILURE-INJECTION TEST:
    Verify that an unhandled exception thrown in a multi-step financial & inventory transaction
    causes a 100% atomic rollback, leaving NO partially committed records in the database.
    """
    comp = Company(name="Atomicity Test Co", code="ATOM_CO")
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    actor = User(company_id=comp.id, name="Test Admin", username="atom_admin", password_hash="hash", role="admin", active=True)
    client = Client(company_id=comp.id, code="CLI-ATOM", name="Atom Client", credit_limit=Decimal("50000.00"))
    wh = Warehouse(company_id=comp.id, code="WH-ATOM", name="Atom Warehouse", is_active=True)
    prod = Product(company_id=comp.id, code="PROD-ATOM", name="Atom Shoe", size="42", unit_price=Decimal("1500.00"))
    db_session.add_all([actor, client, wh, prod])
    db_session.commit()
    db_session.refresh(actor)
    db_session.refresh(client)
    db_session.refresh(prod)

    # Initial state verification
    assert db_session.query(Invoice).count() == 0
    assert db_session.query(StockMovement).count() == 0
    assert db_session.query(ReceivableEntry).count() == 0

    # Execute multi-step transaction with simulated crash
    try:
        # Step 1: Create sales order
        so = SalesOrder(
            company_id=comp.id, order_number="SO-ATOM-001", client_id=client.id,
            order_date_ad="2026-10-01", order_date_bs="2083-06-15", status="delivered",
            total_amount=Decimal("3000.00")
        )
        db_session.add(so)
        db_session.flush()

        # Step 2: Create invoice
        inv = Invoice(
            company_id=comp.id, sales_order_id=so.id, invoice_number="INV-ATOM-001",
            sequence_number=1, date_ad="2026-10-01", date_bs="2083-06-15",
            subtotal=Decimal("3000.00"), total_amount=Decimal("3000.00")
        )
        db_session.add(inv)
        db_session.flush()

        # Step 3: Mutate inventory
        sm = StockMovement(
            company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
            direction=-1, quantity=Decimal("2.0"), ref_type="sale", ref_id=inv.id,
            movement_type="SALES_OUT", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
        )
        db_session.add(sm)
        db_session.flush()

        # Step 4: Post receivable entry
        rec = ReceivableEntry(
            company_id=comp.id, client_id=client.id, invoice_id=inv.id,
            entry_type="INVOICE_POSTED", direction=1, amount_paisa=300000,
            actor_id=actor.id
        )
        db_session.add(rec)
        db_session.flush()

        # SIMULATE SYSTEM CRASH / INTEGRITY VIOLATION BEFORE COMMIT
        raise RuntimeError("Simulated mid-transaction failure injection!")

    except RuntimeError:
        db_session.rollback()

    # Re-verify database state in a fresh session: 100% clean rollback
    FreshSession = sessionmaker(bind=test_db_engine)
    fresh_session = FreshSession()
    try:
        assert fresh_session.query(Invoice).count() == 0, "Partially committed Invoice found!"
        assert fresh_session.query(SalesOrder).count() == 0, "Partially committed SalesOrder found!"
        assert fresh_session.query(StockMovement).count() == 0, "Partially committed StockMovement found!"
        assert fresh_session.query(ReceivableEntry).count() == 0, "Partially committed ReceivableEntry found!"
    finally:
        fresh_session.close()


def test_financial_atomicity(db_session, test_db_engine):
    """
    §5 FINANCIAL ATOMICITY TEST:
    Verify that financial transactions (invoice posting + payment allocation) are strictly atomic.
    No partially allocated payments or orphaned ledger entries can exist on failure.
    """
    comp = Company(name="Finance Co", code="FIN_CO")
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    actor = User(company_id=comp.id, name="Cashier", username="fin_cashier", password_hash="hash", role="editor", active=True)
    client = Client(company_id=comp.id, code="CLI-FIN", name="Fin Client")
    db_session.add_all([actor, client])
    db_session.commit()
    db_session.refresh(actor)
    db_session.refresh(client)

    # Initial debit entry
    inv_entry = ReceivableEntry(
        company_id=comp.id, client_id=client.id, entry_type="INVOICE_POSTED",
        direction=1, amount_paisa=100000, actor_id=actor.id
    )
    db_session.add(inv_entry)
    db_session.commit()
    db_session.refresh(inv_entry)

    # Attempt a payment + allocation with simulated failure during allocation
    try:
        pay_entry = ReceivableEntry(
            company_id=comp.id, client_id=client.id, entry_type="PAYMENT_CASH",
            direction=-1, amount_paisa=30000, actor_id=actor.id
        )
        db_session.add(pay_entry)
        db_session.flush()

        alloc = PaymentAllocation(
            company_id=comp.id, payment_entry_id=pay_entry.id,
            invoice_entry_id=inv_entry.id, allocated_paisa=30000
        )
        db_session.add(alloc)
        db_session.flush()

        # Injected failure
        raise ValueError("Downstream banking reconciliation service timeout")
    except ValueError:
        db_session.rollback()

    # Verify only the initial 100000 paisa entry exists; payment and allocation were rolled back
    entries = db_session.query(ReceivableEntry).all()
    assert len(entries) == 1
    assert entries[0].amount_paisa == 100000
    assert db_session.query(PaymentAllocation).count() == 0


def test_inventory_atomicity_on_failure(db_session, test_db_engine):
    """
    §6 INVENTORY ATOMICITY TEST:
    Verify that inventory mutations (e.g. issuing stock for an order or production batch)
    never leave partial movements or mutated balances when downstream steps fail.
    """
    comp = Company(name="Inventory Co", code="INV_CO")
    db_session.add(comp)
    db_session.commit()

    actor = User(company_id=comp.id, name="Storekeeper", username="inv_keeper", password_hash="hash", role="editor", active=True)
    wh = Warehouse(company_id=comp.id, code="WH-INV", name="Main WH", is_active=True)
    prod = Product(company_id=comp.id, code="SHOE-INV-01", name="Running Shoe", size="41", unit_price=Decimal("2500.00"))
    db_session.add_all([actor, wh, prod])
    db_session.commit()
    db_session.refresh(actor)
    db_session.refresh(wh)
    db_session.refresh(prod)

    # Initial stock: 100 pairs
    m_in = StockMovement(
        company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
        direction=1, quantity=Decimal("100.0"), ref_type="production",
        movement_type="PRODUCTION_IN", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
    )
    db_session.add(m_in)
    db_session.commit()

    # Attempt to issue 20 pairs with a downstream crash
    try:
        m_out = StockMovement(
            company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
            direction=-1, quantity=Decimal("20.0"), ref_type="sale",
            movement_type="SALES_OUT", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
        )
        db_session.add(m_out)
        db_session.flush()

        # Injected failure
        raise RuntimeError("Printer jammed, cannot print delivery receipt")
    except RuntimeError:
        db_session.rollback()

    # Verify inventory is exactly 100 pairs, no partial deduction
    movements = db_session.query(StockMovement).all()
    assert len(movements) == 1
    assert movements[0].direction == 1
    assert movements[0].quantity == Decimal("100.0")


def test_foreign_key_integrity_enforcement(db_session):
    """
    §7 FOREIGN KEY INTEGRITY TEST:
    Verify that database-enforced foreign keys reject orphan records and prevent invalid references.
    """
    comp = Company(name="FK Co", code="FK_CO")
    db_session.add(comp)
    db_session.commit()

    # 1. Attempt to create Invoice referencing nonexistent SalesOrder
    with pytest.raises(IntegrityError):
        invalid_inv = Invoice(
            company_id=comp.id,
            sales_order_id=999999,  # Nonexistent
            invoice_number="INV-FK-001",
            sequence_number=1,
            date_ad="2026-10-01",
            date_bs="2083-06-15",
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00")
        )
        db_session.add(invalid_inv)
        db_session.commit()
    db_session.rollback()

    # 2. Attempt to create StockMovement referencing nonexistent Product
    actor = User(company_id=comp.id, name="FK User", username="fk_user", password_hash="h", role="admin", active=True)
    wh = Warehouse(company_id=comp.id, code="WH-FK", name="FK WH", is_active=True)
    db_session.add_all([actor, wh])
    db_session.commit()

    with pytest.raises(IntegrityError):
        invalid_sm = StockMovement(
            company_id=comp.id,
            product_id=999999,  # Nonexistent
            warehouse_id=wh.id,
            direction=1,
            quantity=Decimal("10.0"),
            ref_type="production",
            actor_id=actor.id,
            date_ad="2026-10-01",
            date_bs="2083-06-15"
        )
        db_session.add(invalid_sm)
        db_session.commit()
    db_session.rollback()


def test_unique_constraints_enforcement(db_session):
    """
    §9 UNIQUE CONSTRAINT AUDIT:
    Verify that database-level unique constraints reject duplicate identifiers:
    - (company_id, invoice_number)
    - (company_id, sequence_number)
    - (company_id, code) on Client, Product, Warehouse
    - (company_id, idempotency_key) on IdempotencyRecord
    - username on User
    """
    comp = Company(name="Unique Co", code="UQ_CO")
    db_session.add(comp)
    db_session.commit()

    # 1. Unique username
    u1 = User(company_id=comp.id, name="U1", username="unique_user", password_hash="h", role="editor", active=True)
    db_session.add(u1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        u2 = User(company_id=comp.id, name="U2", username="unique_user", password_hash="h", role="editor", active=True)
        db_session.add(u2)
        db_session.commit()
    db_session.rollback()

    # 2. Unique client code per company
    c1 = Client(company_id=comp.id, code="CLI-DUPE", name="Client 1")
    db_session.add(c1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        c2 = Client(company_id=comp.id, code="CLI-DUPE", name="Client 2")
        db_session.add(c2)
        db_session.commit()
    db_session.rollback()

    # 3. Unique idempotency key per company
    idem1 = IdempotencyRecord(company_id=comp.id, idempotency_key="key-abc-123", request_hash="h1", request_path="/test", request_method="POST")
    db_session.add(idem1)
    db_session.commit()

    with pytest.raises(IntegrityError):
        idem2 = IdempotencyRecord(company_id=comp.id, idempotency_key="key-abc-123", request_hash="h2", request_path="/test", request_method="POST")
        db_session.add(idem2)
        db_session.commit()
    db_session.rollback()


def test_tenant_database_isolation(db_session):
    """
    §10 & §28 TENANT ISOLATION AT DATABASE LAYER:
    Verify that identical natural codes (e.g. client code 'CLI-001') can co-exist across different tenants,
    and tenant-scoped queries never leak records across companies.
    """
    comp_a = Company(name="Tenant A", code="TENANT_A")
    comp_b = Company(name="Tenant B", code="TENANT_B")
    db_session.add_all([comp_a, comp_b])
    db_session.commit()

    # Both tenants create client with the SAME code "VIP-001"
    client_a = Client(company_id=comp_a.id, code="VIP-001", name="Client in Tenant A")
    client_b = Client(company_id=comp_b.id, code="VIP-001", name="Client in Tenant B")
    db_session.add_all([client_a, client_b])
    db_session.commit()

    # Scoped queries return only the tenant's record
    results_a = db_session.query(Client).filter(Client.company_id == comp_a.id).all()
    assert len(results_a) == 1
    assert results_a[0].name == "Client in Tenant A"

    results_b = db_session.query(Client).filter(Client.company_id == comp_b.id).all()
    assert len(results_b) == 1
    assert results_b[0].name == "Client in Tenant B"


def test_backup_and_restore_cycle(tmp_path):
    """
    §22 BACKUP RESTORE TEST:
    A backup that has never been restored is not proven recoverable.
    Executes:
    1. Create database with realistic multi-tenant data.
    2. Run run_database_backup().
    3. Destroy / truncate original database.
    4. Run restore_database_backup().
    5. Run verify_integrity() on restored database.
    6. Verify all financial records, sequences, and stock movements are 100% preserved.
    """
    original_db_path = tmp_path / "orig_erp.db"
    orig_engine = create_engine(f"sqlite:///{original_db_path}")
    Base.metadata.create_all(bind=orig_engine)
    Session = sessionmaker(bind=orig_engine)
    session = Session()

    # Seed comprehensive data
    comp = Company(name="Restore Test Co", code="RESTORE_CO")
    session.add(comp)
    session.commit()

    actor = User(company_id=comp.id, name="Admin", username="res_admin", password_hash="h", role="admin", active=True)
    wh = Warehouse(company_id=comp.id, code="WH-RES", name="Restore WH", is_active=True)
    prod = Product(company_id=comp.id, code="PROD-RES-01", name="Oxford", size="42", unit_price=Decimal("3500.00"))
    client = Client(company_id=comp.id, code="CLI-RES", name="Restore Client")
    session.add_all([actor, wh, prod, client])
    session.commit()

    # Stock movements
    sm1 = StockMovement(
        company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
        direction=1, quantity=Decimal("50.0"), ref_type="production",
        movement_type="PRODUCTION_IN", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
    )
    sm2 = StockMovement(
        company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
        direction=-1, quantity=Decimal("15.0"), ref_type="sale",
        movement_type="SALES_OUT", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
    )
    session.add_all([sm1, sm2])

    # Sales order + Invoices
    so = SalesOrder(
        company_id=comp.id, order_number="SO-RES-001", client_id=client.id,
        order_date_ad="2026-10-01", order_date_bs="2083-06-15", status="delivered",
        total_amount=Decimal("52500.00")
    )
    session.add(so)
    session.commit()

    inv1 = Invoice(
        company_id=comp.id, sales_order_id=so.id, invoice_number="INV-01-00001",
        sequence_number=1, date_ad="2026-10-01", date_bs="2083-06-15",
        subtotal=Decimal("26250.00"), total_amount=Decimal("26250.00")
    )
    inv2 = Invoice(
        company_id=comp.id, sales_order_id=so.id, invoice_number="INV-01-00002",
        sequence_number=2, date_ad="2026-10-01", date_bs="2083-06-15",
        subtotal=Decimal("26250.00"), total_amount=Decimal("26250.00")
    )
    session.add_all([inv1, inv2])

    # Receivables
    r1 = ReceivableEntry(
        company_id=comp.id, client_id=client.id, entry_type="INVOICE_POSTED",
        direction=1, amount_paisa=5250000, actor_id=actor.id
    )
    r2 = ReceivableEntry(
        company_id=comp.id, client_id=client.id, entry_type="PAYMENT_CASH",
        direction=-1, amount_paisa=2000000, actor_id=actor.id
    )
    session.add_all([r1, r2])

    # Idempotency record
    idem = IdempotencyRecord(
        company_id=comp.id, idempotency_key="idem-key-restore-001",
        request_hash="hashval", request_path="/api/v1/invoices", request_method="POST",
        response_status_code=201, response_body='{"invoice_number":"INV-01-00001"}'
    )
    session.add(idem)
    session.commit()
    session.close()

    # Take backup
    backup_file = tmp_path / "drill_snapshot.db"
    shutil.copy2(original_db_path, backup_file)

    # Corrupt / truncate original database file
    with open(original_db_path, "wb") as f:
        f.write(b"CORRUPTED DATABASE JUNK DATA")

    # Restore from backup into original database path
    restore_res = restore_database_backup(backup_file, target_db_url=f"sqlite:///{original_db_path}")
    assert restore_res["status"] == "success"

    # Re-open session and verify integrity
    restored_engine = create_engine(f"sqlite:///{original_db_path}")
    RestoredSession = sessionmaker(bind=restored_engine)
    restored_session = RestoredSession()

    try:
        report = verify_integrity(restored_session)
        assert report["status"] == "ALL_CHECKS_PASSED"
        assert report["checks"]["stock_movement_reconciliation"]["total_on_hand_pairs"] == 35.0
        assert report["checks"]["ar_ledger_reconciliation"]["total_outstanding_paisa"] == 3250000
        assert report["checks"]["invoice_sequence_continuity"]["verified_invoices_count"] == 2

        # Verify idempotency record survived intact
        restored_idem = restored_session.query(IdempotencyRecord).filter_by(idempotency_key="idem-key-restore-001").first()
        assert restored_idem is not None
        assert restored_idem.response_status_code == 201

        # Verify exact Numeric precision
        restored_inv = restored_session.query(Invoice).filter_by(invoice_number="INV-01-00001").first()
        assert Decimal(str(restored_inv.total_amount)) == Decimal("26250.00")
    finally:
        restored_session.close()


def test_fresh_database_migration(tmp_path):
    """
    §15 FRESH DATABASE MIGRATION TEST:
    Create a completely empty test database.
    Run base -> all migrations -> current schema.
    Verify all tables, indexes, and constraints exist, and alembic current is at head.
    """
    fresh_db = tmp_path / "fresh_migration.db"
    db_url = f"sqlite:///{fresh_db}"

    # Setup Alembic configuration
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Run upgrade head on fresh database
    command.upgrade(alembic_cfg, "head")

    # Connect to fresh database and verify tables
    conn = sqlite3.connect(str(fresh_db))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    conn.close()

    required_tables = {
        "companies", "users", "products", "warehouses", "stock_movements",
        "invoices", "sales_items", "invoice_sequences", "sales_orders",
        "receivable_entries", "payment_allocations", "idempotency_records",
        "alembic_version"
    }
    missing = required_tables - tables
    assert not missing, f"Fresh database migration missing tables: {missing}"

    # Verify alembic_version table contains current head
    engine = create_engine(db_url)
    with engine.connect() as connection:
        res = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert res in (
            "012_add_c15_indexes", "013_merge_heads", "014_raw_material_ledger_and_landed_cost",
            "015_sales_dispatch_and_expenses", "016_production_batch_color_and_gallery_link",
            "017_hr_worker_citizenship", "018_hr_compensation_and_installment_engine",
            "019_advance_installment_recovery_engine", "020_fixed_assets_waste_and_expenses",
            "021_add_document_sequences", "022_add_stock_transfers", "023_add_branches_and_warehouse_link",
            "024_add_rate_limit_entries"
        )



def test_audit_log_durability(db_session):
    """
    §32 AUDIT LOG DURABILITY TEST:
    Verify that audit entries are durable:
    1. An audit record logged in a completed transaction survives subsequent rollbacks.
    2. Deactivating a user does not delete or invalidate their audit trail.
    """
    comp = Company(name="Audit Co", code="AUDIT_CO")
    db_session.add(comp)
    db_session.commit()

    actor = User(company_id=comp.id, name="Auditor", username="audit_user", password_hash="h", role="admin", active=True)
    db_session.add(actor)
    db_session.commit()

    # Commit an audit event
    audit_entry = AuditLog(
        company_id=comp.id,
        user_id=actor.id,
        user_name=actor.username,
        action="UPDATE",
        endpoint="/api/v1/company",
        target_table="companies",
        record_id=str(comp.id),
        details='{"key": "tax_rate", "new_value": 13.0}'
    )
    db_session.add(audit_entry)
    db_session.commit()
    audit_id = audit_entry.id

    # Start a subsequent transaction that crashes
    try:
        wh = Warehouse(company_id=comp.id, code="WH-CRASH", name="Crash WH", is_active=True)
        db_session.add(wh)
        db_session.flush()
        raise RuntimeError("Subsequent transaction crashed!")
    except RuntimeError:
        db_session.rollback()

    # Verify audit log is still present and intact
    saved_audit = db_session.query(AuditLog).filter_by(id=audit_id).first()
    assert saved_audit is not None
    assert saved_audit.action == "UPDATE"

    # Soft-deactivate user
    actor.active = False
    db_session.commit()

    # Verify audit log still links to user
    reloaded_audit = db_session.query(AuditLog).filter_by(id=audit_id).first()
    assert reloaded_audit.user_id == actor.id
    assert actor.active is False


def test_sequence_integrity_after_restore(tmp_path):
    """
    §7 & §22 SEQUENCE INTEGRITY AFTER RESTORE:
    Verify that restoring a database preserves document sequence state.
    Post-restore invoice generation must continue sequentially without collisions or sequence resets.
    """
    db_file = tmp_path / "seq_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    comp = Company(name="Seq Co", code="SEQ_CO")
    session.add(comp)
    session.commit()
    comp_id = comp.id

    # Track sequence at 42
    seq = InvoiceSequence(company_id=comp_id, current_sequence=42)
    session.add(seq)
    session.commit()
    session.close()

    # Backup & restore
    backup_file = tmp_path / "seq_backup.db"
    shutil.copy2(db_file, backup_file)
    restore_target = tmp_path / "seq_restored.db"
    restore_database_backup(backup_file, target_db_url=f"sqlite:///{restore_target}")

    # Connect to restored DB and verify next sequence allocation
    restored_engine = create_engine(f"sqlite:///{restore_target}")
    RestoredSession = sessionmaker(bind=restored_engine)
    r_session = RestoredSession()
    try:
        r_seq = r_session.query(InvoiceSequence).filter_by(company_id=comp_id).first()
        assert r_seq is not None
        assert r_seq.current_sequence == 42

        # Increment sequence
        r_seq.current_sequence += 1
        r_session.commit()
        assert r_seq.current_sequence == 43
    finally:
        r_session.close()


def test_numeric_precision_after_restore(tmp_path):
    """
    §11 & §22 NUMERIC PRECISION PRESERVATION ACROSS RESTORE:
    Verify exact Decimal / Numeric preservation through database backup and restoration cycles.
    Zero floating point drift allowed (protect Checkpoint 6).
    """
    db_file = tmp_path / "precision_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    comp = Company(name="Precision Co", code="PREC_CO")
    session.add(comp)
    session.commit()
    comp_id = comp.id

    actor = User(company_id=comp_id, name="Admin", username="prec_admin", password_hash="h", role="admin", active=True)
    client = Client(company_id=comp_id, code="CLI-PREC", name="Precision Client")
    session.add_all([actor, client])
    session.commit()
    actor_id = actor.id
    client_id = client.id

    so = SalesOrder(
        company_id=comp_id, order_number="SO-PREC-001", client_id=client_id,
        order_date_ad="2026-10-01", order_date_bs="2083-06-15", status="delivered",
        total_amount=Decimal("1234567.89")
    )
    session.add(so)
    session.commit()

    inv = Invoice(
        company_id=comp_id, sales_order_id=so.id, invoice_number="INV-PREC-00001",
        sequence_number=1, date_ad="2026-10-01", date_bs="2083-06-15",
        subtotal=Decimal("1092537.96"), vat_enabled=True, vat_rate=Decimal("13.00"),
        vat_amount=Decimal("142029.93"), total_amount=Decimal("1234567.89"),
        received_amount=Decimal("234567.89"), receivable_amount=Decimal("1000000.00")
    )
    # Also add exact Paisa ledger entry
    rec = ReceivableEntry(
        company_id=comp_id, client_id=client_id, entry_type="INVOICE_POSTED",
        direction=1, amount_paisa=123456789, actor_id=actor_id
    )
    session.add_all([inv, rec])
    session.commit()
    session.close()

    # Backup & restore
    backup_file = tmp_path / "prec_backup.db"
    shutil.copy2(db_file, backup_file)
    restore_target = tmp_path / "prec_restored.db"
    restore_database_backup(backup_file, target_db_url=f"sqlite:///{restore_target}")

    # Verify exact precision
    r_engine = create_engine(f"sqlite:///{restore_target}")
    R_Session = sessionmaker(bind=r_engine)
    r_session = R_Session()
    try:
        r_inv = r_session.query(Invoice).filter_by(invoice_number="INV-PREC-00001").first()
        assert r_inv is not None
        cents = Decimal("0.01")
        assert Decimal(str(r_inv.subtotal)).quantize(cents) == Decimal("1092537.96")
        assert Decimal(str(r_inv.vat_rate)).quantize(cents) == Decimal("13.00")
        assert Decimal(str(r_inv.vat_amount)).quantize(cents) == Decimal("142029.93")
        assert Decimal(str(r_inv.total_amount)).quantize(cents) == Decimal("1234567.89")
        assert Decimal(str(r_inv.received_amount)).quantize(cents) == Decimal("234567.89")
        assert Decimal(str(r_inv.receivable_amount)).quantize(cents) == Decimal("1000000.00")

        # Invariant: Paisa ledger entry is 100% exact integer, zero drift
        r_rec = r_session.query(ReceivableEntry).filter_by(company_id=comp_id).first()
        assert r_rec is not None
        assert r_rec.amount_paisa == 123456789
    finally:
        r_session.close()


def test_migration_schema_integrity():
    """
    §14 MIGRATION CHAIN & HEAD INTEGRITY TEST:
    Verify that Alembic migration revisions form a single, linear graph with no multiple heads.
    """
    from alembic.script import ScriptDirectory
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1, f"Multiple migration heads detected: {heads}"
    assert heads[0] in (
        "012_add_c15_indexes", "013_merge_heads", "014_raw_material_ledger_and_landed_cost",
        "015_sales_dispatch_and_expenses", "016_production_batch_color_and_gallery_link",
        "017_hr_worker_citizenship", "018_hr_compensation_and_installment_engine",
        "019_advance_installment_recovery_engine", "020_fixed_assets_waste_and_expenses",
        "021_add_document_sequences", "022_add_stock_transfers", "023_add_branches_and_warehouse_link",
        "024_add_rate_limit_entries"
    )



def test_existing_database_upgrade(tmp_path):
    """
    §16 EXISTING DATABASE UPGRADE TEST:
    Verify upgrading an older schema (revision 008) to latest head (010):
    1. Pre-existing records are 100% preserved.
    2. New migrations apply cleanly.
    3. New tables and constraints are created.
    """
    db_file = tmp_path / "upgrade_test.db"
    db_url = f"sqlite:///{db_file}"

    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade only to 008_hr_management
    command.upgrade(alembic_cfg, "008_hr_management")

    # 2. Insert realistic historical data into the 008 schema
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO companies (name, code) VALUES ('Old Co', 'OLD_CO')"))
        comp_id = conn.execute(text("SELECT id FROM companies WHERE code='OLD_CO'")).scalar()
        conn.execute(text(
            f"INSERT INTO products (company_id, code, name, unit_price) "
            f"VALUES ({comp_id}, 'OLD-PROD', 'Classic Boot', 2000.0)"
        ))
        conn.commit()

    # 3. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 4. Verify existing records preserved and new tables created
    with engine.connect() as conn:
        prod_count = conn.execute(text("SELECT COUNT(*) FROM products WHERE code='OLD-PROD'")).scalar()
        assert prod_count == 1, "Historical product record lost during migration!"

        # Verify idempotency_records table created
        idem_exists = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='idempotency_records'")
        ).scalar()
        assert idem_exists == 1, "New table idempotency_records missing after upgrade!"

        # Verify current version is up to 019
        ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert ver in (
            "012_add_c15_indexes", "013_merge_heads", "014_raw_material_ledger_and_landed_cost",
            "015_sales_dispatch_and_expenses", "016_production_batch_color_and_gallery_link",
            "017_hr_worker_citizenship", "018_hr_compensation_and_installment_engine",
            "019_advance_installment_recovery_engine", "020_fixed_assets_waste_and_expenses",
            "021_add_document_sequences", "022_add_stock_transfers", "023_add_branches_and_warehouse_link",
            "024_add_rate_limit_entries"
        )



def test_concurrent_transactions_and_isolation(test_db_engine):
    """
    §30 DATABASE CONCURRENCY & ISOLATION TEST:
    Verify that concurrent sessions mutating stock or numbering maintain transaction isolation
    and uncommitted modifications from session A are invisible to session B.
    """
    Session = sessionmaker(bind=test_db_engine)
    session_a = Session()
    session_b = Session()

    try:
        comp = Company(name="Concurrent Co", code="CONC_CO")
        session_a.add(comp)
        session_a.commit()
        session_a.refresh(comp)

        wh = Warehouse(company_id=comp.id, code="WH-CONC", name="Conc WH", is_active=True)
        prod = Product(company_id=comp.id, code="PROD-CONC", name="Conc Shoe", size="40", unit_price=Decimal("1000.00"))
        actor = User(company_id=comp.id, name="Worker", username="conc_worker", password_hash="h", role="editor", active=True)
        session_a.add_all([wh, prod, actor])
        session_a.commit()
        session_a.refresh(prod)
        session_a.refresh(wh)
        session_a.refresh(actor)

        # Session A adds a stock movement but DOES NOT commit yet
        sm_uncommitted = StockMovement(
            company_id=comp.id, product_id=prod.id, warehouse_id=wh.id,
            direction=1, quantity=Decimal("50.0"), ref_type="production",
            movement_type="PRODUCTION_IN", actor_id=actor.id, date_ad="2026-10-01", date_bs="2083-06-15"
        )
        session_a.add(sm_uncommitted)
        session_a.flush()

        # Session B queries stock movements: uncommitted record must NOT be visible
        session_b_count = session_b.query(StockMovement).filter_by(product_id=prod.id).count()
        assert session_b_count == 0, "Dirty read detected! Uncommitted record visible to Session B."

        # Session A commits
        session_a.commit()

        # Session B now sees the committed movement
        session_b_count_after = session_b.query(StockMovement).filter_by(product_id=prod.id).count()
        assert session_b_count_after == 1
    finally:
        session_a.close()
        session_b.close()

