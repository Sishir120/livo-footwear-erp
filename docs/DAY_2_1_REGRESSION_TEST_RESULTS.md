# Day 2.1 Regression Test Execution Log and Results

**Date:** 2026-10-16  
**Environment:** Windows 11, Python 3.14.7, pytest 9.1.1, SQLite / Embedded PostgreSQL, Node v20.x, Next.js 14.2.35  
**Execution Context:** Verification of Day 2 RBAC changes, Day 2.1 Adversarial Authorization, Tenant Isolation, and HR Compensation Redaction Corrections.

---

## 1. Test Suite Execution Summary

| Suite / Target | Command | Exit Code | Tests Passed | Tests Failed | Skipped | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Day 2.1 Adversarial Verification** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v` | **0** | **18** | 0 | 0 | **PASS** |
| **Day 2 RBAC Hardening** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_rbac_hardening.py -v` | **0** | **11** | 0 | 0 | **PASS** |
| **Checkpoint 16 RBAC Suite** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_rbac.py -v` | **0** | **4** | 0 | 0 | **PASS** |
| **Day 1.1 Security Hardening** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_1_1_verification.py -v` | **0** | **3** | 0 | 0 | **PASS** |
| **HR Management & Payroll Suite**| `backend\venv\Scripts\pytest.exe backend/tests/test_hr_management.py -v` | **0** | **6** | 0 | 0 | **PASS** |
| **Phase 5 Branch & Transfer Accounting** | `backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_branch_franchise_accounting.py -v` | **0** | **15** | 0 | 0 | **PASS** |
| **Phase 5.3 Concurrency & Boundaries** | `backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_3_transaction_boundary.py -v` | **0** | **23** | 0 | 0 | **PASS** |
| **Stock Transfer Workflows** | `backend\venv\Scripts\pytest.exe backend/tests/test_stock_transfers.py -v` | **0** | **8** | 0 | 0 | **PASS** |
| **Tenant Isolation & IDOR** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_tenant_isolation.py backend/tests/test_checkpoint_16_idor.py -v` | **0** | **13** | 0 | 0 | **PASS** |
| **Frontend Production Build** | `npm run build` (in `frontend/`) | **0** | **7 static pages** | 0 | 0 | **PASS** |

**Total Backend Tests Executed Across Verification Suites:** **101 tests**  
**Total Passed:** **101**  
**Total Failed:** **0**  
**Frontend Compilation:** **100% Success**

---

## 2. Detailed Command Traces

### 2.1 Adversarial Verification Suite
```
backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 18 items

test_hr_compensation_fields_strictly_absent_for_viewer PASSED            [  5%]
test_hr_compensation_fields_present_for_authorized_roles PASSED          [ 11%]
test_hr_worker_history_forbidden_for_viewer PASSED                       [ 16%]
test_hr_citizenship_doc_download_forbidden_for_non_admin PASSED          [ 22%]
test_cross_company_user_update_rejected PASSED                           [ 27%]
test_cross_company_branch_read_and_mutation_rejected PASSED              [ 33%]
test_cross_company_warehouse_assignment_rejected PASSED                  [ 38%]
test_cross_company_stock_transfer_read_rejected PASSED                   [ 44%]
test_cross_company_stock_transfer_creation_rejected PASSED               [ 50%]
test_cross_company_stock_adjustments_rejected PASSED                     [ 55%]
test_cross_company_purchase_creation_rejected PASSED                     [ 61%]
test_cross_company_production_bom_creation_rejected PASSED               [ 66%]
test_cross_company_sales_order_creation_rejected PASSED                  [ 72%]
test_cross_company_destructive_operations_rejected PASSED               [ 77%]
test_manager_and_editor_cannot_access_user_management PASSED             [ 83%]
test_admin_self_deactivation_and_self_demotion_rejected PASSED           [ 88%]
test_destructive_operations_forbidden_for_editor_and_viewer PASSED      [ 94%]
test_intra_company_transfer_requires_distinct_warehouses PASSED          [100%]

======================== 18 passed, 1 warning in 2.23s ========================
Exit Code: 0
```

### 2.2 Day 2 Hardening + Checkpoint 16 + Day 1.1 + HR Suite
```
backend\venv\Scripts\pytest.exe backend/tests/test_day_2_rbac_hardening.py backend/tests/test_checkpoint_16_rbac.py backend/tests/test_day_1_1_verification.py backend/tests/test_hr_management.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 24 items

test_unauthenticated_request_rejected PASSED                             [  4%]
test_admin_self_deactivation_prevented PASSED                            [  8%]
test_admin_self_demotion_prevented PASSED                                [ 12%]
test_admin_can_update_other_user_role PASSED                             [ 16%]
test_non_admin_cannot_access_user_management PASSED                      [ 20%]
test_invalid_role_assignment_rejected PASSED                             [ 25%]
test_viewer_compensation_redaction_on_workers_list PASSED                [ 29%]
test_viewer_blocked_from_worker_financial_history PASSED                  [ 33%]
test_fixed_asset_deletion_restricted_to_admin PASSED                     [ 37%]
test_bom_item_deletion_restricted_to_admin PASSED                        [ 41%]
test_sales_expense_deletion_restricted_to_admin PASSED                    [ 45%]
test_viewer_mutation_rejection PASSED                                    [ 50%]
test_operator_vertical_escalation_to_admin PASSED                        [ 54%]
test_token_tampering_attacks PASSED                                      [ 58%]
test_mass_assignment_and_privilege_injection PASSED                      [ 62%]
test_rate_limiter_concurrency_write_then_count_atomicity PASSED          [ 66%]
test_security_headers_present_on_error_responses PASSED                  [ 70%]
test_open_redirect_sanitization_rules PASSED                             [ 75%]
test_worker_creation_salary_and_wage PASSED                              [ 79%]
test_worker_code_uniqueness_within_company PASSED                         [ 83%]
test_advance_calculation_issued_and_recovered PASSED                     [ 87%]
test_active_inactive_filtering_and_status_toggle PASSED                   [ 91%]
test_monthly_payroll_calculation_and_advance_deduction PASSED             [ 95%]
test_viewer_role_rejected_from_hr_mutations PASSED                       [100%]

======================= 24 passed, 24 warnings in 3.71s =======================
Exit Code: 0
```

### 2.3 Phase 5 Branch Accounting & Migration Reversibility
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

======================= 15 passed, 1 warning in 16.77s ========================
Exit Code: 0
```

### 2.4 Frontend Production Build
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

Exit Code: 0
```

---

## 3. Environmental Disclosures & Limitations

1. **Database Engines Tested:**
   - SQLite in-memory / file fixtures were utilized for fast API unit and integration testing.
   - Real PostgreSQL (embedded binary on port 5433) was invoked during `test_phase_5_branch_franchise_accounting.py` and `test_phase_5_3_transaction_boundary.py` for testing advisory locks, savepoints, transaction boundaries, and Alembic database migration reversibility.
2. **Untested Scopes:**
   - Day 3 accounting general ledger posting was not touched or tested per strict instructions.
   - Cloud deployment (Vercel / Render / Supabase) was not initiated; all operations were executed and verified in the local workspace.
