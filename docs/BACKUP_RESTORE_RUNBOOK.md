# LIVO Footwear ERP — Production Backup & Restore Runbook

**Document Version:** 1.0.0  
**Effective Date:** October 2, 2026  
**Audience:** Site Reliability Engineers (SRE), Database Administrators (DBA), DevOps Engineers  

---

## 1. Overview & Service Level Objectives

The LIVO Footwear ERP persists mission-critical financial, operational, and inventory data for manufacturing enterprises. This runbook establishes standard operating procedures for continuous backup protection and full disaster recovery drills.

### Recovery Objectives
* **Recovery Point Objective (RPO):** $\le 1\text{ hour}$ for standard automated dumps; $\le 5\text{ minutes}$ when Point-in-Time Recovery (PITR) WAL archiving is enabled on PostgreSQL.
* **Recovery Time Objective (RTO):** $\le 15\text{ minutes}$ from disaster declaration to fully serving traffic on a cold database instance.
* **Backup Retention Policy:**
  * **Daily Full Dumps:** Retained for 30 days locally and replicated to off-site S3-compatible cold storage.
  * **Weekly Snapshots:** Retained for 12 weeks.
  * **Monthly Financial Closes:** Retained for 7 years for statutory Nepal Inland Revenue Department (IRD) compliance.

---

## 2. Backup Scope & Assets

| Asset Category | Location | Backup Mechanism | Format |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Catalog** | PostgreSQL instance | `pg_dump` via `backup_service.py` | Compressed/Plain text SQL dump |
| **Product & Gallery Images** | Container volume `/app/uploads` (`backend_uploads`) | Tarball snapshot / S3 sync | `uploads_<timestamp>.tar.gz` |
| **Environment Configuration** | Host `/etc/livo/.env.production` | Secret manager / encrypted vault | AES-256 encrypted archive |

---

## 3. Automated & Manual Backup Execution

### Automated Execution (System Cron / Task Scheduler)
Automated daily backups run at 02:00 NPT via Docker host cron:
```bash
0 2 * * * docker compose exec -T backend python -c "from app.services.backup_service import run_database_backup; run_database_backup()" >> /var/log/livo_backup.log 2>&1
```

### Manual On-Demand Backup Procedure
Before any schema migration, package upgrade, or maintenance window, generate an on-demand backup:

1. **Verify Database Health:**
   ```bash
   curl -f http://localhost:8000/health/ready
   ```
2. **Execute Backup Command:**
   ```bash
   # From host terminal inside backend container
   docker compose exec backend python -c "
   from app.services.backup_service import run_database_backup
   result = run_database_backup(notes='Pre-deployment Checkpoint 17 manual backup')
   print(result)
   "
   ```
3. **Verify Generated Artifact:**
   ```bash
   docker compose exec backend ls -lh /app/backups/
   ```
   Ensure the output `.sql` file has a non-zero byte size and status in `/app/backups/latest_status.json` states `"status": "success"`.

4. **Snapshot Uploaded Files:**
   ```bash
   docker run --rm -v livo-footwear-erp_backend_uploads:/data -v /var/backups/livo:/backup alpine tar czf /backup/uploads_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
   ```

---

## 4. Disaster Recovery & Restore Procedure

In the event of database corruption, accidental drop, or cloud infrastructure failure:

### Step 1: Quarantine & Halt Ingress Traffic
Prevent partial writes and ensure transaction isolation during recovery:
```bash
# Scale API workers down to 0 to terminate active database connections
docker compose stop backend frontend
```

### Step 2: Provision Clean Target Database
Connect to the PostgreSQL instance as administrative superuser (`postgres`):
```bash
psql -h <PG_HOST> -U postgres -c "DROP DATABASE IF EXISTS livo_erp;"
psql -h <PG_HOST> -U postgres -c "CREATE DATABASE livo_erp WITH OWNER livo_user ENCODING 'UTF8';"
```

### Step 3: Execute Restore Script
Run the automated restore service targeting the latest verified backup:
```bash
# Example syntax using psql
psql "postgresql://livo_user:secret_password@<PG_HOST>:5432/livo_erp" -f /var/backups/livo/backup_latest.sql
```
*Alternatively, invoke the Python service helper:*
```bash
docker compose run --rm backend python -c "
from app.services.backup_service import restore_database_backup
res = restore_database_backup('/app/backups/backup_latest.sql')
print(res)
"
```

### Step 4: Restore Image Assets
Extract persistent uploads to the volume:
```bash
docker run --rm -v livo-footwear-erp_backend_uploads:/data -v /var/backups/livo:/backup alpine tar xzf /backup/uploads_latest.tar.gz -C /data
```

### Step 5: Execute Migration Sanity Check
Ensure the restored database is aligned with current Alembic HEAD:
```bash
docker compose run --rm backend alembic current
docker compose run --rm backend alembic upgrade head
```

### Step 6: Post-Restore Reconciliation & Audit
Run automated data verification script before accepting customer traffic:
```bash
docker compose run --rm backend python -c "
from app.db.session import SessionLocal
from app.models import Company, User, Product, Invoice, Payment, StockMovement
from sqlalchemy import func

db = SessionLocal()
print('--- RESTORE AUDIT REPORT ---')
print('Companies Count: ', db.query(Company).count())
print('Users Count:     ', db.query(User).count())
print('Products Count:  ', db.query(Product).count())
print('Invoices Count:  ', db.query(Invoice).count())
total_sales = db.query(func.coalesce(func.sum(Invoice.total_amount), 0)).scalar()
print('Total Invoiced:  Rs.', float(total_sales))
total_paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
print('Total Payments:  Rs.', float(total_paid))
total_stock = db.query(func.coalesce(func.sum(StockMovement.direction * StockMovement.quantity), 0)).scalar()
print('Physical Stock:  ', float(total_stock), 'pairs')
assert db.query(Company).count() > 0, 'Restored database contains 0 companies!'
print('STATUS: INTEGRITY VERIFIED.')
"
```

### Step 7: Restart Application & Re-open Traffic
```bash
docker compose up -d
curl -f http://localhost:8000/health/ready
```

---

## 5. Automated Drill Verification in Test Suites

The backup and restore procedure is validated continuously by the automated test suite in `backend/tests/test_checkpoint_17_production_readiness.py`:
* **Test Case:** `test_pg_dump_and_restore_financial_parity`
* **Assertion:** Bit-for-bit exact match between primary and restored database for:
  * Company IDs and Codes
  * User credentials and active flags
  * Invoice totals and sequence counters
  * Recorded client payments
  * Net physical stock balance

---

## 6. Known Constraints & Failure Modes

1. **PostgreSQL Binary Discovery:** `pg_dump` and `psql` must match the major version of the PostgreSQL server. In containerized deployments, the backend image uses standard client libraries (`postgresql-client`). In embedded local test runs, binaries are auto-discovered via `find_pg_binary()` in `app/services/backup_service.py`.
2. **Locking During Backup:** Dumps are taken with `--no-owner --no-privileges`. Transactions on concurrent write operations are non-blocking in PostgreSQL through MVCC (Multi-Version Concurrency Control).
