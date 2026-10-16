# LIVO ERP — Controlled Demonstration Recovery & Disaster Runbook

**Runbook Version:** 1.0.0 (Day 3 Disaster Recovery Baseline)  
**Applicability:** Controlled 1-Week Cloud Demonstration Environment  
**Critical Operator Rule:** **NEVER RESTORE OVER AN ACTIVE DATABASE OR OVERWRITE THE ONLY BACKUP COPY.** Always restore into a fresh, isolated target database first.

---

## 1. Quick Emergency Triage & Escalation Stops

### 🛑 STOP AND ESCALATE IMMEDIATELY IF:
1. **The only available backup file is corrupt or unverified:** Do NOT overwrite or wipe the running database. Stop immediately and inspect transaction logs / WAL archives.
2. **Data loss exceeds agreed RPO (> 24 hours):** Notify lead auditor and project stakeholders before restoring or resuming traffic.
3. **Hardware / Volume corruption:** If physical disk volume reports I/O errors, do NOT run repair tools directly on the live database partition without cloning the raw block device.
4. **Credential Leak:** If `SECRET_KEY` or database credentials were leaked into logs, stop all external ingress, rotate keys, and invalidate active JWT sessions immediately.

---

## 2. Procedure A: Creating a Manual Database Backup

### Step 1: Pre-Flight Environment Inspection
Ensure `pg_dump` is in the system PATH and target directory has sufficient disk space (minimum 2x current DB size):
```bash
# Verify pg_dump version
pg_dump --version

# Verify directory space (Linux / Docker container)
df -h /app/backups
```

### Step 2: Trigger Native PostgreSQL Backup
Run `pg_dump` with custom or plaintext SQL format against the active database:
```bash
# Set timestamp and backup filename
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/app/backups/livo_manual_backup_${BACKUP_TIMESTAMP}.sql"
TMP_BACKUP_FILE="${BACKUP_FILE}.tmp"

# Execute dump to atomic temporary file
pg_dump "${DATABASE_URL}" -F p -f "${TMP_BACKUP_FILE}"

# Verify exit code
if [ $? -eq 0 ] && [ -s "${TMP_BACKUP_FILE}" ]; then
    mv "${TMP_BACKUP_FILE}" "${BACKUP_FILE}"
    echo "[OK] Backup created successfully: ${BACKUP_FILE}"
else
    echo "[ERROR] pg_dump failed or produced empty file!"
    rm -f "${TMP_BACKUP_FILE}"
    exit 1
fi
```

### Step 3: Compute & Record Artifact SHA-256 Checksum
```bash
# Generate SHA-256 digest
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
cat "${BACKUP_FILE}.sha256"
```

---

## 3. Procedure B: Verifying a Backup Artifact

Never attempt restoration without pre-flight artifact validation:

```bash
# 1. Verify file exists and is non-empty (> 1024 bytes)
FILE_SIZE=$(stat -c%s "${BACKUP_FILE}")
if [ "${FILE_SIZE}" -lt 1024 ]; then
    echo "[CRITICAL] Backup file size (${FILE_SIZE} bytes) is suspiciously small."
    exit 1
fi

# 2. Verify SHA-256 integrity against recorded checksum
sha256sum -c "${BACKUP_FILE}.sha256"
if [ $? -ne 0 ]; then
    echo "[CRITICAL] SHA-256 checksum mismatch! Artifact is corrupted."
    exit 1
fi

# 3. Check for PostgreSQL dump completion trailer
tail -n 10 "${BACKUP_FILE}" | grep -q "PostgreSQL database dump complete"
if [ $? -ne 0 ]; then
    echo "[WARNING] Backup file does not contain clean dump completion footer."
fi
```

---

## 4. Procedure C: Isolated Database Restoration

Restore strictly into a new, isolated database instance to prevent data overwrites.

### Step 1: Create Isolated Target Database
Connect as database administrator and provision an empty restore target:
```sql
-- Connect to administrative postgres instance
CREATE DATABASE livo_recovery_test;
```

### Step 2: Restore via `psql`
```bash
RESTORE_TARGET_URL="postgresql://livo_admin:Secret@postgres:5432/livo_recovery_test"

# Execute psql restore with stop-on-error flag
psql "${RESTORE_TARGET_URL}" -v ON_ERROR_STOP=1 -f "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "[OK] Restoration completed successfully."
else
    echo "[ERROR] Database restoration encountered SQL errors!"
    exit 1
fi
```

---

## 5. Procedure D: Business Invariant & Integrity Verification

Run the automated verification suite or execute diagnostic queries against the restored database:

