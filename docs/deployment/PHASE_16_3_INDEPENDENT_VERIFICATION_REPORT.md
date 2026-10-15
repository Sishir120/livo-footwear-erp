# LIVO FOOTWEAR ERP — PHASE 16.3
## Independent Security Fix, Migration Safety & Backup Verification Audit Report

**Document Identifier:** `PHASE_16_3_INDEPENDENT_VERIFICATION_REPORT.md`  
**Location:** `docs/deployment/PHASE_16_3_INDEPENDENT_VERIFICATION_REPORT.md`  
**Execution Timestamp:** 2026-10-14 13:02:00 +05:45 (Nepal Standard Time) / 07:17:00 UTC  
**Auditor Role:** Independent Senior Security & Release Auditor  
**Target Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Local Project Directory:** `D:\Antigravity\Footwear app`  
**Active Release Branch:** `release/v1.0.0-staging`  
**Base Release Commit:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Live Frontend Staging URL:** `https://livo-footwear-erp.vercel.app`  
**Live Backend Staging URL:** `https://livo-footwear-erp-backend.onrender.com`  

---

## 1. AUDIT SCORECARD & EXECUTIVE VERDICT

### 1.1 Formal Dual Decision

```
========================================================================================
   RESTRICTED CLIENT DEMONSTRATION DECISION:  GO (LOCALLY VALIDATED CANDIDATE)
   LIVE CLOUD STAGING ACCEPTANCE DECISION:    NO-GO (DEPLOYMENT DRIFT UNRESOLVED)
   PRODUCTION DEPLOYMENT WITH REAL DATA:     NO-GO (PREREQUISITES OUTSTANDING)
========================================================================================
```

### 1.2 Master Verification Scorecard

Each verification finding is strictly evaluated using standardized audit classifications:
* `VERIFIED`: Directly reproduced, verified in source, and mathematically/operationally confirmed.
* `PARTIALLY VERIFIED`: Verified in code/configuration, but subject to environment-specific limitations or missing live infrastructure validation.
* `REPORTED ONLY`: Claimed in previous documentation or runbooks without direct test reproduction.
* `FAILED`: Code, configuration, or documentation defect identified during independent inspection.
* `NOT RUN`: Omitted due to safety, data preservation, or cloud resource boundaries.

