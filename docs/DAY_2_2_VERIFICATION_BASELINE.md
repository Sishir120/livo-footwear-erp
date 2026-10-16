# Day 2.2 Verification Baseline Record

**Timestamp:** 2026-10-16 11:23:00 +05:45  
**Git Branch:** `main`  
**Git Commit HEAD:** `2ab515e1c18fceafb5621a2b5ce4127ec2bf24bb`  

---

## 1. Baseline Preflight Context

This document captures the immutable baseline state prior to executing Day 2.2 independent authorization verification and demo-safety gating.

### 1.1 Git Status (`git status --short`)
Tracked modifications (32 files):
- `.gitignore`
- `backend/app/api/deps.py`
- `backend/app/api/v1/assets.py`
- `backend/app/api/v1/auth.py`
- `backend/app/api/v1/hr.py`
- `backend/app/api/v1/invoices.py`
- `backend/app/api/v1/production.py`
- `backend/app/api/v1/purchase.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/sales.py`
- `backend/app/api/v1/stock.py`
- `backend/app/core/locks.py`
- `backend/app/main.py`
- `backend/app/middleware/rate_limit.py`
- `backend/app/middleware/security_headers.py`
- `backend/app/models/__init__.py`
- `backend/app/models/stock.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/worker.py`
- `backend/tests/test_checkpoint_11_database.py`
- `backend/tests/test_checkpoint_15_2_postgres.py`
- `backend/tests/test_checkpoint_15_query_regression.py`
- `backend/tests/test_checkpoint_17_production_readiness.py`
- `backend/tests/test_checkpoint_18_live_acceptance.py`
- `backend/tests/test_vat_compliance_and_calculation.py`
- `docs/OPERATIONAL_HANDOVER.md`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/HRManagementView.tsx`
- `frontend/src/components/StockReportView.tsx`
- `frontend/src/lib/api.ts`

Key untracked files from Phase 5, Phase 6A, Day 1, Day 1.1, Day 2, and Day 2.1:
- `backend/app/api/v1/branches.py`
- `backend/app/api/v1/transfers.py`
- `backend/app/models/branch.py`
- `backend/app/models/rate_limit.py`
- `backend/app/models/stock_transfer.py`
- `backend/app/schemas/branch.py`
- `backend/migrations/versions/022_add_stock_transfers.py`
- `backend/migrations/versions/023_add_branches_and_warehouse_link.py`
- `backend/migrations/versions/024_add_rate_limit_entries.py`
- `backend/tests/test_day_1_1_verification.py`
- `backend/tests/test_day_1_hardening.py`
- `backend/tests/test_day_2_1_authorization_verification.py`
- `backend/tests/test_day_2_rbac_hardening.py`
- `backend/tests/test_phase_5_branch_franchise_accounting.py`
- `backend/tests/test_phase_5_3_transaction_boundary.py`
- `docs/DAY_2_1_ADVERSARIAL_VERIFICATION_REPORT.md`
- `docs/DAY_2_1_REGRESSION_TEST_RESULTS.md`
- `frontend/src/components/BranchWarehouseView.tsx`
- `frontend/src/components/StockTransferModal.tsx`

### 1.2 Preservation Guarantees
- Zero files staged or committed.
- No destructive git operations (`reset`, `clean`, `checkout`, `stash`).
- Complete preservation of all pre-existing Phase 5–6A, Day 1, Day 1.1, and Day 2.1 work.
- Existing audit findings and test suites are treated as user assets and will be verified against actual code execution.
