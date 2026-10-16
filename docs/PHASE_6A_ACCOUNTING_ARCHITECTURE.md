# LIVO FOOTWEAR ERP — PHASE 6A: GENERAL LEDGER & FINANCIAL ARCHITECTURE SPECIFICATION

**Status:** ARCHITECTURAL SPECIFICATION & DESIGN CONTRACT  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Core Accounting Engine (FastAPI / SQLAlchemy / PostgreSQL)  
**Statutory Context:** Nepal Companies Act 2063, Value Added Tax Act 2052 (Rules 2053), Income Tax Act 2058, Nepal Financial Reporting Standards (NFRS)  

---

## 1. Executive Summary & Existing Accounting Baseline

### 1.1 Baseline Audit: Implemented vs Missing Capabilities
An adversarial inspection of the current production codebase (`backend/app/models/`, `backend/app/api/v1/`) establishes the precise baseline:

| Subsystem / Domain | Implemented Baseline | Missing General Ledger Capabilities | Architecture Risk Level |
| :--- | :--- | :--- | :--- |
| **General Ledger Core** | None. Tables `accounts`, `journal_entries`, `journal_lines`, and `fiscal_periods` do not exist. | Zero double-entry general ledger. No chart of accounts. No debit/credit validation engine. | **CRITICAL**: All financial records exist in single-sided operational silos. |
| **Accounts Receivable (AR)** | `ReceivableEntry` (append-only paisa ledger with `+1` debit / `-1` credit direction) and `PaymentAllocation`. | Unlinked to GL. No corresponding revenue or VAT output entries generated in a balanced ledger. | **HIGH**: Operational AR works, but cannot produce a validated Trial Balance or Balance Sheet. |
| **Accounts Payable (AP)** | `Supplier` master table exists. Purchases tracked in `purchases` table with landed cost fields. | No Accounts Payable subledger (`PayableEntry` or supplier ledger). No vendor aging or payment allocation model. | **CRITICAL**: Supplier liabilities and settlement are unmanaged in double entry. |
| **Sales & VAT** | `Invoice` table with 13% statutory Nepal IRD VAT calculation, integer-paisa getters/setters, immutability on finalization, Annex-10 credit notes. | No Sales Revenue GL posting, no VAT Output GL control account posting, no automated debtor reconciliation. | **MEDIUM-HIGH**: Billing math is correct, but unposted to financial ledgers. |
| **Purchasing & Landed Costs** | `Purchase` table tracks supplier bills, GRN, landed costs (`carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`). | Costs are recorded in columns on purchase records but generate **zero** accounting entries. No Landed Cost Clearing account. | **HIGH**: Material receipt costs do not reflect in financial inventory assets or clearing payables. |
| **Inventory & COGS** | `StockMovement` tracks physical pairs (+1 / -1). `reports.py` computes "estimated value" as $\text{quantity} \times \text{product.unit\_price}$ (sales price). | Violates NAS 2 / IAS 2: inventory valued at selling price rather than manufacturing cost. Zero COGS posted on dispatch. | **CRITICAL**: Cost of Goods Sold is never recognized, distorting manufacturing gross profit. |
| **Factory Operating Expenses** | `FactoryExpense` and `SalesExpense` tables track expense categories, cash/bank methods, and integer paisa. | Expenses are single-sided operational audit logs. No posting to expense GL accounts or credit to Cash/Bank GL. | **MEDIUM**: Cash outflows and operating expenses are unverified against bank accounts. |
| **Payroll & Labor** | `WorkerMonthlyRecord` and `WorkerAdvance` track hours, overtime, gross pay, deductions, and net pay in paisa. | No Payroll Expense GL entries, no Wages Payable liability GL account, no GL advance recovery tracking. | **MEDIUM**: Payroll math is hardened, but financial liabilities are unposted. |
| **Fixed Assets** | `FixedAsset` table records machinery, moulds, vehicles, and tools with integer purchase cost. | No depreciation calculation, no Accumulated Depreciation GL account, no asset disposal or impairment engine. | **MEDIUM**: Asset register is informational; balance sheet asset values remain static. |
| **Branch & Warehouse** | `Branch` (types: `HEAD_OFFICE`, `FACTORY`, `RETAIL_OUTLET`, `REGIONAL_HUB`) linked to `Warehouse`. `StockTransfer` operational. | No multi-segment branch financial ledger. No franchise commercial or consignment ledger model. | **HIGH**: Branch transfers do not have in-transit financial clearing accounts. |

