# LIVO FOOTWEAR ERP — TEST PLAN: NEPAL-FIRST, TRACEABILITY & INVENTORY INTEGRITY

**Project:** LIVO Footwear ERP  
**Document:** Master Test & Acceptance Plan  
**Status:** Approved for Implementation (Phase 9)  
**Author:** Coordinated QA Automation & Application Security Team  

---

## 1. Verified Baseline Test State

Prior to designing or applying new features, the existing test suites were executed in full:
- **Backend Tests:** **369 passed**, 0 failed, 0 skipped in 129.43s (Python 3.14.7, pytest 9.1.1).
- **Frontend Type Safety:** `npx tsc --noEmit` passed with **0 errors** (TypeScript 5.4.3).
- **Security & Multi-Tenant Tests:** Checked tenant boundary isolation, JWT tampering, integer-paisa rounding, and advisory locks.

Every new test created under this directive must add to this green baseline. Zero existing tests may be removed or skipped.

---

## 2. Test Architecture for New Behaviors

### 2.1 Nepal-First Date System Tests (`test_nepali_date_foundation.py`)
- **T-DATE-01 (Round-Trip Invariance):** Every Gregorian date from `1979-01-01` to `2043-12-31` must convert to Bikram Sambat (`2035 BS` to `2100 BS`) and back to the identical Gregorian date with zero day drift.
- **T-DATE-02 (Known Reference Anchors):**
  - Nepal Constitution Day: `2015-09-20 AD` = `2072-06-03 BS` (Ashwin 3, 2072)
  - Nepali New Year 2083: `2026-04-14 AD` = `2083-01-01 BS` (Baisakh 1, 2083)
  - Current Staging Reference: `2026-10-14 AD` = `2083-06-28 BS` (Ashwin 28, 2083)
- **T-DATE-03 (Month & Leap Year Boundaries):** Verify 29, 30, 31, and 32 day months in Bikram Sambat calendar. Ensure invalid dates like `2083-02-33` return HTTP 422.
- **T-DATE-04 (Timezone Boundary Safety):** Ensure date-only business vouchers (`YYYY-MM-DD`) are never shifted by UTC/NPT (+05:45) timezone offsets during API serialization.

### 2.2 Bilingual Guidance & Localization Tests (`test_bilingual_help_system.py`)
- **T-I18N-01 (Help Article Catalog Completeness):** Verify that all 32 inventoried modules in `HELP_COVERAGE_MATRIX.md` have corresponding English and Nepali markdown content in the catalog.
- **T-I18N-02 (String Coverage):** Verify that all UI navigation items, action buttons, status labels, and error messages have non-empty Nepali translations in `LocaleContext.tsx`.
- **T-I18N-03 (State Preservation on Language Switch):** Frontend test verifying that switching from English to Nepali preserves unsaved form inputs and active tab selection.
- **T-I18N-04 (No Fictional UI Elements):** Automated test asserting that all buttons, fields, and paths referenced in help articles exist in the actual DOM/routes.

### 2.3 Location Hierarchy & Transfer State Machine Tests (`test_location_and_transfers.py`)
- **T-LOC-01 (Hierarchy Creation & Circular Prevention):** Verify creation of Facility → Store → Zone → Rack → Bin. Ensure setting a child as its own ancestor is rejected with HTTP 422.
- **T-LOC-02 (Transfer Lifecycle Happy Path):**
  1. Storekeeper creates transfer from Factory Store to Kathmandu Branch for 100 pairs of Article 801 (Size 41, Black, Batch B01).
  2. Factory available stock decreases by 100 pairs; `IN_TRANSIT` stock increases by 100 pairs.
  3. Transfer status transitions to `DISPATCHED` → `IN_TRANSIT`.
  4. Kathmandu Branch manager counts and receives 100 pairs.
  5. `IN_TRANSIT` decreases by 100 pairs; Kathmandu Branch stock increases by 100 pairs.
  6. Transfer status transitions to `RECEIVED` → `CLOSED`.
