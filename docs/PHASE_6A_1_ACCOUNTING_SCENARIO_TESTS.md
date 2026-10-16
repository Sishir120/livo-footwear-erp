# LIVO FOOTWEAR ERP — PHASE 6A.1: ACCOUNTING SCENARIO TESTS

**Status:** VALIDATION GATE AUDIT  
**Phase:** 6A.1 (Specification-Only)  
**Purpose:** Validate Phase 6A posting rules against complete, numbered transactions with verified arithmetic  
**Audit Date:** 2026-10-15  
**All amounts in integer paisa unless NPR noted. 1 NPR = 100 paisa.**

---

## Scenario 1: Raw Material Purchase, GRN, Landed Cost, and AP Settlement

**Setup:** LIVO orders 500 kg of PU soles from a Chinese supplier at NPR 450/kg. Landed costs: customs duty NPR 22,500, freight NPR 15,000, insurance NPR 2,500.

### Step 1.1 — Purchase Order Issuance
- **Trigger:** `Purchase` created with `status = ORDERED`
- **Journal:** NO FINANCIAL POSTING (Event 1 ✓)
- **Documents Required:** `PO-2083-00042`

### Step 1.2 — Goods Receipt (GRN)
- **Trigger:** `Purchase → RECEIVED`, GRN allocated `GRN-0042`
- **Base Cost:** 500 kg × NPR 450 = NPR 225,000 = **22,500,000 paisa**
- **Journal Entry: JE-GRN-0042-RECEIPT**

```
DR  1320  Raw Materials - Soles & Heels            22,500,000 paisa
  CR  2110  Accounts Payable - Material Suppliers              22,500,000 paisa
[Sum DR: 22,500,000 == Sum CR: 22,500,000. Delta = 0 ✓]
```
- **AR Subledger:** AP subledger entry created for Supplier, +22,500,000 paisa (payable)
- **Idempotency Key:** `SHA256("1||PURCHASE_GRN||GRN-0042||GRN_INVENTORY_RECEIPT")`

### Step 1.3 — Landed Cost Allocation
- **Trigger:** Landed cost voucher finalized on purchase
- **Amounts:** 
  - Customs duty: NPR 22,500 = 2,250,000 paisa
  - Freight: NPR 15,000 = 1,500,000 paisa
  - Insurance: NPR 2,500 = 250,000 paisa
  - **Total Landed: 4,000,000 paisa**
- **Effective Unit Cost:** (22,500,000 + 4,000,000) / 500 kg = 26,500,000 / 500 = **53,000 paisa/kg**
- **Journal Entry: JE-GRN-0042-LANDED**

```
DR  1320  Raw Materials - Soles & Heels             4,000,000 paisa
  CR  2120  Landed Cost Clearing / Accrued Freight              4,000,000 paisa
[Sum DR: 4,000,000 == Sum CR: 4,000,000. Delta = 0 ✓]
```
- **Updated Inventory GL Balance for 1320:** 22,500,000 + 4,000,000 = **26,500,000 paisa**

### Step 1.4 — Carrier & Customs Payment
- **Trigger:** Bank payment released to freight forwarder
- **Amount:** 4,000,000 paisa total landed costs
- **Journal Entry: JE-LANDSETTLE-0042**

```
DR  2120  Landed Cost Clearing / Accrued Freight    4,000,000 paisa
  CR  1150  Operating Bank Account (Nabil)                      4,000,000 paisa
[Sum DR: 4,000,000 == Sum CR: 4,000,000. Delta = 0 ✓]
```
- **2120 balance after:** 4,000,000 - 4,000,000 = **0 paisa (cleared) ✓**

### Step 1.5 — Supplier Invoice Settlement (AP Clearing)
- **Trigger:** Payment voucher finalized, net NPR 225,000 transferred to supplier
- **Journal Entry: JE-AP-CLEAR-0042**

