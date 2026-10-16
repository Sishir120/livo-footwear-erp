# LIVO Footwear ERP — Day 7.1 Secret & Session Configuration Checklist

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** OWASP Top 10 API Security & Session Management Baseline  
**Evaluation Scope:** Staging & Cloud Demo Preflight Audit

---

## 1. Secret Management & Startup Invariants

| Configuration Key | Runtime Invariant & Code Location | Behavior on Missing / Invalid | Status |
| :--- | :--- | :--- | :---: |
| **`SECRET_KEY`** | Loaded in `app/config.py` lines 20 & 96–102. Strictly validated before FastAPI initializes. | Raises explicit `ValueError` and terminates process. Never falls back to a default secret. | **PASS** |
| **`ENVIRONMENT`** | Loaded in `app/config.py` line 51. Controls `is_production` property (`"production"`, `"prod"`). | Defaults to `"development"`. Rejects demo seeding if set to `"staging"` or `"production"`. | **PASS** |
| **`LIVO_DEV_MODE`** | Loaded in `app/config.py` lines 26–31. Controls `COOKIE_SECURE` property (`not self.LIVO_DEV_MODE`). | If set to `false`, forces `Secure` attribute on all auth cookies and adds HSTS header. | **PASS** |
| **`ENABLE_DEMO_SEEDING`** | Loaded in `app/config.py` line 58. Checked in `app/core/demo_seeding.py`. | Defaults to `false`. When false, skips all demo provisioning. | **PASS** |
| **`DATABASE_URL`** | Loaded in `app/config.py` line 76 and parsed in `app/db/session.py`. | If remote host detected, enforces `sslmode=require`. Passwords in URL sanitized in errors. | **PASS** |

---

## 2. Session & Cookie Security Architecture

1. **Cookie Attributes (`backend/app/api/v1/auth.py` lines 33–39):**
   - **`HttpOnly=True`:** Prevents client-side JavaScript access (`document.cookie`), mitigating XSS session hijacking.
   - **`SameSite=lax`:** Prevents CSRF token leakage across external origins while allowing top-level navigation.
   - **`Secure=True` (when `LIVO_DEV_MODE=false`):** Prohibits transmission over plaintext HTTP.
   - **`Max-Age=86400`:** Enforces 24-hour expiration window.
2. **Session Termination & Invalidation:**
   - Client logout triggers cookie clearing (`Max-Age=0`, empty value).
   - Inactive accounts (`user.active=False`) are blocked at login (`403 Forbidden`) and on subsequent token requests (`get_current_user` rejects inactive users).
3. **Protected Route Authorization:**
   - Unauthenticated requests to protected endpoints return `401 Unauthorized` without exposing user data.
   - Next.js client-side middleware intercepts unauthenticated sessions and redirects to `/login`.

---

## 3. Reverse Proxy & Network Topology Verification

- **Client IP Extraction (`backend/app/middleware/rate_limit.py`):**
  - Peer IP evaluated against `TRUSTED_PROXIES` allowlist.
  - Forwarded headers from untrusted direct peers are ignored to prevent IP spoofing.
  - Trusted proxies traverse `X-Forwarded-For` right-to-left to locate the client origin.
- **CORS Allowed Origins:**
  - `BACKEND_CORS_ORIGINS` strictly enforces comma-separated domain allowlists.
  - Wildcard (`*`) origins are explicitly rejected by configuration schema.
- **Error Response Sanitization:**
  - Database exceptions pass through `_sanitize_db_error` in `app/main.py`.
  - Database connection strings, passwords, and internal tracebacks are stripped before response serialization.

---

## 4. Staging Configuration Template (Placeholders Only)

```bash
# ==============================================================================
# LIVO FOOTWEAR ERP — STAGING EVALUATION ENVIRONMENT
# (All values are placeholders; supply fresh cryptographic random values on host)
# ==============================================================================

# Application Environment
ENVIRONMENT=staging
LIVO_DEV_MODE=false
AUTO_MIGRATE=true

# Cryptographic Key (64-character hex string generated via secrets.token_hex(32))
SECRET_KEY=<FRESH_STAGING_SECRET_KEY_HEX>
ALGORITHM=HS256

# Session & Cookies
COOKIE_SAMESITE=lax

# Network & Proxy
BACKEND_CORS_ORIGINS=https://staging.livogroup.com
TRUSTED_PROXIES=127.0.0.1,10.0.0.0/8,172.16.0.0/12

# Database Connection (PostgreSQL on internal private network)
DATABASE_URL=postgresql://<DB_USER>:<DB_PASSWORD>@<PRIVATE_DB_HOST>:5432/<DB_NAME>?sslmode=require

# Initial One-Time Seeding (Must be 'false' during normal evaluation)
ENABLE_DEMO_SEEDING=false
```
