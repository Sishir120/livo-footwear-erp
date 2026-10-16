# LIVO FOOTWEAR ERP — PHASE 6A: CHART OF ACCOUNTS (COA) SPECIFICATION

**Status:** ARCHITECTURAL SPECIFICATION & MASTER DATA CONTRACT  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Core Accounting Engine  
**Standard:** 4-Digit Hierarchical Decimal Classification (NFRS Compliant)  

---

## 1. Numbering Architecture & Classification Principles

The Chart of Accounts utilizes a standardized 4-digit code structure grouped into five statutory root classes:

| Code Range | Root Class | Normal Balance | Balance Sheet / P&L Section | Description |
| :--- | :--- | :---: | :--- | :--- |
| **1000 – 1999** | **ASSETS** | **DEBIT** | Statement of Financial Position | Current & Non-Current economic resources owned by company. |
| **2000 – 2999** | **LIABILITIES** | **CREDIT** | Statement of Financial Position | Current & Non-Current obligations to suppliers, workers, and IRD. |
| **3000 – 3999** | **EQUITY** | **CREDIT** | Statement of Financial Position | Share capital, statutory reserves, and accumulated retained earnings. |
| **4000 – 4999** | **REVENUE** | **CREDIT** | Statement of Profit or Loss | Invoiced footwear sales, franchise fees, scrap revenue, and discounts. |
| **5000 – 5999** | **COST OF GOODS SOLD (COGS)** | **DEBIT** | Statement of Profit or Loss | Direct materials, direct labor, and factory overhead absorbed into footwear. |
| **6000 – 6999** | **OPERATING EXPENSES** | **DEBIT** | Statement of Profit or Loss | Selling, administrative, logistical, depreciation, and financing expenses. |

---

## 2. Complete Footwear ERP Master Chart of Accounts

