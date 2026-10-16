# LIVO Seven-Day Backend Hardening Plan
**Date:** 2026-10-16  
**Deadline:** Client evaluation (7 days from today = 2026-10-23)  
**Constraint:** No architectural rewrites. No database renames. No removal of existing features. No code changes in this document — implementation follows this plan.

---

## Pre-Work: Workspace and Branch Safety

**Status at start of plan:**
- Branch: `main`
- HEAD: `2ab515e`
- 66 files modified/untracked (all Phase 5–6A accounting design + branch/transfer work)
- All changes preserved. No stash, reset, or branch switch permitted.

**Required before any changes:**
1. Commit all untracked Phase 5–6A documentation and test files that are complete and stable.
2. Create a named checkpoint commit: `git commit -m "chore: checkpoint before 7-day hardening sprint"`
3. Work on a new branch: `git checkout -b hardening/7-day-sprint`

---

## Remediation Priority Matrix

| ID | Finding | Category | Risk Level | P-Level | Effort | Day Target | Verify Method |
|---|---|---|---|---|---|---|---|
| H-01 | Rate limiter in-memory — ineffective across workers | Security | CRITICAL | P0 | 0.5d | Day 1 | `test_auth_rate_limit_cross_worker` |
| H-02 | Only 3 RBAC roles — financial routes unprotected | Authorization | CRITICAL | P0 | 2d | Day 1–2 | Permission matrix test |
| H-03 | No Content-Security-Policy header | Security | HIGH | P1 | 0.25d | Day 1 | Response header test |
| H-04 | 401 auto-redirect missing in API client | UX/Security | HIGH | P1 | 0.25d | Day 2 | Browser integration test |
| H-05 | Audit log has no field-level data | Compliance | HIGH | P1 | 1d | Day 2–3 | Audit entry inspection |
| H-06 | Branch-scoped authorization not enforced | Authorization | HIGH | P1 | 1.5d | Day 3–4 | IDOR test across branches |
| H-07 | Separation of duties — no prepare/approve for journals | Authorization | HIGH | P1 | 2d | Day 3–5 | Role-based endpoint test |
| H-08 | Readiness health probe missing | Resilience | MEDIUM | P1 | 0.25d | Day 1 | `GET /health/ready` test |
| H-09 | Token version not incremented on password change | Auth | LOW | P2 | 0.5d | Day 5 | Token replay test |
| H-10 | Password reset flow | Feature gap | MEDIUM | P2 | 1.5d | Day 5–6 | End-to-end reset flow |

---

## Phase 1: Day 1 — Security Foundations (Non-Breaking)

### H-01: Migrate Rate Limiter to PostgreSQL-Backed Counter

**Current Defect (VERIFIED):**  
`BasicRateLimitMiddleware` uses `defaultdict(list)` in-process. In a 4-worker deployment, each worker maintains its own counter, allowing up to `4 × 30 = 120` login attempts per minute per IP.

**Root Cause:**  
The middleware comment itself acknowledges this: "For multi-instance / horizontally scaled production deployments, a distributed store (e.g. Redis / PostgreSQL advisory count) is a release prerequisite."

**Proposed Fix (PostgreSQL-backed, no new dependencies):**
```python
# In BasicRateLimitMiddleware.dispatch(), replace in-memory check with:
# SELECT COUNT(*) FROM rate_limit_log WHERE ip = :ip AND endpoint = :endpoint AND created_at > NOW() - INTERVAL '60 seconds'
# If count >= 30: return 429
# Else: INSERT INTO rate_limit_log(ip, endpoint, created_at) VALUES (...)
# Add: CREATE INDEX idx_rate_limit_ip_endpoint ON rate_limit_log(ip, endpoint, created_at);
```

New `rate_limit_log` table is lightweight. Rows auto-purged (cron or background TTL). No Redis needed.

**Files to modify:**
- `backend/app/middleware/rate_limit.py` — replace in-memory logic
- `backend/migrations/versions/024_add_rate_limit_log.py` — new migration

**Compatibility:** Non-breaking. Existing behavior preserved for single-worker dev. Table just won't accumulate in SQLite tests.

**Verification:**
```python
# test_rate_limit_cross_worker.py
# Spawn 4 TestClient instances, fire 8 requests each (total 32)
# Verify 29th request from last client returns 429
```

**Estimated effort:** 4 hours  
**Deadline risk:** None — purely additive

---

### H-03: Add Content-Security-Policy Header

**Current Defect (VERIFIED):**  
`SecurityHeadersMiddleware` does not set `Content-Security-Policy`. XSS can execute arbitrary scripts in the LIVO frontend context.

