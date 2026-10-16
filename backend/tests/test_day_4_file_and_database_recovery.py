"""
LIVO Footwear ERP — Day 4 Database-Plus-File Storage Recovery Verification
========================================================================
Proves complete disaster recovery for both PostgreSQL relational records AND
host filesystem assets (gallery images, worker photos, secure citizenship documents).

Simulates:
1. Complete system backup (SQL dump + storage tarball + manifest).
2. Clean restoration into an isolated disposable database and separate filesystem target.
3. Database-to-storage parity reconciliation (zero orphaned or missing files).
4. RBAC access control verification on restored secure assets.
5. Negative failure testing: missing file detection, archive corruption, and path traversal defense.
"""
import os
import tarfile
import hashlib
import pathlib
from pathlib import Path
import tempfile
import time
from decimal import Decimal
from datetime import datetime, timezone, date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic import command
from fastapi.testclient import TestClient

from embedded_postgres import get_server

# Models
from app.models.company import Company
from app.models.user import User
from app.models.stock import Product
from app.models.gallery import ProductImage
from app.models.worker import Worker
from app.core.security import get_password_hash

# Services
from app.services.backup_service import (
    run_database_backup,
    restore_database_backup,
    run_storage_backup,
    restore_storage_backup,
    verify_database_and_file_parity,
    create_complete_system_backup,
    BACKUP_DIR
)
from app.config import settings


