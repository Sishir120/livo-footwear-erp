# LIVO FOOTWEAR ERP — CHECKPOINT 16 REPORT

**Report Date:** October 2, 2026  
**Auditor:** Principal Application Security Engineer + Adversarial QA Architect  
**Checkpoint Target:** Security, Multi-Tenant Isolation & Authorization — Adversarial Audit  
**Operating Standard:** NIST SP 800-53 Rev 5 / OWASP API Security Top 10 2023 / ASVS 4.0 Level 2  
**Final Gate Decision:** **CHECKPOINT 16 = PASS**

---

## 1. Executive Summary

Checkpoint 16 executed an adversarial application security audit across LIVO Footwear ERP. Operating under the methodology:
$$\text{Inspect} \longrightarrow \text{Threat-model} \longrightarrow \text{Attack} \longrightarrow \text{Observe failure/success} \longrightarrow \text{Fix} \longrightarrow \text{Regression-test} \longrightarrow \text{Re-attack} \longrightarrow \text{Document evidence}$$

Rather than performing a static checklist review, active attacks were launched against the application across multi-tenant boundaries (Company A vs. Company B), object ownership boundaries (IDOR/BOLA), role-based permissions (RBAC), and ERP business invariants.

Four (4) concrete vulnerabilities were identified, reproduced through automated attack scripts, patched with defense-in-depth controls, and verified via automated regression suites:
1. **VULN-01 (High):** Warehouse Cross-Tenant IDOR & Hardcoded ID in Stock Movements & Adjustments (`stock.py`, `sales.py`).
2. **VULN-02 (High):** Offline Production Draft Sync Warehouse IDOR (`production.py`).
3. **VULN-03 (Medium):** Product Gallery File Path Traversal Defense (`gallery.py`).
4. **VULN-04 (Medium):** Receivables Payment Allocation Foreign Invoice Bypass (`receivables.py`).

Following remediation, **all 250 backend tests** (including 20 newly added adversarial security tests across SQLite and embedded PostgreSQL 18.6) pass with zero failures and zero regressions. Frontend TypeScript compilation and production build remain 100% clean.

---

## 2. Threat Model

A comprehensive threat model was constructed and documented in `docs/THREAT_MODEL.md`. The model evaluates 4 primary threat actors:
1. **Untrusted External Adversary:** Public network access attempting brute force, credential stuffing, unauthenticated API access, injection, and path traversal.
2. **Malicious Tenant (Comp-A vs. Comp-B):** Legitimate tenant attempting horizontal privilege escalation, BOLA/IDOR data harvesting, cross-tenant mutation, or shared resource poisoning.
3. **Restricted Internal User (Viewer / Operator):** Low-privilege employee attempting vertical escalation to administrative cockpit, ledger manipulation, supervisor override bypass, or sensitive payroll theft.
4. **Offline Mobile/Tablet Node:** Untrusted/tampered offline sync client replaying transactions, injecting out-of-order timestamps, or submitting forged sync batches.

---

## 3. Authentication Findings

1. **Password Hashing:** Passwords hashed with state-of-the-art Argon2id (`$argon2id$v=19$m=65536,t=3,p=4`) per OWASP recommendations. Verification is constant-time via passlib.
2. **Token Security:** JWT tokens signed with HMAC-SHA256 (`HS256`). Token payloads mandate `user_id` and `company_id`. Missing, expired, or tampered tokens return safe `HTTP 401 Unauthorized`.
3. **Inactive User Invalidation:** Even with a cryptographically valid token, deactivated users (`User.active == False`) are immediately rejected at the dependency layer (`HTTP 401: User not found or inactive`).
4. **Cookie & Header Flexibility:** Authentication accepts both secure `HttpOnly` session cookies (`livo_access_token`) and standard `Authorization: Bearer <token>` headers, enabling both browser security and headless API integration.

---

## 4. Complete Authorization Inventory & Findings

All 69 API endpoints across all 15 routing modules were inventoried in `docs/AUTHORIZATION_MATRIX.md`. Tracing every route from dependency to mutation revealed that:
- Every business table query enforces tenant scoping (`Model.company_id == current_user.company_id`).
- Mutation endpoints enforce `require_editor` or `require_admin`.
- Read endpoints enforce `get_current_user` (`viewer`+).
- Public endpoints are strictly limited to `/auth/login`, `/auth/register`, and `/ops/health`.

---

