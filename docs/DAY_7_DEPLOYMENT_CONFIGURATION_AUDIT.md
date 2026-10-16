# LIVO Footwear ERP — Day 7 Deployment Configuration Audit

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Cloud Demo Security Baseline & OWASP Top 10 API Security Controls  
**Demonstration Scope:** Controlled 1-Week Synthetic Evaluation

---

## 1. Executive Summary

This configuration audit inspects the startup mechanisms, security controls, cookie invariants, CORS topologies, and migration behaviors across the application code. All configuration values were traced directly into Python runtime logic and validated with automated regression checks.

---

## 2. Environment Configuration Matrix

| Parameter | Local Development | Controlled Cloud Demo (Staging) | Production Mode | Verified Invariant |
| :--- | :--- | :--- | :--- | :--- |
| **`ENVIRONMENT`** | `development` | `development` / `test` | `production` | Production mode rejects demo seeding fail-closed |
| **`LIVO_DEV_MODE`** | `true` | `false` | `false` | `false` forces `COOKIE_SECURE=True` & HSTS header |
| **`ENABLE_DEMO_SEEDING`** | `true` (opt-in) | `true` (init only, then `false`) | `false` (hard rejection) | Refuses to execute if `is_production` is True |
| **`SECRET_KEY`** | Local dev key | Cryptographic random 64-hex | Secret Manager secret | App crashes on startup if key is empty |
| **`DATABASE_URL`** | `sqlite:///./livo_dev.db` | Hosted PostgreSQL (internal) | Managed PostgreSQL (HA) | `sslmode=require` enforced on non-local hosts |
| **`COOKIE_SECURE`** | `false` | `true` | `true` | Cookies require HTTPS in staging & prod |
| **`COOKIE_SAMESITE`** | `lax` | `lax` | `lax` (or `strict`) | Prevents cross-site cookie injection |
| **`BACKEND_CORS_ORIGINS`**| `http://localhost:3000` | Staging domain only | Production domain only | Wildcards (`*`) strictly disallowed |
| **`TRUSTED_PROXIES`** | `127.0.0.1, ::1` | Caddy / ALB Private CIDR | Cloudflare / WAF IPs | Right-to-left X-Forwarded-For verification |
| **`AUTO_MIGRATE`** | `true` | `true` | `false` (CI/CD gated) | Startup aborts on migration failure |
| **DB Port Ingress** | Loopback only | Private VPC only (No 5432) | Private VPC only (No 5432) | Database is not publicly reachable |

---

## 3. Code-Level Safeguard Verification

### 3.1. Demo Account Seeding Fail-Closed Guard
- **Source:** `backend/app/core/demo_seeding.py` lines 23–36
- **Test Executed:**
  ```python
  with patch.object(settings, 'ENABLE_DEMO_SEEDING', True):
      with patch.object(settings, 'ENVIRONMENT', 'production'):
          res = seed_demo_users_if_enabled(mock_db, mock_co)
  ```
- **Observed Result:** Emitted critical alert `[SEC-01 ALERT] Demo account seeding was requested but ENVIRONMENT='production' is not positively identified as non-production. Refusing to seed demo credentials (fail closed)!` and returned `{'status': 'rejected', 'reason': 'production_mode_refusal'}`.

### 3.2. Mandatory `SECRET_KEY` Startup Crash
- **Source:** `backend/app/config.py` lines 96–102
- **Rule:** If `SECRET_KEY` is empty, a `ValueError` is raised immediately before the FastAPI app instantiates. No default key is used.

### 3.3. Secure Cookie Invariant
- **Source:** `backend/app/config.py` lines 28–32 & `backend/app/api/v1/auth.py` lines 33–39
- **Rule:** `COOKIE_SECURE` evaluates to `not self.LIVO_DEV_MODE`. In any cloud staging or production setup where `LIVO_DEV_MODE=false`, the session cookie is stamped `Secure; HttpOnly; SameSite=lax`.

### 3.4. Reverse Proxy IP Verification
- **Source:** `backend/app/middleware/rate_limit.py` lines 34–60
- **Rule:** Client IP spoofing via injected `X-Forwarded-For` headers is blocked. Untrusted peer connections ignore forwarded headers; trusted proxies use right-to-left traversal to locate the first untrusted upstream IP.

### 3.5. Migration Failure Propagation
- **Source:** `backend/app/main.py` lines 58–62
- **Rule:** Migration errors caught during `command.upgrade(alembic_cfg, "head")` raise an explicit `RuntimeError`, immediately terminating the process before any HTTP endpoint can accept traffic.
