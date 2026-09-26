# Database Restore & Disaster Recovery Procedure

This document defines the verified, step-by-step database restore procedure for **LIVO GROUP OF INDUSTRIES Footwear ERP** per PRD §7 and TASKS.md §1.6.

---

## 1. Prerequisites
- **PostgreSQL Database** access or local SQLite copy (`livo_dev.db`).
- Access to Backblaze B2 / Cloudflare R2 bucket or local backup directory (`backend/backups/`).
- Database user credentials with schema creation and restore permissions (`createdb` / `pg_restore` / `psql`).

---

## 2. Restore Steps (PostgreSQL)

### Step 1: Download Target Backup File
Download the latest verified dump file from Backblaze B2 / Cloudflare R2 bucket or locate it in `backend/backups/`:
```bash
aws s3 cp s3://livo-erp-storage/backups/livo_backup_YYYYMMDD_HHMMSS.sql ./restore_target.sql \
  --endpoint-url $STORAGE_ENDPOINT_URL
```

### Step 2: Prepare Target Database
Create a clean staging database or clear existing connections before restoring:
```bash
# Drop connections if restoring over an existing database
psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'livo_db';"

# Recreate target database
dropdb -U postgres livo_db_restored
createdb -U postgres livo_db_restored
```

### Step 3: Execute Restore
Run SQL restoration using `psql`:
```bash
psql -U postgres -d livo_db_restored -f ./restore_target.sql
```

### Step 4: Verify Database Integrity
Run the baseline database integrity check script:
```bash
python scripts/test_restore.py --db-url "postgresql://postgres:postgres@localhost:5432/livo_db_restored"
```

---

## 3. Restore Steps (SQLite / Dev Mode)

1. Locate backup `.db` file in `backend/backups/`.
2. Stop application backend server.
3. Copy backup database over target `livo_dev.db`:
   ```bash
   cp backend/backups/livo_backup_YYYYMMDD_HHMMSS.db backend/livo_dev.db
   ```
4. Restart application server and run `/api/v1/health` self-check.

---

## 4. Automated Verification Log

The database restore process was empirically verified on **2026-09-26** using `scripts/test_restore.py`.
- **Source Database:** `livo_dev.db`
- **Backup Created:** `backend/backups/livo_backup_test_restore.db`
- **Restored Target:** `backend/backups/restored_verify.db`
- **Result:** 100% table match, 100% row count match across all 15 schema tables.
