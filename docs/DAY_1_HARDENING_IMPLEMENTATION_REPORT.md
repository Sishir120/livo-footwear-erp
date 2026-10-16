# Day 1 Backend Hardening Implementation Report

**Date:** 2026-10-16  
**Sprint:** Seven-Day Client Demo Hardening (Day 1 of 7)  
**Execution Environment:** Local Windows Workspace (`d:\Antigravity\Footwear app`), Python 3.14 venv, SQLite / PostgreSQL-compatible schema, Next.js 14.2.35.  
**Branch / HEAD:** `main` @ `2ab515e`  
**Working Tree Integrity:** All 66 pre-existing modified/untracked files preserved intact. Zero git resets, cleans, or destructive changes performed.

---

## 1. Executive Summary

Day 1 hardening focused on closing critical security, cross-worker reliability, and client-server resilience gaps identified during the Tigg comparative audit. All fixes followed minimal-blast-radius principles, introducing zero breaking changes to existing data structures, operational models, or frontend views.

### Confirmed Fixes Completed:
1. **H-01 (Distributed Rate Limiting with Fail-Open Resilience):** Upgraded `BasicRateLimitMiddleware` from an in-process dictionary (`defaultdict(list)`) to a hybrid database-backed store (`RateLimitEntry`). Eliminates the $4\times$ rate limit multiplication vulnerability in multi-worker Uvicorn deployments while providing fail-open fallback to in-memory sliding windows if the database is temporarily unreachable.
2. **H-03 (Content-Security-Policy Header):** Attached strict CSP header to `SecurityHeadersMiddleware`. Formulated explicitly for the LIVO architecture: restricts origins to `'self'`, prevents framing (`frame-ancestors 'none'`), allows Next.js styles, Google Fonts (`fonts.googleapis.com` / `fonts.gstatic.com`), data/blob QR assets, and printable HTML invoice styling.
3. **H-04 (Frontend 401 Auto-Redirect & Session Recovery):** Enhanced `frontend/src/lib/api.ts` to intercept 401 Unauthorized responses from expired or revoked sessions. Prevents UI freezing by routing cleanly to `/login?session_expired=1`, while implementing duplicate-redirect suppression and loop protection. Added bilingual session expiry alert banner to `LoginPage`.
4. **H-08 (Health Readiness Verification):** Verified existing production readiness probe `/health/ready` in `backend/app/api/v1/health.py`, which validates database connectivity, dynamic Alembic head matching, and critical table invariants with HTTP 503 fallback.

---

## 2. Detailed Technical Breakdown by Fix

### Fix 1: H-01 — Distributed Rate Limiting Across Workers

- **Problem & Root Cause:** `BasicRateLimitMiddleware` previously relied on an in-memory dictionary. In multi-worker Uvicorn configurations (`--workers 4`), each process had isolated memory, allowing attackers up to $4 \times 30 = 120$ requests/minute before triggering 429.
- **Implementation Strategy:**
  - Created lightweight `RateLimitEntry` model (`app/models/rate_limit.py`) keyed by client IP, endpoint, and epoch timestamp.
  - Implemented `_check_database_rate_limit()` in `BasicRateLimitMiddleware` to atomically query and insert rate limit events in the shared database.
  - Added fail-open error handling: if the database query fails or times out, it logs a warning and falls back to the in-process sliding window (`self.requests`), guaranteeing zero downtime or 500 errors on database hiccups.
  - Added opportunistic periodic pruning of entries older than 5 windows (~5 minutes) on 5% of requests to prevent table bloat.
  - Retained `BasicRateLimitMiddleware.reset_all()` to clear both in-memory and database entries during test runs.
- **Files Modified/Created:**
  - `backend/app/models/rate_limit.py` (New Model)
  - `backend/app/models/__init__.py` (Model Export)
  - `backend/app/middleware/rate_limit.py` (Middleware Upgrade)
- **Rollback Procedure:** Revert `BasicRateLimitMiddleware` in `rate_limit.py` to in-memory dictionary; drop `rate_limit_entries` table.

---

### Fix 2: H-03 — Strict Content-Security-Policy (CSP) Header

- **Problem & Root Cause:** `SecurityHeadersMiddleware` attached X-Frame-Options, HSTS, and nosniff, but omitted `Content-Security-Policy`. Browser-level XSS mitigation and framing restrictions were incomplete.
- **Implementation Strategy:**
  - Audited frontend resource dependencies: Google Fonts (`Fira Code`, `Inter` in `globals.css`), Next.js client-side script chunks, data/blob URIs for QR codes, and inline CSS for printable invoices (`/invoices/{id}/printable`).
  - Added strict CSP policy:
    ```
    default-src 'self';
    img-src 'self' data: blob: https:;
    style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
    font-src 'self' https://fonts.gstatic.com data:;
    script-src 'self' 'unsafe-inline';
    connect-src 'self';
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
    ```
  - Eliminates framing vectors (`frame-ancestors 'none'` reinforces `X-Frame-Options: DENY`) while strictly bounding network fetches to `'self'`.