---

## 2. Dimensional Accounting Architecture

### 2.1 Separation of Concerns: Entity, Branch, Warehouse, and Franchise
To eliminate ambiguity, the system strictly separates statutory legal entities from operating locations, physical stock points, and commercial partners:

```
+----------------------------------------------------------------------------------------------------+
|                                    LEGAL ENTITY (Company)                                          |
|  - Sole statutory entity registered with Inland Revenue Department (IRD)                          |
|  - Holds 9-digit Permanent Account Number (PAN) / VAT Registration                                 |
|  - Sole owner of the primary Balance Sheet and statutory Tax Filing                                |
+----------------------------------------------------------------------------------------------------+
                   |                                                          |
                   | (100% Owned Operating Segments)                          | (Independent B2B Commercial Entity)
                   v                                                          v
+------------------------------------+                     +------------------------------------+
|        INTERNAL BRANCH             |                     |         FRANCHISE PARTNER          |
|  - Profit / Cost Center            |                     |  - Independent 3rd-party Business  |
|  - Inherits Parent PAN             |                     |  - Own Independent 9-digit PAN     |
|  - Sub-segment of Company GL       |                     |  - Customer / Vendor in Company GL |
+------------------------------------+                     +------------------------------------+
                   |                                                          |
                   | Physical Custody Control                                 | Commercial Stock Point
                   v                                                          v
+------------------------------------+                     +------------------------------------+
|        PHYSICAL WAREHOUSE          |                     |        FRANCHISE WAREHOUSE         |
|  - Physical storage building/room  |                     |  - Franchise Owned Stock (Sale)    |
|  - Pure quantity conservation      |                     |  - Consignment Stock Account       |
|  - No legal or financial persona   |                     |    (Title remains with Company)    |
+------------------------------------+                     +------------------------------------+
```

### 2.2 Accounting Dimensions Matrix
Every journal line posted to the General Ledger carries mandatory and optional dimensional tags:

| Dimension | Scope & Type | Nullable? | Purpose | Reporting Aggregation |
| :--- | :--- | :--- | :--- | :--- |
| `company_id` | Foreign Key (`companies.id`) | **NO** | Multi-tenant legal entity boundary. | Top-level Balance Sheet, Statutory P&L, IRD VAT Returns. |
| `branch_id` | Foreign Key (`branches.id`) | **Conditional** (Mandatory on P&L accounts, optional on Balance Sheet equity) | Operating location / Profit Center segmentation. | Branch P&L, Retail Outlet Contribution Margin, Segment Reporting. |
| `cost_center_id` | Categorical / FK | Yes | Sub-allocation within a factory (e.g., Sole Cutting, Stitching, Lasting). | Departmental variance analysis, overhead absorption. |
| `party_type` | Enum (`CUSTOMER`, `SUPPLIER`, `WORKER`, `FRANCHISE`) | Yes | Identifies subledger party for control account lines. | Subledger reconciliation (GL Control vs Subledger Schedule). |
| `party_id` | Integer | Yes | ID of specific client, supplier, or worker. | Open-item tracking, party-level statement of account. |
| `source_doc_type` | Enum (`INVOICE`, `GRN`, `PAYMENT`, `PAYROLL`, `TRANSFER`, `JOURNAL`) | **NO** | Type of operational document initiating the entry. | Audit trails, automated reverse lookups. |
| `source_doc_id` | Integer / String | **NO** | Primary key or voucher number of originating document. | Idempotency enforcement, bidirectional document linking. |

---

## 3. General Ledger Data Model Specification

The General Ledger is designed around immutable, append-only records with integer-paisa financial precision.

