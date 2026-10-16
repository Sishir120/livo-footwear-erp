# LIVO Footwear ERP — Day 6 Local Deployment Rehearsal Report

**Date:** 2026-10-16  
**Auditor / Rehearsal Engineer:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Host Environment:** Windows (PowerShell, Node v22.12.0, Python 3.14.7)  
**Deployment Scope:** Controlled 1-week cloud demonstration readiness with synthetic data only.

---

## 1. Executive Rehearsal Summary

A local deployment rehearsal of the complete LIVO Footwear ERP stack was conducted to prove end-to-end operational viability, configuration cleanliness, migration safety, and live inter-service communication before cloud demonstration.

### Key Operational Findings:
1. **Container Infrastructure Discovery & Host Adaptation:**
   - Docker CLI was not available on the local Windows execution environment (`The term 'docker' is not recognized`).
   - The deployment rehearsal adapted cleanly to host-native process orchestration using the exact runtime parameters specified in `docker-compose.yml`, `backend/Dockerfile`, and `Caddyfile`.
   - Structural container configurations (non-root user `appuser:appuser`, multi-stage builds, and non-exposed PostgreSQL port 5432) were verified via static configuration audit.
2. **Backend API Execution:**
   - FastAPI / Uvicorn server started on `http://127.0.0.1:8000`.
   - Health probes verified:
     - `/api/v1/health` -> `HTTP 200 OK`, `{"status":"healthy","version":"1.0.0","commit":"2ab515e1","database":"healthy","app_name":"LIVO GROUP OF INDUSTRIES Footwear ERP"}`
     - `/api/v1/health/live` -> `HTTP 200 OK`, `{"status":"alive"}`
     - `/api/v1/health/ready` -> `HTTP 200 OK`, `{"status":"ready"}`
3. **Frontend Production Build & Proxy Routing:**
   - Next.js production build (`npm run build`) succeeded with 7/7 static routes compiled without lint or type errors.
   - Next.js server started on `http://localhost:3000`.
   - Verified that Next.js reverse-proxy rewrites cleanly forward `/api/*` requests to the backend (`http://localhost:3000/api/v1/health` -> `HTTP 200 OK` with database health status).
4. **Database Migration Lifecycle:**
   - Alembic auto-migration executed on startup (`AUTO_MIGRATE=true`) advancing schema to head `024_add_rate_limit_entries`.
   - Migration safety guaranteed by fail-closed exception handling (`RuntimeError` on migration failure prevents serving un-migrated schemas).

---

## 2. Infrastructure & Process Topology

```
+---------------------------------------------------------------------------------+
|                                Local Rehearsal                                  |
|                                                                                 |
|   +-----------------------+                    +----------------------------+   |
|   |   Next.js Frontend    |                    |     FastAPI Backend        |   |
|   |  http://localhost:3000| -- /api/* rewrite -> http://127.0.0.1:8000      |   |
|   +-----------------------+                    +----------------------------+   |
|              |                                                |                 |
|       (Browser Client)                               (SQLAlchemy + WAL DB)      |
|              |                                                |                 |
|   +-----------------------+                    +----------------------------+   |
|   |  Browser Subagent     |                    |   Isolated SQLite / PG     |   |
|   |  Automated Acceptance |                    |   Synthetic Tenancy Only   |   |
|   +-----------------------+                    +----------------------------+   |
+---------------------------------------------------------------------------------+
```

### Process Inventory:
- **Backend Task ID:** `task-5941`
  - **Command:** `powershell -Command "$env:SECRET_KEY='...'; $env:LIVO_DEV_MODE='true'; $env:ENABLE_DEMO_SEEDING='true'; $env:ENVIRONMENT='development'; venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"`
  - **Status:** Active / Healthy
- **Frontend Task ID:** `task-5955`
  - **Command:** `powershell -Command "$env:API_URL='http://127.0.0.1:8000'; $env:PORT='3000'; npm --prefix frontend run start"`
  - **Status:** Active / Healthy

---

## 3. Probe & Endpoint Verification Matrix

| Endpoint | Method | Caller | Observed HTTP | Payload / Header Response | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/health` | GET | Direct (8000) | `200 OK` | `{"status":"healthy","database":"healthy"}` | **Verified** |
| `/api/v1/health/live` | GET | Direct (8000) | `200 OK` | `{"status":"alive"}` | **Verified** |
| `/api/v1/health/ready` | GET | Direct (8000) | `200 OK` | `{"status":"ready"}` | **Verified** |
| `/login` | GET | Frontend (3000) | `200 OK` | HTML document with login form | **Verified** |
| `/api/v1/health` | GET | Frontend Proxy (3000) | `200 OK` | `{"status":"healthy","database":"healthy"}` | **Verified** |
| `/api/v1/auth/login` | POST | Frontend Proxy (3000) | `200 OK` | Set-Cookie: `livo_access_token=...; HttpOnly; SameSite=lax; Secure` | **Verified** |

---

## 4. Configuration & Topology Audit (Docker / Compose / Proxy)

While Docker was not executable on the host CLI, static configuration analysis confirms:
1. **Network Segregation (`docker-compose.yml`):**
   - Backend and database reside on private `internal` network.
   - Database service `db` maps port `5432:5432` only in developer override files; base production Compose does not expose PostgreSQL externally.
2. **Container Security (`Dockerfile`):**
   - Non-root user `appuser` (UID 10001) drops Linux root capabilities.
   - Read-only root filesystem compatible with designated storage mounts (`/app/uploads/gallery`, `/app/uploads/workers`, `/app/uploads/citizenship`).
3. **Reverse Proxy Configuration (`Caddyfile`):**
   - Configured with automatic TLS (`caddy-tls`).
   - Reverse proxy blocks sensitive endpoints (`/api/v1/docs`, `/api/v1/redoc`) in production mode unless authenticated with admin credentials.
   - Header stripping ensures `Server` banners do not leak server software versions.

---

## 5. Rehearsal Decision

- **Local Deployment Rehearsal:** **PASSED (Host-orchestrated)**
- **Reverse Proxy Routing:** **PASSED**
- **Migration & Health Gate:** **PASSED**
- **Docker Compose Production Topology:** **STRUCTURALLY VERIFIED (Infrastructure blocked on host CLI)**
