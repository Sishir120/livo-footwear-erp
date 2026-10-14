# LIVO FOOTWEAR ERP — CHECKPOINT 16: SECURITY AUDIT REPORT

**Audit Date:** October 2, 2026  
**Auditor Role:** Principal Application Security Engineer & Adversarial QA Architect  
**Methodology:** *Inspect → Threat-model → Attack → Observe failure/success → Fix → Regression-test → Re-attack → Document evidence*  
**Standards:** NIST SP 800-53 (AC, IA, SC, SI controls), OWASP API Security Top 10 2023, ASVS 4.0 Level 2  
**Scope:** Complete application surface (Backend FastAPI services, SQLAlchemy ORM queries, PostgreSQL advisory locks, Alembic migrations, Frontend Next.js client, Offline sync protocol).

---

## 1. Executive Summary

Checkpoint 16 conducted an adversarial application security audit and vulnerability remediation across LIVO Footwear ERP. Rather than relying on static code inspection, the system was actively attacked under multi-tenant conditions with competing corporate entities (Company A vs. Company B) and adversarial input vectors.

Four (4) concrete vulnerabilities were identified, reproduced through automated attacks, remediated with surgical defense-in-depth controls, and verified via automated regression suites:
- **VULN-01 (High):** Warehouse Cross-Tenant IDOR and Hardcoded Warehouse ID in Stock Movements & Adjustments.
- **VULN-02 (High):** Offline Production Draft Sync Warehouse IDOR.
- **VULN-03 (Medium):** Product Gallery File Path Traversal Defense-in-Depth.
- **VULN-04 (Medium):** Receivables Payment Allocation Foreign Invoice Bypass.

Across all 69 API endpoints, the multi-tenant isolation boundaries, role-based access controls (RBAC), and ERP business invariants were verified to hold firmly.

---

## 2. Vulnerability Discoveries & Remediations

### VULN-01: Warehouse Cross-Tenant IDOR & Hardcoded Warehouse ID
- **Severity:** High (CVSS 8.1 - AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N)
- **Affected Components:** `backend/app/api/v1/stock.py` (`create_stock_movement`, `create_stock_adjustment`), `backend/app/api/v1/sales.py`
- **Vulnerability Description:** In stock movements and stock adjustments, the system accepted a `warehouse_id` from client payloads or defaulted to `warehouse_id=1` without checking whether `Warehouse.company_id == current_user.company_id`. An attacker from Company A could target Company B's warehouse (`warehouse_id=2`), mutating stock ledger balances in foreign warehouses or polluting cross-tenant inventory history.
- **Root Cause:** Absence of tenant verification check on `Warehouse` in `stock.py` and `sales.py`.
- **Fix Applied:** Implemented helper `_get_default_or_validate_warehouse(db, company_id, warehouse_id)`:
  - If `warehouse_id` is supplied, queries `Warehouse.id == warehouse_id` AND `Warehouse.company_id == current_user.company_id`. If not found, immediately raises HTTP 404 Not Found.
  - If `warehouse_id` is None, auto-resolves or provisions the tenant's own active warehouse.
- **Regression Test:** `tests/test_checkpoint_16_tenant_isolation.py::test_cross_company_write_attacks` (Attack 5) and `tests/test_checkpoint_16_idor.py::test_idor_get_substitutions`.
- **Retest Result:** VERIFIED. Attack rejected with HTTP 404.

### VULN-02: Offline Production Draft Sync Warehouse IDOR
- **Severity:** High (CVSS 7.5 - AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N)
- **Affected Components:** `backend/app/api/v1/production.py` (`sync_production_draft`)
- **Vulnerability Description:** The offline production draft reconciliation endpoint accepted `payload.warehouse_id` and directly used it when generating production inward stock movements without verifying tenant ownership.
- **Root Cause:** The offline sync handler verified `product.company_id`, but omitted `Warehouse.company_id` validation.
- **Fix Applied:** Added explicit tenant verification for `payload.warehouse_id` against `current_user.company_id`. Mismatches log a `REJECTED` sync log with error code `INVALID_WAREHOUSE` and raise HTTP 404 Not Found.
- **Regression Test:** `tests/test_checkpoint_16_security.py::test_offline_production_draft_sync_tenant_boundary`.
- **Retest Result:** VERIFIED. Attack rejected with HTTP 404.

