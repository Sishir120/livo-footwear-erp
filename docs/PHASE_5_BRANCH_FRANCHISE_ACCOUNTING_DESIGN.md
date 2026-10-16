# LIVO FOOTWEAR ERP — PHASE 5: BRANCH, WAREHOUSE & FRANCHISE ACCOUNTING ARCHITECTURE & DESIGN

**Status:** ARCHITECTURAL SPECIFICATION & OPERATIONAL DESIGN CONTRACT  
**Version:** 2.0.0  
**Date:** October 2026  
**Target Systems:** LIVO Footwear ERP Backend (FastAPI/SQLAlchemy), Frontend (Next.js/React), PostgreSQL  
**Statutory Context:** Nepal Companies Act 2063, Value Added Tax Act 2052, Income Tax Act 2058  

---

## 1. Executive Summary & Existing Domain Audit

### 1.1 Existing System Capabilities Discovered
An adversarial inspection of the current codebase reveals the following existing domain entities and boundaries:
1. **Tenant / Legal Entity Boundary:**
   - Model `Company` (`companies` table): Defines the legal root with name, legal code, PAN number, address, and phone.
   - Model `User` (`users` table): Belongs to a single `company_id`.
   - `TenantRepository`: Wraps every database query with strict `company_id == current_user.company_id` enforcement.
2. **Physical Warehouses & Inventory Ledger:**
   - Model `Warehouse` (`warehouses` table): Represents physical storage locations (`name`, `code`, `location`, `is_active`).
   - Model `StockMovement` (`stock_movements` table): Append-only transactional ledger tracking product variants, sizes, quantities, and directions (+1, -1, 0) across warehouses.
   - Model `StockTransfer` (`stock_transfers` table): Multi-warehouse transfer lifecycle (`DRAFT` -> `IN_TRANSIT` -> `RECEIVED` / `CANCELLED`) with strict stock conservation:
     $$\text{dispatched\_qty} = \text{received\_qty} + \text{in\_transit\_qty} + \text{resolved\_discrepancy\_qty}$$
3. **Purchasing, Production & Sales:**
   - Model `Purchase` / `RawMaterialMovement`: Central procurement of soles, leather, buckles, and fabrics.
   - Model `ProductionBatch` / `BillOfMaterials`: Consumption of raw materials into finished footwear variants.
   - Model `SalesOrder` / `Invoice` / `ReceivableEntry`: Wholesale customer billing with authoritative integer-paisa 13% Nepal VAT, immutability on finalization, and credit notes (अनुसूची-१०).
4. **General Ledger Gap Analysis:**
   - **Finding:** A traditional double-entry General Ledger table (`accounts`, `journal_entries`, `journal_lines`, `gl_periods`) **does not exist** in the current database.
   - **Current Reality:** Financial transactions are recorded in specialized, auditable **operational subledgers**:
     - *Accounts Receivable Subledger:* `ReceivableEntry` (INVOICE, PAYMENT, CREDIT_NOTE, VOID_REVERSAL).
     - *Inventory Valuation Subledger:* `StockMovement` & `StockSnapshot`.
     - *Factory Cost & Expense Ledger:* `FactoryExpense` (has `amount_paisa`, `category`, and a historical text column `branch`).
     - *Fixed Asset Register:* `FixedAsset` (cost, depreciation).
   - **Architectural Mandate:** Do NOT fabricate a parallel, fake double-entry ledger that competes with existing subledgers. A formal double-entry chart of accounts requires dedicated accounting period closing controls, debit/credit balancing engines, and client CFO validation.

---

## 2. Explicit Domain Boundaries

To prevent confusion between legal accountability, physical inventory custody, and commercial contracts, the domain is split into four distinct tiers:

```
+-----------------------------------------------------------------------------------+
|                                 LEGAL ENTITY                                      |
|                     (Company: [COMPANY_NAME] — PAN: [PAN])                        |
+-----------------------------------------------------------------------------------+
         |                                                              |
         | (100% Owned Operating Units)                                 | (Commercial B2B Contract)
         v                                                              v
+-----------------------------------+                          +-----------------------------------+
|         INTERNAL BRANCHES         |                          |         FRANCHISE PARTNERS        |
| - Birgunj Central Factory         |                          | - Pokhara Footwear Center         |
| - Kathmandu Main Showroom         |                          | - Dharan Retail Partner           |
| (Same Legal Entity, Same PAN)     |                          | (Independent Entity, Own PAN)     |
+-----------------------------------+                          +-----------------------------------+
         |                                                              |
         | Operates & Controls                                          | Independent Custody
         v                                                              v
+-----------------------------------+                          +-----------------------------------+
|        PHYSICAL WAREHOUSES        |                          |        FRANCHISE WAREHOUSES       |
| - Raw Materials Godown            |                          | - Independent Franchise Stock     |
| - Finished Goods Central Storage  |                          | (Or Consignment Stock Account)    |
| - Showroom Floor Display Stock    |                          +-----------------------------------+
+-----------------------------------+
```

### 2.1 Entity Typology & Distinctions

| Dimension | A. Legal Entity (`Company`) | B. Internal Branch (`Branch`) | C. Stock Location (`Warehouse`) | D. Franchise Partner (`Franchise`) |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Definition** | Statutory legal persona | Internal operating division | Physical storage facility | Independent third-party business |
| **Tax Registration (PAN)** | Unique 9-digit PAN/VAT | Inherits parent company PAN | None (physical node) | Separate independent 9-digit PAN |
| **Inventory Ownership** | Legal balance sheet owner | Internal custody | Physical storage point | Outright owner (Wholesale) or Agent (Consignment) |
| **Invoicing Ability** | Issues statutory Tax Invoices | Issues Invoices under Parent PAN + Branch Code | Issues Delivery Challans / Internal Memos only | Issues retail invoices under own PAN |
| **Financial Nature** | Consolidated Balance Sheet | Profit & Loss / Cost Center | Physical Inventory Subledger | External Customer / Debtor |
| **Staff & Payroll** | Statutory employer | Branch staff cost center | Warehouse labor | Franchisee-employed workers |

---

## 3. Financial Operating Model & Decision Matrix

The following matrix formally evaluates the 10 operational workflows across ownership, stock location, statutory documentation, VAT, and accounting implications:

| # | Operating Workflow | Inventory Owner | Stock Location | Selling Legal Entity | Operational Document | Financial & Ledger Postings | VAT / Sequence Implication | Client / CA Decision Required |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Internal Transfer: Factory to Showroom** | Parent Company | Factory WH $\to$ Showroom WH | None (Internal) | `StockTransfer` + Internal Delivery Challan (`DC-`) | Inventory Subledger: `TRANSFER_OUT` $\to$ `TRANSFER_IN`. No revenue or AR. | No VAT. Non-tax internal transfer sequence. | Confirm if transport requires VCTS (DRI) declaration for road transit. |
| **2** | **Intra-Branch Transfer (e.g. WH A to WH B)** | Parent Company | Branch WH 1 $\to$ Branch WH 2 | None (Internal) | Internal Transfer Memo / Challan | Inventory Subledger: Location reclassification. Zero financial posting. | No VAT. No tax impact. | None. Standard physical stock movement. |
| **3** | **Inter-Branch Transfer Across Regions** | Parent Company | Central Hub $\to$ Regional Outlet | None (Internal) | `StockTransfer` + Road Challan | Inventory Subledger: In-transit stock tracking until destination receipt. | No VAT. No sale recognized. | Define transit shortage policy (driver chargeback vs factory write-off). |
| **4** | **Outright Sale to Franchisee** | Franchisee (upon dispatch) | Central WH $\to$ Franchise WH | Parent Company | Sales Order + B2B Tax Invoice (`INV-`) | AR Subledger: Debit Franchisee AR; Credit Sales Revenue + Output VAT. | 13% Nepal VAT charged on wholesale price. Unique statutory invoice sequence. | Confirm franchisee payment terms and wholesale credit limit. |
| **5** | **Consignment Stock to Franchisee** | Parent Company (until retail sale) | Parent WH $\to$ Franchise Consignment WH | Parent Company | Consignment Challan (`CNG-`) | Stock remains company asset in designated Consignment WH. No revenue. | No VAT on dispatch. VAT applies only upon retail sale notification. | Formal CA review of consignment tax risk under Nepal VAT Act §14. |
| **6** | **Franchise Retail Sale & Settlement** | End Consumer | Franchise Consignment WH $\to$ Consumer | Franchisee (Retail) / Parent (Wholesale) | Franchise Retail Bill + Parent Settlement Invoice | Revenue recognized; Franchisee AR debited wholesale amount; Royalty credited. | Franchisee bills consumer with own VAT; Parent bills franchisee wholesale. | Confirm whether settlement is monthly commission or weekly sweep. |
| **7** | **Customer Return to Branch** | Parent Company | Customer $\to$ Branch Showroom WH | Parent Company | Credit Note (अनुसूची-१०) | AR Subledger: Credit Note entry (-1) reducing customer balance and VAT liability. | Reduces output VAT liability; requires reference to original invoice. | Validate if return requires factory quality inspection before restocking. |
| **8** | **Branch Expense Paid Centrally** | N/A | N/A | Parent Company | Expense Voucher + Supplier Bill | Expense Subledger: Debit Branch Cost Center Expense; Credit Central Cash/Bank. | Input VAT deductible by Parent Company if valid VAT bill exists. | Establish branch manager discretionary expense approval limit. |
| **9** | **Central Procurement for Branches** | Parent Company | Supplier $\to$ Central Receiving WH | Supplier | Purchase Order + Goods Receipt (`GRN`) | AP Subledger: Credit Supplier AP; Debit Raw Material / Finished Inventory. | Input VAT credited on central company VAT ledger. | Decide whether supplier delivers directly to branch or via central hub. |
| **10**| **Intercompany Transfer (Sister Entities)** | Entity B (post-sale) | Entity A WH $\to$ Entity B WH | Entity A | B2B Commercial Tax Invoice | Entity A: Dr. Entity B AR, Cr. Revenue/VAT. Entity B: Dr. Inventory, Cr. Entity A AP. | Full 13% VAT charged. Arms-length transfer pricing rules apply. | Mandatory Nepal Transfer Pricing audit review under Income Tax Act §33. |

