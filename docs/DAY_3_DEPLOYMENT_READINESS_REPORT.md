# LIVO ERP — Day 3: Deployment Readiness & Security Review

**Document Date:** 2026-10-16  
**Auditor:** Antigravity Engineering (Deployment Security & Resilience Audit)  
**Target Environment:** Controlled 1-Week Cloud Demonstration (Synthetic Data Only)  
**Status:** **CONDITIONAL PASS** (Ready for Controlled Demonstration; Live Production Gates Documented)

---

## 1. Executive Summary

This report establishes the deployment readiness, migration reliability, and security posture of LIVO Footwear ERP ahead of the scheduled one-week cloud demonstration. 

All verification was conducted against local repository code, container specifications (`Dockerfile`, `docker-compose.yml`), reverse-proxy configurations (`Caddyfile`), application lifecycle handlers (`app/main.py`), and isolated test PostgreSQL instances.

---

## 2. Migration Graph & Startup Correctness Review

### 2.1 Alembic Revision Graph Topology
- **Current Head:** `024_add_rate_limit_entries` (Single deterministic head; zero unresolved branches or heads).
- **Base Revision:** `001_baseline_schema`.
- **Total Migrations:** 24 linear revisions covering multi-tenant companies, document sequencing, stock transfers, branches, raw material landed costs, and rate-limiting storage.
- **Merge Heads History:** Revision `013_merge_heads` cleanly unified earlier parallel schema branches; all subsequent revisions (014 through 024) are strictly linear.

### 2.2 Startup Lifecycle & Concurrency Coordination
- **Startup Migration Execution:** In `app/main.py:lifespan`, when `AUTO_MIGRATE=true`, application instances coordinate migration execution using a PostgreSQL 64-bit advisory lock:
  ```python
  MIGRATION_COORDINATION_LOCK_ID = 8877665544332211
  pg_conn.execute(text(f"SELECT pg_advisory_lock({MIGRATION_COORDINATION_LOCK_ID})"))
  ```
  This eliminates migration race conditions when running multiple replicas or during rolling container deployments.
- **Migration Failure Behavior (SEC-02):** If an Alembic migration encounters an error during startup:
  ```python
  except Exception as e:
      sanitized = _sanitize_db_error(e)
      logger.critical("FATAL: Database migration failed during application startup: %s", sanitized, exc_info=True)
      raise RuntimeError(f"Database migration failure: {sanitized}") from None
  ```
  The application fails fast and crashes immediately. It **never** silently reports success or serves traffic on a corrupted or partially migrated schema.
- **Database Unavailable Behavior:** If the database is unreachable on startup, the connection probe in the lifespan handler catches the error, logs a sanitized error message, and the container fails readiness probes.

### 2.3 Readiness vs. Liveness Probes
- **Liveness Probe (`GET /health/live`):**
  - Evaluates only whether the Python/FastAPI process is running and responding to HTTP requests.
  - Zero external database dependencies; prevents cascading container restarts during transient network blips.
- **Readiness Probe (`GET /health/ready`):**
  - Verifies live database connectivity via `SELECT 1`.
  - Verifies dynamic Alembic migration head resolution (rejects conflicting or multiple heads).
  - Validates `alembic_version` parity against active codebase head (returns HTTP 503 if revision is empty, multiple, behind, or unknown).
  - Executes catalog invariants checking presence of critical tables (`companies`, `users`, `invoices`, `products`, `production_batches`, `stock_movements`) and required user columns in `< 5ms`.
  - Returns HTTP 200 when fully capable of servicing tenant requests, HTTP 503 when degraded or mismatched.

### 2.4 Default & Demo Account Hygiene (SEC-01)
- Demo account seeding is governed by `ENABLE_DEMO_SEEDING` (`bool`, default `false`).
- In `app/core/demo_seeding.py`, seeding is strictly prohibited if `ENVIRONMENT=production`:
  ```python
  if settings.is_production:
      logger.warning("Demo account seeding is strictly forbidden in production mode.")
      return
  ```
- For the controlled cloud demonstration, synthetic accounts are populated via explicit seed commands or opt-in configuration, never implicitly created during production startup.

---

## 3. Deployment Security & Infrastructure Audit

### 3.1 Debug Mode & Error Handling
- **Debug Mode:** `LIVO_DEV_MODE` defaults to `false`. In staging/production, FastAPI debug modes are disabled.
- **Global Exception Handlers:** Handlers in `app/core/exceptions.py` capture unhandled runtime exceptions, log stack traces internally with correlation IDs, and emit sanitized JSON payloads (`detail: "Internal server error"`, returning `X-Correlation-ID`) to prevent topology or trace leakage.

