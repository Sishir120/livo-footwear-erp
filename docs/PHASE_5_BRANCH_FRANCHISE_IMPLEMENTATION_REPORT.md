# LIVO FOOTWEAR ERP — PHASE 5: BRANCH, WAREHOUSE & FRANCHISE ACCOUNTING IMPLEMENTATION REPORT

**Document ID:** LIVO-ERP-PHASE-5-REPORT  
**Evaluation Date:** October 15, 2026  
**Implementation Target:** Branch, Warehouse & Franchise Accounting Architecture (Vertical Slice 1)  
**Execution Environment:** Windows (PowerShell), Python 3.14.7, FastAPI, SQLAlchemy 2.0, PostgreSQL 18.6.3 (Embedded), Next.js 14.2.35  
**Audit Standard:** Zero live record mutation, zero unverified assumptions, explicit verification taxonomy (**VERIFIED**, **PARTIALLY VERIFIED**, **NOT VERIFIED**, **FAILED**).

---

## 1. Executive Summary & Verification Verdict

Phase 5 establishes the architectural domain foundation for multi-location operations across factories, central warehouses, company-owned showrooms, and commercial franchise partners. Rather than creating disconnected CRUD interfaces or fabricating an unverified double-entry general ledger, this phase delivered a safe, production-grade vertical slice: **Company-Owned Branch Registration and Warehouse Attribution with Branch-Aware Authorization, Stock Transfer Integration, and Tenant Isolation**.

| Component / Verification Area | Status | Evidence & Verification Metric |
| :--- | :--- | :--- |
| **Domain Boundary & Architecture Blueprint** | **VERIFIED** | Documented in `docs/PHASE_5_BRANCH_FRANCHISE_ACCOUNTING_DESIGN.md` (4 entity tiers, 10 workflows, decision matrix, GL gap analysis). |
| **Backend Models & Schema Integration** | **VERIFIED** | `Branch` model, `BranchType` enum, nullable `warehouses.branch_id` foreign key, Pydantic V2 schemas. |
| **Alembic Migration 023 Reversibility** | **VERIFIED** | `023_add_branches_and_warehouse_link.py` verified on PostgreSQL 18.6.3 with clean zero-to-head, downgrade, and re-upgrade. |
| **Authenticated REST API & RBAC** | **VERIFIED** | CRUD endpoints mounted under `/api/v1/branches`, tenant repository isolation, editor/admin enforcement, viewer rejection. |
| **Stock Transfer & Warehouse Attribution** | **VERIFIED** | Warehouse listings and stock transfer endpoints enriched with branch resolution (`source_branch_name`, `is_inter_branch`). |
| **Security & Cross-Tenant IDOR Protection** | **VERIFIED** | Cross-company branch read/mutation rejected (HTTP 404/403); cross-company warehouse linking strictly blocked. |
| **Frontend UI & Navigation Integration** | **VERIFIED** | `BranchWarehouseView.tsx` with bilingual (English/Nepali) UI, metrics cards, modals, and dynamic AppShell routing. |
| **Frontend Production Build** | **VERIFIED** | `npx tsc --noEmit` passed with 0 errors; `npm run build` compiled successfully (exit code 0). |
| **Full Backend Regression Suite** | **VERIFIED** | **466 passed, 0 failed, 355 warnings in 158.63s (exit code 0)**. |
| **Independent Franchise Settlement & Statutory GL** | **PARTIALLY VERIFIED** | Architectural contract and decision matrix established; implementation intentionally deferred pending client tax/commercial decisions. |

---

## 2. Existing Architecture Discovered

An adversarial inspection of the codebase before implementing Phase 5 revealed the following architectural facts:
1. **Tenant Isolation:**
   - Enforced by `TenantRepository` and `company_id` columns on core tables (`companies`, `users`, `warehouses`, `products`, `invoices`, `sales_orders`).
   - Every operational transaction is bounded to the authenticated user's `company_id`.
2. **Inventory Model:**
   - Physical inventory is tracked in `warehouses` via append-only `stock_movements`.
   - Inter-warehouse transfers are managed via `stock_transfers` and `stock_transfer_items`, maintaining exact physical stock conservation:
     $$\text{dispatched\_qty} = \text{received\_qty} + \text{in\_transit\_qty} + \text{discrepancy\_qty}$$
