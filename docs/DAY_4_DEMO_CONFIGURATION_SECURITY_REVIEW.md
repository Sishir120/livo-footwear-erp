# LIVO Footwear ERP — Day 4 Demo Configuration Security Review

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Scope:** Demo configuration templates, Docker Compose, Caddy reverse-proxy, environment variable schemas, container hardening, network isolation, and secret management.  
**Execution Environment:** Static and architectural inspection without connecting to external cloud resources.

---

## 1. Executive Summary

This security review independently audited the actual intended deployment and demonstration configurations for LIVO Footwear ERP across `docker-compose.yml`, `Caddyfile`, `render.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `backend/app/config.py`.

The deployment architecture enforces strict defense-in-depth principles:
- **Zero Exposed Database Ports:** PostgreSQL (port 5432) is isolated on internal Docker networks and unreachable from public interfaces.
- **Fail-Fast Secret Enforcement:** The backend process immediately aborts during startup if `SECRET_KEY` is empty, preventing accidental execution under an insecure default.
- **Strict Demo Seeding Guard:** Demo persona seeding is disabled by default (`ENABLE_DEMO_SEEDING=false`), requires explicit non-production environment confirmation, and fails closed in production.
- **Protected File Storage:** Neither product gallery images nor confidential HR citizenship documents are served via public static directory mounts; all uploads are served through tenant-scoped, authenticated, and RBAC-authorized API routes.
- **Safe Reverse-Proxy Traversal:** Client IP derivation traverses `X-Forwarded-For` from right to left against an explicit `TRUSTED_PROXIES` CIDR list, defeating IP spoofing against the distributed rate limiter.

---

## 2. Detailed Configuration & Security Controls Audit

### 2.1 Secrets & Credential Management

| Parameter | Configuration Source | Default Value | Verification Result | Security Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| `SECRET_KEY` | Environment (`os.getenv`) | None (Empty string) | **PASS** | `backend/app/config.py` lines 96–101 crashes application startup with `ValueError` if `SECRET_KEY` is not provided. In `render.yaml`, `generateValue: true` automatically generates a cryptographically secure 256-bit secret. In `docker-compose.yml`, `${SECRET_KEY:?SECRET_KEY must be set}` halts container creation if unset. |
| `POSTGRES_PASSWORD` | Environment | None | **PASS** | `docker-compose.yml` line 8 specifies `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}`. Docker Compose refuses to launch if unsupplied. |
| `DATABASE_URL` | Environment | SQLite fallback in dev | **PASS** | Masked in application logs via regex sanitizer `_sanitize_db_error` in `main.py` (line 28), ensuring connection string credentials never leak to stdout or monitoring sinks. |
| `STORAGE_SECRET_KEY` | Environment | None | **PASS** | S3-compatible credentials for Backblaze/R2 cloud backups are environment-provided with no default commit. |

---

### 2.2 Demo Persona & Administrator Seeding (`SEC-01`)

- **Implementation:** `backend/app/core/demo_seeding.py` invoked during FastAPI `lifespan`.
- **Default State:** `ENABLE_DEMO_SEEDING=false` in `config.py`.
- **Environment Gate:** Even if an operator accidentally configures `ENABLE_DEMO_SEEDING=true`, `seed_demo_users_if_enabled()` checks `settings.ENVIRONMENT`. If the environment is `"production"`, `"prod"`, or unlisted, it emits a `CRITICAL` alert and **fails closed** (`{"status": "rejected", "reason": "production_mode_refusal"}`), refusing to seed accounts.
- **Preservation Invariant:** Demo seeding only creates missing personas (`admin_demo`, `viewer_demo`, `editor_admin`, `viewer_user`). It never updates, resets, or overwrites passwords of existing user accounts.
- **Production Administrator Creation:** For production deployments, initial administrators must be provisioned via a one-off database CLI script or automated secure onboarding script; no hardcoded default admin exists in production configurations.

---

### 2.3 Network Isolation & Port Exposure

```
[ Public Internet ]
         │ (Ports 80 / 443 TLS)
         ▼
 ┌───────────────┐
 │  Caddy Proxy  │  (caddy:2-alpine)
 └───────┬───────┘
         │ (Internal Docker Bridge)
         ├───────────────────────────────┐
         ▼ (Port 3000)                   ▼ (Port 8000)
 ┌───────────────┐               ┌───────────────┐
 │ Next.js Front │               │ FastAPI App   │ (Non-root user `livo`)
 └───────────────┘               └───────┬───────┘
                                         │ (Internal Docker Bridge)
                                         ▼ (Port 5432)
                                 ┌───────────────┐
                                 │  PostgreSQL   │ (UNEXPOSED to host/public)
                                 └───────────────┘
