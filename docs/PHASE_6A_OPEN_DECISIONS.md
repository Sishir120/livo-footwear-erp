# LIVO FOOTWEAR ERP — PHASE 6A: MANDATORY OPEN DECISIONS & SIGN-OFF REGISTER

**Status:** ARCHITECTURAL SPECIFICATION & CLIENT/ACCOUNTANT DECISION REGISTER  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Financial Implementation  

---

## 1. Governance & Approval Protocol

In accordance with professional accounting standards and the engineering guidelines of this ERP project:
**Software engineers do not decide accounting policies, tax classifications, or commercial contract structures in isolation.**

Each decision in this register represents an operational, tax, or statutory fork that requires explicit sign-off by either:
1. **Client Owner / Executive Management (C-Level)**
2. **Certified Chartered Accountant (CA) / Tax Auditor (Nepal)**
3. **Operations & Warehouse Director**

---

## 2. Mandatory Open Decisions Register

### Decision 1: Legal Entity Structure of Franchise Partners
- **Issue:** Are franchise partners (e.g., Pokhara Footwear Center, Dharan Retail Partner) legally distinct corporate entities, or are they operating under LIVO Footwear Industries Pvt. Ltd.'s PAN as internal branches?
- **Available Options:**
  - *Option A (Independent Legal Entities):* Franchisees possess their own 9-digit PAN/VAT certificate, operate their own bank accounts, and file their own IRD tax returns. Transactions with LIVO are B2B wholesale transactions.
  - *Option B (Company Branches):* Franchisees are operated as internal branches under LIVO's central PAN with branch suffixes. LIVO remains legally liable for retail taxes and store lease liabilities.
- **Accounting & Tax Impact:** Under Option A, transfers are external sales or formal consignment subject to B2B tax invoicing. Under Option B, transfers are non-tax internal movements, and retail cash belongs directly to LIVO.
- **Recommended Default:** **Option A (Independent Legal Entities)**. In the Nepal footwear sector, regional dealers and showroom partners operate under independent business registrations.
- **Required Approval:** **Client Executive & Chartered Accountant**.

---

### Decision 2: Franchise Commercial Inventory Model (Outright Sale vs. Consignment)
- **Issue:** Under what commercial terms does footwear move from LIVO's central factory to franchise partner locations?
- **Available Options:**
  - *Option A (Outright Wholesale Purchase):* Footwear is billed via a statutory B2B Tax Invoice with 13% VAT upon factory dispatch. Risk and title pass immediately to the franchisee. Payment is governed by credit terms (e.g., 30 days).
  - *Option B (Consignment Stock Model):* Footwear moves under non-tax Consignment Challans (`CNG-`). LIVO retains title and inventory risk. The franchisee acts as an agent, reporting sales monthly. LIVO bills the franchisee only for pairs sold, less an agreed retail commission.
- **Accounting & Tax Impact:** Option A accelerates revenue recognition and generates immediate output VAT liabilities. Option B defers VAT until retail sale, but requires compliance with Section 14 of the Nepal VAT Act (Consignment filing with IRD) and exposes LIVO to store shrinkage/damage risk.
- **Recommended Default:** **Option A (Outright Wholesale Purchase)** for standard footwear orders, with an optional contract toggle for Option B for high-value pilot stores.
- **Required Approval:** **Client Owner & Chief Accountant**.

---

### Decision 3: Franchise Royalty & License Settlement Structure
- **Issue:** How are brand franchise fees, setup costs, and recurring royalties structured and billed?
- **Available Options:**
  - *Option A (Margin-Only / Embedded):* No separate franchise royalty. LIVO earns its return purely through the wholesale margin on shoe pairs sold.
  - *Option B (Fixed Fee + Royalty):* An upfront non-refundable onboarding fee (e.g., NPR 100,000) plus an ongoing turnover royalty (e.g., 3% of retail sales), billed via monthly tax invoice.
- **Accounting & Tax Impact:** Option B creates a secondary revenue class (`4210 Franchise Royalties`) requiring separate VAT output recognition and monthly sales audits of franchisee POS terminals.
- **Recommended Default:** **Option A (Margin-Only)** for Phase 6, with schema support for Option B when the franchise network scales.
- **Required Approval:** **Client Owner**.

