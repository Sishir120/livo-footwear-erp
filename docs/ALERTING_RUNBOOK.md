# LIVO FOOTWEAR ERP — PRODUCTION ALERTING RUNBOOK
**Checkpoint 14 — Incident Response, Alert Taxonomy & On-Call Playbook**  
*Target Environment: Production (Docker Compose / Ubuntu 22.04 LTS / Managed Postgres)*  
*Audited Date: 2026-10-01*

---

## 1. Alerting Philosophy & Operational Tiers

Alerts in LIVO Footwear ERP are structured around user impact and system invariants.
- **P1 — CRITICAL (Immediate Page):** Service outage, data corruption hazard, database unavailability, or failed backups. Requires 15-minute response.
- **P2 — WARNING (Next Business Hour / Slack Notification):** Degraded performance, elevated error rates, growing queues, or capacity warnings.

Every alert definition provides an actionable remediation recipe to avoid 3am guesswork.

---

## 2. Critical Alert Catalog (P1 — Immediate Action)

### Alert 1: `LivoApplicationUnavailable`
* **Severity:** **CRITICAL**
* **Condition:** Process liveness probe `GET /api/v1/health/live` fails or times out for 3 consecutive checks (over 15 seconds).
* **Why it matters:** Users cannot access the ERP; all factory operations and invoicing are halted.
* **First Diagnostic Step:** Inspect container status: `docker compose ps` and logs: `docker compose logs -n 50 backend`.
* **Likely Causes:** Python unhandled startup exception, out-of-memory killer (OOM), or crashed container process.
* **Remediation:** 
  1. Restart backend container: `docker compose restart backend`.
  2. Inspect `/opt/livo-erp/logs/livo_erp.log` for memory crash or fatal syntax error.
* **Escalation:** Lead Systems Architect / Principal Engineer.
* **Recovery Verification:** `curl -f http://localhost:8000/api/v1/health/live` returns HTTP 200 `{"status": "alive"}`.

---

### Alert 2: `LivoDatabaseReadinessFailure`
* **Severity:** **CRITICAL**
* **Condition:** Readiness probe `GET /api/v1/health/ready` returns HTTP 503 or fails for > 30 seconds.
* **Why it matters:** The backend process is running but cannot reach PostgreSQL. In-flight transactions fail.
* **First Diagnostic Step:** Execute `docker compose exec postgres pg_isready -U livo_admin`.
* **Likely Causes:** PostgreSQL container crashed, disk space exhausted, max connections reached, or network partition.
* **Remediation:**
  1. Check PostgreSQL disk space: `df -h /var/lib/docker`.
  2. Check PostgreSQL active connections: `docker compose exec postgres psql -U livo_admin -d livo_erp -c "SELECT count(*) FROM pg_stat_activity;"`.
  3. Restart database: `docker compose restart postgres`.
* **Escalation:** Database Administrator / On-Call SRE.
* **Recovery Verification:** `curl -f http://localhost:8000/api/v1/health/ready` returns HTTP 200 `{"status": "ready"}`.

---

### Alert 3: `LivoBackupOperationFailed`
* **Severity:** **CRITICAL**
* **Condition:** `GET /api/v1/backup/health` reports `"health": "CRITICAL"` or `backup_operations_total{status="failure"} > 0`.
* **Why it matters:** Nightly backup failed; system is operating without a fresh recovery point.
* **First Diagnostic Step:** Check backup log: `cat /opt/livo-erp/backups/latest_status.json`.
* **Likely Causes:** Insufficient disk space on backup volume, invalid cloud storage credentials (R2/B2), or locked DB tables.
* **Remediation:**
  1. Trigger immediate manual backup: `curl -X POST -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/v1/backup/run`.
  2. If cloud upload failed, verify S3 endpoint and credentials in `.env`.
* **Escalation:** DevOps / Infrastructure Engineer.
* **Recovery Verification:** Verify new `.dump` file generated and `GET /api/v1/backup/health` returns `"health": "HEALTHY"`.

---

### Alert 4: `LivoBackupRestoreVerificationFailed`
* **Severity:** **CRITICAL**
* **Condition:** `backup_restore_verified == 0` or restore verification drill script exits with non-zero code.
* **Why it matters:** Backup dumps exist but cannot be restored; database recovery is compromised.
* **First Diagnostic Step:** Inspect restore drill logs: `python3 scripts/verify_postgres_backup_restore.py`.
* **Likely Causes:** Corrupt SQL dump, schema version mismatch between dump and Alembic head.
* **Remediation:**
  1. Run drill manually on staging copy: `python3 scripts/test_restore.py`.
  2. If corrupted, generate a fresh full dump immediately.
