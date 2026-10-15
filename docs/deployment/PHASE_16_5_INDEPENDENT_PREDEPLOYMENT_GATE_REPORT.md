# LIVO FOOTWEAR ERP — PHASE 16.5
## Independent Pre-Deployment Gate & Staging Readiness Audit Report

**Document Identifier:** `PHASE_16_5_INDEPENDENT_PREDEPLOYMENT_GATE_REPORT.md`  
**Location:** `docs/deployment/PHASE_16_5_INDEPENDENT_PREDEPLOYMENT_GATE_REPORT.md`  
**Execution Timestamp:** 2026-10-14 13:18:00 +05:45 (Nepal Standard Time) / 07:33:00 UTC  
**Auditor Roles:** Independent Release Engineer, Application Security Auditor, DevOps Engineer, QA Lead  
**Target Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Local Project Directory:** `D:\Antigravity\Footwear app`  
**Active Release Branch:** `release/v1.0.0-staging`  
**Verified Candidate HEAD SHA:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Remote Tracking Reference:** `origin/release/v1.0.0-staging` at `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Live Frontend Staging URL:** `https://livo-footwear-erp.vercel.app`  
**Live Backend Staging URL:** `https://livo-footwear-erp-backend.onrender.com`  

---

## 1. FORMAL RELEASE-GATE MATRIX & EXECUTIVE DECISION

```
========================================================================================
   GATE 1 — RESTRICTED LOCAL CLIENT DEMONSTRATION:    PASS (APPROVED FOR DEMO)
   GATE 2 — LIVE CLOUD STAGING ACCEPTANCE:            HOLD (NO-GO — DEPLOYMENT DRIFT & SECRETS)
   GATE 3 — PRODUCTION DEPLOYMENT WITH REAL DATA:     HOLD (NO-GO — OPERATIONAL PREREQUISITES)
========================================================================================
```

### 1.1 Master Release Gate Evaluation

| Gate / Scope Domain | Verdict | Summary of Evidence & Impact |
| :--- | :---: | :--- |
| **Gate 1: Restricted Local Demonstration** | **PASS** | 91/91 tests pass; 0 skipped; 0 failed. Next.js build clean. Startup creates 0 predictable accounts. In-process migration lock verified. N+1 benchmarks pass. Ready for local/synthetic demo. |
| **Gate 2: Live Cloud Staging Acceptance** | **HOLD** | **Blocked by 4 owner prerequisites:** (1) Live Render backend is on older 50-path build (drift: 46 paths); (2) Candidate changes are uncommitted/unpushed; (3) `.github/workflows/scheduled_backup.yml` is untracked and `STAGING_DATABASE_URL` secret is unprovisioned; (4) Persistent demo accounts in cloud DB must be deactivated by owner. |
| **Gate 3: Production Deployment (Live Data)** | **HOLD** | **Blocked by architectural prerequisites:** In-memory rate limiter lacks multi-instance Redis backend; Render free tier lacks pre-deploy migration isolation; backup artifact retention is 7 days without permanent off-site S3/R2 replication. |

---

## 2. WORKSTREAM 1 — VERIFICATION OF PHASE 16.4 CHANGES & REPOSITORY STATE

### 2.1 Git Repository & Working Tree Inventory
- **Current Branch:** `release/v1.0.0-staging`
- **Candidate Commit:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
- **Remote Parity:** `origin/release/v1.0.0-staging` is at `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`. Local HEAD is identical to remote tracking branch.
- **Working Tree State:** Clean uncommitted modifications from Phases 16.2–16.4. Zero files staged (`git add` not run).

