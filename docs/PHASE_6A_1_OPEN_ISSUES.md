# LIVO FOOTWEAR ERP — PHASE 6A.1: OPEN ISSUES REGISTER

**Status:** VALIDATION GATE AUDIT  
**Phase:** 6A.1 (Specification-Only)  
**Audit Date:** 2026-10-15  
**Purpose:** Consolidated, prioritized list of all issues found during Phase 6A.1 design validation, with resolution owner, deadline criticality, and exact document/code references.

> This document is the canonical action register for Phase 6A closure. All items must be formally resolved and signed off before Phase 6B implementation begins.

---

## Summary Status Board

| Issue ID | Severity | Category | Resolution Owner | Blocks Phase 6B? | Status |
|:--|:--|:--|:--|:--|:--|
| VAL-01 | **CRITICAL** | Design defect | Engineering | **Yes** (every financial route) | OPEN |
| VAL-02 | **CRITICAL** | Source model gap | Engineering | **Yes** (Events 8, 9, COGS) | OPEN |
| VAL-03 | **HIGH** | Accounting policy | Chartered Accountant | **Yes** (Events 10, 11) | AWAITING CA |
| VAL-04 | **HIGH** | Spec clarification | Engineering + CA | No (clarification only) | OPEN |
| VAL-05 | **HIGH** | Tax policy | Chartered Accountant | **Yes** (Event 31) | AWAITING CA |
| VAL-06 | **MEDIUM** | COA code error | Engineering | Partially (Event 28) | OPEN |
| VAL-07 | **MEDIUM** | Schema gap | Engineering | **Yes** (fiscal period queries) | OPEN |
| VAL-08 | **MEDIUM** | Implementation gap | Engineering | **Yes** (all financial route authorization) | OPEN |
| VAL-09 | **LOW** | COA hierarchy | Engineering | No (minor) | OPEN |
| VAL-10 | **LOW** | Consistency | Engineering | No (documentation only) | OPEN |
| M1–M7 | **MEDIUM** | Missing events | Engineering + CA | Partially | OPEN |

---

## 1. Critical Issues (Implementation Blocked)

### VAL-01: GL Idempotency Event Taxonomy Undefined
**Severity:** CRITICAL  
**Found In:** `docs/PHASE_6A_ACCOUNTING_ARCHITECTURE.md §4.4`  
**Concrete Risk:** Two separate journal entries for the same source document produce the same SHA-256 hash, the second is silently rejected by PostgreSQL's unique constraint, and the posting application receives an IntegrityError. The first journal committed successfully, so no rollback occurs. The GL is permanently missing one entry.

**Required Action:**
1. Define a sealed `GLEventAction` enum with one unique string per journal event (minimum 20 values).
2. Store this enum in `backend/app/core/gl_events.py`.
3. All posting handlers must import and use this enum — no inline string literals.
4. The idempotency key format must be documented as: `SHA256("{company_id}||{source_doc_type}||{source_doc_id}||{GLEventAction.value}")`.
5. Add a database `CHECK` constraint on `journal_entries.source_doc_type` referencing the same enum.

**Resolution Owner:** Engineering  
**Estimated Effort:** 1–2 days  
**References:** `backend/app/core/idempotency.py` (existing HTTP-level model to follow)

---

### VAL-02: Production Cost Fields Missing from `ProductionBatch` and `ProductionMaterialUsage`
**Severity:** CRITICAL  
**Found In:** `docs/PHASE_6A_POSTING_MATRIX.md Events 8, 9` vs `backend/app/models/production.py`  
**Concrete Risk:** The posting engine for WIP and Finished Goods has no cost column to read from. The only fallback is `Product.unit_price` (selling price), which the specification correctly identifies as a Critical defect.

**Required Action:**
1. Add to `ProductionMaterialUsage`:
   - `unit_cost_paisa_snapshot: BigInteger NOT NULL DEFAULT 0` — weighted average cost per material unit at the moment of BOM issuance
2. Add to `ProductionBatch`:
   - `material_cost_paisa: BigInteger NOT NULL DEFAULT 0`
   - `labor_cost_paisa: BigInteger NOT NULL DEFAULT 0`
   - `overhead_cost_paisa: BigInteger NOT NULL DEFAULT 0`
   - `batch_total_cost_paisa: BigInteger NOT NULL DEFAULT 0` — sum, populated when batch transitions to COMPLETED
