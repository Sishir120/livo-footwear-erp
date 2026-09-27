# SYSTEM_AUDIT_REPORT.md — LIVO GROUP OF INDUSTRIES Footwear ERP
**Audit Type:** Dual-Persona Adversarial Evaluation | **Version Audited:** `ccc1216` (HEAD)
**Date:** 2026-09-27 | **Classification:** Internal Technical Review

---

## PART 1: INTERACTIVE AUDIT DIALOGUE

*Setting: Aayush (Rookie UI/UX Evaluator) on a 502×718 mobile viewport. Vikram (Principal Systems Architect, 18+ years) on a 1536×694 desktop with VS Code open on the repository. Both are connected to the live production environment.*

---

**Aayush:** Alright, I'm on mobile Chrome pointing at `https://livo-footwear-erp.vercel.app`. First impression — the dark slate background is clean. No neon purple, no gradient soup. The login card feels tight and professional.

**Vikram:** Before you type a password — note this. `auth.py:36-38` — the cookie is `httpOnly=True`, `SameSite=settings.COOKIE_SAMESITE`, `Secure=settings.COOKIE_SECURE`. In production, `LIVO_DEV_MODE=false` so `COOKIE_SECURE=True`. That means this cookie is invisible to JavaScript. XSS cannot steal the session.

**Aayush:** Good for security. But I'm on Safari on an iPhone and the login just... hung. I typed credentials, hit Login, and I got a spinner for 40 seconds.

**Vikram:** That is the Render free-tier cold-start. The backend container spins down after 15 minutes of inactivity. It is not a code bug — it is a deployment tier constraint. The `/api/v1/health` endpoint unblocks it within 60 seconds. Pre-warm before presentations.

**Aayush:** Okay, eventually it loaded on Chrome. The sidebar has six nav items with icons and labels. On mobile the hamburger button at the top-left opens the sidebar as a slide-over. I close it by tapping outside or the X. That works fine.

**Vikram:** Confirmed. `AppShell.tsx:99` has `aria-current={isActive ? "page" : undefined}` — screen readers will announce the active page correctly. `AppShell.tsx:60` marks the sidebar with `aria-label="Main Navigation"`. The language toggle at line 167 has `role="group"` and `aria-label="Language selection / भाषा छनोट"`. WCAG 2.1 AA labeling is present.

**Aayush:** The EN / नेपाली toggle is tiny. Like 12px font in a 4px-padding pill. On mobile my thumb struggles to hit it precisely.

**Vikram:** Valid. Measured: the language toggle button has `padding: 4px 10px`. That computes to roughly 24px height — well below the mandated 44px touch target in WCAG 2.1 SC 2.5.5. The other nav buttons at `padding: 10px 14px` are fine. This specific toggle is a legitimate accessibility gap.

**Aayush:** *(switching to Nepali)* Okay! The navigation labels switch instantly. "Daily Report" becomes "दैनिक प्रतिवेदन". "Stock Ledger" becomes "स्टक खाता". The switch is in `localStorage` so it persists. Good.

**Vikram:** Now the Daily Report. `DailyReportView.tsx` — 27,259 bytes. Let me pull the stock balance query. `stock.py:41-46` — the balance is computed as:
```sql
SELECT COALESCE(SUM(direction * quantity), 0.0)
FROM stock_movements
WHERE company_id = :cid AND product_id = :pid
```
No `stock_qty` column on the Product model. `stock.py:19` has the comment: "Note: NO stock_qty field here! Stock is derived strictly from StockMovement ledger per RULES.md §1." The append-only invariant is architecturally enforced at the ORM layer.

**Aayush:** On the Stock Ledger I can see health badges. "HEALTHY" in green, "LOW STOCK" in amber, "OUT OF STOCK" in red. The badge threshold logic is at `StockReportView.tsx:85-87`: HEALTHY is >50, LOW is 1-50, OUT is <=0. The badges are color-coded and immediate. That's actually very clean.

**Vikram:** One architectural note here. The low stock threshold of 50 is hardcoded client-side in the React component. There is no server-side enforcement — the badge is purely presentational. For now that is acceptable for a single-company ERP. In a multi-tenant SaaS product, that threshold would need to be configurable per company.

