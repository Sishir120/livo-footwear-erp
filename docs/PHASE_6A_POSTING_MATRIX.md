# LIVO FOOTWEAR ERP — PHASE 6A: FINANCIAL POSTING MATRIX SPECIFICATION

**Status:** ARCHITECTURAL SPECIFICATION & TRANSACTION POSTING ENGINE CONTRACT  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Double-Entry Posting Engine  
**Currency Standard:** Nepalese Rupee (NPR) in exact integer paisa ($1 \text{ NPR} = 100 \text{ paisa}$)  

---

## 1. Posting Matrix Architecture & Conventions

### 1.1 Physical Movement vs. Financial Recognition Principle
A core invariant of the LIVO ERP architecture: **Operational document creation does not equate to financial recognition.**
- A **Purchase Order (PO)** or **Sales Order (SO)** is a commercial intent memo. It creates zero journal entries.
- A **Delivery Challan** or **Internal Stock Transfer** moves physical goods between warehouses. It creates inventory quantity updates in `stock_movements`, but only triggers financial entries if ownership or valuation boundaries are crossed (e.g., in-transit clearing or sale to franchisee).
- A **Goods Receipt Note (GRN)** or **Finalized Tax Invoice** represents legal title passage and creates balanced double-entry postings.

---

## 2. Comprehensive Financial Posting Matrix