## 5. Multi-Tenant Isolation Results

Adversarially tested between Company A (`COMP_A_C16`) and Company B (`COMP_B_C16`):
- **Cross-Company READ Attacks:**
  - `GET /api/v1/production/products/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/sales/clients/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/stock/warehouses/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/sales/orders/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/invoices/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/invoices/{id_b}/printable` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/purchase/suppliers/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/purchase/raw-materials/{id_b}` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/hr/workers/{id_b}/history` $\rightarrow$ **404 Not Found**
  - `GET /api/v1/gallery/images/{id_b}/download` $\rightarrow$ **404 Not Found**
  - Collection endpoints (`/products`, `/clients`, `/warehouses`) completely omit foreign tenant records.
- **Cross-Company WRITE Attacks:**
  - Sales order referencing foreign client or product $\rightarrow$ **404/422**
  - Invoice generation referencing foreign sales order $\rightarrow$ **404**
  - Stock movement referencing foreign product $\rightarrow$ **404**
  - Stock adjustment referencing foreign warehouse $\rightarrow$ **404**
  - AR payment receipt targeting foreign client $\rightarrow$ **404**
  - AR payment allocation targeting foreign invoice $\rightarrow$ **404/422**
  - Purchase referencing foreign supplier/raw material $\rightarrow$ **404**
  - HR advance for foreign worker $\rightarrow$ **404**
- **Cross-Company DELETE Attacks:**
  - Deleting foreign gallery image $\rightarrow$ **404 Not Found**

---

## 6. IDOR / BOLA Results

Automated regression suite `test_checkpoint_16_idor.py` executes object ID substitution across 18 distinct object-level endpoints. Every attempt to access or mutate an object belonging to another company fails safely with **HTTP 404 Not Found** or **HTTP 422**. No foreign tenant entity details are disclosed.

---

## 7. RBAC & Privilege Escalation Results

Automated regression suite `test_checkpoint_16_rbac.py` attacked role boundaries:
- **Viewer Role:** Strictly rejected from creating or modifying products, clients, sales orders, stock movements, stock adjustments, purchases, or worker advances (**HTTP 403 Forbidden**).
- **Editor Role:** Prevented from accessing administrative telemetry (`/api/v1/ops/telemetry`), triggering manual backups (`/api/v1/backup/run`), or executing downward stock adjustments for loss/damage without supervisor authorization (**HTTP 403 Forbidden**).
- **Supervisor Token Validation:** Trivial bypass tokens (e.g. `'SUPERVISOR'`) are rejected. Downward adjustments for loss/damage require an admin password hash or cryptographic supervisor token.

---

## 8. Mass-Assignment & Privilege Injection Results

Attacks attempting to inject server-owned properties in request payloads were evaluated:
- Injecting `company_id=99999` in `POST /api/v1/production/products` $\rightarrow$ Ignored; created object is bound to `current_user.company_id`.
- Injecting `company_id=88888` in `POST /api/v1/sales/clients` $\rightarrow$ Ignored; bound to `current_user.company_id`.
- Injecting `role="admin"` in user payloads $\rightarrow$ Filtered out by strict Pydantic schemas.

---

## 9. Business-Logic & Statutory Security Results

Tested in `test_checkpoint_16_business_security.py`:
1. **Stock Zero-Floor Invariant:** Requesting 50 pairs when available on-hand stock is 20 fails with **HTTP 422 Unprocessable Entity** (`INSUFFICIENT_STOCK`).
2. **Negative/Zero Boundaries:** Negative or zero quantities in stock movements and sales items fail with **HTTP 400/422**.
3. **Credit Limit Safeguard:** Placing an order that would exceed the client's credit limit without `supervisor_override=True` fails with **HTTP 422** (`CREDIT_LIMIT_EXCEEDED`).
4. **Statutory Tax Invoice Invariant:** Attempting to create duplicate active VAT invoices for the same sales order fails with **HTTP 409 Conflict** (preventing statutory tax double-counting under Nepal IRD Schedule-5).
5. **AR Payment Allocations:** Submitting invoice allocations exceeding the receipt amount fails with **HTTP 422**.

---

## 10. Idempotency Security

Tested in `test_checkpoint_16_security.py::test_idempotency_cross_tenant_isolation`:
- Company A and Company B submitting requests with the **exact same idempotency key** (`SHARED-KEY-12345`) do not collide or share responses. Each tenant maintains an isolated idempotency namespace.
- Submitting identical requests within a tenant returns cached identical responses without double-mutating stock or financial records.