### VULN-03: Product Gallery File Path Traversal Defense
- **Severity:** Medium (CVSS 6.5 - AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N)
- **Affected Components:** `backend/app/api/v1/gallery.py` (`download_product_image`, `delete_product_image`)
- **Vulnerability Description:** File downloading and deletion constructed disk paths via `os.path.join(UPLOAD_DIR, image.file_name)` without validating that the canonical resolved path remained within `UPLOAD_DIR`. If a stored filename contained traversal sequences, file escape was theoretically possible.
- **Root Cause:** Reliance on `os.path.join` without `os.path.realpath` and `os.path.commonpath` verification.
- **Fix Applied:** Introduced `_safe_resolve_image_path(base_dir, file_name)` using `os.path.basename` and `os.path.commonpath([canonical_base, resolved]) == canonical_base`. Raises HTTP 400 Bad Request if path escapes the target directory.
- **Regression Test:** `tests/test_checkpoint_16_security.py::test_gallery_path_traversal_attack`.
- **Retest Result:** VERIFIED. Directory traversal sequences (`..%2F..%2F..%2Fwin.ini`, etc.) safely rejected.

### VULN-04: Receivables Payment Allocation Foreign Invoice Bypass
- **Severity:** Medium (CVSS 6.3 - AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N)
- **Affected Components:** `backend/app/api/v1/receivables.py` (`record_ar_payment`)
- **Vulnerability Description:** When client submitted invoice allocations in payment receipts (`payload.invoice_allocations`), allocations targeting foreign company invoices or non-existent invoices were silently omitted from allocations rather than rejecting the malformed or unauthorized request.
- **Root Cause:** Silent ignore pattern `if inv_entry: ...` without explicit validation of `Invoice.company_id == current_user.company_id` and client ownership.
- **Fix Applied:** Explicitly query `Invoice` by ID and `company_id`. Raise HTTP 404 if foreign/non-existent. If invoice belongs to a different client, raise HTTP 422. If no posted receivable entry exists, raise HTTP 422.
- **Regression Test:** `tests/test_checkpoint_16_tenant_isolation.py::test_cross_company_write_attacks` (Attack 9) and `tests/test_checkpoint_16_business_security.py::test_receivables_over_allocation_rejection`.
- **Retest Result:** VERIFIED. Foreign invoice allocation rejected with HTTP 404/422.

---

## 3. Multi-Tenant Isolation Assessment

### Tenant Isolation Architecture
Every database entity in LIVO Footwear ERP carries a mandatory `company_id` foreign key. The application enforces tenancy through:
1. **Request-Level Context:** `get_current_user` extracts `company_id` from cryptographically signed JWT tokens and validates that the user exists and is active in that specific company.
2. **Repository Layer:** `TenantRepository[T]` automatically attaches `Model.company_id == current_user.company_id` to all `get_all`, `get_by_id`, `filter`, `create`, `update`, and `delete` operations.
3. **Database-Level Unique Constraints:** Multi-column unique constraints enforce tenant isolation at the database engine level:
   - `uq_company_worker_code` on `workers(company_id, worker_code)`
   - `uq_company_warehouse_code` on `warehouses(company_id, code)`
   - `uq_invoice_company_sequence` on `invoices(company_id, sequence_number)`
   - `uq_invoice_company_invoice_number` on `invoices(company_id, invoice_number)`

### Adversarial Testing Results:
- **Cross-Tenant READ:** Company A cannot discover or read Company B's products, clients, warehouses, sales orders, invoices, printable invoices, purchase orders, workers, or images. All direct lookups return **HTTP 404 Not Found**. Collection endpoints return zero Company B records.
- **Cross-Tenant WRITE:** Company A cannot create sales orders for Company B clients, use Company B products, generate invoices against Company B orders, allocate payments to Company B invoices, or execute stock adjustments against Company B warehouses. All return **HTTP 404/422**.
- **Cross-Tenant DELETE:** Company A cannot delete Company B gallery images or entities. Returns **HTTP 404 Not Found**.

---

## 4. Broken Object-Level Authorization (BOLA / IDOR) Assessment

Every route accepting an object identifier (`{id}`, `{order_id}`, `{client_id}`, `{worker_id}`, `{image_id}`) was attacked by authenticating as User A and substituting victim identifiers from Company B.