```
DR  2110  Accounts Payable - Material Suppliers    22,500,000 paisa
  CR  1150  Operating Bank Account (Nabil)                     22,500,000 paisa
[Sum DR: 22,500,000 == Sum CR: 22,500,000. Delta = 0 ✓]
```
- **2110 balance after:** 0 paisa (supplier settled) ✓
- **Reconciliation check:** GL 2110 balance = AP Subledger total = 0 ✓

---

## Scenario 2: Raw Material Issue, Production, Finished Goods Completion

> **Note:** This scenario is currently blocked by VAL-02 (no `unit_cost_paisa_snapshot` in `ProductionMaterialUsage`, no `batch_total_cost_paisa` in `ProductionBatch`). The specification defines the journal entries but Phase 6B cannot implement them until the production schema is extended.

**Setup:** Batch BATCH-0118 uses 50 kg of soles at weighted average cost of 53,000 paisa/kg plus 100 kg of leather at 85,000 paisa/kg. Batch produces 200 pairs "Classic Boot 41".

### Step 2.1 — BOM Issue to WIP (Event 8)
- **Soles cost:** 50 × 53,000 = 2,650,000 paisa
- **Leather cost:** 100 × 85,000 = 8,500,000 paisa
- **Total WIP:** 11,150,000 paisa

```
DR  1340  Work in Progress (WIP)                  11,150,000 paisa
  CR  1320  Raw Materials - Soles & Heels                       2,650,000 paisa
  CR  1310  Raw Materials - Leather & Uppers                    8,500,000 paisa
[Sum DR: 11,150,000 == Sum CR: 11,150,000. Delta = 0 ✓]
```
*Requires: `ProductionMaterialUsage.unit_cost_paisa_snapshot` = 53,000 and 85,000 respectively — **column currently missing in production.py***

### Step 2.2 — Batch Completion — Finished Goods (Event 9)
- **Additional labor absorbed:** 500,000 paisa (direct wages)
- **Total batch cost:** 11,150,000 + 500,000 = 11,650,000 paisa
- **Unit cost per pair:** 11,650,000 / 200 = 58,250 paisa/pair

```
DR  1350  Finished Goods - Central Warehouse      11,650,000 paisa
  CR  1340  Work in Progress (WIP)                             11,650,000 paisa
[Sum DR: 11,650,000 == Sum CR: 11,650,000. Delta = 0 ✓]
```
*Requires: `ProductionBatch.batch_total_cost_paisa` = 11,650,000 — **column currently missing in production.py***

---

## Scenario 3: Wholesale Sale, VAT, Payment, and Credit Note

**Setup:** Client "Kathmandu Shoes Pvt Ltd" (client_id=42) buys 200 pairs at NPR 1,200.00/pair. Manufacturing cost is 58,250 paisa/pair (from Scenario 2). Order dispatched same day as invoice.

### Step 3.1 — Sales Order Created, Dispatched → COGS (Event 10)

> **⚠ VAL-03 Decision Required:** Under Delivery-Date Recognition (Option A), Event 10 and 11 both post simultaneously on dispatch.

- **COGS:** 200 pairs × 58,250 paisa = 11,650,000 paisa

```
DR  5400  Cost of Goods Sold - Finished Shoes     11,650,000 paisa
  CR  1350  Finished Goods - Central Warehouse                 11,650,000 paisa
[Sum DR: 11,650,000 == Sum CR: 11,650,000. Delta = 0 ✓]
```

### Step 3.2 — Invoice Finalized → AR, Revenue, VAT (Event 11)
- **Taxable:** 200 × 1,200 = NPR 240,000 = 24,000,000 paisa
- **VAT (13%):** `round(24,000,000 × 0.13)` = `round(3,120,000.0)` = **3,120,000 paisa** (exact integer — no rounding needed since 240,000 × 13 = 3,120,000 exactly)
- **Total Invoice:** 24,000,000 + 3,120,000 = **27,120,000 paisa** = NPR 271,200.00

```
DR  1210  Accounts Receivable - Wholesale         27,120,000 paisa
  CR  4110  Footwear Sales - Wholesale                         24,000,000 paisa
  CR  2310  VAT Output Liability (13%)                          3,120,000 paisa
[Sum DR: 27,120,000 == Sum CR: 27,120,000. Delta = 0 ✓]
```
- **AR Subledger Entry:** `ReceivableEntry(direction=+1, amount_paisa=27,120,000)`