---

### Decision 4: Inventory Valuation Methodology (NAS 2 / IAS 2)
- **Issue:** How should raw material consumption and finished goods inventory be valued for financial balance sheet reporting?
- **Available Options:**
  - *Option A (Moving Weighted Average Cost):* Real-time re-averaging of unit costs upon each GRN receipt and landed cost allocation.
  - *Option B (First-In, First-Out - FIFO):* Exhausting oldest purchased material batches first.
  - *Option C (Standard Costing with Monthly Variance Absorption):* Pre-set standard BOM cost updated quarterly; actual purchase price and labor variances written off to variance GL accounts.
- **Accounting & Tax Impact:** NAS 2 permits either FIFO or Weighted Average. LIFO is strictly prohibited. Moving Weighted Average matches the ERP's relational database architecture and avoids complex lot-tracking joins across unbatchable bulk materials (e.g., barrels of adhesive, leather scrap).
- **Recommended Default:** **Option A (Moving Weighted Average Cost)**.
- **Required Approval:** **Chartered Accountant / Tax Auditor**.

---

### Decision 5: Fixed Asset Depreciation Policy & Tax Alignment
- **Issue:** Which depreciation method and rates should be applied to machinery, moulds, vehicles, and furniture?
- **Available Options:**
  - *Option A (Straight-Line Method - SLM for Financials):* Equal annual depreciation over economic useful life (e.g., Machinery: 10 years [10%], Moulds: 3 years [33.3%], Vehicles: 5 years [20%], Furniture: 10 years [10%]).
  - *Option B (Tax Depreciation Pooling under Nepal Income Tax Act 2058):* Written-Down Value (WDV) diminishing balance pooling:
    - *Pool A (Buildings):* 5%
    - *Pool B (Office Furniture & Fixtures):* 25%
    - *Pool C (Automobiles & Delivery Vans):* 20%
    - *Pool D (Factory Machinery, Moulds & Equipment):* 15%
- **Accounting & Tax Impact:** Option B aligns the financial books directly with the statutory tax return, eliminating deferred tax calculations under NAS 12. Option A reflects truer economic wear (especially for fashion shoe moulds which obsolete quickly).
- **Recommended Default:** **Option B (Tax Pooling under Schedule 2)** for SME simplicity, with an optional accelerated write-off policy for shoe moulds.
- **Required Approval:** **Chartered Accountant**.

---

### Decision 6: Accounting Period Lock & Prior-Period Correction Policy
- **Issue:** How should corrections to posted transactions in closed or historical periods be handled?
- **Available Options:**
  - *Option A (Strict Forward-Only Adjusting Entries):* Closed periods (e.g., previous month once VAT return is filed on the 25th) can **never** be unlocked. Any discovered error must be corrected via an adjusting journal posted in the current active period.
  - *Option B (Audited Period Reopening):* A `SUPER_ADMIN` or `CHIEF_ACCOUNTANT` can temporarily unlock a closed period, post a back-dated correcting entry, and re-lock the period, generating an automated IRD revised return notice.
- **Accounting & Tax Impact:** Under Nepal VAT rules, amending a finalized period after the monthly VAT return submission requires a formal revised return filing (अनुसूची-१० or amendment application) and exposes the firm to penalties if output tax increases.
- **Recommended Default:** **Option A (Strict Forward-Only Adjusting Entries)**. Historical periods remain completely frozen once closed.
- **Required Approval:** **Chief Accountant / Tax Auditor**.

---

### Decision 7: Statutory IRD Electronic Invoicing & VCTS Integration
- **Issue:** Does LIVO Footwear meet the statutory turnover threshold requiring real-time CBMS electronic invoicing integration with the Inland Revenue Department (IRD), and must road transit be registered on the VCTS portal?
- **Available Options:**
  - *Option A (Internal Sequenced Invoicing):* System enforces immutable sequential numbering and generates print-ready Annex-5 tax invoices and Annex-10 credit notes, but does not push live payloads to the IRD API.
  - *Option B (Certified IRD Real-Time E-Billing):* System integrates directly with the IRD Central Billing Monitoring System (CBMS) API, pushing JSON payloads synchronously upon invoice finalization.
  - *VCTS Requirement:* Ministry of Finance mandates that inter-city commercial road transport of goods must be logged in the Vehicle and Consignment Tracking System (VCTS) prior to dispatch.
