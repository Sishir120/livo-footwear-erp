# LIVO FOOTWEAR ERP — PHASE 6A.1: DESIGN VALIDATION REPORT

**Status:** VALIDATION GATE AUDIT  
**Phase:** 6A.1 — Independent Validation (Specification-Only)  
**Audit Date:** 2026-10-15  
**Documents Audited:**
- `docs/PHASE_6A_ACCOUNTING_ARCHITECTURE.md` (22 KB, 295 lines)
- `docs/PHASE_6A_CHART_OF_ACCOUNTS.md` (19 KB)
- `docs/PHASE_6A_POSTING_MATRIX.md` (16 KB, 105 lines, 34 events)
- `docs/PHASE_6A_FRANCHISE_AND_BRANCH_ACCOUNTING.md` (10 KB, 147 lines)
- `docs/PHASE_6A_RECONCILIATION_AND_RECOVERY.md` (8 KB, 145 lines)
- `docs/PHASE_6A_OPEN_DECISIONS.md` (12 KB, 152 lines)

**Existing Code Inspected:**
- `backend/app/models/` — `invoice.py`, `receivable.py`, `purchase.py`, `stock.py`, `asset.py`, `worker.py`, `waste.py`, `sales.py`, `branch.py`, `stock_transfer.py`, `production.py`
- `backend/app/api/v1/` — `invoices.py`, `purchase.py`, `receivables.py`, `reports.py`, `transfers.py`
- `backend/app/core/currency.py`, `idempotency.py`

---

## VERDICT

> **PASS WITH LIMITATIONS**
>
> The design is structurally sound and its core financial concepts are correct. Its entity relationships, double-entry model, and posting matrix cover the primary business workflows. However, **seven issues in four severity tiers must be resolved before specific workflows are implemented.** Two Critical and two High issues could produce unbalanced ledgers, duplicate journal entries, or an inventory valuation that is permanently inconsistent with the General Ledger.

---

## 1. Severity Summary

| ID | Severity | Short Description | Category |
| :- | :---: | :--- | :--- |
| VAL-01 | **CRITICAL** | Idempotency key collision: same source doc triggers multiple distinct events with same derivable key — no versioned event_action enum defined | Proven design defect |
| VAL-02 | **CRITICAL** | `ProductionBatch` has no unit cost column — Events 8 & 9 (WIP & Finished Goods) are uncomputable from existing schema | Source model gap |
| VAL-03 | **HIGH** | COGS (Event 10) and Revenue (Event 11) post at different lifecycle states — temporal gap produces asymmetric profit in the same or different periods | Design risk |
| VAL-04 | **HIGH** | Payroll Example 2 labels TDS as "1% flat" — misleading since Nepal IT Act §87 is slab-based; statement is only valid for this specific worker | Spec ambiguity |
| VAL-05 | **HIGH** | Consignment settlement (Event 31) VAT base is ambiguous — franchisee already collected VAT; charging 13% on wholesale settlement risks double-VAT | Tax risk |
| VAL-06 | **MEDIUM** | Account 1280 named "Advances to Suppliers" in COA but referenced as "Claims Receivable (Logistics Carrier)" in Franchise doc | Code reference error |
| VAL-07 | **MEDIUM** | `fiscal_periods` table schema lacks `company_id` — breaks multi-tenant period lock performance and integrity | Schema gap |
| VAL-08 | **MEDIUM** | Existing `User.role` supports only `"editor"/"viewer"` — 6 new RBAC roles from spec have no database or enforcement path | Implementation gap |
| VAL-09 | **LOW** | Asset disposal (Event 23) credits/debits to `6400` (parent header) not a leaf posting account — COA hierarchy violation | COA hierarchy |
| VAL-10 | **LOW** | `source_doc_type` enum defined twice with different values in Architecture §2.2 and §3.1 | Consistency gap |

---

## 2. Critical Findings

### VAL-01 — CRITICAL: Idempotency Key Collision Risk

**Location:** `PHASE_6A_ACCOUNTING_ARCHITECTURE.md §4.4`

**Specification formula:**
```
idempotency_key = hash(company_id || source_doc_type || source_doc_id || event_action)
```

**Problem:** One Sales Order legitimately triggers at least 3 separate journal entries:
- Event 10: COGS on dispatch → `SO-001 + event_action=?`
- Event 11: AR+Revenue on invoice finalization → `SO-001 + event_action=?`
- Event 16: Inventory restock on credit note → `SO-001 + event_action=?`

The specification does not define the exhaustive list of `event_action` values, does not version them, and does not guard against two developers independently assigning the same string to different events.

**Concrete failure scenario:** If two handlers produce identical keys (e.g., both use `"INVOICE"`), PostgreSQL's `UNIQUE(company_id, idempotency_key)` silently rejects the second journal. The application receives an `IntegrityError`, returns 500, but the first journal was already committed. The AR or COGS entry never gets recorded.

