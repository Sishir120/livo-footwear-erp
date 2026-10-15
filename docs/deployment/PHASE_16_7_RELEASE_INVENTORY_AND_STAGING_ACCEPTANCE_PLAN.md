# LIVO FOOTWEAR ERP — PHASE 16.7: Release Inventory, Candidate Integrity & Staging Acceptance Plan

**Date:** 2026-10-14  
**Roles:** Senior Release Engineer, Application Security Engineer, DevOps Architect, QA Lead  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Working Directory:** `D:\Antigravity\Footwear app`  
**Document Status:** AUDIT & PLANNING COMPLETE — RELEASE CANDIDATE STAGED FOR OWNER REVIEW (DEPLOYMENT HALTED)

---

## 1. Executive Summary & Verified Baseline

In strict accordance with the mandatory safety boundaries, an independent baseline inspection was conducted before analyzing release scope or planning staging acceptance.

### 1.1 Verified Git & Repository Baseline
- **Current Active Branch:** `release/v1.0.0-staging`
- **Current Local `HEAD` SHA:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
- **Remote Tracking Reference (`origin/release/v1.0.0-staging`):** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` (MATCH CONFIRMED: 0 commits ahead, 0 commits behind)
- **Primary Trunk Reference (`origin/main`):** `aab3d4a1ff54a0b9dca530569961458b1e356a8a`
- **Branch Commit Offset:** `origin/release/v1.0.0-staging` is ahead of `origin/main` by exactly 2 packaged commits:
  1. `5caa3f4 Fix float/Decimal type mismatch across API endpoints`
  2. `47cf8f5 feat(release): package Phase 1-15 client enhancements, migrations 010-020, and staging infrastructure`
- **Working-Tree Status:** 13 tracked files modified, 14 untracked files/directories present. Zero files were staged, committed, pushed, or discarded.

### 1.2 Working-Tree Diff Summary
```
 .env.example                                       |   5 +
 .env.staging.example                               |   5 +
 .gitignore                                         |   1 +
 README.md                                          |  18 +++-
 backend/app/api/v1/health.py                       |   5 +-
 backend/app/config.py                              |  31 ++++++
 backend/app/main.py                                | 116 +++++++--------------
 backend/app/middleware/rate_limit.py               |  84 +++++++++++++--
 .../tests/test_checkpoint_15_query_regression.py   |  35 ++++++-
 docs/CLIENT_PITCH_CHEATSHEET.md                    |   8 +-
 docs/deployment/STAGING_DEPLOYMENT_GUIDE.md        |   2 +-
 frontend/src/app/login/page.tsx                    |  52 ++-------
 render.yaml                                        |   6 ++
 13 files changed, 221 insertions(+), 147 deletions(-)
```

---

## 2. Workstream A — Exact Release-File Inventory & Classification

Every modified tracked file and untracked file was systematically inspected to verify its operational purpose, assess sensitive data risk, and establish whether it belongs in the staging release candidate.

### 2.1 Tracked Modified Files (13 Entries)

| File Path | Status | Operational Purpose | Staging Need | Sensitive Data Risk | Proposed Action | Evidence & Decision Rationale |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| `.env.example` | M | Reference environment template | YES | NONE | **Include** | Documents `ENABLE_DEMO_SEEDING`, `AUTO_MIGRATE`, `TRUSTED_PROXIES`. Contains placeholders only. |
| `.env.staging.example` | M | Staging deployment configuration template | YES | NONE | **Include** | Contains staging placeholders (`replace_with_*`). Verified zero real secrets or database URLs. |
| `.gitignore` | M | Git exclusion rules | YES | NONE | **Include** | Adds `.kilo/` under `# IDE & OS` to prevent local agent/IDE state pollution. |
| `README.md` | M | Project documentation & quickstart | YES | NONE | **Include** | Documents production security rules, staging deployment flow, and verification instructions. |
| `backend/app/api/v1/health.py` | M | Health, liveness, and readiness probes | YES | NONE | **Include** | Adds `commit: settings.BUILD_COMMIT` to `/health`, `/health/live`, `/health/ready`. Truncated to 8 chars. |
| `backend/app/config.py` | M | Central application configuration | YES | NONE | **Include** | Implements `BUILD_COMMIT`, `ENVIRONMENT`, `ENABLE_DEMO_SEEDING`, `AUTO_MIGRATE`, `TRUSTED_PROXIES`, and fail-fast `SECRET_KEY` check. |
| `backend/app/main.py` | M | ASGI startup lifecycle & routers | YES | NONE | **Include** | Enforces fail-fast `RuntimeError` on migration failure, adds `_migration_lock`, removes hardcoded demo seeding. |
| `backend/app/middleware/rate_limit.py` | M | Auth rate limiter & IP extraction | YES | NONE | **Include** | Implements RFC 7239 compliant right-to-left `X-Forwarded-For` traversal with `TRUSTED_PROXIES` whitelist. |
| `backend/tests/test_checkpoint_15_query_regression.py` | M | Query count & pagination regression suite | YES | NONE | **Include** | Updated to assert expanded health check attributes without altering query thresholds. |
| `docs/CLIENT_PITCH_CHEATSHEET.md` | M | Client demo narrative & pitch guide | YES | LOW (Demo only) | **Include** | References non-production synthetic roles; contains no live credentials. |
| `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md` | M | Deployment runbook for staging | YES | NONE | **Include** | Clean deployment steps for Render and Vercel. Zero live secrets. |
| `frontend/src/app/login/page.tsx` | M | Public authentication page | YES | NONE | **Include** | Removes hardcoded one-click demo user credentials and autofill buttons. |
| `render.yaml` | M | Staging infrastructure blueprint | YES | NONE | **Include** | Declares `ENVIRONMENT=staging`, `AUTO_MIGRATE=true`, `TRUSTED_PROXIES="127.0.0.1,::1"`. |

