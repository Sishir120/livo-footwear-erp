# TASKS.md — LIVO GROUP OF INDUSTRIES Footwear ERP

Client wants a first working version in 10–15 days and named **daily report +
stock report** as the highest-priority feature. Printable invoices were
separately called essential. Client also wants desktop + mobile access
(confirmed after the original scope was set — see PRD.md §8 for the
still-open questions this raises). Phase split below assumes the
client-server default in ARCHITECTURE.md; revisit if the client's answers
change hosting or offline requirements.

## Phase 1 — MVP (target: 10–15 days)
Scope: daily operation + the two priority reports + invoicing, reachable from
desktop and mobile browsers. Excludes: HR/payroll, gallery, ranked/ratio
analytics beyond daily & stock, offline writes.

### 1.1 Foundation
- [ ] FastAPI backend scaffold + versioned API (`/api/v1`)
- [ ] Next.js responsive frontend (PWA-installable), no Electron
- [ ] Postgres DB + Alembic migrations wired up (SQLAlchemy as the data-access
      layer — see ARCHITECTURE.md §9 for why Postgres over SQLite now)
- [ ] `companies` table (one row: LIVO GROUP); `company_id` FK added to every
      business table from the first migration
- [ ] Shared tenant-scoped query/repository helper — no business-table query
      bypasses it (RULES.md hard rule)
- [ ] Object storage (Backblaze B2 or Cloudflare R2) configured for backups
      and future product images, instead of local VPS disk
- [ ] Hosting: VPS (committed default, ARCHITECTURE.md §3) — recurring cost
      still needs explicit client sign-off (PRD.md §8)
- [ ] `users` table + login; JWT auth in an httpOnly Secure cookie (not
      localStorage); passwords hashed with bcrypt/argon2; roles `editor` /
      `viewer`
- [ ] CORS locked to the app's own frontend origin; secrets via environment
      variables, never committed
- [ ] `audit_log` table (with `company_id`) + middleware that writes on every
      mutating request
- [ ] Global exception handler + structured JSON logging + rotating log file
- [ ] Basic rate limiting on public endpoints
- [ ] App shell: version number + DB self-check on boot

### 1.2 Purchase (raw materials)
- [ ] `suppliers`, `raw_materials`, `purchases` tables
- [ ] Entry screen: supplier, material, qty, date, amount
- [ ] List/filter view by date range

### 1.3 Production → Stock
- [ ] `products`, `production_batches`, `production_material_usage`,
      `production_worker_log` tables
- [ ] Production entry writes `stock_movements` (direction=in) — never edits
      a stock field directly
- [ ] Daily worker count + production quantity captured per batch (feeds §1.5)
- [ ] Stock list view: filter by item name/code, "pending stock" view

### 1.4 Sales & Invoicing
- [ ] `clients`, `sales_orders`, `sales_items`, `payments` tables
- [ ] Sale entry writes `stock_movements` (direction=out)
- [ ] Received vs. receivable tracking, payment date/method
- [ ] Order "delivered" toggle; filter by date/item/client
- [ ] `invoices` table, sequential immutable numbering
- [ ] Printable invoice template: company name, items, qty, PAN number, rate,
      date, amount, received amt, receivable amt — VAT line present but off
      by default

### 1.5 Reports (client's stated top priority)
- [ ] Daily report: production, sales, stock movement summary for a given day
- [ ] Stock report: current stock by item/code, pending stock
- [ ] Responsive layout for both — must be legible on a phone screen, not
      just shrunk desktop tables

### 1.6 Backup & migration
- [ ] Nightly/on-close backup job → cloud storage, failure surfaced in Settings
- [ ] Restore path documented and test-run once
- [ ] Historical data import script (3 months, both existing formats) — run
      against a DB copy first

### 1.7 Hardening before handover
- [ ] Unit tests: stock-movement balance math, invoice numbering (no
      gaps/reuse)
- [ ] Error boundaries on Purchase / Production / Stock / Sales screens
- [ ] "Send Diagnostics" button in Settings
- [ ] Confirm offline-read caching actually works on a phone with the
      connection dropped mid-session (client did ask for offline capability —
      Phase 1 gives read-only offline, verify that's understood and accepted)

## Phase 2 — Post-MVP
- [ ] HR/payroll module: worker profiles, salary/wage, overtime, advances,
      active toggle
- [ ] Clock-in/out tracking (client wants both this and monthly totals)
- [ ] Product gallery (upload/view/download by code+name)
- [ ] Full analytics: monthly/3-month/1-year ratios, most-selling products,
      top/repeated customers, worker/hours/production graphs
- [ ] BS/AD date toggle polish across all screens
- [ ] Revisit VAT flag if client confirms applicability
- [ ] Revisit offline writes / sync if client says mobile needs to work
      fully offline (this is a real re-architecture, not a small add-on —
      scope it separately if it comes up)

## Open items to resolve with client before/during Phase 1
- [ ] Does mobile need live-simultaneous data with desktop, or occasional
      viewing only? (drives whether Phase 1's "no offline writes" default holds)
- [ ] Hosting: client's PC via tunnel (free) vs. small cloud host (recurring
      cost)?
- [ ] Is the phone in addition to the "1 computer" answer, or replacing it?
- [ ] VAT applicability
- [ ] Exact format of the "both" existing record types for migration
- [ ] Handover deliverable and post-launch support model
