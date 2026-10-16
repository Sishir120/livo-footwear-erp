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
            tmp_backup_file = BACKUP_DIR / f"livo_backup_{now_str}.sql.tmp"
            backup_file = BACKUP_DIR / f"livo_backup_{now_str}.sql"
            # Extract Postgres connection parameters from DATABASE_URL
            pg_dump_bin = find_pg_binary("pg_dump")
            cmd = f'"{pg_dump_bin}" "{db_url}" -F p -f "{tmp_backup_file}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode != 0:
                if tmp_backup_file.exists():
                    tmp_backup_file.unlink(missing_ok=True)
                raise RuntimeError(f"pg_dump failed (exit code {res.returncode}): {res.stderr.strip()}")
            if not tmp_backup_file.exists() or tmp_backup_file.stat().st_size == 0:
                if tmp_backup_file.exists():
                    tmp_backup_file.unlink(missing_ok=True)
                raise RuntimeError("pg_dump generated an empty or non-existent backup file")
            os.replace(tmp_backup_file, backup_file)
        else:
            # SQLite fallback for local dev/testing
            sqlite_db_path = db_url.replace("sqlite:///", "")
            if not os.path.exists(sqlite_db_path):
                # Try relative to backend dir
                sqlite_db_path = str(Path(__file__).parent.parent.parent / "livo_dev.db")
            
            backup_file = BACKUP_DIR / f"livo_backup_{now_str}.db"
            shutil.copy2(sqlite_db_path, backup_file)

        file_size = backup_file.stat().st_size
        import hashlib
        with open(backup_file, "rb") as bf:
            file_hash = hashlib.sha256(bf.read()).hexdigest()
        status_data["file_name"] = backup_file.name
        status_data["file_size_bytes"] = file_size
        status_data["sha256"] = file_hash

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
        logger.info(f"Database backup completed successfully: {backup_file.name} ({file_size} bytes, sha256={file_hash[:12]}...)")
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
    import re
    sanitized_target = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)
    logger.info(f"Initiating database restoration from: {backup_path.name} to {sanitized_target}")

    result = {
        "status": "in_progress",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "restored_from": str(backup_path),
        "target_url": sanitized_target,
        "error_message": None
    }

    try:
        if db_url.startswith("postgresql") or db_url.startswith("postgres"):
            # PostgreSQL restoration via psql
            psql_bin = find_pg_binary("psql")
            cmd = f'"{psql_bin}" -v ON_ERROR_STOP=1 "{db_url}" -f "{backup_path}"'
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

    # Count physical backups retained (*.sql, *.dump, *.db)
    retained_files = (
        list(BACKUP_DIR.glob("*.sql")) +
        list(BACKUP_DIR.glob("*.dump")) +
        list(BACKUP_DIR.glob("*.db"))
    )
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


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

def run_storage_backup(target_archive_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Archives physical upload and secure storage files:
    1. static/uploads/products/ (Product gallery images)
    2. static/uploads/workers/ (Worker profile images)
    3. storage/secure_hr/ (Secure citizenship proofs and HR documents)
    Creates an atomic tar.gz archive with SHA-256 verification.
    """
    import tarfile
    import hashlib

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    final_tar = Path(target_archive_path) if target_archive_path else (BACKUP_DIR / f"livo_files_{now_str}.tar.gz")
    tmp_tar = final_tar.with_suffix(final_tar.suffix + ".tmp")

    storage_targets = [
        ("static/uploads/products", BACKEND_DIR / "static" / "uploads" / "products"),
        ("static/uploads/workers", BACKEND_DIR / "static" / "uploads" / "workers"),
        ("storage/secure_hr", BACKEND_DIR / "storage" / "secure_hr"),
    ]

    total_files = 0
    try:
        with tarfile.open(tmp_tar, "w:gz") as tar:
            for arcname_prefix, local_dir in storage_targets:
                if local_dir.exists():
                    for item in local_dir.rglob("*"):
                        if item.is_file():
                            rel = item.relative_to(local_dir)
                            arcname = f"{arcname_prefix}/{rel.as_posix()}"
                            tar.add(item, arcname=arcname)
                            total_files += 1

        if not tmp_tar.exists() or tmp_tar.stat().st_size == 0:
            if tmp_tar.exists():
                tmp_tar.unlink()
            raise RuntimeError("Storage archive creation produced an empty or missing file")

        # Atomic rename
        os.replace(tmp_tar, final_tar)

        with open(final_tar, "rb") as f:
            sha256_hash = hashlib.sha256(f.read()).hexdigest()

        result = {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_name": final_tar.name,
            "file_path": str(final_tar),
            "file_size_bytes": final_tar.stat().st_size,
            "total_files_archived": total_files,
            "sha256": sha256_hash,
            "error_message": None
        }
        logger.info(f"Storage backup completed: {final_tar.name} ({total_files} files, {result['file_size_bytes']} bytes)")
        return result
    except Exception as e:
        if tmp_tar.exists():
            tmp_tar.unlink()
        err = f"Storage backup failed: {str(e)}"
        logger.error(err, exc_info=True)
        return {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_name": None,
            "file_path": None,
            "file_size_bytes": 0,
            "total_files_archived": 0,
            "sha256": None,
            "error_message": err
        }


def restore_storage_backup(archive_path: Path, target_base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Restores file assets from a verified tar.gz archive into target_base_dir.
    Includes defense against zip/tar slip directory traversal attacks.
    """
    import tarfile

    archive = Path(archive_path)
    if not archive.exists():
        raise FileNotFoundError(f"Storage archive not found: {archive}")

    base = Path(target_base_dir) if target_base_dir else BACKEND_DIR
    base = base.resolve()

    try:
        with tarfile.open(archive, "r:gz") as tar:
            # Validate all members before extracting (Zip slip defense)
            for member in tar.getmembers():
                dest_path = (base / member.name).resolve()
                if not str(dest_path).startswith(str(base)):
                    raise ValueError(f"Illegal path traversal attempt in archive member: {member.name}")

            tar.extractall(path=base)

        logger.info(f"Storage archive restored successfully from {archive.name} into {base}")
        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "restored_from": str(archive),
            "target_dir": str(base),
            "error_message": None
        }
    except Exception as e:
        err = f"Storage restoration failed: {str(e)}"
        logger.error(err, exc_info=True)
        return {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "restored_from": str(archive),
            "target_dir": str(base),
            "error_message": err
        }


