# LIVO FOOTWEAR ERP — PHASE 6A.1: TRACEABILITY MATRIX

**Status:** VALIDATION GATE AUDIT  
**Phase:** 6A.1 (Specification-Only)  
**Audit Date:** 2026-10-15  

This matrix cross-references every posting event to its operational source, accounts, amount basis, idempotency key components, reversal procedure, reconciliation invariant, and required authorization.

**Notation:**  
- `✓` = fully specified and internally consistent  
- `⚠` = present but has a VAL-xx issue; see DESIGN_VALIDATION.md  
- `✗` = missing or unresolvable without external decision  

---

## Event-Level Traceability Table

| Event # | Business Event | Source Document & Status Trigger | Debit Acct | Credit Acct | Amount Basis | Idempotency Key Components | Reversal Procedure | Reconciliation Invariant | Authorization | Consistency |
|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|:--|
| 1 | PO Issuance | `Purchase (ORDERED)` | None | None | NPR 0 | N/A | N/A | None | Any | ✓ |
| 2 | GRN Material Receipt | `Purchase → RECEIVED` + GRN generated | 1310/1320/1330 | 2110 | qty × unit_price_paisa | `company_id + PURCHASE_GRN + grn_number + GRN_INVENTORY_RECEIPT` | Paired reversal journal on GRN cancellation | Invariant 2 (GL 2110 = AP Subledger) | ACCOUNTANT or system | ✓ |
| 3 | Landed Cost Allocation | Landed cost voucher finalized on Purchase | 1310/1320/1330 | 2120 | sum of carrying+duty+china+insurance paisa | `company_id + PURCHASE_GRN + purchase_id + GRN_LANDED_COST` | Reversal entry on dispute resolution | Invariant 3 (GL Inventory = Stock valuation) | ACCOUNTANT | ✓ |
| 4 | Landed Cost Settlement | Cash/Bank payment to carrier/customs | 2120 | 1110/1150 | Actual payment amount | `company_id + SUPPLIER_PAYMENT + payment_voucher_no + LANDED_COST_SETTLE` | Standard reversal | Invariant 4 (GL Bank = Bank Statement) | ACCOUNTANT | ✓ |
| 5 | Supplier Advance Payment | Advance voucher created | 1280 | 1150 | Advance transfer amount | `company_id + SUPPLIER_PAYMENT + advance_voucher_id + ADVANCE_ISSUED` | Reversal on advance refund | Invariant 2 (AP subledger) | ACCOUNTANT | ✓ |
| 6 | AP Clearing (Supplier Payment) | Supplier payment voucher finalized | 2110 | 1150/1280 | Settlement amount | `company_id + SUPPLIER_PAYMENT + payment_ref + AP_CLEARING` | Reversal on dishonored cheque | Invariant 2 | ACCOUNTANT | ✓ |
| 7 | Purchase Return / Debit Note | Debit Note finalized | 2110 | 1310/1320/1330 | qty × effective landed cost per unit | `company_id + PURCHASE_GRN + debit_note_no + PURCHASE_RETURN` | Mirror entry on DN cancellation | Invariant 2 + 3 | ACCOUNTANT | ✓ |
| 8 | Raw Material Issue to WIP | `ProductionBatch` started (BOM issue) | 1340 | 1310/1320/1330 | BOM qty × weighted unit cost paisa | `company_id + STOCK_ADJUSTMENT + batch_id + BOM_ISSUE` | Return unused materials: Dr RM, Cr WIP | Invariant 3 | INVENTORY_MANAGER | ⚠ VAL-02: unit cost not in model |
| 9 | Production Completion | `ProductionBatch → COMPLETED` | 1350 | 1340 | Total accumulated batch cost paisa | `company_id + STOCK_ADJUSTMENT + batch_id + BATCH_COMPLETE` | Batch un-complete: Dr WIP, Cr FG | Invariant 3 | INVENTORY_MANAGER | ⚠ VAL-02: batch_total_cost_paisa missing |
| 10 | Finished Goods COGS on Dispatch | `SalesOrder → DISPATCHED` | 5400 | 1350/1360 | shipped_pairs × unit_manufacturing_cost_paisa | `company_id + SALES_INVOICE + so_number + INVOICE_COGS_DISPATCH` | Sales return: Dr FG, Cr COGS | Invariant 3 | BILLING_OPERATOR (system) | ⚠ VAL-03: timing vs Event 11 |
| 11 | Sales Invoice AR + Revenue + VAT | `Invoice.finalized (is_void=False)` | 1210 (total) | 4110 (taxable), 2310 (vat) | total_amount_paisa = taxable + round(taxable×0.13) | `company_id + SALES_INVOICE + invoice_id + INVOICE_AR_REVENUE_VAT` | Paired reversal on invoice void | Invariant 1 (GL 1210 = AR subledger) | BILLING_OPERATOR (system) | ⚠ VAL-03: decoupled from Event 10 |
| 12 | Customer Payment Receipt | `Payment` created / `ReceivableEntry(PAYMENT)` | 1110/1150/1170 | 1210 | Exact collected amount | `company_id + PAYMENT_RECEIPT + receipt_no + PAYMENT_RECEIPT` | Reversal on dishonor | Invariant 1 | BILLING_OPERATOR | ✓ |
| 13 | Customer Advance Collection | Unallocated receipt before order | 1110/1150 | 2130 | Received deposit | `company_id + PAYMENT_RECEIPT + deposit_receipt_no + ADVANCE_DEPOSIT` | Refund: Dr 2130, Cr Bank | Invariant 1 (pending: 2130 not reconciled to AR subledger) | BILLING_OPERATOR | ✓ |
| 14 | Advance Applied to Invoice | Invoice finalized with existing advance | 2130 | 1210 | Allocated advance | `company_id + SALES_INVOICE + invoice_id + ADVANCE_APPLIED` | Reversal on invoice void | Invariant 1 | BILLING_OPERATOR (system) | ✓ |
| 15 | Sales Return Credit Note (Annex-10) | Credit Note finalized | 4110 (taxable), 2310 (vat) | 1210 (total) | Returned invoice value + 13% VAT | `company_id + CREDIT_NOTE + credit_note_id + CREDIT_NOTE_REVERSAL` | Mirror on CN cancellation | Invariant 1 | ACCOUNTANT | ✓ |
| 16 | Return Restocking (Inventory) | Credit Note + inspection pass | 1350/1360 | 5400 | returned_pairs × original unit cost | `company_id + CREDIT_NOTE + credit_note_id + CREDIT_NOTE_RESTOCK` | Reversal if pairs are damaged | Invariant 3 | INVENTORY_MANAGER | ✓ |
| 17 | Operating Expense Payment | `FactoryExpense` / `SalesExpense` created | 5310–5330 / 6110–6340 | 1110/1150 | Expense amount | `company_id + MANUAL_JOURNAL + expense_id + EXPENSE_PAYMENT` | Voucher cancellation reversal | Invariant 4 (Bank) | BRANCH_MANAGER (within limit) | ✓ |
| 18 | Payroll Accrual (Monthly Finalization) | `WorkerMonthlyRecord` finalized | 5210–5240, 6230, 6310 | 2210 (net), 1290 (advance), 2340 (TDS) | gross = net + advance_deduction + tds | `company_id + PAYROLL_RUN + worker_id + month_year + PAYROLL_ACCRUAL` | Void+replace on recalculation | Invariant 5 (GL 2210 = Payroll subledger) | CHIEF_ACCOUNTANT | ⚠ VAL-04: TDS slab narrative |
| 19 | Payroll Disbursement | Worker salary payment executed | 2210 | 1160/1110 | Net disbursed amount | `company_id + PAYROLL_RUN + worker_id + month_year + PAYROLL_DISBURSEMENT` | Reversal on failed transfer | Invariant 5 | CHIEF_ACCOUNTANT | ✓ |
| 20 | Worker Advance Issuance | `WorkerAdvance (ISSUED)` | 1290 | 1110/1150 | Advance amount | `company_id + PAYMENT_RECEIPT + advance_id + ADVANCE_ISSUED` | Cancellation reversal | None (1290 reconciles via payroll deduction) | ACCOUNTANT | ✓ |
| 21 | Fixed Asset Acquisition | FixedAsset record finalized | 1510/1520/1540 | 2110/1150 | Purchase cost + installation | `company_id + PURCHASE_GRN + asset_code + ASSET_ACQUISITION` | Reversal on vendor dispute | Invariant 6 (GL Assets = Fixed Asset register) | CHIEF_ACCOUNTANT | ✓ |
| 22 | Monthly Depreciation | Depreciation schedule run | 5340, 6350 | 1519/1529/1549 | Monthly SLM or WDV computation | `company_id + MANUAL_JOURNAL + asset_id + period_year_month + ASSET_DEPRECIATION` | Schedule recalculation reverses+reposts | Invariant 6 | CHIEF_ACCOUNTANT | ✓ |
| 23 | Fixed Asset Disposal | Asset retired or sold | 1150 (proceeds), 1519 (accum depr), 6430* (loss) | 1510 (cost), 4200 (gain) | Proceeds, historical cost, accumulated depreciation | `company_id + MANUAL_JOURNAL + asset_code + ASSET_DISPOSAL` | Disposal cancellation reversal | Invariant 6 | CHIEF_ACCOUNTANT | ⚠ VAL-09: posts to 6400 parent |
| 24 | Scrap Sale Revenue | `WasteRecord` sold for cash | 1110 | 4220 | Cash proceeds | `company_id + MANUAL_JOURNAL + waste_record_id + SCRAP_SALE` | Receipt reversal | None | ACCOUNTANT | ✓ |
| 25 | Inventory Write-Off | Stock audit adjustment approved | 5390 | 1310/1320/1350 | damaged_units × unit cost | `company_id + STOCK_ADJUSTMENT + audit_voucher_no + INVENTORY_WRITEOFF` | Reversal if found stock | Invariant 3 | CHIEF_ACCOUNTANT | ✓ |
| 26 | Transfer Dispatch (In-Transit Out) | `StockTransfer → IN_TRANSIT` | 1390 | 1350 | transferred_pairs × standard cost | `company_id + TRANSFER + transfer_no + TRANSFER_TRANSIT_OUT` | Factory cancellation reversal | Invariant 3 | INVENTORY_MANAGER (system) | ✓ |
| 27 | Transfer Receipt (In-Transit In) | `StockTransfer → RECEIVED` | 1360 | 1390 | received_pairs × standard cost | `company_id + TRANSFER + transfer_no + TRANSFER_TRANSIT_RECEIVE` | Disputes clear remainder via 28 | Invariant 3 | INVENTORY_MANAGER (system) | ✓ |
| 28 | Transit Shortage Write-Off | Discrepancy resolved | 5390 / 1295* | 1390 | missing_pairs × standard cost | `company_id + TRANSFER + transfer_no + TRANSFER_SHORTAGE_WRITEOFF` | Found stock reverses write-off | Invariant 3 | CHIEF_ACCOUNTANT | ⚠ VAL-06: 1280 vs 1295 code |
| 29 | Franchise Outright Invoice | Franchise Tax Invoice issued | 1220 | 4130, 2310 | wholesale_price × 1.13 | `company_id + SALES_INVOICE + franchise_invoice_id + FRANCHISE_OUTRIGHT_INVOICE` | Credit note reversal | Invariant 1 (franchise AR) | BILLING_OPERATOR | ✓ |
| 30 | Franchise Consignment Dispatch | Consignment Challan issued | 1370 | 1350 | pairs × mfg_cost | `company_id + TRANSFER + cng_challan_no + FRANCHISE_CONSIGNMENT_DISPATCH` | Return from franchise reversal | Invariant 3 | INVENTORY_MANAGER | ✓ |
| 31 | Franchise Consignment Settlement | Certified sales report | 1220, 5400 | 4140, 2310, 1370 | Wholesale settlement amount | `company_id + SALES_INVOICE + settlement_no + FRANCHISE_CONSIGNMENT_SETTLEMENT` | Dispute reversal | Invariant 1 + 3 | CHIEF_ACCOUNTANT | ⚠ VAL-05: VAT base ambiguous |
| 32 | Franchise Royalty Billing | Annual/monthly fee invoice | 1220 | 4210, 2310 | Agreed fee + 13% VAT | `company_id + SALES_INVOICE + royalty_invoice_id + FRANCHISE_ROYALTY_INVOICE` | Invoice void reversal | Invariant 1 | BILLING_OPERATOR | ✓ |
| 33 | Internal Bank Transfer | Bank transfer executed | 1160 | 1150 | Exact transfer amount | `company_id + PAYMENT_RECEIPT + bank_txn_id + INTERNAL_BANK_TRANSFER` | Transfer rejection reversal | Invariant 4 | CHIEF_ACCOUNTANT | ✓ |
| 34 | Bad Debt Write-Off | CFO formal write-off approval | 1250 / 6420 | 1210 | Uncollectible balance | `company_id + MANUAL_JOURNAL + writeoff_board_ref + BAD_DEBT_WRITEOFF` | Recovery creates recovery entry | Invariant 1 | CHIEF_ACCOUNTANT | ✓ |

