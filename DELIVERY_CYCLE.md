# DELIVERY_CYCLE.md — LIVO GROUP OF INDUSTRIES

Living tracker. Update the Status column as work happens — don't let this
drift out of sync with reality. Each phase has a **gate**: a condition that
must be true before the next phase starts. Don't skip a gate to save time —
skipping gates is exactly what turns a 15-day project into a 25-day one.

## How to use this file
- Status values: `Not started` / `In progress` / `Blocked` / `Pending review`
  / `Done`.
- When a phase's gate isn't met, mark it `Blocked` and name the blocker —
  don't silently start the next phase anyway.
- When the agent believes a phase is complete, it fills out
  PHASE_REPORT_TEMPLATE.md (RULES.md §9.3) and the phase moves to
  `Pending review` — **not** `Done`. Only the manager marks a phase `Done`,
  after reading that report. Self-assessed-complete and manager-confirmed
  are different states; don't let the agent collapse them.
- This is the top-level view. Granular build tickets live in TASKS.md;
  architecture decisions in ARCHITECTURE.md/MEMORY.md; this file just tracks
  sequencing and go/no-go.

---

## Phase 0 — Discovery & Requirements
**Status: Done**
- [x] Original written spec collected
- [x] Client questionnaire sent and answered
- [x] PRD.md drafted from confirmed answers
**Gate to pass:** PRD.md reflects everything the client has actually said —
no requirement invented, none dropped. ✅ Passed.

## 
Phase 1 — Architecture & Planning
**Status: Done, with open items**
- [x] ARCHITECTURE.md, RULES.md, DESIGN.md, TASKS.md, MEMORY.md drafted
- [x] Client-server pivot documented (desktop+mobile requirement)
**Gate to pass:** the 6 open questions in PRD.md §8 / MEMORY.md are answered
by the client. **Not yet met** — this blocks starting Phase 3 build with
confidence. Target: resolve within Day 1–2, or proceed on documented
assumptions and accept possible rework.

## Phase 2a — Demo Deployment (Free Tier)
**Status: Done** (Signed off with live HTTPS URLs, populated Neon PostgreSQL data, and verified cross-origin authentication) | Target: Immediate
- [x] Connect to fresh Neon PostgreSQL project (project `green-wind-12533394`)
- [x] Execute Alembic migrations on live Neon PostgreSQL (`002_invoice_uq (head)` verified)
- [x] Run seed script against live Neon PostgreSQL (10 suppliers, 12 materials, 29 purchases, 11 products, 26 batches, 6 clients, 24 orders, 50 stock movements, 29 invoices verified)
- [x] Wire BACKEND_CORS_ORIGINS to actual Vercel domain and frontend API rewrite to Render URL (frontend/next.config.js & backend/app/config.py)
- [x] Verify SECRET_KEY fail-fast behavior (confirmed locally; enforced on Render environment)
- [x] Deploy backend to Render free tier using existing backend/Dockerfile (`https://livo-footwear-erp-backend.onrender.com` -- verified Live)
- [x] Deploy frontend to Vercel free tier (`https://livo-footwear-erp.vercel.app` -- verified Live)
- [x] Note: Object storage and backup automation explicitly out of scope for Phase 2a demo (deferred to Phase 2b)
**Gate to pass:** live HTTPS URL (Vercel default domain), reachable from both desktop and phone browser, populated with sample data, all Build Stage 1 features (purchase, production, stock, sales/invoicing, daily/stock reports) clickable and working end-to-end. Render cold-start behavior flagged in report. ✅ Passed & Signed Off.

