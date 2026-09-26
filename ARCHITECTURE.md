# ARCHITECTURE.md — LIVO GROUP OF INDUSTRIES

## 1. Why this changed from the original plan
Original plan: Electron + local SQLite, one Windows PC, no server. Client has
since said the software must work on **mobile and desktop**. A phone cannot
share a local SQLite file with a desktop app — the moment a second device
needs the same data, this becomes a **client-server system**. This is a
transport/deployment change; the ledger data model underneath is unchanged.

**This is a working default, not a client-confirmed decision** — see PRD.md
§8. Revisit if the client's answers land differently.

## 2. Stack
- **Backend:** FastAPI, exposing a versioned REST API (`/api/v1/...`).
- **Database:** Postgres from day one (revised 2026-09-25 — see §9). At 3–5
  users this is functionally equivalent to SQLite, but the client wants
  either "same client scales up" or "sold as a product to other companies"
  to stay possible, and both paths eventually hit SQLite's concurrency
  ceiling. Postgres costs nothing extra to run alongside the app on the
  same VPS (one more Docker container) and avoids a genuine data-migration
  project later. Use SQLAlchemy as the data-access layer regardless, so the
  ORM boundary — not raw SQL — is what talks to the database.
- **Frontend:** Next.js as a **responsive web app**, installable as a PWA on
  both desktop browsers and mobile home screens. One codebase, no app-store
  submission, no separate native build. Replaces the Electron shell.
- **Auth:** JWT session tokens, two roles (`editor`, `viewer`) enforced at the
  API layer, not just hidden in the UI.

## 3. Hosting (default: VPS — recurring cost needs client sign-off, PRD.md §8)
Default: a small always-on VPS (Hetzner/DigitalOcean, cheapest tier,
~$5–7/month), not the client's own PC. Reasoning, revised from the original
plan: hosting on the client's PC makes every router reboot, OS update, or
power cut a support incident for you personally — for software they depend
on daily, that's a worse deal than a few dollars a month. This does mean a
small recurring cost that sits in tension with "one-time payment, no
budget" — flag it to the client explicitly, don't assume they'll accept it
silently.

