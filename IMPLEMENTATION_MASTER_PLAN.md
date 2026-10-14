# LIVO FOOTWEAR ERP — IMPLEMENTATION MASTER PLAN & CHANGE CONTROL

**Document:** Implementation Master Plan, Technical Specifications & Risk Control Architecture  
**System:** LIVO Industrial Footwear Enterprise Resource Planning (ERP)  
**Repository:** `https://github.com/Sishir120/livo-footwear-erp`  
**Current Baseline Commit:** `5caa3f471e92aece268d0fa519a920e7cc7dc512` (Branch: `main`)  
**Operating Mode:** STRICT PLANNING & PRE-IMPLEMENTATION VALIDATION ONLY — Zero application code or migrations modified  
**Status:** READY FOR USER/CLIENT REVIEW & APPROVAL (NO CODE AUTHORIZATION GRANTED YET)  
**Last Updated:** 2026-10-12  

---

## 1. Executive Summary & Governance Model

This Master Plan establishes the engineering blueprint for implementing the client's verified change requests for the LIVO Footwear ERP. It translates the forensic findings from [CLIENT_CHANGE_REQUEST_SECOND_PASS_GAP_ANALYSIS.md](file:///d:/Antigravity/Footwear%20app/CLIENT_CHANGE_REQUEST_SECOND_PASS_GAP_ANALYSIS.md), [PRE_IMPLEMENTATION_VALIDATION_REPORT.md](file:///d:/Antigravity/Footwear%20app/PRE_IMPLEMENTATION_VALIDATION_REPORT.md), and [DECISIONS_AND_ASSUMPTIONS.md](file:///d:/Antigravity/Footwear%20app/DECISIONS_AND_ASSUMPTIONS.md) into a sequence of safe, dependency-aware workstreams.

### Strict Governance Terminology (Phase 3.5 & 4 Standards):
To eliminate ambiguity between technical readiness and business authorization, the following mutually exclusive terms govern all requirements in this plan:
1. **Verified Existing Functionality:** Features proven by forensic code and test inspection to fully satisfy the requirement in the current codebase. No new code or migration is required.
2. **Proposed Implementation Scope:** Technical interventions identified by engineering as necessary to address genuine gaps.
3. **Business-Decision Blocked:** Features whose implementation or schema design directly depends on unresolved client business choices (e.g., inventory valuation, scrap accounting, PII access policy).
4. **Technically Blocked:** Features whose implementation depends on a preceding technical deliverable (e.g., gallery batch linkage requires batch color/id schema).
5. **Ready for Approval:** Technical designs that are completely specified, dependency-checked, risk-assessed, and packaged for client review.
6. **Authorized for Implementation:** Features that have received explicit, written client sign-off. **Currently 0 requirements are authorized.**

---

## 2. Verified Baseline & Invariants to Preserve

Before planning any code changes, the following existing guarantees have been forensically audited and must be preserved across all upcoming workstreams:

```
+---------------------------------------------------------------------------------------------------------------+
|                                      SYSTEM GUARANTEES & ARCHITECTURAL INVARIANTS                             |
+------------------------------+----------------------------------------------------+---------------------------+
| Dimension                    | Active Mechanism & Source File                     | Mandatory Preservation    |
+------------------------------+----------------------------------------------------+---------------------------+
| **Financial Precision**      | Integer paisa (BigInteger) & quantize_npr          | Zero floating-point drift |
| **Statutory VAT**            | 13% statutory rate, Schedule-5 printable bill      | Anti-tampering server side|
| **Document Numbering**       | SELECT ... FOR UPDATE row locks in sequence.py     | Monotonic, zero duplicates|
| **Finished Inventory**       | stock_movements append-only ledger (+1/-1)         | No direct balance editing |
| **Raw Material Inventory**   | raw_material_movements append-only ledger (+1/-1)  | No direct balance editing |
| **Concurrency Protection**   | pg_advisory_xact_lock in backend/app/core/locks    | Mutex across all mutations|
| **Multi-Tenant Isolation**   | company_id ForeignKey on all 30 business tables    | Zero cross-tenant IDOR    |
| **Offline Synchronization**  | livo_factory_offline_v1 IndexedDB & UUID keys      | Idempotent batch replay   |
| **Nepali Calendar**          | Bidirectional engine covering 1979-2100 BS         | 0 external dependencies   |
| **RBAC Authorization**       | require_editor, require_admin, read-only viewer    | Viewer blocked from writes|
+------------------------------+----------------------------------------------------+---------------------------+
```