---

## Summary Count

| Status | Count | Events |
|---|---|---|
| ✓ Fully specified | 24 | 1,2,3,4,5,6,7,12,13,14,15,16,17,19,20,21,22,24,25,26,27,29,30,32,33,34 |
| ⚠ Has open issue | 7 | 8,9,10,11,18,23,28,31 |
| ✗ Cannot implement | 0 | — |

*Events 8 and 9 are blocked on VAL-02 (engineering fix). Events 10/11 are blocked on VAL-03 (CA decision). Event 31 is blocked on VAL-05 (CA decision). Events 18/23/28 have clarification fixes only.*

---

## Missing Event Coverage (Not in Matrix — Need Engineering Decision)

The following financial scenarios are not represented in the 34-event matrix and must be addressed before Phase 6B is scoped complete:

| Missing Event | Description | Accounts Affected | Decision Required |
|---|---|---|---|
| M1 | VAT Input Credit on Raw Material Purchases | Dr 1410 VAT Input, Cr 2110 AP | CA: Is LIVO VAT-registered purchaser eligible for input credit? |
| M2 | Monthly VAT Return Settlement (Output - Input) | Dr 2310 VAT Output, Cr 1410 VAT Input, Cr 1150 Bank | CA: Net VAT payment accounting |
| M3 | Opening Balances (Initial GL Setup) | Dr all Assets, Cr all Liabilities, Cr 3200 Retained Earnings | CA: Opening trial balance sign-off |
| M4 | Year-End Closing Entry | Dr all Revenue accounts, Cr 3300 Current Year P&L | CHIEF_ACCOUNTANT |
| M5 | Social Security Fund (SSF) Contribution | Dr Payroll Expense, Cr 2220 SSF Payable | CA: SSF rate confirmation (11% employee + 20% employer per SSF Act) |
| M6 | Customer Credit Limit Breach Handling | No journal; but system must prevent posting AR beyond limit | Client: credit limit enforcement policy |
| M7 | VAT Input on Fixed Asset Acquisition | Dr 1410 VAT Input, Cr 2110 AP | CA: Capital VAT input credit eligibility |