## 4. Offline model (redefined for multi-device)
Single-machine "offline-first" (just don't need internet) no longer applies
cleanly once a phone is a separate client. Default behavior for Phase 1,
chosen to avoid open-ended sync-conflict engineering under the deadline:
- **Reads:** last-fetched data cached client-side (service worker), viewable
  offline.
- **Writes:** require connectivity. No offline write queue, no conflict
  resolution in Phase 1 — if the phone or the hosting PC is offline, new
  entries wait until connectivity returns. This is a scope-reducing choice;
  revisit if the client needs guaranteed offline data entry on mobile.

## 5. Core data model (unchanged principle: ledgers, not editable balances)
Every business table below carries a `company_id` foreign key (see §9) —
today there's exactly one row in `companies` (LIVO GROUP), but the column
exists from the first migration, not added later.
- `companies` (id, name, ...) — one row today
- `suppliers`, `raw_materials`, `purchases`
- `products`, `production_batches`, `production_material_usage`,
  `production_worker_log`
- `stock_movements(product_id, quantity, direction, ref_type, ref_id, date)` —
  current stock = `SUM(direction * quantity)`
- `clients`, `sales_orders`, `sales_items`, `payments`
- `invoices` — sequential, immutable numbering
- `workers`, `attendance`, `payroll_entries` (Phase 2)
- `product_images` (Phase 2)
- `daily_summary(company_id, ...)` — precomputed nightly; dashboards read
  from this, never scan raw tables live
- `users(id, company_id, name, role, password_hash, active)`, `audit_log`
  (append-only) — **both carry `company_id`**, not just the business tables.
  A user must be scoped to a company at login, or a second company's
  addition later creates exactly the cross-tenant leak §9 is meant to
  prevent. This was missed in the first draft of this schema — fixed here.

## 6. API conventions
- One router per module (`purchase`, `production`, `stock`, `sales`, `hr`,
  `gallery`, `analytics`), Pydantic models for all request/response bodies.
- Every mutating endpoint writes an `audit_log` row (user_id, action, table,
  record_id, timestamp) inside the same transaction as the business write.
- Rate limiting on public-facing endpoints is now relevant (the API is
  internet-reachable, unlike the original local-only plan) — basic
  per-IP/per-user throttling, not the "5x load test" scale from generic
  templates. This app has 3 users; size the defenses to that, not to a
  SaaS threat model.

## 7. Dates, invoicing, backup — unchanged from original plan
- Every date stored as Gregorian; BS shown via UI toggle.
- Invoice PDF generation with sequential immutable numbering; VAT line
  present but off by default (client unconfirmed).
- Nightly backup job runs `pg_dump` (not a file copy — this is Postgres, not
  SQLite) and uploads the dump to cloud storage; failures surfaced in
  Settings, not silent; restore path tested before handover.

## 8. Observability & error handling — unchanged from RULES.md
Structured JSON logging, one global exception handler, React error boundaries
per major screen, "Send Diagnostics" button, visible version + DB self-check
on boot. See RULES.md for the full list — repeating it here would just drift
out of sync with the source of truth.

## 9. Scalability & multi-tenancy readiness (added 2026-09-25)
Client doesn't yet know if growth means "same company, more staff/branches"
or "sold to other footwear companies" — decided to keep both paths open
rather than guess. Principle: **build cheap optionality now, not speculative
features.** Nothing here is a SaaS product yet — no billing, no tenant
self-signup, no admin console. Just structural choices that cost almost
nothing today and would cost real time to retrofit.

- **`company_id` on every business table**, enforced through a single shared
  query/repository layer — application code never queries a business table
  without going through a helper that injects the current `company_id`
  filter. This makes "forgot to scope a query" structurally hard, not just
  a code-review hope. Today there's one company row; if a second company is
  ever added, existing code doesn't need to change, only the tenant-lookup
  step at login.
- **Invoice numbering is scoped per `company_id`**, not global — matters the
  moment there's more than one company, free to do correctly from the start.
- **Postgres, not SQLite** (see §2) — handles concurrent writes across many
  more users/devices than SQLite comfortably does, without an app-layer change.
- **Stateless API tier** — already true (JWT auth, no server-side session
  state). This means scaling from 1 to N users, or 1 backend container to
  several behind a load balancer, needs zero code changes — just more
  containers. Keep it this way: no in-memory caches or state that only one
  instance would know about.
- **Object storage for files, not local disk** — product images (gallery,
  Phase 2) and backup snapshots go to S3-compatible storage (Backblaze B2 or
  Cloudflare R2) from day one, not the VPS's local filesystem. Nearly the
  same effort now; avoids a painful migration once there's real file volume.
- **Indexes on foreign keys and commonly filtered columns** (`company_id`,
  date columns, product/client lookups) — cheap now, becomes load-bearing
  as row counts grow.
- **What's deliberately still NOT built:** connection pooling tuning, read
  replicas, horizontal auto-scaling, a task queue (Celery/RQ) for background
  jobs, multi-tenant billing/admin UI. These are real projects in their own
  right — build them if and when the growth path is confirmed, not
  speculatively now. The cron-based nightly backup and simple Docker Compose
  deploy from earlier sections are still correct for 3–5 users.

## 10. Security hardening (added on review — was missing from earlier drafts)
None of this is optional now that the API is internet-reachable and holds
~100 clients' financial data (receivables) and payroll advances.
- **Passwords:** hashed with bcrypt or argon2, never stored or logged in
  plaintext. This wasn't stated anywhere before this review pass — treat its
  absence in earlier docs as an oversight, not an intentional decision.
- **JWT storage:** httpOnly, Secure, SameSite cookie — not `localStorage`.
  A token in localStorage is readable by any injected script (XSS); a
  httpOnly cookie isn't.
- **CORS:** the API allows only the app's own frontend origin, not `*`.
- **Secrets** (DB credentials, JWT signing key, object-storage keys): environment
  variables injected at deploy time, never committed to the repo. A
  `.env.example` with blank values is fine to commit; `.env` itself is not.
- Deliberately not adopted at this scale: automated secret-scanning CI
  pipelines, WAF, dedicated pen-testing — revisit if this becomes the
  multi-tenant product path, not before.