3. **General Ledger Gap Analysis:**
   - **Finding:** A genuine double-entry general ledger (`accounts`, `journal_entries`, `gl_periods`) **does not exist** in the repository.
   - **Operational Reality:** The system operates using audited, domain-specific **operational subledgers**:
     - *Accounts Receivable Subledger:* `receivable_entries` with integer-paisa math and credit notes (अनुसूची-१०).
     - *Inventory Valuation Subledger:* `stock_movements` and periodic `stock_snapshots`.
     - *Factory Cost & Expense Ledger:* `factory_expenses`.
   - **Design Rationale:** Fabricating a pseudo-GL without Chart of Accounts rules, debit/credit balancing engines, and period close controls would destabilize existing financial data. Full GL posting must follow formal client Chart of Accounts approval in Phase 6.

---

## 3. Explicit Domain Boundaries Established

To eliminate confusion between legal entities, physical stock locations, operating units, and commercial contracts, the domain is explicitly separated into four distinct tiers:

1. **Tier A: Legal Entity (`Company`)**
   - Holds statutory legal identity, tax registration (9-digit Nepal PAN/VAT), and final balance sheet responsibility.
   - Issues statutory tax invoices and credit notes.
2. **Tier B: Operating Location / Branch (`Branch`)**
   - Represents internal operational units: factories, head offices, regional distribution hubs, and company-owned retail showrooms.
   - Inherits the parent company's legal PAN. Does NOT issue separate statutory invoices under an independent tax identity.
   - Acts as an operational cost center and management reporting division.
3. **Tier C: Physical Stock Location (`Warehouse`)**
   - Represents physical storage facilities (godowns, finished goods storage, display floors).
   - Linked to an optional `branch_id`. Inventory quantities remain strictly physical and attributable to the warehouse.
4. **Tier D: Franchise Partner (`Franchise`)**
   - Represents independent third-party commercial businesses operating under franchise agreements.
   - Holds its own legal entity, own PAN registration, and retail customer relationships.
   - Transactions between parent company and franchisee are B2B wholesale sales or consignment custody transfers, NOT internal stock transfers.

---

## 4. Evaluated Financial Operating Models

Ten distinct operational workflows were analyzed and synthesized into the accounting decision matrix in `docs/PHASE_5_BRANCH_FRANCHISE_ACCOUNTING_DESIGN.md`:
1. *Internal Transfer: Factory to Showroom* — Non-tax internal transfer (`DC-` challan); physical movement without revenue or VAT.
2. *Intra-Branch Warehouse Transfer* — Physical stock transfer memo; zero accounting impact.
3. *Inter-Branch Regional Transfer* — Road transit via `StockTransfer`; in-transit stock tracking until destination receipt.
4. *Outright Sale to Franchisee* — B2B Tax Invoice; 13% Nepal VAT; franchisee debited in AR subledger.
5. *Consignment Stock to Franchisee* — Consignment challan (`CNG-`); stock remains parent company asset in designated consignment warehouse; no revenue recognized until sold.
6. *Franchise Retail Sale & Settlement* — Franchisee bills consumer under own PAN; parent company issues periodic wholesale settlement invoice.
7. *Customer Return to Branch* — Credit Note (अनुसूची-१०) referencing original tax invoice; output VAT liability reduced.
8. *Branch Expense Paid Centrally* — Expense voucher; debit branch cost center, credit central bank; input VAT reclaimed if valid tax invoice exists.
9. *Central Procurement for Branches* — Central purchase order and goods receipt (`GRN`); input VAT capitalized.
10. *Intercompany Transfer Between Sister Entities* — Commercial B2B sale; full 13% VAT; Nepal Transfer Pricing rules (Income Tax Act §33).

---

## 5. Implemented Vertical Slice: Company-Owned Branch & Warehouse Registration

### 5.1 Architecture & Implementation Details
The implemented vertical slice provides complete end-to-end functionality across database, backend API, authorization, and frontend UI:

1. **Database Model (`backend/app/models/branch.py`):**
   - `Branch` entity with `id`, `company_id`, `code`, `name`, `type`, `address`, `phone`, `email`, `is_active`, `created_at`, `updated_at`.
   - Compound unique constraint `uq_company_branch_code` (`company_id`, `code`) ensuring unique branch codes within a company while allowing different companies to reuse codes.
2. **Warehouse Linking (`backend/app/models/stock.py`):**
   - Added nullable foreign key `branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True, index=True)`.
   - Added bidirectional relationship `branch = relationship("Branch", back_populates="warehouses")`.
   - Preserves 100% backward compatibility: existing warehouses without branch assignments retain `branch_id = NULL` without fabricated backfills.