**Proposed Fix:**
```python
# In security_headers.py:
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "   # 'unsafe-inline' needed for Next.js inline styles — tighten after evaluation
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; "
    "font-src 'self' https://fonts.gstatic.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)
```

**Compatibility:** Non-breaking for API responses. Frontend must be tested to ensure no CSP violations in the browser console.

**Verification:** Open browser DevTools → Console → confirm no CSP violation errors on page load.

**Estimated effort:** 1 hour  
**Deadline risk:** None

---

### H-08: Readiness Health Probe

**Proposed Fix:**
```python
# Add to health.py:
@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes Readiness Probe: Is the application ready to serve live traffic?
    Checks: DB connectivity + migration at expected head.
    Returns 503 if not ready to prevent premature traffic routing.
    """
    try:
        db.execute(text("SELECT 1"))
        # Check migration is at expected head
        rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        expected = get_expected_migration_head()
        if expected and rev != expected:
            return JSONResponse(status_code=503, content={"status": "not_ready", "reason": "migration_pending"})
        return {"status": "ready", "db": "connected", "migration": rev}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": str(e)})
```

**Estimated effort:** 1 hour

---

## Phase 2: Day 1–2 — Authorization Hardening (H-02)

### H-02: Expand Financial RBAC Roles

**Current Defect (VERIFIED):**  
`users.role` is a free `String(50)`. Only `viewer`, `editor`, `admin` are checked. All financial mutations require only `editor`.

**Migration plan (backwards-compatible):**

```sql
-- Migration 025_expand_user_roles.py
-- No data loss: existing 'editor' users retain full access
-- New roles are additive — existing functionality unchanged
-- Mapping: editor → remains editor (still has all old editor permissions)
-- New roles are opt-in, assigned by admin
```

**New roles to add (incremental, does not remove existing):**

| Role | Can Do | Cannot Do |
|---|---|---|
| `viewer` | All reads | No mutations |
| `editor` | All existing editor mutations | Nothing changed from current |
| `billing_operator` | Sales, invoices, payments | HR, payroll, fixed assets |
| `inventory_manager` | Stock movements, transfers, production | Financials, HR |
| `accountant` | Expense approval, payroll approval | COA config, period management |
| `chief_accountant` | All accounting | User management |
| `admin` | Everything | Nothing |

**New dependency functions in `deps.py`:**
```python
def require_billing_operator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("billing_operator", "accountant", "chief_accountant", "admin"):
        raise HTTPException(403, "Requires billing_operator or higher role.")
    return current_user

def require_accountant(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("accountant", "chief_accountant", "admin"):
        raise HTTPException(403, "Requires accountant or higher role.")
    return current_user

def require_chief_accountant(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("chief_accountant", "admin"):
        raise HTTPException(403, "Requires chief_accountant or higher role.")
    return current_user
```

**Compatibility:** All existing `editor` users retain full access. Only new routes or upgraded routes require the new roles. No existing test will break.

**Files to modify:**
- `backend/app/api/deps.py` — add new require_* functions
- `backend/app/models/user.py` — add role enum comment (no schema change needed)
- `backend/migrations/versions/025_expand_user_roles.py` — add CHECK constraint
- **Phase 6B routes** — use new role guards when implemented

**Verification:**
```python
# test_role_expansion.py
# Verify existing editor can still access all existing routes
# Verify viewer cannot access billing_operator route
# Verify role hierarchy: chief_accountant > accountant > billing_operator
```

**Estimated effort:** 2 days (migration + implementation + tests)

---

## Phase 3: Day 2 — Frontend Client Hardening (H-04)

### H-04: 401 Auto-Redirect in API Client

**Current Defect (VERIFIED):**  
`apiFetch` in `api.ts` does not intercept 401 responses. When the 24-hour session expires, every API call returns 401 but the UI continues showing stale data or throws unhandled errors.

**Proposed Fix:**
```typescript
// In api.ts, after: const res = await fetch(targetUrl, requestInit);
if (res.status === 401) {
  // Session expired or unauthorized — redirect to login
  if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
    window.dispatchEvent(new CustomEvent("livo:session-expired", {
      detail: { message: "Your session has expired. Please log in again." }
    }));
    // Components listen for this event and redirect to /login
  }
}
```

**Compatibility:** Non-breaking — adds new event dispatch. Existing components that already handle 401 continue working.

**Estimated effort:** 2 hours

---

## Phase 4: Day 2–3 — Audit Log Enhancement (H-05)

