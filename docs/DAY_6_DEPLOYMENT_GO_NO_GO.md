# LIVO Footwear ERP — Day 6 Deployment Gate Decision (GO / CONDITIONAL GO / NO-GO)

**Date:** 2026-10-16  
**Auditor:** Independent Verification Agent (AGY / DeepMind Antigravity)  
**Target Milestone:** Controlled 1-Week Cloud Demonstration  
**Data Scope:** Synthetic Evaluation Data Only (Strict Client Privacy Guarantee)

---

## 1. Final Gate Decision: CONDITIONAL GO

The deployment readiness evaluation for the LIVO Footwear ERP cloud demonstration concludes with a **`CONDITIONAL GO`**.

### Decision Rationale:
1. **Core Verification Passed:**
   - The complete local application stack (Next.js frontend on port 3000, FastAPI backend on port 8000, and reverse proxy rewrites) was built, run, and verified live.
   - All 10 mandatory browser UI acceptance steps passed under automated headless browser execution, with video and screenshot artifacts preserved.
   - The targeted regression suite (64 test items across 8 critical operational suites) passed with zero failures (`exit code 0`).
   - Dual-layer database and file recovery drill succeeded with byte-for-byte SHA-256 integrity validation.
2. **Acceptable Demonstration Limitations:**
   - The evaluation is strictly bounded to synthetic demonstration data.
   - All known architectural boundaries and missing ERP modules are explicitly cataloged below so demonstrators do not present unverified features to stakeholders.

---

## 2. Explicitly Disclosed Unsupported Functionality

The following items are **not implemented** or **remain API-only / experimental**, and must not be represented as complete during client demonstrations:

1. **No Double-Entry General Ledger or Formal Trial Balance:**
   - The ERP features an operational Accounts Receivable (AR) sub-ledger, invoice tracking, 13% Nepal VAT calculations, and factory expense logging.
   - It **does not** contain a full double-entry chart of accounts, debit/credit journal vouchers, or automatic trial balance generation.
2. **No Mandatory Production-Batch Assignment at Sales Dispatch:**
   - Sales dispatches deduct inventory balances by Product Variant (SKU), size, and warehouse.
   - The schema does not enforce strict physical batch-to-box serial tracking upon dispatch.
3. **No Proven Multi-Client Offline Sync:**
   - While frontend code includes local queue stubs and `X-Idempotency-Key` headers, real multi-client offline-to-online sync across intermittent networks has not undergone end-to-end integration testing.
4. **Destination Discrepancy UI Flow is Simplified:**
   - The backend API fully supports partial receipts and discrepancy shortage logs (`tests/test_stock_transfers.py`).
   - The frontend interface currently implements straightforward receipt confirmation; deep dispute resolution workflows remain API-driven.
5. **Contextual Help & Nepali Calendar (BS/AD) Conversions:**
   - Date conversion is robust in backend core calculations, but selected secondary frontend form modals default to Gregorian calendar inputs.
6. **Milestone 6A Documentation Clarification:**
   - Mentions of Milestone 6A in historical project notes represent planned roadmap proposals rather than verified features in the active codebase.

---

## 3. Findings Categorization Matrix

| Category | Item Description | Verification Evidence |
| :--- | :--- | :--- |
| **Verified** | Next.js Frontend Production Build (7/7 static routes) | `npm run build` output; exit code 0 |
| **Verified** | Local API Probes (`/health`, `/health/live`, `/health/ready`) | Native HTTP GET returns `200 OK` |
| **Verified** | 10-Step Browser UI Smoke Test | Chromium recording `day6_browser_smoke_1792136521870.webp` |
| **Verified** | Targeted Backend Regression (64 tests across 8 suites) | Pytest run `task-6014`: 64 passed, 0 failed in 13.66s |
| **Verified** | Complete Database + File Recovery Drill | Pytest run `task-6019`: 1 passed in 19.39s (PostgreSQL) |
| **Verified** | Fail-Closed Demo Account Guard | `ENABLE_DEMO_SEEDING` rejects production environments |
| **Blocked by Infrastructure** | Docker CLI Execution on Host | Windows host lacks Docker engine CLI (`docker : not recognized`) |
| **Accepted Limitation** | Host-Local Backups vs. Offsite S3 Bucket | Acceptable for synthetic 1-week demo; required for live production |
| **Accepted Limitation** | Absence of Full Double-Entry General Ledger | Documented as out of scope for footwear manufacturing focus |

---

## 4. Operator Pre-Deployment Checklist

Before making the cloud demonstration instance accessible to evaluators, the operator must verify:

- [ ] **Data Isolation:** Ensure the cloud database instance is completely empty and populated exclusively with synthetic demonstration records. Zero live client data.
- [ ] **Environment Flags:** Verify environment variables in the cloud host:
  - `ENVIRONMENT=development` (or `staging`)
  - `ENABLE_DEMO_SEEDING=true` (for automatic creation of demo personas)
  - `SECRET_KEY=<cryptographically-random-64-character-hex-string>`
  - `LIVO_DEV_MODE=false` (forces `Secure` flag on cookies over HTTPS)
- [ ] **Network Access:** Confirm database port 5432 is bound to `127.0.0.1` or internal VPC network only, with no public internet ingress.
- [ ] **HTTPS Certificate:** Verify reverse proxy (Caddy / Cloudflare / Nginx) provides valid TLS encryption.
- [ ] **Credential Distribution:** Securely communicate demo credentials (`admin_demo`, `editor_admin`, `viewer_demo`) via encrypted channel without committing plaintext passwords to Git.
- [ ] **Backup Schedule:** Trigger a manual baseline backup (`python -m app.scripts.backup_full`) before demo kickoff.
