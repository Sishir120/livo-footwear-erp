# LIVO FOOTWEAR ERP — DISASTER RECOVERY RUNBOOK
**Checkpoint 11 — Database Integrity, Migrations, Backups & Disaster Recovery**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Purpose & Incident Escalation

This runbook provides step-by-step procedures for operators and database reliability engineers to recover LIVO Footwear ERP during critical production outages, data corruption events, failed deployments, or cloud provider failures.

---

## 2. Emergency Disaster Scenarios & Playbooks

### Scenario A: Catastrophic Database Corruption / Storage Failure
* **Detection:** Application `/api/v1/health` returns `status: "degraded"`, queries fail with media/I/O errors, or database process terminates abruptly.
* **Impact:** Application cannot process sales orders, invoices, or inventory movements.
* **Recovery Procedure:**
  1. **Halt Application Ingress:** Put frontend in maintenance mode or stop web workers:
     ```bash
     # Stop application workers to avoid partial transactions
     docker compose stop backend
     ```
  2. **Retrieve Latest Verified Backup Artifact:**
     ```bash
     # List local or cloud backup snapshots
     ls -la backend/backups/
     ```
  3. **Restore Database from Snapshot:**
     * For PostgreSQL:
       ```bash
       psql "$DATABASE_URL" -f "backend/backups/livo_backup_LATEST.sql"
       ```
     * For SQLite:
       ```bash
       python -c "from app.services.backup_service import restore_database_backup; from pathlib import Path; restore_database_backup(Path('backend/backups/livo_backup_LATEST.db'))"
       ```
  4. **Run Invariant Reconciliation Drill:**
     ```bash
     python backend/scripts/verify_backup_restore.py
     ```
  5. **Restart Backend & Validate Health:**
     ```bash
     docker compose start backend
     curl -s http://localhost:8000/api/v1/health | jq .
     ```
* **Expected RTO:** < 15 minutes.
* **Potential Data Loss (RPO):** Transactions committed since last backup snapshot (or 0 minutes if Neon PITR is utilized).

---

### Scenario B: Failed Alembic Migration during Deployment
* **Detection:** CI/CD deployment fails during `alembic upgrade head`, or API startup crashes with `PendingRollbackError` or `OperationalError`.
* **Impact:** New application code cannot interact with mismatched schema.
* **Recovery Procedure:**
  1. Inspect Alembic current revision vs heads:
     ```bash
     python -m alembic current
     python -m alembic heads
     ```
  2. **Transaction Rollback Check:**
     * On PostgreSQL, DDL migrations execute inside transactions; if a statement fails, Alembic automatically rolls back the transaction. The database remains at the previous revision.
  3. **Revert Application Deployment:**
     Roll back container deployment to previous stable tag.
  4. **Fix Migration Script Locally:**
     Reproduce in disposable database:
     ```bash
     python -m pytest backend/tests/test_checkpoint_11_database.py
     ```

---

### Scenario C: Accidental Table Deletion or Erroneous Data Update
* **Detection:** Unintended bulk `DELETE` or incorrect script updates operational rows.
* **Impact:** Historical ledger or document continuity compromised.
* **Recovery Procedure using Neon Point-in-Time Recovery (PITR):**
  1. Determine exact UTC timestamp of erroneous operation:
     ```text
     Target Recovery Time: 2026-10-01T14:10:00Z
     ```
  2. In Neon Console (or via CLI):
     * Create a new branch `recovery-branch-20261001` from the parent branch at the timestamp.
  3. Connect to the recovery branch and verify record counts:
     ```bash
     psql "$RESTORED_BRANCH_DATABASE_URL" -c "SELECT COUNT(*) FROM invoices;"
     ```
  4. Update application environment variable `DATABASE_URL` to point to the restored branch.
  5. Restart application services and verify `/api/v1/health`.

---

### Scenario D: Database Connection Timeout / Connection Pool Exhaustion
* **Detection:** Application logs report `TimeoutError: QueuePool limit of size 20 overflow 30 reached`.
* **Impact:** HTTP 500 errors returned to users.
* **Recovery Procedure:**
  1. Check active database connection count:
     ```sql
     SELECT count(*), state FROM pg_stat_activity GROUP BY state;
     ```
  2. Terminate idle-in-transaction connections older than 5 minutes:
     ```sql
     SELECT pg_terminate_backend(pid) 
     FROM pg_stat_activity 
     WHERE state = 'idle in transaction' 
       AND state_change < now() - INTERVAL '5 minutes';
     ```
  3. Check pool recycle settings in `backend/app/db/session.py` (`pool_recycle=1800`, `pool_pre_ping=True`).

---

### Scenario E: Database Credentials Compromised / Secret Rotation
* **Detection:** Credentials leaked in logs or security incident alert.
* **Impact:** Security risk.
* **Recovery Procedure:**
  1. Generate new password in database cluster (PostgreSQL `ALTER USER livo_admin WITH PASSWORD 'new_secure_pwd';`).
  2. Update `DATABASE_URL` in production secrets manager / hosting environment (e.g. Render / AWS Secrets Manager).
  3. Perform rolling restart of backend containers.
  4. Verify `/api/v1/health` reports `"database": "healthy"`.

---

## 3. Post-Incident Verification & Sign-Off Checklist

Before declaring an incident resolved and releasing traffic to users:
- [ ] `/api/v1/health` returns `status: "healthy"` and `database: "healthy"`.
- [ ] Automated drill script passes 100%:
  ```bash
  python backend/scripts/verify_backup_restore.py
  ```
- [ ] Physical stock ledger reconciles: `Sum(quantity * direction) == on_hand`.
- [ ] Accounts receivable ledger reconciles: `Sum(amount_paisa * direction) == client_balance`.
- [ ] Invoice sequence continuity verified: no duplicate or missing sequence numbers.
- [ ] Incident post-mortem logged in `docs/reports/`.
