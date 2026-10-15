# LIVO FOOTWEAR ERP — FINANCIAL ACCOUNTING AND RECONCILIATION AUDIT

**Audit Date:** 2026-10-14  
**Auditor Roles:** Senior ERP Financial Systems Analyst, Lead Forensic Accountant  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Target Branch:** `release/v1.0.0-staging`  

---

## 1. Executive Accounting Verdict

> [!IMPORTANT]
> **Definitive Finding:** LIVO Footwear ERP is an **OPERATIONAL ERP WITH SPECIALIZED SUBLEDGERS AND FINANCIAL ARITHMETIC**, and is **NOT A COMPLETE DOUBLE-ENTRY ACCOUNTING SYSTEM**.

The repository does **NOT** contain a general ledger, does **NOT** implement double-entry balanced journal vouchers, and does **NOT** produce financial statements (Trial Balance, Profit & Loss, Balance Sheet). It successfully tracks specific operational subledgers (Debtors/AR, Payroll Advances, Landed Costs, Tax Invoices, and Scrap), but cannot replace a company's core accounting software without substantial ledger development.

---

## 2. General Ledger Capability Audit

| Core Accounting Component | Status in Codebase | Evidence / Findings |
|---|:---:|---|
| **Chart of Accounts (COA)** | **NOT FOUND** | Zero tables, models, or schemas exist for Account Codes, Account Types (Asset/Liability/Equity/Revenue/Expense), or Account Trees. |
| **Double-Entry Journal Entries** | **EXPLICITLY DROPPED** | In migration `762ea2a34ccb:28-35`, legacy prototype tables `journal_entries`, `journal_vouchers`, `ledger_accounts`, and `account_groups` were **dropped**. Zero replacements exist in `models/`. |
| **Balanced-Entry Enforcement (Debits == Credits)** | **NOT FOUND** | No system-wide validation requiring total debits to equal total credits across posted transactions. |
| **Accounting Periods & Close Controls** | **NOT FOUND** | No fiscal year definitions, no month-end lock dates, no period-close or period-reopen audit controls. |
| **Trial Balance** | **NOT FOUND** | No endpoint or report to aggregate account debits/credits. |
| **Profit & Loss Statement (Income Statement)** | **NOT FOUND** | No dynamic P&L report. Revenue and expenses exist in isolated subledgers without consolidation into net income. |
| **Balance Sheet** | **NOT FOUND** | No balance sheet. Assets, liabilities, and retained earnings are not aggregated into an accounting equation. |
| **Bank Reconciliation** | **NOT FOUND** | No bank statement import, clearance dates, or unpresented cheque reconciliation workflows. |
| **Opening Balances** | **NOT FOUND** | No mechanism to migrate historical opening balances for general ledger accounts. |
| **Cost of Goods Sold (COGS) Ledger** | **NOT FOUND** | When goods are sold and dispatched, finished goods inventory quantity is reduced, but NO journal entry is posted debiting COGS and crediting Finished Inventory Asset. |

---

## 3. Operational Subledgers: Detailed Flow Analysis

While a double-entry general ledger is absent, the ERP implements six robust, self-contained operational subledgers:

### 3.1 Accounts Receivable (AR) Debtor Subledger
- **Models:** `ReceivableEntry`, `PaymentAllocation` (`backend/app/models/receivable.py`)
- **Architecture:** Append-only ledger with directional entries:
  - `direction = +1`: `INVOICE_POSTED` (debits client account upon invoice generation)
  - `direction = -1`: `PAYMENT_CASH`, `PAYMENT_BANK`, `CREDIT_MEMO` (credits client account upon payment)
- **Features:**
  - Real-time running balance calculation: `client.outstanding_balance_paisa`.
  - Credit limit enforcement with visual badge `[EXCEEDED]`.
  - Aging analysis buckets: Current (0–30 days), 31–60 days, 61–90 days, 90+ days.
  - Multi-invoice payment allocation: payments can be apportioned across specific unpaid invoices.
  - Dispute auditing: individual ledger lines can be flagged `is_disputed` with auditable dispute notes.
- **Verification:** Verified passing in `test_receivables.py` and `test_checkpoint_16_business_security.py`.

### 3.2 Worker Advances & Payroll Ledger
- **Models:** `WorkerAdvance`, `WorkerMonthlyRecord`, `CompanyHRSettings` (`backend/app/models/worker.py`)
- **Architecture:**
  - `WorkerAdvance.entry_type`: `ISSUED` (advance taken) vs `RECOVERED` (salary deduction).
  - FIFO automatic advance recovery: advances are repaid against oldest open advance records.
  - Monthly payroll calculations with snapshot inputs: standard monthly hours (default 208 hrs), overtime multiplier (1.5x), maximum advance deduction ceiling (default 50% of gross pay).
- **Verification:** Verified passing in `test_phase_4b4_1_settings_and_snapshots.py` and `test_phase_4b4_2_c1_c2_reconciliation.py`.