---

## 3. Reconciled Scope & Requirement Classification Matrix

| Requirement ID | Requirement Name | Verified Status | Intended Final Behavior | Minimum Implementation | Existing Code to Reuse | Files Likely to Change | Database Impact | Dependencies | Client Decision | Planning Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| **DATE-01** | Nepali Date (BS) | `VERIFIED_IMPLEMENTED` | Dual BS/AD date conversion and display across all modules. | None. Already operating end-to-end. | `core/nepali_date.py`, `lib/nepaliDate.ts`, `NepaliDatePicker.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **DATE-02** | Dispatch Date on Sales | `VERIFIED_IMPLEMENTED` | Decoupled sales order confirmation from physical dispatch. | None. Already operating end-to-end. | `api/v1/sales.py:471`, `SalesInvoiceView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **DATE-03** | Purchase Ordered vs Receipt Date | `VERIFIED_IMPLEMENTED` | PO workflow separating order date from physical GRN receipt date. | None. Already operating end-to-end. | `api/v1/purchase.py:258`, `PurchaseView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **DATE-04** | Sales Ordered vs Dispatch Date | `VERIFIED_IMPLEMENTED` | Independent persistence and display of both sales order dates. | None. Already operating end-to-end. | `models/sales.py:33-36`, `SalesInvoiceView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **PROD-01** | Batch Serial, Article, Name, Color | `PRESENT_BUT_INCORRECT` | Operator can manually type batch color on floor dock; persists on batch. Batch serial number is satisfied by existing monotonic `batch_number`. | Add `color VARCHAR(50)` to `production_batches`; add open combobox in UI. Do NOT add redundant `serial_no`. | `models/production.py`, `ProductionView.tsx`, `core/sequence.py` | `models/production.py`, `api/v1/production.py`, `ProductionView.tsx` | Add `color VARCHAR(50)` to `production_batches` | None | A1 (SKU vs Lot) | **Proposed Scope (Business-Decision Blocked on A1; Ready for Approval)** |
| **STOCK-01** | Automatic Stock Updates | `VERIFIED_IMPLEMENTED` | Append-only ledger updates across all inward/outward events. | Connect waste/scrap recording once approved. | `api/v1/stock.py`, `api/v1/purchase.py`, `api/v1/production.py` | None (until scrap logic approved) | None | None | None | **Verified Existing Functionality** |
| **STOCK-02** | Raw Material Stock Management | `VERIFIED_IMPLEMENTED` | Physical movement ledger, stock card modal, running balances. | None. Already operating end-to-end. | `api/v1/purchase.py:325`, `PurchaseView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **STOCK-03** | Raw Material Units | `VERIFIED_IMPLEMENTED` | Strict restriction to `kg`, `pcs`, `litre`. | None. CheckConstraint already enforced. | `models/purchase.py:25`, `PurchaseView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **PROD-02** | Production Gallery Lot Linkage | `PRESENT_BUT_INCORRECT` | Photographs can be attached to specific production batches. | Add `production_batch_id` FK to `product_images`; add batch upload UI and dual validation (tenant + product match). | `models/gallery.py`, `api/v1/gallery.py`, `ProductGalleryView.tsx` | `models/gallery.py`, `api/v1/gallery.py`, `ProductGalleryView.tsx` | Add `production_batch_id` nullable FK to `product_images` | `PROD-01` | None | **Proposed Scope (Technically Blocked on PROD-01; Ready for Approval)** |
| **PROD-03** | Waste Material Management | `MISSING` | Floor operators can log material offcuts and scrap without corrupting stock. | Create `waste_records` schema in Phase 4D; hold automated stock deduction. | `models/purchase.py` (RM refs), `TenantRepository` | `models/production.py`, `api/v1/production.py`, new `WasteView.tsx` | New table `waste_records` (Phase 4D) | `STOCK-02` | D1 (Double deduct) | **Proposed Scope (Business-Decision Blocked on D1; Ready for Approval)** |
| **HR-01** | Worker Cards Display | `PARTIALLY_IMPLEMENTED` | Worker directory presents visual cards with avatar, name, and employee code. | Add visual card grid view in UI with avatar thumbnails. | `HRManagementView.tsx`, `models/worker.py` | `frontend/src/components/HRManagementView.tsx` | None | None | None | **Proposed Scope (Ready for Approval)** |
| **HR-02** | Worker Profile & Citizenship Vault | `PARTIALLY_IMPLEMENTED` | Full profile with addresses, hours, and admin-only encrypted citizenship storage. | Expose address fields in schemas; create secure `worker_documents` table & vault. | `models/worker.py`, `api/v1/hr.py`, `HRManagementView.tsx` | `models/worker.py`, `schemas/worker.py`, `api/v1/hr.py`, `HRManagementView.tsx` | New table `worker_documents` | `HR-01` | C1 (Access policy)| **Proposed Scope (Business-Decision Blocked on C1; Ready for Approval)** |
| **HR-03** | Worker Active/Inactive Workflow | `PARTIALLY_IMPLEMENTED` | Deactivation prompts confirmation modal recording inactive date and reason. | Add confirmation modal in UI; update `api/v1/hr.py` to record inactive audit fields. | `models/worker.py:25-26`, `api/v1/hr.py` | `backend/app/api/v1/hr.py`, `frontend/src/components/HRManagementView.tsx` | Fields exist; backfill in migration | `HR-01` | None | **Proposed Scope (Ready for Approval)** |
| **HR-04** | Salary & Advance Information | `PARTIALLY_IMPLEMENTED` | Side-by-side display of hours, basic rate, advance due, and current net payable. | Enrich worker table/cards with live net payable calculations. | `api/v1/hr.py:367`, `HRManagementView.tsx` | `frontend/src/components/HRManagementView.tsx` | None | `HR-01` | None | **Proposed Scope (Ready for Approval)** |
| **FIN-01** | General Factory Expenses | `MISSING` | Record factory operating overhead (rent, diesel, generator, maintenance). | Create `general_expenses` schema, API CRUD endpoints, and Expenses UI view. | `models/sales.py` (`SalesExpense` pattern), `TenantRepository` | `models/finance.py`, `api/v1/expenses.py`, `frontend/src/components/ExpensesView.tsx` | New table `general_expenses` | None | None | **Proposed Scope (Ready for Approval)** |
| **FIN-02** | Sales Expenses Subledger | `VERIFIED_IMPLEMENTED` | S.N., Date, Particular, Amount, Remarks linked to sales orders. | None. Already operating end-to-end. | `models/sales.py`, `api/v1/sales.py`, `SalesInvoiceView.tsx` | None | None | None | None | **Verified Existing Functionality** |
| **FIN-03** | Purchase Expenses Multi-Column Ledger | `PARTIALLY_IMPLEMENTED` | View handwritten ledger format (`| S.N. | Date | Particular | Carrying | Duty | China | Insurance |`). | Build dedicated multi-column ledger tab in `PurchaseView.tsx`. | `models/purchase.py:58-63`, `PurchaseView.tsx` | `frontend/src/components/PurchaseView.tsx` | None | `STOCK-02` | B1 (Accounting) | **Proposed Scope (Business-Decision Blocked on B1 reclass; UI is Ready for Approval)** |
| **FIN-04** | Fixed Assets Register | `MISSING` | Track factory machinery, moulds, vehicles, and equipment valuation. | Create `fixed_assets` schema, API CRUD endpoints, and Fixed Assets UI view. | `TenantRepository`, integer-paisa currency utilities | `models/assets.py`, `api/v1/assets.py`, `frontend/src/components/FixedAssetsView.tsx` | New table `fixed_assets` | None | E1 (Depreciation)| **Proposed Scope (Business-Decision Blocked on E1 depr; Basic reg is Ready for Approval)** |
| **OPS-01** | Automated Daily Backup Scheduler | `PARTIALLY_IMPLEMENTED` | Automated daily execution, retention, monitoring, and restore verification. | Commit systemd service/timer units; add background telemetry ping to Ops Cockpit. | `scripts/backup_nightly.sh`, `backup_service.py`, `OpsCockpitView.tsx` | `scripts/livo-backup.service`, `scripts/livo-backup.timer`, `api/v1/health.py` | None | None | F1 (Host target) | **Proposed Scope (Business-Decision Blocked on F1; Units Ready for Approval)** |

