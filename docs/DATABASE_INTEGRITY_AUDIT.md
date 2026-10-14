# LIVO FOOTWEAR ERP — DATABASE INTEGRITY AUDIT
**Checkpoint 11 — Database Integrity, Migrations, Backups & Disaster Recovery**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Executive Summary & Architecture Overview

LIVO Footwear ERP is an industrial multi-tenant footwear manufacturing enterprise system designed to guarantee strict data integrity across inventory mutations, financial postings, production batches, and offline device synchronization.

### 1.1 Database Engine & Dialects
* **Production Database:** PostgreSQL 15+ (Hosted on Neon Serverless Postgres with automatic SSL enforcement, connection pooling, and continuous point-in-time archival).
* **Local Development & Integration Testing:** SQLite 3 (configured with Write-Ahead Logging `WAL`, 30s busy timeout, and enforced connection-level foreign keys via `PRAGMA foreign_keys = ON`).

### 1.2 Connection & Session Management
Database connections and ORM sessions are managed in [`backend/app/db/session.py`](file:///d:/Antigravity/Footwear%20app/backend/app/db/session.py):
* **Connection Pooling:**
  * `pool_size`: 20 persistent connections.
  * `max_overflow`: 30 burst connections.
  * `pool_timeout`: 10 seconds.
  * `pool_recycle`: 1800 seconds (30 minutes) to eliminate stale socket connections.
  * `pool_pre_ping`: `True` (active liveness probe before releasing connection from pool).
  * `sslmode`: `require` enforced automatically for non-local PostgreSQL endpoints.
* **Session Lifecycle:**
  * `autocommit`: `False` (all mutations require explicit transactional commit).
  * `autoflush`: `False` (prevents premature uncommitted queries from dirtying transaction state).
  * `expire_on_commit`: `False` (prevents unnecessary re-querying and detached attribute errors after commits).
  * `get_db()`: FastAPI dependency with `try...finally: db.close()`, guaranteeing no open leaked transactions.

---

## 2. Business-Critical State Classification & Relational Topology

All business state in LIVO Footwear ERP is rigorously classified into six structural data tiers:

```
+---------------------------------------------------------------------------------------------------+
|                                  LIVO ERP DATA TOPOLOGY                                           |
+---------------------------------------------------------------------------------------------------+
|  1. MASTER DATA (Tenant Root & Entities)                                                          |
|     - companies (Tenant Root)                                                                     |
|     - users (Authentication, Roles: superadmin, admin, manager, editor, viewer)                  |
|     - warehouses (Physical Storage Locations)                                                    |
|     - products & raw_materials (SKUs, Bill of Materials, Specifications)                          |
|     - clients & suppliers (Business Partners, Credit Limits)                                      |
|     - workers (Floor Employees, Wage Rates)                                                       |
+---------------------------------------------------------------------------------------------------+
|  2. TRANSACTIONAL DOCUMENTS (Negotiated Business Agreements)                                      |
|     - sales_orders & sales_items (Order Booking, Status: pending, delivered, cancelled)           |
|     - purchase_orders & purchase_items (Procurement Commitments)                                  |
|     - invoices & invoice_sequences (Tax-Compliant Invoices, Continuous Numbering)                 |
|     - production_batches & batch_material_consumptions (Manufacturing Work Orders)                 |
+---------------------------------------------------------------------------------------------------+
|  3. IMMUTABLE FINANCIAL & INVENTORY LEDGERS (Double-Entry & Stock Cards)                          |
|     - stock_movements (Append-only physical stock mutations: direction +1/-1)                     |
|     - receivable_entries (Append-only Accounts Receivable ledger: direction +1/-1, amount_paisa)  |
|     - payment_allocations (Settlement links between payments and invoices in exact paisa)        |
|     - wage_payments (Payroll Disbursements)                                                       |
+---------------------------------------------------------------------------------------------------+
|  4. DERIVED STATE (Computed strictly from Ledger Replay)                                         |
|     - Physical Stock On-Hand = Sum(quantity * direction) per product/warehouse/size               |
|     - Debtor Outstanding Balance = Sum(amount_paisa * direction) per client                       |
+---------------------------------------------------------------------------------------------------+
|  5. AUDIT & TELEMETRY                                                                             |
|     - audit_log (Administrative mutation audit trail with user identity and JSON payload)         |
|     - telemetry_logs (Performance, latency, error telemetry)                                     |
+---------------------------------------------------------------------------------------------------+
|  6. SYNCHRONIZATION & IDEMPOTENCY METADATA                                                        |
|     - idempotency_records (HTTP POST/PUT idempotency cache, scoped by tenant)                     |
|     - production_sync_logs (Offline sync tracking, deduplication fingerprints)                    |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Transaction Boundaries & Mutation Atomicity

### 3.1 Multi-Step Transaction Invariants
In LIVO ERP, financial and inventory state changes cannot commit partially. The following mutation groups are strictly atomic within single database transactions:

1. **Invoice Issuance + Inventory Deduction + Accounts Receivable Posting:**
   ```text
   BEGIN TRANSACTION
     1. Verify sales order status and credit limit.
     2. Allocate gapless sequential invoice number via SELECT FOR UPDATE on invoice_sequences.
     3. Insert record into invoices.
     4. Insert item rows into sales_items.
     5. Post stock deduction into stock_movements (direction = -1, SALES_OUT).
     6. Post debit entry into receivable_entries (direction = +1, INVOICE_POSTED, amount_paisa).
   COMMIT
   ```
   *Failure Behavior:* If any step fails (e.g. credit check, stock shortage, DB constraint), the entire session issues a `ROLLBACK`. Zero partial invoices, orphan stock entries, or desynchronized receivable entries can exist.

2. **Payment Receipt + Receivable Credit + Invoice Settlement:**
   ```text
   BEGIN TRANSACTION
     1. Validate client existence and payment currency amount.
     2. Insert credit entry into receivable_entries (direction = -1, PAYMENT_CASH/BANK).
     3. Insert allocation link into payment_allocations (linking payment to open invoice).
     4. Update invoice received_amount / receivable_amount.
   COMMIT
   ```
   *Failure Behavior:* Downstream failures roll back both the payment receipt and all allocations atomically.

3. **Production Batch Completion + Finished Goods Stock Addition + Raw Material Consumption:**
   ```text
   BEGIN TRANSACTION
     1. Update production_batches status to 'COMPLETED'.
     2. Post finished footwear addition into stock_movements (direction = +1, PRODUCTION_IN).
     3. Post raw material deductions for each BOM item consumed into stock_movements.
   COMMIT
   ```

---

## 4. Constraint & Integrity Audit

### 4.1 Foreign Keys & Deletion Safety
Every transactional and ledger record enforces database-level foreign keys. Soft-deactivation is strictly utilized for master data entities rather than physical cascading deletes:

| Table | Foreign Key Column | Target Primary Key | On Delete Behavior | Business Rationale |
| :--- | :--- | :--- | :--- | :--- |
| `users` | `company_id` | `companies.id` | RESTRICT / NO ACTION | Preserves tenant containment. |
| `warehouses` | `company_id` | `companies.id` | RESTRICT / NO ACTION | Warehouse cannot be deleted if movements exist. |
| `products` | `company_id` | `companies.id` | RESTRICT / NO ACTION | SKUs must remain for historical ledger auditing. |
| `stock_movements` | `product_id` | `products.id` | RESTRICT / NO ACTION | **Critical:** Historical stock movements can NEVER be orphan. |
| `stock_movements` | `warehouse_id` | `warehouses.id` | RESTRICT / NO ACTION | Physical movements must identify facility. |
| `stock_movements` | `actor_id` | `users.id` | RESTRICT / NO ACTION | Statutory audit trail of storekeeper/operator. |
| `sales_orders` | `client_id` | `clients.id` | RESTRICT / NO ACTION | Preserves contract counterpart. |
| `invoices` | `sales_order_id`| `sales_orders.id` | RESTRICT / NO ACTION | Every invoice originates from an authorized order. |
| `receivable_entries`| `client_id` | `clients.id` | RESTRICT / NO ACTION | Debtor subledger cannot have orphaned balances. |
| `receivable_entries`| `invoice_id` | `invoices.id` | RESTRICT / NO ACTION | Settlement tracking must link to tax invoice. |
| `receivable_entries`| `actor_id` | `users.id` | RESTRICT / NO ACTION | Financial entries must record operator identity. |
| `payment_allocations`| `payment_entry_id`| `receivable_entries.id`| RESTRICT / NO ACTION | Allocation must reference valid ledger entry. |
| `idempotency_records`| `company_id` | `companies.id` | RESTRICT / NO ACTION | Multi-tenant scoped idempotency cache. |

### 4.2 Database-Enforced Unique Constraints
Multi-tenant uniqueness is enforced at the database schema level (not solely in Python code):

1. **Invoices:**
   * `UniqueConstraint("company_id", "invoice_number", name="uq_invoice_company_invoice_number")`
   * `UniqueConstraint("company_id", "sequence_number", name="uq_invoice_company_sequence")`
2. **Products:**
   * `UniqueConstraint("company_id", "code", name="uq_company_product_code")`
3. **Clients:**
   * `UniqueConstraint("company_id", "code", name="uq_company_client_code")`
4. **Suppliers:**
   * `UniqueConstraint("company_id", "code", name="uq_company_supplier_code")`
5. **Warehouses:**
   * `UniqueConstraint("company_id", "code", name="uq_company_warehouse_code")`
6. **Sales Orders:**
   * `UniqueConstraint("company_id", "order_number", name="uq_company_sales_order_number")`
7. **Idempotency:**
   * `UniqueConstraint("company_id", "idempotency_key", name="uq_idempotency_company_key")`
8. **Users:**
   * `UniqueConstraint("username")` (Global uniqueness)

### 4.3 Check Constraints & Statutory Invariants
* Non-negative quantitative checks: Physical inventory quantities must be strictly positive (`quantity > 0`), with mutation type encoded via `direction` (+1 or -1).
* Non-negative financial amounts: Invoices and allocations require `total_amount >= 0`, `allocated_paisa >= 0`.
* Financial arithmetic: All Accounts Receivable postings use exact integer `BigInteger` `amount_paisa` (100 paisa = 1 NPR), eliminating IEEE 754 floating-point inaccuracies.

---

## 5. Numeric Precision Verification

To protect Checkpoint 6, an exhaustive audit was performed across all model definitions in `backend/app/models/`:

* **Float / REAL / DOUBLE count in models:** 0 (Zero occurrences).
* **Quantitative columns:** Defined as `Numeric` in SQLAlchemy (PostgreSQL `NUMERIC`, Python `Decimal`).
* **Core financial ledgers:** Defined as `BigInteger` storing integer paisa (`amount_paisa`, `allocated_paisa`).
* **API serialization:** Monies formatted with 2 decimal places or exact integer paisa without floating point representation.

---

## 6. Index Topology & Query Performance Audit

The following composite and single-column indexes are active to optimize high-volume queries:

| Index Identifier | Target Table | Columns Indexed | Query Supported |
| :--- | :--- | :--- | :--- |
| `ix_stock_ledger_lookup` | `stock_movements` | `company_id, product_id, size, created_at` | Real-time stock card balance & SKU valuation |
| `ix_ar_party_date` | `receivable_entries` | `company_id, client_id, occurred_at` | Client ledger statement & aging reports |
| `ix_idempotency_company_key`| `idempotency_records`| `company_id, idempotency_key` | Sub-millisecond duplicate request deduplication |
| `ix_idempotency_status_locked`| `idempotency_records`| `status, locked_until` | Stale idempotency lease recovery & reap jobs |
| `ix_invoices_lookup` | `invoices` | `company_id, invoice_number` | Fast invoice retrieval & numbering verification |
| `ix_audit_log_timestamp` | `audit_log` | `timestamp, company_id` | Historical audit compliance querying |

---

## 7. Audit Durability

1. **Transaction Isolation:** Audit events logged via dedicated sessions or completed commits persist independently of subsequent rollbacks in business workflows.
2. **Soft Deactivation:** Deactivating an operator (`active = False`) retains all historical foreign key relationships and audit event history intact.
3. **Immutability:** The `audit_log` table contains no update endpoints in the API surface; records are write-once append-only.
