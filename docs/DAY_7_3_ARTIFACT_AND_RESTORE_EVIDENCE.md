# LIVO Footwear ERP — Day 7.3 Artifact Packaging & Disaster Recovery Evidence Report

**Evaluation Date:** 2026-10-16  
**Auditor / Verification Agent:** Independent Forensic Verification Agent (AGY / DeepMind Antigravity)  
**Target Milestone:** Day 7.3 Release-Candidate Verification  
**Workspace:** `D:\Antigravity\Footwear app`  
**Git Commit Baseline:** `2ab515e1c18fceafb5621a2b5ce4127ec2bf24bb`

---

## 1. Packaged Deployment Artifact Forensic Verification

### Cryptographic Identity & Metadata
| Artifact Property | Recorded Value | Verification Tool / Command |
| :--- | :--- | :--- |
| **Archive File** | `livo_staging_artifact.tar.gz` | `Get-Item livo_staging_artifact.tar.gz` |
| **Archive Size** | 12,390,784 bytes (11.82 MB) | File system length |
| **Archive SHA-256** | `FF2C3CDA5416F8B839D698D9312362B53F487180CDB423E77413D12F57C1AB9C` | `Get-FileHash -Algorithm SHA256` |
| **Manifest File** | `staging_artifact_manifest.sha256` | `Get-Item staging_artifact_manifest.sha256` |
| **Manifest Size** | 138,934 bytes | File system length |
| **Manifest SHA-256** | `CF08FE6F0953CA79D5395A626516BFBF185F02DBC05A4C4D0E86D58171B36256` | `Get-FileHash -Algorithm SHA256` |
| **Manifest Entries** | 1,196 files | Verified against unpacked tree |

### Exclusions & Boundary Audit
Inspection of all 1,196 entries confirmed the strict exclusion of:
- All local `.env` and secret environment files (`.env`, `.env.local`, `.env.production`).
- All local database files and journals (`*.db`, `*.db-wal`, `*.db-shm`, `staging_pgdata/`).
- All physical database dumps and backup archives (`backups/*.sql`, `backups/*.tar.gz`).
- All dependency trees and build caches (`venv/`, `node_modules/`, `.next/`, `__pycache__/`, `.pytest_cache/`).
- All version control metadata (`.git/`).

### Content Secret Scan
Every file in the archive was scanned for credential patterns:
- Private Keys (`-----BEGIN RSA/EC/DSA/OPENSSH PRIVATE KEY-----`): **0 matches**
- AWS Access Keys (`AKIA...`): **0 matches**
- Hardcoded database passwords in strings: **0 matches**
- Result: **CLEAN**

---

## 2. PostgreSQL 16 Disaster Recovery & Business Invariant Drill

The disaster recovery drill was executed using embedded PostgreSQL 16 and an isolated filesystem storage directory (`test_day_7_3_postgres_restore_invariants.py`).

### Verification Distinction: Logical Equivalence vs. Physical Byte Identity
- **Database Records:** Restored via SQL dump (`pg_dump` and `psql`). This establishes **logical data equivalence** (exact table rows, column types, foreign keys, and constraints), not physical PostgreSQL page-level byte parity.
- **File Storage Assets:** Restored via POSIX `tar.gz` extraction into an isolated target folder. This achieves **genuine physical byte identity**, confirmed by matching SHA-256 digests between pre-backup and restored files.

