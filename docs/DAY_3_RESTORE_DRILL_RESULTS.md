# LIVO ERP — Day 3: Isolated PostgreSQL Restore Drill Results

**Execution Date:** 2026-10-16  
**Auditor:** Antigravity Engineering (Automated DR Drill & Integrity Verification)  
**Target Environment:** Isolated Ephemeral PostgreSQL (`embedded_postgres` on dynamic port)  
**Database Isolation:** Strictly disposable databases (`livo_day3_drill_src` and `livo_day3_drill_dst`)  
**Overall Result:** **PASS (100% RECONCILIATION PARITY)**

---

## 1. Executive Summary

An automated, non-destructive disaster recovery drill was executed in an isolated PostgreSQL environment using 100% synthetic evaluation data. No live development databases, production instances, or client records were accessed or modified.

The drill verified:
1. Fresh Alembic schema migration up to head (`024_add_rate_limit_entries`).
2. Multi-domain synthetic ERP mutations across 10 operational domains.
3. Native point-in-time PostgreSQL backup export (`pg_dump` with atomic temporary staging and SHA-256 calculation).
4. Failure test scenarios (non-existent file and truncated/corrupted backup artifact).
5. Restoration into an empty secondary database using `restore_database_backup()`.
6. Deep ledger reconciliation checking referential integrity, physical stock mathematics, accounts receivable subledger continuity, landed cost purchase pricing, FIFO worker advance recovery, and gapless invoice sequencing.
7. Read-only API verification (`/health/ready` and `/health`) against the restored database.

---

## 2. Environment & Test Infrastructure

| Attribute | Specification |
| :--- | :--- |
| **Database Engine** | PostgreSQL 16.x (`embedded_postgres` ephemeral cluster) |
| **Source Database** | `livo_day3_drill_src` (disposable) |
| **Restored Target Database** | `livo_day3_drill_dst` (disposable) |
| **Alembic Revisions Applied** | 24 Revisions (`001_baseline_schema` $\rightarrow$ `024_add_rate_limit_entries`) |
| **Test Suite Executable** | `backend/tests/test_day_3_restore_drill.py` |
| **Working Directory** | `d:\Antigravity\Footwear app` |

---

## 3. Seeded Synthetic Domain Coverage

The source database was populated with representative synthetic records across all core modules:

1. **Company & Operating Structure:** 1 Company (`LIVO_D3`), 1 Head Office Branch (`BR-KTM-MAIN`), 2 Warehouses (`WH-D3-MAIN` and `WH-D3-RETAIL`).
2. **Access Control:** 3 User accounts with distinct RBAC roles (Admin, Editor, Viewer) using bcrypt password hashing.
3. **Procurement & Raw Materials:** 1 Supplier, 2 Raw Materials (Calf Leather kg, Sole pcs), 1 Landed Cost Purchase with 4-column landed costs (carrying-in, import duty, china transit, insurance) totaling NPR 90,000 (9,000,000 paisa).
4. **BOM & Manufacturing:** 1 Finished Product (`ART-D3-BOOT-42`), 2 BOM ingredient rules, 1 completed Production Batch (95 pairs, Chestnut Brown).
5. **Stock Ledger & Transfers:**
   - Production inbound: +95 pairs to `WH-D3-MAIN`.
   - Multi-warehouse transfer: 30 pairs transferred from `WH-D3-MAIN` to `WH-D3-RETAIL` via `StockTransfer` (`TRF-D3-00001`).
   - Net Main Warehouse On-Hand: 65.0 pairs.
   - Net Retail Warehouse On-Hand: 10.0 pairs (after sales dispatch).
   - Global Physical On-Hand: 75.0 pairs.
6. **Sales, Invoicing & Receivables:**
   - 1 Client (`CLI-D3-POKHARA`), 1 Sales Order (`SO-D3-001`) for 20 pairs.
   - 1 Gapless Tax Invoice (`INV-01-00001`) with 13% VAT (Subtotal: 100,000 NPR, VAT: 13,000 NPR, Total: 113,000 NPR).
   - Receivables: Posted invoice (+11,300,000 paisa), cash receipt (-4,000,000 paisa), Net Outstanding AR: 7,300,000 paisa (NPR 73,000.00).
