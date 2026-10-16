# LIVO Footwear ERP — Day 5 Operator Runbook & Demo Checklist

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Target:** Controlled 1-week cloud demonstration using synthetic evaluation data only.

---

## 1. Pre-Deployment Configuration Checklist

Before booting the containers, the operator must verify that the environment variables are configured securely:

### 1.1 Environment Variable Specification (`.env.production` / Cloud Dashboard)

```ini
# Core Application
ENVIRONMENT=staging
LIVO_DEV_MODE=false
AUTO_MIGRATE=true
PROJECT_NAME="LIVO GROUP OF INDUSTRIES Footwear ERP"
VERSION="1.0.0"

# Cryptographic Keys (MUST BE GENERATED FRESH; DO NOT REUSE)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=e8392a82910fae82937dcb92817291a8271039bc8102938192083921098231aa
POSTGRES_USER=livo_admin
POSTGRES_PASSWORD=SuperSecretPassphrase2026!
POSTGRES_DB=livo_erp
DATABASE_URL=postgresql://livo_admin:SuperSecretPassphrase2026!@postgres:5432/livo_erp

# Network & Proxy Security
BACKEND_CORS_ORIGINS=https://demo.livogroup.com,https://app.livogroup.com
DOMAIN=demo.livogroup.com
TRUSTED_PROXIES=127.0.0.1,::1,172.16.0.0/12

# Controlled Demo Seeding (Explicit Opt-In for Synthetic Evaluation Data Only)
ENABLE_DEMO_SEEDING=true

# Offsite S3 Storage (Required if mirroring backups to Cloud Bucket)
STORAGE_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
STORAGE_ACCESS_KEY=your_b2_access_key
STORAGE_SECRET_KEY=your_b2_secret_key
STORAGE_BUCKET_NAME=livo-erp-storage
```

---

## 2. Container Launch & Port Isolation Verification

Run the multi-container stack:
```bash
docker compose up -d --build
```

### 2.1 Verify Network Isolation
Confirm that PostgreSQL is **not** reachable from external or host network interfaces:
```bash
# Check listening ports on the host
docker compose ps
# Expected:
#   caddy:    0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
#   frontend: 3000/tcp (internal only)
#   backend:  8000/tcp (internal only)
#   postgres: 5432/tcp (internal only — NO host port mapped!)
```

### 2.2 Verify Health & Readiness Probes
```bash
# 1. Check Liveness Probe (Should return 200 alive)
curl -f http://localhost:8000/api/v1/health/live
# Expected: {"status":"alive","version":"1.0.0",...}

# 2. Check Readiness Probe (Should return 200 ready)
curl -i http://localhost:8000/api/v1/health/ready
# Expected: HTTP/1.1 200 OK
# Expected Body: {"status":"ready","database":"healthy","current_head":"024_add_rate_limit_entries"}
```
*Note: If `/api/v1/health/ready` returns HTTP 503, inspect database migrations immediately; the application will not accept live client traffic.*

---

## 3. Demo Persona Credentials

When `ENABLE_DEMO_SEEDING=true` is enabled in `staging`, the following synthetic personas are automatically available for rehearsal and evaluation:

| Persona Name | Username | Password | Role | Permitted Actions |
| :--- | :--- | :--- | :---: | :--- |
| **System Administrator** | `admin_demo` | `LivoAdmin2026!` | `admin` | Full control: user management, confidential HR documents, diagnostics download, fixed asset deletion, ops cockpit. |
| **Factory Supervisor** | `editor_admin` | `LivoEditor2026!` | `editor` | Operational mutations: purchasing, goods receipt, production batches, stock transfers, sales orders, invoices, and expense logging. |
| **Compliance Auditor** | `viewer_demo` | `LivoViewer2026!` | `viewer` | Read-only inspection: stock ledger, receivables aging, product gallery, and production analytics. Salary figures and citizenship PDFs are strictly redacted/blocked. |

---

## 4. Operational Backup & Recovery Procedure