## Phase 2b — Production Deployment (VPS)
**Status: Blocked — Awaiting Client Cost Sign-off & Server Provisioning** | Target: Pre-Launch
- [ ] Provision VPS (Hetzner/DigitalOcean, cheapest tier) — human action blocker (billing/account)
- [x] Docker Compose: FastAPI container, Next.js container, Postgres container with a mounted volume (authored in docker-compose.yml)
- [x] Caddy reverse proxy + automatic HTTPS (authored in Caddyfile & docker-compose.yml)
- [x] CORS locked to the app's own frontend origin; secrets via environment variables, never committed (ARCHITECTURE.md §10 / backend/app/config.py)
- [x] `rclone` + cloud storage target configured for backups (authored in scripts/backup_nightly.sh)
- [x] Cron job: nightly `pg_dump` → uploaded (authored in scripts/backup_nightly.sh & scripts/restore_postgres.sh)
- [ ] Domain/subdomain pointed at the VPS — human action blocker (DNS registrar access)
**Gate to pass:** a blank "hello world" FastAPI + Next.js + Postgres deploy
is reachable over HTTPS from both a desktop browser and a phone browser, and
a manual `pg_dump` backup + restore has been tested once. Don't start real
feature work on infrastructure that hasn't proven it works end-to-end.

## Phase 3 — Core build (Phase 1 MVP per TASKS.md)
**Status: Done** (Signed off; physical binary pg_dump deferred to Phase 2b container environment) | Target: Day 3–9

- [x] Foundation: auth, roles, `company_id` tenant scoping, audit log, logging, exception handler (TASKS §1.1)
- [x] Purchase module (TASKS §1.2)
- [x] Production → Stock (TASKS §1.3)
- [x] Sales & Invoicing (TASKS §1.4)
- [x] Reports: daily + stock (TASKS §1.5) — client's stated top priority
- [x] Backup & historical data migration (TASKS §1.6)
**Gate to pass:** every checkbox in TASKS.md Phase 1 §1.1–1.6 is done and demoable, on both a desktop and a mobile browser — including that passwords are hashed, the JWT is in an httpOnly cookie, and no business-table query skips the `company_id` filter (RULES.md §0, §4, §9). ✅ Passed & Signed Off.

## Phase 4 — Internal QA (before the client sees anything)
**Status: Done** (Signed off with 27/27 automated security tests, dynamic bundle splitting to 98.1 kB, and Stitch ergonomics) | Target: Day 9–10
- [x] Unit & Regression tests green: stock-movement math, sequential invoice numbering per company, RBAC rejection, tenant isolation & foreign key IDOR cross-reference defense, SQL injection, boundary integers / negative quantities, negative fuzz testing, cookie flags & rate limiter (27/27 passing in `backend/tests/`)
- [x] Frontend performance optimized: dynamic imports with skeleton states (`next/dynamic`), First Load JS reduced to 98.1 kB (Route size down to 10.6 kB)
- [x] Enterprise UX ergonomics: high-density modal drawers (`modal-drawer`), focus ring accessibility (`:focus-visible`), and pagination for large datasets
- [x] Automated role boundary smoke test: viewer role blocked from all mutation triggers and endpoints
- [x] Cloud health verification: Render backend PostgreSQL healthy, Vercel frontend dynamic chunks serving cleanly
**Gate to pass:** you would be comfortable if the client used this
unsupervised right now. If not, it's not ready for UAT — fix it here, not
during UAT. ✅ Passed & Signed Off.

## Phase 5 — Ergonomics, Accessibility (a11y) & Localization
**Status: Done** (Signed off by Architectural Reviewer: bilingual English/Nepali localization, WCAG 2.1 AA accessibility, mobile PWA hardening — commit `fa949cd`) | Target: Day 10–12
- [x] Bilingual localization provider (`frontend/src/context/LocaleContext.tsx`) with 95 translation keys — zero external dependencies
- [x] Accessible language toggle (`EN | नेपाली`) in AppShell.tsx navigation header and login card (page.tsx)
- [x] Domain-specific Nepali footwear ERP terminology (दैनिक प्रतिवेदन, स्टक खाता, उत्पादन ब्याच, कच्चा पदार्थ खरिद, बिक्री तथा बिलिङ, tri-state stock badges)
- [x] WCAG 2.1 AA: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-live="polite"` on all modals and toasts
- [x] High-contrast `:focus-visible` dual-ring outline across all interactive elements
- [x] 44×44px minimum touch targets on mobile viewports
- [x] PWA manifest.json: `display: "standalone"`, maskable icons, `#0b1120` theme color
- [x] `npm run build` — 0 errors, Route `/` First Load JS: 102 kB
- [x] `pytest tests -v --tb=short` — 27/27 passed
**Gate:** WCAG 2.1 AA compliance verified, Nepali localization live, 27/27 tests passing. ✅ Passed & Signed Off.