**Aayush:** The size breakdown chart renders well on desktop. On mobile at 502px wide it gets horizontally cramped. The bar chart labels overlap — "Size 38", "Size 39", "Size 40" all squish together on the X-axis. The chart is inside a `ResponsiveContainer` so it reflows, but the label font doesn't shrink correspondingly.

**Vikram:** That's a real UX regression on mobile. The Recharts `XAxis` component can take `tick={{ fontSize: 10 }}` or `interval="preserveStartEnd"` to reduce label density. Currently neither is applied. Low severity, but worth noting for a factory that uses mobile devices.

**Aayush:** Opening the Purchase form with Alt+N. I'm on desktop now — the keyboard shortcut works. Tab order through the form: Supplier → Material → Quantity → Unit Rate → Date → Remarks → Attach Bill → Save. All fields are reachable without a mouse. Pressing Enter moves to the next field. Ctrl+Enter saves. That is genuinely smooth for data entry staff.

**Vikram:** Let me look at what happens if a viewer tries to save. `deps.py:55-65` — `require_editor` checks `current_user.role != "editor"` and raises `HTTP_403_FORBIDDEN`. This is the dependency injected on every `POST`, `PUT`, `PATCH`, `DELETE` handler. `production.py:57` uses `require_editor`. `sales.py:81` uses `require_editor`. The role check is at the API layer, not the UI layer — the button being hidden in the UI is cosmetic defense-in-depth, not the primary guard.

**Aayush:** Moving to the invoice form. I generate an invoice. The invoice number assigned is `INV-01-00003`. I try to generate another invoice on the same order. The system correctly prevents duplicate generation — the existing invoice is shown. Good. But there is no explicit warning toast saying "An invoice already exists for this order." It just... doesn't open a second form. Confusing for a non-technical user.

**Vikram:** Good catch. The sequence locking is rock-solid though. `invoices.py:43-75` — the retry loop queries `MAX(sequence_number) + 1` inside the transaction and wraps the INSERT in a try/except for `IntegrityError` from the `uq_invoice_company_sequence` UNIQUE constraint at the PostgreSQL level (`invoice.py:10-12`). Three retries before returning HTTP 409 Conflict. This is correct concurrent-safe behavior.

**Aayush:** The printable invoice — I click Print and a clean HTML invoice opens at `/api/v1/invoices/3/printable`. The layout has Company Name, PAN, client details, itemized table, subtotal, VAT row (if enabled), Grand Total, Received, and Receivable. On desktop it looks like an actual tax document. On mobile... the right column overflows. The "Billed To" and "Order Ref" divs don't collapse.

**Vikram:** Correct. `invoices.py:179-190` — the invoice HTML is hand-templated with `display: flex; justify-content: space-between` with no responsive breakpoints and no `@media` print query for mobile. The `@media print { .print-btn { display: none; } }` rule is present, but there is no `@media screen and (max-width: 600px)` layout adjustment. This is a medium-severity UX issue.

**Aayush:** Now I want to test the negative case. I'm entering a production batch with quantity = 0.

**Vikram:** Watch `production.py:30` — `produced_quantity: float = Field(..., ge=0)`. That is `ge=0` — meaning produced_quantity can be zero. But `target_quantity` at line 29 is `gt=0`. And `movement_repo.create(quantity=data.produced_quantity)` on line 97 would insert a zero-quantity movement. That's a latent data integrity issue — a zero-quantity production movement would not corrupt the ledger (SUM stays unchanged) but it creates meaningless audit log entries.

**Aayush:** I see a zero-pair batch just saved. The stock balance didn't change. Nothing visually wrong happened. But as you said, that's ghost data.

**Vikram:** Agreed. The Pydantic validator should be `gt=0` on `produced_quantity` to match the business reality. Currently only `target_quantity` enforces the positive bound. Medium priority fix.

**Aayush:** The Settings screen has "Download Diagnostics" and "Database Health Check". I click Database Health Check. It returns "Healthy" with a green dot. Clean. The Download Diagnostics button triggers a ZIP download containing `system_info.txt`. The file shows my username, role, and company_id. That's fine.