### Step 3.3 — Partial Payment Collection (Event 12)
- **Client pays NPR 150,000 cash** = 15,000,000 paisa

```
DR  1110  Cash on Hand - Factory                  15,000,000 paisa
  CR  1210  Accounts Receivable - Wholesale                    15,000,000 paisa
[Sum DR: 15,000,000 == Sum CR: 15,000,000. Delta = 0 ✓]
```
- **AR Subledger Entry:** `ReceivableEntry(direction=-1, amount_paisa=15,000,000)`
- **Outstanding Receivable:** 27,120,000 - 15,000,000 = **12,120,000 paisa** (NPR 121,200 outstanding)
- **Reconciliation check:** GL 1210 balance = AR Subledger balance = 12,120,000 ✓

### Step 3.4 — Statutory Credit Note (Event 15) — 10 Pairs Returned
- **Return value:** 10 pairs × NPR 1,200 = NPR 12,000 = 1,200,000 paisa (taxable)
- **VAT reversal:** round(1,200,000 × 0.13) = round(156,000.0) = **156,000 paisa**
- **Total credit note:** 1,200,000 + 156,000 = **1,356,000 paisa**

```
DR  4110  Footwear Sales - Wholesale (taxable)     1,200,000 paisa
DR  2310  VAT Output Liability (13%)                 156,000 paisa
  CR  1210  Accounts Receivable - Wholesale                     1,356,000 paisa
[Sum DR: 1,356,000 == Sum CR: 1,356,000. Delta = 0 ✓]
```
- **AR Subledger Entry:** `ReceivableEntry(entry_type=CREDIT_NOTE, direction=-1, amount_paisa=1,356,000)`
- **Revised Outstanding:** 12,120,000 - 1,356,000 = **10,764,000 paisa** = NPR 107,640

### Step 3.5 — Return Restocking (Event 16)
- **10 pairs returned to stock at manufacturing cost:** 10 × 58,250 = 582,500 paisa

```
DR  1350  Finished Goods - Central Warehouse         582,500 paisa
  CR  5400  Cost of Goods Sold - Finished Shoes                   582,500 paisa
[Sum DR: 582,500 == Sum CR: 582,500. Delta = 0 ✓]
```

### Final Gross Profit Verification (Scenario 3)
```
Revenue (190 pairs sold net): 190 × 1,200 NPR = 22,800,000 paisa
COGS (200 dispatched - 10 restocked): (11,650,000 - 582,500) = 11,067,500 paisa
Gross Profit = 22,800,000 - 11,067,500 = 11,732,500 paisa = NPR 117,325
Gross Margin = 11,732,500 / 22,800,000 = 51.5%
```
*Note: VAT is collected on behalf of IRD and does not affect gross profit calculation.*

---

## Scenario 4: Payroll Accrual, Advance Recovery, and Disbursement

**Setup:** Worker Arjun Thapa (Stitching section, classified `FACTORY`): monthly basic rate NPR 28,000. Annual gross = NPR 336,000 < 600,000 threshold → TDS slab = 1%.

> **⚠ VAL-04:** TDS computation must reference slab schedule, not a flat rate. This scenario uses the correct 1% slab rate but the specification must document the slab logic.

- **Gross Pay:** 28,000 NPR = 2,800,000 paisa
- **Advance Recovery:** NPR 5,000 = 500,000 paisa (WorkerAdvance ISSUED earlier, now recovered)
- **TDS:** `annualized_gross = 28,000 × 12 = 336,000 NPR < 600,000` → slab rate = 1% → monthly TDS = 28,000 × 0.01 = **NPR 280 = 28,000 paisa**
- **Net Wages Payable:** 2,800,000 - 500,000 - 28,000 = **2,272,000 paisa**

### Step 4.1 — Payroll Accrual (Event 18)