**Compare to existing implementation:** `backend/app/core/idempotency.py` hashes `method + path + query_string + body` as a canonical fingerprint. This works for HTTP idempotency because the path is always unique per business action. The GL equivalent requires a rigourously defined, immutable `event_action` taxonomy.

**Required Fix (Engineering):**
Define a sealed Python enum (or database CHECK constraint):
```python
class GLEventAction(str, Enum):
    GRN_INVENTORY_RECEIPT = "GRN_INVENTORY_RECEIPT"
    GRN_LANDED_COST = "GRN_LANDED_COST"
    INVOICE_AR_REVENUE_VAT = "INVOICE_AR_REVENUE_VAT"
    INVOICE_COGS_DISPATCH = "INVOICE_COGS_DISPATCH"
    CREDIT_NOTE_REVERSAL = "CREDIT_NOTE_REVERSAL"
    CREDIT_NOTE_RESTOCK = "CREDIT_NOTE_RESTOCK"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"
    PAYROLL_ACCRUAL = "PAYROLL_ACCRUAL"
    PAYROLL_DISBURSEMENT = "PAYROLL_DISBURSEMENT"
    ADVANCE_ISSUED = "ADVANCE_ISSUED"
    ASSET_ACQUISITION = "ASSET_ACQUISITION"
    ASSET_DEPRECIATION = "ASSET_DEPRECIATION"          # + period suffix
    ASSET_DISPOSAL = "ASSET_DISPOSAL"
    TRANSFER_TRANSIT_OUT = "TRANSFER_TRANSIT_OUT"
    TRANSFER_TRANSIT_RECEIVE = "TRANSFER_TRANSIT_RECEIVE"
    TRANSFER_SHORTAGE_WRITEOFF = "TRANSFER_SHORTAGE_WRITEOFF"
    FRANCHISE_OUTRIGHT_INVOICE = "FRANCHISE_OUTRIGHT_INVOICE"
    FRANCHISE_CONSIGNMENT_DISPATCH = "FRANCHISE_CONSIGNMENT_DISPATCH"
    FRANCHISE_CONSIGNMENT_SETTLEMENT = "FRANCHISE_CONSIGNMENT_SETTLEMENT"
    # ... exhaustive sealed list
```

---

### VAL-02 — CRITICAL: Production Model Has No Cost Field — Events 8 & 9 Uncomputable

**Location:** `PHASE_6A_POSTING_MATRIX.md Events 8 and 9`

**Spec requires:**
- Event 8: `BOM quantity × standard/weighted unit cost in paisa`
- Event 9: `Total accumulated batch cost (materials + absorbed labor)`

**Actual `backend/app/models/production.py`:**
```python
class ProductionBatch(Base):
    produced_quantity = Column(Numeric, ...)
    status = Column(String(50), ...)
    # NO: unit_cost_paisa, total_cost_paisa, bom_cost_paisa

class ProductionMaterialUsage(Base):
    quantity_used = Column(Numeric, ...)
    # NO: unit_cost_paisa_at_issuance (no historical cost snapshot)
```

The only available cost is `Product.unit_price` (selling price), which the specification correctly identifies in §1.1 as `CRITICAL: inventory valued at selling price rather than manufacturing cost`.

**Phase 6B cannot implement Events 8 or 9 without first adding these columns.**

**Required Fix (Engineering, Phase 6B pre-requisite):**
```python
# ProductionMaterialUsage additions:
unit_cost_paisa_snapshot = Column(BigInteger, nullable=False, default=0)
# Captured at time of BOM issuance from raw_material weighted average cost

# ProductionBatch additions:
material_cost_paisa = Column(BigInteger, nullable=False, default=0)
labor_cost_paisa = Column(BigInteger, nullable=False, default=0)
overhead_cost_paisa = Column(BigInteger, nullable=False, default=0)
batch_total_cost_paisa = Column(BigInteger, nullable=False, default=0)
# Sum populated when batch transitions to COMPLETED
```

---

## 3. High Severity Findings

### VAL-03 — HIGH: COGS and Revenue Post at Different Lifecycle States

**Location:** `PHASE_6A_POSTING_MATRIX.md Events 10 and 11`

| Event | Trigger | Posts |
|---|---|---|
| Event 10 | `SalesOrder.status → DISPATCHED` | Dr COGS, Cr Finished Goods |
| Event 11 | `Invoice.finalized` | Dr AR, Cr Revenue, Cr VAT |

These are separate API calls. A sales order may be dispatched and COGS posted in Month 1, but the invoice finalized in Month 2. When Month 1 is closed, Gross Profit = Revenue₁ - COGS₁ - COGS₁(orphan) → Gross Profit is understated.

