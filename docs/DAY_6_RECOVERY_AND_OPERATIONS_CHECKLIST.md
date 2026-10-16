# LIVO Footwear ERP — Day 6 Recovery & Operations Checklist

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Enterprise Disaster Recovery & Data Integrity Baseline  
**Drill Proof File:** `backend/tests/test_day_4_file_and_database_recovery.py`

---

## 1. Recovery Architecture Overview

The LIVO Footwear ERP recovery framework combines dual-layer backup coverage:
1. **Relational Database Backup:** SQL dump (`pg_dump`) capturing complete multi-tenant relational state (companies, users, products, raw materials, stock transfers, batches, sales orders, invoices, and payments).
2. **File Storage Backup:** POSIX tarball archiving all persistent user uploads (`uploads/gallery`, `uploads/workers`, `uploads/citizenship`) coupled with SHA-256 cryptographic manifest generation.

---

## 2. Verification Drill Results Matrix

The recovery drill was executed against isolated PostgreSQL and file storage instances:

| Test Item | Verification Scenario | Tested Mechanism | Result | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **Artifact Creation** | Clean DB dump and tar archive created | `pg_dump` execution + tar archiving of active directories | **PASS** | Valid `.dump` and `.tar.gz` created |
| **Manifest Integrity** | SHA-256 checksums generated for every file | Manifest file `manifest.sha256` created alongside archive | **PASS** | Hashes recorded for all synthetic files |
| **Disaster Restoration** | Full restore into empty disposable target DB | `pg_restore` / SQL execution against new PostgreSQL instance | **PASS** | All relational tables and foreign keys re-created |
| **File Byte Parity** | Restored files match original sources byte-for-byte | Re-computation of SHA-256 hashes on restored filesystem | **PASS** | 100% hash equivalence across all files |
| **Missing File Detection** | Archive missing a listed file triggers abort | Manifest validator checks presence of every listed path | **PASS** | Explicit error raised; partial restore blocked |
| **Corrupted File Detection**| Checksum mismatch aborts restore | Tampered file bytes detected during manifest validation | **PASS** | Explicit checksum failure raised |
| **Tar Slip Prevention** | Malicious directory traversal filenames rejected | Tar extractor rejects paths with `../` or leading slashes | **PASS** | Path traversal attempt safely blocked |

---

## 3. Operator Recovery Runbook

### Step 1: Execute Backup
```bash
# In backend directory
python -m app.scripts.backup_full --output-dir /var/backups/livo
```
Expected output:
- `db_backup_YYYYMMDD_HHMMSS.sql.gz`
- `files_backup_YYYYMMDD_HHMMSS.tar.gz`
- `manifest_YYYYMMDD_HHMMSS.sha256`

### Step 2: Validate Manifest & Checksums
```bash
sha256sum -c manifest_YYYYMMDD_HHMMSS.sha256
```

### Step 3: Execute Restoration into Clean Instance
```bash
# Restore PostgreSQL database
psql -h <host> -U <user> -d <database> < db_backup_YYYYMMDD_HHMMSS.sql

# Restore persistent storage
tar -xzf files_backup_YYYYMMDD_HHMMSS.tar.gz -C /app/
```

### Step 4: Run Application Health Check
```bash
curl -f http://<host>:8000/api/v1/health/ready
```

---

## 4. Offsite Backup & Cloud Demo Limitation Notice

> [!WARNING]
> **Host-Local vs. Offsite Backup Storage**  
> Backups stored strictly on the local host or local Docker volume protect against application bugs and human error, but **do not protect against host loss, volume corruption, or cloud provider region failure**.
>
> **Prerequisite for Production / Accepted Limitation for Demo:**  
> 1. For the controlled 1-week cloud evaluation demonstration using synthetic data, local volume snapshots are **accepted as bounded risk**.  
> 2. For any live client production deployment, automated offsite synchronization (e.g., streaming backups to an S3/Backblaze B2 bucket with object locking) is a **mandatory prerequisite**.