---

## 11. Offline Sync Security

Tested in `test_checkpoint_16_security.py::test_offline_production_draft_sync_tenant_boundary`:
- Offline draft synchronization rejects foreign product IDs and foreign warehouse IDs (**HTTP 404/422**).
- Mismatched sync attempts are recorded in `production_sync_logs` with status `REJECTED` and actor audit trail.
- Non-integer or negative draft quantities are rejected with **HTTP 422**.

---

## 12. Information Disclosure Audit

Tested across 400, 401, 404, 409, 422, and 500 error responses:
- Deliberately triggered invalid lookups, constraint violations, and authentication errors.
- Verified responses NEVER leak:
  - Python stack traces (`Traceback (most recent call last)`)
  - Database URLs (`sqlite://`, `postgresql://`)
  - Password hashes (`password_hash`)
  - Server secrets (`SECRET_KEY`)
  - Filesystem paths (`D:\Antigravity`, `/var/app`)

---

## 13. CORS, CSRF & Browser Security

1. **CORS:** Configured via FastAPI `CORSMiddleware`. Allowed origins are driven by `ALLOWED_ORIGINS` environment setting. Development defaults to `http://localhost:3000`; production rejects wildcard `*` with credentials.
2. **CSRF:** The application utilizes Bearer tokens in headers and `SameSite=Lax` cookies for browser navigation. State-changing requests mandate Bearer headers or API tokens.
3. **Cookie Attributes:** Cookies issued by `/auth/login` set `HttpOnly=True`, `SameSite="lax"`, and `Secure` conditional on production environment.

---

## 14. Security Headers

HTTP security headers verified on responses:
- `X-Content-Type-Options: nosniff` (prevents MIME-type confusion attacks)
- `X-Frame-Options: DENY` (neutralizes Clickjacking / UI redressing)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents referrer leakage)
- `Permissions-Policy: geolocation=(), camera=(), microphone=()` (disables unused browser APIs)
- Caddy reverse proxy enforces HSTS (`Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`).

---

## 15. Secret & Configuration Audit

- Automated search confirmed zero hardcoded production secrets, API keys, or database passwords in source code.
- `.gitignore` properly excludes `.env`, `*.db`, `pgdata`, `venv/`, and `node_modules/`.
- Default test secret keys are overridden by `SECRET_KEY` environment variables.

---

## 16. Backup & Administrative Endpoint Security

- `/api/v1/backup/run` is strictly guarded by `require_admin`. Operators and Viewers receive **HTTP 403 Forbidden**.
- `/api/v1/diagnostics/download` is strictly restricted to `admin` role.
- `/api/v1/ops/telemetry` is restricted to `admin` role.

---

## 17. PostgreSQL Security Validation

Executed on real embedded PostgreSQL 18.6 (`test_checkpoint_16_postgres.py`):
1. **Multi-Column Unique Constraints:**
   - `uq_company_worker_code` on `workers(company_id, worker_code)` enforced by PostgreSQL index.
   - `uq_invoice_company_sequence` on `invoices(company_id, sequence_number)` enforced by PostgreSQL index.
2. **Distributed Advisory Lock Isolation:**
   - PostgreSQL advisory lock keys derived via `(company_id << 32) | id`.
   - Verified that Company 1 and Company 2 taking locks on identical IDs do not collide or block.
3. **SQL Injection Defense:**
   - Parameterized queries verified immune to SQL injection (`' OR '1'='1`, `'; DROP TABLE companies; --`).

---

## 18. Vulnerabilities Discovered & Remediation Log

