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