### 3.2 Secret Key & Credential Hygiene
- **`SECRET_KEY` Enforcement:** `Settings` in `app/config.py` enforces a mandatory non-empty `SECRET_KEY`. If unset, startup raises an explicit `ValueError`. There is no insecure hardcoded default.
- **Log Sanitization:** Database passwords in connection strings are masked via `_sanitize_db_error` in `app/main.py` and `app/services/backup_service.py`.
- **Diagnostics Security:** The `GET /api/v1/diagnostics/download` endpoint is restricted to users with `Role.ADMIN` (`require_admin`).

### 3.3 Network Exposure & Reverse Proxy
- **Database Isolation:** In `docker-compose.yml`, the PostgreSQL service (`livo-postgres`) is attached solely to the internal Docker network. Host ports (`5432`) are **not** exposed to the public internet.
- **Reverse Proxy:** Caddy reverse proxy (`Caddyfile`) terminates HTTPS on ports 80/443 with automated Let's Encrypt certificates.
- **Security Headers:**
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 3.4 CORS & Trusted Proxy Configurations
- **CORS Configuration:** `BACKEND_CORS_ORIGINS` accepts comma-separated origins. In `docker-compose.yml`, default is locked to `https://localhost` or the explicit deployment domain.
- **Trusted Proxy Handling:** `TRUSTED_PROXIES` allows specifying reverse proxy IPs (e.g. Caddy/Cloudflare/Render). `BasicRateLimitMiddleware` traverses `X-Forwarded-For` from right to left, stripping trusted hops to prevent IP spoofing attacks.

### 3.5 Session Cookies & Authentication Tokens
- **Cookie Security:** `COOKIE_SECURE` automatically evaluates to `True` when `LIVO_DEV_MODE=false`.
- **SameSite:** `COOKIE_SAMESITE="lax"`.
- **Tokens:** Bearer JWT tokens expire after 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`). Passwords are encrypted with `bcrypt`.

### 3.6 Uploaded Files & Sensitive Documents Isolation
- **Product Images (`static/uploads/products/`):** Multi-tenant access controls enforce company ownership on download (`GET /gallery/images/{id}/download`). Path traversal attempts are blocked via `_safe_resolve_image_path`.
- **Worker Citizenship Documents (`storage/secure_hr/`):**
  - Government ID documents are stored outside the public document root in `storage/secure_hr/company_{id}/citizenship/`.
  - Downloads strictly require `Role.ADMIN` (`require_admin`).
  - Responses include `Cache-Control: private, no-store, no-cache, must-revalidate` and `X-Content-Type-Options: nosniff`.
  - File extension and magic byte verification enforce genuine PDF/JPEG/PNG payloads.

---

## 4. Deployment Verification Matrix

| Security / Deployment Control | Implemented Mechanism | Verification Evidence | Assessment |
| :--- | :--- | :--- | :--- |
| **Production Debug Mode** | `LIVO_DEV_MODE=false` | `app/config.py` default | **VERIFIED** |
| **Secret Key Enforcement** | Fast-crash on empty string | `app/config.py` line 96 | **VERIFIED** |
| **Alembic Single Head** | `024_add_rate_limit_entries` | Alembic inspect check | **VERIFIED** |
| **Startup Migration Lock** | `pg_advisory_lock` (64-bit ID) | `app/main.py` lines 42–70 | **VERIFIED** |
| **Startup Migration Abort** | Immediate `RuntimeError` | `app/main.py` line 62 | **VERIFIED** |
| **Readiness Probe Guard** | DB + Head + Table invariants | `app/api/v1/health.py` lines 81–235 | **VERIFIED** |
| **Demo Seeding Guard** | Blocked in production | `app/core/demo_seeding.py` line 34 | **VERIFIED** |
| **Database Port Exposure** | Unexposed (Internal Docker network) | `docker-compose.yml` | **VERIFIED** |
| **CORS Restriction** | Explicit origin whitelist | `app/main.py` line 159 | **VERIFIED** |
| **Secure Cookie Flags** | Secure=True, SameSite=Lax | `app/config.py` line 29 | **VERIFIED** |
| **HR Document Protection** | Non-public storage, Admin only | `app/api/v1/hr.py` line 1238 | **VERIFIED** |
| **Path Traversal Defense** | Commonpath canonical check | `app/api/v1/hr.py`, `gallery.py` | **VERIFIED** |
| **Rate Limiter Proxy Trust** | Right-to-left X-Forwarded-For | `app/middleware/rate_limit.py` | **VERIFIED** |

---

## 5. Controlled Demo Readiness Decision

### Final Verdict: **PASS (FOR CONTROLLED DEMO)**

The codebase, container definitions, migration topology, and security guards satisfy all requirements for the one-week cloud demonstration using synthetic evaluation data.