---

## 4. Phased Implementation Roadmap

The implementation is structured into sequential phases to minimize blast radius and enforce dependency order:

```
+-------------------------------------------------------------------------------------------------------------------+
|                                        DEPENDENCY-AWARE IMPLEMENTATION PHASES                                     |
+-------------------------------------------------------------------------------------------------------------------+
|                                                                                                                   |
|  [PHASE 4A: Production Batch Metadata & Batch-Specific Media Linkage]                                             |
|  ├── Workstream 1.1: Typable Batch Color (`PROD-01` — Ready for approval; serial satisfied by batch_number)         |
|  └── Workstream 1.2: Production Batch Photograph Linkage (`PROD-02` — Dual tenant + product validation)           |
|                                                                                                                   |
|  [PHASE 4B: HR Worker Profile Cards, KYC & Identity Vault]                                                         |
|  ├── Workstream 2.1: Worker Directory Card Grid View (`HR-01` — Ready for approval)                               |
|  ├── Workstream 2.2: Worker Profile Modal, Address Fields & Admin Citizenship Vault (`HR-02` — Blocked on C1)     |
|  ├── Workstream 2.3: Formal Deactivation Modal with Inactive Date & Reason (`HR-03` — Ready for approval)          |
|  └── Workstream 2.4: Directory Salary & Current Net Payable Enrichment (`HR-04` — Ready for approval)             |
|                                                                                                                   |
|  [PHASE 4C: Factory Overhead Expenses, Purchase Ledger & Fixed Assets]                                             |
|  ├── Workstream 3.1: General Factory Operating Expenses Module (`FIN-01` — Ready for approval)                    |
|  ├── Workstream 3.2: Purchase Multi-Column Landed Cost Ledger UI (`FIN-03` — Ready for approval)                   |
|  └── Workstream 3.3: Fixed Assets Inventory Register & Valuation (`FIN-04` — Ready for approval, blocked on E1)   |
|                                                                                                                   |
|  [PHASE 4D: Floor Scrap & Waste Accounting] (STRICTLY BLOCKED ON DECISION D1)                                     |
|  └── Workstream 4.1: Waste Records Schema & Floor Logging (Held until double-deduction rules confirmed)           |
|                                                                                                                   |
|  [PHASE 4E: Backup Automation & Operational Monitoring] (BLOCKED ON DECISION F1)                                  |
|  ├── Workstream 5.1: Host-Specific Scheduler Service & Timer Configuration (`OPS-01`)                             |
|  └── Workstream 5.2: Background Backup Age Telemetry in /health and Ops Cockpit Card                              |
|                                                                                                                   |
|  [PHASE 5: Regression Validation, Security Audit & Release Readiness]                                             |
|  ├── Workstream 6.1: Complete 295+ Pytest Regression Suite Run (100% green pass required)                         |
|  ├── Workstream 6.2: Next.js Production Build & Bundle Budget Verification (<= 115 kB)                            |
|  └── Workstream 6.3: Multi-Tenant IDOR and Financial Ledger Reconciliation Verification                           |
|                                                                                                                   |
+-------------------------------------------------------------------------------------------------------------------+
```