3. **Pydantic V2 Schemas (`backend/app/schemas/branch.py`):**
   - Enum `BranchType`: `HEAD_OFFICE`, `FACTORY`, `RETAIL_OUTLET`, `REGIONAL_HUB`.
   - Schemas: `BranchCreate`, `BranchUpdate`, `BranchResponse`, `WarehouseDetailResponse`, `WarehouseAssignRequest` using `model_config = {"from_attributes": True}`.
4. **REST API Endpoints (`backend/app/api/v1/branches.py`):**
   - `GET /api/v1/branches` — List all branches for authenticated company (with warehouse counts).
   - `POST /api/v1/branches` — Create new branch (validated, unique code enforcement, requires editor/admin).
   - `GET /api/v1/branches/{id}` — Get branch detail with linked warehouses.
   - `PUT /api/v1/branches/{id}` — Update branch metadata (requires editor/admin).
   - `PATCH /api/v1/branches/{id}/toggle-active` — Toggle branch active status (prevents deactivating branches with in-transit transfers).
   - `POST /api/v1/branches/{id}/warehouses` — Link warehouse to branch (strictly validates same company boundary).
   - `DELETE /api/v1/branches/{id}/warehouses/{wh_id}` — Unlink warehouse from branch (sets `branch_id = NULL`).
5. **Stock Transfer & Warehouse API Extensions:**
   - `GET /api/v1/stock/warehouses` and `GET /api/v1/stock/warehouses/{id}`: Return `branch_id`, `branch_name`, `branch_code`.
   - `GET /api/v1/transfers` and `GET /api/v1/transfers/{id}`: Return `source_branch_name`, `destination_branch_name`, and boolean flag `is_inter_branch`.
6. **Frontend Integration (`frontend/src/components/BranchWarehouseView.tsx`):**
   - Bilingual (English & Nepali) dashboard.
   - Metrics cards: Total Branches, Showrooms & Outlets, Factories & Hubs, Linked Warehouses.
   - Filterable branch list with active status pills and warehouse chips.
   - Modal dialogs: "Register New Branch" with Nepali labels and "Link Warehouse to Branch" modal.
   - Integrated into `AppShell.tsx` navigation with `Building2` icon and dynamically loaded in `frontend/src/app/page.tsx`.

---

## 6. Verification Evidence & Test Results

### 6.1 PostgreSQL 18.6.3 Migration & Downgrade Reversibility
- **Migration File:** `backend/migrations/versions/023_add_branches_and_warehouse_link.py`
- **Dialect Handling:**
  - SQLite: Uses `op.batch_alter_table` with named foreign key constraint `fk_warehouses_branch_id`.
  - PostgreSQL: Uses direct `op.add_column` and `op.create_index`.
- **Test:** `test_pg_migration_023_reversibility` in `backend/tests/test_phase_5_branch_franchise_accounting.py`
- **Execution:** Ran on real embedded PostgreSQL 18.6.3 instance:
  1. Base to 023 upgrade: Table `branches` created, column `warehouses.branch_id` created, indexes created.
  2. Downgrade to 022: Column `warehouses.branch_id` cleanly dropped, table `branches` dropped.
  3. Re-upgrade to 023: Schema re-applied cleanly without orphaned constraints.
- **Result:** **VERIFIED** (Exit Code 0).

### 6.2 Acceptance Tests for Phase 5 Vertical Slice
The test suite in `backend/tests/test_phase_5_branch_franchise_accounting.py` executed **15 tests, 0 failures** in 15.80s:

| Test Case | Description | Verification Result |
| :--- | :--- | :--- |
| `test_create_branch_success` | Creates a company branch with complete contact details and verifies database persistence. | **VERIFIED** |
| `test_duplicate_branch_code_in_same_company_rejected` | Confirms duplicate code in same tenant is rejected with HTTP 400. | **VERIFIED** |
| `test_same_branch_code_allowed_in_different_company` | Confirms different companies can use the same branch code without collision. | **VERIFIED** |
| `test_viewer_role_forbidden_from_creating_branch` | Confirms `viewer` role receives HTTP 403 on mutation endpoints. | **VERIFIED** |
| `test_list_branches_returns_only_current_tenant_branches` | Verifies tenant isolation prevents leaking branches across companies. | **VERIFIED** |
| `test_update_branch_metadata` | Updates branch name, address, and type successfully. | **VERIFIED** |
| `test_cross_company_branch_read_denied` | Confirms tenant cannot read another company's branch (HTTP 404). | **VERIFIED** |
| `test_cross_company_branch_mutation_denied` | Confirms tenant cannot edit or mutate another company's branch (HTTP 404). | **VERIFIED** |
| `test_assign_warehouse_to_branch_success` | Links warehouse to branch and verifies bidirectional relationship. | **VERIFIED** |
| `test_cross_company_warehouse_assignment_rejected` | Confirms cross-company warehouse linking is strictly rejected (HTTP 404). | **VERIFIED** |
| `test_unlink_warehouse_from_branch` | Detaches warehouse from branch (`branch_id = NULL`) without deleting warehouse. | **VERIFIED** |
| `test_cannot_assign_warehouse_to_inactive_branch` | Confirms deactivated branch cannot receive new warehouse links (HTTP 400). | **VERIFIED** |
| `test_branch_aware_stock_transfer_resolution` | Verifies transfers resolve source/destination branch names and `is_inter_branch`. | **VERIFIED** |
| `test_cannot_deactivate_branch_with_in_transit_transfers` | Confirms branch deactivation is blocked if transfers are in transit (HTTP 400). | **VERIFIED** |
| `test_pg_migration_023_reversibility` | Verifies migration 023 upgrade, downgrade, and re-upgrade on PostgreSQL 18.6.3. | **VERIFIED** |