def test_complete_database_and_file_recovery_drill(tmp_path, monkeypatch):
    """
    Validates synchronized recovery of database and file storage.
    Ensures that database records and physical files match 100%, and detects any discrepancy.
    """
    pgdata = tmp_path / "pgdata_day4"
    server = get_server(pgdata, cleanup_mode="delete")
    server.ensure_pgdata_inited()
    server.ensure_postgres_running()
    time.sleep(1.5)

    # Isolated storage mock staging directory
    staging_base = tmp_path / "mock_app_root"
    prod_upload_dir = staging_base / "static" / "uploads" / "products"
    worker_upload_dir = staging_base / "static" / "uploads" / "workers"
    secure_hr_dir = staging_base / "storage" / "secure_hr" / "company_1" / "citizenship"

    prod_upload_dir.mkdir(parents=True, exist_ok=True)
    worker_upload_dir.mkdir(parents=True, exist_ok=True)
    secure_hr_dir.mkdir(parents=True, exist_ok=True)

    # Patch BACKEND_DIR in backup_service so it archives our staging_base
    monkeypatch.setattr("app.services.backup_service.BACKEND_DIR", staging_base)

    try:
        raw_master_url = server.get_uri("postgres")
        sa_master_url = raw_master_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        admin_engine = create_engine(sa_master_url, isolation_level="AUTOCOMMIT")

        src_db_name = "livo_day4_files_src"
        dst_db_name = "livo_day4_files_dst"

        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {src_db_name}"))
            conn.execute(text(f"DROP DATABASE IF EXISTS {dst_db_name}"))
            conn.execute(text(f"CREATE DATABASE {src_db_name}"))
            conn.execute(text(f"CREATE DATABASE {dst_db_name}"))

        src_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{src_db_name}"
        src_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{src_db_name}"
        dst_raw_url = raw_master_url.rsplit("/", 1)[0] + f"/{dst_db_name}"
        dst_sa_url = sa_master_url.rsplit("/", 1)[0] + f"/{dst_db_name}"

        # 1. Apply Alembic migrations up to head (024)
        backend_dir = pathlib.Path(__file__).resolve().parent.parent
        alembic_ini = backend_dir / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", src_sa_url)
        command.upgrade(cfg, "head")

        # 2. Seed database records and physical files
        src_engine = create_engine(src_sa_url)
        with Session(src_engine) as session:
            comp = Company(name="Livo Day4 Synthetic Corp", code="LIVO_D4", pan_number="601889900")
            session.add(comp)
            session.commit()
            session.refresh(comp)

            admin_user = User(company_id=comp.id, name="Admin D4", username="admin_d4", password_hash=get_password_hash("Pass123!"), role="admin", active=True)
            viewer_user = User(company_id=comp.id, name="Viewer D4", username="viewer_d4", password_hash=get_password_hash("Pass123!"), role="viewer", active=True)
            session.add_all([admin_user, viewer_user])
            session.commit()

            prod = Product(company_id=comp.id, code="ART-D4-SNEAKER", name="Summit Trail Sneaker", size="42", unit_price=Decimal("4200.00"))
            session.add(prod)
            session.commit()
            session.refresh(prod)

            # Create physical file 1: Product image
            img_filename = "prod_d4_summit.jpg"
            img_file = prod_upload_dir / img_filename
            with open(img_file, "wb") as f:
                f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF_MOCK_JPEG_IMAGE_BYTES_123456789")

            prod_img = ProductImage(
                company_id=comp.id,
                product_id=prod.id,
                image_url=f"/api/v1/gallery/images/{img_filename}",
                file_name=img_filename,
                mime_type="image/jpeg",
                file_size_bytes=img_file.stat().st_size,
                is_primary=True
            )
            session.add(prod_img)

            # Create physical file 2: Worker citizenship document (PDF)
            doc_filename = f"cit_{comp.id}_999_mockhash12345.pdf"
            doc_file = secure_hr_dir / doc_filename
            with open(doc_file, "wb") as f:
                f.write(b"%PDF-1.4_MOCK_GOVERNMENT_CITIZENSHIP_DOCUMENT_CONFIDENTIAL")

            worker = Worker(
                company_id=comp.id,
                worker_code="EMP-D4-01",
                name="Sunita Shrestha",
                pay_type="SALARY",
                basic_rate_paisa=3500000,
                is_active=True,
                citizenship_doc_path=doc_filename,
                citizenship_doc_name="sunita_citizenship.pdf",
                citizenship_uploaded_at=datetime.now(timezone.utc)
            )
            session.add(worker)
            session.commit()
            session.refresh(worker)
            worker_id = worker.id

        # 3. Create synchronized system backup (Database + File Storage)
        monkeypatch.setattr(settings, "DATABASE_URL", src_raw_url)
        system_backup = create_complete_system_backup()
        assert system_backup["overall_status"] == "success"

        db_backup = system_backup["database_backup"]
        files_backup = system_backup["storage_backup"]

        assert db_backup["status"] == "success"
        assert files_backup["status"] == "success"
        assert files_backup["total_files_archived"] >= 2
        assert "sha256" in db_backup
        assert "sha256" in files_backup

        db_backup_path = BACKUP_DIR / db_backup["file_name"]
        files_backup_path = Path(files_backup["file_path"])
        assert db_backup_path.exists()
        assert files_backup_path.exists()

        # 4. Prepare fresh isolated target directory and target database
        restore_base = tmp_path / "restored_app_root"
        restore_base.mkdir(parents=True, exist_ok=True)

        # Restore database
        db_restore_res = restore_database_backup(db_backup_path, target_db_url=dst_raw_url)
        assert db_restore_res["status"] == "success"

        # Restore file storage
        storage_restore_res = restore_storage_backup(files_backup_path, target_base_dir=restore_base)
        assert storage_restore_res["status"] == "success"

        # 5. Verify Database and File Parity
        dst_engine = create_engine(dst_sa_url)
        with Session(dst_engine) as session:
            parity = verify_database_and_file_parity(session, base_dir=restore_base)
            assert parity["status"] == "PARITY_CONFIRMED", f"Parity discrepancies found: {parity['missing_files']}"
            assert parity["missing_files_count"] == 0
            assert parity["verified_files_count"] == 2

            # Confirm file contents match original bytes
            rest_img = restore_base / "static" / "uploads" / "products" / img_filename
            assert rest_img.exists()
            assert rest_img.read_bytes() == b"\xff\xd8\xff\xe0\x00\x10JFIF_MOCK_JPEG_IMAGE_BYTES_123456789"

            rest_doc = restore_base / "storage" / "secure_hr" / "company_1" / "citizenship" / doc_filename
            assert rest_doc.exists()
            assert rest_doc.read_bytes() == b"%PDF-1.4_MOCK_GOVERNMENT_CITIZENSHIP_DOCUMENT_CONFIDENTIAL"

        # 6. Verify RBAC security on restored secure HR files
        # Point SECURE_DOCS_DIR to restored storage
        monkeypatch.setattr("app.api.v1.hr.SECURE_DOCS_DIR", str(restore_base / "storage" / "secure_hr"))

        from app.api.deps import get_db, get_current_user, require_admin
        from app.main import app

        def override_db():
            s = Session(dst_engine)
            try:
                yield s
            finally:
                s.close()

        with Session(dst_engine) as session:
            admin_obj = session.query(User).filter_by(username="admin_d4").first()
            viewer_obj = session.query(User).filter_by(username="viewer_d4").first()

        app.dependency_overrides[get_db] = override_db

        # Test A: Viewer attempt to download citizenship document -> MUST BE REJECTED 403
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            pytest.importorskip("fastapi").HTTPException(status_code=403, detail="Forbidden")
        )
        with TestClient(app) as client:
            resp_viewer = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship")
            assert resp_viewer.status_code == 403, f"Viewer should have been rejected, got: {resp_viewer.status_code}"

        # Test B: Admin can download citizenship document -> HTTP 200 with private cache headers
        app.dependency_overrides[require_admin] = lambda: admin_obj
        app.dependency_overrides[get_current_user] = lambda: admin_obj
        with TestClient(app) as client:
            resp_admin = client.get(f"/api/v1/hr/workers/{worker_id}/citizenship")
            assert resp_admin.status_code == 200
            assert "private, no-store" in resp_admin.headers.get("Cache-Control", "")
            assert resp_admin.content.startswith(b"%PDF-1.4")

        app.dependency_overrides.clear()

        # 7. Negative Failure Tests:
        # A. Missing file detection
        rest_img.unlink()  # Intentionally delete 1 physical file
        with Session(dst_engine) as session:
            parity_fail = verify_database_and_file_parity(session, base_dir=restore_base)
            assert parity_fail["status"] == "DISCREPANCIES_DETECTED"
            assert parity_fail["missing_files_count"] == 1
            assert parity_fail["missing_files"][0]["type"] == "PRODUCT_IMAGE"

        # B. Corrupted storage archive fails cleanly
        corrupt_archive = tmp_path / "corrupt_storage.tar.gz"
        with open(corrupt_archive, "wb") as f:
            f.write(b"CORRUPTED_GZIP_GARBAGE_BYTES_SIMULATION")
        corrupt_res = restore_storage_backup(corrupt_archive, target_base_dir=restore_base)
        assert corrupt_res["status"] == "failed"
        assert corrupt_res["error_message"] is not None

        # C. Zip / Tar Slip Directory Traversal Defense
        slip_archive = tmp_path / "tar_slip_attack.tar.gz"
        with tarfile.open(slip_archive, "w:gz") as tar:
            import io
            dummy_data = b"EVIL_PAYLOAD"
            ti = tarfile.TarInfo(name="../../escaped_passwd.txt")
            ti.size = len(dummy_data)
            tar.addfile(ti, io.BytesIO(dummy_data))

        slip_res = restore_storage_backup(slip_archive, target_base_dir=restore_base)
        assert slip_res["status"] == "failed"
        assert "path traversal" in slip_res["error_message"].lower()

        # Dispose engines prior to drop
        src_engine.dispose()
        dst_engine.dispose()

        # Clean up isolated databases
        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE {src_db_name}"))
            conn.execute(text(f"DROP DATABASE {dst_db_name}"))

        if db_backup_path.exists():
            db_backup_path.unlink()
        if files_backup_path.exists():
            files_backup_path.unlink()

    finally:
        server.cleanup()