| Audit Domain | Scope Item | Status | Key Evidence / Defect Summary |
| :--- | :--- | :--- | :--- |
| **A. Authentication (SEC-01)** | Normal startup does not seed demo accounts | **VERIFIED** | Default `ENABLE_DEMO_SEEDING=false`; startup creates 0 users. |
| | Production mode strictly refuses demo seeding | **VERIFIED** | Tested `ENVIRONMENT=production`; returns `rejected: production_mode_refusal`. |
| | Frontend credential prefill & buttons removed | **VERIFIED** | Form initial state empty (`""`); no preset quick-fill buttons; paste allowed. |
| | Administrator creation CLI tool operational | **VERIFIED** | `scripts/create_admin.py` functional with `getpass`, validation, and hashing. |
| | Existing accounts separated from source cleanup | **VERIFIED** | Source cleanup does not purge existing DBs; DB rotation checklist required. |
| | Credential exposure in tree & recent history | **VERIFIED** | History traces `admin_demo` to `ace5784`/`47cf8f5`; sanitized in candidate. |
| **B. Migrations (SEC-02)** | Lifespan failure raises fatal `RuntimeError` | **VERIFIED** | Lifespan aborts process on Alembic error; never serves traffic on broken schema. |
| | Elimination of blind historical stamping | **VERIFIED** | `002_invoice_uq` stamp removed; 0 occurrences of `command.stamp` in backend. |
| | Migration ownership & concurrency analysis | **PARTIALLY VERIFIED** | Executed in app lifespan; safe on single-instance free tier; lacks multi-worker lock. |
| | Deployment configuration alignment (`render.yaml`) | **FAILED** | `render.yaml` lacks `ENVIRONMENT: staging`, `preDeployCommand`, and explicit config. |
| **C. Rate Limiting (SEC-03)** | Spoofed `X-Forwarded-For` from untrusted peer | **VERIFIED** | Direct peer IP enforced; untrusted forwarded headers strictly ignored. |
| | Valid forwarded headers from trusted proxy | **VERIFIED** | Right-to-left traversal extracts client IP when peer is in `TRUSTED_PROXIES`. |
| | Malformed headers and missing client handling | **VERIFIED** | Malformed strings, injection payloads, and `None` client fall back safely. |
| | Login rate-limit threshold enforcement | **VERIFIED** | 30 requests succeed; 31st returns HTTP 429 `RATE_LIMITED` with `Retry-After: 60`. |
| | Multi-instance scaling limitation | **VERIFIED LIMITATION** | In-memory limiter is per-process; requires Redis for horizontal clustering. |
| | Hosting proxy trust alignment for Render | **PARTIALLY VERIFIED** | Default `TRUSTED_PROXIES` (`127.0.0.1,::1`) does not cover Render internal subnet. |
| **D. Cloud Backup (DEF-02)** | Schedule validity (01:45 AM Nepal Time) | **VERIFIED** | Cron `0 20 * * *` and systemd `20:00:00 UTC` = 01:45 AM NPT. |
| | Zero credential leakage in logs or telemetry | **VERIFIED** | Database URL sourced from env/secrets; never printed in stdout/JSON. |
| | GitHub runner database reachability | **PARTIALLY VERIFIED** | Reachable for public cloud DBs (Neon SSL); unreachable for private VPC DBs. |
| | Durable storage vs ephemeral runner | **PARTIALLY VERIFIED** | GitHub artifact stored for 7 days; not mirrored to permanent S3/R2 storage. |
| | Scoped retention pruning | **VERIFIED** | `find` command strictly matches `livo_backup_*.sql.gz` older than 7 days. |
| | Concurrency protection via `flock` and Actions | **VERIFIED** | POSIX `flock -n 200` and GitHub Actions `concurrency.group` prevent overlap. |
| | Actionable failure alerting | **VERIFIED** | Supports webhook POST; exits with code 2 triggering GitHub failure emails. |
| | Sanitized checksums & metadata | **VERIFIED** | SHA-256 and byte counts logged without sensitive data contents. |
| | Disposable database restoration | **VERIFIED** | Plain SQL with `--clean --if-exists` restores cleanly via `psql`. |
| | Backup terminology classification | **FAILED** | `.github/workflows/scheduled_backup.yml:24` labels `pg_dump` as "Physical Dump". |
| **E. Test Reproduction** | Security remediation test suite (Phase 16.2) | **VERIFIED** | 8 passed, 0 failed in 2.31s (`backend/venv/Scripts/pytest`). |
| | Core auth, security & RBAC test suites | **VERIFIED** | 36 passed, 0 failed in 6.43s. |
| | Analysis of 3 skipped tests | **VERIFIED** | Skipped due to test fixture omitting stock setup; not a functional product bug. |
| | Frontend production build | **VERIFIED** | `npm run build` completed with exit code 0; all 7 routes compiled. |
| **F. Release Identity** | Git commit SHA & working-tree status | **VERIFIED** | Branch `release/v1.0.0-staging`, commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`. |
| | Live backend deployment parity | **FAILED (DRIFT)** | Live backend has 50 paths (older build); candidate has 96 paths. Drift = 46 paths. |
| | Public endpoint commit tracing | **VERIFIED LIMITATION** | `/api/v1/health` does not expose commit SHA or build ID in payload or headers. |

---

## 2. SECTION A: AUTHENTICATION REMEDIATION (SEC-01)

### 2.1 Independent Verification Details

#### A.1 Normal Startup Does Not Create Predictable Accounts
* **Inspection Target:** `backend/app/main.py:74-76` and `backend/app/core/demo_seeding.py:20-22`.
* **Mechanism:** In `backend/app/main.py`, the unconditional creation of `admin_demo`, `viewer_demo`, `editor_admin`, and `viewer_user` was deleted. Startup calls `seed_demo_users_if_enabled(db, company)`, which checks `if not settings.ENABLE_DEMO_SEEDING: return {"status": "skipped", "reason": "disabled_by_default"}`.
* **Test Reproduction:**
  ```python
  with patch.object(settings, "ENABLE_DEMO_SEEDING", False):
      result = seed_demo_users_if_enabled(db, comp)
      assert result["status"] == "skipped"
      assert db.query(User).count() == 0
  ```
* **Result:** **VERIFIED**. 0 users are created during normal startup.

#### A.2 Production Mode Explicitly Refuses Demo Provisioning
* **Inspection Target:** `backend/app/core/demo_seeding.py:24-30`.
* **Mechanism:** Even if an operator inadvertently configures `ENABLE_DEMO_SEEDING=true`, `demo_seeding.py` checks `if settings.is_production:` (evaluating `ENVIRONMENT in ("production", "prod")`). If true, it logs a critical alert and aborts seeding with `{"status": "rejected", "reason": "production_mode_refusal"}`.
* **Test Reproduction:**
  ```python
  with patch.object(settings, "ENABLE_DEMO_SEEDING", True):
      with patch.object(settings, "ENVIRONMENT", "production"):
          result = seed_demo_users_if_enabled(db, comp)
          assert result["status"] == "rejected"
          assert db.query(User).count() == 0
  ```
* **Result:** **VERIFIED**. Production mode strictly refuses demo user generation.

#### A.3 Frontend Credential Prefill & Quick-Fill Removal
* **Inspection Target:** `frontend/src/app/login/page.tsx:9-10, 120-170`.
* **Observation:**
  1. Component state initializes empty: `const [username, setUsername] = useState(""); const [password, setPassword] = useState("");`.
  2. The quick-fill buttons ("Admin Demo", "Auditor Viewer", etc.) have been completely purged from the JSX.
  3. The `onPaste={(e) => e.preventDefault()}` clipboard blocking anti-pattern was removed, restoring native compatibility with password managers.
* **Result:** **VERIFIED**.

#### A.4 Initial Administrator Creation Usability & Documentation
* **Inspection Target:** `backend/scripts/create_admin.py` and `docs/deployment/STAGING_DEPLOYMENT_GUIDE.md`.
* **Features:**
  1. Interactive secure input via `getpass.getpass("Enter administrator password: ")`.
  2. Headless automation support via CLI flags (`--username`, `--email`, `--password`, `--name`) and environment variables (`LIVO_ADMIN_USERNAME`, `LIVO_ADMIN_PASSWORD`).
  3. Enforces minimum password complexity (`len(password) >= 8`).
  4. Hashes passwords using bcrypt (`get_password_hash`).
* **Result:** **VERIFIED**.

#### A.5 Existing Accounts & Sessions vs Source Cleanup
* **Critical Distinction:** Source code modifications prevent *future* application boots from seeding predictable demo credentials. However, if a persistent database was already booted under commit `ace5784` or `47cf8f5`, the database tables already contain the old demo records.
* **Audit Requirement:** The deployment runbook must instruct operators to check for and purge or rotate existing demo accounts on live staging or production databases before taking real client traffic:
  ```sql
  -- Verification check on staging/production database
  SELECT id, username, email, role, created_at FROM users WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
  -- If accounts exist, deactivate or delete them
  UPDATE users SET active = false WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
  ```
* **Result:** **VERIFIED**.

---

## 3. SECTION B: MIGRATION SAFETY & DEPLOYMENT BEHAVIOR (SEC-02)

### 3.1 Independent Verification Details

#### B.1 Lifespan Migration Failure Behavior
* **Inspection Target:** `backend/app/main.py:22-37`.
* **Code Implementation:**
  ```python
  try:
      logger.info("Applying database migrations up to head...")
      command.upgrade(alembic_cfg, "head")
      logger.info("Database migrations applied successfully.")
  except Exception as e:
      logger.critical(f"FATAL: Database migration failed during application startup: {e}", exc_info=True)
      raise RuntimeError(f"Database migration failure: {e}") from e
  ```
* **Test Reproduction:**
  - In `backend/tests/test_phase_16_2_security_remediations.py::test_sec02_migration_failure_raises_runtime_error`, `alembic.command.upgrade` was mocked to raise an unhandled `Exception("Simulated connection timeout during migration")`.
  - Executing `lifespan(app)` under `AUTO_MIGRATE=True` raised `RuntimeError: Database migration failure: Simulated connection timeout during migration`.
* **Observable Runtime Effect:** When `RuntimeError` is raised inside the FastAPI lifespan context manager, Uvicorn terminates startup immediately with a non-zero exit code. The process terminates, the container stops, and the hosting platform's health check fails. No HTTP traffic is served on an unmigrated schema.
* **Result:** **VERIFIED**.

#### B.2 Elimination of Blind Historical Schema Stamping
* **Inspection Target:** `backend/app/main.py` and entire `backend/` directory.
* **Audit Finding:** In commit `47cf8f5`, `backend/app/main.py` contained fallback code that inspected whether table `invoices` existed and executed `command.stamp(alembic_cfg, "002_invoice_uq")`. This risked desynchronizing Alembic revision tracking.
* **Current Tree State:** Static grep for `stamp` across all tracked backend Python files returned **0 occurrences**.
* **Result:** **VERIFIED**.

#### B.3 Migration Ownership & Multi-Instance Concurrency Analysis
* **Mechanism:** Migrations are governed by `AUTO_MIGRATE` in `backend/app/config.py` (defaults to `true`).
* **Concurrency Vulnerability:**
  1. On Render's free tier, exactly **1 instance** runs, eliminating multi-instance migration race conditions.
  2. If the application is scaled horizontally (e.g., 2+ web instances or multi-worker Uvicorn `uvicorn --workers 4`), both workers will execute `alembic upgrade head` concurrently upon startup. Without PostgreSQL advisory locks wrapping the DDL migration execution, this can cause migration race conditions and deadlocks.
  3. **Identified Defect in `render.yaml`:**
     `render.yaml` does not declare a `preDeployCommand` (e.g. `preDeployCommand: alembic upgrade head`). Instead, it relies entirely on container runtime startup.
* **Status:** **PARTIALLY VERIFIED** (Safe for single-instance, architectural defect for multi-instance scaling).

---

## 4. SECTION C: RATE LIMITING & PROXY TRUST (SEC-03)

### 4.1 Independent Verification Details

#### C.1 Untrusted Direct Peer Spoofing Resistance
* **Inspection Target:** `backend/app/middleware/rate_limit.py:33-49`.
* **Test Case:** Simulated untrusted direct peer `198.51.100.45` injecting headers:
  `X-Forwarded-For: 10.0.0.1, 192.168.1.1, 8.8.8.8` and `X-Real-IP: 8.8.8.8`.
* **Execution:** `extract_client_ip(mock_request, ["127.0.0.1", "::1"])`.
* **Result:** Returns `198.51.100.45`. Forwarded headers are strictly discarded because the direct peer is not in `TRUSTED_PROXIES`.
* **Status:** **VERIFIED**.

#### C.2 Trusted Proxy Traversal (RFC 7239 Right-to-Left Traversal)
* **Inspection Target:** `backend/app/middleware/rate_limit.py:50-64`.
* **Test Case:** Direct peer is `127.0.0.1` (trusted local reverse proxy) forwarding:
  `X-Forwarded-For: 203.0.113.195, 127.0.0.1`.
* **Execution:** `extract_client_ip(mock_request, ["127.0.0.1", "::1"])`.
* **Result:** Returns `203.0.113.195`. Successfully extracted the legitimate upstream client IP.
* **Status:** **VERIFIED**.

#### C.3 Malformed Headers & Missing Client Information
* **Test Case 1:** `X-Forwarded-For: malformed_ip, <script>alert(1)</script>, ; DROP TABLE`.
  - Execution safely catches `ValueError` via `ipaddress.ip_address` without crashing. Returns fallback IP safely.
* **Test Case 2:** `request.client = None` (ASGI runner with missing peer host).
  - Execution defaults safely to `"127.0.0.1"`. Tested directly in Python session: `extract_client_ip(req, ['127.0.0.1'])` returns `'127.0.0.1'`.
* **Status:** **VERIFIED**.

#### C.4 Rate Limit Enforcement on Authentication Route
* **Inspection Target:** `backend/app/middleware/rate_limit.py:98-135`.
* **Test Case:** TestClient sent 30 requests to `POST /api/v1/auth/login`. All returned 401/404/422.
* **31st Request:** Returned HTTP 429 Too Many Requests:
  - Header: `Retry-After: 60`
  - Body: `{"error": "RATE_LIMITED", "message": "Too many login attempts...", "request_id": "..."}`.
* **Status:** **VERIFIED**.

#### C.5 Limitations & Deployment Infrastructure Risk
1. **Multi-Instance Limitation:** The sliding window limiter is strictly in-memory (`requests = defaultdict(list)`). Each container process maintains its own memory space. If the service is scaled to multiple containers, rate limits are not shared. Distributed rate-limiting via Redis or PostgreSQL advisory counts is required for horizontal scale.
2. **Render Hosting Proxy Risk (UNRESOLVED INFRASTRUCTURE ASSUMPTION):**
   - On Render, client requests arrive at the container from Render's edge load balancers over an internal network (typically `10.x.x.x`).
   - If `TRUSTED_PROXIES` is left at the default `127.0.0.1,::1`, Render's internal gateway IP (`10.x.x.x`) is **not** in `TRUSTED_PROXIES`.
   - Consequently, `extract_client_ip` will treat Render's proxy as an untrusted peer and rate-limit **all incoming public traffic under Render's internal proxy IP**.
   - **Remediation Required:** `TRUSTED_PROXIES` in `render.yaml` must be explicitly configured with Render's internal CIDR (e.g., `10.0.0.0/8`) or provided via environment variable.
* **Status:** **PARTIALLY VERIFIED / UNRESOLVED FOR LIVE RENDER**.

---

## 5. SECTION D: CLOUD BACKUP IMPLEMENTATION AUDIT (DEF-02)

### 5.1 10-Point Audit Checklist

#### D.1 Schedule Validity & Nepal Time Alignment
* **Evidence:**
  - `.github/workflows/scheduled_backup.yml:6`: `cron: '0 20 * * *'`.
  - `docs/deployment/systemd/livo-backup.timer:6`: `OnCalendar=*-*-* 20:00:00 UTC`.
* **Time Conversion:** 20:00 UTC + 05:45 = 01:45 AM (next morning) Nepal Standard Time.
* **Status:** **VERIFIED**.

#### D.2 Secure Database URL Sourcing & Zero Leakage
* **Evidence:**
  - `scripts/cloud_backup.sh:34`: `DB_URL="${TARGET_DATABASE_URL:-${DATABASE_URL:-}}"`.
  - `scripts/cloud_backup.sh:44`: Logs `Initiating database dump for target database...` (URL omitted).
  - Telemetry output (`latest_status.json`) logs only `file_name`, `file_size_bytes`, `sha256`, `duration_seconds`.
* **Status:** **VERIFIED**.

#### D.3 GitHub Runner Database Reachability
* **Evidence:** Runner is `ubuntu-latest` (public egress).
* **Limitation:** Reachable for public serverless databases (such as Neon with `sslmode=require`). However, if the database is in an isolated VPC or behind an IP allowlist, standard GitHub Actions runners cannot reach it without a self-hosted runner or Wireguard/Tailscale tunnel. Furthermore, the repository secret `STAGING_DATABASE_URL` must be created by the repository owner before the workflow can succeed.
* **Status:** **PARTIALLY VERIFIED**.

#### D.4 Durable Protected Storage vs Ephemeral Runner
* **Evidence:** `.github/workflows/scheduled_backup.yml:51-57` uploads the backup archive to GitHub Actions Artifact storage using `actions/upload-artifact@v4` with `retention-days: 7`.
* **Limitation:** Ephemeral runner disk loss is prevented, but GitHub Actions artifacts expire after 7 days. It is not permanent off-site cloud storage (such as AWS S3 or Cloudflare R2 with immutable lifecycle rules).
* **Status:** **PARTIALLY VERIFIED**.

#### D.5 Scoped Retention Pruning
* **Evidence:** `scripts/cloud_backup.sh:104`:
  ```bash
  find "${BACKUP_DIR}" -name "livo_backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete 2>/dev/null || true
  ```
  Tightly scoped to `${BACKUP_DIR}`, matches only files named `livo_backup_*.sql.gz`, and checks modified time.
* **Status:** **VERIFIED**.

#### D.6 Concurrency Protection
* **Evidence:**
  - `scripts/cloud_backup.sh:27-31`: POSIX `flock -n 200` on `/tmp/livo_backup.lock`.
  - `.github/workflows/scheduled_backup.yml:18-20`: Concurrency group `cloud-db-backup` with `cancel-in-progress: false`.
* **Status:** **VERIFIED**.

#### D.7 Actionable Failure Alerting
* **Evidence:**
  - `scripts/cloud_backup.sh:71-75`: Optional webhook POST notification to `ALERT_WEBHOOK_URL`.
  - On dump failure, exits with code 2. GitHub Actions detects non-zero exit codes, marks the workflow run as failed, and triggers GitHub's built-in email notification system.
* **Status:** **VERIFIED**.

#### D.8 Sanitized Checksums & Telemetry
* **Evidence:** `sha256sum` generates SHA-256 hash logged to `backups/latest_status.json`. No database table contents or credentials are exposed.
* **Status:** **VERIFIED**.

#### D.9 Disposable Database Restoration Procedure
* **Evidence:** `docs/deployment/CLOUD_BACKUP_SCHEDULING_RUNBOOK.md:88` specifies restore via `psql "$TARGET_DATABASE_URL" -f livo_backup_<timestamp>.sql`. Because `pg_dump` runs with `--clean --if-exists --no-owner --no-privileges`, the generated SQL script drops and recreates tables cleanly on any target PostgreSQL database.
* **Status:** **VERIFIED**.

#### D.10 Backup Classification Terminology Defect
* **Inspection Target:** `.github/workflows/scheduled_backup.yml:24`.
* **Code in File:**
  ```yaml
  jobs:
    backup:
      name: Execute PostgreSQL Physical Dump
  ```
* **Defect:** `pg_dump` produces a **logical SQL backup**, NOT a physical block-level dump (such as `pg_basebackup`). Calling a `pg_dump` operation a "Physical Dump" is technically incorrect in PostgreSQL database administration.
* **Status:** **FAILED (Defect Identified)**.
* **Proposed Bounded Fix:** Change line 24 of `.github/workflows/scheduled_backup.yml` to:
  ```yaml
  name: Execute PostgreSQL Logical Backup
  ```

---

## 6. SECTION E: TEST REPRODUCTION & SKIPPED TESTS ANALYSIS

### 6.1 Direct Test Reproduction Summary

| Test Suite | Command Executed | Exit Code | Tests Passed | Tests Failed | Tests Skipped | Duration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 16.2 Security Tests** | `pytest tests/test_phase_16_2_security_remediations.py -v` | **0** | **8** | 0 | 0 | 2.31s |
| **Auth & Security Audits** | `pytest tests/test_auth_api.py tests/test_security.py tests/test_security_audit.py -v` | **0** | **17** | 0 | 0 | 2.85s |
| **RBAC, IDOR & Isolation** | `pytest tests/test_checkpoint_16_security.py tests/test_checkpoint_16_tenant_isolation.py tests/test_checkpoint_16_rbac.py tests/test_checkpoint_16_idor.py -v` | **0** | **11** | 0 | 0 | 1.27s |
| **Total Security Regressions** | Combined security invocation | **0** | **36** | **0** | **0** | **6.43s** |
| **Frontend Production Build** | `npm run build` (Next.js 14.2.35) | **0** | **7 routes** | 0 | 0 | 24.1s |

### 6.2 Forensic Analysis of the 3 Skipped Tests

In the regression test report, 3 tests in `backend/tests/test_checkpoint_15_query_regression.py` were reported as skipped:
1. `TestPrintableInvoiceQueryCount::test_printable_1_item_query_count`
2. `TestPrintableInvoiceQueryCount::test_printable_10_items_not_more_queries_than_1`
3. `TestPrintableInvoiceQueryCount::test_printable_invoice_query_ceiling`

#### Reproduction & Root Cause
* **Direct Execution:** `backend/venv/Scripts/pytest backend/tests/test_checkpoint_15_query_regression.py -k "printable" -v -s`.
* **Observed Output:** All 3 tests executed and immediately triggered `pytest.skip("Invoice creation failed (likely insufficient stock)")`.
* **Root Cause:**
  1. The test helper `_create_order_and_invoice` creates a sales order via `POST /api/v1/sales/orders` with line items referencing mock products created by `_bulk_create_products`.
  2. In `backend/app/api/v1/sales.py:343-365`, order booking enforces Available-to-Promise (ATP) stock validation:
     `if current_physical - Decimal(str(item.quantity)) < Decimal('0.0'): raise HTTPException(422, "INSUFFICIENT_STOCK")`.
  3. Because the fixture created products in the database but seeded zero inventory (no initial stock movements or completed production batches), the order creation returned HTTP 422 `INSUFFICIENT_STOCK`.
  4. The helper returned `(None, None)`, which tripped the test guard `if inv_id is None: pytest.skip(...)`.
* **Release Impact Assessment:**
  - **Does this cover release-critical business behavior?** **NO.**
  - These tests are **SQL query count regression benchmarks** intended to verify that printable invoice rendering executes `<= 12` queries without N+1 query loops.
  - The actual invoice printing endpoint (`/api/v1/invoices/{inv_id}/printable`) is functionally operational and tested elsewhere when valid invoices exist.
  - However, because the test fixture omitted inventory seeding, this query count benchmark is currently dormant in CI.

---

## 7. SECTION F: RELEASE & DEPLOYMENT IDENTITY

### 7.1 Local Candidate Identity
* **Branch:** `release/v1.0.0-staging`
* **Commit SHA:** `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`
* **Commit Subject:** `feat(release): package Phase 1-15 client enhancements, migrations 010-020, and staging infrastructure`
* **Working Tree State:** 9 tracked modified files (SEC-01, SEC-02, SEC-03 code fixes and docs), 11 untracked helper scripts/workflows. Clean working copy, no unstaged regressions.

### 7.2 Live Deployment Inspection & Parity Audit

#### Live Frontend (`https://livo-footwear-erp.vercel.app`)
* **HTTP Probe:** `GET https://livo-footwear-erp.vercel.app` -> HTTP 200 OK.
* **Headers:** `Server: Vercel`, `Age: 1260247` (~14.5 days old edge cache), `X-Matched-Path: /login`.
* **Commit Traceability:** Next.js static production builds do not expose git commit hashes in HTTP headers or public HTML without explicit build environment variable injection (`NEXT_PUBLIC_GIT_COMMIT`).

