# LIVO FOOTWEAR ERP — SECURITY THREAT MODEL

**Version:** 1.0.0 | **Author:** Principal Application Security Engineer & Security Architect | **Date:** 2026-10-02  
**Scope:** LIVO Footwear ERP (FastAPI Backend, Next.js Frontend, PostgreSQL / SQLite, Docker/Caddy)

---

## 1. THREAT ACTORS & CAPABILITY PROFILES

| Actor Profile | Description | Motive | Assumed Capabilities |
|---|---|---|---|
| **External Attacker** | Unauthenticated internet-based adversary targeting public web endpoints. | Data theft, disruption, unauthorized access to ERP financial data. | HTTP network probes, automated vulnerability scanners, brute force, token forgery, replay attacks, parameter fuzzing. |
| **Malicious / Compromised Tenant (Company B)** | Legitimate tenant company user seeking access to another tenant's data (Company A). | Competitive intelligence (pricing, clients, stock, production metrics), disruption. | Valid authentication credentials, JWT session token for their own company, API access. |
| **Untrusted / Disgruntled Insider (Viewer)** | Authenticated user with read-only `viewer` role attempting privilege escalation. | Fraud, unauthorized inventory adjustment, invoice cancellation, data sabotage. | Valid employee credentials, local browser session, knowledge of internal business IDs and endpoints. |
| **Rogue Data Entry Operator (Editor)** | Authenticated `editor` attempting unauthorized administrative actions. | User creation, role tampering, unapproved stock write-offs, log deletion, backup exfiltration. | Valid editor credentials, capability to issue mutations on standard ledgers. |
| **Offline Device Adversary** | Terminal device in warehouse or transit with cached offline mutations. | Forging production drafts, manipulating timestamps/quantities, event replay. | Direct access to device storage, capability to tamper with pending JSON sync payloads. |

---

## 2. THREAT CATEGORIES & ADVERSARIAL ANALYSIS

### 2.1 Authentication & Session Threats

#### T-AUTH-01: Credential Brute Force & Dictionary Attacks
- **Threat:** Automated attacker executes rapid dictionary login attempts against `POST /api/v1/auth/login`.
- **Target:** User credentials and password hashes.
- **Impact:** Account takeover, unauthorized ERP access.
- **Controls & Mitigation:**
  - In-process sliding-window rate limiter (`BasicRateLimitMiddleware`) enforcing max 30 requests / 60 seconds per IP with `Retry-After: 60` and `429 Too Many Requests`.
  - Cryptographic Argon2id password hashing with high memory cost and adaptive salt, defeating offline dictionary cracking.
  - Constant-time verification semantics; generic `Incorrect username or password` response to prevent username enumeration.

#### T-AUTH-02: Session Token Theft, Manipulation & Replay
- **Threat:** Attacker intercepts, tampers with, or replays session JWTs.
- **Target:** `livo_access_token` session cookie.
- **Impact:** Impersonation of users, bypass of tenant isolation.
- **Controls & Mitigation:**
  - Token delivered exclusively via `httpOnly`, `SameSite=lax`, and `Secure` (in HTTPS production) cookies; inaccessible to JavaScript `document.cookie` (neutralizing DOM XSS exfiltration).
  - Explicit HMAC-SHA256 (`HS256`) cryptographic signature verification against a mandatory ≥32-character `SECRET_KEY` that fails fast at startup if omitted.
  - Strict expiration timestamp (`exp`) enforced by PyJWT with standard rejection on expiration.
  - Zero trust in client-side JWT claims: the database is queried on every request (`get_current_user`) to verify `user.id`, `user.company_id`, and `user.active == True`. Tampered claims or deactivated users trigger immediate HTTP 401 Unauthorized.

#### T-AUTH-03: Logout Invalidation Bypass
- **Threat:** Client logs out, but token remains accepted by server or retained by browser.
- **Target:** `POST /api/v1/auth/logout`.
- **Impact:** Session hijacking on shared warehouse terminals.
- **Controls & Mitigation:**
  - Explicit dual deletion: `response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=True)` followed by overwriting with `max_age=0` and `expires=0` to force immediate browser cache eviction.

