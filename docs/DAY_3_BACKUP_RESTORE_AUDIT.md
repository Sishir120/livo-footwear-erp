# LIVO ERP — Day 3: Backup and Restore Implementation Audit

**Audit Date:** 2026-10-16  
**Auditor:** Antigravity Engineering (Independent Recovery & Resilience Audit)  
**Target System:** LIVO Footwear ERP (FastAPI + PostgreSQL / SQLAlchemy 2.0 / Alembic)  
**Target Milestone:** Controlled 1-Week Cloud Demonstration Readiness  

---

## 1. Executive Summary

This audit evaluates the database backup, disaster recovery, and operational durability mechanisms of LIVO Footwear ERP. The audit traces the lifecycle from the API trigger (`/api/v1/backup/run`) and background service (`app.services.backup_service`), through storage, integrity validation, and restoration execution (`restore_database_backup` and `scripts/staging_disaster_recovery_drill.py`).

### Key Findings Summary
1. **Relational Database Point-in-Time Consistency:** PostgreSQL backups utilize native `pg_dump` producing standard SQL dumps under MVCC repeatable read transaction snapshots, ensuring database relational consistency during concurrent reads and writes without table locking.
2. **File Storage & Relational Database Separation Gap:** Worker citizenship government identification documents (`storage/secure_hr/`), worker profile photographs (`static/uploads/workers/`), and product catalog imagery (`static/uploads/products/`) are stored as raw files on the host filesystem and are **completely omitted** from the database backup artifact. A database restore recovers database paths/metadata, but leaves the physical files missing unless persistent volume snapshots or object storage syncing are separately coupled.
3. **Health Report File Pattern Defect:** In `get_backup_health_report()`, retained backup discovery searches for `*.dump` and `*.db`, but `run_database_backup()` generates files named `livo_backup_<timestamp>.sql`. Consequently, on PostgreSQL environments, `retained_backups_count` incorrectly evaluates to `0` and health reporting misrepresents backup presence.
4. **Credential Redaction Flaw in Restore Reporting:** `restore_database_backup()` attempts to redact connection strings using `db_url if not "password" in db_url else "redacted"`. If a PostgreSQL connection string contains a password that does not contain the literal word `"password"`, the full DSN with plaintext credentials is recorded in the result structure.
5. **Non-Atomic Backup File Staging:** `pg_dump` outputs directly to the final target filename `livo_backup_<timestamp>.sql`. If the process is killed, runs out of disk space, or encounters a network partition midway, a corrupted, partial `.sql` file is retained in the backups directory without an integrity failure barrier.
6. **Integrity Validation Gap on Creation:** While SQLite restoration validates backups via `PRAGMA integrity_check`, PostgreSQL backup creation does not compute an artifact SHA-256 checksum or verify non-zero file byte thresholds before declaring `"status": "success"`.

---

## 2. Detailed Technical Audit Findings

### Finding BK-01: Uploaded Images & Secure HR Documents Excluded from Backup Artifact
- **Source File:** `backend/app/services/backup_service.py` (`run_database_backup`)
- **Severity:** **HIGH** (Operational Data Durability Gap)
- **Description:** `run_database_backup()` executes:
  ```python
  cmd = f'"{pg_dump_bin}" "{db_url}" -F p -f "{backup_file}"'
  ```
  This exports PostgreSQL database tables (metadata, ledger records, user credentials, document paths). However, worker citizenship proofs in `backend/storage/secure_hr/`, worker photos in `backend/static/uploads/workers/`, and product images in `backend/static/uploads/products/` reside on the filesystem.
- **Evidence:** `backup_service.py` contains no logic archiving `storage/` or `static/uploads/`. If a server volume crashes or a restore drill is executed into a clean container, all database foreign keys and file path columns (`citizenship_doc_path`, `photo_url`, `file_name`) point to missing files.
- **Impact:** Following a disaster recovery restore, worker verification and product gallery features will suffer 404 file errors for any historic uploads.
- **Recommended Action:**
  1. For the controlled demo, document this operational boundary in the recovery runbook: the database backup covers ledger and entity records; file storage requires volume-level snapshotting or S3 bucket synchronization.
  2. Implement an optional archive bundling helper or document a synchronized storage recovery procedure.

---

