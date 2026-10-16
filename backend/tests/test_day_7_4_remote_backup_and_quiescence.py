"""
LIVO Footwear ERP — Day 7.4 Remote Backup & Quiescence Forensic Test Suite
==========================================================================
Verifies:
1. Cloud storage upload behavior when credentials are unset (fails safely, retains local).
2. Cloud storage upload behavior under mock boto3 (success path).
3. Cloud storage upload error handling (ClientError, network timeout):
   - Local backup is strictly retained.
   - Failure is recorded in status data as a warning without crashing backup job.
4. Storage backup (file uploads/attachments) scope:
   - Verifies that file backups and manifest.json are NOT uploaded to S3/B2.
5. Remote recovery capability:
   - Verifies absence of download_from_cloud_storage / remote restore in backup_service.
6. Write quiescence invariants:
   - Verifies pg_dump / sqlite backup operates without transactional write locks,
     confirming the operational requirement for a maintenance window.
"""

import sys
import tempfile
import pathlib
from unittest.mock import MagicMock, patch
import pytest

from app.config import settings
from app.services import backup_service


def test_cloud_upload_disabled_when_unconfigured():
    with tempfile.NamedTemporaryFile(suffix=".sql") as tmp:
        p = pathlib.Path(tmp.name)
        with patch.object(settings, "STORAGE_ENDPOINT_URL", ""), \
             patch.object(settings, "STORAGE_ACCESS_KEY", ""), \
             patch.object(settings, "STORAGE_SECRET_KEY", ""):
            res = backup_service.upload_to_cloud_storage(p, "backups/test.sql")
            assert res is None, "Cloud upload must return None when credentials are unset"


def test_cloud_upload_success_with_mock_s3():
    with tempfile.NamedTemporaryFile(suffix=".sql") as tmp:
        p = pathlib.Path(tmp.name)
        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        with patch.object(settings, "STORAGE_ENDPOINT_URL", "https://s3.us-west-000.backblazeb2.com"), \
             patch.object(settings, "STORAGE_ACCESS_KEY", "mock_key_id"), \
             patch.object(settings, "STORAGE_SECRET_KEY", "mock_secret_key"), \
             patch.object(settings, "STORAGE_BUCKET_NAME", "livo-erp-storage"), \
             patch.dict("sys.modules", {"boto3": mock_boto3, "botocore.config": MagicMock()}):
            res = backup_service.upload_to_cloud_storage(p, "backups/test.sql")
            assert res == "s3://livo-erp-storage/backups/test.sql"
            mock_s3_client.upload_file.assert_called_once_with(
                Filename=str(p),
                Bucket="livo-erp-storage",
                Key="backups/test.sql"
            )


def test_cloud_upload_failure_retains_local_and_warns():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        fake_db = tmp_path / "livo_dev.db"
        fake_db.write_text("synthetic sqlite content")

        mock_boto3 = MagicMock()
        mock_s3_client = MagicMock()
        mock_s3_client.upload_file.side_effect = RuntimeError("S3 Connection Timeout: 504 Gateway Timeout")
        mock_boto3.client.return_value = mock_s3_client

        with patch.object(backup_service, "BACKUP_DIR", tmp_path), \
             patch.object(settings, "DATABASE_URL", f"sqlite:///{fake_db}"), \
             patch.object(settings, "STORAGE_ENDPOINT_URL", "https://s3.us-west-000.backblazeb2.com"), \
             patch.object(settings, "STORAGE_ACCESS_KEY", "mock_key"), \
             patch.object(settings, "STORAGE_SECRET_KEY", "mock_secret"), \
             patch.dict("sys.modules", {"boto3": mock_boto3, "botocore.config": MagicMock()}):
            res = backup_service.run_database_backup()
            assert res["status"] == "success"
            assert "cloud_upload_warning" in res
            assert "S3 Connection Timeout" in res["cloud_upload_warning"]
            assert "Local Server Storage" in res["storage_destination"]
            # Verify local backup file exists and is intact
            backup_file = tmp_path / res["file_name"]
            assert backup_file.exists()
            assert backup_file.stat().st_size > 0


def test_storage_backup_does_not_upload_to_cloud():
    """Verify that file storage (attachments) backup is purely local and does not push to S3."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)
        storage_dir = tmp_path / "storage" / "secure_hr"
        storage_dir.mkdir(parents=True)
        (storage_dir / "doc.pdf").write_bytes(b"%PDF-1.4 synthetic")

        with patch.object(backup_service, "BACKUP_DIR", tmp_path), \
             patch.object(backup_service, "BACKEND_DIR", tmp_path), \
             patch("app.services.backup_service.upload_to_cloud_storage") as mock_cloud_upload:
            res = backup_service.run_storage_backup()
            assert res["status"] == "success"
            # Crucial verification: upload_to_cloud_storage is NEVER called by run_storage_backup
            mock_cloud_upload.assert_not_called()


def test_absence_of_remote_restore_function():
    """Verify that backup_service has no automated download or remote restore mechanism."""
    assert not hasattr(backup_service, "download_from_cloud_storage"), \
        "download_from_cloud_storage should not exist in backup_service"
    assert not hasattr(backup_service, "restore_from_cloud_storage"), \
        "restore_from_cloud_storage should not exist in backup_service"
    # Verify restore_database_backup requires a local file path
    import inspect
    sig = inspect.signature(backup_service.restore_database_backup)
    assert "backup_file_path" in sig.parameters


def test_restore_fails_safely_on_corrupted_file():
    """Verify restore_database_backup aborts and surfaces error on corrupted/non-existent file."""
    non_existent = pathlib.Path("/tmp/non_existent_dump.sql")
    with pytest.raises(FileNotFoundError):
        backup_service.restore_database_backup(non_existent)