---

### 2.2 Authorization & Access Control Threats

#### T-AUTHZ-01: Horizontal Privilege Escalation & Cross-Tenant Data Access (IDOR / BOLA)
- **Threat:** Authenticated user from Company A attempts to view, modify, or delete resources belonging to Company B by substituting foreign IDs into path parameters, query strings, or request bodies.
- **Target:** Products, Clients, Warehouses, Stock Movements, Invoices, Sales Orders, Receivable Entries, Production Batches, Workers, Images.
- **Impact:** Critical breach of multi-tenant isolation, confidential business leak.
- **Controls & Mitigation:**
  - Architectural enforcement via `TenantRepository`: every database query, update, and deletion is constrained by `WHERE company_id = :current_user_company_id`.
  - Foreign key verification on mutations: any referenced foreign key (e.g. `client_id`, `product_id`, `supplier_id`, `raw_material_id`, `warehouse_id`) must explicitly exist within the caller's tenant company, returning HTTP 404/422 if mismatched.
  - Absence of cross-tenant search leaks: listing endpoints (`get_all`, `filter`) strictly append tenant scoping.

#### T-AUTHZ-02: Vertical Privilege Escalation (RBAC Bypass)
- **Threat:** User with `viewer` role attempts to invoke mutating endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) or an `editor` attempts to invoke administrative endpoints (`/auth/users`, `/backup/run`, `/ops/telemetry`, `/diagnostics/download`).
- **Target:** RBAC gatekeepers (`require_editor`, `require_admin`).
- **Impact:** Unauthorized financial transactions, user management manipulation, system disruption.
- **Controls & Mitigation:**
  - Server-side dependency injection guards (`require_editor`, `require_admin`) enforced on every mutating route.
  - Zero trust in client-supplied role parameters: `current_user.role` is retrieved directly from the database record, never parsed from caller-supplied headers or request payloads.
  - Attempted role escalation returns HTTP 403 Forbidden.

#### T-AUTHZ-03: Mass Assignment & Privilege Injection
- **Threat:** Attacker injects extra fields into JSON request payloads (e.g., `"company_id": 2`, `"role": "admin"`, `"is_admin": true`, `"actor_id": 1`).
- **Target:** Pydantic model schemas and SQLAlchemy repository layers.
- **Impact:** Silent reassignment of objects to another tenant or elevation of privileges.
- **Controls & Mitigation:**
  - Strict Pydantic input schemas (`ClientCreate`, `ProductCreate`, `UserCreate`, etc.) whitelist only allowable business fields.
  - `TenantRepository.create()` explicitly overrides `kwargs["company_id"] = self.company_id`.
  - `TenantRepository.update()` strips out `company_id` via `kwargs.pop("company_id", None)`.

---

### 2.3 Financial & Business Integrity Threats

#### T-BIZ-01: Negative Inventory Invariant Violation (Overselling Race Conditions)
- **Threat:** Attacker issues concurrent outbound stock movements (`direction: -1`) exceeding physical on-hand stock.
- **Target:** `POST /api/v1/stock/movements`, `POST /api/v1/sales/orders`.
- **Impact:** Negative physical stock balances, inventory corruption, unfulfilled commitments.
- **Controls & Mitigation:**
  - Pessimistic locking architecture: transaction-scoped PostgreSQL advisory locks (`pg_advisory_xact_lock`) combined with in-process threading locks (`get_stock_mutex`).
  - Atomic zero-floor verification: stock balance is evaluated inside the exclusive transaction boundary. If `current_balance - requested < 0`, the transaction is rolled back with HTTP 422 `INSUFFICIENT_STOCK`.
  - Append-only stock ledger: direct modification of inventory quantities is structurally prohibited; stock is derived exclusively from `SUM(direction * quantity)`.

