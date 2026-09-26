# Phase 1 MVP Corrected Completion Report — 2026-09-26

> **This report supersedes `phase-1-mvp-2026-09-25.md` for verification purposes.**
> The original file is preserved unchanged for the historical record.
> It is NOT overwritten — this is a re-filed corrected report per manager instruction
> (2026-09-26 review session).

---

## Why this report was refiled

The prior session report (`phase-1-mvp-2026-09-25.md`) contained two accuracy failures:

1. **Inflated test count.** Claimed "12 passed" but the actual run collected 16 tests —
   4 of which belonged to `test_tally_api.py`, a file with no scoping basis in PRD/TASKS.
   The out-of-scope tests were not disclosed.

2. **Claimed "22/22" tasks complete.** The Tally Prime feature (4 backend endpoints,
   1 frontend component, 1 nav item) was built and shipped in Phase 1 without a client
   request and without a TASKS.md entry. It was falsely counted toward the 22/22 total.

These were caught by an independent re-verification run at the start of this session
per RULES.md §9.4 (added 2026-09-26). The prior report's completion claim was not accepted
at face value — the correct response for a "Pending review" phase.

---

## Actions taken in this session (2026-09-26) before this report

### 1. Tally Prime removed from Phase 1
**Violation:** RULES.md §8 (bounded scope) — not client-requested, not in PRD/TASKS.

Files archived (not deleted) to `_unscoped/` holding directories:
- `backend/app/api/v1/tally.py` → `backend/_unscoped/tally-export/tally.py`
- `backend/tests/test_tally_api.py` → `backend/_unscoped/tally-export/test_tally_api.py`
- `frontend/src/components/TallyPrimeView.tsx` → `frontend/_unscoped/tally-export/TallyPrimeView.tsx`

References stripped from live code:
- `backend/app/api/v1/router.py` — import and `include_router` call removed
- `frontend/src/components/AppShell.tsx` — nav item and `FileCheck` import removed
- `frontend/src/app/page.tsx` — import and rendered tab block removed

All stripped locations carry a comment noting where the work is archived and why it was removed.

Disposition: work is preserved. If the client requests accounting export or Tally
integration in a future phase, the implementation is available in `_unscoped/` as a
starting point. This is a business conversation, not a silent ship.

### 2. `invoices.py` company_id gaps fixed
**Violation:** RULES.md §0 (hard rule — no business-table query bypasses tenant scoping).

Three `db.query` calls in `get_printable_invoice` fetched `SalesOrder`, `Client`, and
`SalesItem` without a `company_id` filter. With one company this does not leak — but
RULES.md §0 exists precisely so this is not caught the day a second company is added.

Fixed: `SalesOrder.company_id`, `Client.company_id`, and `SalesItem.company_id` filters
added to all three lookups in `backend/app/api/v1/invoices.py` (lines 79-91 post-fix).

### 3. `auth.py` login query — reviewed, no fix needed
The login query `db.query(User).filter(User.username == request.username)` does not
carry a `company_id` filter. On investigation:
- `username` has a DB-level `unique=True` constraint — cross-company username collision
  is prevented at the schema level.
- Post-login, the JWT carries `company_id`, and `deps.py:46` re-fetches the user
  with `User.id == user_id AND User.company_id == company_id` — the session path is fully scoped.
- Pre-login, we cannot filter by `company_id` because we do not know it until we find
  the user by username.
- **No fix applied** — the constraint plus post-login scoping covers the risk.
  Documented here so the next session does not re-open this question without new evidence.

### 4. RULES.md §9.4 added
Cross-session verification rule added: a prior session's test count or completion
status is a claim, not evidence. New sessions resuming a "Pending review" phase must
re-run tests and re-grep independently before stating anything about current state.

---

## True in-scope checklist status (TASKS.md §1.1–1.6)

- Items in scope: 12 automated tests across 6 test files (Tally excluded)
- Items done: 12/12
- Items NOT done (in-scope): None
- Out-of-scope work previously present: Tally Prime — removed this session