| Endpoint | Method | Attack Vector | Response | Result |
|---|---|---|---|---|
| `/api/v1/production/products/{id}` | GET | Foreign Product ID | 404 Not Found | **VERIFIED** |
| `/api/v1/sales/clients/{id}` | GET | Foreign Client ID | 404 Not Found | **VERIFIED** |
| `/api/v1/stock/warehouses/{id}` | GET | Foreign Warehouse ID | 404 Not Found | **VERIFIED** |
| `/api/v1/sales/orders/{id}` | GET | Foreign Order ID | 404 Not Found | **VERIFIED** |
| `/api/v1/invoices/{id}` | GET | Foreign Invoice ID | 404 Not Found | **VERIFIED** |
| `/api/v1/invoices/{id}/printable` | GET | Foreign Invoice ID | 404 Not Found | **VERIFIED** |
| `/api/v1/purchase/suppliers/{id}` | GET | Foreign Supplier ID | 404 Not Found | **VERIFIED** |
| `/api/v1/purchase/raw-materials/{id}` | GET | Foreign Raw Mat ID | 404 Not Found | **VERIFIED** |
| `/api/v1/purchase/purchases/{id}` | GET | Foreign Purchase ID | 404 Not Found | **VERIFIED** |
| `/api/v1/hr/workers/{id}/history` | GET | Foreign Worker ID | 404 Not Found | **VERIFIED** |
| `/api/v1/hr/workers/{id}` | PATCH | Foreign Worker ID | 404 Not Found | **VERIFIED** |
| `/api/v1/production/{order_id}` | GET | Foreign Batch ID | 404 Not Found | **VERIFIED** |
| `/api/v1/production/{order_id}/complete` | POST | Foreign Batch ID | 404 Not Found | **VERIFIED** |
| `/api/v1/gallery/images/{id}/download` | GET | Foreign Image ID | 404 Not Found | **VERIFIED** |
| `/api/v1/gallery/{id}` | DELETE | Foreign Image ID | 404 Not Found | **VERIFIED** |

---

## 5. RBAC & Privilege Escalation Assessment

The application defines 3 tiers of authenticated access: `admin`, `editor`/`operator`, and `viewer`.

### Privilege Boundaries Verified:
1. **Viewer Restrictions:**
   - Any mutation (`POST /api/v1/stock/movements`, `POST /api/v1/stock/adjustments`, `POST /api/v1/sales/orders`, `POST /api/v1/sales/clients`, `POST /api/v1/production/products`, `POST /api/v1/hr/advances`) attempted by `viewer` returns **HTTP 403 Forbidden**.
2. **Operator vs. Admin Restrictions:**
   - Operational telemetry (`GET /api/v1/ops/telemetry`) is restricted via `require_admin` -> Operator returns **HTTP 403 Forbidden**.
   - Database backup trigger (`POST /api/v1/backup/run`) requires `require_admin` -> Operator returns **HTTP 403 Forbidden**.
   - Downward stock adjustments for loss/damage require `admin` role or a verified supervisor authorization token -> Operator without token returns **HTTP 403 Forbidden**.

---

## 6. Authentication Hardening & Token Security

Adversarial token testing verified:
- **Expired Token:** Immediate rejection (`HTTP 401 Unauthorized: Invalid or expired session token`).
- **Signature Tampering:** Modifying token bytes invalidates HMAC-SHA256 signature -> `HTTP 401 Unauthorized`.
- **Foreign Signing Key:** Token signed with attacker key rejected -> `HTTP 401 Unauthorized`.
- **Missing Claims:** Tokens missing `user_id` or `company_id` claims rejected -> `HTTP 401 Unauthorized: Token payload invalid`.
- **Inactive User:** Even with a valid cryptographic token, `User.active == False` prevents authentication -> `HTTP 401 Unauthorized: User not found or inactive`.

---

## 7. Business Logic & Statutory ERP Invariants

Adversarial testing against core ERP integrity rules:
1. **Stock Zero-Floor Invariant:**
   - Outbound stock movement exceeding available physical pairs is rejected with **HTTP 422 Unprocessable Entity** (`INSUFFICIENT_STOCK`).
   - Negative and zero quantities in stock movements are rejected with **HTTP 400/422**.