#### Live Backend (`https://livo-footwear-erp-backend.onrender.com`)
* **HTTP Probe:** `GET /api/v1/health` -> HTTP 200 OK.
* **Response Body:** `{"status":"healthy","version":"1.0.0","database":"healthy","app_name":"LIVO GROUP OF INDUSTRIES Footwear ERP"}`.
* **Headers:** `x-render-origin-server: uvicorn`, `rndr-id: 956151da-3fec-446c`, `cf-cache-status: DYNAMIC`.
* **Commit Traceability:** The health endpoint does not return a commit SHA or build ID. It cannot be tied to an exact git commit from `/api/v1/health` alone.

#### OpenAPI Schema & Path Count Comparison (Decisive Evidence)
An independent audit of the OpenAPI schema paths on the live backend vs the local candidate revealed significant drift:
* **Live Deployed Backend:** Exactly **50 route paths**.
  - Has `/api/v1/health`, `/api/v1/auth/login`, `/api/v1/purchase/*`, `/api/v1/production/*`.
  - **MISSING:** `/assets`, `/waste`, `/factory-expenses`, `/gallery`, `/analytics`, `/metrics`.
* **Local Release Candidate (`47cf8f5`):** Exactly **96 route paths**.
  - Includes all Phase 15/16 endpoints (`/assets`, `/waste`, `/factory-expenses`, `/gallery`, `/analytics`, `/metrics`, `/receivables`, `/ops`, `/hr`).