#### T-BIZ-02: Credit Limit Bypass & Unauthorized Dispatch
- **Threat:** Attacker issues sales orders exceeding customer credit limit without supervisor override.
- **Target:** `POST /api/v1/sales/orders`.
- **Impact:** Uncollectible bad debt, client credit limit breach.
- **Controls & Mitigation:**
  - Client credit advisory lock (`acquire_client_credit_lock`) serializes concurrent order evaluations per client.
  - Exact integer paisa calculation of current receivables vs. `client.credit_limit_paisa`.
  - Rejection with HTTP 422 `CREDIT_LIMIT_EXCEEDED` unless valid supervisor credentials/tokens are provided.

#### T-BIZ-03: Statutory VAT & Invoice Sequence Tampering
- **Threat:** Attacker attempts to forge invoice sequences, create duplicate active VAT invoices, or delete issued invoices.
- **Target:** `invoices`, `invoice_sequences`, Nepal IRD Schedule-5 compliance.
- **Impact:** Statutory tax non-compliance, audit failure, tax liability duplication.
- **Controls & Mitigation:**
  - Monotonic document sequence generator (`allocate_next_sequence`) using atomic `SELECT ... FOR UPDATE` with unique database constraint `uq_company_invoice_sequence`.
  - Nepal IRD Schedule-5 invariant: duplicate active VAT tax invoices for the same sales order are rejected with HTTP 409 Conflict.
  - Statutory cancellation: invoices are NEVER deleted. Cancelling an invoice sets `is_void = True` and writes an immutable `VOID_REVERSAL` to the AR subledger.

#### T-BIZ-04: Idempotency Key Abuse & Request Replay
- **Threat:** Attacker re-submits a previously executed request with a different payload using the same idempotency key, or cross-tenant key replay.
- **Target:** `IdempotencyMiddleware`, `/production/sync/draft`.
- **Impact:** Double invoicing, duplicated stock deductions, cross-tenant key collision.
- **Controls & Mitigation:**
  - Idempotency records are strictly tenant-scoped (`company_id`, `idempotency_key`).
  - Tamper detection: incoming payload is hashed (`SHA-256`); mismatched payload with existing key is rejected with HTTP 409 Conflict.
  - Cached replay returns identical status code and body with `X-Idempotent-Replay: true` without re-executing business logic.

---

### 2.4 Application & API Threats

#### T-API-01: Injection Attacks (SQLi, Command Injection, Stored XSS)
- **Threat:** Malicious characters injected into form fields or query parameters (`' OR 1=1`, `<script>`, `; rm -rf`).
- **Target:** API query filters, database queries, printable invoice HTML rendering.
- **Impact:** Database compromise, cross-site scripting on administrative workstations.
- **Controls & Mitigation:**
  - 100% parameterized queries via SQLAlchemy ORM; zero dynamic string concatenation in SQL statements.
  - Stored XSS defense in printable invoice renderer: all interpolated business fields (Company name, PAN, client, address, item names) are sanitized using `html.escape()`.
  - No shell command execution from web request context.

#### T-API-02: Path Traversal in Gallery File Storage
- **Threat:** Injected relative paths (`../../etc/passwd`) in filename parameters.
- **Target:** `POST /api/v1/gallery/upload/{product_id}`, `GET /api/v1/gallery/images/{image_id}/download`, `DELETE /api/v1/gallery/{image_id}`.
- **Impact:** Arbitrary file read or deletion on host filesystem.
- **Controls & Mitigation:**
  - Sanitization of uploaded filenames using regex `[^a-zA-Z0-9_.-]`.
  - Storage under dedicated UUID prefixes.
  - Defensive canonical path verification (`os.path.commonpath`) verifying that target files reside strictly within `UPLOAD_DIR`.