| # | Business Workflow & Event | Trigger Document / Status | Posting Timing | Debit Account | Credit Account | Amount Basis (Paisa) | Reversal / Correction Behavior | Source References Required |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Purchase Order Issuance** | `Purchase` created (`ORDERED`) | Pre-delivery | *NO FINANCIAL POSTING* | *NO FINANCIAL POSTING* | NPR 0 (Commitment memo only) | N/A | `PO-YYYY-XXXXX` |
| **2** | **Raw Material Goods Receipt (GRN)** | `Purchase` status $\to$ `RECEIVED` (GRN generated) | Physical receipt at factory warehouse | **1310/1320/1330** Raw Materials Inventory | **2110** Accounts Payable - Material Suppliers | $\text{base\_cost\_paisa} = \text{qty} \times \text{unit\_price} \times 100$ | Generate paired reversal journal if GRN cancelled before bill booking | `PO-REF`, `GRN-NUMBER`, `supplier_id` |
| **3** | **Landed Cost Allocation (Duty, Freight, Insurance)** | Landed cost voucher finalized on Purchase | Upon receipt of carrier & customs bills | **1310/1320/1330** Raw Materials Inventory | **2120** Landed Cost Clearing / Accrued Freight | $\text{carrying} + \text{duty} + \text{china\_carrying} + \text{insurance}$ | Reversal entry if landed cost dispute is verified | `GRN-NUMBER`, `CARRIER-BILL-NO`, `CUSTOMS-DECL-NO` |
| **4** | **Landed Cost Settlement (Carrier / Customs Paid)** | Cash / Bank Payment to Carrier / Customs | Payment release | **2120** Landed Cost Clearing / Accrued Freight | **1110/1150** Cash on Hand / Nabil Bank | Actual freight / customs invoice amount in paisa | Standard reversal entry | `PAYMENT-REF`, `VOUCHER-NO` |
| **5** | **Supplier Advance Payment** | Advance voucher created | Prior to material dispatch by supplier | **1280** Advances to Suppliers | **1150** Operating Bank Account (Nabil) | Actual advance transfer amount in paisa | Advance refund receipt reverses entry | `CHQ-NO`, `BANK-TXN-ID`, `supplier_id` |
| **6** | **Supplier Invoice Settlement (AP Clearing)** | Supplier payment voucher finalized | Upon bill due date or discount window | **2110** Accounts Payable - Material Suppliers | **1150** Operating Bank Account / **1280** Advances to Suppliers | Invoiced payable settlement amount | Reversal entry if cheque bounces or is recalled | `PAYMENT-VOUCHER`, `INV-REF`, `supplier_id` |
| **7** | **Purchase Return to Supplier (Debit Note)** | Debit Note finalized | Defective materials rejected and returned | **2110** Accounts Payable - Material Suppliers | **1310/1320/1330** Raw Materials Inventory | Returned quantity $\times$ effective landed cost per unit | Debit note cancellation creates mirror entry | `DEBIT-NOTE-NO`, `GRN-REF`, `ORIGINAL-PO` |
| **8** | **Raw Material Issue to Production Floor** | `ProductionBatch` started (BOM issue) | Shop-floor requisition | **1340** Work in Progress (WIP) | **1310/1320/1330** Raw Materials Inventory | BOM quantity $\times$ standard/weighted unit cost in paisa | Unused materials returned to store: Dr. RM, Cr. WIP | `BATCH-ID`, `BOM-VERSION`, `voucher_no` |
| **9** | **Production Completion (Finished Footwear)** | `ProductionBatch` status $\to$ `COMPLETED` | Batch inspection passed, pairs boxed | **1350** Finished Goods - Central Warehouse | **1340** Work in Progress (WIP) | Total accumulated batch cost (materials + absorbed labor) | Batch un-completion: Dr. WIP, Cr. Finished Goods | `BATCH-ID`, `QC-REPORT-NO`, `product_id` |
| **10** | **Finished Goods Dispatch & COGS Recognition** | `SalesOrder` status $\to$ `DISPATCHED` | Physical exit from warehouse | **5400** Cost of Goods Sold - Finished Shoes | **1350/1360** Finished Goods (Factory / Retail) | Shipped pairs $\times$ unit manufacturing cost in paisa | Sales return: Dr. Finished Goods, Cr. COGS | `SO-NUMBER`, `DELIVERY-CHALLAN-NO` |
| **11** | **Wholesale Sales Invoice Issuance** | `Invoice` finalized (`is_void = False`) | Statutory tax invoice issued to client | **1210** Accounts Receivable (`total`) | **4110** Wholesale Sales Revenue (`taxable`)<br>**2310** VAT Output Liability (`vat`) | `total_amount_paisa` = `taxable_paisa` + `vat_paisa` (where $\text{vat} = 13\%$) | Voiding invoice generates paired reversing journal | `INV-2083-XXXXX`, `SO-NUMBER`, `client_id` |
| **12** | **Customer Payment Receipt (Cash / Bank / QR)** | `Payment` created / `ReceivableEntry` (`PAYMENT`) | Funds collected and verified | **1110** Cash on Hand / **1150** Nabil Bank / **1170** QR Clearing | **1210** Accounts Receivable - Wholesale | Exact collected amount in paisa | Receipt dishonor creates reversal journal | `RECEIPT-NO`, `BANK-SLIP-REF`, `client_id` |
| **13** | **Customer Advance Collection** | Unallocated customer receipt | Prior to order placement or delivery | **1110/1150** Cash on Hand / Nabil Bank | **2130** Customer Advances & Deposits | Received deposit amount in paisa | Advance refund: Dr. Customer Advances, Cr. Bank | `DEPOSIT-RECEIPT`, `client_id` |
| **14** | **Customer Advance Applied to Invoice** | Invoice finalized against existing advance | At invoice generation | **2130** Customer Advances & Deposits | **1210** Accounts Receivable - Wholesale | Allocated advance amount in paisa | Reversal entry if invoice is voided | `ALLOCATION-ID`, `INV-REF`, `client_id` |
| **15** | **Sales Return & Statutory Credit Note** | Credit Note finalized (अनुसूची-१०) | Returned pairs received and inspected | **4110** Wholesale Sales Revenue (`taxable`)<br>**2310** VAT Output Liability (`vat`) | **1210** Accounts Receivable (`total`) | Returned invoice taxable value + 13% VAT in paisa | Credit note cancellation generates mirror entry | `CN-2083-XXXXX`, `ORIG-INV-REF`, `client_id` |
| **16** | **Sales Return Restocking (Inventory Adjustment)** | Return inspection passed | Shoes returned to sellable stock | **1350/1360** Finished Goods Inventory | **5400** Cost of Goods Sold - Finished Shoes | Returned pairs $\times$ original unit cost in paisa | Reversal if returned pairs are found damaged and scrapped | `CN-REF`, `STOCK-INSPECTION-NO` |
| **17** | **Operating Expense Payment (Cash / Bank)** | `FactoryExpense` / `SalesExpense` created | Immediate cash disbursement | **5310-5330 / 6110-6340** Specific Expense GL | **1110** Cash on Hand / **1150** Nabil Bank | Incurred expense amount in integer paisa | Expense voucher cancellation reverses entry | `EXP-VOUCHER-NO`, `RECEIPT-REF`, `branch_id` |
| **18** | **Payroll Monthly Run Finalization** | `WorkerMonthlyRecord` finalized | Monthly payroll approval | **5210-5240** Direct Factory Wages<br>**6230** Retail Salaries<br>**6310** Admin Salaries | **2210** Wages & Salaries Payable (`net`)<br>**1290** Advances to Workers (`deduction`)<br>**2340** TDS Payable - Payroll | `gross_pay_paisa` = `net_paid_paisa` + `advance_deduction_paisa` + `tds_paisa` | Payroll recalculation voids and replaces journal | `PAYROLL-MONTH-YEAR`, `worker_id` |
| **19** | **Payroll Disbursement (Bank / Cash Payout)** | Worker salary payment executed | Payout date | **2210** Wages & Salaries Payable | **1160** Payroll Bank (Global IME) / **1110** Cash | Net disbursed amount in paisa | Stale cheque or failed transfer reverses entry | `BANK-TRANSFER-BATCH-ID`, `PAYROLL-REF` |
| **20** | **Worker Advance Issuance** | `WorkerAdvance` status `ISSUED` | Advance disbursed to worker | **1290** Advances to Factory Workers | **1110/1150** Cash on Hand / Bank | Disbursed advance amount in integer paisa | Immediate cancellation reverses entry | `ADVANCE-VOUCHER-ID`, `worker_id` |
| **21** | **Fixed Asset Acquisition (Machinery / Moulds)** | Fixed Asset record finalized | Equipment delivered and commissioned | **1510/1520/1540** Fixed Asset Cost Account | **2110** Accounts Payable / **1150** Bank | Purchase cost + installation + import duties in paisa | Asset invoice dispute reverses entry | `ASSET-CODE`, `VENDOR-INV-NO` |
| **22** | **Monthly Fixed Asset Depreciation** | Monthly depreciation schedule run | End of fiscal month | **5340** Depreciation - Factory Machinery<br>**6350** Depreciation - Office / Showrooms | **1519/1529/1549** Accumulated Depreciation Contra Accounts | Monthly straight-line or diminishing depreciation in paisa | Schedule recalculation reverses and reposts | `DEPR-SCHEDULE-YYYY-MM` |
| **23** | **Fixed Asset Disposal (Sale / Retirement)** | Asset retired or sold | Bill of sale finalized | **1150** Bank Account (`sale_price`)<br>**1519** Accum. Depreciation (`cumulative`)<br>**6400** Loss on Disposal (if loss) | **1510** Fixed Asset Cost (`historical`)<br>**4200** Gain on Disposal (if gain) | Historical cost, accumulated depreciation, net proceeds | Disposal cancellation reverses entry | `ASSET-CODE`, `DISPOSAL-VOUCHER-NO` |
| **24** | **Floor Scrap & Waste Disposal (Resold)** | `WasteRecord` sold for cash | Scrap sale transaction | **1110** Cash on Hand | **4220** Sale of Factory Scrap & Offcuts | Cash proceeds collected in paisa | Scrap receipt cancellation reverses entry | `WASTE-RECORD-ID`, `SCRAP-INVOICE-NO` |
| **25** | **Inventory Shrinkage / Damage Write-Off** | Physical stock audit adjustment approved | Post-cycle count reconciliation | **5390** Inventory Shrinkage & Floor Rejects | **1310/1320/1350** Raw Material / Finished Goods | Damaged / missing units $\times$ unit cost in paisa | Audit recalculation reverses entry | `AUDIT-ADJUSTMENT-VOUCHER`, `wh_id` |
| **26** | **Inter-Branch Stock Transfer (Factory to Showroom)**| `StockTransfer` status `IN_TRANSIT` | Dispatched from factory warehouse | **1390** Inventory In-Transit Clearing | **1350** Finished Goods - Central Warehouse | Transferred pairs $\times$ standard manufacturing cost | Cancellation at factory reverses entry | `TRF-NUMBER`, `source_wh`, `dest_wh` |
| **27** | **Inter-Branch Stock Receipt at Destination** | `StockTransfer` status `RECEIVED` | Acknowledged at destination showroom | **1360** Finished Goods - Retail Showroom | **1390** Inventory In-Transit Clearing | Received pairs $\times$ standard manufacturing cost | Transit discrepancy write-off clears remainder | `TRF-NUMBER`, `RECEIPT-VOUCHER` |
| **28** | **Inter-Branch Transit Loss / Shortage** | Discrepancy resolved on Stock Transfer | Receiving inspection short | **5390** Inventory Shrinkage (or Transporter Claim) | **1390** Inventory In-Transit Clearing | Missing pairs $\times$ standard manufacturing cost | Found stock reverses shortage write-off | `TRF-NUMBER`, `DISCREPANCY-CLAIM-NO` |
| **29** | **Independent Franchise Outright Sale** | Franchise Tax Invoice issued | Goods dispatched to franchise store | **1220** Accounts Receivable - Franchise Partners | **4130** Footwear Sales - Franchise Outright<br>**2310** VAT Output Liability (13%) | Wholesale price + 13% statutory VAT in paisa | Credit note reverses entry | `INV-2083-FRAN-XXXXX`, `franchise_id` |
| **30** | **Independent Franchise Consignment Transfer** | Consignment Challan issued | Dispatched to franchise custody | **1370** Consignment Inventory - Franchise Stores | **1350** Finished Goods - Central Warehouse | Transferred pairs $\times$ manufacturing cost in paisa | Goods returned from franchise reverses entry | `CNG-CHALLAN-NO`, `franchise_id` |
| **31** | **Franchise Consignment Sales Settlement** | Monthly sales report certified | Franchise reports retail sales | **1220** Accounts Receivable - Franchise Partners<br>**5400** COGS - Finished Shoes | **4140** Franchise Consignment Sales Revenue<br>**2310** VAT Output Liability (13%)<br>**1370** Consignment Inventory | Wholesale value billed, retail commission retained, stock derecognized | Settlement dispute reverses entry | `FRAN-SETTLEMENT-NO`, `PERIOD-REF` |
| **32** | **Franchise Royalty & Fixed Fee Billing** | Annual / monthly franchise fee invoice | Contract anniversary date | **1220** Accounts Receivable - Franchise Partners | **4210** Franchise Onboarding & Royalty Fees<br>**2310** VAT Output Liability (13%) | Agreed fee amount + 13% statutory VAT | Invoice voiding reverses entry | `FEE-INV-NO`, `franchise_id` |
| **33** | **Internal Bank Transfer (Operating to Payroll)** | Bank transfer executed | Electronic bank confirmation | **1160** Payroll Bank (Global IME) | **1150** Operating Bank (Nabil) | Exact transfer amount in paisa | Transfer rejection reverses entry | `BANK-REF-TXN-ID`, `TRANSFER-SLIP` |
| **34** | **Bad Debt Write-Off** | Formal write-off approved by CFO | Debtor legally uncollectible | **1250** Allowance for Doubtful Accounts (or **6420**) | **1210** Accounts Receivable - Wholesale | Uncollectible balance in paisa | Recovery of written-off debt creates recovery entry | `WRITEOFF-BOARD-APPROVAL-NO`, `client_id` |