```
+---------------------------------------------------------------------------------------------------+
|                                          FiscalYear                                               |
|  - id, company_id, code ("2082/83"), start_date_bs, end_date_bs, start_date_ad, end_date_ad      |
|  - is_closed, closed_at, closed_by_id                                                             |
+---------------------------------------------------------------------------------------------------+
                                                  | 1:N
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                         FiscalPeriod                                              |
|  - id, fiscal_year_id, period_num (1..12: Shrawan..Ashad), name ("2083-Bhadra"), is_locked        |
+---------------------------------------------------------------------------------------------------+
                                                  | References
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                         JournalEntry                                              |
|  - id, company_id, entry_number ("JE-2083-00042"), date_ad, date_bs, period_id                    |
|  - status ("DRAFT", "POSTED", "REVERSED"), posted_at, posted_by_id                                |
|  - source_doc_type, source_doc_ref, idempotency_key (UNIQUE)                                      |
|  - total_debit_paisa, total_credit_paisa (MUST BE EQUAL)                                          |
|  - is_reversal, reversal_of_entry_id (nullable self-reference)                                    |
+---------------------------------------------------------------------------------------------------+
                                                  | 1:N
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                          JournalLine                                              |
|  - id, entry_id, account_id, branch_id (nullable), line_number (1..N)                              |
|  - debit_paisa (BigInteger >= 0), credit_paisa (BigInteger >= 0)                                  |
|  - CHECK: (debit_paisa > 0 AND credit_paisa == 0) OR (credit_paisa > 0 AND debit_paisa == 0)      |
|  - party_type, party_id, description                                                              |
+---------------------------------------------------------------------------------------------------+
                                                  | References
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                            Account                                                |
|  - id, company_id, code ("1110"), name ("Cash on Hand - Birgunj"), account_type (ASSET, etc.)     |
|  - is_control_account (Boolean), normal_balance ("DEBIT" / "CREDIT"), is_active                   |
+---------------------------------------------------------------------------------------------------+
```

### 3.1 Proposed Database Tables & Column Definitions

#### 1. `fiscal_years`
- `id`: `Integer`, Primary Key.
- `company_id`: `Integer`, Foreign Key to `companies.id`, NOT NULL.
- `code`: `String(20)`, NOT NULL (e.g., `"2082/83"`).
- `start_date_ad`: `Date`, NOT NULL.
- `end_date_ad`: `Date`, NOT NULL.
- `start_date_bs`: `String(10)`, NOT NULL (e.g., `"2082-04-01"`).
- `end_date_bs`: `String(10)`, NOT NULL (e.g., `"2083-03-31"`).
- `is_closed`: `Boolean`, default `False`, NOT NULL.
- `closed_at`: `DateTime(timezone=True)`, Nullable.
- `closed_by_id`: `Integer`, Foreign Key to `users.id`, Nullable.
- *Constraints:* `UniqueConstraint("company_id", "code")`.

#### 2. `fiscal_periods`
- `id`: `Integer`, Primary Key.
- `fiscal_year_id`: `Integer`, Foreign Key to `fiscal_years.id`, NOT NULL.
- `period_number`: `Integer`, NOT NULL (1 for Shrawan, 12 for Ashad).
- `name`: `String(50)`, NOT NULL (e.g., `"Shrawan 2082"`).
- `start_date_ad`: `Date`, NOT NULL.
- `end_date_ad`: `Date`, NOT NULL.
- `is_locked`: `Boolean`, default `False`, NOT NULL.
- *Constraints:* `UniqueConstraint("fiscal_year_id", "period_number")`.

#### 3. `accounts` (Chart of Accounts)
- `id`: `Integer`, Primary Key.
- `company_id`: `Integer`, Foreign Key to `companies.id`, NOT NULL.
- `code`: `String(32)`, NOT NULL (e.g., `"1110"`, `"4110"`).
- `name`: `String(255)`, NOT NULL.
- `account_type`: `String(32)`, NOT NULL (`ASSET`, `LIABILITY`, `EQUITY`, `REVENUE`, `EXPENSE`).
- `parent_account_id`: `Integer`, Foreign Key to `accounts.id`, Nullable (Hierarchical Rollup).
- `is_control_account`: `Boolean`, default `False`, NOT NULL (If True, direct manual journals are prohibited; entries must originate from specialized subledgers).
- `subledger_type`: `String(32)`, Nullable (`CUSTOMER_AR`, `SUPPLIER_AP`, `INVENTORY`, `WORKER_PAYROLL`, `BANK`, `VAT`).
- `normal_balance`: `String(10)`, NOT NULL (`DEBIT` or `CREDIT`).
- `is_active`: `Boolean`, default `True`, NOT NULL.
- *Constraints:* `UniqueConstraint("company_id", "code")`.

