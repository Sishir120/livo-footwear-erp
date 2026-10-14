# LIVO Footwear ERP — Production Deployment Runbook

**Version:** 1.0.0  
**Effective Date:** October 2, 2026  
**Audience:** Release Engineering, Site Reliability Engineering, Production Operations  

---

## 1. System Architecture Topology

The production environment is structured as a hardened, multi-tier containerized topology:

```text
       [ Public Client Browser ]
                   │  HTTPS (443) / Strict TLS 1.3
                   ▼
         [ Caddy Reverse Proxy ]
       (HTTP -> HTTPS Redirect, HSTS, Rate Limiting,
        Forwarded Headers, Request Size Limits)
         │                         │
         │ /                       │ /api/*
         ▼                         ▼
 [ Next.js Frontend ]      [ FastAPI API Backend ]
 (Node 20 Alpine, Non-Root)  (Python 3.11 Slim, Non-Root)
         │                         │
         │                         ├──▶ [ PostgreSQL 16+ ] (Persistent DB)
         │                         └──▶ [ Persistent Volume: /app/uploads ]
```

### Component Details
* **Reverse Proxy:** Caddy / Nginx handling automated ACME TLS certificates, HTTP/2 + HTTP/3, and request termination.
* **Frontend Service:** Next.js 14 Standalone container executed under non-root system user `nodejs` (UID 1001).
* **Backend API:** FastAPI application served via Gunicorn / Uvicorn workers executed under non-root system user `livo` (UID 10001).
* **Database:** Dedicated PostgreSQL 16+ instance configured with connection pooling (`pool_size=20`, `max_overflow=10`).
* **Persistent Storage:** Docker named volume `backend_uploads` mounted at `/app/uploads` for permanent catalog media retention.

---

## 2. Pre-Deployment Verification Checklist

Before initiating any production release:

1. **Verify Environment Configuration:**
   Ensure production `.env` is populated with cryptographically strong secrets:
   * `SECRET_KEY`: Minimum 32 random characters generated via `secrets.token_urlsafe(48)`
   * `DEBUG`: Explicitly `false`
   * `COOKIE_SECURE`: `true`
   * `DATABASE_URL`: Valid PostgreSQL connection string (`postgresql+psycopg2://...`)
   * `BACKEND_CORS_ORIGINS`: Explicit client origin whitelist (e.g. `https://erp.clientdomain.com`), never `*`

2. **Execute Automated Deployment Preflight:**
   ```bash
   python scripts/deploy_preflight.py
   ```
   *Release cannot proceed unless preflight outputs `ALL PREFLIGHT CHECKS PASSED`.*

3. **Verify Database Backup:**
   Execute a fresh snapshot per `docs/BACKUP_RESTORE_RUNBOOK.md`.

---

## 3. Production Deployment Procedure

### Step 1: Clone or Fetch Release Artifacts
```bash
git fetch origin main --tags
git checkout <RELEASE_TAG_OR_COMMIT>
```

### Step 2: Build Hardened Container Images
```bash
docker compose build --no-cache
```

### Step 3: Run Database Migrations
Execute Alembic migrations in a standalone ephemeral container before rolling the application:
```bash
docker compose run --rm backend alembic current
docker compose run --rm backend alembic upgrade head
```
Verify that the output indicates `012_add_c15_indexes` (or latest HEAD).

### Step 4: Deploy / Rolling Restart Containers
```bash
docker compose up -d --remove-orphans
```

### Step 5: Verify Container Health & Status
```bash
docker compose ps
```
Both `backend` and `frontend` must report `healthy` or `running`.

---

## 4. Post-Deployment Verification & Smoke Testing

### Liveness Probe
```bash
curl -f -i https://erp.clientdomain.com/health/live
```
*Expected Response:* `HTTP 200 OK`, `{"status": "alive"}`

### Readiness Probe
```bash
curl -f -i https://erp.clientdomain.com/health/ready
```
*Expected Response:* `HTTP 200 OK`, `{"status": "ready", "database": "connected"}`

### Core API Smoke Execution
Run curl or test harness to verify token issuance and inventory balance:
```bash
# 1. Login Authentication
curl -c cookies.txt -X POST https://erp.clientdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "<PRODUCTION_ADMIN_PASSWORD>"}'

# 2. Query Stock Balance
curl -b cookies.txt https://erp.clientdomain.com/api/v1/stock/balance?limit=10

# 3. Query Receivables Aging
curl -b cookies.txt https://erp.clientdomain.com/api/v1/receivables/aging
```

---

## 5. Production Observability & Monitoring

* **Structured Logging:** All backend logs stream as JSON to stdout containing `correlation_id`, `request_id`, `company_id`, and `actor_id`.
* **Privacy Boundary:** Sensitive keys (`password`, `access_token`, `authorization`) are masked before log output.
* **Alerting Metrics:** Monitor container CPU, memory usage, and HTTP status codes:
  * Alert if 5xx error rate exceeds $0.1\%$ over a 5-minute rolling window.
  * Alert if database connection pool saturation exceeds $80\%$.
  * Alert if `/health/ready` fails consecutively for 3 checks.
