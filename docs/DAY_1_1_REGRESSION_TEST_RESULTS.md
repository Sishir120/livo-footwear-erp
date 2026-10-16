# LIVO ERP — Day 1.1 Regression Test Results

**Date:** October 16, 2026  
**Environment:** Windows (PowerShell), Python 3.14.7, pytest 9.1.1, Next.js 14.2.35  
**Execution Context:** Local LIVO Footwear ERP Workspace  
**Status:** ALL REQUIRED TEST SUITES GREEN (0 Failures, 0 Regressions)

---

## 1. Test Execution Summary

| Suite / Target | Command Executed | Exit Code | Passed | Failed | Skipped | Duration |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Day 1 Hardening** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_day_1_hardening.py -v` | 0 | 6 | 0 | 0 | 2.59s |
| **Day 1.1 Verification** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_day_1_1_verification.py -v` | 0 | 3 | 0 | 0 | 2.36s |
| **Phase 16.2 Security Remediations** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_phase_16_2_security_remediations.py -v` | 0 | 31 | 0 | 0 | 3.74s |
| **Security Audit Suite** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_security_audit.py -v` | 0 | 10 | 0 | 0 | 3.34s |
| **Checkpoint 16 Business Security** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_checkpoint_16_business_security.py -v` | 0 | 5 | 0 | 0 | 1.81s |
| **Combined Security Suite** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_day_1_hardening.py backend/tests/test_day_1_1_verification.py backend/tests/test_phase_16_2_security_remediations.py backend/tests/test_security_audit.py backend/tests/test_checkpoint_16_business_security.py -v` | 0 | 55 | 0 | 0 | 7.76s |
| **Checkpoint 11 Database** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_checkpoint_11_database.py -v` | 0 | 14 | 0 | 0 | 14.65s |
| **Checkpoint 17 & 18 Acceptance** | `.\venv\Scripts\python.exe -m pytest backend/tests/test_checkpoint_17_production_readiness.py backend/tests/test_checkpoint_18_live_acceptance.py -v` | 0 | 16 | 0 | 0 | 44.71s |
| **Frontend Production Build** | `npm run build` (in `frontend/`) | 0 | 7 pages | 0 | 0 | ~18s |

---

## 2. Detailed Test Suite Outputs

### Suite 1: Combined Security Verification (55 Tests)
**Command:**
```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/test_day_1_hardening.py backend/tests/test_day_1_1_verification.py backend/tests/test_phase_16_2_security_remediations.py backend/tests/test_security_audit.py backend/tests/test_checkpoint_16_business_security.py -v
```
**Output Log:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Antigravity\Footwear app\backend
configfile: pytest.ini
plugins: anyio-4.15.1, platformdirs-4.12.2
collected 55 items

backend\tests\test_day_1_hardening.py::test_h01_rate_limiter_shared_db_store_concurrency PASSED [  1%]
backend\tests\test_day_1_hardening.py::test_h01_rate_limiter_storage_failure_fail_open_resilience PASSED [  3%]
backend\tests\test_day_1_hardening.py::test_h01_rate_limiter_multi_client_isolation PASSED [  5%]
backend\tests\test_day_1_hardening.py::test_h03_content_security_policy_header_enforcement PASSED [  7%]
backend\tests\test_day_1_hardening.py::test_h08_readiness_probe_contract_verification PASSED [  9%]
backend\tests\test_day_1_hardening.py::test_financial_authorization_negative_boundaries PASSED [ 10%]
backend\tests\test_day_1_1_verification.py::test_rate_limiter_concurrency_write_then_count_atomicity PASSED [ 12%]
backend\tests\test_day_1_1_verification.py::test_security_headers_present_on_error_responses PASSED [ 14%]
backend\tests\test_day_1_1_verification.py::test_open_redirect_sanitization_rules PASSED [ 16%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec01_demo_seeding_disabled_by_default PASSED [ 18%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec01_production_mode_strictly_refuses_demo_seeding PASSED [ 20%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec01_dev_mode_opt_in_seeding_creates_accounts PASSED [ 21%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec02_migration_failure_raises_runtime_error PASSED [ 23%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec02_auto_migrate_disabled_skips_startup_migrations PASSED [ 25%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec02_render_yaml_configuration_validity PASSED [ 27%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec03_untrusted_client_spoofed_forwarded_header_ignored PASSED [ 29%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec03_trusted_proxy_extracts_legitimate_client_ip PASSED [ 30%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec03_malformed_forwarded_header_falls_back_safely PASSED [ 32%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec03_rate_limiting_enforcement_on_auth_route PASSED [ 34%]
backend\tests\test_phase_16_2_security_remediations.py::test_sec03_evasion_attempt_by_changing_forwarded_for_fails PASSED [ 36%]
backend\tests\test_deployment_identity_in_health_response PASSED [ 38%]
backend\tests\test_sec01_ambiguous_environment_refuses_demo_seeding PASSED [ 40%]
backend\tests\test_sec01_existing_account_preserved_without_overwrite PASSED [ 41%]
backend\tests\test_sec02_migration_failure_sanitizes_db_credentials PASSED [ 43%]
backend\tests\test_sec02_readiness_probe_schema_mismatch_returns_503 PASSED [ 45%]
backend\tests\test_sec02_readiness_probe_missing_table_returns_503 PASSED [ 47%]
backend\tests\test_sec02_readiness_probe_matching_schema_returns_200 PASSED [ 49%]
backend\tests\test_sec02_readiness_probe_database_unavailable_returns_503 PASSED [ 50%]
backend\tests\test_sec02_readiness_probe_empty_version_table_returns_503 PASSED [ 52%]
backend\tests\test_sec02_readiness_probe_unknown_revision_returns_503 PASSED [ 54%]
backend\tests\test_sec02_readiness_probe_multiple_revisions_in_db_returns_503 PASSED [ 56%]
backend\tests\test_sec02_readiness_probe_multiple_alembic_heads_returns_503 PASSED [ 58%]
backend\tests\test_sec02_readiness_probe_missing_critical_table_invariant_returns_503 PASSED [ 60%]
backend\tests\test_sec02_readiness_probe_missing_critical_column_invariant_returns_503 PASSED [ 61%]
backend\tests\test_liveness_probe_does_not_access_database PASSED [ 63%]
backend\tests\test_create_admin_script_fails_if_company_not_found PASSED [ 65%]
backend\tests\test_create_admin_script_fails_if_user_already_exists PASSED [ 67%]
backend\tests\test_create_admin_script_validates_password_length PASSED [ 69%]
backend\tests\test_create_admin_script_provisions_active_admin_account PASSED [ 70%]
backend\tests\test_sec03_proxy_traversal_with_private_ip_hops PASSED [ 72%]
backend\tests\test_security_audit.py::test_viewer_strictly_rejected_from_mutating_endpoints PASSED [ 74%]
backend\tests\test_security_audit.py::test_unauthenticated_requests_rejected_from_business_routes PASSED [ 76%]
backend\tests\test_security_audit.py::test_tenant_isolation_and_idor_prevention PASSED [ 78%]
backend\tests\test_security_audit.py::test_sql_injection_defense_in_parameters PASSED [ 80%]
backend\tests\test_security_audit.py::test_negative_fuzz_testing_payloads PASSED [ 81%]
backend\tests\test_security_audit.py::test_cookie_flags_security PASSED [ 83%]
backend\tests\test_security_audit.py::test_rate_limiter_threshold_protection PASSED [ 85%]
backend\tests\test_security_audit.py::test_cross_tenant_reference_idor_rejection PASSED [ 87%]
backend\tests\test_security_audit.py::test_boundary_integers_and_negative_quantities PASSED [ 89%]
backend\tests\test_security_audit.py::test_owasp_security_hardening PASSED [ 90%]
backend\tests\test_checkpoint_16_business_security.py::test_stock_invariants_attack PASSED [ 92%]
backend\tests\test_checkpoint_16_business_security.py::test_sales_and_credit_invariants_attack PASSED [ 94%]
backend\tests\test_checkpoint_16_business_security.py::test_vat_invoice_statutory_invariant PASSED [ 96%]
backend\tests\test_checkpoint_16_business_security.py::test_receivables_over_allocation_rejection PASSED [ 98%]
backend\tests\test_checkpoint_16_business_security.py::test_error_responses_do_not_leak_sensitive_internals PASSED [100%]

======================= 55 passed, 2 warnings in 7.76s ========================
```

