# LIVO FOOTWEAR ERP — DATABASE & API PERFORMANCE AUDIT
**Checkpoint 12 — Observability, Performance, Reliability & Operational Readiness**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Executive Summary

This audit evaluates the database query topology, anti-patterns (such as N+1 queries and unbounded responses), index strategies, and connection pool sizing for high-volume multi-tenant footwear manufacturing operations.

---

## 2. Resolved Anti-Patterns & Query Optimization

### 2.1 Resolution of N+1 Query in Sales Orders
* **Prior Anti-Pattern:** In `GET /api/v1/sales/orders`, the application queried all sales orders for a tenant, and then inside an iterative loop, executed an individual database query for each order's line items (`db.query(SalesItem).filter(SalesItem.sales_order_id == ord.id, ...)`). For 250 orders, this triggered 1 + 250 = 251 database queries.
* **Remediation:** Refactored in [`backend/app/api/v1/sales.py`](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/sales.py#L70-L115) to batch-fetch all line items for the entire page in a single query:
  ```python
  all_items = db.query(SalesItem).filter(
      SalesItem.sales_order_id.in_(order_ids),
      SalesItem.company_id == current_user.company_id
  ).all()
  ```
  *Benefit:* Query count reduced from **O(N)** to **O(1)** (exactly 2 queries regardless of page size).

### 2.2 Bounded Collection Pagination
Unbounded collection queries pose severe Out-Of-Memory (OOM) and latency threats in production. Bounded pagination parameters (`limit` and `offset`) have been introduced across all primary collection endpoints:

| Endpoint | Prior Behavior | Hardened Production Behavior | Default Limit | Maximum Limit |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/v1/sales/orders` | Unbounded `repo.get_all()` | Bounded pagination with batch item loading | 100 | 500 |
| `GET /api/v1/sales/clients` | Unbounded `repo.get_all()` | Bounded pagination | 200 | 500 |
| `GET /api/v1/invoices` | Unbounded `repo.get_all()` | Bounded pagination | 100 | 500 |
| `GET /api/v1/stock/movements`| Unbounded `repo.get_all()` | Bounded pagination | 100 | 500 |
| `GET /api/v1/stock/ledger` | Paginated | Paginated with window function running balance | 50 | 500 |

---

## 3. Stock Snapshot O(1) Scalability Architecture

To prevent historical stock movement ledger queries from degrading as transaction volume expands, LIVO ERP implements periodic stock snapshot materialization ([`backend/app/api/v1/stock.py`](file:///d:/Antigravity/Footwear%20app/backend/app/api/v1/stock.py#L262-L345)):

$$\text{Current Stock} = \text{Latest Snapshot Balance} + \sum_{i > \text{last\_movement\_id}} (\text{direction} \times \text{quantity})$$

* **Query Cost:** Scanning only movements created after the latest snapshot instead of replaying the entire history of the company since inception.
* **Fallback:** Gracefully sums all movements if no snapshot exists yet for a newly created SKU.

---

## 4. Index Topology & Cost-Benefit Analysis

| Table | Index Identifier | Columns | Query Accelerated | Write Cost | Uniqueness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `stock_movements` | `ix_stock_ledger_lookup` | `company_id, product_id, size, created_at` | Stock card balance & ledger audit queries | Low (single B-tree insert per movement) | No |
| `receivable_entries`| `ix_ar_party_date` | `company_id, client_id, occurred_at` | Client ledger statement & aging reports | Low | No |
| `idempotency_records`| `ix_idempotency_company_key`| `company_id, idempotency_key` | Sub-millisecond duplicate mutation check | Minimal (1 row per mutation) | Yes |
| `idempotency_records`| `ix_idempotency_status_locked`| `status, locked_until` | Stale lease recovery & background reap jobs | Minimal | No |
| `invoices` | `uq_invoice_company_sequence` | `company_id, sequence_number` | Monotonic invoice sequence allocation | Low | Yes |
| `invoices` | `uq_invoice_company_invoice_number` | `company_id, invoice_number` | Document retrieval & tax auditing | Low | Yes |

---

## 5. Connection Pool Capacity Sizing Formula

The relationship between application instances, pool sizing, and database capacity is governed by:

$$\text{Total Connections} = \text{Application Instances} \times (\text{pool\_size} + \text{max\_overflow}) \le \text{PostgreSQL max\_connections}$$

In [`backend/app/db/session.py`](file:///d:/Antigravity/Footwear%20app/backend/app/db/session.py), connection pooling parameters are configurable via environment variables with safe production defaults:
* `DB_POOL_SIZE`: 15 (default)
* `DB_MAX_OVERFLOW`: 15 (default)
* `DB_POOL_TIMEOUT`: 10 seconds
* `DB_POOL_RECYCLE`: 1800 seconds (30 minutes)

**Capacity Verification:**
* For 3 running application replicas: $3 \times (15 + 15) = 90 \le 100\text{ (Standard Neon / RDS max\_connections)}$, leaving a safe margin of 10 connections for administrative access and migration runners.