---

## 5. Cross-Module Dependencies for Phase 4A

```
                    +------------------------------------+
                    | Migration 016 (Batch Color & Media)|
                    +-----------------+------------------+
                                      |
                           +----------v----------+
                           |  PROD-01 Batch Color|
                           |  (color VARCHAR(50))|
                           +----------+----------+
                                      |
                           +----------v----------+
                           |  PROD-02 Gallery    |
                           |  Batch Linkage      |
                           |  (production_batch) |
                           +---------------------+
```

---

## 6. Database and Migration Plan: Phase 4A

### Migration 016: `016_production_batch_color_and_gallery_link.py`
- **Prerequisite:** Head `015_sales_dispatch_and_expenses`
- **Design Rationale:**
  - Redundant `serial_no` column is **eliminated**; `ProductionBatch.batch_number` already satisfies the monotonic serial identifier requirement.
  - Blocked `waste_records` table is **isolated** to Phase 4D, keeping Migration 016 strictly scoped and non-destructive.
- **Schema Modifications:**
  1. `ALTER TABLE production_batches ADD COLUMN color VARCHAR(50);`
  2. `ALTER TABLE product_images ADD COLUMN production_batch_id INTEGER REFERENCES production_batches(id) ON DELETE SET NULL;`
  3. `CREATE INDEX ix_product_images_company_batch ON product_images (company_id, production_batch_id);`
- **Backfill Strategy:**
  - All added columns are `nullable=True`. Existing historical records default to `NULL`.
  - For historical batches with `color = NULL`, UI gracefully displays the master product's default catalog color.
  - For historical images with `production_batch_id = NULL`, UI cleanly displays the general catalog badge.