```
DR  5220  Direct Factory Wages - Stitching Section  2,800,000 paisa
  CR  2210  Wages & Salaries Payable (net)                      2,272,000 paisa
  CR  1290  Advances to Factory Workers (deduction)               500,000 paisa
  CR  2340  TDS Payable - Employee Payroll                         28,000 paisa
[Sum DR: 2,800,000 == Sum CR: (2,272,000 + 500,000 + 28,000) = 2,800,000. Delta = 0 ✓]
```
- **Payroll Subledger:** `WorkerMonthlyRecord(status=PENDING, net_paid_paisa=2,272,000)`
- **Reconciliation check:** GL 2210 balance includes this worker's 2,272,000. GL 1290 decreased by 500,000 (advance recovered).

### Step 4.2 — Payroll Disbursement (Event 19)

```
DR  2210  Wages & Salaries Payable                  2,272,000 paisa
  CR  1160  Payroll Bank Account (Global IME)                   2,272,000 paisa
[Sum DR: 2,272,000 == Sum CR: 2,272,000. Delta = 0 ✓]
```
- **Payroll Subledger:** `WorkerMonthlyRecord(status=PAID, paid_date=2083-07-31)`
- **Reconciliation check:** GL 2210 balance reduced by 2,272,000. Payroll subledger sum of `PENDING` records decreases correspondingly. ✓

---

## Scenario 5: Fixed Asset Acquisition, Depreciation, and Disposal

**Setup:** LIVO purchases a hydraulic cutting press from a local supplier. Invoice: NPR 850,000. Import duties NPR 50,000. Useful life: 10 years (SLM) or Nepal IT Act Pool D: 15% WDV.

> **⚠ D5 Decision Required (CA):** SLM vs WDV must be confirmed before depreciation Event 22 can post.

### Step 5.1 — Asset Acquisition (Event 21)
- **Total cost:** 850,000 + 50,000 = NPR 900,000 = 90,000,000 paisa

```
DR  1510  Plant, Machinery & Footwear Equipment    90,000,000 paisa
  CR  2110  Accounts Payable - Material Suppliers              90,000,000 paisa
[Sum DR: 90,000,000 == Sum CR: 90,000,000. Delta = 0 ✓]
```
- **Fixed Asset Register:** `FixedAsset(purchase_cost_paisa=90,000,000)`
- **Invariant 6 check:** GL 1510 += 90,000,000; FA Register total += 90,000,000 ✓

### Step 5.2 — Monthly Depreciation (Event 22)
**Under SLM (10-year life):**
- Annual depreciation = 90,000,000 / 10 / 12 = **750,000 paisa/month**

**Under WDV Pool D (15%/year):**
- Annual depreciation = 90,000,000 × 0.15 = 13,500,000 paisa/year → **1,125,000 paisa/month** (Year 1)

Using SLM for this scenario:
```
DR  5340  Depreciation - Factory Machinery            750,000 paisa
  CR  1519  Accumulated Depreciation - Machinery               750,000 paisa
[Sum DR: 750,000 == Sum CR: 750,000. Delta = 0 ✓]
```

### Step 5.3 — Asset Disposal after 3 Years (Event 23)
- **Accumulated depreciation:** 3 years × 12 months × 750,000 = **27,000,000 paisa**
- **Net book value:** 90,000,000 - 27,000,000 = 63,000,000 paisa
- **Sale proceeds:** NPR 550,000 = **55,000,000 paisa**
- **Loss on disposal:** 63,000,000 - 55,000,000 = **8,000,000 paisa** (Loss)

```
DR  1150  Operating Bank Account                   55,000,000 paisa
DR  1519  Accumulated Depreciation - Machinery     27,000,000 paisa
DR  6430* Loss on Asset Disposal                    8,000,000 paisa
  CR  1510  Plant, Machinery & Footwear Equipment              90,000,000 paisa
[Sum DR: (55,000,000 + 27,000,000 + 8,000,000) = 90,000,000 == Sum CR: 90,000,000. Delta = 0 ✓]
```
*Note: Uses proposed `6430` from VAL-09 fix. Current spec posts to parent `6400` (incorrect).*

---

