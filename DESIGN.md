# DESIGN.md — LIVO GROUP OF INDUSTRIES

Minimal design conventions — this is an internal operations tool for 3 users,
not a branded product. Optimize for fast, unambiguous data entry over polish.

## 1. Layout
- Mobile-first responsive breakpoints: single-column stacked forms under
  ~640px, table/grid layouts above that.
- Data-entry screens (Purchase, Production, Sales) prioritize speed: large
  tap targets, numeric keypads for quantity/amount fields on mobile, minimal
  required taps per entry.
- Reports/dashboards (Daily report, Stock report) are read-first: default to
  today's data, one clear date-range control, no nested filter menus.

## 2. Roles in the UI
- `viewer` accounts hide (not just disable) write controls — but this is a
  UX convenience only, never the actual access control (that's enforced
  server-side per RULES.md §4).
- Every record shows who entered/last changed it and when, visible without
  extra clicks — the audit trail should feel present, not buried in a
  separate log screen.

## 3. Dates
- BS/AD toggle is a persistent, visible control (not buried in settings) —
  client-facing invoices and reports get read by people who think in BS.

## 4. Invoices
- Print stylesheet separate from screen stylesheet — invoice must render
  correctly on a physical printer, not just look fine in a browser tab.
- Fields in a fixed, predictable order: company name → items → qty/PAN
  number/rate/date/amount/received/receivable, matching what the client
  specified verbatim (don't redesign the layout they already described).

## 5. Offline/connectivity state
- Since writes require connectivity in Phase 1, the UI must clearly show
  "offline — viewing cached data" rather than silently failing a submit or
  showing stale data as if it were live.

## 6. Visual style
- No branding requirements from the client beyond the company name; use a
  plain, high-contrast, legible style (this is a shop-floor/office tool,
  often viewed on small phone screens in variable lighting).