### 2.2 Untracked Files and Directories (14 Entries)

| File / Directory Path | Operational Purpose | Staging Need | Sensitive Data Risk | Proposed Action | Evidence & Decision Rationale |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `.github/workflows/scheduled_backup.yml` | Nightly automated PostgreSQL backup workflow | YES | NONE | **Include** | Syntactically verified; references `${{ secrets.STAGING_DATABASE_URL }}` securely. |
| `backend/app/core/demo_seeding.py` | Isolated demo user provisioning module | YES | LOW (Default passwords) | **Include** | Strictly gated by `ENABLE_DEMO_SEEDING=true` and rejected in `production` mode. |
| `backend/scripts/create_admin.py` | CLI administrative user creation script | YES | NONE | **Include** | Interactive secure password prompting via `getpass`; zero hardcoded credentials. |
| `backend/tests/test_phase_16_2_security_remediations.py` | Remediation test suite (12 tests) | YES | NONE | **Include** | Covers demo seeding refusal, migration aborts, IP spoofing resistance, evasion tests, and deployment identity. |
| `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md` | Operational runbook for GitHub Actions backups | YES | NONE | **Include** | Operational instructions for owner secret provisioning and restore drills. |
| `docs/deployment/PHASE_16_1_RELEASE_VERIFICATION_REPORT.md` | Historical Phase 16.1 audit report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker build context by `.dockerignore`. |
| `docs/deployment/PHASE_16_2_SECURITY_REMEDIATION_REPORT.md` | Historical Phase 16.2 remediation report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/PHASE_16_3_INDEPENDENT_VERIFICATION_REPORT.md` | Historical Phase 16.3 audit report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/PHASE_16_4_RELEASE_CONFIGURATION_REMEDIATION_REPORT.md` | Historical Phase 16.4 remediation report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/PHASE_16_5_INDEPENDENT_PREDEPLOYMENT_GATE_REPORT.md` | Historical Phase 16.5 pre-deploy audit | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/PHASE_16_6_STAGING_BLOCKER_REMEDIATION_REPORT.md` | Historical Phase 16.6 remediation report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/PHASE_16_RELEASE_EXECUTION_REPORT.md` | Historical Phase 16.0 release execution report | NO | NONE | **Retain Locally / Doc Only** | Audit documentation; excluded from Docker context. |
| `docs/deployment/systemd/` | Linux VPS backup service/timer unit files | OPTIONAL | NONE | **Retain as Reference** | Standalone VPS alternative templates; not used in Render staging. |
| `scripts/cloud_backup.sh` | Logical PostgreSQL backup engine | YES | NONE | **Include** | Bash script using flock, SHA-256 validation, and credential redaction. |

### 2.3 Proposed Release Allowlist (To Stage for Commit by Owner)
```
.env.example
.env.staging.example
.gitignore
README.md
backend/app/api/v1/health.py
backend/app/config.py
backend/app/core/demo_seeding.py
backend/app/main.py
backend/app/middleware/rate_limit.py
backend/scripts/create_admin.py
backend/tests/test_checkpoint_15_query_regression.py
backend/tests/test_phase_16_2_security_remediations.py
frontend/src/app/login/page.tsx
render.yaml
.github/workflows/scheduled_backup.yml
scripts/cloud_backup.sh
docs/CLIENT_PITCH_CHEATSHEET.md
docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md
docs/deployment/STAGING_DEPLOYMENT_GUIDE.md
```

### 2.4 Explicit Release Exclusions
- `.kilo/` (Local IDE scratch directory — ignored by `.gitignore`)
- `docs/deployment/PHASE_16_*_REPORT.md` (Audit artifacts — retained in repository history, excluded from container build context)
- `docs/deployment/systemd/` (VPS backup alternative templates — retained in repository docs, excluded from container build context)
- `backend/staging_pgdata/`, `staging_pgdata/` (Local PostgreSQL data — ignored by `.gitignore`)
- `backend/*.db`, `*.sqlite3` (Local test databases — ignored by `.gitignore`)
- `logs/`, `backend/logs/` (Local log files — ignored by `.gitignore`)

---

## 3. Workstream B — Candidate Integrity Assessment

### 3.1 Comparison of Repository References
- **Local `HEAD`:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
- **Remote `origin/release/v1.0.0-staging`:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
- **Integrity Status:** The local commit graph perfectly matches the remote release branch. There is no commit divergence.

### 3.2 Evaluation of Working-Tree Modifications vs. Committed State
- The 13 modified files and 4 core untracked code/test files (`demo_seeding.py`, `create_admin.py`, `test_phase_16_2_security_remediations.py`, `scheduled_backup.yml`, `cloud_backup.sh`) exist **only in the local working tree**.
- **Crucial Finding:** The deployed live backend on Render (`https://livo-footwear-erp-backend.onrender.com`) is running the un-remediated revision `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` committed during Phase 16. It does **not** yet contain the Phase 16.2–16.6 remediations because those changes have not been committed or pushed.
- Prior audit claims in Phase 16.1 through 16.6 correctly distinguished local remediation from live staging state.
- The release candidate can be fully reconstructed from the explicit allowlist above without risk of data loss.

---

## 4. Workstream C — Deployment Identity Verification Plan

### 4.1 Deployment Identity Architecture
- **Injected Variable:** Render automatically injects `RENDER_GIT_COMMIT` into both Docker build contexts and runtime container environments for web services deployed from a Git repository.
- **Application Resolution (`backend/app/config.py`):**
  ```python
  BUILD_COMMIT: str = (
      os.getenv("BUILD_COMMIT")
      or os.getenv("RENDER_GIT_COMMIT")
      or os.getenv("GIT_COMMIT")
      or "dev"
  )[:8]
  ```
- **Exposure Endpoints:**
  - `GET /api/v1/health` $\rightarrow$ `{"status": "healthy", "version": "1.0.0", "commit": "<sha>", "database": "healthy", "app_name": "..."}`
  - `GET /api/v1/health/live` $\rightarrow$ `{"status": "alive", "version": "1.0.0", "commit": "<sha>", "app_name": "..."}`
  - `GET /api/v1/health/ready` $\rightarrow$ `{"status": "ready", "database": "healthy", "version": "1.0.0", "commit": "<sha>"}`

### 4.2 Failure & Security Analysis
- **Fallback Behavior:** If `RENDER_GIT_COMMIT`, `BUILD_COMMIT`, and `GIT_COMMIT` are unset, `BUILD_COMMIT` defaults to `"dev"`. A response of `"dev"` indicates that commit identity was **not** populated by the hosting provider.
- **Safety:** Truncation to 8 characters ensures that no internal hashes, full tokens, or environment data can be leaked.
- **Staging Acceptance Test:** Following an authorized release push, the owner queries `/api/v1/health` and verifies that `"commit"` matches the short SHA of the newly pushed candidate commit. If `"commit"` is `"dev"` or matches the older `47cf8f58`, the deployment is rejected.

---

## 5. Workstream D — Migration and Startup Safety Assessment

### 5.1 Startup Migration Lifecycle
1. When the container boots, `lifespan(app)` executes in `backend/app/main.py`.
2. If `AUTO_MIGRATE=true`, it acquires `_migration_lock = threading.Lock()`.
3. Alembic executes `command.upgrade(alembic_cfg, "head")`.
4. **Fail-Safe Mechanism:** If Alembic encounters an error (e.g. database connection timeout, locked table, schema conflict), it logs `FATAL: Database migration failed during application startup` and executes:
   ```python
   raise RuntimeError(f"Database migration failure: {e}") from e
   ```
5. Raising `RuntimeError` during lifespan crashes Uvicorn immediately with exit code 1. The container fails its container health probe (`HEALTHCHECK` in Dockerfile), and Render does not route incoming traffic to the container.

### 5.2 Thread Lock vs. Multi-Worker / Multi-Instance Boundaries
- **In-Process Lock:** `_migration_lock` protects concurrent threads inside one Python process. It does **not** protect against independent OS processes (e.g. Uvicorn `--workers > 1`) or independent container replicas.
- **Render Free Tier Hosting Limits:**
  - `render.yaml` specifies `plan: free`.
  - Render Free plan enforces **exactly 1 web service instance** (no horizontal scaling).
  - `backend/Dockerfile` runs `uvicorn app.main:app` with a single worker process.
  - Therefore, multi-process and multi-instance migration race conditions cannot occur on the current staging configuration.
- **Hosting Plan Limitation:** Render Free tier does not support `preDeployCommand`. Setting `AUTO_MIGRATE=true` inside application startup is the only automated mechanism supported on the free tier.
- **Production Evolution:** When upgrading to Render Starter or a dedicated VPS, migrations must be migrated to `preDeployCommand: alembic upgrade head` with `AUTO_MIGRATE="false"`.

### 5.3 Staging Migration Verification & Rollback Procedure
- **Verification:** Owner checks deployment logs for `Database migrations applied successfully` and confirms database state via:
  ```sql
  SELECT version_num FROM alembic_version;
  ```
  Expected: `020_performance_indexes`.
- **Recovery Plan:** If a migration fails mid-flight:
  1. Revert Git deployment in Render dashboard to previous stable release.
  2. Restore staging database from pre-deployment snapshot using `pg_restore`.

---

## 6. Workstream E — Authentication & Demo-Account Cleanup Plan

### 6.1 Authentication Trace & Inactive Account Enforcement
A forensic trace of `backend/app/api/deps.py` and `backend/app/api/v1/auth.py` was conducted:

1. **Login Path (`auth.py:L20-L24`):**
   ```python
   if not user.active:
       raise HTTPException(
           status_code=status.HTTP_403_FORBIDDEN,
           detail="Account is inactive. Please contact administrator.",
       )
   ```
2. **Protected API Requests (`deps.py:L49-L54`):**
   ```python
   user = db.query(User).filter(
       User.id == user_id, 
       User.company_id == company_id, 
       User.active == True
   ).first()
   if not user:
       raise HTTPException(
           status_code=status.HTTP_401_UNAUTHORIZED,
           detail="User not found or inactive.",
       )
   ```
- **Architectural Guarantee:** Because `get_current_user` queries `User.active == True` against the database on **every single request**, deactivating an account immediately blocks all subsequent API calls even if the client presents a cryptographically valid, non-expired JWT cookie.

### 6.2 Owner Staging Account Cleanup Procedure
1. **Identify Existing Demo Accounts in Staging Database:**
   ```sql
   SELECT id, username, email, role, active, created_at 
   FROM users 
   WHERE username IN ('admin_demo', 'viewer_demo', 'manager_demo');
   ```
2. **Deactivate All Demo Accounts:**
   ```sql
   UPDATE users SET active = FALSE 
   WHERE username IN ('admin_demo', 'viewer_demo', 'manager_demo');
   ```
3. **Verify Inactive Account Rejection:**
   - Attempt login via `POST /api/v1/auth/login` with deactivated username $\rightarrow$ Assert `HTTP 403 Forbidden`.
   - Attempt authenticated request with existing cookie $\rightarrow$ Assert `HTTP 401 Unauthorized`.
4. **Provision Legitimate Administrator:**
   Run CLI script interactively:
   ```bash
   python backend/scripts/create_admin.py --username staging_admin --email owner@livo.local --company-code LIVO
   ```
   (Prompts securely for password using `getpass`, hashes with bcrypt, sets `active=True`, `role="admin"`).
5. **Verify Startup Does Not Recreate Demo Accounts:**
   Confirm `ENABLE_DEMO_SEEDING=false` in Render dashboard. Restart service and confirm zero demo accounts are re-seeded.

---

## 7. Workstream F — Rate-Limit Acceptance Behind the Real Proxy

### 7.1 Real Proxy Request Path
```
Client Request
      │
      ▼
Cloudflare Edge / Render Load Balancer (Terminates TLS, adds X-Forwarded-For)
      │
      ▼ (Internal Container Bridge / Dynamic IP)
Uvicorn ASGI Container (Peer IP: dynamic private container IP)
      │
      ▼
BasicRateLimitMiddleware ──> extract_client_ip(request, TRUSTED_PROXIES)
```

### 7.2 Blocker Analysis & Security Trade-offs
- **Current Security Baseline:** `TRUSTED_PROXIES = ["127.0.0.1", "::1"]`.
- Render does **not** publish static IP ranges or CIDR blocks for free-tier ingress load balancers.
- **Why Blind Subnet Trust is Forbidden:** Trusting `10.0.0.0/8` or `*` allows any untrusted client to inject arbitrary `X-Forwarded-For: <spoofed-ip>` headers and completely bypass the rate limiter.
- **Consequence of Conservative Trust:** Because Render's edge peer IP is not `127.0.0.1`, `extract_client_ip` ignores `X-Forwarded-For` and falls back safely to `request.client.host`.
  - **Security Outcome:** Rate limiting **cannot be bypassed** by spoofing headers.
  - **Operational Outcome:** All external clients behind Render's edge router share a **single rate-limiting pool of 30 requests per minute**.
- **Process Boundary Limitation:** `BasicRateLimitMiddleware` stores state in process memory. Counters reset on container restart and do not coordinate across multiple workers or instances.
- **Verdict:** Retained as **UNRESOLVED for Render Free Tier**.

### 7.3 Controlled Staging Test Plan (To Be Run by Owner)
| Step | Action | Expected Result | Pass/Fail Criteria |
| :--- | :--- | :--- | :--- |
| **RL-01** | Send 5 valid login requests from IP A | HTTP 200 OK | All 5 succeed; under 30 req limit |
| **RL-02** | Send login request with spoofed `X-Forwarded-For: 198.51.100.1` | HTTP 401/422 (Normal peer attribution) | Header ignored; direct peer IP logged |
| **RL-03** | Send 30 failed login requests rapidly cycling `X-Forwarded-For` | Requests 1–30 return 401; Request 31 returns HTTP 429 | Header spoofing cannot bypass rate limit |
| **RL-04** | Check response headers on HTTP 429 | `Retry-After: 60`, `error: "RATE_LIMITED"` | Strict error taxonomy preserved |
| **RL-05** | Send malformed headers (`<script>`, SQL injection, non-IP strings) | Safe fallback to peer IP without 500 error | No middleware exception or crash |

---

## 8. Workstream G — Backup and Disaster-Recovery Acceptance

### 8.1 Verification Status Across the 8 Disaster Recovery Stages

| Stage | Disaster Recovery Requirement | Verification Status | Evidence / Notes |
| :---: | :--- | :---: | :--- |
| **1** | Backup script and workflow code present locally | **VERIFIED** | `scripts/cloud_backup.sh` and `.github/workflows/scheduled_backup.yml` inspected and validated. |
| **2** | Workflow committed to release branch | **PENDING** | Files are currently untracked locally; awaits owner commit authorization. |
| **3** | GitHub Actions enabled in repository settings | **PENDING** | Requires owner verification in GitHub repository settings. |
| **4** | Required secret (`STAGING_DATABASE_URL`) configured | **PENDING** | Must be added under `Settings -> Secrets and variables -> Actions`. |
| **5** | Scheduled backup execution succeeded | **PENDING CLOUD RUN** | Nightly cron (`0 20 * * *`) scheduled; cloud run pending. |
| **6** | Backup artifact checksum and size verified | **PENDING CLOUD RUN** | Script generates SHA-256 and JSON telemetry; verified in local mock tests. |
| **7** | Restore into disposable isolated database verified | **PENDING OWNER DRILL** | Owner must execute restore drill against disposable database before acceptance. |
| **8** | Retention & recovery objectives verified | **DOCUMENTED LIMITATION** | GitHub Actions 7-day artifact retention is temporary; permanent off-site S3/B2 storage required for production. |

---

## 9. Workstream H — Ordered Staging Acceptance Matrix

This matrix provides the complete, ordered, step-by-step acceptance procedure for the repository owner upon approving the release candidate.

| Test ID | Area | Preconditions | Exact Action / Command | Expected Result | Evidence to Capture | Pass/Fail Criteria | Resp. Party | Destructive? | Rollback / Cleanup |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **STG-01** | Build Identity | Staging deployment completed | `curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health \| jq .` | `"commit"` matches deployed short commit SHA | JSON response output | Pass if `"commit"` matches Git SHA; fail if `"dev"` or mismatch | Owner | No | Re-deploy correct commit |
| **STG-02** | Health & Probes | Container running | `curl -s -i https://livo-footwear-erp-backend.onrender.com/api/v1/health/ready` | HTTP 200 OK, `"status": "ready"`, `"database": "healthy"` | HTTP headers and body | Pass if HTTP 200 and DB healthy | Owner | No | Check DB connection strings |
| **STG-03** | Frontend API Link | Vercel frontend deployed | Open `https://livo-footwear-erp.vercel.app` in browser; inspect network tab | Requests route to `https://livo-footwear-erp-backend.onrender.com/api/v1` | Browser DevTools network log | Pass if 0 CORS errors and correct target URL | Owner | No | Update `NEXT_PUBLIC_API_URL` |
| **STG-04** | Migration Status | Backend started | Inspect Render deployment logs; run `psql -c "SELECT version_num FROM alembic_version;"` | Revision `020_performance_indexes` active | Render deploy log + SQL query result | Pass if migration 020 applied; fail if startup error | Owner | No | Restore DB from pre-deploy dump |
| **STG-05** | Demo Account Inactivation | Staging database connected | Run deactivation SQL: `UPDATE users SET active=FALSE WHERE username IN ('admin_demo','viewer_demo');` | `UPDATE 2` (or matched count) | SQL output log | Pass if accounts set to `active=false` | Owner | Yes (Data update) | Re-enable accounts if needed |
| **STG-06** | Inactive Login Rejection | STG-05 complete | Attempt login via frontend or `POST /api/v1/auth/login` with demo credentials | HTTP 403 Forbidden: `"Account is inactive"` | API response payload | Pass if HTTP 403 returned | Owner | No | None |
| **STG-07** | Session Invalidation | STG-05 complete | Submit GET to `/api/v1/auth/me` with previous demo cookie | HTTP 401 Unauthorized: `"User not found or inactive"` | API response payload | Pass if HTTP 401 returned | Owner | No | None |
| **STG-08** | Admin Provisioning | STG-05 complete | Run `python backend/scripts/create_admin.py --username staging_admin --email admin@livo.local` | Admin user created with bcrypt hash, `role="admin"`, `active=True` | CLI output log | Pass if login succeeds with new admin credentials | Owner | Yes (User inserted) | Delete created user if invalid |
| **STG-09** | Rate Limiting Enforcement | STG-08 complete | Execute 31 rapid requests to `/api/v1/auth/login` | 30 requests process; 31st returns HTTP 429 Too Many Requests | HTTP status codes and `Retry-After` header | Pass if HTTP 429 returned on 31st request | Owner | No | Wait 60s for window expiration |
| **STG-10** | Tenant Isolation & IDOR | Logged in as Admin | Request resource belonging to different `company_id` (e.g. `/api/v1/stock/balance?company_id=999`) | Rejection or strictly scoped to user's assigned `company_id` | API response payload | Pass if cross-tenant data is completely unreachable | Owner | No | None |
| **STG-11** | Business Invariants | Synthetic test order | Create sales order, dispatch stock, check inventory ledger | Stock decrements accurately; financial balances match exactly | Stock ledger and order JSON | Pass if zero stock discrepancy and Decimal precision maintained | Owner | Yes (Test transaction) | Mark order void/cancelled |
| **STG-12** | Invoice Query Limit | Synthetic test order | Execute `/api/v1/sales/orders/{id}/printable` | Response within 3 queries; 0 N+1 query regression | SQL query count log | Pass if queries <= 3 | Owner | No | None |
| **STG-13** | Audit Log Redaction | Authenticated requests made | Inspect `logs/livo_erp.log` or database audit table | Passwords, tokens, and PAN numbers are redacted (`***`) | Audit log extract | Pass if zero cleartext secrets in logs | Owner | No | Clear test log entries |
| **STG-14** | Manual Backup Dispatch | STAGING_DATABASE_URL set in GitHub secrets | Trigger GitHub Actions: `Automated Cloud Database Backup -> Run workflow` | Workflow succeeds; artifact `db-backup-<id>` generated | GitHub Actions run log | Pass if artifact exists and size > 0 | Owner | No | Delete test artifact |
| **STG-15** | Restore Drill | Backup artifact downloaded | Restore artifact into disposable database: `pg_restore -d disposable_staging` | Schema and tables restore cleanly with zero errors | Restore command output log | Pass if `SELECT count(*) FROM users` matches staging | Owner | Yes (Disposable DB only) | Drop disposable database |

---

## 10. Workstream I — Regression Verification Results

All local test suites were independently re-executed in the current environment to produce fresh verification evidence.

### 10.1 Backend Test Suite (Pytest)
- **Command:**
  ```powershell
  backend\venv\Scripts\python -m pytest `
    backend/tests/test_phase_16_2_security_remediations.py `
    backend/tests/test_auth_api.py `
    backend/tests/test_security.py `
    backend/tests/test_security_audit.py `
    backend/tests/test_checkpoint_16_rbac.py `
    backend/tests/test_checkpoint_16_tenant_isolation.py `
    backend/tests/test_checkpoint_16_idor.py `
    backend/tests/test_checkpoint_16_security.py `
    backend/tests/test_checkpoint_16_business_security.py `
    backend/tests/test_checkpoint_15_query_regression.py `
    backend/tests/test_concurrency_race.py `
    backend/tests/test_document_numbering_concurrency.py -v
  ```
- **Exit Code:** `0`
- **Results:** **110 passed**, 0 failed, 0 skipped in 10.52s.
- **Key Verifications:**
  - Demo account seeding disabled by default, rejected in production: **PASSED**
  - Migration failure aborts startup via `RuntimeError`: **PASSED**
  - Untrusted client header spoofing ignored: **PASSED**
  - Header cycling evasion attempt fails (HTTP 429 triggered): **PASSED**
  - Deployment identity exposed in `/health`, `/health/live`, `/health/ready`: **PASSED**
  - RBAC token tampering rejection: **PASSED**
  - Tenant isolation and IDOR defenses: **PASSED**
  - Sales order and credit limit concurrency races: **PASSED**
  - Document numbering sequence concurrency: **PASSED**
  - Printable invoice query count limits (N+1 regression): **PASSED**

### 10.2 GitHub Actions Backup Workflow Syntax Validation
- **Command:**
  ```powershell
  backend\venv\Scripts\python -c "import yaml; data = yaml.safe_load(open('.github/workflows/scheduled_backup.yml')); print('YAML Valid! Keys:', list(data.keys()), 'Jobs:', list(data['jobs'].keys()), 'Triggers:', list(data['on'].keys()))"
  ```
- **Exit Code:** `0`
- **Output:** `YAML Valid! Keys: ['name', 'on', 'concurrency', 'jobs'] Jobs: ['backup'] Triggers: ['schedule', 'workflow_dispatch']`

### 10.3 Frontend Production Build and TypeScript Verification
- **Command:** `npm run build` (in `frontend/`)
- **Exit Code:** `0`
- **Output:**
  - Next.js 14.2.35 optimized production build compiled successfully.
  - Type-checking & linting: 0 errors, 0 warnings.
  - 7/7 static pages generated. Shared first load JS: 87.6 kB.

---

## 11. Owner-Only Operational Checklist & Required Permissions

Before staging acceptance can proceed, the repository owner must execute the following non-delegable actions:

1. **Repository Access Permissions:**
   - Owner access to GitHub repository `Sishir120/livo-footwear-erp` (Settings, Secrets, Actions).
   - Administrative access to Render Dashboard (`livo-footwear-erp-backend`).
   - Administrative access to Vercel Dashboard (`livo-footwear-erp`).
2. **Action 1 — Review and Commit Release Candidate:**
   - Stage the allowed files:
     ```bash
     git add .env.example .env.staging.example .gitignore README.md \
             backend/app/api/v1/health.py backend/app/config.py \
             backend/app/core/demo_seeding.py backend/app/main.py \
             backend/app/middleware/rate_limit.py backend/scripts/create_admin.py \
             backend/tests/test_checkpoint_15_query_regression.py \
             backend/tests/test_phase_16_2_security_remediations.py \
             frontend/src/app/login/page.tsx render.yaml \
             .github/workflows/scheduled_backup.yml scripts/cloud_backup.sh \
             docs/CLIENT_PITCH_CHEATSHEET.md docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md \
             docs/deployment/STAGING_DEPLOYMENT_GUIDE.md
     ```
   - Commit: `git commit -m "release: prepare auditable staging candidate v1.0.0-staging"`
   - Push to GitHub: `git push origin release/v1.0.0-staging`
3. **Action 2 — Configure GitHub Actions Secret:**
   - Go to `Settings -> Secrets and variables -> Actions`.
   - Add Secret `STAGING_DATABASE_URL` pointing to the isolated staging PostgreSQL database.
   - (Optional) Add Secret `BACKUP_ALERT_WEBHOOK_URL` for alert telemetry.
4. **Action 3 — Verify Render Staging Environment:**
   - In Render Dashboard -> `livo-footwear-erp-backend`:
     - Confirm `ENVIRONMENT=staging`
     - Confirm `AUTO_MIGRATE=true`
     - Confirm `ENABLE_DEMO_SEEDING=false`
     - Confirm `TRUSTED_PROXIES=127.0.0.1,::1`
     - Trigger manual deploy if auto-deploy is disabled.
5. **Action 4 — Execute Staging Acceptance Checklist:**
   - Execute tests `STG-01` through `STG-15` from Section 9.

---

## 12. Unresolved Risks & Severity Matrix

| Risk ID | Risk Description | Severity | Impact | Mitigation / Status |
| :---: | :--- | :---: | :--- | :--- |
| **RSK-01** | Render Free Tier Shared Rate-Limit Pool | **MEDIUM** | Render does not supply static proxy CIDRs. All clients share 30 req/min pool. | Blocker retained as **UNRESOLVED for Render Free**. Acceptable for single-evaluator staging demo; unacceptable for multi-user production. |
| **RSK-02** | In-Memory Limiter Single-Process Scope | **MEDIUM** | Rate-limit counters stored in memory; resets on container restart; no coordination across replicas. | Documented. Production upgrade requires Redis-backed distributed rate limiter. |
| **RSK-03** | Startup Migration In-Process Thread Lock | **LOW (Staging)**<br>**HIGH (Prod)** | `threading.Lock()` does not protect multi-instance deployments. | Safe on Render Free tier (strictly 1 instance). Production requires `preDeployCommand` or CI release phase. |
| **RSK-04** | Temporary Backup Storage on GitHub Actions | **MEDIUM** | Backup artifacts expire after 7 days; tied to GitHub infrastructure. | Documented. Production requires permanent off-site S3/B2 encrypted replication with lifecycle retention. |
| **RSK-05** | Staging Demo Account Residue | **HIGH (If Unaddressed)** | Database created prior to Phase 16.2 may still contain active demo accounts. | Mitigated via mandatory owner-executed deactivation checklist (`STG-05`, `STG-06`, `STG-07`). |

---

## 13. Final Release Gate Decisions

### Gate 1: Local Synthetic-Data Demo
- **Status:** **PASS (READY)**
- **Verdict:** Fully verified. All 110 regression, security, RBAC, tenant isolation, and concurrency tests pass locally. Next.js production build succeeds with 0 type errors. Public login interface is cleansed of exposed credentials. Controlled local demonstrations using synthetic data are fully approved.

### Gate 2: Live Staging Deployment
- **Status:** **HOLD (PENDING OWNER ACTIONS)**
- **Verdict:** The release candidate is internally consistent, fully documented, and ready for owner review. However, live staging deployment is strictly on HOLD pending owner approval of the release scope, execution of the Git commit/push, provisioning of the `STAGING_DATABASE_URL` GitHub secret, and completion of the staging acceptance matrix (`STG-01` through `STG-15`).

### Gate 3: Production Deployment
- **Status:** **NO-GO (STRICTLY PROHIBITED)**
- **Verdict:** Release candidate is not approved for production. Production deployment is prohibited until:
  1. Live staging acceptance passes completely.
  2. Rate limiting is upgraded to a distributed Redis store.
  3. Migrations are decoupled from application boot via `preDeployCommand`.
  4. Off-site permanent encrypted backup storage (S3/B2) is operational.
  5. Dedicated production infrastructure and secrets are provisioned.

---

**AUDIT CONCLUSION:** Phase 16.7 is complete. No code modifications were made during this phase, no staging deployment was initiated, no cloud database was touched, and no Git commit or push was executed. The repository remains in an auditable baseline state awaiting owner action.