### 2.1 Class 1000: Assets

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1100** | **Cash & Cash Equivalents** | ASSET | - | Yes | - | DEBIT | Header for all liquid monetary accounts. |
| 1110 | Cash on Hand - Central Factory | ASSET | 1100 | Yes | CASH_DESK | DEBIT | Physical currency kept at Birgunj Factory vault. |
| 1120 | Cash on Hand - Kathmandu Showroom | ASSET | 1100 | Yes | CASH_DESK | DEBIT | Cash drawer currency at Kathmandu Retail Outlet. |
| 1130 | Petty Cash - Factory Imprest | ASSET | 1100 | No | - | DEBIT | Imprest fund for local factory sundries & teas. |
| 1150 | Operating Bank Account - Nabil Bank | ASSET | 1100 | Yes | BANK | DEBIT | Primary company current account for vendor payouts & collections. |
| 1160 | Payroll Bank Account - Global IME | ASSET | 1100 | Yes | BANK | DEBIT | Dedicated corporate account for worker electronic transfers. |
| 1170 | Digital Wallet & QR Clearing (eSewa / Fonepay) | ASSET | 1100 | Yes | PAYMENT_GATEWAY| DEBIT | Unsettled merchant QR collections from retail/wholesale customers. |
| **1200** | **Trade & Other Receivables** | ASSET | - | Yes | - | DEBIT | Header for trade debts and operational claims. |
| 1210 | Accounts Receivable - Wholesale Customers | ASSET | 1200 | **YES** | `receivable_entries` | DEBIT | **Control Account:** Reconciles to wholesale client subledger. Direct manual journal prohibited. |
| 1220 | Accounts Receivable - Franchise Partners | ASSET | 1200 | **YES** | `franchise_entries` | DEBIT | **Control Account:** Trade receivables due from independent franchise stores. |
| 1250 | Allowance for Doubtful Accounts | ASSET (Contra) | 1200 | No | - | CREDIT | Provision against delinquent/uncollectible customer receivables. |
| 1280 | Advances to Suppliers | ASSET | 1200 | Yes | `supplier_advances` | DEBIT | Upfront deposits paid to leather, sole, or chemical suppliers. |
| 1290 | Advances to Factory Workers | ASSET | 1200 | **YES** | `worker_advances` | DEBIT | **Control Account:** Reconciles to `worker_advances` table. |
| **1300** | **Inventories** | ASSET | - | Yes | - | DEBIT | Footwear manufacturing & retail stock holdings. |
| 1310 | Raw Materials - Leather & Upper Materials | ASSET | 1300 | **YES** | `raw_material_movements` | DEBIT | Value of raw leather, synthetics, and lining in storage. |
| 1320 | Raw Materials - Soles & Heels | ASSET | 1300 | **YES** | `raw_material_movements` | DEBIT | PU, TPR, EVA, and rubber soles stock valuation. |
| 1330 | Raw Materials - Consumables & Chemicals | ASSET | 1300 | **YES** | `raw_material_movements` | DEBIT | Adhesives, thread, buckles, eyelets, and packaging cartons. |
| 1340 | Work in Progress (WIP) - Production Floor | ASSET | 1300 | **YES** | `production_batches` | DEBIT | Costs absorbed in uncompleted batches (Cutting, Stitching, Assembly). |
| 1350 | Finished Goods - Central Warehouse (Factory) | ASSET | 1300 | **YES** | `stock_movements` | DEBIT | Boxed footwear pairs stored at Birgunj Central Warehouse. |
| 1360 | Finished Goods - Retail Showrooms | ASSET | 1300 | **YES** | `stock_movements` | DEBIT | Footwear pairs held at company-owned retail branches. |
| 1370 | Consignment Inventory - Franchise Stores | ASSET | 1300 | **YES** | `consignment_ledger` | DEBIT | Footwear physically held at franchise stores under consignment terms. |
| 1390 | Inventory In-Transit Clearing | ASSET | 1300 | **YES** | `stock_transfers` | DEBIT | Goods dispatched from factory but not yet acknowledged at branch. |
| **1400** | **Prepayments & Statutory Tax Assets** | ASSET | - | Yes | - | DEBIT | Tax input credits and prepaid rentals. |
| 1410 | Value Added Tax (VAT) Input Credit (13%) | ASSET | 1400 | **YES** | IRD Purchase Book | DEBIT | Recoverable VAT paid on raw material purchases & capital assets. |
| 1420 | Advance Income Tax / Withholding Tax Deducted | ASSET | 1400 | No | - | DEBIT | Tax deducted at source by corporate clients on payments. |
| 1430 | Prepaid Factory Rent | ASSET | 1400 | No | - | DEBIT | Advance lease paid for factory premises and showroom spaces. |
| **1500** | **Property, Plant & Equipment (Fixed Assets)** | ASSET | - | Yes | - | DEBIT | Capital assets tracked in `fixed_assets` register. |
| 1510 | Plant, Machinery & Footwear Equipment | ASSET | 1500 | **YES** | `fixed_assets` | DEBIT | Hydraulic cutting presses, stitching machines, sole injection moulds. |
| 1519 | Accumulated Depreciation - Machinery | ASSET (Contra) | 1500 | No | - | CREDIT | Cumulative depreciation charged against factory machinery. |
| 1520 | Shoe Lasts & Steel Dies / Moulds | ASSET | 1500 | **YES** | `fixed_assets` | DEBIT | Specialized footwear lasting moulds and clicking dies. |
| 1529 | Accumulated Depreciation - Moulds | ASSET (Contra) | 1500 | No | - | CREDIT | Cumulative depreciation charged against moulds & lasts. |
| 1530 | Commercial Motor Vehicles & Delivery Vans | ASSET | 1500 | **YES** | `fixed_assets` | DEBIT | Logistics trucks and vans used for inter-branch and retail transport. |
| 1539 | Accumulated Depreciation - Vehicles | ASSET (Contra) | 1500 | No | - | CREDIT | Cumulative depreciation charged against delivery vehicles. |
| 1540 | Office Furniture, Fixtures & Computers | ASSET | 1500 | **YES** | `fixed_assets` | DEBIT | IT workstations, showroom display racks, and factory furniture. |
| 1549 | Accumulated Depreciation - Furniture & IT | ASSET (Contra) | 1500 | No | - | CREDIT | Cumulative depreciation charged against furniture and IT. |

---