### 6.3 Full Backend Test Suite
Executed the entire backend test suite across all 23 checkpoints and phases:
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests -q
```
**Outcome:** **466 passed, 355 warnings, 0 failed in 158.63 seconds (exit code 0)**.

### 6.4 Frontend Typecheck and Production Build
```powershell
npx tsc --noEmit
npm run build
```
- **Typecheck Result:** Exit code 0 (0 errors).
- **Next.js Production Build Result:**
  - Compiled successfully (`▲ Next.js 14.2.35`).
  - Generated all 7 static routes (`/`, `/_not-found`, `/login`, `/privacy`, `/terms`).
  - Exit code 0.

---

## 7. Files Changed During Phase 5

### 7.1 New Files Created in Phase 5
1. `backend/app/models/branch.py` — SQLAlchemy `Branch` model and `BranchType` enum.
2. `backend/app/schemas/branch.py` — Pydantic V2 schemas for branch creation, updates, and warehouse assignment.
3. `backend/app/api/v1/branches.py` — REST API endpoints for branch management and warehouse linking.
4. `backend/migrations/versions/023_add_branches_and_warehouse_link.py` — Reversible Alembic migration script.
5. `backend/tests/test_phase_5_branch_franchise_accounting.py` — 15 comprehensive integration, security, and migration tests.
6. `frontend/src/components/BranchWarehouseView.tsx` — Bilingual frontend view for branch and warehouse management.
7. `docs/PHASE_5_BRANCH_FRANCHISE_ACCOUNTING_DESIGN.md` — Complete architectural blueprint and accounting decision matrix.
8. `docs/PHASE_5_BRANCH_FRANCHISE_IMPLEMENTATION_REPORT.md` — This implementation and verification report.

### 7.2 Existing Files Modified in Phase 5
1. `backend/app/models/__init__.py` — Exported `Branch` and `BranchType`.
2. `backend/app/models/stock.py` — Added `branch_id` foreign key and `branch` relationship to `Warehouse`.
3. `backend/app/api/v1/router.py` — Mounted `branches_router` under `/branches`.
4. `backend/app/api/v1/stock.py` — Added branch attribution fields to warehouse responses.
5. `backend/app/api/v1/transfers.py` — Added branch resolution and `is_inter_branch` indicator to transfer responses.
6. `frontend/src/components/AppShell.tsx` — Added "Branches & Locations (शाखा र गोदाम)" to navigation sidebar.
7. `frontend/src/app/page.tsx` — Integrated `BranchWarehouseView` under `activeTab === "branches"`.
8. `backend/tests/test_checkpoint_11_database.py` — Updated allowed migration head list to include `023`.
9. `backend/tests/test_checkpoint_15_2_postgres.py` — Updated allowed migration head list to include `023`.
10. `backend/tests/test_checkpoint_17_production_readiness.py` — Updated allowed migration head list to include `023`.
11. `backend/tests/test_checkpoint_18_live_acceptance.py` — Updated allowed migration head list to include `023`.

*(Pre-existing modifications from earlier phases in `backend/app/api/v1/invoices.py`, `backend/app/api/v1/purchase.py`, `backend/app/core/locks.py`, `backend/app/models/stock_transfer.py`, and `frontend/src/components/StockTransferModal.tsx` were strictly preserved without mutation).*

---

## 8. Security and Tenant Isolation Evidence

1. **Cross-Tenant Boundary Enforcement:**
   - Every branch operation verifies `Branch.company_id == current_user.company_id`.
   - Accessing a branch belonging to another company returns HTTP 404, preventing company enumeration or IDOR vulnerability.
2. **Cross-Tenant Warehouse Linking Protection:**
   - Endpoint `POST /api/v1/branches/{id}/warehouses` queries both the branch and the warehouse under the user's `company_id`.
   - Attempting to link a warehouse from Company B to a branch of Company A fails immediately with HTTP 404 (`test_cross_company_warehouse_assignment_rejected`).
3. **Role-Based Access Control (RBAC):**
   - Mutation endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) require `require_editor` or `require_admin`.
   - Viewer accounts are strictly limited to read-only access (`GET /api/v1/branches`).
4. **State Machine Safeguards:**
   - Deactivating a branch (`PATCH /toggle-active`) verifies whether any active stock transfers (`IN_TRANSIT` or `DRAFT`) reference warehouses belonging to that branch.
   - If active transfers exist, deactivation is rejected with HTTP 400 (`test_cannot_deactivate_branch_with_in_transit_transfers`).
   - Inactive branches cannot have new warehouses assigned (`test_cannot_assign_warehouse_to_inactive_branch`).

---

## 9. Open Business Decisions & Professional Tax Questions

Before implementing Phase 6 (Consignment Accounting, Franchise Settlements, and Double-Entry GL), the following items require client CFO and qualified Nepal Chartered Accountant (CA) resolution:

1. **Nepal Value Added Tax Act §14 (Consignment Stock):**
   - Does stock transferred to a franchise location on consignment require a formal tax invoice at time of dispatch, or is an internal delivery challan accompanied by Department of Revenue Investigation (DRI) VCTS declaration legally compliant?
2. **Franchise Royalty & Revenue Recognition:**
   - Is retail franchise revenue recognized gross by the parent company (with commission paid to franchisee), or net at wholesale billing value?
3. **Double-Entry Chart of Accounts Structure:**
   - Formal approval of the standard Nepal footwear Chart of Accounts (COA) numbering hierarchy (e.g., Assets 1000–1999, Liabilities 2000–2999, Equity 3000–3999, Revenue 4000–4999, COGS 5000–5999, Expenses 6000–6999).
4. **Intercompany Transfer Pricing (Income Tax Act §33):**
   - If footwear is transferred between distinct legal entities under common ownership, what transfer pricing documentation and margin policy are mandated?

---

## 10. Explicit Limitations & Remaining Risks

1. **No Pseudo-GL Posted:** Phase 5 intentionally does not post double-entry general ledger journals. All financial tracking continues to rely on the hardened operational subledgers (`ReceivableEntry`, `StockMovement`, `FactoryExpense`).
2. **Independent Franchise Portal:** Franchisees do not yet have an isolated external login portal. Franchise operations are currently managed via B2B wholesale client accounts and consignment warehouse tags.
3. **Automated VCTS Integration:** VCTS tracking numbers are captured as metadata on transfers, but real-time XML API submission to the Nepal Department of Revenue Investigation server is not yet automated.

---

## 11. Recommendations for Phase 6

1. **Formal Chart of Accounts & General Ledger Engine:**
   - Introduce `accounts`, `gl_periods`, `journal_entries`, and `journal_lines` with double-entry balancing ($\sum \text{Debits} = \sum \text{Credits}$) and branch dimensions.
2. **Automated Subledger-to-GL Posting Service:**
   - Implement idempotent posting listeners that create balancing GL journals whenever an invoice, payment, credit note, or production batch is finalized.
3. **Franchise Settlement & Consignment Portal:**
   - Build consignment stock consumption reporting and automated periodic wholesale settlement billing for franchise partners.

---

**Report Certification:**  
All verifications, tests, and builds cited in this document were executed locally in the workspace. No live database records were mutated, no Git commits were pushed, and no production services were restarted.