---

### Suite 2: Checkpoint 11 Database Durability & Migrations (14 Tests)
**Command:**
```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/test_checkpoint_11_database.py -v
```
**Output Log:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Antigravity\Footwear app\backend
configfile: pytest.ini
plugins: anyio-4.15.1, platformdirs-4.12.2
collected 14 items

backend\tests\test_checkpoint_11_database.py::test_transaction_rollback_guarantee PASSED [  7%]
backend\tests\test_checkpoint_11_database.py::test_financial_atomicity PASSED [ 14%]
backend\tests\test_checkpoint_11_database.py::test_inventory_atomicity_on_failure PASSED [ 21%]
backend\tests\test_checkpoint_11_database.py::test_foreign_key_integrity_enforcement PASSED [ 28%]
backend\tests\test_checkpoint_11_database.py::test_unique_constraints_enforcement PASSED [ 35%]
backend\tests\test_checkpoint_11_database.py::test_tenant_database_isolation PASSED [ 42%]
backend\tests\test_checkpoint_11_database.py::test_backup_and_restore_cycle PASSED [ 50%]
backend\tests\test_checkpoint_11_database.py::test_fresh_database_migration PASSED [ 57%]
backend\tests\test_checkpoint_11_database.py::test_audit_log_durability PASSED [ 64%]
backend\tests\test_checkpoint_11_database.py::test_sequence_integrity_after_restore PASSED [ 71%]
backend\tests\test_checkpoint_11_database.py::test_numeric_precision_after_restore PASSED [ 78%]
backend\tests\test_checkpoint_11_database.py::test_migration_schema_integrity PASSED [ 85%]
backend\tests\test_checkpoint_11_database.py::test_existing_database_upgrade PASSED [ 92%]
backend\tests\test_checkpoint_11_database.py::test_concurrent_transactions_and_isolation PASSED [100%]