### 2.2 Class 2000: Liabilities

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **2100** | **Trade & Other Payables** | LIABILITY | - | Yes | - | CREDIT | Current obligations to vendors and suppliers. |
| 2110 | Accounts Payable - Material Suppliers | LIABILITY | 2100 | **YES** | `supplier_entries` | CREDIT | **Control Account:** Reconciles to vendor AP subledger. |
| 2120 | Landed Cost Clearing / Accrued Freight | LIABILITY | 2100 | Yes | `purchase_landed_costs`| CREDIT | Clearing account for customs duty, shipping, and cross-border freight. |
| 2130 | Customer Advances & Deposits | LIABILITY | 2100 | **YES** | `receivable_entries` | CREDIT | Advance payments collected from clients before invoice issuance. |
| 2140 | Franchise Security Deposits | LIABILITY | 2100 | Yes | `franchises` | CREDIT | Refundable security deposits collected from independent franchisees. |
| **2200** | **Payroll & Labor Liabilities** | LIABILITY | - | Yes | - | CREDIT | Unsettled compensation owed to factory and office staff. |
| 2210 | Wages & Salaries Payable | LIABILITY | 2200 | **YES** | `worker_monthly_records`| CREDIT | **Control Account:** Unpaid net payroll finalized in monthly records. |
| 2220 | Social Security Fund (SSF) Payable | LIABILITY | 2200 | No | - | CREDIT | Statutory employee & employer SSF contributions (31%). |
| 2230 | Factory Overtime & Piece-Rate Accrual | LIABILITY | 2200 | No | - | CREDIT | Unprocessed piece-work earnings earned during current pay cycle. |
| **2300** | **Statutory Tax & Government Liabilities** | LIABILITY | - | Yes | - | CREDIT | Taxes payable to Inland Revenue Department (IRD). |
| 2310 | Value Added Tax (VAT) Output Liability (13%) | LIABILITY | 2300 | **YES** | IRD Sales Book | CREDIT | Statutory 13% VAT billed to customers on taxable tax invoices. |
| 2320 | Withholding Tax / TDS Payable - Rent | LIABILITY | 2300 | No | - | CREDIT | TDS deducted on factory and showroom rent (10%). |
| 2330 | Withholding Tax / TDS Payable - Contracts & Transport | LIABILITY | 2300 | No | - | CREDIT | TDS deducted on freight, transport, and contractors (1.5% - 15%). |
| 2340 | Withholding Tax / TDS Payable - Employee Payroll | LIABILITY | 2300 | No | - | CREDIT | Income tax deducted from worker earnings under Income Tax §87. |
| 2350 | Corporate Income Tax Provision | LIABILITY | 2300 | No | - | CREDIT | Estimated annual company corporate tax payable under Income Tax Act. |
| **2400** | **Inter-Branch & Intercompany Clearing** | LIABILITY | - | Yes | - | CREDIT | Internal clearing balances between operating units. |
| 2410 | Inter-Branch Clearing - Factory vs Showrooms | LIABILITY | 2400 | Yes | `branch_clearing` | CREDIT/DEBIT | Clears internal transactions between factory and retail branches. |

---

### 2.3 Class 3000: Equity

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| 3100 | Authorized & Issued Share Capital | EQUITY | - | No | - | CREDIT | Par value of shares issued to company shareholders. |
| 3200 | Retained Earnings | EQUITY | - | No | - | CREDIT | Cumulative prior-year profits retained in the business. |
| 3300 | Current Year Profit / (Loss) Summary | EQUITY | - | Yes | - | CREDIT | Clearing account for year-end profit closing entries. |

---