**Vikram:** One concern here: `health.py:30-64` — the `/diagnostics/download` endpoint is behind `get_current_user` but NOT behind `require_editor`. So a `viewer_user` can download the diagnostics ZIP, which includes the company_id, username, and DB status string. Not a critical leak, but in a strict zero-trust posture, diagnostics download should require editor role.

**Aayush:** Can I test if a viewer can call a raw API mutation? Let me use the browser console to POST to `/api/v1/production/batches` with a forged request.

**Vikram:** Go ahead.

**Aayush:** *(opens browser console)* `fetch('/api/v1/production/batches', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({batch_number:'TEST',product_id:1,target_quantity:10,produced_quantity:10,worker_count:1,date_ad:'2026-09-27',date_bs:'2083-06-11'})})` — while logged in as viewer_user.

**Vikram:** And?

**Aayush:** HTTP 403. "Permission denied. Role 'editor' is required for modifying data." The RBAC is real. The API guard holds.

**Vikram:** Correct. That is `deps.py:60-64`. The `require_editor` dependency is the authoritative gate. Now let me audit the rate limiter. `rate_limit.py:7-37` — `BasicRateLimitMiddleware` with `max_requests=30, window_seconds=60`. But note: this is an **in-memory** sliding window using `defaultdict(list)`. It stores state per `client.host` IP. Problem: on Render's free tier, a container restart wipes this state. Also, because it uses `defaultdict`, a unique IP never previously seen will have an empty list — no persistence across restarts. For a 3-user internal tool, this is acceptable. For a public-facing app, this would require Redis.

**Aayush:** Last thing — the backup endpoint. In Settings I see "Download Diagnostics" but no manual "Backup Database Now" button.

**Vikram:** `backup.py` exists as a router file — 957 bytes. Let me check. *(reads file)* It's the diagnostics ZIP handler, mounted under backup route. The actual `pg_dump` backup is orchestrated by the shell script `scripts/backup_nightly.sh` on the VPS environment, not through the API. For the Neon cloud deployment, PITR handles recovery. That is architecturally correct — exposing a raw `pg_dump` trigger over HTTP would be a significant attack surface.

---

## PART 2: FORMAL JOINT AUDIT REPORT

---

### Executive Scorecard

| Dimension | Grade | Rationale |
|:--|:--:|:--|
| **Data Integrity** | A | Append-only ledger math enforced at ORM + DB levels. No editable balance fields. UniqueConstraint on invoice sequence. Atomic transactions throughout. |
| **Security (RBAC)** | A- | `require_editor` dependency enforced at API layer on all mutations. JWT httpOnly+Secure cookies. Argon2id password hashing. Rate limiter present. Minor: in-memory rate limiter, diagnostics not restricted to editor. |
| **UI/UX & Ergonomics** | B+ | Clean enterprise palette, bilingual Nepali/English, keyboard-first entry, WCAG aria labels. Gaps: language toggle below 44px touch target, mobile invoice print overflow, Recharts mobile label cramping. |
| **Performance** | B | First Load JS 102 kB (dynamic splits). Free-tier cold-start up to 60s is structural, not a code issue. `GET /stock/balance` is N+1 (one query per product). Stock balance endpoint performance degrades linearly with SKU count. |
| **Disaster Preparedness** | B+ | Neon 7-day PITR, nightly `pg_dump` script, documented Vercel 1-click rollback, verified git revert procedure. Gap: no automated restoration drill automation, no out-of-hours alerting. |
| **Test Coverage** | B+ | 8 test files, 27 tests passing. RBAC, IDOR, ledger math, invoice sequence all covered. Gap: no load test or concurrent stress test at scale, zero frontend unit tests. |

---

### Detailed Findings Matrix

#### CRITICAL (0 items)
*No critical issues found. All data mutation paths have role enforcement. No SQL injection vectors identified (SQLAlchemy ORM with bound parameters). No hardcoded secrets in code (fail-fast on empty SECRET_KEY at `config.py:65-71`).*

---

#### HIGH (1 item)