#### T-API-03: Information Disclosure via Error Responses
- **Threat:** Application crashes exposing database connection strings, stack traces, table names, or file paths.
- **Target:** Exception handling middleware (`global_exception_handler`, `http_exception_handler`).
- **Impact:** Reconnaissance aid for targeted attacks.
- **Controls & Mitigation:**
  - Global exception handler catches all unhandled exceptions, logs the full traceback internally with correlation ID, and returns a generic JSON response with HTTP 500: `"An unexpected error occurred. Please contact system administrator."`.
  - Sensitive internal database URLs and passwords never returned in HTTP bodies.

---

### 2.5 Operational & Infrastructure Threats

#### T-OPS-01: CORS & Cross-Origin Weaponization
- **Threat:** Malicious web origin initiates unauthorized cross-origin requests using browser credentials.
- **Target:** `CORSMiddleware`.
- **Impact:** Unauthorized API actions performed from third-party sites.
- **Controls & Mitigation:**
  - Wildcard `*` origins prohibited in production configuration.
  - Explicit origin whitelist (`settings.BACKEND_CORS_ORIGINS`) locked to trusted production frontend domains.
  - `allow_credentials=True` paired only with explicit trusted origin list.

#### T-OPS-02: Backup Data Exfiltration & Manipulation
- **Threat:** Unauthorized access to database backup archives or restore endpoints.
- **Target:** `POST /api/v1/backup/run`, `GET /api/v1/backup/status`.
- **Impact:** Complete database exfiltration, ransomware attack.
- **Controls & Mitigation:**
  - `/backup/run` is strictly restricted to `require_admin`.
  - Backup files written to dedicated isolated storage with restricted filesystem permissions.
  - Backups encrypted in transit to S3/B2 cloud object storage.

---

## 3. THREAT MITIGATION VERIFICATION MAPPING

| Threat ID | Category | Primary Defense | Automated Regression Suite |
|---|---|---|---|
| T-AUTH-01 | Authentication | Argon2id + Rate Limiter | `test_security_audit.py`, `test_checkpoint_16_rbac.py` |
| T-AUTH-02 | Authentication | httpOnly cookie + DB claim validation | `test_checkpoint_10_security.py`, `test_checkpoint_16_rbac.py` |
| T-AUTH-03 | Authentication | Cookie expiration & max_age=0 eviction | `test_checkpoint_16_rbac.py` |
| T-AUTHZ-01 | Authorization / Tenant | `TenantRepository` + FK validation | `test_checkpoint_16_tenant_isolation.py`, `test_checkpoint_16_idor.py` |
| T-AUTHZ-02 | Authorization / RBAC | Role dependency injection (`require_editor`/`require_admin`) | `test_checkpoint_16_rbac.py` |
| T-AUTHZ-03 | Authorization | Pydantic Schema whitelist + Repo override | `test_checkpoint_16_business_security.py` |
| T-BIZ-01 | Financial / Stock | Advisory lock + zero-floor check | `test_concurrency_race.py`, `test_checkpoint_16_business_security.py` |
| T-BIZ-02 | Financial / Sales | Credit advisory lock + limit calculation | `test_receivables.py`, `test_checkpoint_16_business_security.py` |
| T-BIZ-03 | Financial / Tax | Atomic document sequences + Schedule-5 void | `test_document_numbering_concurrency.py`, `test_checkpoint_16_business_security.py` |
| T-BIZ-04 | Business / Idempotency | Canonical payload hash + tenant scoping | `test_idempotency.py`, `test_checkpoint_16_business_security.py` |
| T-API-01 | AppSec / Injection | Parameterized queries + HTML entity escaping | `test_security_audit.py`, `test_checkpoint_16_business_security.py` |
| T-API-02 | AppSec / File Path | Path normalization & `UPLOAD_DIR` boundary | `test_checkpoint_16_idor.py` |
| T-API-03 | AppSec / Info Leak | Sanitized JSON exception handlers | `test_checkpoint_16_business_security.py` |
| T-OPS-01 | Operational / CORS | Strict origin matching + no wildcard credentials | `test_checkpoint_16_rbac.py` |
| T-OPS-02 | Operational / Backup | `require_admin` gate on backup triggers | `test_backup.py`, `test_checkpoint_16_rbac.py` |

---