#### 4. `journal_entries`
- `id`: `Integer`, Primary Key.
- `company_id`: `Integer`, Foreign Key to `companies.id`, NOT NULL.
- `entry_number`: `String(64)`, NOT NULL (e.g., `"JE-2083-00042"`).
- `entry_date_ad`: `Date`, NOT NULL.
- `entry_date_bs`: `String(10)`, NOT NULL.
- `period_id`: `Integer`, Foreign Key to `fiscal_periods.id`, NOT NULL.
- `status`: `String(20)`, default `"DRAFT"`, NOT NULL (`DRAFT`, `POSTED`, `REVERSED`).
- `source_doc_type`: `String(32)`, NOT NULL (`SALES_INVOICE`, `CREDIT_NOTE`, `PURCHASE_GRN`, `PAYMENT_RECEIPT`, `SUPPLIER_PAYMENT`, `PAYROLL_RUN`, `STOCK_ADJUSTMENT`, `MANUAL_JOURNAL`).
- `source_doc_id`: `String(64)`, NOT NULL.
- `idempotency_key`: `String(128)`, NOT NULL (Compound hash of `company_id` + `source_doc_type` + `source_doc_id` + `event_action`).
- `total_debit_paisa`: `BigInteger`, NOT NULL.
- `total_credit_paisa`: `BigInteger`, NOT NULL.
- `narrative`: `Text`, NOT NULL.
- `is_reversal`: `Boolean`, default `False`, NOT NULL.
- `reversal_of_entry_id`: `Integer`, Foreign Key to `journal_entries.id`, Nullable.
- `posted_at`: `DateTime(timezone=True)`, Nullable.
- `posted_by_id`: `Integer`, Foreign Key to `users.id`, Nullable.
- `created_at`: `DateTime(timezone=True)`, server_default=now().
- *Constraints:*
  - `UniqueConstraint("company_id", "entry_number")`
  - `UniqueConstraint("company_id", "idempotency_key")`
  - `CheckConstraint("total_debit_paisa = total_credit_paisa", name="chk_je_balanced")`
  - `CheckConstraint("total_debit_paisa >= 0", name="chk_je_non_negative")`

#### 5. `journal_lines`
- `id`: `BigInteger`, Primary Key.
- `company_id`: `Integer`, Foreign Key to `companies.id`, NOT NULL.
- `entry_id`: `Integer`, Foreign Key to `journal_entries.id`, NOT NULL.
- `line_number`: `Integer`, NOT NULL.
- `account_id`: `Integer`, Foreign Key to `accounts.id`, NOT NULL.
- `branch_id`: `Integer`, Foreign Key to `branches.id`, Nullable.
- `debit_paisa`: `BigInteger`, default 0, NOT NULL.
- `credit_paisa`: `BigInteger`, default 0, NOT NULL.
- `party_type`: `String(32)`, Nullable (`CUSTOMER`, `SUPPLIER`, `WORKER`, `FRANCHISE`).
- `party_id`: `Integer`, Nullable.
- `description`: `String(255)`, Nullable.
- *Constraints:*
  - `UniqueConstraint("entry_id", "line_number")`
  - `CheckConstraint("(debit_paisa > 0 AND credit_paisa = 0) OR (credit_paisa > 0 AND debit_paisa = 0)", name="chk_line_debit_xor_credit")`
  - `Index("ix_jl_account_date", "company_id", "account_id", "entry_id")`
  - `Index("ix_jl_party", "company_id", "party_type", "party_id")`

---

## 4. Double-Entry Posting Engine Specifications

### 4.1 Strict Mathematical Balancing Invariant
A journal entry **must balance in integer paisa** before it can transition from `DRAFT` to `POSTED`:

$$\sum_{i=1}^{N} \text{line}_i.\text{debit\_paisa} = \sum_{i=1}^{N} \text{line}_i.\text{credit\_paisa}$$

$$\text{Tolerance} = 0 \text{ paisa} \quad (0.00 \text{ NPR})$$

Any posting payload where $\Delta = \sum \text{debits} - \sum \text{credits} \neq 0$ must immediately raise an `UnbalancedJournalError` and abort the surrounding database transaction. Silent absorption, auto-balancing write-offs, or floating-point rounding allowances are strictly prohibited.

### 4.2 Lifecycle State Machine

```
                      +------------------+
                      |      DRAFT       |  (Payload staged, lines verified,
                      +------------------+   not reflected in ledger balances)
                                |
                   Post Event   |  Validation Gates:
                   Validated    |  1. Sum(Debits) == Sum(Credits)
                                |  2. Fiscal Period Open & Unlocked
                                |  3. Accounts Active & Valid
                                |  4. Idempotency Key Unique
                                v
                      +------------------+
                      |      POSTED      |  (IMMUTABLE. Included in all
                      +------------------+   Trial Balance and Financial Reports)
                                |
              Corrective Action |  Strict Rule:
              Required          |  NO in-place UPDATE or DELETE permitted.
                                |  Must generate equal-and-opposite entry.
                                v
                      +------------------+
                      |     REVERSED     |  (Original flagged REVERSED;
                      +------------------+   Paired Reversal Entry created)
```