### Table Row Count Reconciliation Before vs. After Restore
| Database Model / Table | Seeded Count | Restored Count | Status |
| :--- | :---: | :---: | :---: |
| `companies` (`Company`) | 1 | 1 | **MATCH** |
| `warehouses` (`Warehouse`) | 2 | 2 | **MATCH** |
| `branches` (`Branch`) | 1 | 1 | **MATCH** |
| `users` (`User`) | 1 | 1 | **MATCH** |
| `products` (`Product`) | 1 | 1 | **MATCH** |
| `stock_movements` (`StockMovement`) | 1 | 1 | **MATCH** |
| `stock_transfers` (`StockTransfer`) | 1 | 1 | **MATCH** |
| `stock_transfer_items` (`StockTransferItem`) | 1 | 1 | **MATCH** |
| `suppliers` (`Supplier`) | 1 | 1 | **MATCH** |
| `raw_materials` (`RawMaterial`) | 1 | 1 | **MATCH** |
| `purchases` (`Purchase`) | 1 | 1 | **MATCH** |
| `clients` (`Client`) | 1 | 1 | **MATCH** |
| `sales_orders` (`SalesOrder`) | 1 | 1 | **MATCH** |
| `invoices` (`Invoice`) | 1 | 1 | **MATCH** |
| `payments` (`Payment`) | 1 | 1 | **MATCH** |
| `receivable_entries` (`ReceivableEntry`) | 1 | 1 | **MATCH** |
| `workers` (`Worker`) | 1 | 1 | **MATCH** |
| `worker_advances` (`WorkerAdvance`) | 1 | 1 | **MATCH** |
| `fixed_assets` (`FixedAsset`) | 1 | 1 | **MATCH** |
| `factory_expenses` (`FactoryExpense`) | 1 | 1 | **MATCH** |
| `waste_records` (`WasteRecord`) | 1 | 1 | **MATCH** |
| `product_images` (`ProductImage`) | 1 | 1 | **MATCH** |

### Verified Business Invariants
1. **Inventory & Stock Ledger:**
   - Product `BOOT-TREK-01`: Unit price verified at `Rs. 4,500.00`.
   - Stock movement quantity: `200` units, `direction=1`, `movement_type="PRODUCTION_IN"`.
2. **Inter-Branch Stock Transfers:**
   - Transfer `TRF-2026-001`: Status verified as `IN_TRANSIT`.
   - Transferred items: `50` units requested and dispatched to Destination Warehouse `WH-SHOWROOM`.
3. **Sales, Invoicing & VAT Compliance:**
   - Invoice `INV-2026-0001`: Subtotal `Rs. 20,000.00`, statutory 13% VAT `Rs. 2,600.00`, total `Rs. 22,600.00`.
   - Payment: `Rs. 10,000.00` received via bank transfer.
   - AR Subledger: Receivable entry verified with `amount_paisa = 2,260,000` (Rs. 22,600.00).
4. **Purchasing & Landed Costs:**
   - Purchase order `SUP-INV-8891`: Total raw material cost `Rs. 17,500.00`, landed cost freight allocation `100,000` paisa (`Rs. 1,000.00`).
5. **Worker Advances:**
   - Worker advance: `500,000` paisa (`Rs. 5,000.00`), entry type `ISSUED`, status approved.
6. **Fixed Assets, Expenses & Scrap:**
   - Fixed asset `AST-CUTTER-01`: Purchase cost `45,000,000` paisa (`Rs. 450,000.00`).
   - Factory expense: Electricity utility bill `1,520,000` paisa (`Rs. 15,200.00`).
   - Waste tracking: `14.50 kg` leather offcut pattern scrap logged.
7. **Physical Storage Asset Parity:**
   - Product image `trek_boot_01.jpg`: Physical file verified on restored disk.
   - Restored size: Matches original exactly.
   - Restored SHA-256 hash: Matches pre-backup image hash identically.

---

## 3. Disclosed Limitations & Operator Runbook Requirement

1. **Write Quiescence Window:**  
   Because PostgreSQL database dumping (`pg_dump`) and filesystem tarball compression (`tar.gz`) execute sequentially without a distributed lock manager, concurrent client writes during a backup could produce point-in-time skew.  
   **Operator Requirement:** Operators must enforce a short 2-minute quiesce window (via Caddy reverse proxy maintenance mode or off-peak cron) when taking full backups.

2. **Clean Failure Cleanup:**  
   In the event of an archive failure (e.g. disk space exhaustion), all partial `.tmp` files are deleted immediately by `backup_service.py`, leaving no dangling partial files.
