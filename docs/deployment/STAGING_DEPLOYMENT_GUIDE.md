# LIVO FOOTWEAR ERP — STAGING DEPLOYMENT & OPERATIONS GUIDE

**Document Identifier:** `STAGING_DEPLOYMENT_GUIDE.md`  
**Document Path:** `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md`  
**Target Environment:** Staging (PaaS Cloud & Local PostgreSQL 18 Runner)  
**Authoring Team:** Cross-Functional Staging Engineering Team  
**Date of Release:** 2026-10-14  

---

## 1. PURPOSE & PRINCIPLES

This guide provides the authoritative, repeatable procedure for provisioning, configuring, migrating, and deploying the LIVO Footwear ERP into an isolated staging environment.

### Core Operational Principles:
1. **Zero Secret Leakage:** No plaintext passwords, database connection strings, or JWT secret keys are ever committed to version control.
2. **Immutable Migration Ordering:** Database schema migrations are governed strictly by Alembic revisions `001` through `020`. No ad-hoc DDL or manual `CREATE TABLE` scripts are permitted.
3. **Automated Lifespan Initialization:** The backend automatically applies pending Alembic migrations and seeds baseline test users upon startup.
4. **Complete Data Isolation:** Staging operates on a dedicated PostgreSQL database (`livo_staging`). It never shares tables, connections, or state with production or developer databases.

---

## 2. PRE-DEPLOYMENT PREFLIGHT CHECKLIST

Before deploying or migrating staging infrastructure, execute the preflight validation script:

```bash
python scripts/deploy_preflight.py
```

### Preflight Verification Gates:
- [x] **1. Environment Secrets:** `SECRET_KEY` is at least 32 characters (64 hex characters recommended) and does not contain placeholder strings.
- [x] **2. Database & Migrations:** `DATABASE_URL` is reachable; current revision matches Alembic head (`020_fixed_assets_waste_and_expenses`).
- [x] **3. Container & Reverse Proxy:** `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `Caddyfile` are present.
- [x] **4. Backup & Recovery Scripts:** `backup_nightly.sh`, `restore_postgres.sh`, and `verify_postgres_backup_restore.py` are present.
- [x] **5. Cryptographic Primitives:** Password hashing via `bcrypt` / `argon2` is active and operational.

---

## 3. STAGING SECRET MANAGEMENT & CONFIGURATION

### 3.1 Generating Application Secrets
Generate a cryptographically secure 256-bit random secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 Secret Ingestion Rules
1. **Never commit `.env.staging`**: Verify it is excluded by `.gitignore`.
2. **Cloud PaaS (Vercel / Render / Koyeb):** Ingest secrets via the provider's Environment Variables dashboard with type `Secret` or `Sensitive`.
3. **Local Staging Runner:** Place the generated `.env.staging` file in `backend/` and verify permissions (`chmod 600` on Linux or restricted ACL on Windows).

---

## 4. DATABASE INITIALIZATION & MIGRATIONS

### 4.1 Provisioning the Staging Database
For Neon / Managed PostgreSQL:
1. Create a dedicated project named `livo-footwear-erp-staging`.
2. Create an isolated database: `CREATE DATABASE livo_staging;`.
3. Create a least-privilege staging role:
   ```sql
   CREATE USER livo_staging_user WITH ENCRYPTED PASSWORD 'StrongRandomPasswordHere';
   GRANT ALL PRIVILEGES ON DATABASE livo_staging TO livo_staging_user;
   ```
4. Obtain the TLS-enabled connection string:
   `postgresql://livo_staging_user:StrongRandomPasswordHere@ep-hostname.region.aws.neon.tech/livo_staging?sslmode=require`

### 4.2 Executing Migrations
Migrations are managed linearly by Alembic from revision `001_initial_schema` to `020_fixed_assets_waste_and_expenses`.

To apply all migrations against the staging database:
```bash
cd backend
alembic upgrade head
```

To verify the migration head without applying changes:
```bash
cd backend
alembic current
alembic heads
```
Expected output:
```
020_fixed_assets_waste_and_expenses (head)
```

---

## 5. BACKEND API DEPLOYMENT

### 5.1 Production ASGI Entrypoint
The backend runs via Uvicorn ASGI server with standard worker configuration:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips="*"
```

### 5.2 Health & Readiness Verification
Immediately upon backend startup, verify the health probes:
1. **Liveness Probe:**
   ```bash
   curl -s -i https://<staging-backend-host>/health/live
   ```
   *Expected Response:* HTTP 200 OK, `{"status":"alive","version":"1.0.0"}`
2. **Readiness Probe:**
   ```bash
   curl -s -i https://<staging-backend-host>/health/ready
   ```
   *Expected Response:* HTTP 200 OK, `{"status":"ready","database":"healthy"}`

---

## 6. FRONTEND DEPLOYMENT

### 6.1 Environment Injection
Set the public staging API URL in the frontend build environment:
```env
NEXT_PUBLIC_API_URL=https://<staging-backend-host>
```

### 6.2 Production Compilation
```bash
cd frontend
npm run build
```
Verify that the static export and TypeScript checks compile with 0 errors.

### 6.3 Routing & Rewrites
Frontend requests to `/api/*` are automatically proxied via `next.config.js` to `${NEXT_PUBLIC_API_URL}/api/*`. This guarantees:
- Secure cookies are sent on first-party domains.
- No CORS blocks on modern browsers (Safari, Chrome, Firefox).

---

## 7. POST-DEPLOYMENT VERIFICATION SEQUENCE

1. **Access Web App:** Navigate to `https://<staging-frontend-host>`.
2. **Authenticate:** Log in with seeded staging credentials (`admin_demo` / `LivoAdmin2026!`).
3. **Verify Seeded Data:** Confirm seeded company `LIVO GROUP OF INDUSTRIES` and `WH-MAIN` warehouse are visible on the dashboard.
4. **Execute Synthetic E2E Flow:** Run through Gate 4 test scenarios (Purchase GRN -> Production Batch -> Sales Dispatch -> HR Advance).