In the opposite case: invoice finalized (revenue recognized) before dispatch (COGS never posted) if the period closes before dispatch — Gross Profit is overstated.

**Required Fix (CA Decision Required):**
The specification must declare one of:
- **Option A:** Both COGS and Revenue/AR post simultaneously on dispatch (no gap possible)
- **Option B:** Both post simultaneously on invoice finalization (no dispatch-based COGS)
- **Option C:** Accrual bridge: COGS on dispatch → Dr COGS, Cr Inventory; Revenue on invoice → Dr AR, Cr Revenue, Cr VAT; the two entries are independent and period close timing is explicitly managed

This is an accounting policy decision, not an engineering decision.

---

### VAL-04 — HIGH: Payroll TDS Narrative Implies Flat 1% Rate

**Location:** `PHASE_6A_POSTING_MATRIX.md §3 Example 2`

The example states `TDS = NPR 280.00 (1%)` for a worker with gross pay of NPR 28,000/month. This is arithmetically correct (1% × 28,000 = 280) for a worker earning below the first slab threshold.

However the Nepal Income Tax Act 2058 Schedule 1 establishes progressive slabs:
- 1%: Up to NPR 600,000/year
- 10%: NPR 600,001 to NPR 1,500,000/year
- 20%: NPR 1,500,001 to NPR 2,000,000/year
- 30%: Above NPR 2,000,000/year

A factory floor supervisor earning NPR 55,000/month (NPR 660,000/year) would owe TDS at 1% on the first NPR 600K and 10% on the remaining NPR 60K — not 1% flat.

**Required Fix (Spec clarification):** The payroll posting specification must reference the full slab schedule, note that TDS is computed on annualized gross, and must state that the Phase 6B payroll module requires an annual projection engine (or CA-provided rate lookup table) rather than a fixed-rate multiplier.

---

### VAL-05 — HIGH: Consignment Settlement VAT Base Undefined

**Location:** `PHASE_6A_FRANCHISE_AND_BRANCH_ACCOUNTING.md §3.2`, `PHASE_6A_POSTING_MATRIX.md Event 31`

The scenario describes retail sales of NPR 300,000 (VAT-inclusive at franchisee level), with franchisee retaining 20% and remitting NPR 240,000 to LIVO. LIVO then issues a tax invoice for the settlement.

**Unresolved questions:**

1. **Has VAT already been collected?** The franchisee billed consumers at NPR 300,000 inclusive of their own VAT. LIVO charging 13% again on the wholesale settlement NPR 240,000 creates potential double-VAT — the same economic value taxed twice.

2. **If VAT must be charged:** Taxable = 240,000 / 1.13 = 212,389.38 NPR. This does not resolve to a clean integer paisa amount: 21,238,938 paisa / 1.13 = 18,795,520.35... paisa — requires explicit rounding rule.

3. **COGS timing:** The settlement invoice in Month 3 derecognizes inventory (Dr COGS, Cr 1370 Consignment) for pairs sold in Months 1-3. This violates matching principle for monthly profit reports.

**Required Fix:** CA must confirm whether LIVO's settlement invoice is subject to 13% VAT or treated as a commercial commission. The specification must then explicitly state the VAT-inclusive vs VAT-exclusive settlement basis and define the rounding rule for the arithmetic case above.

---

## 4. Medium Severity Findings

### VAL-06 — MEDIUM: Account Code 1280 Name/Function Mismatch

**COA defines:** `1280 | Advances to Suppliers | ASSET | ...`

**Franchise doc uses:** `1280 Claims Receivable (Logistics Carrier)` for transit damage claims

These are different asset classes. Carrier transit claims are contingent receivables against freight contractors, not supplier advances. Posting them to the same account would contaminate the supplier advance control account balance.

**Fix:** Add `1295 Carrier & Transit Claims Receivable` to the COA as a new leaf under parent `1200`.

---

### VAL-07 — MEDIUM: `fiscal_periods` Missing `company_id`

The `fiscal_periods` table schema in Architecture §3.1 does not include `company_id` directly. In a multi-tenant deployment, this means:
- Period lock queries require a JOIN: `fiscal_periods → fiscal_years → company_id`
- The period cannot be indexed independently by company for fast lock checks
- A bug in the join could accidentally check another company's period status

**Fix:** Add `company_id INTEGER NOT NULL FK(companies.id)` to `fiscal_periods`, with `UNIQUE(company_id, fiscal_year_id, period_number)` and index `(company_id, is_locked)`.

---

### VAL-08 — MEDIUM: Role Model Insufficient for Specification's RBAC

Current `user.py`: `role = Column(String(50), default="viewer")` — effectively a binary `viewer/editor`.

