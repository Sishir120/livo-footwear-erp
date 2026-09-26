# PHASE_REPORT_TEMPLATE.md

Copy this into a new dated entry (e.g. `docs/reports/phase-3-2026-10-02.md`)
at the end of every TASKS.md phase. This is evidence, not a status update —
every line should be something you checked, not something you believe.

---

## Phase [N] Completion Report — [date]

**Checklist status**
- Items done: [x/y]
- Items NOT done (list each, and why): ...

**Automated tests**
- Test suite run: [yes/no]
- Pass/fail counts: ...
- Any ledger-math or invoice-numbering test failing? (must be "no" to proceed) ...

**Invariant checks**
- Direct writes to a stock/balance field found outside stock_movements/
  payroll_entries? (must be "none") ...
- Business-table queries missing a `company_id` filter? (must be "none") ...
- Mutating endpoints touched this phase missing an audit_log write?
  (must be "none") ...

**Gate condition (per DELIVERY_CYCLE.md)**
- Stated gate for this phase: ...
- Met? [yes/no] — evidence: ...

**Deviations from manager instructions**
- Any instruction that conflicted with a documented rule, what was built
  instead, and why (§9.2 of RULES.md). Write "none" if there were none —
  don't omit the section.

**Open concerns**
- Anything the agent is uncertain about, flagged rather than silently
  resolved by guessing. Write "none" if there are none.

**Recommendation**
- [ ] Ready for manager to mark this phase "Done" in DELIVERY_CYCLE.md
- [ ] Not ready — blocked on: ...