### 4.1 Creating a Complete System Backup (Database + Files)
Execute inside the backend container or via admin scheduled cron:
```python
from app.services.backup_service import create_complete_system_backup
from app.db.session import SessionLocal

db = SessionLocal()
try:
    manifest = create_complete_system_backup(db)
    print(f"System Backup Complete: {manifest}")
finally:
    db.close()
```
**Artifacts Generated:**
1. Database dump: `backups/livo_dump_<timestamp>.sql` (SHA-256 digested)
2. Storage archive: `backups/livo_files_<timestamp>.tar.gz` (SHA-256 digested)
3. Manifest: `backups/livo_manifest_<timestamp>.json`

### 4.2 Restoring from Backup
```bash
# 1. Restore Database SQL Dump
psql -h postgres -U livo_admin -d livo_erp -v ON_ERROR_STOP=1 -f backups/livo_dump_<timestamp>.sql

# 2. Restore File Storage Archive
python -c "
from app.services.backup_service import restore_storage_backup
restore_storage_backup('backups/livo_files_<timestamp>.tar.gz')
"

# 3. Verify Database and File Parity
python -c "
from app.services.backup_service import verify_database_and_file_parity
from app.db.session import SessionLocal
db = SessionLocal()
res = verify_database_and_file_parity(db)
print(res)
assert res['status'] == 'healthy', f'Discrepancy found: {res}'
db.close()
"
```

---

## 5. Live Demonstration Sequence

Follow this tested path to wow the client while respecting verified product capabilities:

1. **Login & Role Briefing (`00:00 - 05:00`):**
   - Log in as `editor_admin`. Show the modern, responsive `AppShell` with the active role badge.
   - Highlight the **Nepali Date Picker** (`NepaliDatePicker.tsx`) showing Bikram Sambat (2083 BS) and AD synchronization.
2. **Purchasing & Landed Cost (`05:00 - 10:00`):**
   - Navigate to **Purchase Raw Materials**.
   - Input a supplier purchase for Synthetic PU Leather Sheet (100 kg @ 450 NPR).
   - Enter landed expenses: Carrying In (2,500 NPR), Import Duty (1,500 NPR), Customs (1,000 NPR).
   - Show that the landed unit cost recalculates to 500.00 NPR / kg.
3. **Production & Finished Goods Output (`10:00 - 15:00`):**
   - Open **Production Batches**. Create a batch producing 40 pairs of "LIVO Trekker Pro Boot" (Size 42, Brown).
   - Show that the finished pairs automatically appear in the factory finished goods stock ledger.
4. **Inter-Warehouse Stock Transfer (`15:00 - 20:00`):**
   - Open **Branches & Godowns** / **Stock Transfer Modal**.
   - Transfer 15 pairs from Hetauda Factory to Kathmandu Retail Hub.
   - Show status moving from `DRAFT` -> `IN_TRANSIT` (source balance reduces) -> `RECEIVED` (retail balance increases).
5. **Sales, 13% Nepal VAT Invoicing & AR (`20:00 - 25:00`):**
   - Navigate to **Sales & Invoicing**. Dispatch 10 pairs to "Kathmandu Adventure Gear" (42,000 NPR).
   - Generate official VAT Tax Invoice showing 13% VAT (5,460 NPR) and Total (47,460 NPR).
   - Record a partial payment (27,460 NPR) and show the outstanding receivable in **Accounts Receivable Aging**.
6. **HR Privacy & Security Walkthrough (`25:00 - 30:00`):**
   - Log in as `admin_demo` to show worker salary records and citizenship document attachments.
   - Switch to `viewer_demo` and demonstrate that salary fields and document download buttons are completely suppressed.

---

## 6. Emergency Troubleshooting & Rollback

| Symptom | Probable Cause | Immediate Remediation |
| :--- | :--- | :--- |
| **HTTP 503 on `/health/ready`** | Migration failed or divergent schema head | Inspect container logs: `docker compose logs backend`. Confirm Alembic is at head `024_add_rate_limit_entries`. |
| **Login fails with 401** | Missing demo accounts | Ensure `ENABLE_DEMO_SEEDING=true` and `ENVIRONMENT=staging`. Restart backend container to trigger lifespan seeding. |
| **CORS error in browser** | Mismatched domain | Verify `BACKEND_CORS_ORIGINS` in `.env` matches the exact browser URL including protocol (e.g., `https://demo.livogroup.com`). |
| **Missing images after restore** | Incomplete file restore | Run `verify_database_and_file_parity(db)` to pinpoint missing files in `static/uploads/`. |
