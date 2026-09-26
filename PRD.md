# PRD.md — LIVO GROUP OF INDUSTRIES Management Software

## 1. Overview
Custom management software for a footwear factory (manufactures in-house AND
buys/resells finished pairs, multi-location) covering purchase, production,
stock, sales/invoicing, HR, gallery, and reporting. Interface language: English.

## 2. Users & access
- 3 named users at launch: 1 **editor** (data entry + changes), 2 **viewers**
  (read-only). No per-module permission granularity requested.
- Every write is attributed to a user and logged (audit trail — explicitly
  required by client regardless of headcount).
- **Platforms:** desktop AND mobile (client requirement, confirmed after
  initial spec — see §8 Assumptions, this is the single biggest scope change
  since kickoff and is not yet fully specced with the client).

## 3. Functional requirements

### 3.1 Purchase (raw materials)
- Record supplier name, quantity, date, amount per purchase; 100+ material
  types, ~100 regular suppliers, credit and pay-at-purchase both used.
- Filter by custom date range.

### 3.2 Production
- Raw materials consumed → finished footwear produced; track quantity
  produced by date, daily worker count.
- Production increases finished-goods stock (via stock_movements, not a
  manual edit — see ARCHITECTURE.md).

### 3.3 Stock
- Tracked by size + colour as distinct items, counted in pairs, identified
  by number+colour product codes.
- Auto-updates from production (in) and sales (out); never manually edited.
- Filterable by item name/code; "pending stock" view.

### 3.4 Sales & invoicing
- ~100 active retailer/wholesale clients; client record: name, address, location.
- Sale record: date, item, qty, rate, amount; received vs. receivable amount
  tracked with payment date/method.
- Order "delivered" toggle; filter by date/item/client.
- Returns/exchanges recorded.
- Credit sales sometimes offered.
- **Printable invoice/challan — explicitly essential.** Must show: company
  name, items, qty, PAN number, rate, date, amount, received amt, receivable
  amt. VAT applicability unconfirmed — invoice must support an optional VAT
  line, off by default.
- Payment methods accepted: cash, bank transfer, online payment, mobile
  money, cheque.
- Invoice numbers sequential and immutable.

### 3.5 HR & payroll (Phase 2 — see TASKS.md)
- Workers paid both fixed-salary and wage-based; overtime calculated per hour.
- Worker profile: name, joining date, ID, basic salary, monthly hours,
  overtime, salary-paid history, advance record (auto-shown).
- Active/inactive toggle.
- Needs both clock-in/out tracking and monthly totals.

### 3.6 Product gallery (Phase 2)
- Upload product images tagged with code + name; viewable/downloadable.

### 3.7 Reports & analytics
- **Client's stated top priority: daily report + stock report** — build first.
- Daily report: production, sales, stock movement summary for a given day.
- Stock report: current stock by item/code, pending stock.
- Phase 2: product report and sales report "day by day," analytics graphs/charts
  (daily worker/production, monthly/3-month/1-year ratios, most-selling
  products, top/repeated customers).
- Report layout: client has no preference ("a fresh layout is fine").

## 4. Non-functional requirements
- **Dates:** every record stores Gregorian date; Bikram Sambat displayed via
  a UI toggle (dual-stored, not BS-only).
- **Offline behavior:** app must remain usable without internet for a device
  already holding data; only cloud backup strictly requires connectivity
  (see ARCHITECTURE.md §Offline model for how this changes under the
  desktop+mobile requirement).
- **Backup:** automatic, to cloud storage; restore path must be tested before
  handover.
- **Historical data:** client has ~3 months of existing records (mixed
  formats) to migrate.
- **Audit trail:** append-only log of who changed what, when.

## 5. Business/commercial constraints
- Target: first working version within 10–15 days of kickoff.
- No fixed budget stated; client prefers a one-time payment over an ongoing
  support contract.
- Staff training: not needed. Handover deliverable and post-launch support
  model: not yet decided by client — needs an answer before Phase 1 closes.
- Requirement changes during development: client is open to change,
  decided case by case.

## 6. Out of scope for Phase 1 (see TASKS.md for full split)
HR/payroll, product gallery, ranked/ratio analytics beyond daily & stock
reports, BS/AD UI polish beyond basic dual-storage.

## 7. Success criteria (in client's own terms)
1. Daily report
2. Stock report
3. Product report day by day
4. Sales report day by day
5. Analytics graphs/charts
Client named #1 and #2 as most important if forced to prioritize.

## 8. Open questions / assumptions requiring client confirmation
These are unresolved as of this document and materially affect architecture —
flag before committing to the 10–15 day estimate:
- [ ] **Mobile scope:** does a phone need the same live data as desktop
  simultaneously, or is it for occasional viewing/reports only?
- [ ] **Hosting:** recommended default is a small VPS (~$5–7/month) rather
  than the client's own PC — see ARCHITECTURE.md §3 for why. This is a
  recurring cost against a stated "one-time payment" preference; needs the
  client's explicit sign-off, not silent assumption.
- [ ] **Device count:** is the phone in addition to the previously-confirmed
  "1 computer," or does it replace that answer?
- [ ] VAT applicability and rate.
- [ ] Exact format of existing records to migrate.
- [ ] Handover deliverable and post-launch support model.

ARCHITECTURE.md proceeds with a working default for the mobile question
(near-real-time via a hosted API, no offline writes) so the build isn't
blocked — treat it as a documented assumption, not a client-confirmed
decision.