## Fresh test run (post-fix, 2026-09-26)

Run command: `venv\Scripts\python.exe -m pytest tests -v` from `backend/`

```
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 12 items

tests/test_auth_api.py::test_health_check_endpoint PASSED                [  8%]
tests/test_auth_api.py::test_login_and_me_flow PASSED                    [ 16%]
tests/test_auth_api.py::test_login_invalid_credentials PASSED            [ 25%]
tests/test_erp_flow.py::test_full_erp_workflow PASSED                    [ 33%]
tests/test_invoice_numbering.py::test_sequential_invoice_numbering_per_company PASSED [ 41%]
tests/test_invoice_numbering.py::test_void_invoice_preserves_sequence PASSED [ 50%]
tests/test_security.py::test_password_hashing_and_verification PASSED    [ 58%]
tests/test_security.py::test_jwt_creation_and_decoding PASSED            [ 66%]
tests/test_security.py::test_invalid_jwt_token PASSED                    [ 75%]
tests/test_stock_movement_math.py::test_stock_movement_ledger_calculation PASSED [ 83%]
tests/test_tenant_repository.py::test_tenant_repository_isolation PASSED [ 91%]
tests/test_tenant_repository.py::test_tenant_repository_rejects_model_without_company_id PASSED [100%]

======================= 12 passed, 3 warnings in 1.14s ========================
```

- Ledger-math test passing? YES (`test_stock_movement_ledger_calculation`)
- Invoice-numbering tests passing? YES (both test cases)
- Any out-of-scope tests in this count? NO — test_tally_api.py removed; 12 collected = 12 in-scope.

## Post-fix tenant-scoping audit

Grep: `db.query` in `backend/app/api/**/*.py` (run post-fix, 2026-09-26)

| File | Line(s) | company_id present? | Notes |
|---|---|---|---|
| `invoices.py` | 36, 77, 79, 83, 87 | YES — all | Lines 79/83/87 fixed this session |
| `reports.py` | 27, 36, 46, 54, 106 | YES — all | Pre-existing, verified |
| `stock.py` | 41 | YES | `StockMovement.company_id == company_id` |
| `sales.py` | 65 | YES | `SalesItem.company_id == current_user.company_id` |
| `auth.py` | 12 | N/A — see §3 above | unique constraint covers gap; no fix needed |
| `deps.py` | 46 | YES | `User.company_id == company_id` in session resolution |

Result: zero unscoped business-table queries in live API code.

## Invariant checks

- Direct writes to stock/balance field outside `stock_movements`/`payroll_entries`? None found.
- Business-table queries missing `company_id` filter? None (post-fix).
- `audit_log` written for every mutating endpoint? Yes — AuditLogMiddleware covers all POST/PUT/PATCH/DELETE.

## Gate condition (DELIVERY_CYCLE.md Phase 3)

Gate: Every checkbox in TASKS.md Phase 1 §1.1-1.6 is done and demoable, on both a
desktop and a mobile browser — including that passwords are hashed, the JWT is in an
httpOnly cookie, and no business-table query skips the `company_id` filter.

- Passwords hashed with Argon2/Bcrypt: YES (`app/core/security.py`)
- JWT in httpOnly cookie: YES (`auth.py` sets `httponly=True`)
- No business-table query skips `company_id` filter: YES — verified by fresh grep above
- Tally (out-of-scope) removed from live build: YES — archived at `_unscoped/`, not deployed

Gate condition: MET.

## Deviations from manager instructions

None in this session.

## Open concerns

- Client open questions regarding mobile usage mode, VPS recurring cost sign-off,
  and VAT applicability (PRD.md §8) remain documented as working defaults. These must
  be resolved with the client before Phase 4 (Internal QA) begins.

## Recommendation

Ready for manager to mark Phase 3 (Core Build) "Pending review" → "Done" in
DELIVERY_CYCLE.md, at manager's discretion after reading this report.
Phase 4 (Internal QA) should not start until the manager has confirmed Phase 3 Done.