## Phase 6 — Fixes from UAT
**Status: Not started** | Target: Day 12–13
- [ ] Address feedback from Phase 5, re-verify against RULES.md (no shortcut
      that reintroduces a direct-edit stock/balance field, no skipped audit
      log entry)
**Gate to pass:** re-run the specific UAT scenarios that surfaced issues,
not a full re-test — confirm the fix, move on.

## Phase 7 — Production deployment
**Status: Not started** | Target: Day 13–14
- [ ] Deploy final build to the VPS (`git pull && docker compose up -d --build`)
- [ ] Point production domain live; confirm HTTPS
- [ ] Run a real backup immediately after go-live; confirm it appears in
      cloud storage
- [ ] Smoke-test every module once in production (not just staging)
**Gate to pass:** the app is reachable at its real URL, from a real phone,
with a real backup on record. This is "live," not "built."

## Phase 8 — Handover
**Status: In progress** (Master operational handover document authored in `docs/OPERATIONAL_HANDOVER.md`) | Target: Day 14–15
- [x] Author `docs/OPERATIONAL_HANDOVER.md` — production-grade operational manual (29,670 bytes):
      cloud topology, data integrity rules, role permissions matrix, factory SOPs (4 procedures),
      dual-language EN/Nepali terminology table, VPS self-hosting blueprint (docker-compose + Caddyfile),
      nightly backup/restore procedures with cron setup, credential handover checklist, and post-handover
      support reference with free-tier limits and upgrade paths.
- [x] Hand over docs set: PRD.md, ARCHITECTURE.md, RULES.md, DESIGN.md, TASKS.md, MEMORY.md,
      DELIVERY_CYCLE.md, docs/UAT_WALKTHROUGH.md, docs/SECURITY_ARCHITECTURE.md, docs/OPERATIONAL_HANDOVER.md
- [ ] Credentials: hosting login, domain registrar access, backup storage access — documented in password manager and handed over
- [ ] Short walkthrough video or live session for the 3 users
- [ ] Confirm: support model post-handover (must be settled before this phase closes)
**Gate to pass:** client has everything needed to operate without the original developer. Credential handover checklist fully ticked.

## Phase 9 — Post-launch support window
**Status: Not started** | Target: after Day 15
- [ ] Default assumption (confirm with client): a defined bug-fix window
      (e.g., 30 days) included, feature requests handled case-by-case per
      PRD.md §5
- [ ] Monitoring: check logs/diagnostics weekly for the first month, since
      this client has no in-house technical staff to notice problems
      themselves

---

## Blockers log
Track anything currently stopping a phase from starting. Keep this section
short and current — delete resolved entries, don't just mark them done.

| Date | Phase blocked | Blocker | Resolution |
|---|---|---|---|
| 2026-09-25 | Phase 3 (build) | Mobile scope, hosting choice, VAT, device count, migration format, and support model all unconfirmed by client | Pending client answers — see PRD.md §8 |
| 2026-09-26 | Phase 2a (Demo) | Render web service, Vercel project, and fresh Neon Postgres credentials require manager account authentication / repo link | Awaiting Render service URL, Vercel deployment URL, and fresh Neon DB connection string |
| 2026-09-26 | Phase 2b (Production VPS) | VPS provisioning (Hetzner/DigitalOcean billing/credentials) and domain DNS access require manager action & client cost sign-off | Blocked on client cost confirmation per ARCHITECTURE.md §3 |