## Scenario 6: Inter-Branch Stock Transfer with Shortage

**Setup:** 100 pairs transferred from Birgunj Factory to Kathmandu Showroom. Manufacturing cost: 58,250 paisa/pair. Upon receipt, 2 pairs are missing (transit shortage).

### Step 6.1 — Dispatch: Factory → In-Transit (Event 26)
- **100 pairs × 58,250 = 5,825,000 paisa**

```
DR  1390  Inventory In-Transit Clearing             5,825,000 paisa
  CR  1350  Finished Goods - Central Warehouse                  5,825,000 paisa
[Sum DR: 5,825,000 == Sum CR: 5,825,000. Delta = 0 ✓]
```

### Step 6.2 — Partial Receipt at Showroom: 98 pairs received (Event 27)
- **98 × 58,250 = 5,708,500 paisa**

```
DR  1360  Finished Goods - Retail Showroom          5,708,500 paisa
  CR  1390  Inventory In-Transit Clearing                       5,708,500 paisa
[After: 1390 balance = 5,825,000 - 5,708,500 = 116,500 paisa remaining]
```

### Step 6.3 — Shortage Write-Off: 2 missing pairs (Event 28)
- **2 × 58,250 = 116,500 paisa**

```
DR  5390  Inventory Shrinkage & Transit Loss         116,500 paisa
  CR  1390  Inventory In-Transit Clearing                       116,500 paisa
[1390 cleared: 116,500 - 116,500 = 0 paisa ✓]
[Sum DR: 116,500 == Sum CR: 116,500. Delta = 0 ✓]
```
- **Final inventory position:** Factory -100 pairs, In-transit 0, Showroom +98 pairs, Shrinkage expense charged ✓

---

## Scenario 7: Franchise Outright Sale vs Consignment Settlement

### 7A — Outright Wholesale to Independent Franchise (Event 29)

**Setup:** Franchise "Pokhara Footwear Center Pvt. Ltd." (franchise_id=5, own PAN) orders 50 pairs at wholesale NPR 900/pair.

- **Taxable:** 50 × 900 = NPR 45,000 = 4,500,000 paisa
- **VAT (13%):** round(4,500,000 × 0.13) = **585,000 paisa**
- **Total Invoice:** 4,500,000 + 585,000 = **5,085,000 paisa**
- **COGS (manufacturing cost):** 50 × 58,250 = **2,912,500 paisa**

```
Step A: Invoice
DR  1220  Accounts Receivable - Franchise Partners  5,085,000 paisa
  CR  4130  Footwear Sales - Franchise Outright                 4,500,000 paisa
  CR  2310  VAT Output Liability (13%)                           585,000 paisa
[Sum DR: 5,085,000 == Sum CR: 5,085,000. Delta = 0 ✓]

Step B: COGS
DR  5400  Cost of Goods Sold - Finished Shoes       2,912,500 paisa
  CR  1350  Finished Goods - Central Warehouse                  2,912,500 paisa
[Sum DR: 2,912,500 == Sum CR: 2,912,500. Delta = 0 ✓]

Step C: Settlement (30-day terms)
DR  1150  Operating Bank Account                    5,085,000 paisa
  CR  1220  Accounts Receivable - Franchise Partners             5,085,000 paisa
[Sum DR: 5,085,000 == Sum CR: 5,085,000. Delta = 0 ✓]
```
- **Gross Profit on Franchise Outright:** 4,500,000 - 2,912,500 = **1,587,500 paisa (35.3% margin)**
- **No stock appears in franchise's custodial count** (title transferred on dispatch) ✓

### 7B — Consignment Dispatch + Settlement (Events 30, 31)

> **⚠ VAL-05 Decision Required (CA):** The VAT base on the settlement invoice is unresolved. This scenario illustrates BOTH interpretations.

**Setup:** 50 pairs dispatched on consignment. 40 pairs sold at franchisee retail price NPR 1,500 inclusive VAT. LIVO settlement: 80% of retail ex-VAT.

- **Consignment Dispatch (Event 30):** 50 pairs × 58,250 = **2,912,500 paisa** (no revenue)