### 2.4 Class 4000: Revenue

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **4100** | **Footwear Sales Revenue** | REVENUE | - | Yes | - | CREDIT | Core turnover from footwear trading. |
| 4110 | Footwear Sales - Wholesale (Factory Direct) | REVENUE | 4100 | **YES** | `invoices` | CREDIT | Invoiced sales to wholesale shoe distributors. |
| 4120 | Footwear Sales - Retail Showrooms | REVENUE | 4100 | **YES** | `invoices` | CREDIT | Retail over-the-counter shoe sales at company showrooms. |
| 4130 | Footwear Sales - Franchise Outright Billing | REVENUE | 4100 | **YES** | `invoices` | CREDIT | Wholesale billing to independent franchise partners. |
| 4140 | Footwear Sales - Franchise Consignment Commission | REVENUE | 4100 | Yes | `franchise_settlements`| CREDIT | Commission earned from sales through consignment franchise stores. |
| 4190 | Sales Discounts & Volume Rebates | REVENUE (Contra) | 4100 | No | - | DEBIT | Cash discounts and seasonal trade rebates granted to buyers. |
| **4200** | **Other Operating & Franchise Income** | REVENUE | - | No | - | CREDIT | Secondary revenue streams. |
| 4210 | Franchise Onboarding & Royalty Fees | REVENUE | 4200 | Yes | `franchises` | CREDIT | Fixed annual franchise royalties and initial store setup fees. |
| 4220 | Sale of Factory Scrap & Leather Offcuts | REVENUE | 4200 | Yes | `waste_records` | CREDIT | Proceeds from selling leather remnants, scrap rubber, and used barrels. |

---

### 2.5 Class 5000: Cost of Goods Sold (COGS)

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **5100** | **Direct Materials Consumed** | COGS | - | Yes | - | DEBIT | Raw material costs absorbed into completed production. |
| 5110 | Direct Material - Leather & Uppers | COGS | 5100 | **YES** | `production_batches` | DEBIT | Cost of leather issued to production batches. |
| 5120 | Direct Material - Soles & Bottoms | COGS | 5100 | **YES** | `production_batches` | DEBIT | Cost of soles and heels consumed in assembly. |
| 5130 | Direct Material - Adhesives, Thread & Hardware | COGS | 5100 | **YES** | `production_batches` | DEBIT | Cements, glues, eyelets, buckles, and laces consumed. |
| 5140 | Packaging Materials - Shoe Boxes & Cartons | COGS | 5100 | **YES** | `production_batches` | DEBIT | Inner branded shoe boxes and master shipping cartons. |
| **5200** | **Direct Labor** | COGS | - | Yes | - | DEBIT | Direct shop-floor production wages. |
| 5210 | Direct Factory Wages - Cutting Section | COGS | 5200 | Yes | `worker_monthly_records`| DEBIT | Wages paid to leather and lining clicker operators. |
| 5220 | Direct Factory Wages - Stitching / Upper Making | COGS | 5200 | Yes | `worker_monthly_records`| DEBIT | Wages paid to sewing and closing floor workers. |
| 5230 | Direct Factory Wages - Lasting & Assembly | COGS | 5200 | Yes | `worker_monthly_records`| DEBIT | Wages paid to shoe lasting, sole bonding, and finishing teams. |
| 5240 | Direct Piece-Rate Production Pay | COGS | 5200 | Yes | `worker_monthly_records`| DEBIT | Piece-work incentives directly assigned to completed pairs. |
| **5300** | **Factory Overhead (Manufacturing Overhead)** | COGS | - | Yes | - | DEBIT | Indirect production expenses absorbed into shoes. |
| 5310 | Factory Power, Generator Diesel & Electricity | COGS | 5300 | Yes | `factory_expenses` | DEBIT | Utility costs powering heavy cutting and moulding machinery. |
| 5320 | Factory Machinery Maintenance & Spare Parts | COGS | 5300 | Yes | `factory_expenses` | DEBIT | Needles, cutting boards, hydraulic oil, motor repairs. |
| 5330 | Factory Building Rent | COGS | 5300 | Yes | `factory_expenses` | DEBIT | Factory premises lease at Birgunj industrial area. |
| 5340 | Depreciation of Production Machinery & Moulds | COGS | 5300 | Yes | `fixed_assets` | DEBIT | Depreciation portion allocated directly to manufacturing. |
| 5390 | Inventory Shrinkage, Scrap & Floor Rejects | COGS | 5300 | Yes | `waste_records` | DEBIT | Unusable rejects and scrap exceeding standard BOM tolerances. |
| **5400** | **Cost of Goods Sold - Finished Shoes** | COGS | - | **YES** | `stock_movements` | DEBIT | Cost of finished pairs recognized upon customer invoice dispatch. |

---

### 2.6 Class 6000: Operating Expenses