- **Rollback (`downgrade`):**
  - Drop index `ix_product_images_company_batch`.
  - Drop foreign key `fk_product_images_production_batch_id`.
  - Drop column `production_batch_id` from `product_images`.
  - Drop column `color` from `production_batches`.

---

## 7. Backend & API Plan: Phase 4A

### 7.1 Production Batch Module (`backend/app/api/v1/production.py`)
- **`ProductionBatchCreate` Schema:**
  - Add `color: Optional[str] = Field(None, max_length=50)`
  - Keep `batch_number` generated monotonically via `generate_document_number(db, company_id, "PRODUCTION", "PROD")`.
- **`ProductionDraftSyncRequest` Schema:**
  - Add `color: Optional[str] = Field(None, max_length=50)`
- **`POST /api/v1/production/batches` & `POST /api/v1/production/sync/draft`:**
  - Persist `color` directly to `ProductionBatch.color`.
  - Invariant: Zero modifications to `products` table. Free-text floor color typing does not create catalog SKUs.

### 7.2 Media Gallery Module (`backend/app/api/v1/gallery.py`)
- **`POST /api/v1/gallery/upload/{product_id}`:**
  - Accept optional query or form parameter `production_batch_id: Optional[int] = None`.
  - **Dual Integrity Guard:**
    1. Tenant Guard: Verify `batch.company_id == current_user.company_id` (returns HTTP 404 if not found).
    2. Product Alignment Guard: Verify `batch.product_id == product_id` (returns HTTP 422 if mismatched).
- **`GET /api/v1/gallery`:**
  - Perform outer join:
    ```python
    query = db.query(ProductImage, Product, ProductionBatch).join(
        Product, ProductImage.product_id == Product.id
    ).outerjoin(
        ProductionBatch, (ProductImage.production_batch_id == ProductionBatch.id) & (ProductionBatch.company_id == current_user.company_id)
    ).filter(
        ProductImage.company_id == current_user.company_id,
        Product.company_id == current_user.company_id
    )
    ```
  - Map response fields:
    - `production_batch_id = img.production_batch_id`
    - `batch_number = batch.batch_number if batch else None`
    - `batch_color = batch.color if (batch and batch.color) else prod.color`
    - `batch_date_bs = batch.date_bs if batch else None`

---

## 8. Frontend and UI Plan: Phase 4A

### 8.1 Production Dock (`frontend/src/components/ProductionView.tsx`)
- Replace the locked color text with an accessible combobox (`<input list="catalog-colors-datalist">`).
- Auto-suggest existing catalog SKU colors while permitting arbitrary custom floor color typing (e.g. "Olive Green", "Matte Black").
- Send `color` in the `draftPayload` to `/api/v1/production/sync/draft`.
- In the historical batch table, render the lot color badge next to the batch number.

### 8.2 Product Media Gallery (`frontend/src/components/ProductGalleryView.tsx`)
- In the Upload Modal:
  - Add an optional "Attach to Production Batch (Optional)" select dropdown.
  - Dropdown options are filtered strictly by `selectedProductId` and `currentCompanyId`.
- In Gallery Card Footer:
  - Render metadata: `Article: {product_code} | Name: {product_name}`.
  - If `batch_number` is present: render `Batch: #{batch_number} | Color: {batch_color} | Date: {batch_date_bs}`.
  - If `batch_number` is null: render `Catalog SKU | Color: {product_color || "Standard"}`.

---

## 9. Security & Data Integrity Safeguards

```
+---------------------------------------------------------------------------------------------------------------+
|                                      SECURITY & DATA INTEGRITY MATRIX (PHASE 4A)                              |
+------------------------------+----------------------------------------------------+---------------------------+
| Area                         | Threat / Failure Mode                              | Enforced Safeguard        |
+------------------------------+----------------------------------------------------+---------------------------+
| **Tenant IDOR**              | Attaching image to another company's batch.        | Backend verifies          |
|                              |                                                    | batch.company_id == user  |
|                              |                                                    | returns HTTP 404.         |
| **Product Mismatch**         | Attaching image of Shoe A to a batch of Shoe B.    | Backend verifies          |
|                              |                                                    | batch.product_id == prod  |
|                              |                                                    | returns HTTP 422.         |
| **Catalog Corruption**       | Floor typing creates fragmented duplicate SKUs.    | Color stored strictly on  |
|                              |                                                    | ProductionBatch. Zero     |
|                              |                                                    | rows added to products.   |
| **Batch Deletion Cascade**   | Deleting batch destroys product photo.             | ON DELETE SET NULL on FK. |
|                              |                                                    | Image reverts to catalog. |
| **Path Traversal & Payload** | Malicious file upload or path breakout.            | Magic-byte validation &   |
|                              |                                                    | _safe_resolve_image_path. |
+------------------------------+----------------------------------------------------+---------------------------+
```

