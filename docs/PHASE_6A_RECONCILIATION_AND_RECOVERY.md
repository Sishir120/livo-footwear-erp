# LIVO FOOTWEAR ERP — PHASE 6A: RECONCILIATION, RECOVERY & INTEGRITY SPECIFICATION

**Status:** ARCHITECTURAL SPECIFICATION & SYSTEM RECONCILIATION CONTRACT  
**Version:** 1.0.0  
**Phase:** 6A (Specification-Only)  
**Target Systems:** LIVO Footwear ERP Data Integrity, General Ledger Engine & Audit Controls  
**Mathematical Invariant:** Zero-Tolerance Integrity ($\Delta = 0 \text{ paisa}$)  

---

## 1. General Ledger vs. Subledger Reconciliation Architecture

A primary duty of the General Ledger engine is to verify that control account balances in the General Ledger match the sum of open items in specialized operational subledgers.

```
+----------------------------------------------------------------------------------------------------+
|                                    DOUBLE-ENTRY GENERAL LEDGER                                     |
|                               (JournalEntry / JournalLine Tables)                                  |
+----------------------------------------------------------------------------------------------------+
        |                            |                           |                          |
        | GL Control 1210            | GL Control 2110           | GL Control 1310-1360     | GL Control 2210
        | (Accounts Receivable)      | (Accounts Payable)        | (Inventory Valuation)    | (Wages Payable)
        v                            v                           v                          v
+-----------------------+    +-----------------------+   +-----------------------+  +-----------------------+
|  AR SUBLEDGER         |    |  AP SUBLEDGER         |   |  INVENTORY SUBLEDGER  |  |  PAYROLL SUBLEDGER    |
|  `receivable_entries` |    |  `supplier_entries`   |   |  `stock_movements`    |  |  `worker_monthly_     |
|  (Client Open Items)  |    |  (Vendor Invoices)    |   |  & `raw_material_     |  |   records`             |
|                       |    |                       |   |   movements`          |  |  (Unpaid Net Pay)     |
+-----------------------+    +-----------------------+   +-----------------------+  +-----------------------+
```

---

## 2. Formal Reconciliation Invariants & Mathematical Formulations

### 2.1 Control Invariant 1: General Ledger vs. Accounts Receivable Subledger
The posted balance of Account `1210 Accounts Receivable - Wholesale` must equal the net open balance of all active client receivables:

$$\text{GL\_Balance}(1210) = \sum_{c \in \text{Clients}} \text{AR\_Subledger\_Balance}(c)$$

$$\text{AR\_Subledger\_Balance}(c) = \sum_{e \in \text{receivable\_entries}(c)} (e.\text{direction} \times e.\text{amount\_paisa})$$

$$\Delta_{\text{AR}} = \text{GL\_Balance}(1210) - \sum \text{AR\_Subledger\_Balance}(c) \equiv 0 \text{ paisa}$$

- **Automated Check:** Run nightly at 00:00 NPT.
- **Tolerance:** 0 paisa. If $\Delta_{\text{AR}} \neq 0$, the engine raises a `P1_FINANCIAL_INVARIANT_ALERT`.

---

### 2.2 Control Invariant 2: General Ledger vs. Accounts Payable Subledger
The posted balance of Account `2110 Accounts Payable - Material Suppliers` must equal the sum of unpaid supplier bills:

$$\text{GL\_Balance}(2110) = \sum_{s \in \text{Suppliers}} \text{AP\_Subledger\_Balance}(s)$$

$$\Delta_{\text{AP}} = \text{GL\_Balance}(2110) - \sum \text{AP\_Subledger\_Balance}(s) \equiv 0 \text{ paisa}$$

---

### 2.3 Control Invariant 3: General Ledger vs. Inventory Valuation Subledger
For each inventory account (Raw Materials `1310-1330`, Finished Goods `1350-1360`), the General Ledger debit balance must match the physical inventory valuation derived from item lot costs or weighted-average manufacturing rates:

$$\text{GL\_Balance}(1310) = \sum_{r \in \text{RawMaterials}} \text{CurrentStock}(r) \times \text{WeightedCostPerUnitPaisa}(r)$$

$$\text{GL\_Balance}(1350) = \sum_{p \in \text{Products}} \text{WarehouseStock}(p, \text{BirgunjFactory}) \times \text{StandardManufacturingCostPaisa}(p)$$

$$\Delta_{\text{INV}} \equiv 0 \text{ paisa}$$

---

