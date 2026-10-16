# Day 1 Regression Test Results

**Date:** 2026-10-16  
**Execution Context:** Local Python 3.14 virtual environment + Next.js 14.2.35 production builder  
**Working Directory:** `d:\Antigravity\Footwear app`  
**Command Runner:** `.\venv\Scripts\python.exe -m pytest` and `npm run build`

---

## 1. Test Summary

| Test Suite | Tests Executed | Passed | Failed | Skipped | Status |
|---|---|---|---|---|---|
| `backend/tests/test_day_1_hardening.py` | 6 | 6 | 0 | 0 | **PASS** |
| `backend/tests/test_phase_16_2_security_remediations.py` | 31 | 31 | 0 | 0 | **PASS** |
| `backend/tests/test_security_audit.py` | 10 | 10 | 0 | 0 | **PASS** |
| `backend/tests/test_checkpoint_16_business_security.py` | 5 | 5 | 0 | 0 | **PASS** |
| **Total Backend Tests** | **52** | **52** | **0** | **0** | **100% PASS** |
| Frontend Production Build (`npm run build`) | 7 routes | 7 | 0 | 0 | **COMPILED OK** |

---

## 2. Detailed Results by Test Case

### A. Day 1 Hardening Suite (`test_day_1_hardening.py`)

```
backend/tests/test_day_1_hardening.py::test_h01_rate_limiter_shared_db_store_concurrency PASSED [16%]
backend/tests/test_day_1_hardening.py::test_h01_rate_limiter_storage_failure_fail_open_resilience PASSED [33%]
backend/tests/test_day_1_hardening.py::test_h01_rate_limiter_multi_client_isolation PASSED [50%]
backend/tests/test_day_1_hardening.py::test_h03_content_security_policy_header_enforcement PASSED [66%]
backend/tests/test_day_1_hardening.py::test_h08_readiness_probe_contract_verification PASSED [83%]
backend/tests/test_day_1_hardening.py::test_financial_authorization_negative_boundaries PASSED [100%]
```

#### Detailed Verifications:
- **`test_h01_rate_limiter_shared_db_store_concurrency`**:
  - Sent 30 failed login attempts from a test client.
  - Inspected database `rate_limit_entries` table directly: verified 30 distinct rows logged with timestamps.
  - Verified 31st request triggers HTTP 429 Too Many Requests with:
    - `"error": "RATE_LIMITED"`
    - `"Retry-After": "60"`
    - Request correlation ID attached.
- **`test_h01_rate_limiter_storage_failure_fail_open_resilience`**:
  - Mocked database connection failure during `_check_database_rate_limit()`.
  - Verified the middleware logged a warning and failed open to the in-process sliding window (`self.requests`), preventing a 500 Internal Server Error.
- **`test_h01_rate_limiter_multi_client_isolation`**:
  - Simulated 30 failed login requests from Client A (`198.51.100.1`) behind a trusted reverse proxy (`127.0.0.1`).
  - Verified Client A is blocked with HTTP 429.
  - Verified Client B (`203.0.113.88`) connecting concurrently is NOT blocked (receives normal auth challenge 401).
- **`test_h03_content_security_policy_header_enforcement`**:
  - Verified `Content-Security-Policy` header is present on outgoing API responses.
  - Asserted presence of `default-src 'self'`, `frame-ancestors 'none'`, `script-src 'self' 'unsafe-inline'`, `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`, and `img-src 'self' data: blob: https:`.
- **`test_h08_readiness_probe_contract_verification`**:
  - Mocked healthy database connectivity and Alembic head: `/health/ready` returned HTTP 200 with `status: ready, database: healthy`.
  - Mocked database connection failure: `/health/ready` returned HTTP 503 with `status: unready, database: unhealthy`.
- **`test_financial_authorization_negative_boundaries`**:
  - Unauthenticated GET requests to `/api/v1/invoices`, `/api/v1/transfers`, and `/api/v1/purchases` returned HTTP 401 with `"detail": "Not authenticated. Session cookie missing."`.

---

### B. Pre-Existing Security & Remediation Suite (`test_phase_16_2_security_remediations.py`)

31/31 passed:
- `test_sec01_demo_seeding_disabled_by_default` PASSED
- `test_sec01_production_mode_strictly_refuses_demo_seeding` PASSED
- `test_sec01_dev_mode_opt_in_seeding_creates_accounts` PASSED
- `test_sec02_migration_failure_raises_runtime_error` PASSED
- `test_sec02_auto_migrate_disabled_skips_startup_migrations` PASSED
- `test_sec02_render_yaml_configuration_validity` PASSED
- `test_sec03_untrusted_client_spoofed_forwarded_header_ignored` PASSED
- `test_sec03_trusted_proxy_extracts_legitimate_client_ip` PASSED
- `test_sec03_malformed_forwarded_header_falls_back_safely` PASSED
- `test_sec03_rate_limiting_enforcement_on_auth_route` PASSED
- `test_sec03_evasion_attempt_by_changing_forwarded_for_fails` PASSED
- `test_deployment_identity_in_health_response` PASSED
- `test_sec01_ambiguous_environment_refuses_demo_seeding` PASSED
- `test_sec01_existing_account_preserved_without_overwrite` PASSED
- `test_sec02_migration_failure_sanitizes_db_credentials` PASSED
- `test_sec02_readiness_probe_schema_mismatch_returns_503` PASSED
- `test_sec02_readiness_probe_missing_table_returns_503` PASSED
- `test_sec02_readiness_probe_matching_schema_returns_200` PASSED
- `test_sec02_readiness_probe_database_unavailable_returns_503` PASSED
- `test_sec02_readiness_probe_empty_version_table_returns_503` PASSED
- `test_sec02_readiness_probe_unknown_revision_returns_503` PASSED
- `test_sec02_readiness_probe_multiple_revisions_in_db_returns_503` PASSED
- `test_sec02_readiness_probe_multiple_alembic_heads_returns_503` PASSED
- `test_sec02_readiness_probe_missing_critical_table_invariant_returns_503` PASSED
- `test_sec02_readiness_probe_missing_critical_column_invariant_returns_503` PASSED
- `test_liveness_probe_does_not_access_database` PASSED
- `test_create_admin_script_fails_if_company_not_found` PASSED
- `test_create_admin_script_fails_if_user_already_exists` PASSED
- `test_create_admin_script_validates_password_length` PASSED
- `test_create_admin_script_provisions_active_admin_account` PASSED
- `test_sec03_proxy_traversal_with_private_ip_hops` PASSED

---

### C. Frontend Production Build Verification

```
> livo-footwear-erp-frontend@1.0.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/7) ...
   Generating static pages (1/7) 
   Generating static pages (3/7) 
   Generating static pages (5/7) 
 ✓ Generating static pages (7/7)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    27.2 kB         121 kB
├ ○ /_not-found                          873 B          88.5 kB
├ ○ /login                               5.83 kB        99.6 kB
├ ○ /privacy                             179 B          96.5 kB
└ ○ /terms                               179 B          96.5 kB
+ First Load JS shared by all            87.7 kB
  ├ chunks/117-22f4f9f4adf3fd71.js       31.7 kB
  ├ chunks/fd9d1056-7c8cb799e19c27d1.js  53.6 kB
  └ other shared chunks (total)          2.29 kB

ƒ Middleware                             26.7 kB
○  (Static)  prerendered as static content
```

Exit code: `0` (Zero TypeScript, lint, or bundling errors).