- **Accounting & Tax Impact:** Non-compliance with CBMS/VCTS if turnover exceeds thresholds attracts severe statutory fines from the Department of Revenue Investigation (DRI).
- **Recommended Default:** Verify current annual turnover with client. If below NPR 25 Crore, implement **Option A** with schema hooks ready for CBMS API certification when mandated. Mandate VCTS challan generation for all factory-to-showroom transit.
- **Required Approval:** **Client Executive & Tax Legal Counsel**.

---

### Decision 8: Branch-Level User Access & Margin Visibility
- **Issue:** What level of financial visibility should retail showroom managers and branch cashiers have within the ERP?
- **Available Options:**
  - *Option A (Isolated Retail POS Visibility):* Branch staff see only their branch's retail sales, cash drawer receipts, and local inventory quantities. Manufacturing costs, wholesale supplier bills, and central factory gross profit are hidden.
  - *Option B (Branch Contribution P&L Visibility):* Branch managers can view their specific branch contribution margin (Retail Sales minus Manufacturing Cost of sold pairs minus Branch Expenses) to incentivize store profitability.
- **Accounting & Tax Impact:** Relates to operational confidentiality and role-based permissions (`backend/app/api/deps.py`).
- **Recommended Default:** **Option A** for retail cashiers; **Option B** for Branch Managers (restricted strictly to their assigned `branch_id`).
- **Required Approval:** **Client Operations Director**.

---

## 3. Implementation Readiness Assessment

### 3.1 What Is Already Implemented & Tested (Phase 5 Baseline)
- High-concurrency pessimistic locking and transactional boundaries for stock movements and transfers (`backend/app/core/locks.py`, `StockTransfer`).
- Exact integer-paisa financial arithmetic across invoices, worker payroll, and expense tables (`Invoice`, `ReceivableEntry`, `WorkerMonthlyRecord`, `FactoryExpense`).
- 13% statutory Nepal VAT calculations and immutable Annex-10 credit note mechanics.
- Company-owned branch master data and warehouse linking (`Branch`, `Warehouse`).
- 520 automated backend unit and integration tests passing; clean frontend Next.js production build.

### 3.2 What Must Be Built in Phase 6B (Implementation Phase)
1. **Database Schema & Migrations:**
   - Create tables: `fiscal_years`, `fiscal_periods`, `accounts`, `journal_entries`, `journal_lines`, `account_period_balances`.
2. **Core Posting Engine:**
   - Double-entry validation service enforcing $\sum \text{Debits} = \sum \text{Credits}$ with 0-paisa tolerance.
   - Idempotent transaction wrappers executing within existing operational handlers (`invoices.py`, `purchases.py`, `stock_transfer.py`, `hr.py`).
3. **Control Account Reconciliation Daemon:**
   - Automated nightly reconciliation checking GL controls against AR, AP, Inventory, and Payroll.
4. **Financial Reporting Engine:**
   - General Ledger Inquiry, Trial Balance, Profit & Loss Statement (Company & Branch-Segmented), and Balance Sheet.

### 3.3 Recommended Phase 6B Implementation Sequence
```
Step 1: Schema Migration (Accounts, Fiscal Periods, Journal Entries)
   |
Step 2: Seed Authoritative Footwear Chart of Accounts (COA)
   |
Step 3: Build & Unit Test Core Posting Engine (Balance Invariant & Idempotency)
   |
Step 4: Attach Posting Hooks to Existing Handlers (Invoices, Purchases, Payroll)
   |
Step 5: Implement Nightly Subledger Reconciliation & Invariant Alerts
   |
Step 6: Build Financial Reports (Trial Balance, P&L, Balance Sheet)
```