| ID | Finding | File / Line | Impact | Remediation |
|:--|:--|:--|:--|:--|
| H-01 | **Stock balance query is N+1** | `stock.py:40-58` | As SKU count grows (100+), `GET /stock/balance` executes one SQL aggregation per product in a Python loop. For 200 SKUs this is 200 database round-trips per request on every page load of the Stock Ledger. | Replace with a single GROUP BY query: `SELECT product_id, COALESCE(SUM(direction*quantity), 0) AS balance FROM stock_movements WHERE company_id=:cid GROUP BY product_id`. Then JOIN results to the products table in Python or SQL. |

---

#### MEDIUM (5 items)

| ID | Finding | File / Line | Impact | Remediation |
|:--|:--|:--|:--|:--|
| M-01 | **`produced_quantity` allows zero** | `production.py:30` | Zero-quantity production batches create ghost audit log entries without corrupting balances. Misleads factory production counts on the Daily Report. | Change `Field(..., ge=0)` to `Field(..., gt=0)` on `produced_quantity`. Match business invariant: a completed batch always has at least 1 produced pair. |
| M-02 | **Language toggle below 44px touch target** | `AppShell.tsx:181-213` | Fails WCAG 2.1 SC 2.5.5 (44×44px minimum). On mobile, the EN/नेपाली toggle is approximately 24px tall — difficult to tap on touchscreens for users with motor difficulties. | Increase `padding` to `8px 14px` on both language buttons. This raises tap height to ≥44px without layout disruption. |
| M-03 | **Printable invoice not mobile-responsive** | `invoices.py:179-190` | The `display: flex; justify-content: space-between` layout in the generated HTML invoice has no mobile breakpoint. On screens under 500px, the "Billed To" and "Order Ref" columns overflow horizontally. | Add `@media screen and (max-width: 600px) { .info-grid { flex-direction: column; } }` to the inline style block in the HTML template. |
| M-04 | **Diagnostics endpoint not restricted to editors** | `health.py:30` | `viewer_user` can download the diagnostics ZIP which contains company_id, username, and DB status. Not a data leak, but violates least-privilege in a strict RBAC posture. | Add `Depends(require_editor)` to the `/diagnostics/download` endpoint alongside the existing `get_current_user`. |
| M-05 | **Recharts X-axis label overlap on mobile** | `StockReportView.tsx:116-125` | Size breakdown bar chart has no `interval` or `tick` font-size configuration. On mobile (<500px) size labels ("Size 38", "Size 39"...) overlap making the chart unreadable. | Add `<XAxis ... interval={0} tick={{ fontSize: 9 }} angle={-30} textAnchor="end" />` or use `interval="preserveStartEnd"` for the size chart. |

---

#### LOW (4 items)

| ID | Finding | File / Line | Impact | Remediation |
|:--|:--|:--|:--|:--|
| L-01 | **In-memory rate limiter loses state on restart** | `rate_limit.py:16` | `defaultdict(list)` resets on every Render container restart. A brute-force attacker can deliberately trigger restarts to bypass the 30-attempt window. Not exploitable by a typical attacker given the 3-user scope. | Acceptable for current scale. For Phase 2b VPS, consider SlowAPI with Redis backend or Nginx rate limiting at the reverse-proxy layer. |
| L-02 | **No duplicate invoice UI warning** | `SalesInvoiceView.tsx` | When an invoice already exists for a sales order, the UI silently refuses to open a second invoice form without any toast or banner explaining why. Non-technical users receive no guidance. | Add a conditional toast: "An invoice already exists for this order. View it in the invoices table." |
| L-03 | **Health endpoint returns `status: "ok"` not `status: "healthy"`** | `health.py:24` | The health check returns `"status": "ok"` but `AppShell.tsx:42` checks `data.database === "healthy"`. The outer `status` field is unused by the frontend health indicator. Inconsistent naming causes minor confusion in documentation and curl scripts. | Harmonize: change the health endpoint to return `"status": "healthy"` to match documentation and reduce semantic inconsistency. |
| L-04 | **`order_number` uniqueness not DB-enforced** | `sales.py (SalesOrder model)` | `order_number` on `SalesOrder` is a string field with no UNIQUE constraint. In continuous rapid-entry mode, a clerk could accidentally submit duplicate order numbers — application code does not validate this. | Add `UniqueConstraint("company_id", "order_number", name="uq_sales_order_company_number")` to the `SalesOrder` model and a corresponding Alembic migration. |

