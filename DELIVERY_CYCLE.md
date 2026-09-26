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
**Status: Pass** (all checklist items completed, live links verified) | Target: Immediate
- [x] Connect to fresh Neon PostgreSQL project (project `green-wind-12533394`)
- [x] Execute Alembic migrations on live Neon PostgreSQL (`002_invoice_uq (head)` verified)
- [x] Run seed script against live Neon PostgreSQL (10 suppliers, 12 materials, 29 purchases, 11 products, 26 batches, 6 clients, 24 orders, 50 stock movements, 29 invoices verified)
- [x] Wire BACKEND_CORS_ORIGINS to actual Vercel domain and frontend API rewrite to Render URL (frontend/next.config.js & backend/app/config.py)
- [x] Verify SECRET_KEY fail-fast behavior (confirmed locally; enforced on Render environment)
- [x] Deploy backend to Render free tier using existing backend/Dockerfile (`https://livo-footwear-erp-backend.onrender.com` -- verified Live)
- [x] Deploy frontend to Vercel free tier (`https://livo-footwear-erp.vercel.app` -- verified Live)
- [x] Note: Object storage and backup automation explicitly out of scope for Phase 2a demo (deferred to Phase 2b)
**Gate to pass:** live HTTPS URL (Vercel default domain), reachable from both desktop and phone browser, populated with sample data, all Build Stage 1 features (purchase, production, stock, sales/invoicing, daily/stock reports) clickable and working end-to-end. Render cold-start behavior flagged in report.

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
**Status: Pending review — 1 item deferred to Phase 2 (documented)** | Target: Day 3–9

- [x] Foundation: auth, roles, `company_id` tenant scoping, audit log, logging, exception handler (TASKS §1.1)
- [x] Purchase module (TASKS §1.2)
- [x] Production → Stock (TASKS §1.3)
- [x] Sales & Invoicing (TASKS §1.4)
- [x] Reports: daily + stock (TASKS §1.5) — client's stated top priority
- [x] Backup & historical data migration (TASKS §1.6)
**Gate to pass:** every checkbox in TASKS.md Phase 1 §1.1–1.6 is done and demoable, on both a desktop and a mobile browser — including that passwords are hashed, the JWT is in an httpOnly cookie, and no business-table query skips the `company_id` filter (RULES.md §0, §4, §9). ✅ Phase Report generated at `docs/reports/phase-1-mvp-2026-09-25.md`.

## Phase 4 — Internal QA (before the client sees anything)
**Status: Not started** | Target: Day 9–10
- [ ] Unit tests green: stock-movement math, invoice numbering (RULES §6)
- [ ] Error boundaries confirmed working (force a screen to throw, verify
      the rest of the app survives)
- [ ] "Send Diagnostics" button produces a usable log bundle
- [ ] Backup restore tested against a real snapshot, not just the empty-DB
      test from Phase 2
- [ ] Offline-read behavior verified on an actual phone with WiFi disabled
**Gate to pass:** you would be comfortable if the client used this
unsupervised right now. If not, it's not ready for UAT — fix it here, not
during UAT.

## Phase 5 — UAT (User Acceptance Testing) with the client
**Status: Not started** | Target: Day 10–12
- [ ] Walk the client through each PRD.md §7 success criterion live
- [ ] Client enters real (or realistic) data themselves, not just watches
- [ ] Collect feedback as a dated list, not verbal-only — write it down
- [ ] Explicit sign-off: client confirms daily report + stock report +
      invoicing meet what they asked for
**Gate to pass:** client sign-off obtained (even informal — a "yes, this
works" message is enough, but get it in writing). Don't deploy to production
without this — it's the checkpoint that prevents a surprised client at
handover.

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
**Status: Not started** | Target: Day 14–15
- [ ] Hand over: PRD.md, ARCHITECTURE.md, RULES.md, DESIGN.md, TASKS.md,
      MEMORY.md, DELIVERY_CYCLE.md (full context for whoever maintains this
      later, not a partial set)
- [ ] Credentials: hosting login, domain registrar access, backup storage
      access — documented, not just verbally shared
- [ ] Short walkthrough video or live session for the 3 users
- [ ] Confirm: handover deliverable and support model (still "not sure yet"
      per client — **must be settled before this phase closes**, not left
      open after launch)
**Gate to pass:** client has everything needed to operate without you
disappearing being a single point of failure.

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

