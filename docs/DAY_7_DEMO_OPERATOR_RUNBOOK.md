# LIVO Footwear ERP — Day 7 Demo Operator Runbook

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Target Environment:** Staging / Cloud Evaluation Instance  
**Scope:** 1-Week Controlled Demonstration (Synthetic Data Only)

---

## 1. Safety Mandates & Prerequisites

1. **Zero Real Client Data:** Under no circumstances should live client database dumps, PAN numbers, or employee documents be loaded into this instance. Only synthetic demonstration records may be used.
2. **Secret Generation:** Never reuse secrets from local environments or development files. Generate fresh 256-bit keys:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. **Network Isolation:** Ensure PostgreSQL port 5432 is strictly private within the container network / VPC. Only port 443 (HTTPS) should be accessible to evaluators.

---

## 2. Environment Configuration Profile (Staging Demo)

Create `.env` on the staging host:
```bash
# Core Environment
ENVIRONMENT=development
LIVO_DEV_MODE=false
AUTO_MIGRATE=true

# Security & Sessions
SECRET_KEY=<FRESH_CRYPTOGRAPHIC_RANDOM_64_HEX>
COOKIE_SAMESITE=lax
BACKEND_CORS_ORIGINS=https://demo.livogroup.com

# Initial Bootstrap (Set to 'false' after initial startup)
ENABLE_DEMO_SEEDING=true

# Database & Infrastructure
DATABASE_URL=postgresql://livo_user:<DB_PASSWORD>@internal-pg:5432/livo_demo?sslmode=require
TRUSTED_PROXIES=127.0.0.1,10.0.0.0/8,172.16.0.0/12
```

---

## 3. Step-by-Step Operator Procedures

### Step 1: Initialize Database & Seed Demo Personas
```bash
# 1. Start backend process to execute migrations and initial demo seeding
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Check health probes
curl -s http://127.0.0.1:8000/api/v1/health/ready | grep '"status":"ready"'
```

### Step 2: Lock Down Demo Seeding
Immediately after successful initial startup:
```bash
# Change in .env:
ENABLE_DEMO_SEEDING=false
```
Restart backend process to ensure no subsequent startups can re-trigger demo provisioning.

### Step 3: Start Frontend & Reverse Proxy
```bash
# 1. Start Next.js frontend
PORT=3000 API_URL=http://127.0.0.1:8000 npm --prefix frontend run start

# 2. Start reverse proxy (Caddy / Nginx) with TLS certificates
caddy run --config /etc/caddy/Caddyfile
```

### Step 4: Capture Baseline Backup
Before giving evaluators access, capture a pristine synthetic baseline:
```bash
python -m app.services.backup_service
```
Verify that `livo_manifest_*.json` and `livo_files_*.tar.gz` are written to `/app/backups/`.

---

## 4. Evaluator Credential Distribution

Distribute credentials to client evaluators through an encrypted, private channel:
- **Executive Administrator (`admin_demo`):** Unrestricted access across factory production, purchase orders, sales dispatch, VAT invoices, and user management.
- **Factory Supervisor (`editor_admin`):** Access to daily operations (batches, transfers, sales dispatches, goods receipt). Restricted from user management and asset deletions.
- **Compliance Auditor (`viewer_demo`):** Read-only access to stock balances and production ledger. Sensitive worker compensation and private documents are redacted.

*(Note: Passwords must be delivered through an ephemeral secret link or password manager; do not transmit in plaintext chat or commit to Git).*

---

## 5. Monitoring & Health Probes

Monitor the instance using standard probes:
- **Liveness:** `GET /api/v1/health/live` (Returns `200 OK` if process is responding).
- **Readiness:** `GET /api/v1/health/ready` (Returns `200 OK` if DB connection and schema revision `024_add_rate_limit_entries` are intact; returns `503` if degraded).
- **Log Hygiene:** Inspect logs (`tail -f /var/log/livo_erp.log`) to confirm that passwords, JWT tokens, and connection strings are sanitized (`_sanitize_db_error` active).

---

## 6. End-of-Demo Shutdown & Teardown

At the conclusion of the 1-week evaluation period:
```bash
# 1. Terminate web services
pkill -f "next start"
pkill -f "uvicorn app.main:app"

# 2. Purge synthetic database and upload directories
dropdb -h internal-pg -U livo_user livo_demo
rm -rf /app/uploads/gallery/* /app/uploads/workers/* /app/uploads/citizenship/*

# 3. Archive audit logs for evaluation retrospective
tar -czf evaluation_logs_archive.tar.gz /var/log/livo_erp.log
```

---

## 7. Concise Operator Quick-Action Checklist

- [ ] `.env` populated with fresh random `SECRET_KEY` and `LIVO_DEV_MODE=false`.
- [ ] Database created on private network; port 5432 unexposed to internet.
- [ ] Initial boot with `ENABLE_DEMO_SEEDING=true` applied schema head `024_add_rate_limit_entries`.
- [ ] Switched `ENABLE_DEMO_SEEDING=false` after initial bootstrap.
- [ ] `/api/v1/health/ready` returns `HTTP 200` with `status: ready`.
- [ ] Baseline backup executed and SHA-256 manifest confirmed.
- [ ] Demo credentials securely communicated to evaluators without committing to Git.
- [ ] Teardown and database purge scheduled for evaluation completion date.
