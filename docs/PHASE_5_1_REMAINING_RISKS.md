# LIVO FOOTWEAR ERP — PHASE 5.1: REMAINING RISKS & DECISION REGISTER

**Document Version:** 1.0.0  
**Audit Date:** October 15, 2026  
**Audited Subsystems:** Multi-Location Branches, Warehouses, Stock Transfers, RBAC, Database Concurrency  
**Status:** ACTIVE AUDIT REGISTER  

---

## 1. Risk Register Summary

| Risk ID | Title / Subsystem | Severity | Business Impact | Verification Status | Next Action Needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-51-01** | User Authorization Lack of Branch-Level Scoping | **MEDIUM** | Store clerks and showroom managers can view other showroom operational records within the same company. | **VERIFIED (Gap Documented)** | Client approval for `user_branches` M2M table in Phase 6. |
| **RISK-51-02** | Absence of Formal Double-Entry General Ledger (GL) | **HIGH** | Operational inventory & receivable ledgers exist, but formal balanced Dr/Cr journal vouchers do not. | **VERIFIED (Deferred by Design)** | Implement Phase 6 Double-Entry GL architecture. |
| **RISK-51-03** | Nepal VAT Act 2052 Consignment Tax & Delivery Challan Ambiguity | **HIGH** | Risk of IRD non-compliance if franchise transfers are billed as inter-branch stock transfers rather than taxable sales. | **VERIFIED (Regulatory Gap)** | Formal written consultation with licensed Nepal Chartered Accountant. |
| **RISK-51-04** | SQLite In-Process Concurrency Limitation on Test Runners | **LOW** | Thread lock contention and SQLite read-snapshot staleness on local developer environments during massive test suites. | **VERIFIED (PostgreSQL Mitigated)** | Ensure CI runs against real PostgreSQL; maintain in-process mutexes for local development. |
| **RISK-51-05** | Franchise Settlement Subledger & Margin Reconciliation | **MEDIUM** | Royalty/commission rates for franchise showrooms cannot be settled automatically against sales. | **VERIFIED (Deferred to Phase 6)** | Design Franchise Settlement Engine in Phase 6 after client review. |

---

## 2. Detailed Risk Profiles

### RISK-51-01: User Authorization Lack of Branch-Level Scoping
- **Severity:** Medium
- **Subsystem:** RBAC / Identity (`backend/app/models/user.py`, `backend/app/api/deps.py`)
- **Evidence:**
  - Inspection of `User` model shows fields: `id`, `company_id`, `username`, `email`, `password_hash`, `role` (`admin`, `editor`, `viewer`), `active`.
  - There is **no `branch_id`** or `user_branches` mapping.
  - In `branches.py` and `transfers.py`, authorization is enforced via `require_editor` or `require_viewer`. Both dependencies verify `current_user.company_id == resource.company_id`.
- **Business Impact:**
  - If a company operates showrooms in Kathmandu, Pokhara, and Butwal, an `editor` at the Pokhara showroom can view Kathmandu transfer slips, inventory levels, and stock movements.
  - This is acceptable for centralized headquarters staff and small enterprise teams, but unacceptable for decentralized retail cashier staff.
- **Recommended Action:**
  - Do NOT inject arbitrary columns without client sign-off.
  - In Phase 6, introduce a `user_branches` association table:
    ```python
    user_branches = Table(
        "user_branches",
        Base.metadata,
        Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        Column("branch_id", Integer, ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True)
    )
    ```
  - Introduce an optional `@require_branch_access(branch_id)` dependency for POS and branch-specific dispatch operations.

---

### RISK-51-02: Absence of Formal Double-Entry General Ledger (GL)
- **Severity:** High
- **Subsystem:** Financial Accounting / Chart of Accounts
- **Evidence:**
  - Audited `backend/app/models/`: Models include `Invoice`, `ReceivableEntry`, `Expense`, `StockMovement`, `Product`, `Warehouse`, `StockTransfer`.
  - There is NO `Account`, `JournalEntry`, `JournalLine`, or `FiscalPeriod` model.
  - Invoices automatically credit Accounts Receivable subledgers, but no debit/credit double-entry vouchers are posted.
- **Business Impact:**
  - Balance Sheet, Profit & Loss (Income Statement), and Trial Balance cannot be generated directly from a formal General Ledger.
  - Financial reporting currently relies on operational subledger aggregation.
