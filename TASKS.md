# TASKS.md — LIVO GROUP OF INDUSTRIES Footwear ERP

Client wants a first working version in 10–15 days and named **daily report + stock report** as the highest-priority feature. Printable invoices were separately called essential. Client also wants desktop + mobile access (confirmed after the original scope was set — see PRD.md §8).

**STATUS: ALL DEVELOPMENT, HARDENING, AND PRODUCTION AUDIT PHASES COMPLETED (CHECKPOINTS 1–18).**

---

## Phase 1 — MVP (Completed & Verified)
Scope: daily operation + the two priority reports + invoicing, reachable from desktop and mobile browsers.

### 1.1 Foundation
- [x] FastAPI backend scaffold + versioned API (`/api/v1`)
- [x] Next.js responsive frontend (PWA-installable), no Electron
- [x] Postgres DB + Alembic migrations wired up (`001_initial_schema` to `012_add_c15_indexes`)
- [x] `companies` table (LIVO GROUP); `company_id` FK added to every business table
- [x] Shared tenant-scoped query/repository helper (`TenantRepository`) enforcing multi-tenant isolation
- [x] Object storage (Backblaze B2 or Cloudflare R2 S3-compatible) configured for backups and product images
- [x] Hosting topology: VPS / Docker Compose + Caddy TLS reverse proxy default (ARCHITECTURE.md §3)
- [x] `users` table + login; JWT auth in an `httpOnly`, `Secure`, `SameSite` cookie; Argon2id password hashing; roles `admin`, `editor`, `viewer`
- [x] CORS locked to app frontend origin; secrets via environment variables, validated on startup
- [x] `audit_log` table (with `company_id`) + middleware that writes on every mutating request
- [x] Global exception handler + structured JSON logging + correlation IDs
- [x] Rate limiting on public and mutating endpoints (SlowAPI)
- [x] App shell: version number + DB self-check + network status badge on boot

### 1.2 Purchase (raw materials)
- [x] `suppliers`, `raw_materials`, `purchases` tables
- [x] Entry screen: supplier, material, qty, date, amount
- [x] List/filter view by date range

### 1.3 Production → Stock
- [x] `products`, `production_batches`, `production_material_usage`, `production_worker_log` tables
- [x] Production entry writes `stock_movements` (direction=1) — never edits stock directly
- [x] Daily worker count + production quantity captured per batch
- [x] Stock list view: filter by item name/code, pending stock view, size variants

### 1.4 Sales & Invoicing
- [x] `clients`, `sales_orders`, `sales_items`, `payments` tables
- [x] Sale entry writes `stock_movements` (direction=-1) with pessimistic locking and zero-floor defense
- [x] Received vs. receivable tracking, payment date/method, AR aging subledger
- [x] Order "delivered" toggle; filter by date/item/client
- [x] `invoices` table, sequential immutable numbering per company (`uq_invoice_company_sequence`)
- [x] Printable invoice template: company name, items, qty, PAN number, rate, date, amount, received amt, receivable amt, Nepal statutory 13% VAT line with XSS sanitization

### 1.5 Reports (client's stated top priority)
- [x] Daily report: production, sales, stock movement summary for a given day
- [x] Stock report: current stock by item/code, category filter, O(1) snapshot math
- [x] Responsive layout for both desktop and mobile viewports

### 1.6 Backup & migration
- [x] Automated backup service (`run_database_backup` via native `pg_dump`)
- [x] Restore path documented and empirically drill-tested (`restore_database_backup` via native `psql`) with 0% discrepancy
- [x] Incremental migration data preservation verified from revision 008 to HEAD

### 1.7 Hardening before handover
- [x] Unit & integration tests: 266 passed, 3 skipped across full backend suite
- [x] Error boundaries across all screens
- [x] System telemetry & diagnostics in Settings
- [x] Offline-read caching and idempotency-backed offline write queue with retry replay

---

## Phase 2 — Post-MVP Features (Completed & Verified)
- [x] HR/payroll module: worker profiles, salary/wage, overtime, advances, active status toggle
- [x] Clock-in/out tracking and monthly payroll summary
- [x] Product gallery: secure upload with MIME/magic-byte inspection, download, and deletion
- [x] Full analytics: monthly ratios, top-selling products, repeated customers, worker ratios
- [x] BS/AD dual calendar date conversion across all screens
- [x] Statutory Nepal VAT Schedule-5 compliance and void reversal ledger accounting
- [x] Offline sync reconciliation engine with tenant isolation and conflict prevention

---

## Phase 3 — Client Change Requests & Operational Extensions (Completed & Verified)
- [x] **REQ-A: Interactive Bikram Sambat (BS) Calendar Dropdown:** Native interactive calendar popup in [NepaliDatePicker.tsx](file:///d:/Antigravity/Footwear%20app/frontend/src/components/NepaliDatePicker.tsx) with day grid, Saturday highlighting, month/year navigation, and synchronous AD date calculation.
- [x] **REQ-B: Dispatch & Receipt Lifecycle:** Separate order vs. physical dispatch dates on sales (`POST /sales/orders/{id}/dispatch`) and order vs. physical receipt dates on purchases (`POST /purchase/purchases/{id}/receive`).
- [x] **REQ-C & REQ-F: Production Batches Custom Color & Factory Gallery Link:** Batch-level dynamic color field without SKU proliferation and direct linking between lot photos and batch records.
- [x] **REQ-D: Raw Material Stock Ledger & Units:** Append-only movement ledger with zero-floor defense, unit enforcement (`kg`, `pcs`, `litre`), and capitalized landed cost rate tracking.
- [x] **REQ-E: HR Worker Profiles & Citizenship Vault:** Worker profiles with temporary/permanent addresses, encrypted citizenship document vault with MIME magic-byte validation, and advance installment recovery engine.
- [x] **REQ-G: Multi-Column Landed Cost Ledger & Factory Expenses:** 4-column landed costs (carrying-in, import duty, China carrying-in, insurance) with live bottom totals and CSV export in [PurchaseView.tsx](file:///d:/Antigravity/Footwear%20app/frontend/src/components/PurchaseView.tsx), plus operational factory expenses tracking.
- [x] **REQ-H: Fixed Assets Register & Depreciation:** Asset acquisition ledger with dual dates, book value calculation, and automated depreciation schedule posting (`/api/v1/assets`).
- [x] **REQ-I: Waste Material & Scrap Management:** Production scrap records (`waste_records`) tracking offcuts, scrap revenue in paisa, and scrap recycling summaries (`/api/v1/waste`).
- [x] **REQ-J: Encrypted Automated Daily Backups:** Automated daily backup daemon with AES-256 encryption, local + cloud replication, and verified zero-loss restoration drill.

---

## Deployment & Production Readiness (Checkpoint 18 Status)
- [x] Container hardening: Non-root execution (`livo` UID 10001, `nodejs` UID 1001)
- [x] Health & readiness probes: `/health/live` (process) and `/health/ready` (database dependency)
- [x] Multi-tenant live attack validation: 100% foreign tenant reads/writes rejected with 403/404
- [x] Complete 23-step client operational acceptance workflow verified
- [x] Disaster recovery & backup restore drill verified on PostgreSQL
- [x] Performance smoke budgets verified (< 250ms on all core endpoints)
- [x] Release Status: **CONDITIONAL RELEASE** (Application stack 100% production-ready; awaiting client public domain DNS delegation and VPS hosting credentials).