```text
ID: VULN-01
Severity: High (CVSS 8.1)
Affected component: backend/app/api/v1/stock.py, sales.py
Attack: Submit stock movement or stock adjustment specifying foreign warehouse_id
Expected behavior: Safe 404 rejection if warehouse does not belong to caller company
Observed behavior: Accepted warehouse_id without tenant validation; defaulted to warehouse 1
Root cause: Missing Warehouse.company_id filter
Fix: Added _get_default_or_validate_warehouse helper verifying tenant ownership; auto-resolves company warehouse if omitted
Regression test: tests/test_checkpoint_16_tenant_isolation.py (Attack 5)
Retest result: VERIFIED (404 Not Found)

ID: VULN-02
Severity: High (CVSS 7.5)
Affected component: backend/app/api/v1/production.py (sync_production_draft)
Attack: Submit offline production draft sync specifying foreign warehouse_id
Expected behavior: Rejection of draft with 404 and REJECTED sync log
Observed behavior: Warehouse ID passed to stock movement without tenant verification
Root cause: Offline draft handler omitted Warehouse.company_id check
Fix: Added explicit Warehouse lookup verifying company_id; logs REJECTED with INVALID_WAREHOUSE
Regression test: tests/test_checkpoint_16_security.py::test_offline_production_draft_sync_tenant_boundary
Retest result: VERIFIED (404 Not Found)

ID: VULN-03
Severity: Medium (CVSS 6.5)
Affected component: backend/app/api/v1/gallery.py (download_product_image, delete_product_image)
Attack: File path traversal via ../ sequences in stored file names
Expected behavior: Canonical path verification preventing filesystem escape
Observed behavior: os.path.join used without commonpath boundary check
Fix: Implemented _safe_resolve_image_path using os.path.basename and os.path.commonpath
Regression test: tests/test_checkpoint_16_security.py::test_gallery_path_traversal_attack
Retest result: VERIFIED (400 Bad Request / 404 Not Found)

ID: VULN-04
Severity: Medium (CVSS 6.3)
Affected component: backend/app/api/v1/receivables.py (record_ar_payment)
Attack: Submit invoice allocation targeting invoice belonging to another company or client
Expected behavior: Explicit rejection with 404 or 422
Observed behavior: Silently skipped foreign allocations without error
Root cause: Silent ignore pattern if inv_entry: ...
Fix: Added explicit Invoice lookup verifying company_id (404) and client_id (422)
Regression test: tests/test_checkpoint_16_tenant_isolation.py (Attack 9)
Retest result: VERIFIED (404 / 422)
```

---

## 19. Remaining Risks & Production-Dependent Controls

1. **In-Memory Rate Limiter:** The current rate limiter is memory-bound to the single FastAPI process. In a multi-worker or horizontally scaled deployment, an external Redis instance must back the rate limiter to provide distributed rate limiting.
2. **Reverse Proxy TLS & HSTS:** HSTS and HTTPS redirection are delegated to Caddy in the production Docker/Render topology.

---

## 20. Exact Verification Commands & Results

### 1. Checkpoint 16 Security Test Suites
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_security.py tests/test_checkpoint_16_tenant_isolation.py tests/test_checkpoint_16_idor.py tests/test_checkpoint_16_rbac.py tests/test_checkpoint_16_business_security.py tests/test_checkpoint_16_postgres.py -v
```
**Result:** **20 passed in 9.54s** (100% PASS)

### 2. Full Backend Test Suite
```bash
venv\Scripts\python -m pytest tests/ -q
```
**Result:** **250 passed, 3 skipped in 38.64s** (100% PASS)

### 3. Frontend TypeScript Compilation
```bash
cd frontend && npx tsc --noEmit
```
**Result:** **Exit code 0** (Zero type errors)

### 4. Frontend Production Build
```bash
cd frontend && npm run build
```
**Result:** **Exit code 0** (Static pages and routes compiled cleanly)

### 5. Alembic Migration Health
```bash
venv\Scripts\python -m alembic heads
venv\Scripts\python -m alembic current
```
**Result:** **Single head `012_add_c15_indexes` (clean)**

### 6. Deployment Preflight Check
```bash
python scripts/deploy_preflight.py
```
**Result:** **Preflight checks PASSED**

---

## 21. Final Gate Decision

```text
================================================================================
FINAL GATE DECISION: CHECKPOINT 16 = PASS
================================================================================
- Zero known critical vulnerabilities remaining.
- Zero known high-severity tenant-isolation vulnerabilities remaining.
- Multi-tenant isolation attacks: 100% DEFENDED (No data leaked).
- IDOR / BOLA attacks: 100% DEFENDED (404/422).
- RBAC privilege escalation attacks: 100% DEFENDED (403 Forbidden).
- Authentication hardening: 100% DEFENDED (401 Unauthorized).
- ERP business invariants & statutory tax rules: 100% VERIFIED.
- PostgreSQL validation: 100% PASS (Real embedded-postgres 18.6).
- All 250 backend tests pass (0 regressions).
- TypeScript & Next.js production build: 100% PASS.
- Alembic database migration state: Single head (clean).
================================================================================
```
