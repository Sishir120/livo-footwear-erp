# LIVO FOOTWEAR ERP — OPERATIONAL RUNBOOK
**Checkpoint 14 — Day-to-Day Operations, Triage & Maintenance Procedures**  
*Audited Date: 2026-10-01*

---

## 1. Routine System Health & Telemetry Verification

### 1.1 Quick CLI Health Check
Execute the following commands on the production host:
```bash
# 1. Process Liveness Check (Should return HTTP 200 {"status": "alive"})
curl -s http://localhost:8000/api/v1/health/live

# 2. Database Dependency Readiness Check (Should return HTTP 200 {"status": "ready"})
curl -s http://localhost:8000/api/v1/health/ready

# 3. Live Metrics Snapshot
curl -s http://localhost:8000/api/v1/metrics/json | jq .

# 4. Backup Health Status
curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/v1/backup/health | jq .
```

---

## 2. Investigating Slow Queries & Connection Pool Exhaustion

### 2.1 Symptoms
- Alert: `LivoDatabasePoolUtilizationHigh` or `db_slow_queries_total` incrementing rapidly.
- Users report sluggish page loads on Daily Report or Stock Report screens.

### 2.2 Triage Procedure
1. Inspect slow query warnings in access logs:
   ```bash
   tail -n 200 /opt/livo-erp/logs/livo_erp.log | grep -i "slow_database_query"
   ```
2. Check PostgreSQL active connections and long-running transactions:
   ```bash
   docker compose exec postgres psql -U livo_admin -d livo_erp -c "
     SELECT pid, now() - query_start AS duration, state, query 
     FROM pg_stat_activity 
     WHERE state != 'idle' 
     ORDER BY duration DESC 
     LIMIT 5;
   "
   ```
3. If an unindexed or runaway analytics query is locking connections:
   ```bash
   docker compose exec postgres psql -U livo_admin -d livo_erp -c "SELECT pg_terminate_backend(<PID>);"
   ```

---

## 3. Offline Synchronization Triage & Dead-Letter Resolution

### 3.1 Symptoms
- Factory floor tablets show unsynced changes that do not resolve automatically.
- Metric: `offline_sync_mutations_total{state="CONFLICT"}` is increasing.

### 3.2 Triage Procedure
1. Open the **Operations Cockpit** in the web UI (`/ops/telemetry`).
2. Review the `Broken Core Runs` and `Recent 422 Blocks` counters.
3. Query the `production_sync_logs` table for stuck transactions:
   ```bash
   docker compose exec postgres psql -U livo_admin -d livo_erp -c "
     SELECT id, idempotency_key, status, error_code, error_message, created_at 
     FROM production_sync_logs 
     WHERE status IN ('CONFLICT', 'REJECTED') 
     ORDER BY created_at DESC 
     LIMIT 10;
   "
   ```
4. If a physical stock discrepancy caused a conflict:
   - Perform a physical inventory count.
   - Use the **Stock Adjustment** screen in the UI with supervisor authorization to post an adjustment movement.
   - Re-queue the pending production batch from the tablet.

---

## 4. Disaster Recovery Drill Automation

A routine disaster recovery drill must be executed monthly to verify dump integrity and restoration speed without affecting production data.

### 4.1 Safety Constraints
- **NEVER** run drills directly against the production database container.
- Drills must target an isolated ephemeral database (`livo_drill_temp`).

### 4.2 Drill Execution
```bash
# 1. Trigger fresh backup dump
bash scripts/backup_nightly.sh

# 2. Run automated drill verification
python3 scripts/verify_postgres_backup_restore.py
```

### 4.3 Output Verification
The script verifies:
1. Dump generation duration and file integrity.
2. Complete schema restoration to temporary drill database.
3. Stock ledger balance reconciliation ($SUM(direction \times quantity)$ parity).
4. AR subledger and invoice numbering sequence continuity.
5. Emits auditable result: `RESTORE INTEGRITY VERIFIED (PASS)`.

---

## 5. Log Rotation & Maintenance

- **Rotation Policy:** Logs in `/opt/livo-erp/logs/livo_erp.log` rotate automatically at 10 MB with 5 backups retained (`livo_erp.log.1` through `.5`).
- **Disk Usage Audit:**
  ```bash
  du -sh /opt/livo-erp/logs
  du -sh /opt/livo-erp/backups
  ```
- **Diagnostics Package Export:**
  Administrators can download a full diagnostics package from `GET /api/v1/health/diagnostics/download`, bundling system information, active database self-checks, and recent sanitized logs.
