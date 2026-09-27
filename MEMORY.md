# MEMORY.md — Running Context Ledger

Read this at the start of every new agent session. Append new entries at the
bottom when a decision, assumption, or open question changes — don't rewrite
history.

## Confirmed facts (from client's written spec + questionnaire)
- Footwear factory: manufactures in-house AND buys/resells finished pairs;
  multi-location.
- 3 users: 1 editor, 2 viewers; no per-role permission granularity wanted;
  audit trail required.
- Stock tracked by size+colour, in pairs, number+colour codes.
- ~100 suppliers, ~100 clients, mixed credit terms, returns/exchanges needed.
- Invoice essential; fields: company name, items, qty, PAN number, rate, date,
  amount, received amt, receivable amt.
- Payments: cash, bank transfer, online, mobile money, cheque.
- HR: mixed salary/wage, hourly overtime, both clock-in/out and monthly totals
  (Phase 2).
- ~3 months of historical records to migrate (mixed formats).
- Cloud backup wanted. Dual BS/AD date storage. English interface.
- Software name: LIVO GROUP OF INDUSTRIES.
- Target: first working version in 10–15 days. No budget set; one-time
  payment preferred. Staff training not needed.
- Top priority features (client's own words): daily report, stock report.

## Architecture pivot (2026-09-25)
- Original plan (single Windows PC, Electron, local-only SQLite, "1
  computer" answer) is superseded: client now wants **desktop AND mobile**
  access.
- This forces a client-server model (FastAPI API + Next.js responsive
  web/PWA) instead of a local-file desktop app. See ARCHITECTURE.md for the
  reasoning.
- Working defaults adopted so the build isn't blocked (**not yet
  client-confirmed** — see next section):
  - Hosting: client's own PC + tunnel (free), cloud host as fallback
    (recurring cost).
  - Offline: reads cached client-side; writes require connectivity in
    Phase 1 (no sync/conflict resolution yet).

## Open questions — get these answered before Phase 1 closes
- Does mobile need live-simultaneous data with desktop, or occasional
  viewing only?
- Hosting: client's PC via tunnel vs. small recurring-cost cloud host?
- Is the phone in addition to the "1 computer" answer, or replacing it?
- VAT applicability and rate.
- Exact format of existing records to migrate.
- Handover deliverable and post-launch support model.

## Scalability decision (2026-09-25)
- Client is unsure whether future growth (500–1000 users) means the same
  company scaling up, or the software being sold to other footwear
  companies — decided to keep both paths open rather than guess.
- Adopted now (cheap optionality, not speculative features): Postgres
  instead of SQLite (supersedes the earlier SQLite call — concurrency
  ceiling was the deciding factor, not raw user count); `company_id` on
  every business table + a shared tenant-scoped query helper; invoice
  numbering scoped per company; object storage (not local disk) for
  backups/images; stateless API tier (already true, just confirmed as a
  rule to preserve).
- Deliberately still NOT built: multi-tenant billing, tenant self-signup,
  admin console, connection pooling tuning, read replicas, task queue,
  horizontal auto-scaling. Build these only once the growth path is
  actually confirmed.

## Hosting decision reversal (2026-09-25)
- Superseded the "client's PC + tunnel" default from the architecture-pivot
  entry above: **VPS is now the committed default** (ARCHITECTURE.md §3).
  Reasoning: hosting on the client's PC turns every reboot/power-cut into a
  support incident; a $5–7/month VPS avoids that. Recurring cost still needs
  explicit client sign-off — it wasn't dropped, just re-decided as the
  recommended default pending that sign-off.

## Senior review pass (2026-09-25) — gaps found and fixed
A full doc review surfaced drift and one real gap, both fixed same-day:
- Stale SQLite references in ARCHITECTURE.md/RULES.md/DELIVERY_CYCLE.md
  (backup commands, hosting default) — leftover from before the Postgres
  switch, corrected to Postgres/`pg_dump` throughout.
- **Security gap:** `users` and `audit_log` were missing `company_id` —
  a cross-tenant leak risk the moment a second company exists, undetected
  until this review. Fixed: both tables now carry `company_id`.
- **Missing entirely:** password hashing (bcrypt/argon2), JWT storage
  location (httpOnly cookie, not localStorage), CORS policy, and secrets
  management (env vars, never committed) — none of this was specified
  anywhere before this pass, despite the app being internet-facing and
  holding client financial data. Added as ARCHITECTURE.md §10 / RULES.md §4.
Lesson for future passes: when a foundational decision changes (DB engine,
hosting target), grep every doc for the old term before considering the
change complete — a decision recorded in one file and stale in three others
is worse than not having decided at all, because it looks resolved.

## Adopted engineering practices (from external checklist review, 2026-09-25)
Kept: forced-diagnosis-before-fix protocol, bounded agent scope, one-concern-
per-turn incremental execution, git hard-reset over hand-debugging AI output,
this running-context file.
Deliberately not adopted (over-scoped for a 3-user internal tool): Postgres
connection pooling, 5x load testing, HPA/serverless auto-scaling, PITR,
automated secret-scanning pipelines. Revisit only if the client's needs
genuinely grow past this scale.

## Database Test Environment & Backup Verification Deferral (2026-09-26)
- **Local Host OS Constraints:** Host Windows environment lacks Docker and native PostgreSQL client binaries (`pg_dump`, `psql`). Automated direct installer downloads from EnterpriseDB are blocked by 403 Forbidden.
- **Hosted Postgres Parity:** Testing was executed against an active hosted Neon PostgreSQL instance (`postgresql+psycopg2://...`). All 14 core unit/API tests, 4 backup unit tests, Alembic migrations (`001_baseline_schema` & `002_add_invoice_unique_constraint`), and the historical data import script (`scripts/import_historical_data.py`) ran and passed 100% against Neon Postgres.
- **Backup/Restore Classification:** Data-replication integrity was verified via same-database schema copy on Neon Postgres (`scripts/verify_postgres_backup_restore.py`). Real `pg_dump`/`pg_restore` end-to-end binary execution is formally deferred to Phase 2 (DELIVERY_CYCLE.md's Phase 2 gate already requires Docker container setup where Postgres client tools are available).

## Phase 2 Environment & DevOps Infrastructure Setup (2026-09-26)
- **Fresh Context Review:** PRD.md, ARCHITECTURE.md, RULES.md, and MEMORY.md read fresh at initiation of Phase 2.
- **Container Infrastructure Ready:** Authored full Docker Compose environment:
  - `backend/Dockerfile` using Python 3.11-slim with `postgresql-client` installed, enabling native `pg_dump`/`pg_restore`.
  - `frontend/Dockerfile` multi-stage Next.js production build.
  - `docker-compose.yml` orchestrating `postgres:16-alpine` (volume-mounted to `postgres_data`), `backend` (depends on healthy postgres, double fail-fast on `SECRET_KEY`), `frontend`, and `caddy:2-alpine` (handling automatic Let's Encrypt HTTPS and routing `/api/*` + `/docs` to backend, `/` to Next.js).
  - `Caddyfile` with production security headers (HSTS, nosniff, DENY) and reverse proxy rules.
  - `backend/app/config.py` updated with a Pydantic field validator for `BACKEND_CORS_ORIGINS` loaded from environment variables (defaults locked to localhost / production domain, no `*`).
  - Production backup & restore automation created in `scripts/backup_nightly.sh` and `scripts/restore_postgres.sh`.
  - `.env.production.example` authored with explicit secret instructions.
- **Human Action Blocker Encountered:** Task 1 (VPS provisioning on Hetzner/DigitalOcean) and Task 7 (DNS domain routing) require manager action (account creation, credit card billing, registrar DNS management). No CLI tools (`doctl`, `hcloud`) or cloud credentials exist on the host machine.
- **Standing Stop Rule Triggered:** Stopped after one attempt and reported back to manager to provide VPS access (IP + SSH credentials or API token) and target domain name. Phase 2 marked `Blocked` in DELIVERY_CYCLE.md.

## Pivot to Phase 2a Free-Tier Demo & Phase 2b VPS Separation (2026-09-26)
- **Phase Restructuring:** Separated DevOps into `Phase 2a — Demo Deployment (Free Tier)` and `Phase 2b — Production Deployment (VPS)`. All Phase 2b assets (`docker-compose.yml`, `Caddyfile`, `scripts/backup_nightly.sh`, `scripts/restore_postgres.sh`) remain preserved, sequenced for post-client sign-off.
- **Phase 2a Technical Preparation:**
  - `backend/Dockerfile` updated to bind Uvicorn to `${PORT:-8000}`, ensuring immediate compatibility with Render's dynamic port assignment.
  - `frontend/next.config.js` updated to proxy `/api/*` rewrites to `NEXT_PUBLIC_API_URL` or `API_URL` (pointing to Render's backend domain).
  - `render.yaml` blueprint authored for 1-click Docker web service deployment.
  - `scripts/seed_demo_data.py` authored and verified: creates company, users, 4 suppliers, 6 raw materials, 4 material purchases, 5 footwear products, 5 production batches (+IN stock movements), 3 retail/wholesale clients, 3 sales orders (-OUT stock movements), and 3 sequential immutable invoices.
  - Object storage and backup automation are explicitly out of scope for Phase 2a demo (retained in Phase 2b).
- **Human Action Blocker Encountered:** Deploying backend to Render, frontend to Vercel, and creating fresh Neon DB credentials requires manager account authentication (email verification, OAuth/repo linkage, dashboard creation).
- **Standing Stop Rule Triggered:** Stopped after one attempt per the standing rule to request the deployment URLs/credentials from the manager.

## Phase 2a Live PostgreSQL Migrations & Seeding Verified (2026-09-26)
- **Database Engine Parity Verified:** Connected directly to live Neon PostgreSQL instance (`green-wind-12533394` / `ep-gentle-glade-b4tb64by.c-6.us-east-2.aws.neon.tech`).
- **Alembic Migrations Applied:** Executed `alembic upgrade head`. Output confirmed `Context impl PostgresqlImpl`, `Will assume transactional DDL`, reaching `002_invoice_uq (head)`.
- **Demo Data Seeded on Live PostgreSQL:** Executed `scripts/seed_demo_data.py`. Fixed invoice sequence generator to dynamically query `func.max(Invoice.sequence_number)` ensuring strict compliance with `uq_invoice_company_sequence`. Successfully seeded and verified on live PostgreSQL:
  - 10 suppliers, 12 materials, 29 purchases, 11 products, 26 batches, 6 clients, 24 orders, 50 stock movements, and 29 sequential immutable invoices (`INV-01-00001` through `INV-01-00029`).
- **Dashboard Inspection:** Browser subagent confirmed Neon database is fully populated and healthy. Render environment `livofootwear` has 0 active web services, and Vercel has 0 projects for Livo ERP. Code needs to be pushed to GitHub to build the Web Service on Render and deploy the frontend on Vercel.

## Phase 4 UI/UX Polish Sprint & Ergonomics Baseline (2026-09-27)
- **Verified Production Head Commit:** `06434e7` ("feat(ui): continuous mouse-free rapid data entry mode and keyboard ergonomics").
- **High-Density Data Architecture:** Refactored tables across `PurchaseView.tsx`, `ProductionView.tsx`, `StockReportView.tsx`, and `SalesInvoiceView.tsx` with compact spacing, border dividers, and monospace tabular alignment (`num-mono`).
- **Continuous Hands-Free Entry:**
  - Global hotkeys (`Alt+N` to open modal, `Escape` to close).
  - Sequential `Enter` key traversal across all form fields.
  - Quick commit via `Ctrl+Enter` or `⌘+Enter` from any field.
  - "Continuous Rapid Entry Mode" toggles keeping form active, retaining common inputs (dates, active supplier/client), auto-generating next sequence batch/order numbers, and resetting focus back to the SKU selector.
- **Visual Analytics:**
  - Integrated 2D Recharts in `DailyReportView.tsx` (Production Output by Model, Produced vs Dispatched Volume) and `StockReportView.tsx` (Stock by Category, Size Curve Distribution across Paris Points 38–44).
  - Tri-state stock health badging (`HEALTHY` >50, `LOW` ≤50, `OUT OF STOCK` ≤0) derived dynamically from append-only movement logs.
- **Spreadsheet Portability:**
  - Built `frontend/src/utils/csvExport.ts` with `\uFEFF` UTF-8 BOM encoding for Microsoft Excel compatibility and RFC 4180 escaping.
  - 1-click CSV exports wired across all 5 operational ledger views.
- **Live Deployment Verification:**
  - Render backend (`https://livo-footwear-erp-backend.onrender.com/api/v1/health`) healthy with live Neon DB connection.
  - Vercel frontend (`https://livo-footwear-erp.vercel.app`) verified live and operational on commit `06434e7`.

## Phase 4 Automated Security Audit, Dynamic Bundling & Stitch Ergonomics (2026-09-27)
- **Verified Production Commit:** `d0e8254` ("feat(sec,perf): automated security audit suite, dynamic code-splitting, and high-density modal ergonomics").
- **Security Audit & Defensive Hardening (`backend/tests/test_security_audit.py`):**
  - All 27/27 unit, regression, and vulnerability tests pass cleanly (`pytest tests -v --tb=short`).
  - **RBAC Enforcement:** Viewer role strictly denied (`403 Forbidden`) on all mutating endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) across purchases, production, stock movements, and sales.
  - **Unauthenticated Access:** Business routes reject requests without valid JWT (`401 Unauthorized`).
  - **Tenant Isolation & IDOR Defense (Remediated):** Verified and patched mutating endpoints (`/purchase/purchases`, `/production/batches`, `/sales/orders`, `/sales/payments`) to ensure referenced foreign keys (`supplier_id`, `raw_material_id`, `product_id`, `client_id`) are verified to exist strictly within the authenticated caller's company. Cross-tenant references now return HTTP 404.
  - **Boundary Integers & Fuzzing (Remediated):** Enforced Pydantic `Field(..., gt=0)` and `Field(..., ge=0)` on quantities, unit prices, worker counts, and VAT rates (0-100%). Negative quantities and rates strictly return HTTP 422 Unprocessable Entity. Added string length constraints to prevent memory exhaustion DoS.
  - **SQL Injection Defense:** SQLAlchemy parameterized bindings prevent `' OR '1'='1` and nested statement injection payloads.
  - **Session & Transport:** Auth cookies retain `HttpOnly`, `SameSite=lax`. Sliding window rate limiter enforces HTTP 429 when threshold (30 rapid attempts) is exceeded.
  - **Nepal VAT Cancellation:** Authored statutory `POST /api/v1/invoices/{invoice_id}/cancel` endpoint (requires editor; sets `is_void = True` without deleting the row).
- **Frontend Bundle Optimization:**
  - Introduced `next/dynamic` code splitting with high-density `SkeletonLoader.tsx` across all dashboard tabs (`DailyReportView`, `StockReportView`, `ProductionView`, `PurchaseView`, `SalesInvoiceView`, `SettingsView`).
  - Route `/` size reduced from **140 kB to 10.6 kB** (92.4% reduction).
  - First Load JS reduced from **227 kB to 98.1 kB** (56.8% reduction), enabling lightning-fast loads on 3G/4G mobile warehouse terminals.
- **Stitch MCP UI/UX Refinement:**
  - Extracted enterprise ergonomics guidelines from Stitch MCP project `15866847607130442980` (screen `7713fdb90a1e486ca5ea73d164f00cf7`).
  - Converted modals to full-height responsive `.modal-drawer` components with sticky headers, scrollable `.modal-body`, and pinned `.modal-footer` action bars.
  - Enhanced accessibility with `:focus-visible` dual-ring outline (`2px solid #3b82f6`, `2px offset`).
  - Implemented client-side pagination (10 items/page) for large datasets across Production Batches, Purchase Vouchers, and Sales Invoices/Orders.

## Phase 5 Client UAT Preparation & Governance Transition (2026-09-27)
- **Phase 4 Closed:** Phase 4 QA sign-off granted by Architectural Reviewer.
- **Phase 5 Status:** Active (`In Progress`).
- **Cloud Infrastructure Status:**
  - Render Backend: `https://livo-footwear-erp-backend.onrender.com/api/v1/health` returning 200 OK (`database: healthy`).
  - Vercel Frontend: `https://livo-footwear-erp.vercel.app` serving dynamic bundle chunks (First Load JS 98.1 kB) and responsive `.modal-drawer` interfaces.
- **Client Demonstration Guide:** Authored `docs/UAT_WALKTHROUGH.md` covering 4 real-world factory operational scenarios (Raw Material Inward, Production Size Runs, Wholesale Tax Invoicing with Nepal VAT, and Executive Summaries with Excel Portability).
- **Role Boundary Smoke Check:** Verified `viewer_user` has all mutation buttons and shortcuts visually blocked and hidden, while `editor_admin` retains full ledger execution rights.

## Phase 5 Ergonomics, Accessibility & Nepali Localization (2026-09-27)
- **Bilingual Localization Provider (`frontend/src/context/LocaleContext.tsx`):**
  - Zero-dependency client-side translation provider with persistent state in `localStorage` (`livo_locale`), defaulting to English with instant 1-click toggle to नेपाली.
  - Accessible toggle switch (`EN | नेपाली`) integrated into the top navigation bar of `AppShell.tsx` and login card of `page.tsx`.
  - Domain-specific translations for factory operations: दैनिक प्रतिवेदन (Daily Report), स्टक खाता / मौज्दात (Stock Ledger), उत्पादन ब्याच (Production Batches), कच्चा पदार्थ खरिद (Purchase / Raw Materials), बिक्री तथा बिलिङ (Sales & Invoicing), कर बिजक (भ्याट) (Tax Invoice VAT), and tri-state status badges (सम्पन्न / पर्याप्त, न्यून मौज्दात, स्टक समाप्त).
- **Accessibility (a11y) & WCAG 2.1 AA Compliance:**
  - High-contrast `:focus-visible` dual-ring outline (`2px solid #3b82f6`, `2px offset`) across all interactive inputs, selects, and buttons.
  - Modal drawers configured with `role="dialog"`, `aria-modal="true"`, and `aria-labelledby`.
  - Screen reader status feedback configured with `role="status" aria-live="polite"` on all success/error toasts.
  - Descriptive `aria-label` applied to all icon-only buttons (search, modal close, print, void, pagination, mobile menu).
- **Mobile PWA & Touch Compatibility:**
  - Minimum 44x44px touch targets enforced on mobile viewports for all buttons, pagination triggers, and drawer controls.
  - Mobile virtual keyboard protection: pinned `.modal-footer` with `env(safe-area-inset-bottom)`.
  - `manifest.json` updated with standalone display mode, maskable icons, and `#0b1120` theme color for native home-screen installation on Android and iOS.