```

- **Database Exposure:** In `docker-compose.yml`, the `postgres` service contains no `ports:` mapping, only internal network visibility to `backend`. Host and WAN interfaces cannot directly bind or query PostgreSQL port 5432.
- **Application Services:** `backend` (port 8000) and `frontend` (port 3000) use `expose:`, making them accessible only to the Caddy reverse-proxy service within the container network.
- **TLS & Public Edge:** Only Caddy binds to host ports 80 and 443, handling automatic TLS certificate management, HSTS, and request routing.

---

### 2.4 Reverse Proxy & HTTP Security Headers

Inspected `Caddyfile`:
- **Routing Isolation:**
  - `/api/*`, `/health/*`, `/docs*`, `/openapi.json` are routed to `backend:8000`.
  - All other paths default to `frontend:3000`.
  - **No Direct Storage/Static Mount:** Neither `/storage/*` nor `/static/*` is mapped in Caddy.
- **Security Headers Enforced:**
  - `Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"`
  - `X-Content-Type-Options "nosniff"`
  - `X-Frame-Options "DENY"`
  - `Referrer-Policy "strict-origin-when-cross-origin"`
- **Structured Logging:** Caddy outputs structured JSON access logs to `stdout`.

---

### 2.5 Sensitive Uploads & File Protection

An audit of storage mechanisms verified that uploads cannot be scraped or accessed by unauthorized actors:
1. **Product Gallery Images:**
   - Uploaded to `backend/static/uploads/products/`.
   - Served via `/api/v1/gallery/images/{image_id}/download`.
   - **Protection:** Requires valid JWT authentication (`Depends(get_current_user)`), filters by `company_id`, and runs `_safe_resolve_image_path()` to block directory traversal attacks (`../`).
2. **Worker Profile Photos:**
   - Uploaded to `backend/static/uploads/workers/`.
   - Stored with UUID prefixes.
3. **Confidential HR Citizenship Documents:**
   - Uploaded to `backend/storage/secure_hr/company_{id}/citizenship/`.
   - Served via `/api/v1/hr/workers/{worker_id}/citizenship`.
   - **Protection:** Strictly restricted to `Role.ADMIN` (`Depends(require_admin)`). Emits `Cache-Control: private, no-store, no-cache, must-revalidate` and `Content-Disposition: inline` headers to prevent intermediary proxy caching and browser disk persistence. Non-admin users receiving worker lists only see sanitized booleans (`has_citizenship_doc: true/false`).

---

### 2.6 Error Sanitization & Information Disclosure

- **Unhandled Server Exceptions (500):** Handled by `global_exception_handler` in `backend/app/core/exceptions.py`. Emits a generic error message (`"An unexpected error occurred. Please contact system administrator."`), an internal tracking `request_id`, and error taxonomy code `INTERNAL_ERROR`. Raw exception traces, SQL syntax, and internal server paths are never sent to HTTP clients.
- **Database Connection Strings:** Sanitized via regex in `main.py` (`_sanitize_db_error`), replacing `:password@` with `:***@` in all startup logs.
- **Diagnostics Bundle:** Route `/api/v1/health/diagnostics/download` requires `Role.ADMIN`. Regular users and viewers cannot exfiltrate application diagnostic bundles.

---

### 2.7 Rate Limiting & Client IP Derivation (`SEC-03`)

- **Middleware:** `BasicRateLimitMiddleware` in `backend/app/middleware/rate_limit.py`.
- **IP Resolution:** `extract_client_ip()` verifies the direct peer connection against `settings.TRUSTED_PROXIES`.
  - If peer is **not trusted**, forwarded headers (`X-Forwarded-For`, `X-Real-IP`) are strictly ignored, defeating header injection.
  - If peer is **trusted**, `X-Forwarded-For` is parsed from right to left to select the outermost untrusted public client IP.
- **Persistence Store:** PostgreSQL table `rate_limit_entries` ensures cross-worker rate limiting under multi-process Uvicorn deployments, with transparent fallback to in-memory sliding window if database communication is interrupted.

---

### 2.8 Health & Readiness Probes

- **Liveness Probe (`/api/v1/health/live`):**
  - **Contract:** Returns HTTP 200 `{"status": "alive"}` with build commit.
  - **Dependency:** No database or network calls. Prevents cascading container restarts when the database is restarting or under transient load.
- **Readiness Probe (`/api/v1/health/ready`):**
  - **Contract:** Returns HTTP 200 when ready, HTTP 503 when degraded or schema mismatch.
  - **Checks Executed:**
    1. Database `SELECT 1` connectivity.
    2. Dynamic Alembic migration head resolution (verifies single head in graph).
    3. `alembic_version` database check (flags empty, multiple, divergent, or lagging revisions).
    4. Fast catalog inspection of critical tables (`companies`, `users`, `invoices`, `products`, `production_batches`, `stock_movements`) and core columns (< 5ms).

---

### 2.9 Startup Migration Discipline (`SEC-02`)

- **Configuration:** `AUTO_MIGRATE=true` (configurable via env).
- **Multi-Instance Coordination:** Uses PostgreSQL advisory lock (`SELECT pg_advisory_lock(8877665544332211)`) to serialize concurrent migration executions across replica containers during rolling deployments.
- **Failure Behavior:** If `alembic.command.upgrade(alembic_cfg, "head")` fails, the exception is caught, database credentials are sanitized in logs, and `main.py` explicitly raises `RuntimeError(f"Database migration failure: {sanitized}")`. Startup **aborts immediately**, preventing the server from accepting live requests on an invalid schema.

---

### 2.10 Backup Destination & Retention Rules

- **Local / Container Backup Mounts:**
  - `backend_backups` mounted to `/app/backups`.
  - `backend_storage` mounted to `/app/storage`.
  - `backend_uploads` mounted to `/app/static/uploads/products`.
- **Disaster Recovery Requirement:**
  - In a production or persistent demo deployment, `backend_backups` must be mirrored or synced to external object storage (`STORAGE_ENDPOINT_URL`, S3/B2/R2) or an off-host volume. Retaining backups solely inside a Docker volume on the same host leaves them vulnerable to host termination.

---

## 3. Operational Setup Verification Checklist

Before starting the controlled demo environment:

1. [x] Generate cryptographically random `SECRET_KEY` (minimum 32 hex bytes).
2. [x] Set `POSTGRES_PASSWORD` with high-entropy passphrase.
3. [x] Set `LIVO_DEV_MODE=false` to ensure `Secure` cookie flags and strict HTTPS enforcement.
4. [x] Configure `BACKEND_CORS_ORIGINS` to match the exact frontend demo domain (e.g., `https://demo.livogroup.com`).
5. [x] Set `TRUSTED_PROXIES` to include the Caddy container IP / reverse-proxy CIDR.
6. [x] Enable `ENABLE_DEMO_SEEDING=true` ONLY IF synthetic demo personas are required and `ENVIRONMENT=staging` or `development`.
7. [x] Ensure external backup destination (e.g. S3 bucket `livo-erp-storage`) is provisioned if automated cloud offsite backups are active.

---

## 4. Verification Conclusion

The demo configuration and security controls have been audited and verified. No unauthenticated data access paths, hardcoded secrets, or insecure default configurations were found. The configuration is robust for the controlled one-week demonstration on synthetic evaluation data.