---

## 4. Minimal Chart-of-Accounts & General Ledger Strategy

### 4.1 Ledger Evaluation
- The current ERP functions on an **Operational Subledger Architecture**:
  - `StockMovement`: Pure quantity conservation and movement categorization.
  - `ReceivableEntry`: Customer accounts receivable ledger with integer-paisa tracking.
  - `FactoryExpense`: Operational overhead tracking by category and branch.
- **Why NOT inject a fake double-entry GL now?**
  - Injecting arbitrary debit/credit tables without an authoritative Chart of Accounts (COA), accounting period locks, trial balance generators, and bank reconciliation introduces high risk of financial desynchronization.
  - The correct architectural progression is:
    1. **Phase 5 (Current):** Establish operational Branch and Warehouse master data, linking physical stock locations and cost centers.
    2. **Phase 6:** Introduce Chart of Accounts (COA) and Branch-dimensional Journal Posting once client accounting policies are formalized.

---

## 5. Selected Vertical Slice: Company-Owned Branch & Warehouse Foundation

To deliver maximum immediate operational value with zero financial corruption risk, Phase 5 implements:

**Company-Owned Branch Registration & Warehouse Attribution**
1. **Branch Master Entity:**
   - Model `Branch`: `(id, company_id, code, name, type, address, phone, email, is_active, created_at, updated_at)`.
   - Branch types: `HEAD_OFFICE`, `FACTORY`, `RETAIL_OUTLET`, `REGIONAL_HUB`.
   - Tenant isolation: compound unique constraint `(company_id, code)`.
2. **Warehouse Linking:**
   - Nullable `branch_id` foreign key added to `warehouses` table.
   - Historical warehouses remain 100% valid with `branch_id = NULL`.
   - Warehouses can be associated with or detached from branches within the same tenant.
3. **Branch-Aware Stock Transfer & Inventory Operations:**
   - Existing `StockTransfer` operations resolve source and destination warehouse branch attributions.
   - Cross-branch transfers are clearly distinguished from intra-branch transfers.
4. **Reversible Alembic Migration:**
   - Single revision: `023_add_branches_and_warehouse_link.py` (down_revision = `022_add_stock_transfers`).
   - Downgrade cleanly drops foreign keys and tables.
5. **Full Stack Integration:**
   - FastAPI endpoints under `/api/v1/branches`.
   - Frontend management view `BranchWarehouseView.tsx` with bilingual support and live API connectivity.
