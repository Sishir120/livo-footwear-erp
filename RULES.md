# RULES.md — LIVO GROUP OF INDUSTRIES Footwear ERP

Non-negotiable engineering rules for whoever (human or agent) writes code on this project.
If a change conflicts with a rule here, stop and flag it — do not silently deviate.

## 0. Confirmed platform facts (do not re-litigate)
- **Client-server model.** FastAPI backend serves a REST API; Next.js frontend
  is a responsive web app/PWA used from both desktop and mobile browsers.
  No Electron, no native mobile build. See ARCHITECTURE.md for why this
  changed from the original single-machine plan.
- **Offline model:** reads are cached client-side for offline viewing; writes
  require connectivity in Phase 1 (no offline write queue/sync-conflict
  handling yet — documented assumption, see PRD.md §8).
- **Two roles only:** `editor` (full read/write) and `viewer` (read-only).
  Enforced at the API layer, not just hidden in the UI.
- **Audit trail is mandatory**, independent of role count. Every write to a
  business table logs `user_id`, `action`, `table`, `record_id`, `timestamp`.
- **Dates are dual-stored**: every date column has a Gregorian (AD) value; BS
  is derived/stored alongside and toggled in the UI.
- **VAT is unresolved** — invoice template has an optional VAT line
  (rate + amount), OFF by default, one config flag to enable.
- **The API is now internet-reachable** (unlike the original local-only
  plan) — basic auth + rate limiting matter here in a way they didn't before.
- **Database is Postgres, not SQLite** (revised 2026-09-25 — ARCHITECTURE.md §9),
  to keep future scaling paths open without a migration project later.
- **Every business table has a `company_id`.** There is one company today.
  No query against a business table bypasses the shared tenant-scoped
  query/repository helper — this is a hard rule, not a style preference,
  because a forgotten filter here is a cross-tenant data leak the moment a
  second company ever exists.

## 1. Ledger principle (highest priority — this is where money/stock bugs hide)
Stock and payroll are **derived from movement logs**, never directly edited.
- `stock_movements(product_id, quantity, direction, ref_type, ref_id, date)` —
  current stock = `SUM(direction * quantity)`. No `products.stock_qty` field
  that gets manually incremented anywhere.
- `payroll_entries(worker_id, type[earned|advance|paid], amount, date)` —
  advance balance = `SUM(advance) - SUM(paid)`.
- Any code that writes a stock or balance number directly (instead of
  inserting a movement row) is a bug, full stop. Automated tests must cover
  this (see §6).