- **Recommended Action:**
  - Keep operational inventory and financial subledgers decoupled until Phase 6.
  - Design a formal 5-pillar Chart of Accounts (Assets, Liabilities, Equity, Revenue, Expenses) with Nepal standard formatting in Phase 6.

---

### RISK-51-03: Nepal VAT Act 2052 Consignment Tax & Delivery Challan Ambiguity
- **Severity:** High (Regulatory / Legal Compliance)
- **Subsystem:** Tax & Statutory Compliance (Inland Revenue Department — IRD Nepal)
- **Evidence:**
  - Nepal Value Added Tax Act, 2052 (1996) Section 14 and VAT Rules 2053 require registered entities transferring goods between different physical premises to carry an approved Delivery Challan (चलान - Schedule 7/8).
  - Furthermore, transferring goods to an independent franchisee (with a separate PAN/VAT number) constitutes a taxable supply requiring a VAT Invoice, whereas transfer to a company-owned showroom under the same PAN requires an internal transfer challan.
  - Currently, `StockTransfer` issues an operational transfer document (`TRF-XXXXXX`), but does not distinguish between tax invoice generation and internal delivery challan.
- **Business Impact:**
  - Risk of road inspection penalties by the Department of Revenue Investigation (DRI) during highway transit between Kathmandu and provinces if vehicles lack authorized IRD Delivery Challans.
- **Recommended Action:**
  - Engage the client's appointed Nepal Chartered Accountant (CA).
  - Implement a dedicated "Delivery Challan" printable format with QR code and vehicle/driver registration numbers.

---

### RISK-51-04: SQLite In-Process Concurrency Limitation on Test Runners
- **Severity:** Low (Development / CI Environment)
- **Subsystem:** Database Engine / Locking Layer (`backend/app/core/locks.py`)
- **Evidence:**
  - Local unit tests running against SQLite utilize in-process `threading.RLock` objects because SQLite does not natively support transaction-scoped advisory locks (`pg_advisory_xact_lock`) or row locks (`SELECT ... FOR UPDATE`).
  - During heavy test execution (480+ consecutive tests), SQLite connection pool saturation can cause transient read snapshot staleness across concurrently spawned threads.
- **Business Impact:**
  - Production deployments use managed PostgreSQL (e.g. Neon, RDS, Cloud SQL) where advisory locks and row-level locks are strictly honored across separate Uvicorn workers and container replicas.
  - Developers on SQLite may occasionally experience flakiness in multi-threaded test cases if connection pool limits are reached.
- **Recommended Action:**
  - Ensure CI/CD pipelines run integration and concurrency test suites against an isolated PostgreSQL container or service instance.
  - Maintain `db.rollback()` and `db.expire_all()` in lock acquisition routines to safeguard SQLite test runners.

---

### RISK-51-05: Franchise Settlement Subledger & Margin Reconciliation
- **Severity:** Medium
- **Subsystem:** Commercial Contracts / Settlement
- **Evidence:**
  - `Branch` model supports `type = Column(String(50), default="COMPANY_OWNED")` (e.g. `COMPANY_OWNED`, `FRANCHISE`).
  - However, no pricing tiers, wholesale discount schedules, or royalty percentage fields are modeled yet.
- **Business Impact:**
  - If a franchise branch sells footwear, the margin split between the manufacturing parent company and the franchise operator cannot be computed or settled automatically.
- **Recommended Action:**
  - Defer franchise settlement logic until Phase 6, after client signs off on the specific commercial arrangement (consignment stock vs wholesale purchase vs commission agency).

---

## 3. Decision Log Required From Client

Prior to commencement of Phase 6, the client executive sponsor must provide written decisions on the following questions:

1. **User Scoping:** Shall branch staff (cashiers, stock keepers) be locked to their assigned physical showroom, or should all company employees maintain cross-branch visibility?
2. **Franchise Model:** Are franchise showrooms treated as external wholesale customers (B2B Tax Invoicing with immediate A/R) or as consignment partners (stock transferred with internal delivery challans, and royalties settled monthly)?
3. **General Ledger Rollout:** Shall the Phase 6 Double-Entry General Ledger run in parallel with existing subledgers (shadow mode) or replace manual spreadsheet accounting immediately?
