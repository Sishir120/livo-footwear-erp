# LIVO Footwear ERP — Day 7.1 Staging Acceptance & Boundary Checklist

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Enterprise Cloud Deployment Gate & Boundary Segregation  
**Target Scope:** Controlled 1-Week Synthetic Evaluation

---

## 1. Executive Summary & Verification Boundaries

To maintain rigorous truth in reporting, deployment evidence is strictly classified across five distinct verification tiers. We distinguish local test execution from configuration inspection, and explicitly identify items that cannot be proven until an operator provisions the live staging host.

---

## 2. 5-Tier Verification Boundary Matrix

| Verification Tier | Description & Scope | Verified Items / Evidence |
| :--- | :--- | :--- |
| **Tier 1: Verified Local Behavior** | Tested live against running local frontend (`:3000`) and backend (`:8000`). | • 10/10 automated browser UI checks passed (`day7_browser_gate`).<br>• Fixed `toFixed` bug in `HRManagementView.tsx`.<br>• Next.js `/api/*` reverse-proxy rewrites.<br>• 61 backend unit/regression tests passed (`exit code 0`). |
| **Tier 2: Verified Isolated PostgreSQL Tests** | Tested against local isolated PostgreSQL 16 instances. | • Full database dump + storage archive disaster recovery drill (`test_day_4_file_and_database_recovery.py`) in 17.56s.<br>• 100% SHA-256 byte parity on restore.<br>• PostgreSQL advisory locks on migrations.<br>• Negative tests for path traversal & checksum mismatch. |
| **Tier 3: Configuration Verified by Source Code Inspection** | Validated via Python AST & runtime logic analysis. | • Startup crash on missing `SECRET_KEY`.<br>• `COOKIE_SECURE=True` when `LIVO_DEV_MODE=false`.<br>• `app/core/demo_seeding.py` fail-closed refusal in production and staging.<br>• `_sanitize_db_error` masking connection strings in logs.<br>• Right-to-left `X-Forwarded-For` traversal in `rate_limit.py`. |
| **Tier 4: Requires Staging Host Verification** | Must be verified by operator on staging server before granting evaluator access. | • Public TLS certificate handshake on port 443.<br>• Reverse proxy header preservation under public WAN.<br>• Managed PostgreSQL connectivity over VPC private network.<br>• Initial baseline backup execution on host storage. |
| **Tier 5: Requires Separate Operator Authorization** | Actions strictly prohibited without explicit user sign-off. | • Deploying artifacts to cloud compute instances.<br>• Binding public domain names or updating DNS records.<br>• Exposing port 443 to external networks.<br>• Issuing evaluation access credentials to client evaluators. |

---

## 3. Operator Pre-Deployment Checklist

Before requesting deployment authorization, the staging operator must verify:

- [ ] **Infrastructure & Network:**
  - [ ] Disposable staging VPS / container instance provisioned.
  - [ ] Isolated PostgreSQL 16 instance created with zero client data.
  - [ ] Port 5432 bound to private VPC / internal subnet only (zero internet ingress).
- [ ] **Configuration & Secrets:**
  - [ ] Fresh 256-bit `SECRET_KEY` generated (`python -c "import secrets; print(secrets.token_hex(32))"`).
  - [ ] `LIVO_DEV_MODE=false` set in staging `.env`.
  - [ ] `BACKEND_CORS_ORIGINS` set to the exact staging domain (no wildcards).
- [ ] **Provisioning & Demo Accounts:**
  - [ ] Initial boot performed with `ENVIRONMENT=test` and `ENABLE_DEMO_SEEDING=true` to apply schema `024_add_rate_limit_entries` and seed synthetic personas.
  - [ ] `.env` updated to `ENVIRONMENT=staging` and `ENABLE_DEMO_SEEDING=false` immediately following bootstrap.
  - [ ] Backend restarted to lock out any subsequent seeding.
- [ ] **Health & Disaster Recovery:**
  - [ ] `/api/v1/health/ready` probe checked (`HTTP 200 OK`, `status: ready`).
  - [ ] Baseline backup executed via `python -m app.services.backup_service`.
  - [ ] Backup manifest confirmed in `/app/backups/`.
- [ ] **Evaluator Access:**
  - [ ] Temporary evaluator passwords distributed over encrypted channel.
  - [ ] Evaluators informed of operational boundaries (synthetic data only, no double-entry GL, no mandatory batch dispatch).
- [ ] **Teardown Schedule:**
  - [ ] Scheduled teardown date set (maximum 7 days from authorization).