### 4.3 Closed-Period & Lock Controls
Before any journal entry is posted, the posting engine evaluates the target date against the accounting period calendar:
1. Lookup `FiscalPeriod` matching `entry_date_ad`.
2. Check `fiscal_periods.is_locked == True` or `fiscal_years.is_closed == True`.
3. If locked/closed, reject posting with `ClosedPeriodPostingError(period_name)`.
4. Only users with the statutory role `SUPER_ADMIN` or `CHIEF_ACCOUNTANT` may unlock a period, subject to an immutable audit record in `security_audit_events`.

### 4.4 Idempotency & Duplicate Prevention
To guarantee that network retries or concurrent frontend clicks never post duplicate ledger entries:
1. The engine computes an SHA-256 idempotency key:
   $$\text{idempotency\_key} = \text{hash}( \text{company\_id} \mathbin{\Vert} \text{source\_doc\_type} \mathbin{\Vert} \text{source\_doc\_id} \mathbin{\Vert} \text{event\_action} )$$
2. The database enforces a `UNIQUE(company_id, idempotency_key)` constraint.
3. If an operational handler receives a duplicate request, the engine detects the existing record and returns the already-posted `JournalEntry` without re-posting.

### 4.5 Atomicity With Operational Documents
Financial posting is executed within the **exact same database transaction boundary** as the business event:
- Example: Finalizing an Invoice (`POST /api/v1/invoices/{id}/finalize`):
  1. Acquire pessimistic lock `SELECT FOR UPDATE` on `invoices` row.
  2. Transition invoice status to `FINALIZED`.
  3. Generate and insert `ReceivableEntry` in AR subledger.
  4. Generate and validate balanced `JournalEntry` and `JournalLine` rows in General Ledger.
  5. Atomically commit the transaction. If any step fails, all mutations rollback to savepoint.

### 4.6 Concurrency & Balance Derivation Strategy
To prevent row-locking contention across concurrent transactions updating shared accounts:
- **Decision:** **Derived Balances with Materialized Daily Rollups.**
- Rather than holding a single row-lock on an account balance column during every transaction (which serializes all ERP activity into a bottleneck), account balances are computed as:
  $$\text{Balance}(\text{Account}, T) = \sum \text{Debit Lines} - \sum \text{Credit Lines} \quad (\text{for } \text{status} = \text{'POSTED'})$$
- For high-speed reporting, an asynchronous worker maintains a materialized summary table `account_period_balances` updated after commit. In the event of an inconsistency, the materialized cache can be wiped and re-derived from immutable journal lines with zero data loss.

---

## 5. Authorization & Audit Trail Requirements

### 5.1 Role-Based Financial Access Control (RBAC)
Financial actions are governed by strict capability boundaries:

| Role | Create Draft Journal | Post Operational Journal | Post Manual Adjusting Journal | Close / Lock Period | Void / Reverse Journal | View GL & Financial Reports |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `BILLING_OPERATOR` | Yes (System) | Auto (Sales) | No | No | No | No (Subledger only) |
| `INVENTORY_MANAGER`| Yes (System) | Auto (Stock) | No | No | No | No (Stock values only) |
| `BRANCH_MANAGER`   | No | Auto (Branch Exp) | No | No | No | Branch P&L only |
| `ACCOUNTANT`       | Yes | Yes | Yes | No | Yes (With approval) | Full GL & Financials |
| `CHIEF_ACCOUNTANT` | Yes | Yes | Yes | Yes | Yes | Full Company & Consolidated |
| `SUPER_ADMIN`      | Yes | Yes | Yes | Yes | Yes | Full System Audit |

### 5.2 Immutable Financial Audit Trail
Every posted journal captures:
- `posted_by_id`: User ID of authenticated actor.
- `posted_at`: Microsecond-precision UTC timestamp.
- `source_doc_ref`: Fully qualified business reference (e.g., `INV-2083-00124`).
- `client_ip` and `request_id`: Captured in `security_audit_events`.
- For reversal entries: `reversal_of_entry_id` pointing directly to the original entry, with mandatory `reversal_reason`.