---

## 3. Worked Mathematical Posting Examples (in Integer Paisa)

### Example 1: Wholesale Footwear Sale with 13% Nepal VAT
- **Scenario:** Client buys 100 pairs of "Classic Boot 41" at NPR 1,200.00/pair. Manufacturing cost is NPR 750.00/pair.
- **Amounts:**
  - Taxable Subtotal = $100 \times 1,200 = \text{NPR } 120,000.00 = 12,000,000 \text{ paisa}$.
  - VAT (13%) = $120,000 \times 0.13 = \text{NPR } 15,600.00 = 1,560,000 \text{ paisa}$.
  - Total Invoice Amount = $\text{NPR } 135,600.00 = 13,560,000 \text{ paisa}$.
  - COGS Value = $100 \times 750 = \text{NPR } 75,000.00 = 7,500,000 \text{ paisa}$.

**Entry A: Commercial Invoicing (Date of Finalization)**
```
DR  1210 Accounts Receivable - Wholesale               13,560,000 paisa
    CR  4110 Footwear Sales - Wholesale                               12,000,000 paisa
    CR  2310 Value Added Tax (VAT) Output Liability                    1,560,000 paisa
[Balance Verification: DR 13,560,000 == CR 13,560,000. Delta = 0 paisa]
```

**Entry B: Inventory & COGS Recognition (Date of Dispatch)**
```
DR  5400 Cost of Goods Sold - Finished Shoes            7,500,000 paisa
    CR  1350 Finished Goods - Central Warehouse                        7,500,000 paisa
[Balance Verification: DR 7,500,000 == CR 7,500,000. Delta = 0 paisa]
```

---

### Example 2: Worker Monthly Payroll Finalization with Advance Deduction
- **Scenario:** Worker has Gross Pay of NPR 28,000.00. Salary advance recovery is NPR 5,000.00. TDS is NPR 280.00 (1%). Net payable is NPR 22,720.00.
- **Amounts in Paisa:**
  - Gross Pay = $2,800,000 \text{ paisa}$.
  - Advance Deduction = $500,000 \text{ paisa}$.
  - TDS Payable = $28,000 \text{ paisa}$.
  - Net Wages Payable = $2,272,000 \text{ paisa}$.

**Journal Entry:**
```
DR  5220 Direct Factory Wages - Stitching Section       2,800,000 paisa
    CR  2210 Wages & Salaries Payable                                  2,272,000 paisa
    CR  1290 Advances to Factory Workers                                 500,000 paisa
    CR  2340 Withholding Tax / TDS Payable - Employee Payroll             28,000 paisa
[Balance Verification: DR 2,800,000 == CR (2,272,000 + 500,000 + 28,000) = 2,800,000 paisa. Delta = 0]
```