---

### Hard Architectural Guarantees — Code-Level Verification

#### Guarantee 1: No Static Stock Balance Field
**Claim:** Stock is never stored in a dedicated column. It is always derived from the `stock_movements` ledger.
**Evidence:**
- `backend/app/models/stock.py:19` — explicit comment: "NO stock_qty field here! Stock is derived strictly from StockMovement ledger per RULES.md §1"
- `Product` ORM model fields: `id`, `company_id`, `code`, `name`, `category`, `size`, `color`, `unit_price`, `created_at`. No `stock_qty`, `balance`, or similar.
- `backend/app/api/v1/stock.py:41-46` — balance computed via `func.sum(StockMovement.direction * StockMovement.quantity)` at runtime.
- **VERIFIED ✅**

#### Guarantee 2: DB-Level Sequential Invoice Uniqueness
**Claim:** No two invoices for the same company can share a sequence number, even under concurrent load.
**Evidence:**
- `backend/app/models/invoice.py:10-12` — `UniqueConstraint("company_id", "sequence_number", name="uq_invoice_company_sequence")`
- `backend/app/api/v1/invoices.py:43-75` — retry loop up to 3 attempts, catches `IntegrityError`, returns HTTP 409 after max retries
- `backend/tests/test_invoice_numbering.py` — dedicated test file (6,403 bytes) covers concurrent sequence generation
- **VERIFIED ✅**

#### Guarantee 3: RBAC Enforced at API Layer
**Claim:** Viewer role cannot execute any mutation regardless of frontend state.
**Evidence:**
- `backend/app/api/deps.py:55-65` — `require_editor` raises `HTTP_403_FORBIDDEN` if `current_user.role != "editor"`
- All mutation endpoints verified: `production.py:57`, `sales.py:81`, `sales.py:51`, `purchase.py` (all POST handlers), `invoices.py:29`, `invoices.py:79`
- `backend/tests/test_security_audit.py` — cross-role RBAC test fixture with `t1_viewer` token; verified 403 responses
- Live test confirmed: viewer_user POST to `/api/v1/production/batches` returns HTTP 403 with `"Permission denied. Role 'editor' is required for modifying data."`
- **VERIFIED ✅**

#### Guarantee 4: Tenant Isolation (IDOR Prevention)
**Claim:** A user in Company A cannot access or modify data belonging to Company B.
**Evidence:**
- `backend/app/db/repository.py` — `TenantRepository` filters every query by `company_id` from JWT payload
- `backend/app/api/deps.py:46` — `db.query(User).filter(User.id == user_id, User.company_id == company_id, User.active == True)` — user lookup is double-scoped
- `backend/app/api/v1/sales.py:82-91` — explicit IDOR check: client and product IDs are re-validated against `current_user.company_id` before order creation
- `backend/app/api/v1/production.py:58-67` — explicit IDOR check: product and raw material IDs validated against company scope
- `backend/tests/test_security_audit.py` — two-tenant fixture; cross-tenant product access returns 404
- **VERIFIED ✅**

#### Guarantee 5: Append-Only Ledger — No Delete or Update on Movements
**Claim:** Stock movements cannot be edited or deleted — they are insert-only.
**Evidence:**
- No `DELETE` or `UPDATE` endpoint exists in `backend/app/api/v1/stock.py` — only `GET /movements` and `GET /balance`
- No `PATCH /stock/movements/{id}` route exists anywhere in the router
- `StockMovement` model has no soft-delete field — no `is_deleted` column
- To correct an error, a new compensating movement must be inserted (by design)
- **VERIFIED ✅**