- **Files Modified:**
  - `backend/app/middleware/security_headers.py`
- **Rollback Procedure:** Remove the `response.headers["Content-Security-Policy"]` line from `security_headers.py`.

---

### Fix 3: H-04 — Frontend 401 Auto-Redirect & Session Recovery

- **Problem & Root Cause:** `frontend/src/lib/api.ts` previously logged API errors to console and dispatched an event, but left the browser on dead screens when a JWT session expired or was revoked.
- **Implementation Strategy:**
  - In `apiFetch()` response processing, detected `res.status === 401`.
  - Excluded `/auth/login` (which represents invalid credential challenges during login and must not redirect).
  - Excluded requests initiated when `window.location.pathname === "/login"` to prevent redirect loops.
  - Implemented single-flight redirect flag `__LIVO_REDIRECTING_401__` on `window` to prevent duplicate redirect cascades across parallel API requests.
  - Appends `?session_expired=1&return_url=...` to route back after re-authentication.
  - In `frontend/src/app/login/page.tsx`, added a bilingual session-expired notice banner (`EN` and `नेपाली`).
- **Files Modified:**
  - `frontend/src/lib/api.ts`
  - `frontend/src/app/login/page.tsx`
- **Rollback Procedure:** Revert the 401 handling block in `frontend/src/lib/api.ts` and notice state in `login/page.tsx`.

---

### Fix 4: H-08 — Health Readiness Probe Verification

- **Verification:**
  - Inspected `backend/app/api/v1/health.py:81-180`. Confirmed that `/health/ready` evaluates:
    1. Active database connectivity via `SELECT 1`.
    2. Dynamic Alembic head matching between `alembic.ini` revision graph and `alembic_version` table.
    3. Critical table invariants (`companies`, `users`, `invoices`, etc.) and columns.
    4. Returns HTTP 200 with `{ "status": "ready", "database": "healthy" }` when valid; returns HTTP 503 on database disconnect, unmigrated schemas, or conflicting heads.
  - Verified 11 existing test scenarios in `backend/tests/test_phase_16_2_security_remediations.py`.

---

## 3. Changed File Inventory

| File Path | Type | Nature of Change |
|---|---|---|
| `backend/app/models/rate_limit.py` | New File | SQLAlchemy `RateLimitEntry` model with composite index `(key, endpoint, timestamp)` |
| `backend/app/models/__init__.py` | Existing File | Export `RateLimitEntry` |
| `backend/app/middleware/rate_limit.py` | Existing File | Added database-backed rate limit check, table auto-creation, opportunistic cleanup, and fail-open in-memory fallback |
| `backend/app/middleware/security_headers.py` | Existing File | Appended `Content-Security-Policy` header |
| `frontend/src/lib/api.ts` | Existing File | Added 401 Unauthorized session expiration auto-redirect with loop & duplicate suppression |
| `frontend/src/app/login/page.tsx` | Existing File | Added bilingual `session_expired` notification banner |
| `backend/tests/test_day_1_hardening.py` | New File | 6 comprehensive regression tests covering H-01, H-03, H-08, and authorization boundaries |

---

## 4. Remaining Open Findings (Sprint Days 2–7)

| ID | Finding | Tier | Target Day | Planned Resolution |
|---|---|---|---|---|
| **H-02** | 3-role RBAC (`viewer`, `editor`, `admin`) — financial routes require only `editor` | P0 | Days 2–3 | Add `accountant`, `inventory_manager`, `production_manager` roles and capability dependencies |
| **H-05** | Audit log has no field-level snapshotting (`target_table=None`) | P1 | Day 3 | Enrich `AuditLogMiddleware` to record affected entity ID and payload summary |
| **H-06** | Branch-scoped warehouse authorization not enforced on transfer mutations | P1 | Day 4 | Enforce user branch binding on non-admin stock transfer endpoints |
| **H-07** | Separation of duties for journal entries | P1 | Day 5 | Document & prepare role gate for Phase 6B |
| **H-09** | Token version not incremented on password change | P2 | Day 5 | Add `token_version` column to `User` and check in `deps.py` |
| **H-10** | Password reset flow missing | P2 | Day 6 | Add signed email reset token flow |

---

## 5. Phase Readiness Assessment

**Status:** **DAY 1 COMPLETE — SUITABLE FOR NEXT PHASE**  
All Day 1 goals achieved:
- 100% of newly written tests pass (6/6).
- 100% of existing security & compliance tests pass (46/46).
- Frontend Next.js production build succeeded with zero errors.
- Working tree remains completely intact with zero destructive operations.