### Finding BK-02: Retained Backup Discovery Pattern Ignores `.sql` Files
- **Source File:** `backend/app/services/backup_service.py` (`get_backup_health_report`, lines 247–248)
- **Severity:** **MEDIUM** (Operational Observability Defect)
- **Description:** Line 247 searches the backup directory with:
  ```python
  retained_files = list(BACKUP_DIR.glob("*.dump")) + list(BACKUP_DIR.glob("*.db"))
  retained_count = len(retained_files)
  ```
  However, line 108 creates PostgreSQL backups with the `.sql` extension:
  ```python
  backup_file = BACKUP_DIR / f"livo_backup_{now_str}.sql"
  ```
- **Evidence:** Any PostgreSQL deployment using `run_database_backup()` saves `.sql` files. `retained_files` ignores all `.sql` files, consistently reporting `retained_backups_count: 0`.
- **Impact:** Monitoring dashboards, Prometheus metrics (`retained_backups_count`), and admin health screens report 0 backups retained even when valid backups exist locally.
- **Recommended Action:** Update the file glob to include `*.sql`:
  ```python
  retained_files = list(BACKUP_DIR.glob("*.sql")) + list(BACKUP_DIR.glob("*.dump")) + list(BACKUP_DIR.glob("*.db"))
  ```

---

### Finding BK-03: Ineffective Credential Masking in Restoration Audit Log
- **Source File:** `backend/app/services/backup_service.py` (`restore_database_backup`, line 173)
- **Severity:** **MEDIUM** (Security / Credential Exposure)
- **Description:** Line 173 records the destination target URL in the audit log dictionary:
  ```python
  "target_url": db_url if not "password" in db_url else "redacted",
  ```
  If the PostgreSQL password is e.g. `SecretPass2026!`, `"password"` is not a substring of `postgresql://livo_admin:SecretPass2026!@postgres:5432/livo_erp`. The check evaluates to `True`, leaking the full DSN with plaintext password into memory, logs, or status structures.
- **Evidence:** Python substring search `'password' in 'postgresql://user:Secret123@host:5432/db'` returns `False`.
- **Impact:** Database administrator passwords can be leaked in application logs or restore operation dictionaries.
- **Recommended Action:** Use standard URI masking regex (e.g., `re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)`), identical to `app/main.py:_sanitize_db_error`.

---

### Finding BK-04: Non-Atomic File Output on Interrupted Backup Creation
- **Source File:** `backend/app/services/backup_service.py` (`run_database_backup`, lines 108–114)
- **Severity:** **MEDIUM** (Resilience / Interruption Safety)
- **Description:** `pg_dump` writes directly to `backup_file = BACKUP_DIR / f"livo_backup_{now_str}.sql"`. If disk space is exhausted, the server process is killed (`SIGKILL`), or the PostgreSQL connection terminates prematurely, a truncated file remains at `backup_file`.
- **Evidence:** `pg_dump` writes incrementally to the target file. While `res.returncode != 0` catches standard exit errors, an unhandled SIGKILL or immediate power failure leaves a partial file on disk. Furthermore, if `res.returncode != 0` is caught in Python, the partial file is not unlinked.
- **Impact:** Subsequent automated restore or operator recovery may attempt to restore from a truncated dump file.
- **Recommended Action:**
  1. Write to a temporary file `f"{backup_file}.tmp"`.
  2. Perform an atomic rename (`os.replace`) to the final `.sql` path only upon returncode 0 and validation that file size > 0.
  3. Clean up the `.tmp` file in the exception handler.

---

### Finding BK-05: Absence of SHA-256 Artifact Checksum and Size Gate
- **Source File:** `backend/app/services/backup_service.py` (`run_database_backup`, lines 125–128)
- **Severity:** **LOW** (Data Integrity Verification)
- **Description:** `run_database_backup()` checks file size via `backup_file.stat().st_size`, but does not verify that size exceeds a minimum baseline (e.g. > 1024 bytes) or compute a cryptographic hash (SHA-256) for artifact integrity verification and audit logging.
- **Evidence:** An empty 0-byte dump (e.g. created by touch or empty stdout) would be accepted if `returncode == 0`.
- **Impact:** Operators cannot verify if a restored or transferred backup file suffered bit rot or tampering without external hashing tools.
- **Recommended Action:** Compute SHA-256 digest on backup completion, verify non-zero payload, and persist the checksum in `latest_status.json`.

---