Architecture §5.1 proposes 6 distinct financial roles: `BILLING_OPERATOR`, `INVENTORY_MANAGER`, `BRANCH_MANAGER`, `ACCOUNTANT`, `CHIEF_ACCOUNTANT`, `SUPER_ADMIN`. Until these are enforced at the API dependency level (`deps.py`), the "Control Account Enforcement" claim is entirely UI-layer gating. Any authenticated `editor` can call any financial endpoint.

**Fix (Phase 6B prerequisite):** Migrate `users.role` to a formal enum, update `deps.py` to enforce role-level capabilities on financial endpoints, and add a migration that maps existing `editor → ACCOUNTANT` and `viewer → BILLING_OPERATOR` as safe defaults.

---

## 5. Low Severity Findings

### VAL-09 — LOW: Asset Disposal Posts to Parent Account Code

Event 23 debits `6400 Loss on Disposal`. COA §2.6 defines `6400 Financial & Other Expenses` as a header/parent account. Its leaf children are `6410` and `6420`. Posting to the parent violates the COA convention that only leaf accounts receive journal lines.

**Fix:** Add leaf account `6430 Loss on Asset Disposal & Write-Off` under parent `6400`.

### VAL-10 — LOW: `source_doc_type` Enum Defined Twice with Different Values

Architecture §2.2 (Dimensions Matrix): `INVOICE | GRN | PAYMENT | PAYROLL | TRANSFER | JOURNAL`

Architecture §3.1 (`journal_entries` column spec): `SALES_INVOICE | CREDIT_NOTE | PURCHASE_GRN | PAYMENT_RECEIPT | SUPPLIER_PAYMENT | PAYROLL_RUN | STOCK_ADJUSTMENT | MANUAL_JOURNAL`

The §3.1 list is more operationally precise. The §2.2 list should be removed and replaced with a reference to the §3.1 canonical enum.

---

## 6. Validated as Correct (Non-Issues)

1. **Integer-paisa arithmetic:** `currency.py` correctly converts `Decimal → ROUND_HALF_UP → paisa`. Example 1 arithmetic verified: DR 13,560,000 = CR (12,000,000 + 1,560,000) = 13,560,000. ✓

2. **Example 2 payroll arithmetic:** DR 2,800,000 = CR (2,272,000 + 500,000 + 28,000) = 2,800,000. ✓ (arithmetic is correct; narrative around TDS rate needs clarification — see VAL-04)

3. **Balance constraint:** `CheckConstraint("total_debit_paisa = total_credit_paisa")` on `journal_entries` is database-enforced. XOR constraint on `journal_lines` prevents split debit/credit. ✓

4. **Existing idempotency integration:** `backend/app/core/idempotency.py` is a production-ready HTTP-level idempotency engine. The GL must integrate with this system, not duplicate it.

5. **Franchise vs Branch structural separation:** The design correctly prevents franchise transfers from being treated as no-revenue internal movements and prevents branch movements from generating unauthorized external sales. ✓

6. **Post-restore verification runbook:** The 5-step procedure is complete and logically ordered. Universal balance check before subledger checks is the correct sequence. ✓

7. **AR subledger reconciliation formula:** The formula `GL_Balance(1210) = Σ(direction × amount_paisa)` across `receivable_entries` is correct and consistent with the existing `ReceivableEntry` model. ✓

---

## 7. Required Sign-Off Matrix

### Client / Executive Management
| Decision | Blocking Phase 6B? |
|---|---|
| D1: Franchise legal entity structure | **Yes** — determines franchise GL model |
| D3: Royalty fee structure | Partially (only if royalties exist) |
| D7: IRD CBMS e-billing compliance | **Yes** — affects invoice posting handler |
| D8: Branch financial visibility | No — RBAC configuration only |

### Chartered Accountant / Nepal Tax Professional
| Decision | Blocking Phase 6B? |
|---|---|
| D2: Consignment vs outright wholesale | **Yes** — determines franchise event triggers |
| D4: Inventory costing method (NAS 2) | **Yes** — determines Event 8/9 cost basis |
| D5: Depreciation method | Partially (only for Event 22) |
| D6: Period lock policy | **Yes** — determines period-lock enforcement strictness |
| VAL-03: Revenue & COGS recognition date | **Yes** — determines Events 10 & 11 coupling |
| VAL-05: Consignment VAT base | **Yes** — determines Event 31 amount |

### Engineering Team (No External Input Required)
| Fix | Scope |
|---|---|
| VAL-01: Define GLEventAction enum | 1–2 days |
| VAL-02: Add cost fields to Production models | 0.5 days (schema + migration) |
| VAL-06: Add account 1295 to COA | 0.25 days (COA document + seed data) |
| VAL-07: Add company_id to fiscal_periods | 0.5 days (schema + index) |
| VAL-08: Extend role system | 2–3 days (migration + deps.py refactor) |
| VAL-09: Add account 6430 | 0.25 days |
| VAL-10: Unify source_doc_type enum | 0.25 days |