```sql
-- 1. Check Alembic Schema Revision parity
SELECT version_num FROM alembic_version;
-- Expected: 024_add_rate_limit_entries

-- 2. Verify Physical Stock Balance Math
-- Sum(quantity * direction) must match on-hand products
SELECT 
    product_id, 
    SUM(quantity * direction) as net_stock_pairs
FROM stock_movements
GROUP BY product_id;

-- 3. Verify Accounts Receivable Subledger Integrity
-- Total AR subledger entries must match sum of debtor client balances
SELECT 
    client_id,
    SUM(amount_paisa * direction) as net_receivable_paisa
FROM receivable_entries
GROUP BY client_id;

-- 4. Verify Gapless Invoice Numbering
SELECT 
    company_id, 
    invoice_number, 
    sequence_number
FROM invoices
ORDER BY company_id, sequence_number ASC;

-- 5. Verify Unclosed HR Advance Remaining Principal
SELECT 
    w.worker_code,
    w.name,
    a.amount_paisa as initial_advance_paisa,
    COALESCE(SUM(r.amount_paisa), 0) as total_repaid_paisa,
    a.amount_paisa - COALESCE(SUM(r.amount_paisa), 0) as remaining_debt_paisa
FROM worker_advances a
JOIN workers w ON w.id = a.worker_id
LEFT JOIN worker_advances r ON r.parent_advance_id = a.id AND r.entry_type = 'RECOVERED'
WHERE a.entry_type = 'ISSUED'
GROUP BY w.worker_code, w.name, a.id, a.amount_paisa;
```

---

## 6. Procedure E: Switching Application Traffic to Restored Database

1. **Stop Application Ingress:**
   ```bash
   # Scale backend down to 0 to prevent writes to old database
   docker compose stop backend
   ```
2. **Update Environment Configuration:**
   Update `DATABASE_URL` in `.env` or deployment environment to point to the restored database:
   ```bash
   DATABASE_URL=postgresql://livo_admin:Secret@postgres:5432/livo_recovery_test
   ```
3. **Verify Readiness:**
   Start single replica and poll readiness endpoint:
   ```bash
   docker compose up -d backend
   curl -f http://localhost:8000/health/ready
   ```
   *Expected Response:* `{"status": "ready", "database": "healthy", "current_head": "024_add_rate_limit_entries"}`.
4. **Resume Full Traffic:**
   Bring reverse proxy (`caddy`) and frontend back into active routing.

---

## 7. Procedure F: Recovering Uploaded Files & Secure HR Documents

Database dumps do **not** contain raw filesystem files. Execute file recovery in parallel:

```bash
# 1. Restore product catalog images
rsync -avz /backup_storage/static/uploads/products/ /app/static/uploads/products/

# 2. Restore worker profile photos
rsync -avz /backup_storage/static/uploads/workers/ /app/static/uploads/workers/

# 3. Restore secure HR citizenship documents
rsync -avz /backup_storage/storage/secure_hr/ /app/storage/secure_hr/

# 4. Enforce strict non-root ownership and file permissions
chown -R livo:livo /app/static/uploads /app/storage/secure_hr
chmod 700 /app/storage/secure_hr
```

---

## 8. Procedure G: Credential Rotation (In Case of Exposure)

If `SECRET_KEY` or database passwords are leaked:

1. **Generate New Strong `SECRET_KEY`:**
   ```bash
   NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   ```
2. **Update `SECRET_KEY` in deployment environment:**
   Updating `SECRET_KEY` invalidates all outstanding JWT bearer tokens immediately, forcing all users to re-authenticate.
3. **Rotate Database Password:**
   ```sql
   ALTER USER livo_admin WITH PASSWORD 'NewUltraSecurePassword2026!';
   ```
   Update `DATABASE_URL` across all environment definitions and restart services.

---

## 9. Procedure H: Rollback for Failed Deployment or Migration

### If a Migration Fails During Application Startup:
1. The application lifespan handler immediately aborts startup (`RuntimeError`) and refuses to serve traffic.
2. Inspect the startup log to identify the failing revision ID and root cause:
   ```bash
   docker compose logs backend | grep "FATAL: Database migration failed"
   ```
3. **NEVER** run `alembic downgrade -1` blindly if the failed migration partially committed DDL.
4. Check the database `alembic_version` table:
   ```sql
   SELECT version_num FROM alembic_version;
   ```
5. If the schema is corrupted, do NOT attempt ad-hoc schema editing. Revert to the snapshot taken immediately prior to the deployment and restart the previous container image version.
