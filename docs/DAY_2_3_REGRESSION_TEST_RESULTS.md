# Day 2.3 Comprehensive Regression Test Results

**Date of Execution:** 2026-10-16  
**Operating Environment:** Windows 11 Pro, Python 3.14.7, pytest 9.1.1, Node v20.x, Next.js 14.2.35  
**Database Engines Tested:** SQLite in-memory & file fixtures; PostgreSQL 18.6 via `embedded_postgres`  
**Working Directory:** `d:\Antigravity\Footwear app`  
**Python Virtualenv:** `d:\Antigravity\Footwear app\backend\venv\Scripts\python.exe`

---

## 1. Master Regression Suite Execution Summary

| Test Target / Suite | Exact Command Executed | Exit Code | Collected | Passed | Failed | Skipped | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Day 2.3 Adversarial Verification & Concurrency** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v` | **0** | **24** | **24** | 0 | 0 | **PASS** |
| **Day 2 RBAC Hardening** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_2_rbac_hardening.py -v` | **0** | **11** | **11** | 0 | 0 | **PASS** |
| **Checkpoint 16 RBAC Suite** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_rbac.py -v` | **0** | **4** | **4** | 0 | 0 | **PASS** |
| **Day 1.1 Security Hardening** | `backend\venv\Scripts\pytest.exe backend/tests/test_day_1_1_verification.py -v` | **0** | **3** | **3** | 0 | 0 | **PASS** |
| **HR Management & Payroll Engine**| `backend\venv\Scripts\pytest.exe backend/tests/test_hr_management.py -v` | **0** | **6** | **6** | 0 | 0 | **PASS** |
| **Phase 5 Branch Accounting & Reversibility** | `backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_branch_franchise_accounting.py -v` | **0** | **15** | **15** | 0 | 0 | **PASS** |
| **Phase 5.3 Concurrency & Boundaries** | `backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_3_transaction_boundary.py -v` | **0** | **28** | **28** | 0 | 0 | **PASS** |
| **Stock Transfer Workflows** | `backend\venv\Scripts\pytest.exe backend/tests/test_stock_transfers.py -v` | **0** | **12** | **12** | 0 | 0 | **PASS** |
| **Checkpoint 16 Tenant & IDOR** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_tenant_isolation.py backend/tests/test_checkpoint_16_idor.py -v` | **0** | **5** | **5** | 0 | 0 | **PASS** |
| **Checkpoint 16 Security & Invariants** | `backend\venv\Scripts\pytest.exe backend/tests/test_checkpoint_16_security.py backend/tests/test_checkpoint_16_business_security.py -v` | **0** | **8** | **8** | 0 | 0 | **PASS** |
| **Frontend Production Compilation** | `npm run build` (in `frontend/`) | **0** | **7 static routes** | **7** | 0 | 0 | **PASS** |

**Total Backend Tests Executed:** **116 tests**  
**Total Passed:** **116**  
**Total Failed:** **0**  
**Frontend Compilation:** **100% Success**

---

## 2. Detailed Execution Traces

### 2.1 Day 2.3 Adversarial Verification & Concurrency Suite (24 Tests)
```
backend\venv\Scripts\pytest.exe backend/tests/test_day_2_1_authorization_verification.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 24 items

test_hr_compensation_fields_strictly_absent_for_viewer PASSED            [  4%]
test_hr_compensation_fields_present_for_authorized_roles PASSED          [  8%]
test_hr_worker_history_forbidden_for_viewer PASSED                       [ 12%]
test_hr_citizenship_doc_download_forbidden_for_non_admin PASSED          [ 16%]
test_cross_company_user_update_rejected PASSED                           [ 20%]
test_cross_company_branch_read_and_mutation_rejected PASSED              [ 25%]
test_cross_company_warehouse_assignment_rejected PASSED                  [ 29%]
test_cross_company_stock_transfer_read_rejected PASSED                   [ 33%]
test_cross_company_stock_transfer_creation_rejected PASSED               [ 37%]
test_cross_company_stock_adjustments_rejected PASSED                     [ 41%]
test_cross_company_purchase_creation_rejected PASSED                     [ 45%]
test_cross_company_production_bom_creation_rejected PASSED               [ 50%]
test_cross_company_sales_order_creation_rejected PASSED                  [ 54%]
test_cross_company_destructive_operations_rejected PASSED               [ 58%]
test_manager_and_editor_cannot_access_user_management PASSED             [ 62%]
test_admin_self_deactivation_and_self_demotion_rejected PASSED           [ 66%]
test_destructive_operations_forbidden_for_editor_and_viewer PASSED      [ 70%]
test_intra_company_transfer_requires_distinct_warehouses PASSED          [ 75%]
test_anonymous_access_rejected_across_sensitive_endpoints PASSED        [ 79%]
test_last_active_admin_protection_comprehensive PASSED                   [ 83%]
test_rejected_cross_company_operations_preserve_data_invariants PASSED  [ 87%]
test_concurrent_mutual_admin_deactivation_race_prevented PASSED          [ 91%]
test_admin_lockout_strictly_scoped_by_company PASSED                     [ 95%]
test_pg_concurrent_mutual_admin_deactivation_race_prevented PASSED       [100%]

======================= 24 passed, 1 warning in 12.86s ========================
Exit code: 0
```

