"""
LIVO Footwear ERP — Day 7.1 Demo Seeding & Backup Command Verification Suite
=============================================================================
Verifies:
1. Production mode unconditionally rejects demo seeding (fail closed).
2. Staging mode rejects automatic demo seeding (prevents accidental credential generation in staging).
3. Routine startup with ENABLE_DEMO_SEEDING=false skips seeding.
4. Pre-existing accounts preserve passwords, roles, and status without overwrite.
5. Backup CLI creates valid DB dump, storage archive, and manifest with verified SHA-256 hashes.
"""

import os
import json
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.session import Base
from app.models.company import Company
from app.models.user import User
from app.core.demo_seeding import seed_demo_users_if_enabled
from app.services import backup_service


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        comp = Company(name="LIVO Test Footwear", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)
        yield db, comp


def test_demo_seeding_production_refusal(memory_db):
    """Safeguard 1: Production unconditionally rejects demo seeding."""
    db, comp = memory_db
    with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
        with patch.object(settings, "ENVIRONMENT", "production"):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "rejected"
            assert res["reason"] == "production_mode_refusal"
            assert db.query(User).count() == 0


def test_demo_seeding_staging_refusal(memory_db):
    """Safeguard 2: Staging rejects automatic startup seeding (fail closed on non-whitelisted env)."""
    db, comp = memory_db
    with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
        with patch.object(settings, "ENVIRONMENT", "staging"):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "rejected"
            assert res["reason"] == "ambiguous_environment_refusal"
            assert db.query(User).count() == 0


def test_demo_seeding_disabled_by_default(memory_db):
    """Safeguard 3: ENABLE_DEMO_SEEDING=false skips seeding even in development."""
    db, comp = memory_db
    with patch.object(settings, "ENABLE_DEMO_SEEDING", False):
        with patch.object(settings, "ENVIRONMENT", "development"):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "skipped"
            assert res["reason"] == "disabled_by_default"
            assert db.query(User).count() == 0


def test_existing_account_preservation(memory_db):
    """Safeguard 4: Demo seeding never alters existing passwords or roles."""
    db, comp = memory_db
    custom_hash = "custom_scrypt_argon_hash_immutable_98765"
    existing_admin = User(
        company_id=comp.id,
        name="Existing Admin",
        username="admin_demo",
        email="existing@livogroup.com",
        password_hash=custom_hash,
        role="admin",
        active=True
    )
    db.add(existing_admin)
    db.commit()

    with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
        with patch.object(settings, "ENVIRONMENT", "development"):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "seeded"
            assert "admin_demo" not in res["seeded_users"]

    reloaded = db.query(User).filter(User.username == "admin_demo").first()
    assert reloaded.password_hash == custom_hash
    assert reloaded.email == "existing@livogroup.com"


def test_backup_service_creates_manifest_and_checksums():
    """Safeguard 5: create_complete_system_backup creates artifacts and valid manifest."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with patch.object(backup_service, "BACKUP_DIR", tmp_path), \
             patch.object(backup_service, "STATUS_FILE", tmp_path / "latest_status.json"):
            
            manifest = backup_service.create_complete_system_backup()
            assert manifest["overall_status"] == "success"
            assert "database_backup" in manifest
            assert "storage_backup" in manifest
            assert manifest["database_backup"]["status"] == "success"
            assert manifest["storage_backup"]["status"] == "success"

            # Verify manifest file exists on disk
            manifest_path = Path(manifest["manifest_file"])
            assert manifest_path.exists()

            with open(manifest_path, "r", encoding="utf-8") as mf:
                saved = json.load(mf)
                assert saved["overall_status"] == "success"

            # Verify checksum of database backup
            db_file = tmp_path / manifest["database_backup"]["file_name"]
            assert db_file.exists()
            with open(db_file, "rb") as f:
                calc_sha = hashlib.sha256(f.read()).hexdigest()
                assert calc_sha == manifest["database_backup"]["sha256"]

            # Verify checksum of storage archive
            storage_file = Path(manifest["storage_backup"]["file_path"])
            assert storage_file.exists()
            with open(storage_file, "rb") as f:
                calc_storage_sha = hashlib.sha256(f.read()).hexdigest()
                assert calc_storage_sha == manifest["storage_backup"]["sha256"]