3. Write a new Alembic migration (revision after `023_add_branches_and_warehouse_link.py`).
4. The batch completion handler must atomically calculate and persist `batch_total_cost_paisa` before the status transitions to `COMPLETED`.

**Resolution Owner:** Engineering  
**Estimated Effort:** 0.5 days (schema) + 1 day (handler logic)  
**References:** `backend/app/models/production.py` lines 6–39, `backend/app/api/v1/production.py`

---

## 2. High Severity Issues (Accounting Policy Decisions)

### VAL-03: Revenue and COGS Recognition Date Must Be Formalized
**Severity:** HIGH  
**Found In:** `docs/PHASE_6A_POSTING_MATRIX.md Events 10 and 11`  
**Concrete Risk:** Current specification posts COGS on `SalesOrder.DISPATCHED` and Revenue on `Invoice.finalized`. If these occur in different accounting periods, one period shows revenue without COGS and another shows COGS without revenue. Monthly P&L is unreliable.

**Required CA Decision:** One of the following:
- **Option A:** Both COGS and Revenue post simultaneously on dispatch (no invoice-date gap)
- **Option B:** Both post simultaneously on invoice finalization (no dispatch-date COGS)
- **Option C:** Accrual bridge — COGS on dispatch, Revenue on invoice, with Deferred Revenue liability bridging periods

**Required Action (Engineering, after CA decision):**
- Update PHASE_6A_POSTING_MATRIX.md §Events 10 and 11 with the agreed trigger
- If Option C: add `2135 Deferred Revenue` account to COA under Liabilities

**Resolution Owner:** Chartered Accountant (policy decision) + Engineering (implementation)  
**References:** `backend/app/api/v1/sales.py` (dispatch handler), `backend/app/api/v1/invoices.py` (finalize handler)

---

### VAL-04: TDS Slab Narrative Requires Clarification
**Severity:** HIGH  
**Found In:** `docs/PHASE_6A_POSTING_MATRIX.md §3 Example 2`  
**Concrete Risk:** The "1%" label implies a flat rate. Future payroll engineers may apply 1% to all workers regardless of income, causing systematic TDS undercharge for higher-earning supervisors and managers.

**Required Action:**
1. Add a TDS Rate Table section to the posting specification:
   ```
   Nepal Income Tax Act 2058 Schedule 1 — Annual Salary Slabs:
   Slab 1: 0 – NPR 600,000     → 1%
   Slab 2: 600,001 – 1,500,000 → 10%
   Slab 3: 1,500,001–2,000,000 → 20%
   Slab 4: > 2,000,000         → 30%
   ```