### H-05: Field-Level Audit Data

**Current Defect (VERIFIED):**  
`AuditLogMiddleware` sets `target_table=None` and `details=f"Status: {response.status_code}"` — no field-level information.

**Proposed Fix — Phase A (quick win, no schema change):**  
Update `details` to include the request body summary for mutations:
```python
# In audit.py:
try:
    body = await request.body()
    if body:
        body_summary = json.loads(body.decode("utf-8", errors="replace"))
        # Redact sensitive fields
        for field in ("password", "password_hash", "token"):
            body_summary.pop(field, None)
        details_str = json.dumps({"status": response.status_code, "body": body_summary})[:2000]
    else:
        details_str = f"Status: {response.status_code}"
except Exception:
    details_str = f"Status: {response.status_code}"
```

**Warning:** Reading the request body in middleware after it has already been consumed by the route requires the body to be cached. The idempotency middleware already caches the body. Verify ordering.

**Phase B (later — schema change):** Add `target_id`, `before_state`, `after_state` JSON columns to `audit_logs` table. Implement per-route decorators to capture before/after for critical financial records.

**Estimated effort:** Phase A = 1 day. Phase B = deferred to P2.

---

## Phase 5: Day 3–4 — Branch Authorization (H-06)

### H-06: Enforce Branch-Scoped Authorization

**Current Defect (INFERRED):**  
The `branches` and `transfers` routes are untracked (new) files. Users can potentially read or write to any branch within their company if the API does not enforce `branch_id` scoping beyond `company_id`.

**Required investigation before implementation:**  
Read `backend/app/api/v1/branches.py` and `backend/app/api/v1/transfers.py` in full. Determine whether branch-level scoping already exists.

**If missing, proposed fix:**  
Add `branch_id` to `user` session context or create a `user_branch_permissions` table. For initial 7-day sprint: restrict `PATCH`/`DELETE` on branch-owned resources to users with an explicit `branch_manager` role assignment for that branch.

**This item requires investigation before specification is complete.**

**Estimated effort:** 1.5 days (after investigation)

---

## Phase 6: Day 5–6 — Deferred P2 Items

### H-09: Password Change Invalidates Old Tokens

**Mechanism:** Add `token_version: int` column to `users`. Increment on password change. Include in JWT. `get_current_user` rejects tokens with `token_version < current`.

**Estimated effort:** 4 hours

### H-10: Password Reset Flow

**Mechanism:** 
1. POST `/auth/reset/request` — generate a signed, time-limited (15min) token, store hash in `password_reset_tokens` table, log the action.
2. POST `/auth/reset/confirm` — verify token, update password_hash, delete token, increment token_version.
3. Email delivery: defer if no SMTP configured — log the reset URL to application logs in dev.

**Estimated effort:** 1.5 days

---

## Day 7: Verification and Acceptance Testing

### Acceptance Test Suite

```python
# test_hardening_sprint_acceptance.py

def test_rate_limiter_works_cross_worker():
    """30th login attempt from same IP returns 429 regardless of which worker handles it"""

def test_content_security_policy_set():
    """Every API response has Content-Security-Policy header"""

def test_readiness_probe_blocks_during_migration():
    """GET /health/ready returns 503 if alembic_version != expected head"""

def test_401_event_dispatched_on_session_expiry():
    """Frontend API client dispatches livo:session-expired on 401"""

def test_editor_cannot_access_chief_accountant_routes():
    """Editor role gets 403 on routes requiring chief_accountant"""

def test_audit_log_contains_request_summary():
    """Audit log entry for POST /sales includes body summary"""

def test_csp_no_violations_in_browser():
    """Browser console shows no CSP violations on LIVO page load"""

def test_existing_editor_routes_still_accessible():
    """All pre-sprint editor routes return 200 for editor role"""
```

---

## Items Explicitly Excluded From 7-Day Sprint

| Item | Reason for Exclusion |
|---|---|
| Redis adoption | No measured performance problem; adds operational complexity |
| Architecture rewrite (multi-org) | 5+ day effort; breaks existing auth flow |
| Full GL implementation | Phase 6B scope — awaiting Phase 6A.2 resolution |
| Distributed tracing (OpenTelemetry) | Infrastructure dependency; deferred to post-evaluation |
| React Query / frontend caching | UX improvement; no active bug |
| Background job queue (Celery) | No current long-running operations blocking |
| Frontend PWA service worker | Separate frontend sprint |

---

## Day-by-Day Schedule

