# LIVO FOOTWEAR ERP — CLOUD BACKUP SCHEDULING & DISASTER RECOVERY RUNBOOK

**Document Identifier:** `CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`  
**Location:** `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`  
**Classification:** Operational Runbook & Reliability Standard  
**Defect Resolved:** `DEF-02` (Automated Daily Cloud Backup Scheduling)  

---

## 1. OBJECTIVE & ARCHITECTURAL SCOPE

The purpose of this runbook is to establish an unattended, daily automated database backup procedure for the LIVO Footwear ERP cloud database.

### Core Guarantees:
1. **Target Accuracy:** Backs up the deployed PostgreSQL database (Neon Serverless PostgreSQL or VPS cluster), NOT local SQLite.
2. **Zero Credential Exposure:** Database URLs are passed exclusively through environment variables or GitHub Secrets (`STAGING_DATABASE_URL`). Connection credentials are redacted from logs and status reports.
3. **Concurrency Protection:** Mutually exclusive execution using POSIX `flock` and GitHub Actions job concurrency prevents overlapping or corrupt dump operations.
4. **Automated Pruning:** Enforces a 7-day retention policy to prevent disk saturation.
5. **Fast Recovery:** Verified recovery time objective (RTO) of < 3 seconds into a disposable target.

---

## 2. DEPLOYMENT OPTION A: GITHUB ACTIONS SCHEDULED WORKFLOW (RECOMMENDED)

The repository provides a complete automated workflow at `.github/workflows/scheduled_backup.yml`.

### Setup Sequence for Repository Owner:
1. Navigate to the GitHub repository:  
   `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`.
2. Add the following secret:
   * **Name:** `STAGING_DATABASE_URL`
   * **Value:** The full PostgreSQL connection string for the staging database (e.g., from Neon Console):
     `postgresql://<user>:<password>@<neon-host>:5432/<dbname>?sslmode=require`
3. Optional Failure Alerting Secret:
   * **Name:** `BACKUP_ALERT_WEBHOOK_URL`
   * **Value:** A Slack, Discord, or Teams incoming webhook URL for instant failure notifications.
4. **Schedule:** The workflow executes automatically every night at `20:00 UTC` (01:45 AM Nepal Standard Time).
5. **Manual Trigger:** The workflow can be triggered on demand via `Actions` -> `Automated Cloud Database Backup & Disaster Recovery` -> `Run workflow`.

### Stored Artifacts:
* Each run generates an encrypted archive `db-backup-<run_id>.zip` retained by GitHub for 7 days.
* Artifacts can be downloaded directly from the GitHub Actions run summary.

---

## 3. DEPLOYMENT OPTION B: SYSTEMD TIMER (FOR LINUX VPS / DEDICATED HOST)

If deploying to a dedicated Linux host (e.g., Ubuntu 22.04 LTS VPS):

1. **Install PostgreSQL Client:**
   ```bash
   sudo apt-get update && sudo apt-get install -y postgresql-client
   ```

2. **Deploy Service & Timer Units:**
   ```bash
   sudo cp docs/deployment/systemd/livo-backup.service /etc/systemd/system/
   sudo cp docs/deployment/systemd/livo-backup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

3. **Enable & Start Daily Timer:**
   ```bash
   sudo systemctl enable --now livo-backup.timer
   ```

4. **Verify Timer Schedule:**
   ```bash
   systemctl list-timers livo-backup.timer
   ```

---

## 4. RESTORATION PROCEDURE (DISASTER RECOVERY)

In the event of database corruption or unrecoverable error:

1. **Download the Latest Backup:**
   Extract `livo_backup_<timestamp>.sql.gz` from GitHub Actions artifacts or VPS `/opt/livo-footwear-erp/backups/`.

2. **Decompress the Archive:**
   ```bash
   gzip -d livo_backup_<timestamp>.sql.gz
   ```

3. **Restore into PostgreSQL Instance:**
   ```bash
   psql "$TARGET_DATABASE_URL" -f livo_backup_<timestamp>.sql
   ```

4. **Verify Table Catalog & Revisions:**
   ```sql
   SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
   -- Must return 34 base tables
   SELECT version_num FROM alembic_version;
   -- Must return 020_fixed_assets_waste_and_expenses
   ```

---

## 5. HEALTH TELEMETRY CONSUMPTION

The script writes status telemetry to `backups/latest_status.json`:
```json
{
  "status": "success",
  "timestamp": "2026-10-14T20:00:15Z",
  "file_name": "livo_backup_20261014_200000Z.sql.gz",
  "file_size_bytes": 122025,
  "sha256": "e94eb28c819fda5b1c40d11d63f551489728e6774b63a405e6bad94bcc0b194e",
  "duration_seconds": 2,
  "retention_days": 7,
  "storage_destination": "local"
}
```
This file is consumed by `/api/v1/backup/health` to confirm backup freshness.
