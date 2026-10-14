# LIVO Footwear ERP — Production Rollback Runbook

**Version:** 1.0.0  
**Effective Date:** October 2, 2026  
**Audience:** Incident Commander, Release Manager, Site Reliability Engineering  

---

## 1. Rollback Criteria & Decision Triggers

A production rollback is immediately authorized if any of the following conditions persist for $> 5\text{ minutes}$ post-deployment:

| Severity | Condition / Trigger | Measurement Threshold |
| :--- | :--- | :--- |
| **P0 - CRITICAL** | Financial calculation mismatch | Any discrepancy in invoice VAT, payment allocation, or stock ledger math |
| **P0 - CRITICAL** | Persistent service unavailability | Readiness probe `/health/ready` failing consecutively $> 3\text{ minutes}$ |
| **P0 - CRITICAL** | Multi-tenant isolation defect | Cross-tenant data leakage detected in logs or API responses |
| **P1 - HIGH** | Elevated API error rate | HTTP 5xx error rate $> 1.0\%$ across all incoming requests |
| **P1 - HIGH** | Critical performance regression | P95 latency for core endpoints (`/stock/balance`, `/sales/orders`) $> 1500\text{ms}$ |
| **P1 - HIGH** | Container startup crashloop | Backend or frontend container failing healthchecks or restarting repeatedly |

---

## 2. Rollback Decision Protocol

1. **Incident Commander (IC)** reviews monitoring telemetry, error rates, and user reports.
2. **Database Reliability Engineer (DBA)** determines if the migration introduced destructive schema changes:
   * **Case A: Schema is Backward-Compatible:** Proceed with Application-Only Rollback.
   * **Case B: Irreversible / Destructive Schema Mutation:** Execute Full Database Restore Procedure from pre-deployment snapshot.
3. **Release Manager** issues explicit order: `INITIATE ROLLBACK TO RELEASE <PREVIOUS_STABLE_TAG>`.

---

## 3. Application-Only Rollback Procedure (Backward-Compatible Schema)

When the deployed Alembic migration is additive (e.g. new nullable column, non-destructive index, new table):

### Step 1: Checkout Previous Known-Good Commit/Tag
```bash
git fetch --tags
git checkout <PREVIOUS_STABLE_TAG>
```

### Step 2: Build / Redeploy Container Images
```bash
docker compose build --no-cache
docker compose up -d --remove-orphans
```

### Step 3: Verify Process Health
```bash
curl -f http://localhost:8000/health/live
curl -f http://localhost:8000/health/ready
```

---

## 4. Full Database & Application Rollback Procedure

When a migration modified or corrupted existing data structures:

### Step 1: Terminate Traffic Immediately
```bash
docker compose stop backend frontend
```

### Step 2: Restore Database from Pre-Deployment Snapshot
Follow the verified restore procedure in `docs/BACKUP_RESTORE_RUNBOOK.md`:
```bash
# 1. Clean target database
psql -h <PG_HOST> -U postgres -c "DROP DATABASE livo_erp;"
psql -h <PG_HOST> -U postgres -c "CREATE DATABASE livo_erp WITH OWNER livo_user ENCODING 'UTF8';"

# 2. Replay pre-deployment backup dump
psql "postgresql://livo_user:<PASSWORD>@<PG_HOST>:5432/livo_erp" -f /var/backups/livo/pre_deploy_backup.sql
```

### Step 3: Checkout and Re-deploy Previous Application State
```bash
git checkout <PREVIOUS_STABLE_TAG>
docker compose build --no-cache
docker compose up -d
```

### Step 4: Validate Financial & Data Integrity
```bash
docker compose run --rm backend python -c "
from app.db.session import SessionLocal
from app.models import Company, User, Invoice
db = SessionLocal()
assert db.query(Company).count() > 0
assert db.query(Invoice).count() > 0
print('ROLLBACK DATA INTEGRITY VERIFIED.')
"
```

---

## 5. Post-Rollback Protocol

1. **Verify Customer Access:** Perform smoke verification of login and invoice viewing.
2. **Notify Stakeholders:** Update incident channel confirming stable state restoration.
3. **Capture Post-Mortem Diagnostics:**
   * Retain container failure logs: `docker compose logs backend > /var/log/livo_failed_deploy.log`
   * Preserve database query logs for forensic analysis.
4. **Hold Retrospective:** Schedule Root Cause Analysis (RCA) meeting within 24 hours. No new release allowed until defect is resolved and validated in staging.