### 2.2 Phase 5.3 Concurrency & Transaction Boundary Suite (28 Tests)
```
backend\venv\Scripts\pytest.exe backend/tests/test_phase_5_3_transaction_boundary.py -v

============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 28 items

TestStage2LockHelperSessionLifecycle::test_1_caller_pending_orm_object_preserved PASSED [  3%]
TestStage2LockHelperSessionLifecycle::test_2_caller_modified_persistent_object_preserved PASSED [  7%]
TestStage2LockHelperSessionLifecycle::test_3_caller_raw_sql_execution_preserved PASSED [ 10%]
TestStage2LockHelperSessionLifecycle::test_4_active_transaction_lock_acquisition PASSED [ 14%]
TestStage2LockHelperSessionLifecycle::test_5_lock_acquisition_failure_cleanup PASSED [ 17%]
TestStage2LockHelperSessionLifecycle::test_6_business_operation_failure_after_lock PASSED [ 21%]
TestStage2LockHelperSessionLifecycle::test_7_lock_release_on_success_rollback_exception_early_return PASSED [ 25%]
TestStage2LockHelperSessionLifecycle::test_8_session_reused_after_lock_cleanup PASSED [ 28%]
TestStage2LockHelperSessionLifecycle::test_9_caller_mixed_raw_sql_and_orm_mutations_preserved PASSED [ 32%]
TestStage2LockHelperSessionLifecycle::test_10_session_reused_after_failed_operation PASSED [ 35%]
TestStage3PostgreSQLConcurrency::test_pg_dialect_and_version PASSED      [ 39%]
TestStage3PostgreSQLConcurrency::test_pg_race_1_concurrent_dispatches_serialized PASSED [ 42%]
TestStage3PostgreSQLConcurrency::test_pg_race_2_concurrent_receipts_serialized PASSED [ 46%]
TestStage3PostgreSQLConcurrency::test_pg_race_3_receipt_racing_cancellation PASSED [ 50%]
TestStage3PostgreSQLConcurrency::test_pg_race_4_concurrent_cancellations PASSED [ 53%]
TestStage3PostgreSQLConcurrency::test_pg_race_5_overlapping_stock_consumption PASSED [ 57%]
TestStage3PostgreSQLConcurrency::test_pg_race_6_concurrent_credit_notes_ceiling PASSED [ 60%]
TestStage4InventoryConservationModel::test_full_receipt_conservation PASSED [ 64%]
TestStage4InventoryConservationModel::test_partial_receipt_conservation PASSED [ 67%]
TestStage4InventoryConservationModel::test_multi_stage_receipt_conservation PASSED [ 71%]
TestStage4InventoryConservationModel::test_shortage_with_discrepancy_reason PASSED [ 75%]
TestStage4InventoryConservationModel::test_shortage_without_discrepancy_reason_rejected PASSED [ 78%]
TestStage4InventoryConservationModel::test_cancellation_before_receipt PASSED [ 82%]
TestStage4InventoryConservationModel::test_cancellation_after_partial_receipt PASSED [ 85%]
TestStage5FailureInjectionAndIdempotency::test_failure_after_source_deduction_before_transfer_status PASSED [ 89%]
TestStage5FailureInjectionAndIdempotency::test_failure_after_destination_receipt_before_commit PASSED [ 92%]
TestStage5FailureInjectionAndIdempotency::test_failure_during_discrepancy_creation PASSED [ 96%]
TestStage5FailureInjectionAndIdempotency::test_idempotent_retry_prevents_duplicate_movements PASSED [100%]

======================= 28 passed, 1 warning in 12.55s ========================
Exit code: 0
```

### 2.3 Phase 5 Branch Accounting & Migration Reversibility Suite (15 Tests)
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

Exit code: 0
```
