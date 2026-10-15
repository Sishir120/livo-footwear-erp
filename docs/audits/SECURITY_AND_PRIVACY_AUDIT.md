# LIVO FOOTWEAR ERP — SECURITY AND PRIVACY AUDIT

**Audit Date:** 2026-10-14  
**Auditor Roles:** Principal Application Security Engineer, Independent Security Auditor  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Target Branch:** `release/v1.0.0-staging` @ `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4`  
**Investigation Mode:** Strict Read-Only Forensic Audit  

---

## 1. Executive Security Verdict

| Gate | Assessment | Rationale |
|---|:---:|---|
| **Live Client Demonstration** | **CONDITIONAL PASS** | Only safe if demonstrated under supervised walkthrough using isolated synthetic data; demo accounts must not be used on live client networks. |
| **Production Exposure** | **STRICT FAIL** | Hardcoded credentials disclosed on public GitHub README and live Vercel login page presets; in-memory rate limiting; uncommitted security patches. |

---

## 2. Priority Vulnerability Register

### [VULN-01] Public Disclosure of Administrative Credentials & Live Login Presets
- **Severity:** CRITICAL (CVSS 9.8)
- **Status:** Verified (Reproduced against live Vercel deployment and Git history)
- **Affected Files:**
  - `README.md:25-33` (Committed on branch `release/v1.0.0-staging` SHA `47cf8f5`)
  - `docs/CLIENT_PITCH_CHEATSHEET.md:22-30`
  - `frontend/src/app/login/page.tsx:44-55, 203-211` (Live Vercel bundle `https://livo-footwear-erp.vercel.app/login`)
- **Evidence:**
  The public GitHub repository's README discloses default usernames and passwords for `admin_demo` (`LivoAdmin2026!`) and `viewer_demo` (`LivoViewer2026!`). Furthermore, the live Vercel frontend renders clickable preset buttons (`Admin Operator` and `Auditor Viewer`) that automatically populate credentials.
- **Preconditions:** Anyone with access to the public GitHub repository or live URL.
- **Business Impact:** Complete administrative takeover, unauthorized tax invoice generation, data exfiltration of confidential worker citizenship records, and potential ransomware or deletion of database records.
- **Immediate Containment (Owner Action Required):**
  1. Rotate `SECRET_KEY` in Render environment to invalidate all issued session JWTs immediately.
  2. Execute SQL against production DB: `UPDATE users SET active = false WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');`
  3. Deploy local uncommitted `frontend/src/app/login/page.tsx` (which removes quick-fill buttons and hardcoded strings).

---

### [VULN-02] Unconditional Application Startup Account Seeding in Committed Baseline
- **Severity:** HIGH (CVSS 8.5)
- **Status:** Verified
- **Affected Files:**
  - `backend/app/main.py:54-106` (in baseline commit `47cf8f5`)
- **Evidence:**
  In commit `47cf8f5`, the FastAPI `lifespan` hook unconditionally executes user seeding on every application restart. If `admin_demo` is absent, it creates the user with role `admin` and hardcoded password. If an administrator deletes or disables the demo account, the next container restart automatically recreates it.
  *Note:* Local uncommitted working tree introduces `backend/app/core/demo_seeding.py` with `ENABLE_DEMO_SEEDING` and `is_production` safeguards, but this patch is uncommitted and not deployed to Render.
- **Business Impact:** Inability to permanently remove demo accounts; persistent backdoor across restarts.

---

### [VULN-03] Client IP Spoofing & Rate-Limiting Bypass Behind Reverse Proxy
- **Severity:** HIGH (CVSS 7.5)
- **Status:** Verified
- **Affected Files:**
  - `backend/app/middleware/rate_limit.py:29-35` (in baseline commit `47cf8f5`)
- **Evidence:**
  In baseline commit `47cf8f5`, `BasicRateLimitMiddleware` extracted client IP via:
  ```python
  forwarded = request.headers.get("X-Forwarded-For")
  if forwarded:
      client_ip = forwarded.split(",")[0].strip()
  ```
  It accepted the leftmost IP from `X-Forwarded-For` without validating if the direct peer is a trusted reverse proxy. An attacker can send arbitrary spoofed headers (`X-Forwarded-For: 1.1.1.1`, `X-Forwarded-For: 1.1.1.2`), rotating the attributed IP on every attempt and completely bypassing login brute-force throttling.
  *Note:* Local uncommitted changes contain `extract_client_ip` and `TRUSTED_PROXIES` validation, but this remains uncommitted.