```
DR  1370  Consignment Inventory - Franchise Stores  2,912,500 paisa
  CR  1350  Finished Goods - Central Warehouse                  2,912,500 paisa
[Sum DR: 2,912,500 == Sum CR: 2,912,500. Delta = 0 ✓]
```

**Consignment Settlement (Event 31) — 40 pairs sold at retail NPR 1,500 incl. VAT:**
- Franchisee retail revenue (incl VAT at franchisee's PAN): 40 × 1,500 = NPR 60,000
- Retail ex-VAT: 60,000 / 1.13 = NPR 53,097.35... → This has a rounding issue at paisa level

**Interpretation A (Settlement is ex-VAT at wholesale, LIVO adds 13%):**
- Settlement base: 80% × 53,097 = NPR 42,478 ≈ 4,247,800 paisa
- LIVO adds 13% VAT: 4,247,800 × 0.13 = 552,214 paisa (rounded)
- AR debit: 4,247,800 + 552,214 = 4,800,014 paisa → Risk of double-VAT on the same goods

**Interpretation B (Settlement excludes VAT — commercial commission only):**
- Settlement: NPR 42,478 = 4,247,800 paisa (no additional VAT)
- COGS derecognition: 40 × 58,250 = **2,330,000 paisa**

```
[Interpretation B — CA-confirmed required]
DR  1220  Accounts Receivable - Franchise Partners  4,247,800 paisa
DR  5400  Cost of Goods Sold                        2,330,000 paisa
  CR  4140  Franchise Consignment Revenue                       4,247,800 paisa
  CR  1370  Consignment Inventory                               2,330,000 paisa
[Sum DR: 6,577,800 == Sum CR: 6,577,800. Delta = 0 ✓]
```

**⚠ CA decision required before this event can be posted.**

---

## Scenario 8: Central Payment of Company-Owned Branch Expense

**Setup:** LIVO HQ pays Kathmandu Showroom rent of NPR 50,000 + 10% TDS directly to landlord.

- **Gross rent:** NPR 50,000 = 5,000,000 paisa
- **TDS (10%):** 5,000,000 × 0.10 = **500,000 paisa**
- **Net bank payment:** 5,000,000 - 500,000 = **4,500,000 paisa**

```
DR  6210  Retail Showroom Rent - Kathmandu   [branch_id=KTM]  5,000,000 paisa
  CR  1150  Operating Bank Account (Nabil)                      4,500,000 paisa
  CR  2320  TDS Payable - Rent (10%)                              500,000 paisa
[Sum DR: 5,000,000 == Sum CR: (4,500,000 + 500,000) = 5,000,000. Delta = 0 ✓]
```
- **Branch dimension tag:** `branch_id = KTM` propagated to journal_line for the expense debit ✓
- **Branch P&L impact:** NPR 50,000 rent expense assigned to Kathmandu Showroom segment ✓

---

## Rounding Edge-Case Verification

The following cases test the `calculate_vat_paisa` function in `backend/app/core/currency.py`:

| Taxable (paisa) | × 0.13 (exact) | Rounded (Python round()) | Total | Balanced? |
|---|---|---|---|---|
| 100 | 13.0 | 13 | 113 | ✓ |
| 77 | 10.01 | 10 | 87 | ✓ |
| 769 | 99.97 | 100 | 869 | ✓ |
| 3 | 0.39 | 0 | 3 | ✓ (VAT rounds to 0 on tiny amounts) |
| 7692307 | 999,999.91 | 1,000,000 | 8,692,307 | ✓ |
| 7692308 | 1,000,000.04 | 1,000,000 | 8,692,308 | ✓ |

Python `round()` uses banker's rounding (round half to even). The existing `calculate_vat_paisa` uses `int(round(...))` which applies Python's banker's rounding to the Decimal calculation. This is consistent for VAT computation. The `ROUND_HALF_UP` in `quantize_npr` applies only to the NPR → paisa conversion step.

**Verified:** The existing `currency.py` implementation is correct and will produce 0-paisa balanced journals across these edge cases.
