"""
LIVO Footwear ERP — Day 7.2 Provisioning & Backup Consistency Test Suite
========================================================================
Verifies:
1. provision_demo_personas refuses production ENVIRONMENT.
2. provision_demo_personas refuses database URLs containing 'prod', 'live', or 'client_master'.
3. provision_demo_personas refuses unconfirmed or mismatched database targets.
4. provision_demo_personas succeeds when explicit database identity is confirmed.
5. Repeated provisioning is repeat-safe and preserves existing passwords/roles.
6. Backup consistency failure modes (cleanup of partial files on error).
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.session import Base
from app.models.company import Company
from app.models.user import User
from scripts.provision_demo_personas import (
    provision_demo_personas,
    is_production_database,
    extract_db_name
)
from app.services import backup_service


@pytest.fixture
def isolated_provision_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        comp = Company(name="LIVO Staging Factory", code="LIVO")
        db.add(comp)
        db.commit()
        db.refresh(comp)
        yield db, comp, engine, Session


def test_provision_refuses_production_environment(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch.object(settings, "ENVIRONMENT", "production"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        res = provision_demo_personas(confirm_db="livo_dev.db")
        assert res["status"] == "rejected"
        assert res["reason"] == "production_refusal"


def test_provision_refuses_production_database_name(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch.object(settings, "DATABASE_URL", "postgresql://user:secret@internal-pg:5432/livo_production_primary"), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        assert is_production_database(settings.DATABASE_URL) is True
        res = provision_demo_personas(confirm_db="livo_production_primary")
        assert res["status"] == "rejected"
        assert res["reason"] == "production_refusal"


def test_provision_refuses_production_database_host(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch.object(settings, "DATABASE_URL", "postgresql://user:secret@prod-rds.internal:5432/livo_eval"), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        assert is_production_database(settings.DATABASE_URL) is True
        res = provision_demo_personas(confirm_db="livo_eval")
        assert res["status"] == "rejected"
        assert res["reason"] == "production_refusal"


def test_provision_refuses_missing_or_incorrect_db_confirmation(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch.object(settings, "DATABASE_URL", "sqlite:///./livo_disposable.db"), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        # Missing confirmation flag (empty or None)
        res_empty = provision_demo_personas(confirm_db="")
        assert res_empty["status"] == "rejected"
        assert res_empty["reason"] == "database_confirmation_mismatch"

        # Incorrect confirmation name
        res_wrong = provision_demo_personas(confirm_db="wrong_name.db")
        assert res_wrong["status"] == "rejected"
        assert res_wrong["reason"] == "database_confirmation_mismatch"


def test_provision_refuses_wrong_host_with_matching_db_name(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    # Target is remote postgres server with matching DB name 'livo_staging'
    remote_url = "postgresql://user:secret@staging-server-01.internal:5432/livo_staging"
    with patch.object(settings, "DATABASE_URL", remote_url), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        # 1. Matching DB name alone is NOT sufficient for non-local host (unconfirmed host fails closed)
        res_unconfirmed = provision_demo_personas(confirm_db="livo_staging")
        assert res_unconfirmed["status"] == "rejected"
        assert res_unconfirmed["reason"] == "unconfirmed_remote_host"

        # 2. Confirmed host mismatch (operator thought host was staging-server-02)
        res_mismatch = provision_demo_personas(confirm_db="livo_staging", confirm_host="staging-server-02.internal")
        assert res_mismatch["status"] == "rejected"
        assert res_mismatch["reason"] == "host_confirmation_mismatch"

        # 3. Matching DB and matching host succeeds
        res_match = provision_demo_personas(confirm_db="livo_staging", confirm_host="staging-server-01.internal")
        assert res_match["status"] == "success"
        assert res_match["host"] == "staging-server-01.internal"


def test_provision_refuses_production_environment_aliases_and_url_markers(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    test_cases = [
        ({"ENVIRONMENT": "live"}, "sqlite:///./livo_dev.db", "livo_dev.db"),
        ({"ENVIRONMENT": "client_prod"}, "sqlite:///./livo_dev.db", "livo_dev.db"),
        ({"ENVIRONMENT": "staging"}, "postgresql://user:pass@127.0.0.1:5432/livo_master", "livo_master"),
        ({"ENVIRONMENT": "staging"}, "postgresql://user:pass@127.0.0.1:5432/livo_client_live", "livo_client_live"),
    ]
    for env_patch, db_url, db_name in test_cases:
        with patch.multiple(settings, **env_patch), \
             patch.object(settings, "DATABASE_URL", db_url), \
             patch("scripts.provision_demo_personas.SessionLocal", Session):
            res = provision_demo_personas(confirm_db=db_name)
            assert res["status"] == "rejected"
            assert res["reason"] == "production_refusal"


def test_provision_refuses_missing_or_malformed_db_config(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch("scripts.provision_demo_personas.SessionLocal", Session):
        # Empty DATABASE_URL
        with patch.object(settings, "DATABASE_URL", ""):
            res = provision_demo_personas(confirm_db="any")
            assert res["status"] == "rejected"
            assert res["reason"] == "malformed_database_configuration"

        # Malformed URL without database name
        with patch.object(settings, "DATABASE_URL", "postgresql://user:pass@localhost:5432/"):
            res = provision_demo_personas(confirm_db="any")
            assert res["status"] == "rejected"
            assert res["reason"] == "malformed_database_configuration"


def test_provision_preserves_existing_accounts_and_credentials(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    # Pre-create an admin_demo user with a CUSTOM password and role
    custom_pass_hash = "custom_hash_123456"
    pre_user = User(
        company_id=comp.id,
        name="Custom Existing Admin",
        username="admin_demo",
        email="custom@livogroup.com",
        password_hash=custom_pass_hash,
        role="custom_super_role",
        active=True
    )
    db.add(pre_user)
    db.commit()

    with patch.object(settings, "DATABASE_URL", "sqlite:///./livo_dev.db"), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session):
        res = provision_demo_personas(confirm_db="livo_dev.db")
        assert res["status"] == "success"
        assert "admin_demo" in res["preserved_users"]
        assert "admin_demo" not in res["created_users"]

        # Verify DB: password hash and role were NEVER overwritten
        refreshed = db.query(User).filter(User.username == "admin_demo").first()
        assert refreshed.password_hash == custom_pass_hash
        assert refreshed.role == "custom_super_role"
        assert refreshed.name == "Custom Existing Admin"


def test_provision_transaction_rollback_on_partial_failure(isolated_provision_db):
    db, comp, engine, Session = isolated_provision_db
    with patch.object(settings, "DATABASE_URL", "sqlite:///./livo_dev.db"), \
         patch.object(settings, "ENVIRONMENT", "staging"), \
         patch("scripts.provision_demo_personas.SessionLocal", Session), \
         patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("Simulated database constraint crash")):
        res = provision_demo_personas(confirm_db="livo_dev.db")
        assert res["status"] == "failed"
        assert res["reason"] == "db_exception"


def test_startup_does_not_seed_in_staging_without_test_env():
    # Verify that in STAGING mode, seed_demo_users_if_enabled refuses even if ENABLE_DEMO_SEEDING is true
    from app.core.demo_seeding import seed_demo_users_if_enabled
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        comp = Company(name="LIVO Staging Factory", code="LIVO")
        db.add(comp)
        db.commit()

        # In STAGING mode, startup seeding is strictly rejected
        with patch.object(settings, "ENVIRONMENT", "staging"), \
             patch.object(settings, "ENABLE_DEMO_SEEDING", True):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "rejected"
            assert res["reason"] == "ambiguous_environment_refusal"

        # In STAGING mode with default ENABLE_DEMO_SEEDING=false, skipped
        with patch.object(settings, "ENVIRONMENT", "staging"), \
             patch.object(settings, "ENABLE_DEMO_SEEDING", False):
            res = seed_demo_users_if_enabled(db, comp)
            assert res["status"] == "skipped"


def test_backup_cleans_up_temporary_files_on_error():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        with patch.object(backup_service, "BACKUP_DIR", tmp_path), \
             patch("tarfile.open", side_effect=IOError("Disk quota exceeded")):
            res = backup_service.run_storage_backup()
            assert res["status"] == "failed"
            # Assert no dangling *.tmp files
            assert len(list(tmp_path.glob("*.tmp"))) == 0