- **T-LOC-03 (Transfer Shortage & Discrepancy):**
  - Factory dispatches 100 pairs. Branch receives 95 pairs, noting 5 pairs lost/missing in transit.
  - Branch available stock increases by 95; in-transit stock decreases by 100.
  - 5 pairs are recorded in `stock_transfer_items.discrepancy_quantity` with reason `MISSING_SHORTAGE`.
  - Transfer status transitions to `PARTIALLY_RECEIVED`.
- **T-LOC-04 (Damaged Goods Quarantine):**
  - Branch receives 90 intact pairs and 10 water-damaged pairs.
  - Intact pairs move to Branch Available Stock; damaged pairs move to Branch Quarantine Store.
- **T-LOC-05 (Pre-Dispatch Cancellation):**
  - Cancelling a transfer before dispatch releases reserved quantities with zero stock ledger impact.
- **T-LOC-06 (Post-Dispatch Immutability):**
  - Cancelling or modifying a transfer after dispatch is forbidden; goods must be received or formally returned via reverse transfer.

### 2.4 Concurrency, Idempotency & Security Tests (`test_traceability_concurrency.py`)
- **T-CONC-01 (Double Dispatch Prevention):** Concurrent dispatch requests on the same transfer cannot double-deduct source stock (PostgreSQL advisory lock `acquire_stock_mutation_lock`).
- **T-CONC-02 (Double Receipt Prevention):** Concurrent destination receipt requests cannot double-increment branch stock.
- **T-CONC-03 (Cross-Tenant Transfer Attack):** Attempting to transfer stock from Company A to a location belonging to Company B returns HTTP 404/403.
- **T-CONC-04 (Insufficient Stock Guard):** Attempting to dispatch more pairs than physically available at the source location is rejected with HTTP 422 `INSUFFICIENT_STOCK`.

---

## 3. Mandatory 15-Step Realistic Footwear Simulation Scenario

An automated end-to-end integration scenario (`test_e2e_footwear_traceability_lifecycle.py`) will simulate a complete factory lifecycle:

```text
Step 1:  Procure 500 kg raw leather and 1,000 rubber outsoles into Factory Raw Material Store (GRN-2026-001).
Step 2:  Record Landed Costs (Duty, Freight, Insurance) and verify effective unit rate capitalization.
Step 3:  Create Production Batch B-801 for 200 pairs of Chelsea Boots (Size 41, Color: Cognac Brown).
Step 4:  Verify automatic BOM deduction of raw leather and outsoles from Raw Material Store.
Step 5:  Complete production batch, verifying 200 pairs incremented into Factory Central Finished Store.
Step 6:  Associate batch photo in Product Gallery.
Step 7:  Create Transfer TRF-001 to move 100 pairs from Factory Store to Kathmandu Branch.
Step 8:  Dispatch TRF-001: Factory store balance becomes 100, In-Transit balance becomes 100.
Step 9:  Kathmandu Branch inspects shipment: receives 95 pairs, reports 5 pairs damaged in transit.
Step 10: Verify Kathmandu Branch available stock = 95, Branch Quarantine = 5, In-Transit = 0.
Step 11: Create Sales Order SO-001 for wholesale buyer at Kathmandu Branch for 50 pairs.
Step 12: Dispatch Sales Order SO-001: Kathmandu Branch stock decreases from 95 to 45.
Step 13: Generate Sequential Tax Invoice INV-2026-001 with 13% statutory VAT.
Step 14: Execute Traceability Query for Batch B-801:
         - Verifies initial 200 pairs produced
         - Verifies 100 pairs remaining at Factory
         - Verifies 45 pairs available at Kathmandu Branch
         - Verifies 5 pairs quarantined at Kathmandu Branch
         - Verifies 50 pairs sold under INV-2026-001
Step 15: Run reconciliation: Sum of all location balances (100 + 45 + 5 + 50 sold) == 200 pairs produced.
```

---

## 4. Test Execution Gate

Before any release candidate is promoted:
1. All 369 existing tests must pass.
2. All new tests (T-DATE, T-I18N, T-LOC, T-CONC, and 15-Step E2E) must pass.
3. Frontend TypeScript build must pass with 0 errors.
4. Total test count expected to exceed **400 passed automated tests**.