#### Tracked Modified Files (11 Files)
1. `.env.example`: Template documentation updated with `ENABLE_DEMO_SEEDING=false`, `AUTO_MIGRATE=true`, `TRUSTED_PROXIES=127.0.0.1,::1`.
2. `.env.staging.example`: Template for staging deployment updated with security boundaries.
3. `README.md`: Sanitized demo credentials; updated triage runbooks.
4. `backend/app/config.py`: Added `ENVIRONMENT`, `ENABLE_DEMO_SEEDING`, `AUTO_MIGRATE`, and `TRUSTED_PROXIES` settings with validators.
5. `backend/app/main.py`: Replaced silent exception swallowing with `RuntimeError` fail-fast; added `_migration_lock = threading.Lock()`; delegated user seeding to opt-in `seed_demo_users_if_enabled`.
6. `backend/app/middleware/rate_limit.py`: Implemented RFC 7239 compliant client IP extraction; checks peer against `TRUSTED_PROXIES`; right-to-left traversal of `X-Forwarded-For`.
7. `backend/tests/test_checkpoint_15_query_regression.py`: Added `Warehouse` and `StockMovement` (+100 pairs) seeding and dedicated client (`CLI15-{comp_id}-0099`) to `TestPrintableInvoiceQueryCount`.
8. `docs/CLIENT_PITCH_CHEATSHEET.md`: Sanitized credentials.
9. `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md`: Updated onboarding procedure using `scripts/create_admin.py`.
10. `frontend/src/app/login/page.tsx`: Purged form pre-fills (`username=""`, `password=""`), removed role quick-fill buttons, removed clipboard paste blocking.
11. `render.yaml`: Added `ENVIRONMENT: staging`, `AUTO_MIGRATE: "true"`, and `TRUSTED_PROXIES: "127.0.0.1,::1"`.

#### Untracked Files (Preserved Intact)
- `.github/workflows/scheduled_backup.yml`: Nightly automated backup workflow (line 24 corrected to "Execute PostgreSQL Logical Backup").
- `.kilo/`: Agent workspace metadata.
- `backend/app/core/demo_seeding.py`: Opt-in demo seeding module with strict production refusal.
- `backend/scripts/create_admin.py`: Interactive CLI administrator onboarding tool.
- `backend/tests/test_phase_16_2_security_remediations.py`: 10 regression tests for SEC-01, SEC-02, SEC-03, and `render.yaml`.
- `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md`: Disaster recovery and scheduling runbook.
- `docs/deployment/PHASE_16_1_RELEASE_VERIFICATION_REPORT.md`
- `docs/deployment/PHASE_16_2_SECURITY_REMEDIATION_REPORT.md`
- `docs/deployment/PHASE_16_3_INDEPENDENT_VERIFICATION_REPORT.md`
- `docs/deployment/PHASE_16_4_RELEASE_CONFIGURATION_REMEDIATION_REPORT.md`
- `docs/deployment/PHASE_16_RELEASE_EXECUTION_REPORT.md`
- `docs/deployment/systemd/`: Linux systemd service and timer definitions.
- `scripts/cloud_backup.sh`: Standalone POSIX flock-locked PostgreSQL backup engine.

### 2.2 Safeguard Verification
Audit of the actual diffs confirmed:
- No safeguards were weakened.
- Stock validation, credit checking, and ATP enforcement remain 100% active.
- Startup migration fail-fast (`raise RuntimeError`) is intact.
- Demo provisioning remains strictly disabled by default and rejected in production.

---

## 3. WORKSTREAM 2 — MIGRATION SAFETY & LIFECYCLE AUDIT

### 3.1 Docker Startup & ASGI Server Configuration
* **Dockerfile CMD (`backend/Dockerfile:30`):**
  ```dockerfile
  CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
  ```
* **Worker Count:** Uvicorn starts with default worker count = **1 OS process** (no `--workers` flag).
* **Render Plan:** `plan: free` in `render.yaml`. Render free tier enforces a strict limit of **1 instance**. Horizontal autoscaling is not supported.

### 3.2 Evaluation of the Migration Lock
* **Implementation (`backend/app/main.py:20-25`):**
  `_migration_lock = threading.Lock()` wraps the Alembic upgrade block inside `lifespan(app)`.