2. **Credit Limit Dispatch Safeguard:**
   - Submitting sales order exceeding customer's credit limit without `supervisor_override=True` is rejected with **HTTP 422** (`CREDIT_LIMIT_EXCEEDED`).
3. **Statutory Tax Invoice Invariant:**
   - Under Nepal IRD Schedule-5 VAT rules, attempting to create a second active VAT invoice for the same sales order is rejected with **HTTP 409 Conflict**.
4. **AR Payment Allocations:**
   - Submitting invoice allocations where sum of allocated paisa exceeds receipt amount is rejected with **HTTP 422**.

---

## 8. PostgreSQL-Specific Security Verification

All critical security invariants were verified on real PostgreSQL (embedded-postgres 18.6):
1. **Database-Level Unique Constraints:** Multi-column unique constraints prevent cross-tenant duplication while allowing identical SKU/worker codes in separate companies.
2. **Advisory Lock Tenant Keyspace Isolation:** PostgreSQL advisory locks derive keys via `(company_id << 32) | resource_id`. Tested that Company 1 and Company 2 taking locks on identical IDs do not collide or block each other.
3. **SQL Injection Immunity:** Evaluated parameterized ORM queries against SQL injection payloads (`' OR '1'='1`, `'; DROP TABLE companies; --`). Parametric isolation ensures zero leakage.

---

## 9. Evidence Classification

| Security Control | Classification | Evidence / Automated Test |
|---|---|---|
| Tenant Isolation (Read/Write/Delete) | **VERIFIED** | `tests/test_checkpoint_16_tenant_isolation.py` (3 passed) |
| IDOR / BOLA Prevention | **VERIFIED** | `tests/test_checkpoint_16_idor.py` (2 passed) |
| RBAC Least Privilege & Escalation | **VERIFIED** | `tests/test_checkpoint_16_rbac.py` (4 passed) |
| Token Hardening & Tamper Defense | **VERIFIED** | `tests/test_checkpoint_16_rbac.py::test_token_tampering_attacks` |
| Mass Assignment Immunity | **VERIFIED** | `tests/test_checkpoint_16_rbac.py::test_mass_assignment_and_privilege_injection` |
| Stock Zero-Floor Invariant | **VERIFIED** | `tests/test_checkpoint_16_business_security.py::test_stock_invariants_attack` |
| Credit Limit Safeguard | **VERIFIED** | `tests/test_checkpoint_16_business_security.py::test_sales_and_credit_invariants_attack` |
| Statutory VAT Duplicate Prevention | **VERIFIED** | `tests/test_checkpoint_16_business_security.py::test_vat_invoice_statutory_invariant` |
| AR Over-Allocation Rejection | **VERIFIED** | `tests/test_checkpoint_16_business_security.py::test_receivables_over_allocation_rejection` |
| Gallery Path Traversal Resistance | **VERIFIED** | `tests/test_checkpoint_16_security.py::test_gallery_path_traversal_attack` |
| Idempotency Multi-Tenant Isolation | **VERIFIED** | `tests/test_checkpoint_16_security.py::test_idempotency_cross_tenant_isolation` |
| Offline Sync Draft Tenant Boundary | **VERIFIED** | `tests/test_checkpoint_16_security.py::test_offline_production_draft_sync_tenant_boundary` |
| PostgreSQL Advisory Lock Separation | **VERIFIED** | `tests/test_checkpoint_16_postgres.py::test_postgres_advisory_lock_tenant_key_separation` |
| PostgreSQL Tenant Constraints | **VERIFIED** | `tests/test_checkpoint_16_postgres.py::test_postgres_tenant_unique_constraints` |
| SQL Injection Defense | **VERIFIED** | `tests/test_checkpoint_16_postgres.py::test_sql_injection_defense_in_tenant_queries` |
| Production Caddy HSTS / CSP Headers | **PRODUCTION-DEPENDENT** | Configured in Caddyfile; enforced by reverse proxy in live deployment |
| Secret Rotation Policy | **PRODUCTION-DEPENDENT** | Runtime secret manager / vault integration in cloud container |

---

## 10. Audit Conclusion

All 4 discovered vulnerabilities have been fixed with surgical precision and automated regression tests. The entire backend test suite (250 tests across SQLite and PostgreSQL) is passing with zero failures.

**Gate Recommendation:** **PASS**