---

### [VULN-04] Lack of Location / Branch-Level Authorization Boundaries
- **Severity:** HIGH (CVSS 7.1)
- **Status:** Verified
- **Affected Files:**
  - `backend/app/models/user.py:6-21`
  - `backend/app/api/v1/stock.py:104, 683`
  - `backend/app/api/deps.py:20-82`
- **Evidence:**
  Multi-tenancy is scoped strictly at the company level (`company_id`). The `User` model contains no `warehouse_id` or `branch_id`. Any user with `editor` or `admin` permissions can post stock adjustments, create stock movements, or view stock cards for ANY warehouse or branch in the company by manipulating `warehouse_id` in API payloads.
- **Business Impact:** Branch managers or storekeepers can tamper with central factory stock or another branch showroom's stock without authorization.

---

### [VULN-05] In-Memory Rate Limiting State Isolation across Multiple Instances
- **Severity:** MEDIUM (CVSS 5.3)
- **Status:** Verified
- **Affected Files:**
  - `backend/app/middleware/rate_limit.py:75-90`
- **Evidence:**
  `BasicRateLimitMiddleware` maintains sliding window request counts in an in-memory Python dictionary (`defaultdict(list)`). When deployed across multiple Uvicorn workers or multiple Render instances, state is not shared. An attacker can distribute authentication attempts across instances.
- **Remediation Direction:** In multi-instance production, migrate rate limiting state to Redis or PostgreSQL advisory token counters.

---

## 3. Server-Side Role-Based Authorization Matrix

| Endpoint Group | Resource / Function | Reader Role | Editor Role | Admin Role | Enforced Dependency |
|---|---|:---:|:---:|:---:|---|
| `/api/v1/auth/users` | User Creation & Role Assignment | Denied (403) | Denied (403) | **Allowed** | `require_admin` |
| `/api/v1/backup/` | Database Backup & Diagnostics | Denied (403) | Denied (403) | **Allowed** | `require_admin` |
| `/api/v1/invoices/{id}/void` | Tax Invoice Voiding / Reversal | Denied (403) | Denied (403) | **Allowed** | `require_admin` |
| `/api/v1/stock/movements` | Append Stock Movements | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/stock/adjustments` | Stock Balance Reconciliation | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/sales/orders` | Sales Order Entry | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/sales/dispatch` | Stock Relief & Dispatch | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/purchases/` | PO Creation & Landed Costs | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/purchases/{id}/receive` | Raw Material GRN Inwarding | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/production/batches` | Batch Assembly & BOM Deduction | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/hr/workers` | Worker Profile Creation | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/hr/workers/{id}/citizenship` | Confidential Vault Upload | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/hr/advances` | Issue / Recover Advances | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/expenses/factory` | Operating Expense Vouchers | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/assets/` | Capital Asset Acquisitions | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/waste/` | Factory Scrap & Reject Logging | Denied (403) | **Allowed** | **Allowed** | `require_editor` |
| `/api/v1/stock/ledger` | View Stock Card Movements | **Allowed** | **Allowed** | **Allowed** | `get_current_user` |
| `/api/v1/receivables/aging` | View AR Aging Subledger | **Allowed** | **Allowed** | **Allowed** | `get_current_user` |
| `/api/v1/analytics/` | View Leaderboards & Ratios | **Allowed** | **Allowed** | **Allowed** | `get_current_user` |

---

## 4. Privacy & Confidential Data Protection

1. **Worker Citizenship Vault:**
   - Worker citizenship documents (`citizenship_doc_path`) are stored under `backend/uploads/citizenship/`.
   - Access to raw files is guarded by authentication.
   - However, files are stored on local container disk rather than private encrypted object storage (e.g., S3/B2 with pre-signed URLs). Container restarts on Render ephemerally delete uploads unless persistent disks are mounted.
2. **PII Redaction in Telemetry:**
   - Verified: `CorrelationIdMiddleware` and logging formatters redact passwords, tokens, and authorization headers in `app/core/logging.py`.
   - Health check endpoints do NOT leak environment secrets.
3. **Session Cookies:**
   - Cookie flags: `httponly=True`, `samesite="lax"`, `secure=True` (in production mode). Local dev supports `LIVO_DEV_MODE=true` for HTTP.