* **Lock Scope Finding:**
  - **In-Process Protection (VERIFIED):** The Python `threading.Lock()` successfully serializes threads within the single Uvicorn process. This eliminated the `KeyError: 'script'` race condition when multiple threads entered `lifespan` during concurrency testing.
  - **Cross-Process & Multi-Instance Limitation (CRITICAL AUDIT DISTINCTION):** A Python `threading.Lock` is strictly an in-memory primitive. It **does not** provide cross-process locking (e.g., if Uvicorn were run with `--workers 2+`) and **does not** provide distributed locking across multiple container instances.
* **Overlapping Deployment Analysis:**
  On Render, a rolling deploy starts a new container instance while the old instance is still running and serving traffic. When the new container boots, `AUTO_MIGRATE=true` applies DDL migrations while the old container is still processing user requests. If a migration introduces backward-incompatible DDL (e.g. dropping a column, renaming a table, or adding a NOT NULL column without a default), the running old container will fail on live requests before the new container is promoted.

### 3.3 Fail-Fast Failure Behavior
* **Mechanism (`backend/app/main.py:34-37`):**
  ```python
  except Exception as e:
      logger.critical(f"FATAL: Database migration failed during application startup: {e}", exc_info=True)
      raise RuntimeError(f"Database migration failure: {e}") from e
  ```
* **Runtime Result (VERIFIED):** Raising `RuntimeError` in `lifespan` aborts Uvicorn startup. The container crashes with a non-zero exit code. Render health checks (`/api/v1/health`) never succeed, and traffic is never routed to the failed instance. Blind historical schema stamping (`command.stamp`) was completely eradicated.

### 3.4 Recovery Path for Failed Migrations
* **PostgreSQL Behavior:** PostgreSQL supports transactional DDL. Most failed Alembic migrations roll back automatically within the transaction, leaving `alembic_version` at the prior revision.
* **Documented Rollback Gap:** The project documents disaster recovery via full backup restoration (`docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md:88`), but currently lacks an explicit step-by-step Alembic downgrade SOP (`alembic downgrade -1`).

### 3.5 Plan Compatibility & Minimum Safe Remediation
* **Render Free Plan Limitation:** Render's Blueprint specification only supports `preDeployCommand` on **paid instance types (Starter and above)**. It cannot be executed on `plan: free`.
* **Verdict:** Running migrations on boot (`AUTO_MIGRATE=true`) with fail-fast `RuntimeError` is the only automated migration mechanism supported on Render's free tier, and is acceptable strictly for single-instance staging.
* **Minimum Safe Remediation for Production:**
  1. Upgrade to Render Starter plan.
  2. Configure `preDeployCommand: alembic upgrade head` in `render.yaml`.
  3. Set `AUTO_MIGRATE: "false"` on web service instances.

---

## 4. WORKSTREAM 3 — REVERSE-PROXY AND RATE-LIMIT SAFETY

### 4.1 Request Path Tracing
```
Client Browser -> Cloudflare Edge -> Render Reverse Proxy (10.x.x.x) -> Container (0.0.0.0:8000) -> Uvicorn -> BasicRateLimitMiddleware -> Auth Endpoint
```

### 4.2 Header Inspection & Proxy Trust Logic
* **Inspection Target:** `backend/app/middleware/rate_limit.py:33-75`.
* **Headers Evaluated:** Evaluates `X-Forwarded-For` right-to-left; falls back to `X-Real-IP`; falls back to `request.client.host`.
* **Direct Spoofing Rejection (VERIFIED):** Direct peer `198.51.100.45` injecting forged headers is rejected; client IP resolves strictly to `198.51.100.45`.
* **Trusted Traversal (VERIFIED):** Direct peer `127.0.0.1` forwarding `203.0.113.195` resolves correctly to `203.0.113.195`.
* **Malformed & Injection Resistance (VERIFIED):** SQL injection and XSS payloads in headers do not crash the parser.