### Finding BK-06: Unbounded Backup Directory Retention (No Pruning Policy)
- **Source File:** `backend/app/services/backup_service.py`
- **Severity:** **LOW** (Operational Stability / Disk Exhaustion)
- **Description:** `backup_service.py` does not include an automated retention or rotation policy. Backups accumulate indefinitely in `backend/backups/`.
- **Evidence:** There is no function pruning backups older than $N$ days or keeping only the last $M$ backups.
- **Impact:** Over long periods, production disks could experience out-of-disk conditions (ENOSPC), halting database write operations.
- **Recommended Action:** Implement a retention pruning function (e.g. retain last 14 daily backups, prune older local backups after successful cloud sync) or document an external host cron pruning policy in the runbook.

---

### Finding BK-07: Silent Ignored Errors During PostgreSQL `psql` Restore
- **Source File:** `backend/app/services/backup_service.py` (`restore_database_backup`, line 181)
- **Severity:** **HIGH** (Data Corruption / Silent Failure)
- **Description:** `restore_database_backup()` executed `psql "{db_url}" -f "{backup_path}"` without `-v ON_ERROR_STOP=1`. By default, `psql` prints SQL errors to stderr but continues execution and exits with return code `0`.
- **Evidence:** During negative failure testing with an invalid/truncated SQL artifact, `subprocess.run` returned exit code `0`, causing the restore to erroneously report `"status": "success"` on a corrupt database.
- **Impact:** A broken, truncated, or incompatible backup restored in an emergency would report success while leaving tables partially unpopulated or constraints broken.
- **Recommended Action:** Add `-v ON_ERROR_STOP=1` to the `psql` invocation so that any SQL syntax or execution error immediately terminates `psql` with a non-zero exit code (exit code 3), triggering proper error handling and status tracking.

---

## 3. Systematic Invariant and Operational Matrix

| Question / Requirement | Current Implementation Status | Verified Evidence & Behavior |
| :--- | :--- | :--- |
| **What data is included in a backup?** | All PostgreSQL database tables in `public` schema + Alembic revision history. | `pg_dump "{db_url}" -F p` dumps entire PostgreSQL database. |
| **Is PostgreSQL backed up consistently?** | **YES**. Consistent MVCC point-in-time snapshot. | `pg_dump` executes inside an implicit `REPEATABLE READ` snapshot; no table locks needed. |
| **Are uploaded files & secure documents included?** | **NO**. Filesystem files are separate. | `static/uploads/` and `storage/secure_hr/` are host files, omitted from SQL dump. |
| **Where are backups stored?** | Local directory `backend/backups/` + optional S3 cloud upload. | Saved locally; if `STORAGE_*` env vars set, uploaded to S3 bucket. |
| **Who can access, download, or delete backups?** | `POST /api/v1/backup/run` requires **Admin**. No download/delete API endpoints exist. | Guarded by `require_admin`. Local filesystem access requires host SSH/root. |
| **Do backups contain credentials or secrets?** | User password hashes (bcrypt) are included. DB connection password masked in logs. | Standard relational dump contains `users.password_hash`. |
| **Are paths protected against path traversal?** | **YES**. No public download endpoint; internal paths use `Path` resolution. | Verified in `gallery.py` (`_safe_resolve_image_path`) and `hr.py` (`_safe_resolve_path`). |
| **Is backup creation atomic & interruption-safe?** | **YES**. Staged via `.sql.tmp` with atomic rename. | Verified in remediated `backup_service.py`. |
| **Can retention cleanup delete the only recovery copy?** | **NO**. No automatic deletion exists (risk is disk exhaustion, not premature deletion). | No pruning code exists in `backup_service.py`. |
| **Does the system verify backup integrity after creation?** | **YES**. Computes SHA-256 digest and validates file size > 0. | Verified in remediated `backup_service.py`. |
| **Can backups occur during active transactions?** | **YES**. Native PostgreSQL MVCC allows concurrent reads/writes during dump. | Verified via `pg_dump` standard transactional behavior. |
| **What happens on disk full, DB down, or interruption?** | Subprocess returns non-zero code; caught and recorded as `"status": "failed"`. | Captured in `latest_status.json` and reported via `GET /backup/health`. |

---

## 4. Remediation Plan

Applied non-destructive fixes to `backend/app/services/backup_service.py`:
1. Included `*.sql` in `retained_files` glob (`BK-02`).
2. Implemented robust DSN password masking using regex (`BK-03`).
3. Wrote to temporary `.tmp` file and atomically renamed upon verified `pg_dump` exit code 0 (`BK-04`).
4. Validated that backup size > 0 and calculated SHA-256 digest (`BK-05`).
5. Added `-v ON_ERROR_STOP=1` to `psql` restore invocation to fail fast on SQL errors (`BK-07`).