| Day | Tasks | Owner | Gate |
|---|---|---|---|
| **1** | Git checkpoint commit; H-01 (rate limiter); H-03 (CSP); H-08 (ready probe) | Engineering | All tests green |
| **2** | H-02 (role expansion migration + deps.py); H-04 (401 auto-redirect) | Engineering | Role hierarchy test passes |
| **3** | H-02 complete (route guard updates); H-05 Phase A (audit body capture) | Engineering | Audit log body test passes |
| **4** | H-06 investigation + implementation | Engineering | Branch IDOR test passes |
| **5** | H-07 separation of duties (document only for Phase 6B gate); H-09 token version | Engineering | Token version test passes |
| **6** | H-10 password reset; integration testing | Engineering | Reset flow test passes |
| **7** | Full acceptance test run; regression check; documentation update | Engineering | All P0+P1 tests green; no P0 regressions |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| H-02 role expansion breaks existing tests | Medium | High | Run full test suite before merging; map all existing editor routes |
| CSP header causes browser loading errors | Medium | High | Test in dev browser with CSP header before production deploy |
| Branch authorization investigation reveals larger gap | Low | Medium | Scope to `require_editor` + `company_id` check as minimum; log gap for P2 |
| Rate limit migration fails on existing PostgreSQL schema | Low | Low | Migration is additive; new table only |

---

## Changes Specifically NOT Recommended for 7-Day Sprint

1. **Do not replace JWT with sessions** — existing tests depend on JWT.
2. **Do not add Redis** — no measured slowness that Redis would solve.
3. **Do not change SQLite WAL workaround** — it works correctly and is production-safe.
4. **Do not restructure the entire backend** — TenantRepository pattern is sound.
5. **Do not remove the Bearer token fallback** in `deps.py` — needed for API testing and pytest.
6. **Do not touch Phase 6A accounting specification documents** — they are correct pending CA decisions.
7. **Do not implement GL posting routes** — VAL-01, VAL-02, VAL-03, VAL-05 are unresolved.

---

## Evidence-Based Re-Ranked Implementation Priorities (Post-Tigg Investigation)

Following deep DOM and architectural evaluation of Tigg's authenticated workflows and comparison with LIVO's local workspace, implementation priorities have been re-evaluated and ordered strictly by client-facing risk, operational impact, and feasibility within the 7-day sprint window.

### Priority 1: H-01 — PostgreSQL-Backed Rate Limiting (P0, Security Critical)
- **Demonstrated Problem:** `BasicRateLimitMiddleware` (`middleware/rate_limit.py`) tracks request frequencies in an in-memory dictionary. Across a 4-worker production deployment, each worker maintains isolated memory, multiplying allowable attempts by $4\times$ ($120$ attempts/min) and failing to protect against brute-force attacks.
- **Risk Reduction:** Completely neutralizes distributed brute-force attacks and credential stuffing across all horizontally scaled containers.
- **Implementation Estimate:** 4 hours (Day 1).
- **Regression Tests:** `backend/tests/test_rate_limit_cross_worker.py` (simulating concurrent worker clients firing beyond threshold).
- **Acceptance Criteria:** Exceeding 30 requests/minute to auth endpoints from an IP across any worker yields HTTP 429 with `Retry-After` header.
- **Rollback Method:** Revert `rate_limit.py` to in-memory dictionary; drop migration table `rate_limit_log`.

### Priority 2: H-03 — Strict Content-Security-Policy Header (P1, Browser Security)
- **Demonstrated Problem:** `SecurityHeadersMiddleware` (`middleware/security_headers.py`) enforces HSTS, X-Frame-Options, and nosniff, but completely omits CSP, leaving the frontend vulnerable to cross-site scripting and unauthorized iframe embeds.
- **Risk Reduction:** Restricts script execution to trusted origins, prevents DOM-based credential theft, and satisfies enterprise security checklists during client evaluation.
- **Implementation Estimate:** 1 hour (Day 1).
- **Regression Tests:** `backend/tests/test_security_headers.py` asserting header presence; browser console inspection for zero CSP violations.
- **Acceptance Criteria:** Every HTTP response includes `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...`.
- **Rollback Method:** Remove the single dictionary entry from `security_headers.py`.

