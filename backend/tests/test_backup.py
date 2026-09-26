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