2. State that TDS is computed on annualized monthly gross (not just that month's gross).
3. Note that the Social Security Fund (SSF) Act 2074 also mandates contributions (employee 11% + employer 20% of basic salary) — see Missing Event M5.

**Resolution Owner:** Engineering (spec update) + CA (confirm slab rates for current FY)

---

### VAL-05: Consignment Settlement VAT Base Requires CA Determination
**Severity:** HIGH  
**Found In:** `docs/PHASE_6A_FRANCHISE_AND_BRANCH_ACCOUNTING.md §3.2`, `docs/PHASE_6A_POSTING_MATRIX.md Event 31`  
**Concrete Risk:** If LIVO charges 13% VAT on the wholesale settlement amount for goods the franchisee has already sold and collected VAT on, the VAT on those goods is effectively collected twice at different levels of the supply chain. This is a potential VAT compliance violation.

**Required Action (CA must determine and confirm in writing):**
1. Confirm whether the settlement invoice from LIVO to the franchise partner is subject to Nepal VAT at 13%.
2. If yes: confirm the correct taxable base (wholesale amount exclusive of tax).
3. If no: confirm the statutory basis for VAT exemption on the settlement invoice.
4. Confirm treatment of the 2-3 month COGS recognition lag (when consignment goods sold in Month 1 are only derecognized in Month 3 when the settlement is processed).

**Resolution Owner:** Chartered Accountant (mandatory) + Client Owner (commercial structure)

---

## 3. Medium Severity Issues (Must Fix Before Affected Workflows)

### VAL-06: Account Code 1280 Name Mismatch
**Severity:** MEDIUM  
**Found In:** `docs/PHASE_6A_FRANCHISE_AND_BRANCH_ACCOUNTING.md §2.1` vs `docs/PHASE_6A_CHART_OF_ACCOUNTS.md §2.1`  
**Concrete Risk:** Carrier transit claims posted to `1280 Advances to Suppliers` would contaminate supplier advance balances, making the supplier advance control account unreliable.

**Required Action:**
1. Add to COA: `1295 Carrier & Transit Claims Receivable` as a leaf account under parent `1200 Trade & Other Receivables`
2. Update `PHASE_6A_FRANCHISE_AND_BRANCH_ACCOUNTING.md §2.1` reference from `1280` to `1295`
3. Update `PHASE_6A_POSTING_MATRIX.md Event 28` to reference `1295`

**Resolution Owner:** Engineering  
**Estimated Effort:** 0.25 days

---

### VAL-07: `fiscal_periods` Table Missing `company_id`
**Severity:** MEDIUM  
**Found In:** `docs/PHASE_6A_ACCOUNTING_ARCHITECTURE.md §3.1`  
**Concrete Risk:** Multi-tenant period lock queries require a two-hop JOIN through `fiscal_years` to reach `company_id`. A bug in the join could check a different company's period lock status.

**Required Action:**
1. Add `company_id: Integer, FK(companies.id), NOT NULL` to `fiscal_periods` table spec
2. Add unique constraint: `UNIQUE(company_id, fiscal_year_id, period_number)`
3. Add covering index: `INDEX(company_id, is_locked)`
4. Update `PHASE_6A_ACCOUNTING_ARCHITECTURE.md §3.1` with the corrected schema

**Resolution Owner:** Engineering  
**Estimated Effort:** 0.5 days

---

### VAL-08: User Role Model Insufficient for Financial RBAC
**Severity:** MEDIUM  
**Found In:** `docs/PHASE_6A_ACCOUNTING_ARCHITECTURE.md §5.1` vs `backend/app/models/user.py line 15`  
**Concrete Risk:** Financial endpoints are accessible to any `editor`-role user. The "Control Account Enforcement" described in §5.1 is entirely UI-layer until backend role guards are implemented.

**Required Action:**
1. Migrate `users.role` to support expanded enum:
   - Preserve: `viewer`, `editor`
   - Add: `billing_operator`, `inventory_manager`, `branch_manager`, `accountant`, `chief_accountant`, `super_admin`
2. Update `backend/app/api/deps.py` to add role-level dependency guards:
   - `require_accountant()`, `require_chief_accountant()`, etc.
3. Apply role guards to all new Phase 6B financial endpoints
4. Write Alembic migration that maps: current `editor → accountant`, `viewer → billing_operator` as safe defaults

**Resolution Owner:** Engineering  
**Estimated Effort:** 2–3 days

---

## 4. Low Severity Issues (Cleanup)

### VAL-09: Asset Disposal Posts to Parent Account `6400`
**Severity:** LOW  
**Found In:** `docs/PHASE_6A_POSTING_MATRIX.md Event 23`  
**Required Action:** Add leaf account `6430 Loss on Asset Disposal & Write-Off` under parent `6400 Financial & Other Expenses` in the COA. Update Event 23 to reference `6430`.

### VAL-10: Duplicate `source_doc_type` Enum Definitions
**Severity:** LOW  
**Found In:** `docs/PHASE_6A_ACCOUNTING_ARCHITECTURE.md §2.2 and §3.1`  
**Required Action:** Remove the abbreviated enum from §2.2 (Dimensions Matrix). Replace with a reference: "See `source_doc_type` canonical enum in §3.1."

---

## 5. Missing Events (M1–M7) — Additional Coverage Required

These financial scenarios are not in the 34-event posting matrix but will arise during Phase 6B implementation:

### M1 — VAT Input Credit on Raw Material Purchases
**Missing from:** Posting Matrix  
**Required if:** LIVO is a registered VAT payer purchasing from VAT-registered suppliers  
**Posting:**
```
DR  1410  Value Added Tax (VAT) Input Credit      [purchase_vat_paisa]
  CR  2110  Accounts Payable - Material Suppliers   [purchase_vat_paisa]
```
**CA Decision Required:** Confirm LIVO's VAT input credit eligibility and whether Chinese imports carry IRD-recognized input VAT.

### M2 — Monthly VAT Return Net Settlement
**Missing from:** Posting Matrix  
**Posting:**
```
DR  2310  VAT Output Liability                    [total_output_vat_paisa]
  CR  1410  VAT Input Credit                        [total_input_vat_paisa]
  CR  1150  Operating Bank Account                  [net_vat_payable_paisa]
```
**CA Decision Required:** Confirm filing deadline (25th of following month) and penalty structure.

### M3 — Opening Balances (Initial GL Setup)
**Missing from:** Posting Matrix  
**Required for:** Initial deployment with historical financial data migration  
**Posting:** Dr all Asset accounts; Cr all Liability accounts; Cr 3200 Retained Earnings for the balancing difference  
**CA Sign-Off Required:** Opening trial balance must be certified by CA before posting.

### M4 — Year-End Closing Entry
**Missing from:** Posting Matrix  
**Posting:**
```
DR  4000-4999  All Revenue Accounts             [total_revenue_paisa]
  CR  3300  Current Year Profit / Loss Summary   [net_profit_paisa]
  CR  5000-6999  All Expense Accounts            [total_expense_paisa]
Then:
DR  3300  Current Year Profit / Loss Summary    [net_profit_paisa]
  CR  3200  Retained Earnings                    [net_profit_paisa]
```

### M5 — Social Security Fund (SSF) Contributions
**Missing from:** Posting Matrix and COA  
**Under SSF Act 2074:** Employee contributes 11%, employer contributes 20% of basic salary  
**Posting:**
```
DR  6310  Administrative Salaries (SSF Employer 20%)
  CR  2220  Social Security Fund Payable
```
**CA Decision Required:** Confirm whether LIVO's workers are enrolled in SSF or an alternative provident fund.

### M6 — Customer Credit Limit Enforcement
**Missing from:** Posting Matrix  
**No journal entry required** but posting handler for Event 11 must check: `GL_Balance(1210, client_id) + new_invoice_total ≤ client.credit_limit` before finalization.

### M7 — VAT Input on Fixed Asset Acquisition
**Missing from:** Posting Matrix  
**Posting:**
```
DR  1410  VAT Input Credit                       [asset_vat_paisa]
DR  1510  Fixed Asset Cost                       [asset_ex_vat_paisa]
  CR  2110  Accounts Payable                      [total_asset_invoice_paisa]
```
**CA Decision Required:** Confirm if capital goods VAT is fully recoverable as input credit or must be capitalized.

---

## 6. Closing Disposition Statement

The Phase 6A specification is **PASS WITH LIMITATIONS**. The following must be completed before Phase 6B implementation begins:

**Hard Blocks (cannot code until resolved):**
1. VAL-01: Event action enum defined *(Engineering, ~2 days)*
2. VAL-02: Production cost schema fields *(Engineering, ~1.5 days)*
3. VAL-03: Revenue/COGS recognition date *(CA decision + 0.5 day spec update)*
4. VAL-05: Consignment VAT base *(CA decision + 0.5 day spec update)*
5. VAL-07: `fiscal_periods.company_id` *(Engineering, ~0.5 days)*
6. VAL-08: Role system extension *(Engineering, ~2.5 days)*

**Should Fix Before Coding (not hard blocks but high risk if deferred):**
7. VAL-04: TDS slab narrative *(Engineering, ~0.25 days)*
8. VAL-06: Account 1295 added to COA *(Engineering, ~0.25 days)*

**Can Fix During Phase 6B Without Risk:**
9. VAL-09: Account 6430 added to COA leaf
10. VAL-10: Unified source_doc_type enum
11. M1–M7: Missing event specifications (add incrementally)

**Total Engineering Pre-Work Estimate:** ~8 days before first Phase 6B financial route is safe to implement.