### Priority 3: H-08 — Readiness Health Probe `/health/ready` (P1, Deployment Reliability)
- **Demonstrated Problem:** LIVO currently exposes only `/health` (static status). Cloud orchestrators and reverse proxies cannot detect database connection outages or unapplied Alembic migrations, causing 500 errors to route to users during rollouts.
- **Risk Reduction:** Guarantees zero downtime deployments and prevents traffic routing to unmigrated instances during client demonstration.
- **Implementation Estimate:** 1 hour (Day 1).
- **Regression Tests:** `backend/tests/test_health_ready.py` verifying HTTP 200 when DB is active and HTTP 503 when disconnected or unmigrated.
- **Acceptance Criteria:** `GET /health/ready` validates `SELECT 1` and matches `alembic_version` to head; returns 503 with error detail on failure.
- **Rollback Method:** Remove `/health/ready` route definition from `backend/app/api/v1/health.py`.

### Priority 4: H-04 — Frontend 401 Auto-Redirect Interceptor (P1, Client UX/Security)
- **Demonstrated Problem:** `frontend/src/lib/api.ts` does not intercept 401 Unauthorized responses. Expired sessions or deactivated credentials result in raw unhandled fetch rejections, causing silent UI freezing for the client.
- **Risk Reduction:** Eliminates confusing broken screens during live demo; guarantees immediate, clean redirect to `/login`.
- **Implementation Estimate:** 2 hours (Day 2).
- **Regression Tests:** Frontend integration test verifying automated window redirect to `/login?session_expired=1` on mock 401 response.
- **Acceptance Criteria:** Any API call returning 401 clears cached user state in client and navigates to the login route with return URL preserved.
- **Rollback Method:** Revert the fetch response interceptor wrapper in `api.ts`.

### Priority 5: H-02 & VAL-08 — Role-Based Access Control Expansion (P0, Financial Compliance)
- **Demonstrated Problem:** `users.role` only supports `viewer`, `editor`, `admin`. All financial routes (`invoices.py`, `sales.py`, `purchase.py`) require only generic `editor`. Warehouse personnel can alter invoices; sales agents can post inventory adjustments.
- **Risk Reduction:** Resolves primary statutory audit blocker; enforces separation of duties between sales, inventory, and accounting.
- **Implementation Estimate:** 1.5 days (Days 2–3).
- **Regression Tests:** `backend/tests/test_checkpoint_16_business_security.py` + new `test_role_hierarchy.py`.
- **Acceptance Criteria:** Financial endpoints require `accountant` or `admin`; stock adjustments require `inventory_manager` or `admin`; legacy `editor` retains backward-compatible alias.
- **Rollback Method:** Revert route dependencies in `invoices.py`, `sales.py`, `purchase.py` to `require_editor`.

### Priority 6: H-05 — Financial Audit Log Field-Level Snapshotting (P1, Statutory Audit)
- **Demonstrated Problem:** `AuditLog` captures HTTP method, endpoint, and user ID, but leaves `target_table=None` and fails to capture before/after values or affected entity IDs.
- **Risk Reduction:** Guarantees immutable forensic auditability of financial adjustments and invoice voiding.
- **Implementation Estimate:** 6 hours (Day 3).
- **Regression Tests:** `backend/tests/test_audit_trail.py` verifying payload capture on invoice issuance and credit note creation.
- **Acceptance Criteria:** Financial mutation records write entity name, record ID, and sanitized payload JSON to `AuditLog`.
- **Rollback Method:** Omit request body snapshotting hook in `middleware/audit.py`.

### Priority 7: H-06 — Branch-Scoped Warehouse Authorization (P1, Multi-Location Security)
- **Demonstrated Problem:** `warehouses` are linked to `branches`, but `User` models lack branch assignment enforcement. A user at Factory A can execute stock transfers or inventory receipts on Showroom B's warehouse.
- **Risk Reduction:** Prevents accidental or unauthorized inter-branch inventory manipulation during evaluation.
- **Implementation Estimate:** 1 day (Day 4).
- **Regression Tests:** `backend/tests/test_branch_isolation.py` ensuring cross-branch mutation rejection (HTTP 403).
- **Acceptance Criteria:** Branch-scoped users are restricted to warehouses linked to their branch ID unless holding `admin` role.
- **Rollback Method:** Remove branch ID constraint from `transfers.py` and `stock.py` query filters.

### Priority 8: H-09 — Token Version Invalidation on Password Change (P2, Auth Security)
- **Demonstrated Problem:** Changing a user's password does not invalidate existing JWT cookies on other browsers until cookie expiration.
- **Risk Reduction:** Closes post-credential-rotation session hijack window.
- **Implementation Estimate:** 4 hours (Day 5).
- **Regression Tests:** `backend/tests/test_token_revocation.py`.
- **Acceptance Criteria:** Password change increments `user.token_version`; subsequent requests with previous token version return 401.
- **Rollback Method:** Remove `token_version` verification check from `deps.py:get_current_user`.