### 4.3 Hosting Architecture Reality & Unverified Client IP Attribution
* **Finding (UNVERIFIED FOR LIVE RENDER HOSTING):**
  - In `render.yaml`, `TRUSTED_PROXIES` is set to `"127.0.0.1,::1"`.
  - When traffic arrives on Render, the direct peer connection to the container originates from Render's internal proxy network (typically private RFC 1918 addresses such as `10.x.x.x`).
  - Because `10.x.x.x` is **not** in `["127.0.0.1", "::1"]`, `extract_client_ip` treats Render's proxy itself as an untrusted client!
  - **Consequence:** `extract_client_ip` ignores `X-Forwarded-For` and returns the Render internal proxy IP (`10.x.x.x`) for **every public user**.
  - **Impact on Rate Limiting:** All external users are bucketed into a single rate-limiting counter. If 30 total logins occur across all users in 60 seconds (or if one user triggers 30 failed attempts), the rate limiter returns HTTP 429 `RATE_LIMITED` for **all users globally**.
  - **Why `10.0.0.0/8` Was Not Blindly Added:** Render does not publish static proxy CIDRs, and trusting `10.0.0.0/8` would trust any container sharing the internal subnet.
* **Multi-Instance Rate Limiting Limitation:**
  `BasicRateLimitMiddleware` stores state in `self.requests = defaultdict(list)` (process memory). In a multi-worker or multi-instance topology, limits are per-process and can be bypassed by distributing requests across instances.

---

## 5. WORKSTREAM 4 — BACKUP AND RECOVERY READINESS

### 5.1 Verification Checklist & Cloud Gap Analysis

| Audit Item | Code / Config | Local Drill | Cloud Execution Evidence | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Workflow Schedule** | `cron: '0 20 * * *'` (01:45 NPT) | N/A | Untracked locally; not on remote GitHub | **UNVERIFIED (NOT PUSHED)** |
| **Staging DB Access** | Sourced via `STAGING_DATABASE_URL` | Verified with env | Secret not configured in GitHub repo | **UNVERIFIED (NO SECRET)** |
| **Logical Backup Execution** | `pg_dump --format=plain --clean` | Verified locally | No cloud execution runs exist | **UNVERIFIED IN CLOUD** |
| **SHA-256 Checksum** | Logged to `latest_status.json` | Verified locally | No cloud telemetry | **VERIFIED LOCALLY** |
| **Disposable DB Restore** | `psql "$TARGET" -f dump.sql` | 34 tables restored | No cloud drill executed | **VERIFIED LOCALLY** |
| **7-Day Retention Pruning** | `find -mtime +7 -delete` | Verified syntax | Artifact upload active in workflow | **VERIFIED IN CONFIG** |
| **Failure Alerting** | Webhook POST + exit code 2 | Verified in script | Dependent on secret `BACKUP_ALERT_WEBHOOK_URL` | **VERIFIED IN CODE** |
| **Permanent Cloud Storage** | Ephemeral runner -> GitHub artifact | Verified 7-day zip | S3/R2 permanent storage not configured | **PARTIALLY VERIFIED** |

*Audit Conclusion: The backup script and workflow configuration are technically sound and locally verified, but cloud backup is **UNVERIFIED in production** because `.github/workflows/scheduled_backup.yml` has not been committed/pushed, and repository secrets have not been configured by the owner.*

---

## 6. WORKSTREAM 5 — AUTHENTICATION & EXPOSED DEMO ACCOUNTS

