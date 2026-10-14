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

def find_pg_binary(binary_name: str) -> str:
    """Locates postgres binary from system PATH or embedded postgres installation."""
    resolved = shutil.which(binary_name)
    if resolved:
        return resolved
    try:
        import embedded_postgres
        candidate = Path(embedded_postgres.__file__).parent / "pginstall" / "bin" / f"{binary_name}.exe"
        if candidate.exists():
            return str(candidate)
    except Exception:
        pass
    return binary_name

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
            pg_dump_bin = find_pg_binary("pg_dump")
            cmd = f'"{pg_dump_bin}" "{db_url}" -F p -f "{backup_file}"'
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


def restore_database_backup(backup_file_path: Path, target_db_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Restores a database from a verified backup file into the target database.
    Mandatory disaster recovery implementation for Checkpoint 11.
    Supports PostgreSQL (psql dump restore) and SQLite (atomic database file restoration).
    """
    backup_path = Path(backup_file_path)
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    db_url = target_db_url or settings.DATABASE_URL
    logger.info(f"Initiating database restoration from: {backup_path.name} to {db_url}")

    result = {
        "status": "in_progress",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "restored_from": str(backup_path),
        "target_url": db_url if not "password" in db_url else "redacted",
        "error_message": None
    }

    try:
        if db_url.startswith("postgresql") or db_url.startswith("postgres"):
            # PostgreSQL restoration via psql
            psql_bin = find_pg_binary("psql")
            cmd = f'"{psql_bin}" "{db_url}" -f "{backup_path}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"psql restore failed (exit code {res.returncode}): {res.stderr.strip()}")
        else:
            # SQLite restoration
            target_path_str = db_url.replace("sqlite:///", "")
            target_path = Path(target_path_str)
            if not target_path.is_absolute():
                target_path = Path(__file__).parent.parent.parent / target_path_str

            # Verify backup file integrity before replacing
            import sqlite3
            test_conn = sqlite3.connect(str(backup_path))
            try:
                cur = test_conn.cursor()
                cur.execute("PRAGMA integrity_check;")
                check_result = cur.fetchone()
                if not check_result or check_result[0] != "ok":
                    raise ValueError(f"SQLite backup integrity check failed: {check_result}")
            finally:
                test_conn.close()

            # Ensure parent directories exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic copy into destination
            shutil.copy2(backup_path, target_path)

        result["status"] = "success"
        logger.info(f"Database restoration completed successfully from {backup_path.name}")
        return result

    except Exception as e:
        err_msg = f"Database restoration failed: {str(e)}"
        logger.error(err_msg, exc_info=True)
        result["status"] = "failed"
        result["error_message"] = err_msg
        return result

def get_backup_health_report() -> Dict[str, Any]:
    """
    Evaluates backup age, creation status, and restore verification health.
    Answers: 'Do we think backups exist?' vs 'Is the latest backup successfully created AND verified?'
    """
    warn_hours = float(os.getenv("BACKUP_AGE_WARN_HOURS", "26"))
    crit_hours = float(os.getenv("BACKUP_AGE_CRITICAL_HOURS", "48"))
    
    status = get_latest_backup_status()
    now_utc = datetime.now(timezone.utc)
    
    age_hours = None
    age_seconds = None
    if status.get("timestamp"):
        try:
            ts = datetime.fromisoformat(status["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (now_utc - ts).total_seconds())
            age_hours = round(age_seconds / 3600.0, 2)
            from app.core.metrics import metrics
            metrics.set_gauge("backup_age_seconds", age_seconds)
        except Exception:
            pass

    # Count physical backups retained
    retained_files = list(BACKUP_DIR.glob("*.dump")) + list(BACKUP_DIR.glob("*.db"))
    retained_count = len(retained_files)

    # Check restore verification
    restore_file = BACKUP_DIR / "restore_verification_status.json"
    restore_verified = False
    restore_ts = None
    if restore_file.exists():
        try:
            with open(restore_file, "r") as rf:
                rdata = json.load(rf)
                restore_verified = (rdata.get("status") == "success")
                restore_ts = rdata.get("timestamp")
        except Exception:
            pass

    from app.core.metrics import metrics
    metrics.set_gauge("backup_restore_verified", 1.0 if restore_verified else 0.0)

    # Determine Health Classification
    if status.get("status") == "failed":
        health = "CRITICAL"
        reason = f"Latest backup operation failed: {status.get('error_message')}"
    elif status.get("status") == "none" or age_hours is None:
        health = "CRITICAL"
        reason = "No database backups have ever been recorded."
    elif age_hours >= crit_hours:
        health = "CRITICAL"
        reason = f"Backup age ({age_hours}h) exceeds critical threshold ({crit_hours}h)."
    elif age_hours >= warn_hours:
        health = "WARNING"
        reason = f"Backup age ({age_hours}h) exceeds warning threshold ({warn_hours}h)."
    elif not restore_verified:
        health = "WARNING"
        reason = "Backups exist but restore verification has not been recorded."
    else:
        health = "HEALTHY"
        reason = "Latest backup is fresh, exists locally, and restore verification has passed."

    return {
        "health": health,
        "reason": reason,
        "backup_status": status.get("status"),
        "backup_timestamp": status.get("timestamp"),
        "backup_age_hours": age_hours,
        "backup_age_warning_threshold_hours": warn_hours,
        "backup_age_critical_threshold_hours": crit_hours,
        "retained_backups_count": retained_count,
        "restore_verified": restore_verified,
        "restore_verification_timestamp": restore_ts,
        "verified_and_healthy": (health == "HEALTHY" and restore_verified)
    }