### 2.4 Control Invariant 4: General Ledger vs. Bank Reconciliation
The balance of Account `1150 Nabil Bank` must equal the bank statement balance adjusted for uncredited deposits and unpresented cheques:

$$\text{GL\_Balance}(1150) + \text{Unpresented Cheques} - \text{Uncredited Deposits} = \text{Bank Statement Balance}$$

---

### 2.5 Control Invariant 5: General Ledger vs. Payroll Liabilities
The balance of Account `2210 Wages & Salaries Payable` must equal the sum of finalized monthly payroll records in `status = 'PENDING'`:

$$\text{GL\_Balance}(2210) = \sum_{w \in \text{WorkerRecords}} w.\text{net\_paid\_paisa} \quad [\text{for } w.\text{status} = \text{'PENDING'}]$$

$$\Delta_{\text{PAYROLL}} \equiv 0 \text{ paisa}$$

---

### 2.6 Control Invariant 6: General Ledger vs. Fixed Asset Register
The gross balance of Account `1500 Fixed Assets` and contra-account `1519-1549 Accumulated Depreciation` must match the sum of historical cost and accumulated depreciation in `fixed_assets`:

$$\text{GL\_Balance}(1510 + 1520 + 1530 + 1540) = \sum_{a \in \text{fixed\_assets}} a.\text{purchase\_cost\_paisa}$$

$$\Delta_{\text{ASSETS}} \equiv 0 \text{ paisa}$$

---

## 3. Crash Recovery, Idempotency & Posting Boundary Architecture

### 3.1 Strict Transaction Boundary & Savepoints
To prevent partial postings where an operational document transitions but its journal fails (or vice versa):
```python
# Execution Contract for All Financial Handlers
with db.begin_nested(): # PostgreSQL SAVEPOINT
    try:
        # 1. Acquire pessimistic locks on operational documents
        # 2. Transition operational state (e.g., invoice.status = 'FINALIZED')
        # 3. Create subledger records (e.g., ReceivableEntry)
        # 4. Generate JournalEntry and JournalLine rows
        # 5. Assert: sum(lines.debit_paisa) == sum(lines.credit_paisa)
        # 6. Insert JournalEntry with UNIQUE(company_id, idempotency_key)
    except Exception as exc:
        # Automatic rollback to savepoint; zero partial state persisted
        logger.error("Financial posting failed: %s", exc)
        raise
```

### 3.2 Interrupted Posting & Idempotent Retry Protocol
In distributed environments, a network timeout can occur after the database commits but before the client receives the HTTP response:
1. **Idempotency Key Verification:**
   - Every posting request carries an authoritative idempotency key derived from the source voucher.
   - If a retry arrives with the same idempotency key, PostgreSQL throws a unique constraint violation (`uq_je_company_idempotency_key`).
2. **Deterministic Resolution:**
   - The engine catches the violation, queries the existing posted `journal_entries` record, and returns the existing entry ID with status code `200 OK` (or `201 Created`).
   - No duplicate journal lines or subledger mutations are ever created.

---

## 4. Disaster Recovery & Post-Restore Verification Runbook

### 4.1 Automated Nightly Backup & WAL Archiving
- Point-in-time recovery (PITR) enabled via continuous PostgreSQL Write-Ahead Log (WAL) archiving.
- Daily full logical dumps generated via `pg_dump -Fc` and validated with automated test restores.

### 4.2 Post-Restore Integrity Verification Runbook
Whenever a database backup is restored, the following verification suite must execute and pass before traffic is routed to the application:

1. **Step 1: Universal Ledger Balance Check:**
   $$\text{Assert } \sum \text{All Debit Lines} - \sum \text{All Credit Lines} = 0 \text{ paisa across entire database.}$$
2. **Step 2: Subledger Reconciliation Suite:**
   Execute automated reconciliation queries for Invariants 1 through 6 ($\Delta_{\text{AR}}, \Delta_{\text{AP}}, \Delta_{\text{INV}}, \Delta_{\text{PAYROLL}}, \Delta_{\text{ASSETS}}$).
3. **Step 3: Document Sequence Gap Check:**
   Verify that invoice sequences (`sequence_number`) and journal entry numbers (`entry_number`) have no unexpected gaps or duplicates.
4. **Step 4: Immutability Audit:**
   Verify that zero `journal_entries` in `POSTED` status have `updated_at > created_at`.
5. **Step 5: Sign-Off:**
   If all 5 steps return `0 discrepancies`, the database is certified healthy and application services are opened.