| Account Code | Account Name | Account Type | Parent Account | Is Control Account? | Subledger Link | Normal Balance | Operational Description |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **6100** | **Selling & Distribution Expenses** | EXPENSE | - | Yes | - | DEBIT | Costs incurred delivering and promoting footwear. |
| 6110 | Outward Freight, Delivery & Cargo Costs | EXPENSE | 6100 | Yes | `sales_expenses` | DEBIT | Transport charges delivering shoes to dealers and branches. |
| 6120 | Sales Commissions | EXPENSE | 6100 | Yes | `sales_expenses` | DEBIT | Incentive commissions paid to external sales agents. |
| 6130 | Advertising, Marketing & Brand Promotion | EXPENSE | 6100 | No | - | DEBIT | Social media, hoardings, print ads, and trade exhibitions. |
| 6140 | Promotional Free Samples & Marketing Pairs | EXPENSE | 6100 | Yes | `stock_movements` | DEBIT | Footwear pairs distributed free to retail dealers for display. |
| 6150 | Loading, Unloading & Porterage Charges | EXPENSE | 6100 | Yes | `sales_expenses` | DEBIT | Labor charges for vehicle loading and unloading. |
| **6200** | **Showroom & Retail Branch Operating Expenses** | EXPENSE | - | Yes | - | DEBIT | Operating overheads of company-owned retail branches. |
| 6210 | Retail Showroom Rent - Kathmandu | EXPENSE | 6200 | Yes | `branches` | DEBIT | Lease of Kathmandu retail premises. |
| 6220 | Retail Showroom Electricity & Internet | EXPENSE | 6200 | Yes | `branches` | DEBIT | Utility bills for retail store operations. |
| 6230 | Retail Sales Staff Salaries | EXPENSE | 6200 | Yes | `worker_monthly_records`| DEBIT | Compensation for retail counter and sales assistants. |
| **6300** | **Administrative & General Expenses** | EXPENSE | - | Yes | - | DEBIT | Back-office management expenses. |
| 6310 | Administrative & Executive Salaries | EXPENSE | 6300 | Yes | `worker_monthly_records`| DEBIT | Management, accounting, and clerical staff payroll. |
| 6320 | Office Supplies, Printing & Software Subscriptions | EXPENSE | 6300 | Yes | `factory_expenses` | DEBIT | ERP hosting, accounting stationary, office printer toner. |
| 6330 | Legal, Audit & Professional Consulting Fees | EXPENSE | 6300 | No | - | DEBIT | Chartered Accountant audit fees and legal retainers. |
| 6340 | Staff Refreshments, Tea & Hospitality | EXPENSE | 6300 | Yes | `factory_expenses` | DEBIT | Daily tea, drinking water, and visitor hospitality. |
| 6350 | Depreciation - Office & Showroom Fixtures | EXPENSE | 6300 | Yes | `fixed_assets` | DEBIT | Depreciation of retail display counters and office computers. |
| **6400** | **Financial & Other Expenses** | EXPENSE | - | Yes | - | DEBIT | Bank charges and credit losses. |
| 6410 | Bank Service Charges, Cheque Clearance & QR Fees | EXPENSE | 6400 | No | - | DEBIT | Transaction commissions charged by banks and Fonepay. |
| 6420 | Bad Debts Expense / Receivables Written Off | EXPENSE | 6400 | Yes | `receivable_entries` | DEBIT | Authorized write-off of uncollectible customer balances. |

---

## 3. Control Account Enforcement & Posting Rules

1. **Strict Control Account Guard:**
   - Any account marked `is_control_account = True` (e.g., `1210 Accounts Receivable`, `2110 Accounts Payable`, `1310-1360 Inventories`, `2210 Wages Payable`, `2310 VAT Output`) **strictly rejects manual journal entry lines**.
   - Posting to these accounts is only permitted through certified posting handlers tied to authoritative business documents (Invoices, GRNs, Payroll Runs, Stock Transfers).
2. **Account Deactivation Invariant:**
   - An account cannot be deactivated (`is_active = False`) if its net balance is non-zero ($\text{Balance} \neq 0$).
   - An account cannot be deleted if any historical `journal_lines` reference its `id`.