7. **HR & Payroll Ledger:**
   - 1 Active Salary Worker (`WRK-D3-001`).
   - 1 Issued Advance (1,500,000 paisa with 500,000 installment).
   - 1 Recovered Installment (500,000 paisa linked via `parent_advance_id`).
   - Net Reconciled Debt: 1,000,000 paisa.
8. **Fixed Assets, Operating Expenses & Waste:**
   - 1 Machinery Asset (`AST-D3-SOLE-PRESS-01`, NPR 650,000 valuation).
   - 1 Factory Operating Expense (Electricity, NPR 35,000 bank payment).
   - 1 Scrap Waste Record (8.4 kg leather offcuts).

---

## 4. Failure Mode Test Results

| Test Scenario | Induced Condition | Expected Behavior | Observed Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Missing Backup File** | Path pointing to `non_existent_ghost.sql` | Raise `FileNotFoundError` before touching DB | Raised `FileNotFoundError` | **PASSED** |
| **Corrupted SQL Artifact** | File containing syntax errors & truncated DDL | `psql` fails with exit code 3 (`-v ON_ERROR_STOP=1`); reports `"status": "failed"` | Subprocess caught error; returned `"status": "failed"` | **PASSED** |

---

## 5. Ledger Invariant Reconciliation Results

Following restoration of the verified backup into `livo_day3_drill_dst`, deep reconciliation was performed between source and target databases:

| Invariant / Check | Source Baseline | Restored Target | Discrepancy | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Catalog Base Tables** | 25 Tables | 25 Tables | 0 | **PASSED** |
| **Total Record Counts** | 100% Match | 100% Match | 0 | **PASSED** |
| **Schema Revision Head** | `024_add_rate_limit_entries` | `024_add_rate_limit_entries` | 0 | **PASSED** |
| **Global Stock On-Hand** | 75.0 pairs | 75.0 pairs | 0.0 | **PASSED** |
| **Main Factory WH Stock** | 65.0 pairs | 65.0 pairs | 0.0 | **PASSED** |
| **Retail Depot WH Stock** | 10.0 pairs | 10.0 pairs | 0.0 | **PASSED** |
| **Stock Transfer Status** | `RECEIVED` (30 pairs) | `RECEIVED` (30 pairs) | 0 | **PASSED** |
| **Net Accounts Receivable** | 7,300,000 paisa | 7,300,000 paisa | 0 paisa | **PASSED** |
| **Landed Cost Valuation** | 9,000,000 paisa | 9,000,000 paisa | 0 paisa | **PASSED** |
| **Worker Advance Balance** | 1,000,000 paisa | 1,000,000 paisa | 0 paisa | **PASSED** |
| **Fixed Asset Valuation** | 65,000,000 paisa | 65,000,000 paisa | 0 paisa | **PASSED** |
| **Factory Operating Cost** | 3,500,000 paisa | 3,500,000 paisa | 0 paisa | **PASSED** |
| **Scrap Scrap Quantity** | 8.4 kg | 8.4 kg | 0.0 kg | **PASSED** |
| **Readiness Probe (`/ready`)**| HTTP 200 OK | HTTP 200 OK | None | **PASSED** |
| **Backward Health (`/health`)**| Database: healthy | Database: healthy | None | **PASSED** |

---

## 6. Recovery Time & Performance Metrics

- **Backup Generation Time:** $< 0.8$ seconds
- **Restore Time (RTO):** $< 1.2$ seconds
- **Recovery Point Objective (RPO):** Verified to point of backup execution (Near-zero in drill)
- **Artifact SHA-256 Checksum:** Cryptographically verified before and after restore.
- **Resource Cleanup:** Ephemeral databases (`livo_day3_drill_src`, `livo_day3_drill_dst`) and temporary server files unlinked automatically.
