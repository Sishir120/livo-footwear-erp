# LIVO Footwear ERP — Day 7.4 Security & Nepali Calendar Gap Reconciliation Report

**Phase:** Day 7.4 Final Artifact Identity & Staging Authorization Gate  
**Timestamp:** 2026-10-16T15:58:00+05:45  
**Workspace:** `D:\Antigravity\Footwear app`  

---

## 1. Release Package Security & Provenance Audit

A comprehensive forensic audit of `backend/scripts/package_staging_artifact.py` and `backend/scripts/validate_staging_artifact.py` was conducted.

### 1.1 Archive Integrity and Traversal Defense
- **Path Traversal Protection:**  
  `validate_staging_artifact.py` explicitly verifies that no archive entry contains `..` path elements, absolute paths starting with `/` or `\\`, or drive letters (`C:`, `D:`).
- **Symlink Boundary Enforcement:**  
  Hardlinks and symbolic links are audited; any link containing `..` or pointing outside the sandbox root causes an immediate fatal abort.
- **Extraction Behavior:**  
  Unpacking into an isolated temporary directory verified zero out-of-boundary file creation.

### 1.2 Boundary Exclusion Verification
The packaging script strictly enforces exclusion boundaries across the workspace:
- **Secrets & Credentials:** All `.env`, `.env.*` files excluded (except `.example` templates).
- **Databases & Journals:** `livo_dev.db`, `*.sqlite`, `*.db-wal`, `*.db-shm`, and `staging_pgdata/` excluded.
- **Physical Backups:** All `backend/backups/*.sql`, `*.db`, `*.tar.gz`, and `livo_manifest_*.json` excluded.
- **Build Caches & Dependencies:** `venv/`, `node_modules/`, `.next/`, `__pycache__/`, and `.pytest_cache/` excluded.
- **Binaries & Scratch:** `pg_binaries.zip` and `scratch/` excluded.

### 1.3 Secret Scanning Across File Contents
`validate_staging_artifact.py` performs deep content inspection across all bundled files:
- **Scanned Regex Patterns:**
  - `-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----` (Private Key Headers)
  - `AKIA[0-9A-Z]{16}` (AWS Access Key ID)
  - `(?i)postgres://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@` (Embedded Database Connection Strings)
- **Findings:** **Zero violations detected** across all 1,196 files. No active secrets, API keys, or database passwords are packaged in the release artifact.

### 1.4 Cryptographic Verification vs Digital Provenance
- **Manifest Coverage:**  
  `staging_artifact_manifest.sha256` covers all 1,196 files with individual SHA-256 digests. Zero unexpected or untracked files are permitted.
- **Provenance Limitation Disclaimer:**  
  A SHA-256 checksum proves only that an archive matches an expected hash; **it does not authenticate the author or origin of the package**. An attacker with repository write access could replace both `livo_staging_artifact.tar.gz` and `staging_artifact_manifest.sha256` simultaneously. True provenance requires an external cryptographic signature (e.g. GPG signature or Cosign/Sigstore keyless signing) stored outside the application archive.

---

## 2. Nepali Bikram Sambat (BS) Calendar Coverage Reconciliation

### 2.1 Backend vs Frontend Engine Parity
| Parameter | Backend (`app/core/nepali_date.py`) | Frontend (`frontend/src/lib/nepaliDate.ts`) | Parity Status |
| :--- | :--- | :--- | :--- |
| **Supported BS Range** | BS 1979-01-01 to BS 2100-12-30 | BS 1979-01-01 to BS 2100-12-30 | **Identical (122 Years)** |
| **Astronomical Anchor** | BS 1979-01-01 = AD 1922-04-13 | BS 1979-01-01 = AD 1922-04-13 | **Identical** |
| **Lookup Data Table** | 122 arrays of 12 monthly day counts | 122 arrays of 12 monthly day counts | **Bit-for-Bit Parity** |
| **Boundary Handling** | Raises `ValueError` outside [1979, 2100] | Falls back / returns null outside [1979, 2100] | **Safe (Fail-Closed)** |

### 2.2 UI Date Component & Form Coverage Matrix
The application employs `NepaliDatePicker.tsx` to provide bilingual (English/Nepali) date selection and automatic AD/BS synchronization.

| Application Form / View | Component Used | Nepali (BS) Date Support | Gregorian (AD) Date Support |
| :--- | :--- | :---: | :---: |
| **Sales & VAT Invoicing** (`SalesInvoiceView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Purchase & Material GRN** (`PurchaseView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Production Batches** (`ProductionView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Production Analytics** (`ProductionAnalyticsView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Accounts Receivable Aging** (`PartyAgingView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **HR & Payroll Ledger** (`HRManagementView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Factory Expenses & Assets** (`ExpensesAssetsView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Daily Operations Report** (`DailyReportView.tsx`) | `NepaliDatePicker` | **YES** | YES |
| **Party Statement Filter Modal** (`PartyStatementModal.tsx`) | `<input type="date">` | **NO (AD Only)** | YES |
| **Stock Card History Modal** (`StockCardModal.tsx`) | `<input type="date">` | **NO (AD Only)** | YES |

### 2.3 Operational Gap Analysis
1. **Core Transaction Forms:** 100% of mutation forms (Sales, Purchase, Production, HR, Expenses) support Bikram Sambat date entry.
2. **Identified Modal Reporting Gaps:** Two secondary modal dialogs (`PartyStatementModal.tsx` and `StockCardModal.tsx`) continue to rely on HTML native `<input type="date">`. Operators filtering statement history on these modals must input dates in Gregorian (AD) format.
3. **Database Persistence Architecture:**  
   To prevent index fragmentation and ensure compliance with Nepal IRD standards:
   - Primary timestamp arithmetic uses PostgreSQL `DATE` / `TIMESTAMP WITH TIME ZONE` columns (`invoice_date`, `created_at`).
   - Fiscal Bikram Sambat strings are stored in dedicated `VARCHAR(10)` columns (`nepali_date`, `bs_date`) for official invoice printing and tax auditing.
