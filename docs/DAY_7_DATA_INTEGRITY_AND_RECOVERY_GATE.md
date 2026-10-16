# LIVO Footwear ERP — Day 7 Data Integrity & Recovery Gate Report

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Standard:** Enterprise Data Integrity & Disaster Recovery Baseline  
**Evaluation Scope:** Controlled 1-Week Cloud Demonstration (Synthetic Data Only)

---

## 1. Executive Summary

Data integrity, transaction boundaries, tenant isolation, and disaster recovery mechanisms were verified through automated test suites and live database drills. Test executions were tracked individually by command, database engine, collected items, and outcomes.

No SQLite results are conflated with PostgreSQL results. Dual-engine distinctions are maintained throughout this audit.

---

## 2. Test Execution Inventory Matrix

| Test Group | Target Domain | Command Executed | Database Engine | Collected | Passed | Failed | Exit Code | Duration |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Group 1** | Stock Transfers & Ledger | `pytest -v tests/test_stock_transfers.py tests/test_stock_ledger.py` | Isolated SQLite (WAL) | 16 | 16 | 0 | `0` | 4.28s |
| **Group 2** | Idempotency & Retries | `pytest -v tests/test_idempotency.py` | Isolated SQLite (WAL) | 12 | 12 | 0 | `0` | 3.06s |
| **Group 3** | RBAC & Cross-Company Tenant Isolation | `pytest -v tests/test_day_2_rbac_hardening.py tests/test_checkpoint_16_tenant_isolation.py` | Isolated SQLite (WAL) | 14 | 14 | 0 | `0` | 2.22s |
| **Group 4** | VAT & Invoice Compliance | `pytest -v tests/test_vat_compliance_and_calculation.py` | Isolated SQLite (WAL) | 12 | 12 | 0 | `0` | 3.82s |
| **Group 5** | HR Sensitive Fields & Document RBAC | `pytest -v tests/test_hr_management.py` | Isolated SQLite (WAL) | 6 | 6 | 0 | `0` | 2.31s |
| **Group 6** | Dual DB + File Recovery Drill | `pytest -v tests/test_day_4_file_and_database_recovery.py` | Isolated Embedded PostgreSQL 16 | 1 | 1 | 0 | `0` | 17.56s |
| **Probe** | Database Unavailability Readiness Probe | Python unit execution (`readiness_check(mock_db_failure)`) | Mocked Connection Drop | 1 | 1 | 0 | `0` | <0.5s |

**Total Regression Items Executed:** **61 distinct tests across 8 suites + 1 probe verification** -> **100% Passed (0 Failures, 0 Skips)**.

---

## 3. Database & Storage Invariants Verified

### 3.1. Stock Ledger Invariants
- Transfers require distinct source and destination warehouses (`same_source_destination_rejected`).
- In-transit cancellation reverses source warehouse stock immediately.
- Final receipt with shortages requires an explicit operator reason.
- Over-receipt attempts are strictly blocked (`over_receipt_attempt_rejected`).

### 3.2. Idempotency & Concurrency Defenses
- Idempotent request replays return cached responses with identical headers.
- Concurrent duplicate mutations with the same `X-Idempotency-Key` produce exactly one database side effect.
- Stale processing leases are recovered cleanly on server timeouts.

### 3.3. Tenant Isolation & Authorization
- Cross-company read, write, and delete attacks are blocked at query boundaries.
- Viewer role is strictly prohibited from modifying data or viewing worker compensation numbers.
- Administrator accounts cannot demote or deactivate themselves.

### 3.4. VAT Compliance & Precision
- Nepal 13% VAT calculations round strictly per statutory tax rules.
- Credit notes correctly debit accounts receivable and reduce VAT liability.
- Client-tampered tax calculations are detected and corrected server-side.

### 3.5. Readiness on Database Loss
- When PostgreSQL connection drops, `/api/v1/health/ready` immediately flags `HTTP 503 Service Unavailable`:
  `{"status": "unready", "database": "unhealthy", "detail": "Database connection probe failed."}`.

---

## 4. Disaster Recovery Scope & Consistency Protocol

### What the Backup Includes:
1. **Relational Database (`pg_dump`):** All tenant companies, users, product variants, raw materials, stock transfers, purchase orders, production batches, sales orders, invoices, payments, and worker ledgers.
2. **Persistent File Storage (`tar.gz`):** All active upload paths (`uploads/gallery/`, `uploads/workers/`, `uploads/citizenship/`).
3. **Cryptographic Integrity Manifest:** SHA-256 hash list of all archived files.

### What the Backup Excludes:
- Temporary cache files (`__pycache__`, `.next/cache`, `.pytest_cache`).
- Live database transaction journals (`*.db-wal`, `*.db-shm`).
- Unmounted external cloud storage buckets.
- Automated offsite cross-region replication (documented as accepted demo limitation).

### Point-in-Time Consistency Procedure:
1. Schedule a brief 2-minute maintenance window to freeze file ingestion.
2. Execute transactional database dump: `pg_dump --clean --no-owner`.
3. Immediately create the file storage tarball: `tar -czf files_backup.tar.gz /app/uploads`.
4. Generate the manifest: `sha256sum files_backup.tar.gz db_backup.sql > manifest.sha256`.
5. Restore into disposable test instance and execute checksum validation: `sha256sum -c manifest.sha256`.