### 3.3 Raw Material Landed Cost Capitalization
- **Models:** `PurchaseOrder`, `PurchaseItem`, `RawMaterialMovement` (`backend/app/models/purchase.py`)
- **Architecture:**
  - Decoupled Purchase Order Date (`order_date_ad`) vs Goods Receipt Date (`receipt_date_ad`).
  - 4-Column auxiliary landed costs: Customs Duty (`customs_duty_paisa`), Freight (`freight_paisa`), Insurance (`insurance_paisa`), Handling (`loading_unloading_paisa`).
  - Auxiliary costs are apportioned across line items and capitalized directly into `RawMaterial.standard_cost` and `RawMaterialMovement.unit_cost_paisa`.
- **Accounting Note:** Capitalizes costs into inventory asset value, but does not post accounts payable vouchers.

### 3.4 Finished Goods Sales Invoicing & 13% VAT
- **Models:** `Invoice`, `SalesOrder`, `SalesItem` (`backend/app/models/sales.py`)
- **Architecture:**
  - Decoupled Order Date (`order_date_ad`) vs Physical Dispatch Date (`dispatch_date_ad`).
  - Tax invoice numbering: strictly sequential (`INV-000001`), enforced via advisory locks.
  - Tax arithmetic: Gross Amount, Line Discounts, 13% Nepal VAT, Non-Taxable amount, Net Amount.
  - Voiding controls: Invoices cannot be deleted. Voiding requires `admin` role and an auditable `void_reason`.
- **Compliance Note:** Meets Nepal IRD Schedule-5 formatting layout, but lacks direct IRD real-time CBMS API sync.

### 3.5 Factory Operating Expenses Log
- **Models:** `FactoryExpense` (`backend/app/models/sales.py:199`)
- **Architecture:** Single-entry log categorized by `FACTORY_RENT`, `ELECTRICITY_WATER`, `GENERATOR_FUEL`, `MACHINE_MAINTENANCE`, `FACTORY_LABOR`, `OFFICE_SUPPLIES`, `TEA_REFRESHMENT`, `OTHER`.
- **Limitation:** Purely informational logging. Does not credit Cash/Bank accounts or integrate into trial balance. Zero frontend screen currently exists.

### 3.6 Fixed Assets & Depreciation
- **Models:** `FixedAsset`, `AssetDepreciation` (`backend/app/models/asset.py`)
- **Architecture:** Tracks capital assets (machinery, lasts, cutting dies, vehicles), purchase cost in paisa, useful life, salvage value, and annual straight-line depreciation.
- **Limitation:** Depreciation calculations are informational; no journal vouchers are posted. Zero frontend screen currently exists.

---

## 4. Transaction-to-Ledger Reconciliation Matrix

| Business Transaction | Operational Record | Subledger Effect | General Ledger (GL) Effect | Financial Reconciled? |
|---|---|---|---|:---:|
| **Supplier PO Placement** | `PurchaseOrder` | None (Commitment) | None | N/A |
| **Raw Material Receipt (GRN)** | `RawMaterialMovement` | Capitalizes landed cost into unit rate | **None (Missing AP voucher)** | **PARTIAL** |
| **Material Issue to Production** | `ProductionBatch` | Deducts RM quantity per BOM | **None (Missing WIP voucher)** | **PARTIAL** |
| **Finished Goods Receipt** | `StockMovement` (+1) | Adds FG quantity to warehouse | **None (Missing FG Asset voucher)**| **PARTIAL** |
| **Sales Order Entry** | `SalesOrder` | None (Reservation) | None | N/A |
| **Sales Order Physical Dispatch**| `StockMovement` (-1) | Deducts FG quantity from warehouse | **None (Missing COGS relief)** | **PARTIAL** |
| **Sales Tax Invoice Issue** | `Invoice` | **Debits Client AR subledger (+1)** | **None (Missing Sales & VAT Output)**| **PARTIAL** |
| **Customer Payment Receipt** | `ReceivableEntry` | **Credits Client AR subledger (-1)**| **None (Missing Cash/Bank debit)** | **PARTIAL** |
| **Worker Advance Disbursement** | `WorkerAdvance` (ISSUED)| Increases worker advance balance | **None (Missing Cash credit)** | **PARTIAL** |
| **Payroll Advance Deduction** | `WorkerAdvance` (RECOVERED)| Reduces worker advance balance | **None (Missing Wage expense voucher)**| **PARTIAL** |
| **Factory Operating Expense** | `FactoryExpense` | Records expense voucher entry | **None (Missing Bank/Cash credit)**| **PARTIAL** |
| **Fixed Asset Purchase** | `FixedAsset` | Records asset profile & cost | **None (Missing Fixed Asset debit)**| **PARTIAL** |
| **Asset Depreciation** | `AssetDepreciation` | Computes straight-line amortization| **None (Missing Depreciation expense)**| **PARTIAL** |

---

## 5. Auditor Recommendations for Accounting Completeness

If the client requires full accounting replacement rather than operational subledgers:
1. **Phase A (Subledger Integration):** Keep existing operational subledgers intact as the single source of truth for manufacturing, inventory, and billing.
2. **Phase B (General Ledger Architecture):** Design a Chart of Accounts and posting rules engine that subscribes to operational events (GRN, Dispatch, Invoicing, Payment, Payroll) and generates balanced double-entry journal vouchers asynchronously.
3. **Phase C (Financial Reporting):** Implement Trial Balance, P&L, and Balance Sheet derived strictly from posted journal entries.