## 2. Error handling & observability
- **Structured logging only** — JSON lines to a rotating local log file. No `print()`.
- **One global exception handler** in FastAPI. No scattered `try/except: pass`.
- Separate **validation errors** (bad user input → friendly inline message)
  from **real exceptions** (log full trace, show "something went wrong —
  click to report").
- Frontend: one **error boundary per major screen** (Purchase / Production /
  Stock / Sales / HR). A crash in one screen must not take down the app shell.
- **Settings → "Send Diagnostics"** button: zips recent logs + app version +
  DB self-check result, no technical steps required from the client.
- App shell shows **visible version number + DB self-check status** on boot.

## 3. Schema & migrations
- Alembic (or equivalent) from commit #1. Every schema change is a versioned,
  reversible migration — no manual `ALTER TABLE` outside migrations.
- Invoice numbers are **sequential and immutable** once issued — no gaps
  closed by renumbering, no reuse after voiding (void = new negative/credit
  record).

## 4. Auth & audit
- `users(id, company_id, name, role[editor|viewer], password_hash, active)` —
  `company_id` is mandatory even with one company today (ARCHITECTURE.md §5);
  `password_hash` via bcrypt/argon2, never plaintext, never logged.
- JWT session tokens stored in an httpOnly, Secure, SameSite cookie — not
  `localStorage` (XSS-exposed). Every request re-validated server-side.
  Middleware rejects any write request from a `viewer` at the API layer.
- `audit_log` table is append-only, carries `company_id`. No update/delete
  endpoints against it, ever.
- Basic per-IP/per-user rate limiting on public endpoints — sized to a 3-user
  internal tool, not a SaaS threat model. Don't over-build this.
- CORS restricted to the app's own frontend origin, never `*`.
- Secrets (DB credentials, JWT signing key, object-storage keys) come from
  environment variables at deploy time — never committed to the repo.

## 5. Backup
- Nightly (or on-close) job runs `pg_dump` against the Postgres database
  (not a file copy — this is Postgres, not SQLite) and uploads the dump to
  the configured cloud destination. Backup failures must be logged and
  surfaced in Settings, not silent.
- Restore path must be documented and tested before handover — a backup
  nobody can restore is not a backup.

## 6. Testing (minimum bar, given the timeline)
- Unit tests on stock-movement math and payroll-balance math are **not
  optional**, even under time pressure — this is the single highest-value
  place to catch silent corruption before it reaches a client who can't
  debug it themselves.
- Everything else (UI, reports) can be manually verified given the 10–15 day
  window.

## 7. Data migration
- Historical import (3 months, "both" existing formats) is a one-time script,
  not a recurring feature. Keep it in `scripts/`, document the expected input
  format, and run it against a copy of the DB first, never production data
  directly.

## 8. Agent workflow (how the AI coding agent should operate on this repo)
- **Bounded scope:** don't inspect or edit files outside the directory tree
  the current task names.
- **Incremental execution, one concern per turn:** write/verify the test →
  implement minimal passing code → refactor for types/readability → add
  edge-case handling. Don't do implementation + tests in the same turn.
- **Forced diagnosis before fixing a bug:** when a runtime error or failing
  test shows up, output first — before touching any file — (1) the affected
  files, (2) each file's role, (3) root cause, (4) three ranked candidate
  fixes. Then implement the top one.
- **Git hygiene:** commit a clean working state before a complex multi-file
  prompt. If a generated change fails or bloats the diff, hard-reset to the
  last good commit rather than hand-debugging AI output.
- **Running context:** MEMORY.md is the standing decisions/assumptions log.
  Read it at the start of a new session; append to it (don't rewrite history)
  whenever a decision, assumption, or open question changes.

## 9. Professional autonomy & phase-end validation

### 9.1 Role split
- **Manager (Sishir):** sets priorities, scope, business constraints, resolves
  open questions with the client, makes trade-off calls between speed and
  scope.
- **Agent (Antigravity):** owns *how* the work gets done within the
  boundaries already documented in PRD.md / ARCHITECTURE.md / RULES.md /
  MEMORY.md. The agent is not a typist for instructions — it is expected to
  apply the judgment of a professional developer who has read this repo's
  own rules.

### 9.2 When a manager instruction conflicts with a documented rule
This is the specific, narrow trigger for pushback — not general disagreement,
not style preferences, not "I'd have done it differently."
Trigger: the instruction would violate a hard invariant already written down
— the ledger principle (§1), tenant scoping (§0), the audit trail (§4), or
invoice immutability (§3).
When triggered, the agent must, **before writing any code**:
1. Name the specific rule/section being conflicted with.
2. Explain the conflict in one or two sentences — not a lecture.
3. Propose a compliant alternative that achieves the same underlying goal.
4. **Stop and wait for confirmation** if the conflict touches a hard
   invariant. For anything else (a naming choice, a UI detail, a minor
   scope tweak), proceed with the compliant alternative and note the
   substitution in the next Phase Completion Report — don't block on it.
This is not insubordination — silently complying with an instruction that
corrupts the stock ledger or leaks cross-tenant data is a worse outcome than
a five-second pushback.

### 9.3 Phase-end self-validation protocol (automatic — not on request)
Triggered whenever the agent believes every checkbox in a TASKS.md phase
section is complete. Do not wait to be asked to "test it" — this runs by
default at the end of every phase.
1. Walk every checkbox in that phase's TASKS.md section — done / not done,
   no partial credit for "mostly working."
2. Run the automated test suite. Ledger-math and invoice-numbering tests
   (§6) must actually pass, not be skipped or commented out.
3. Run the deterministic invariant checks: no direct write to a stock/balance
   field outside `stock_movements`/`payroll_entries`, no business-table query
   missing a `company_id` filter, `audit_log` written for every mutating
   endpoint touched this phase.
4. Cross-check the phase's Gate condition in DELIVERY_CYCLE.md — confirm it
   is literally true with evidence, not "should be fine."
5. Fill out PHASE_REPORT_TEMPLATE.md completely and present it to the
   manager. This report — not a verbal "done!" — is the deliverable at
   phase end.
6. Mark the phase **"Pending review"** in DELIVERY_CYCLE.md, not "Done."
   Only the manager moves a phase to "Done," after reading the report. A
   phase the agent thinks is finished and a phase the manager has confirmed
   are different states — don't collapse them.

### 9.4 Cross-session verification (added 2026-09-26 — incident-driven)
A prior session's self-reported test count, completion status, or phase
report is **not evidence** — it is a claim. When a new session picks up a
phase that is "Pending review":
1. **Re-run the test suite independently.** Do not quote a prior session's
   "N passed" output. Run it now, paste the output.
2. **Re-run the tenant-scoping grep** (`db.query` without `company_id`
   filter) across all business routers touched in that phase.
3. **Check every file added this phase against the PRD/TASKS scope.** If a
   file has no scoping basis, flag it before doing anything else — it is a
   bounded-scope violation (§8) until proven otherwise.
4. Only after completing 1–3 independently may the agent state what is or
   isn't working. Verbal trust in a previous session's self-assessment is
   exactly the failure mode that inflated the Phase 1 report — don't repeat it.

## 10. Conventions
- Backend: FastAPI, one router per module (`purchase.py`, `production.py`,
  `stock.py`, `sales.py`, `hr.py`, `gallery.py`, `analytics.py`), Pydantic
  models for all I/O.
- Frontend: Next.js, responsive/mobile-first, data-entry screens before
  dashboards.
- Commits: one logical change per commit, message states *what* and *why*.
- No feature ships without: (a) a migration if schema changed, (b) a log
  statement on failure paths, (c) an error boundary if it's a new top-level
  screen.