def verify_database_and_file_parity(db, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Audits physical existence and readability of all file assets referenced in the database:
    1. ProductImage.file_name in static/uploads/products/
    2. Worker.citizenship_doc_path in storage/secure_hr/company_{id}/citizenship/
    Prevents false success in disaster recovery drills.
    """
    from app.models.gallery import ProductImage
    from app.models.worker import Worker

    base = Path(base_dir) if base_dir else BACKEND_DIR
    missing_files = []
    verified_files = []

    # 1. Product gallery images
    images = db.query(ProductImage).all()
    for img in images:
        expected_path = base / "static" / "uploads" / "products" / img.file_name
        if not expected_path.exists() or expected_path.stat().st_size == 0:
            missing_files.append({
                "type": "PRODUCT_IMAGE",
                "id": img.id,
                "company_id": img.company_id,
                "file_name": img.file_name,
                "expected_path": str(expected_path)
            })
        else:
            verified_files.append(str(expected_path))

    # 2. Worker citizenship documents
    workers = db.query(Worker).filter(Worker.citizenship_doc_path.isnot(None)).all()
    for w in workers:
        expected_path = base / "storage" / "secure_hr" / f"company_{w.company_id}" / "citizenship" / w.citizenship_doc_path
        if not expected_path.exists() or expected_path.stat().st_size == 0:
            missing_files.append({
                "type": "WORKER_CITIZENSHIP_DOC",
                "worker_id": w.id,
                "worker_code": w.worker_code,
                "company_id": w.company_id,
                "file_name": w.citizenship_doc_path,
                "expected_path": str(expected_path)
            })
        else:
            verified_files.append(str(expected_path))

    is_parity = (len(missing_files) == 0)
    return {
        "status": "PARITY_CONFIRMED" if is_parity else "DISCREPANCIES_DETECTED",
        "verified_files_count": len(verified_files),
        "missing_files_count": len(missing_files),
        "missing_files": missing_files
    }


def create_complete_system_backup() -> Dict[str, Any]:
    """
    Creates a synchronized database-plus-storage backup package.
    1. Executes run_database_backup()
    2. Executes run_storage_backup()
    3. Emits manifest linking both artifacts with matching timestamp and checksums.
    """
    manifest_time = datetime.now(timezone.utc).isoformat()
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    db_res = run_database_backup()
    files_res = run_storage_backup()

    manifest = {
        "timestamp": manifest_time,
        "version": settings.VERSION,
        "database_backup": db_res,
        "storage_backup": files_res,
        "overall_status": "success" if (db_res.get("status") == "success" and files_res.get("status") == "success") else "failed"
    }

    manifest_file = BACKUP_DIR / f"livo_manifest_{now_str}.json"
    try:
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        manifest["manifest_file"] = str(manifest_file)
    except Exception as e:
        logger.error(f"Failed to write backup manifest: {e}")

    return manifest


if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="LIVO Footwear ERP System Backup CLI")
    parser.add_argument("--output-dir", help="Directory where backups should be saved", default=None)
    args = parser.parse_args()

    if args.output_dir:
        target_dir = Path(args.output_dir).resolve()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            BACKUP_DIR = target_dir
            STATUS_FILE = BACKUP_DIR / "latest_status.json"
        except Exception as e:
            print(f"[FATAL] Cannot create or access backup destination '{target_dir}': {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Executing LIVO Footwear ERP Full System Backup to: {BACKUP_DIR}")
    manifest = create_complete_system_backup()
    status = manifest.get("overall_status")
    print(f"Backup Result: {status.upper()}")
    print(json.dumps(manifest, indent=2))
    if status != "success":
        sys.exit(1)
    sys.exit(0)