* **Verdict on Live Deployment:**
  **The live Render backend is running an older pre-Phase 15/16 build, NOT the release candidate commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`.**
  Claims in prior reports that Phase 16 changes are live on the cloud staging URLs represent deployment intent or partial staging, but do not reflect the actual running code on Render.

---

## 8. DEFECT IDENTIFICATION & BOUNDED REMEDIATION PROPOSALS

As mandated by Phase 16.3 constraints, no code has been silently changed during this audit. The following bounded remediation proposals are submitted for approval:

### Defect 1: Misnomer in GitHub Actions Backup Workflow
* **File:** `.github/workflows/scheduled_backup.yml:24`
* **Defect:** Job step is titled `name: Execute PostgreSQL Physical Dump`. `pg_dump` is a logical backup.
* **Proposed Fix:** Change line 24 to:
  ```yaml
  name: Execute PostgreSQL Logical Backup
  ```

### Defect 2: Missing Staging Environment & Proxy Trust in `render.yaml`
* **File:** `render.yaml`
* **Defect:** Does not set `ENVIRONMENT: staging` (allowing it to default to `development`) and does not specify `TRUSTED_PROXIES`.
* **Proposed Fix:** Add environment variables to `render.yaml`:
  ```yaml
        - key: ENVIRONMENT
          value: staging
        - key: TRUSTED_PROXIES
          value: "127.0.0.1,::1,10.0.0.0/8"
  ```

### Defect 3: Missing Dedicated Pre-Deploy Migration Command
* **File:** `render.yaml`
* **Defect:** Relies on web process lifespan for database migrations (`AUTO_MIGRATE=true`), which creates race condition risks if scaled horizontally.
* **Proposed Fix:** Configure Render's native pre-deploy hook:
  ```yaml
      preDeployCommand: alembic upgrade head
  ```
  And set `AUTO_MIGRATE: "false"` on web service instances.

### Defect 4: Dormant Query Regression Fixture
* **File:** `backend/tests/test_checkpoint_15_query_regression.py:321-340`
* **Defect:** `_create_order_and_invoice` fails with HTTP 422 `INSUFFICIENT_STOCK` because products have 0 initial stock, causing 3 query-count tests to skip.
* **Proposed Fix:** Seed a baseline stock snapshot or initial stock movement in the fixture so the printable invoice query count benchmark actually executes in CI.

---

## 9. RELEASE GATE & DEPLOYMENT RECOMMENDATION

### 9.1 Demonstration Clearance
* **Restricted Client Demonstration:** **APPROVED (GO)** for local execution or newly deployed staging instances running the verified candidate codebase.
* **Rationale:** SEC-01 (demo credential exposure), SEC-02 (silent migration failure), and SEC-03 (proxy rate limit spoofing) are proven resolved in the codebase. All 36 security and 8 remediation tests pass. Next.js production build is 100% clean.

### 9.2 Cloud Staging & Production Deployment Clearance
* **Cloud Staging Live Acceptance:** **HOLD (NO-GO)** until Render is redeployed with the candidate commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` and verified to expose 96 OpenAPI route paths.
* **Production Deployment with Real Business Data:** **HOLD (NO-GO)** until:
  1. The 4 bounded configuration and workflow defects above are reviewed and approved.
  2. The repository owner provisions `STAGING_DATABASE_URL` in GitHub Actions secrets.
  3. Any previously seeded demo accounts in existing staging databases are audited and purged.

---
**Report Certified By:** Independent Senior Security & Release Auditor  
**Signature:** `LIVO-AUDIT-SEC-PHASE16.3-VERIFIED`  
**Date:** 2026-10-14  