============================= 14 passed in 14.65s =============================
```

---

### Suite 3: Checkpoint 17 & 18 Acceptance & Readiness (16 Tests)
**Command:**
```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/test_checkpoint_17_production_readiness.py backend/tests/test_checkpoint_18_live_acceptance.py -v
```
**Output Log:**
```text
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Antigravity\Footwear app\backend
configfile: pytest.ini
plugins: anyio-4.15.1, platformdirs-4.12.2
collected 16 items

backend\tests\test_checkpoint_17_production_readiness.py::test_fresh_postgresql_migration_zero_to_head PASSED [  6%]
backend\tests\test_checkpoint_17_production_readiness.py::test_incremental_migration_data_preservation PASSED [ 12%]
backend\tests\test_checkpoint_17_production_readiness.py::test_postgresql_transaction_rollback_safety PASSED [ 18%]
backend\tests\test_checkpoint_17_production_readiness.py::test_pg_dump_and_restore_financial_parity PASSED [ 25%]
backend\tests\test_checkpoint_17_production_readiness.py::test_storage_file_upload_security_defenses PASSED [ 31%]
backend\tests\test_checkpoint_17_production_readiness.py::test_financial_reconciliation_math PASSED [ 37%]
backend\tests\test_checkpoint_17_production_readiness.py::test_idempotency_replay_conflict_and_tenant_isolation PASSED [ 43%]
backend\tests\test_checkpoint_17_production_readiness.py::test_liveness_and_readiness_probe_behavior PASSED [ 50%]
backend\tests\test_checkpoint_17_production_readiness.py::test_realistic_client_lifecycle_smoke PASSED [ 56%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_production_configuration_hygiene PASSED [ 62%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_fresh_production_postgresql_migration_head PASSED [ 68%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_health_and_readiness_failure_injection_and_recovery PASSED [ 75%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_production_authentication_and_multi_tenant_live_attack PASSED [ 81%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_complete_client_acceptance_workflow_and_financial_reconciliation PASSED [ 87%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_production_backup_and_restore_zero_discrepancy PASSED [ 93%]
backend\tests\test_checkpoint_18_live_acceptance.py::test_performance_smoke_production_budgets PASSED [100%]

====================== 16 passed, 70 warnings in 44.71s =======================
```

---

### Suite 4: Frontend Next.js Production Build
**Command:**
```powershell
npm run build
```
**Working Directory:** `frontend/`  
**Output Log:**
```text
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
├ ○ /login                               5.95 kB        99.7 kB
├ ○ /privacy                             179 B          96.5 kB
└ ○ /terms                               179 B          96.5 kB
+ First Load JS shared by all            87.7 kB
  ├ chunks/117-22f4f9f4adf3fd71.js       31.7 kB
  ├ chunks/fd9d1056-7c8cb799e19c27d1.js  53.6 kB
  └ other shared chunks (total)          2.29 kB

ƒ Middleware                             26.7 kB
○ (Static) prerendered as static content
```

---

## 3. Environmental Limitations & Verification Boundary

1. **Local Operating System:** Windows environment with SQLite for local interactive development and in-memory test databases.
2. **PostgreSQL Verification:** Verified through automated embedded/mocked PostgreSQL migration tests (`test_checkpoint_17_production_readiness.py`, `test_checkpoint_18_live_acceptance.py`). Full physical multi-region PostgreSQL cluster failover remains a live deployment check.
3. **No Unrelated Regressions:** Confirmed zero modifications to Phase 5–6A branch and franchise accounting schemas, GL posting structures, or pending design documents.