### 6.1 Code-Level Safeguards (SEC-01)
* **Startup Seeding:** `backend/app/main.py:74-76` delegates exclusively to `seed_demo_users_if_enabled`.
* **Disabled by Default:** `backend/app/config.py:52` defines `ENABLE_DEMO_SEEDING: bool = False`. Normal startup creates 0 users.
* **Production Refusal:** `backend/app/core/demo_seeding.py:24-30` explicitly logs a critical alert and rejects seeding if `ENVIRONMENT in ("production", "prod")`.
* **Login UI Form:** `frontend/src/app/login/page.tsx:9-10` initializes `username=""`, `password=""`. Quick-fill persona chips and clipboard paste blocks are completely removed.
* **Admin Onboarding CLI:** `backend/scripts/create_admin.py` verified; enforces password length >= 8, bcrypt hashing, and interactive masked input via `getpass`.

### 6.2 Session Invalidation Analysis
* **Mechanism (`backend/app/api/deps.py:49-54`):**
  ```python
  user = db.query(User).filter(User.id == user_id, User.company_id == company_id, User.active == True).first()
  if not user:
      raise HTTPException(status_code=401, detail="User not found or inactive.")
  ```
* **Audit Proof:** Authentication is **stateful**. Every authenticated API request performs a live database query requiring `User.active == True`. Setting `active = false` immediately invalidates all active sessions and existing JWT bearer tokens for that account on their very next request.

### 6.3 Safe Owner-Executed Remediation Runbook
*Execute only on live staging/production databases after candidate deployment:*

1. **Audit Existing Database Records:**
   ```sql
   SELECT id, company_id, username, email, role, active, created_at 
   FROM users 
   WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
   ```
2. **Deactivate Accounts (Preserves Foreign-Key Audit Trail):**
   ```sql
   UPDATE users 
   SET active = false, 
       email = 'deactivated_' || username || '_' || extract(epoch from now()) || '@disabled.local'
   WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
   ```
3. **Invalidate Global Signatures (Optional):**
   In the hosting dashboard, generate and set a new `SECRET_KEY` (32 bytes / 64 hex chars).
4. **Verify Account Lockout:**
   Authenticate via `POST /api/v1/auth/login` with the deactivated username. Expected response: `HTTP 403 Forbidden` (`Account is inactive`).
5. **Create Authorized Administrator:**
   Run `python scripts/create_admin.py` to create a dedicated administrator with unique credentials.

---

## 7. WORKSTREAM 6 — TEST REPRODUCTION & DEPLOYMENT IDENTITY

### 7.1 Independent Test Suite Reproduction

```bash
backend\venv\Scripts\pytest tests/test_phase_16_2_security_remediations.py tests/test_auth_api.py tests/test_security.py tests/test_security_audit.py tests/test_checkpoint_16_security.py tests/test_checkpoint_16_tenant_isolation.py tests/test_checkpoint_16_rbac.py tests/test_checkpoint_16_idor.py tests/test_checkpoint_15_query_regression.py -v
```

**Results:**
- **91 passed, 0 failed, 0 skipped** in 8.05s.
- `test_phase_16_2_security_remediations.py`: **10 passed** (SEC-01, SEC-02, SEC-03, `render.yaml`).
- `test_checkpoint_15_query_regression.py`: **53 passed** (including all 3 printable invoice benchmarks).
- `TestConcurrency`: **7 passed** (no thread collisions; `_migration_lock` verified).
- Frontend Build: `npm run build` completed with exit code 0; all 7 routes compiled.

### 7.2 Forensic Deployment Identity & OpenAPI Drift Analysis