---

## 10. Test Plan: Phase 4A

A dedicated test suite [backend/tests/test_production_batch_color_and_gallery.py](file:///d:/Antigravity/Footwear%20app/backend/tests/test_production_batch_color_and_gallery.py) will be created containing 8 explicit test cases:

1. `test_online_batch_creation_with_custom_color`: POST batch with custom color; verify persistence and sequential batch number.
2. `test_offline_draft_sync_with_custom_color`: POST `/sync/draft` with custom color; verify persistence and idempotency replay.
3. `test_custom_color_does_not_create_product_sku`: Assert `products` table row count is identical before and after creating custom color batch.
4. `test_upload_image_with_valid_batch_association`: Upload image with valid batch ID; verify `batch_number` and `batch_color` returned in `GET /gallery`.
5. `test_upload_image_without_batch_association_preserves_catalog_defaults`: Upload image with no batch ID; verify `batch_number is None` and catalog color displayed.
6. `test_cross_tenant_batch_link_rejected`: User from Company 1 attempts to link image to Company 2 batch; verify HTTP 404 rejection.
7. `test_mismatched_product_batch_link_rejected`: User attempts to link image of Product 1 to batch of Product 2; verify HTTP 422 rejection.
8. `test_historical_images_without_batch_links_serialize_cleanly`: Pre-existing images with `production_batch_id=None` serialize cleanly without error.

#### Post-Implementation Test Execution Commands:
```bash
# 1. Targeted Phase 4A Suite
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_production_batch_color_and_gallery.py -v

# 2. Existing Production & Gallery Regression Suites
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_gallery_and_analytics.py backend/tests/test_offline_sync.py -v

# 3. Frontend Production Build & Type Check
cd frontend && npm run build
```

---

## 11. Acceptance Criteria

1. **Floor Color Customization:**
   - Operators can select an existing color or type a custom dye lot name (e.g. "Matte Olive").
   - The custom color survives page refresh, offline sync replay, and batch listing.
   - The master catalog `products` table has zero unintended rows created.
2. **Production Gallery Association:**
   - Gallery cards display Article No, Article Name, Batch Color, and Batch No for batch-associated photos.
   - General product photos continue to display catalog metadata cleanly.
3. **Security Invariant:**
   - Cross-tenant and mismatched-product associations are blocked at the API level with HTTP 404 and HTTP 422.

---

## 12. Unresolved Risks & Mitigations

```
+------------------------------------------+---------------------+---------------------------------------------------------------+
| Risk Description                         | Severity Level      | Architectural Mitigation                                      |
+------------------------------------------+---------------------+---------------------------------------------------------------+
| **Cross-Tenant IDOR on Batch Link**      | HIGH (Security)     | Backend query filters by `company_id = user.company_id`.       |
| **Product Mismatch on Batch Link**       | MEDIUM (Integrity)  | Backend validates `batch.product_id == product.id` (HTTP 422).|
| **Legacy Media Serialization Breakage**  | LOW (Presentation)  | Outer join with automatic fallback to master product color.   |
+------------------------------------------+---------------------+---------------------------------------------------------------+
```

---

## 13. Release-Readiness Checklist (Phase 4A)

- [ ] All 16 historical Alembic migrations remain untouched.
- [ ] Migration 016 applies cleanly and supports complete rollback (`downgrade`).
- [ ] All 295 existing tests remain 100% green.
- [ ] All 8 new Phase 4A tests pass with 0 failures.
- [ ] Next.js production build succeeds with 0 TypeScript/ESLint errors and First Load JS $\le 115\text{ kB}$.
- [ ] Industrial Paper design aesthetics and bilingual English/Nepali localization preserved.

---

## 14. STOP CONDITION

In strict compliance with prompt directives:
- The Phase 4A plan has been revised and corrected.
- Redundant `serial_no` columns have been eliminated.
- Dual tenant and product integrity validations are established.
- **Zero application code, schemas, migrations, or tests have been modified.**

**Awaiting your explicit authorization to begin Phase 4A implementation.**
