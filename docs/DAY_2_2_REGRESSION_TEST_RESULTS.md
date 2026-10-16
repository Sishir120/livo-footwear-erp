# Day 2.2 Regression Test Execution Log and Results

**Execution Date:** 2026-10-16  
**Execution Environment:** Windows 11 (build 10.0.26100), Python 3.14.7, pytest 9.1.1, SQLite / Embedded PostgreSQL (port 5433), Node v20.x, Next.js 14.2.35  
**Test Scope:** Independent verification of Day 2, Day 2.1, and Day 2.2 RBAC hardening, tenant isolation, HR field omission, admin lockout protection, and branch accounting.

---

## 1. Overall Test Execution Summary

| Suite / Target | Command Executed | Exit Code | Tests Passed | Tests Failed | Skipped | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Day 2.2 Adversarial Verification** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v` | **0** | **21** | 0 | 0 | **PASS** |
| **Day 2 RBAC Hardening** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_rbac_hardening.py -v` | **0** | **11** | 0 | 0 | **PASS** |
| **Checkpoint 16 RBAC Suite** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_rbac.py -v` | **0** | **4** | 0 | 0 | **PASS** |
| **Day 1.1 Security Suite** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_1_1_verification.py -v` | **0** | **3** | 0 | 0 | **PASS** |
| **HR Management & Payroll** | `backend\venv\Scripts\pytest.exe backend/tests/test_hr_management.py -v` | **0** | **6** | 0 | 0 | **PASS** |
| **Phase 5 Branch & Transfer Accounting** | `backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_branch_franchise_accounting.py -v` | **0** | **15** | 0 | 0 | **PASS** |
| **Stock Transfer Lifecycle** | `backend\venv\Scripts\pytest.exe backend/tests/test_stock_transfers.py -v` | **0** | **12** | 0 | 0 | **PASS** |
| **Checkpoint 16 Tenant Isolation** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_tenant_isolation.py -v` | **0** | **3** | 0 | 0 | **PASS** |
| **Checkpoint 16 IDOR Suite** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_idor.py -v` | **0** | **2** | 0 | 0 | **PASS** |
| **Frontend Production Build** | `npm run build` (in `frontend/`) | **0** | **7 static routes** | 0 | 0 | **PASS** |

**Total Regression Tests Passing:** **77 backend tests + 7 frontend static routes**  
**Total Failures:** **0**  
**Total Broken Regressions:** **0**

---

## 2. Command Traces & Detailed Test Outputs

### 2.1 Day 2.2 Expanded Adversarial Verification Suite
```
backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 21 items

test_hr_compensation_fields_strictly_absent_for_viewer PASSED            [  4%]
test_hr_compensation_fields_present_for_authorized_roles PASSED          [  9%]
test_hr_worker_history_forbidden_for_viewer PASSED                       [ 14%]
test_hr_citizenship_doc_download_forbidden_for_non_admin PASSED          [ 19%]
test_cross_company_user_update_rejected PASSED                           [ 23%]
test_cross_company_branch_read_and_mutation_rejected PASSED              [ 28%]
test_cross_company_warehouse_assignment_rejected PASSED                  [ 33%]
test_cross_company_stock_transfer_read_rejected PASSED                   [ 38%]
test_cross_company_stock_transfer_creation_rejected PASSED               [ 42%]
test_cross_company_stock_adjustments_rejected PASSED                     [ 47%]
test_cross_company_purchase_creation_rejected PASSED                     [ 52%]
test_cross_company_production_bom_creation_rejected PASSED               [ 57%]
test_cross_company_sales_order_creation_rejected PASSED                  [ 61%]
test_cross_company_destructive_operations_rejected PASSED               [ 66%]
test_manager_and_editor_cannot_access_user_management PASSED             [ 71%]
test_admin_self_deactivation_and_self_demotion_rejected PASSED           [ 76%]
test_destructive_operations_forbidden_for_editor_and_viewer PASSED      [ 80%]
test_intra_company_transfer_requires_distinct_warehouses PASSED          [ 85%]
test_anonymous_access_rejected_across_sensitive_endpoints PASSED        [ 90%]
test_last_active_admin_protection_comprehensive PASSED                   [ 95%]
test_rejected_cross_company_operations_preserve_data_invariants PASSED  [100%]

======================== 21 passed, 1 warning in 2.31s ========================
Exit code: 0
```

### 2.2 Phase 5 Branch Accounting & Migration Reversibility
```
backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_branch_franchise_accounting.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 15 items

test_create_branch_success PASSED                                        [  6%]
test_duplicate_branch_code_in_same_company_rejected PASSED                 [ 13%]
test_same_branch_code_allowed_in_different_company PASSED                 [ 20%]
test_viewer_role_forbidden_from_creating_branch PASSED                   [ 26%]
test_list_branches_returns_only_current_tenant_branches PASSED           [ 33%]
test_update_branch_metadata PASSED                                       [ 40%]
test_cross_company_branch_read_denied PASSED                             [ 46%]
test_cross_company_branch_mutation_denied PASSED                         [ 53%]
test_assign_warehouse_to_branch_success PASSED                           [ 60%]
test_cross_company_warehouse_assignment_rejected PASSED                  [ 66%]
test_unlink_warehouse_from_branch PASSED                                 [ 73%]
test_cannot_assign_warehouse_to_inactive_branch PASSED                   [ 80%]
test_branch_aware_stock_transfer_resolution PASSED                       [ 86%]
test_cannot_deactivate_branch_with_in_transit_transfers PASSED            [ 93%]
test_pg_migration_023_reversibility PASSED                               [100%]

======================= 15 passed, 1 warning in 17.58s ========================
Exit code: 0
```

### 2.3 Day 1.1 Verification Suite
```
backend\venv\Scripts\pytest.exe backend/tests/test_day_1_1_verification.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 3 items

test_rate_limiter_concurrency_write_then_count_atomicity PASSED          [ 33%]
test_security_headers_present_on_error_responses PASSED                  [ 66%]
test_open_redirect_sanitization_rules PASSED                             [100%]

======================== 3 passed, 1 warning in 2.22s =========================
Exit code: 0
```

### 2.4 Frontend Production Compilation
```
npm run build (in frontend/)

> livo-footwear-erp-frontend@1.0.0 build
> next build

  ▲ Next.js 14.2.35

   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/7) ...
   Generating static pages (7/7) 
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    27.2 kB         121 kB
├ ○ /_not-found                          873 B          88.5 kB
├ ○ /login                               5.95 kB        99.7 kB
├ ○ /privacy                             179 B          96.5 kB
└ ○ /terms                               179 B          96.5 kB
+ First Load JS shared by all            87.7 kB
ƒ Middleware                             26.7 kB
○  (Static)  prerendered as static content

Exit code: 0
```

---

## 3. Environmental Disclosures & Limitations

1. **Database Backend Differentiation:**
   - Unit tests and REST API contract checks were conducted against an in-memory SQLite database (`sqlite:///:memory:`).
   - Database migration reversibility (`test_pg_migration_023_reversibility`) and concurrency boundary tests were executed against embedded PostgreSQL (port 5433).
2. **Rate Limiting Concurrency Note:**
   - `test_rate_limiter_concurrency_write_then_count_atomicity` tests 35 concurrent requests over a 30-request ceiling. When run concurrently with other test suites hitting `/auth/login`, rate limit windows must be cleanly cleared (`reset_all()`). Ran in isolation, it achieves 100% pass rate.
3. **Out-of-Scope Elements:**
   - Day 3 general ledger posting was not touched.
   - Live cloud environments were not targeted.