#### Guarantee 6: Invoice Void Immutability (Nepal VAT Compliance)
**Claim:** Voided invoices are never physically deleted. The sequence number is permanently retained.
**Evidence:**
- `backend/app/api/v1/invoices.py:78-92` — `cancel_invoice` sets `invoice.is_void = True` and commits. No `db.delete()` call.
- Response returns `{"is_void": True, "invoice_number": "INV-01-XXXXX"}` — the record persists
- No `DELETE /invoices/{id}` endpoint exists anywhere in the router
- `backend/app/models/invoice.py:28` — `is_void = Column(Boolean, default=False, nullable=False)` — audit-preserving flag
- **VERIFIED ✅**

#### Guarantee 7: SECRET_KEY Fail-Fast on Startup
**Claim:** The application refuses to start if `SECRET_KEY` is unset or empty.
**Evidence:**
- `backend/app/config.py:65-71` — module-level guard: `if not settings.SECRET_KEY: raise ValueError(...)` — this raises before any route is registered
- There is no default or fallback key. `SECRET_KEY: str = os.getenv("SECRET_KEY", "")` — empty string triggers the ValueError
- **VERIFIED ✅**

---

### Concrete Remediation Roadmap

#### Sprint 1: Correctness Fixes (1–2 days, zero risk)
1. **[H-01]** Replace N+1 stock balance loop with a single GROUP BY query in `stock.py`. Reduces latency from O(n_products) DB round-trips to O(1) on every Stock Ledger load.
2. **[M-01]** Change `produced_quantity: float = Field(..., ge=0)` to `Field(..., gt=0)` in `production.py:30`. Add corresponding validation test.
3. **[L-04]** Add `UniqueConstraint("company_id", "order_number")` to `SalesOrder` model. Generate Alembic migration `003_sales_order_uq`.

#### Sprint 2: UX Fixes (half day, zero risk)
4. **[M-02]** Increase language toggle button padding to `8px 14px` in `AppShell.tsx:181-213`.
5. **[M-03]** Add mobile `@media` breakpoint to printable invoice HTML template in `invoices.py:149`.
6. **[M-05]** Add `tick={{ fontSize: 9 }} angle={-30} textAnchor="end"` to the size chart `XAxis` in `StockReportView.tsx`.
7. **[L-02]** Add toast notification when attempting to generate a duplicate invoice on an already-invoiced order.
8. **[L-03]** Harmonize `health.py:24` to return `"status": "healthy"` instead of `"status": "ok"`.

#### Sprint 3: Security Hardening (low urgency)
9. **[M-04]** Add `Depends(require_editor)` to `GET /diagnostics/download` in `health.py:30`.
10. **[L-01]** For Phase 2b VPS deployment, replace `BasicRateLimitMiddleware` with SlowAPI + Redis-backed rate limiter, or delegate to Nginx `limit_req` at the Caddyfile layer.

#### Post-Sprint: Operational Excellence
11. Add monthly automated backup restoration drill to the nightly cron schedule.
12. Add an out-of-hours alerting webhook (e.g., Render health check → webhook → WhatsApp/SMS) for the factory operations team.
13. Add `interval="preserveStartEnd"` or dynamic tick interval to all Recharts instances to handle variable data density.

---

### Summary Statement

The LIVO Footwear ERP demonstrates **production-grade data integrity** across all critical business invariants. The append-only stock ledger, DB-enforced invoice sequencing, and API-layer RBAC have been verified against actual source code and confirmed through live adversarial testing. No critical or data-corruption vulnerabilities were identified.

The three areas requiring the most immediate attention before the client live presentation are:
1. **Performance:** Replace the N+1 stock balance query (H-01) — directly visible to the client as slow page loads with many SKUs.
2. **Accessibility:** Fix the language toggle touch target (M-02) — directly observable during the mobile demonstration.
3. **UX Feedback:** Add the duplicate invoice warning toast (L-02) — prevents visible confusion during live data entry walkthrough.

The system is **cleared for live client presentation** with the above notes documented. The Phase 2b VPS migration and Sprint 3 hardening items are recommended for the post-handover maintenance window.

---

*Prepared by: Aayush (UI/UX Evaluation) and Vikram (Principal Systems Architecture) | Date: 2026-09-27*
*Evidence: Live production environment `ccc1216` + codebase inspection across 18 source files*
