import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.backup_service import (
    run_database_backup,
    get_latest_backup_status,
    save_backup_status,
    upload_to_cloud_storage
)
from app.config import settings

def test_get_latest_backup_status():
    status = get_latest_backup_status()
    assert "status" in status
    assert "timestamp" in status

def test_save_backup_status(tmp_path):
    test_status = {
        "status": "success",
        "timestamp": "2026-09-26T00:00:00Z",
        "file_name": "test_backup.sql",
        "file_size_bytes": 1024,
        "storage_destination": "local",
        "error_message": None
    }
    save_backup_status(test_status)
    read_status = get_latest_backup_status()
    assert read_status["status"] == "success"
    assert read_status["file_name"] == "test_backup.sql"

def test_run_database_backup_postgres_mocked():
    """
    [MOCKED SUBPROCESS TEST]
    Exercises backup_service.py's PostgreSQL pg_dump code path using unittest.mock.patch.
    Mocks subprocess.run to simulate pg_dump generating a SQL backup file on a Postgres DSN.
    """
    def mock_run(cmd, **kwargs):
        # Extract output filename from cmd string -f "path"
        import re
        m = re.search(r'-f "(.*?)"', cmd)
        if m:
            filepath = m.group(1)
            with open(filepath, "w") as f:
                f.write("-- MOCKED PG_DUMP SQL BACKUP DATA\n")
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stderr = ""
        return mock_res

    with patch("app.services.backup_service.settings.DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/testdb"), \
         patch("subprocess.run", side_effect=mock_run) as mock_sub:

        result = run_database_backup()
        assert mock_sub.called
        assert result["status"] == "success"
        assert result["file_name"].startswith("livo_backup_")
        assert result["file_name"].endswith(".sql")


def test_run_database_backup_postgres_failure_mocked():
    """
    [MOCKED SUBPROCESS TEST]
    Exercises backup_service.py's error tracking path when pg_dump returns non-zero exit code.
    """
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stderr = "pg_dump: error: connection failed"

    with patch("app.services.backup_service.settings.DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/testdb"), \
         patch("subprocess.run", return_value=mock_res):

        result = run_database_backup()
        assert result["status"] == "failed"
        assert "pg_dump failed" in result["error_message"]


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models import Company, User, Warehouse, Product, StockMovement
from app.models.invoice import Invoice
from app.models.receivable import ReceivableEntry
from scripts.backup_drill import verify_integrity, TARGET_RPO_MINUTES, TARGET_RTO_MINUTES

def test_backup_drill_integrity_verification(tmp_path):
    """
    Automated Disaster Recovery & Integrity Drill Test.
    Verifies RPO/RTO targets, stock math reconciliation, AR reconciliation,
    and gapless invoice sequence checks.
    """
    assert TARGET_RPO_MINUTES <= 60
    assert TARGET_RTO_MINUTES <= 15

    db_file = tmp_path / "drill_test.db"
    engine_test = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine_test)
    SessionTest = sessionmaker(bind=engine_test)
    session = SessionTest()

    # Seed company
    comp = Company(name="Drill Company", code="DRILL_CO")
    session.add(comp)
    session.commit()
    session.refresh(comp)

    # Seed warehouse
    wh = Warehouse(company_id=comp.id, name="Drill WH", code="WH-DRILL", is_active=True)
    session.add(wh)
    session.commit()

    # Seed product & stock movement
    p = Product(company_id=comp.id, code="DRILL-SNK-40", name="Drill Sneaker", size="40", unit_price=2000.0)
    session.add(p)
    session.commit()
    session.refresh(p)

    m1 = StockMovement(company_id=comp.id, product_id=p.id, warehouse_id=1, direction=1, quantity=10.0, ref_type="production", date_ad="2026-10-01", date_bs="2083-06-15", notes="In")
    m2 = StockMovement(company_id=comp.id, product_id=p.id, warehouse_id=1, direction=-1, quantity=3.0, ref_type="sale", date_ad="2026-10-01", date_bs="2083-06-15", notes="Out")
    session.add_all([m1, m2])
    session.commit()

    # Seed client & receivable entries
    from app.models.sales import Client
    cl = Client(company_id=comp.id, code="DRILL-CLI", name="Drill Client")
    session.add(cl)
    session.commit()
    session.refresh(cl)

    u = User(company_id=comp.id, name="Actor", username="drill_actor", password_hash="mock_hash", role="editor", active=True)
    session.add(u)
    session.commit()
    session.refresh(u)

    r1 = ReceivableEntry(company_id=comp.id, client_id=cl.id, entry_type="INVOICE_POSTED", direction=1, amount_paisa=50000, actor_id=u.id)
    r2 = ReceivableEntry(company_id=comp.id, client_id=cl.id, entry_type="PAYMENT_CASH", direction=-1, amount_paisa=20000, actor_id=u.id)
    session.add_all([r1, r2])
    session.commit()

    # Seed continuous invoices
    from app.models.sales import SalesOrder
    so = SalesOrder(
        company_id=comp.id,
        order_number="SO-01-00001",
        client_id=cl.id,
        order_date_ad="2026-10-01",
        order_date_bs="2083-06-15",
        status="delivered",
        total_amount=300.0
    )
    session.add(so)
    session.commit()
    session.refresh(so)

    inv1 = Invoice(
        company_id=comp.id,
        sales_order_id=so.id,
        invoice_number="INV-01-00001",
        sequence_number=1,
        date_ad="2026-10-01",
        date_bs="2083-06-15",
        subtotal=100.0,
        vat_enabled=False,
        vat_rate=0.0,
        vat_amount=0.0,
        total_amount=100.0
    )
    inv2 = Invoice(
        company_id=comp.id,
        sales_order_id=so.id,
        invoice_number="INV-01-00002",
        sequence_number=2,
        date_ad="2026-10-01",
        date_bs="2083-06-15",
        subtotal=200.0,
        vat_enabled=False,
        vat_rate=0.0,
        vat_amount=0.0,
        total_amount=200.0
    )
    session.add_all([inv1, inv2])
    session.commit()

    # Verify integrity passes cleanly
    report = verify_integrity(session)
    assert report["status"] == "ALL_CHECKS_PASSED"
    assert report["checks"]["stock_movement_reconciliation"]["total_on_hand_pairs"] == 7.0
    assert report["checks"]["ar_ledger_reconciliation"]["total_outstanding_paisa"] == 30000
    assert report["checks"]["invoice_sequence_continuity"]["verified_invoices_count"] == 2

    # Test gap detection in invoice sequence
    inv_gap = Invoice(
        company_id=comp.id,
        sales_order_id=so.id,
        invoice_number="INV-01-00005",
        sequence_number=5,
        date_ad="2026-10-01",
        date_bs="2083-06-15",
        subtotal=50.0,
        vat_enabled=False,
        vat_rate=0.0,
        vat_amount=0.0,
        total_amount=50.0
    )
    session.add(inv_gap)
    session.commit()

    with pytest.raises(AssertionError, match="Invoice sequence gap detected"):
        verify_integrity(session)

    session.close()