* **Escalation:** Principal Database Engineer.
* **Recovery Verification:** `python3 scripts/verify_postgres_backup_restore.py` outputs `RESTORE INTEGRITY VERIFIED (PASS)`.

---

### Alert 5: `LivoAlembicMigrationMismatch`
* **Severity:** **CRITICAL**
* **Condition:** Active database revision does not match Alembic head (`alembic current != alembic heads`).
* **Why it matters:** Database schema is out of sync with application code; SQL queries will fail at runtime.
* **First Diagnostic Step:** Inspect migration status: `docker compose exec backend alembic current`.
* **Likely Causes:** Deployment omitted migration step, or migration crashed mid-transaction.
* **Remediation:**
  1. Run migrations: `docker compose exec backend alembic upgrade head`.
  2. Verify exact match with `alembic heads`.
* **Escalation:** Backend Engineering Lead.
* **Recovery Verification:** `docker compose exec backend alembic current` reports `(head)`.

---

## 3. Warning Alert Catalog (P2 — Proactive Warning)

### Alert 6: `LivoElevated5xxRate`
* **Severity:** **WARNING**
* **Condition:** 5xx HTTP responses exceed 1% of total requests over a 5-minute sliding window.
* **Why it matters:** Intermittent server errors impact user workflows and offline synchronization.
* **First Diagnostic Step:** Search logs for `INTERNAL_ERROR`: `docker compose logs backend | grep -i "INTERNAL_ERROR"`.
* **Likely Causes:** Unhandled edge cases in business logic, transient database deadlocks, or third-party storage timeouts.
* **Remediation:** Identify failing endpoint from request logs (`route` and `request_id`); reproduce and apply patch.
* **Escalation:** Backend Engineering Team.
* **Recovery Verification:** 5xx rate drops below 0.1%.

---

### Alert 7: `LivoDatabasePoolUtilizationHigh`
* **Severity:** **WARNING**
* **Condition:** `db_pool_utilization >= 0.85` for more than 2 minutes.
* **Why it matters:** Connection pool is near exhaustion; new requests will experience queuing latency or timeouts.
* **First Diagnostic Step:** Check active query durations: `SELECT pid, now() - query_start, query FROM pg_stat_activity WHERE state != 'idle';`.
* **Likely Causes:** Long-running analytics or export queries holding open connections without releasing them.
* **Remediation:**
  1. Terminate orphaned queries: `SELECT pg_terminate_backend(pid);`.
  2. Increase pool size in `.env`: `DB_POOL_SIZE=20` and restart backend.
* **Escalation:** SRE / Backend Team.
* **Recovery Verification:** `db_pool_utilization` drops below 0.50.

---

### Alert 8: `LivoBackupAgeApproachingLimit`
* **Severity:** **WARNING**
* **Condition:** `backup_age_hours >= 26` (warning threshold exceeded).
* **Why it matters:** Scheduled nightly backup did not execute or was delayed.
* **First Diagnostic Step:** Check cron daemon status on host: `systemctl status cron`.
* **Likely Causes:** Cron job skipped due to server reboot, or host timezone shift.
* **Remediation:** Execute `bash scripts/backup_nightly.sh`.
* **Escalation:** Infrastructure Team.
* **Recovery Verification:** `GET /api/v1/backup/health` returns `backup_age_hours < 26`.

---

### Alert 9: `LivoGrowingOfflineSyncConflicts`
* **Severity:** **WARNING**
* **Condition:** `offline_sync_mutations_total{state="CONFLICT"} > 5` within 1 hour.
* **Why it matters:** Multiple offline devices are submitting conflicting stock deductions or invoice updates.
* **First Diagnostic Step:** Check supervisor cockpit at `/ops/telemetry` and inspect `ProductionSyncLog` table.
* **Likely Causes:** Disconnected factory floor tablet reconnected with stale stock counts.
* **Remediation:** Open Supervisor Re-Sync screen in UI, review conflict diff, and approve authoritative balance.
* **Escalation:** Factory Operations Lead / Floor Supervisor.
* **Recovery Verification:** Conflict queue cleared in Operations Cockpit.
