import os
import json
import logging
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger("app.backup")

BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"
STATUS_FILE = BACKUP_DIR / "latest_status.json"

def get_latest_backup_status() -> Dict[str, Any]:
    """Returns the latest database backup status from persistent JSON log."""
    if not STATUS_FILE.exists():
        return {
            "status": "none",
            "timestamp": None,
            "file_name": None,
            "file_size_bytes": 0,
            "storage_destination": None,
            "error_message": None
        }
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read backup status file: {e}")
        return {
            "status": "failed",
            "timestamp": None,
            "error_message": f"Status read error: {str(e)}"
        }

def save_backup_status(status_dict: Dict[str, Any]) -> None:
    """Saves backup status to persistent JSON log."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(status_dict, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write backup status file: {e}")

def upload_to_cloud_storage(file_path: Path, destination_key: str) -> Optional[str]:
    """
    Uploads a backup file to Backblaze B2 / Cloudflare R2 per ARCHITECTURE.md §9.
    Returns destination URL or storage descriptor string on success.
    """
    if not (settings.STORAGE_ENDPOINT_URL and settings.STORAGE_ACCESS_KEY and settings.STORAGE_SECRET_KEY):
        return None  # Cloud storage not configured; local backup retained

    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY,
        config=Config(signature_version="s3v4")
    )

    s3.upload_file(
        Filename=str(file_path),
        Bucket=settings.STORAGE_BUCKET_NAME,
        Key=destination_key
    )
    return f"s3://{settings.STORAGE_BUCKET_NAME}/{destination_key}"

def run_database_backup() -> Dict[str, Any]:
    """
    Executes a pg_dump (or SQLite fallback) database backup and uploads to cloud storage.
    Logs and returns failure details visibly per TASKS.md §1.6.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    db_url = settings.DATABASE_URL

    status_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress",
        "file_name": None,
        "file_size_bytes": 0,
        "storage_destination": "local",
        "error_message": None
    }

    try:
        if db_url.startswith("postgresql") or db_url.startswith("postgres"):
            backup_file = BACKUP_DIR / f"livo_backup_{now_str}.sql"
            # Extract Postgres connection parameters from DATABASE_URL
            cmd = f'pg_dump "{db_url}" -F p -f "{backup_file}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"pg_dump failed (exit code {res.returncode}): {res.stderr.strip()}")
        else:
            # SQLite fallback for local dev/testing
            sqlite_db_path = db_url.replace("sqlite:///", "")
            if not os.path.exists(sqlite_db_path):
                # Try relative to backend dir
                sqlite_db_path = str(Path(__file__).parent.parent.parent / "livo_dev.db")
            
            backup_file = BACKUP_DIR / f"livo_backup_{now_str}.db"
            shutil.copy2(sqlite_db_path, backup_file)

        file_size = backup_file.stat().st_size
        status_data["file_name"] = backup_file.name
        status_data["file_size_bytes"] = file_size

        # Cloud storage upload if configured
        cloud_url = None
        try:
            cloud_url = upload_to_cloud_storage(backup_file, f"backups/{backup_file.name}")
        except Exception as cloud_err:
            logger.warning(f"Cloud upload failed, retaining local copy: {cloud_err}")
            status_data["cloud_upload_warning"] = str(cloud_err)

        if cloud_url:
            status_data["storage_destination"] = f"Cloud Storage ({cloud_url})"
        else:
            status_data["storage_destination"] = f"Local Server Storage ({backup_file})"

        status_data["status"] = "success"
        save_backup_status(status_data)
        logger.info(f"Database backup completed successfully: {backup_file.name} ({file_size} bytes)")
        return status_data

    except Exception as e:
        error_msg = f"Backup job failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        status_data["status"] = "failed"
        status_data["error_message"] = error_msg
        save_backup_status(status_data)
        return status_data