| Property | Local Release Candidate (`47cf8f5`) | Live Backend (`livo-footwear-erp-backend.onrender.com`) | Parity Status |
| :--- | :---: | :---: | :---: |
| **OpenAPI Path Count** | **96 route paths** | **50 route paths** | **FAILED (DRIFT: 46 PATHS)** |
| **Fixed Assets API** | Present (`/api/v1/fixed-assets`) | Missing (404) | Missing on live |
| **Factory Expenses API**| Present (`/api/v1/expenses/factory`) | Missing (404) | Missing on live |
| **HR Master & Photo** | Present (`/api/v1/hr/*`) | Missing (404) | Missing on live |
| **Backup Health API** | Present (`/api/v1/backup/health`) | Missing (404) | Missing on live |
| **Health Liveness/Readiness**| Present (`/api/v1/health/live`) | Missing (404) | Missing on live |
| **Exposed Commit SHA** | None in `/api/v1/health` | None in `/api/v1/health` | **UNVERIFIED IDENTITY** |
| **Frontend Age Header** | Fresh build | `Age: 1260247` (~14.5 days old) | Stale edge cache |

#### Proven Identity Conclusions:
1. The live Render backend is running an older pre-Phase 15/16 build. It does NOT contain candidate commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` or Phase 16.4 configuration fixes.
2. The live deployment identity cannot be verified from HTTP endpoints alone because `/api/v1/health` does not expose a commit SHA.
3. **Recommended Deployment Identity Mechanism:** Add `commit: os.getenv("RENDER_GIT_COMMIT", "unknown")[:8]` to `/api/v1/health` to allow unambiguous, non-secret commit identification.

---

## 8. ORDERED REMEDIATION & OWNER ACTION PLAN

The following actions must be executed in order by the repository owner to clear Gate 2 (Cloud Staging) and Gate 3 (Production):

```
+---------------------------------------------------------------------------------------+
| STEP 1: COMMIT & PUSH CANDIDATE TO GITHUB                                              |
| Action: Review working tree changes, stage tracked files and .github/, commit to      |
|         release/v1.0.0-staging, and push to origin.                                   |
| Responsible: Repository Owner                                                          |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| STEP 2: CONFIGURE GITHUB ACTIONS REPOSITORY SECRETS                                   |
| Action: In GitHub Settings -> Secrets -> Actions, add STAGING_DATABASE_URL with        |
|         the staging PostgreSQL connection string.                                     |
| Responsible: Repository Owner / DevOps Lead                                           |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| STEP 3: REDEPLOY CLOUD STAGING (RENDER & VERCEL)                                      |
| Action: Trigger a manual deploy on Render and Vercel from release/v1.0.0-staging.     |
|         Verify that GET /api/v1/openapi.json returns 96 route paths.                  |
| Responsible: DevOps Engineer / Owner                                                  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| STEP 4: PURGE PERSISTENT DEMO ACCOUNTS ON CLOUD DATABASE                              |
| Action: Execute the deactivation SQL query in §6.3 against the staging database.      |
|         Verify that admin_demo cannot authenticate.                                   |
| Responsible: Database Administrator / Owner                                           |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
| STEP 5: PROVISION AUTHORIZED ADMINISTRATOR & TEST BACKUP                              |
| Action: Run python scripts/create_admin.py to onboard authorized administrator.       |
|         Trigger .github/workflows/scheduled_backup.yml via workflow_dispatch.         |
| Responsible: Owner / QA Lead                                                          |
+---------------------------------------------------------------------------------------+
```

---

## 9. RELEASE GATE RECOMMENDATIONS

1. **Gate 1 — Restricted Local Demonstration:** **APPROVED (GO)**. The local candidate codebase is fully verified, robust, and safe for synthetic client demonstrations.
2. **Gate 2 — Live Cloud Staging Acceptance:** **HOLD (NO-GO)** until the 5 owner actions in §8 are executed and staging parity (96 endpoints) is verified.
3. **Gate 3 — Production Deployment with Real Business Data:** **HOLD (NO-GO)** until dedicated pre-deploy migration commands (Starter plan), Redis-backed rate limiting, and permanent S3/R2 backup replication are established.

---
**Report Certified By:** Independent Release Engineer, Application Security Auditor & DevOps Lead  
**Signature:** `LIVO-PHASE16.5-PREDEPLOY-GATE-AUDITED`  
**Date:** 2026-10-14  
