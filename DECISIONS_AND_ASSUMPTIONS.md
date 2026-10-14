# LIVO FOOTWEAR ERP — DECISIONS AND ASSUMPTIONS REGISTER

**Document:** Business Decisions, Technical Assumptions & Client Clarifications  
**Project:** LIVO Industrial Footwear Enterprise Resource Planning (ERP)  
**Baseline Commit:** `5caa3f471e92aece268d0fa519a920e7cc7dc512` (Branch: `main`)  
**Operating Mode:** STRICT PLANNING & VALIDATION — Zero code or migrations executed  
**Status:** ALL SIX DECISIONS AWAITING CLIENT CONFIRMATION  
**Last Updated:** 2026-10-12  

---

## 1. Purpose & Governance Rules

This register documents all unresolved business choices that materially affect the data model, accounting, inventory integrity, permissions, and operational infrastructure of the LIVO Footwear ERP.

### Non-Negotiable Governance Invariants:
1. **Zero Fabricated Approval:** In strict adherence to Phase 3.5 directives, no client decision is assumed or marked confirmed without explicit, written confirmation in available project records.
2. **Explicit Standardized Statuses:** Every decision is formally marked as one of:
   - `AWAITING_CLIENT_CONFIRMATION`: Requires client confirmation before related mutating work can proceed.
   - `CONFIRMED`: Explicit confirmation verified in written records (currently NONE).
   - `NOT_APPLICABLE`: Requirement retracted or eliminated.
3. **Safety Isolation of Blocked Work:** Where an unresolved decision could cause inventory corruption, statutory tax/accounting non-compliance, or sensitive PII leakage, all dependent implementation phases are marked as **BLOCKED** and will not proceed until authorized.

---

## 2. Decision Register

### Decision A — Production Batch Color: Floor Lot Attribute vs. Master Catalog Variant
- **Current Evidence:**  
  In the current database schema ([models/production.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/production.py)), `production_batches` contains `batch_number`, `product_id`, `target_quantity`, and `produced_quantity`. It lacks any `color` column. In [models/stock.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/stock.py), `color` is an immutable column on the master `products` catalog table. In [ProductionView.tsx](file:///d:/Antigravity/Footwear%20app/frontend/src/components/ProductionView.tsx), the operator is forced to select an existing product, and color is displayed statically from that SKU.
- **Exact Unresolved Question:**  
  > *"When a factory operator manually types a color name on the production dock (e.g., 'Olive Green' or 'Matte Black'), should the system automatically create a brand new product SKU in the master catalog with its own price, barcode, and inventory card, or should the typed color remain strictly an attribute of that specific production batch?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (Batch-Level Lot Attribute — Recommended):** Add `color VARCHAR(50)` directly to `production_batches`. The floor UI provides an open combobox that auto-suggests existing catalog colors but allows typing any custom color string without altering the catalog.  
    *Trade-off:* Master catalog remains clean and uncluttered; inventory reporting aggregates by parent article code while retaining lot-level color visibility.
  - **Option 2 (Auto-Create Master Product Variant):** When an unlisted color string is entered, backend automatically inserts a new row into `products`.  
    *Trade-off:* Operators will inevitably introduce typos (e.g. "Blk", "black", "BLACK", "Black ") resulting in catalog explosion, duplicate orphan SKUs, and fragmented stock consolidation.
  - **Option 3 (Strict Predefined Dropdown Only):** Reject free-text typing; force admins to pre-configure colors in an admin dictionary.  
    *Trade-off:* Directly violates the client's explicit request for quick, manual entry during floor dyeing runs.
- **Recommended Default & Rationale:**  
  **Option 1.** Retain the color as a production batch attribute. This fulfills the client's request for floor speed without risking master catalog corruption.
- **Risks if Recommendation is Wrong:**  
  If the client later demands that each floor color have an independent sales price and barcode, batch-colored goods would need to be retroactively split into separate catalog SKUs.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 4 (Workstream 1.1)** — Migration `016` column definition and backend batch creation endpoints.

---

### Decision B — Purchase Expenses: Landed Cost Capitalization vs. Operating Expense Ledger
- **Current Evidence:**  
  The client provided a handwritten ledger format: `| S.N. | Date | Particular | Carrying-in Expense | Import Duty/Tax | China Carrying-in Expense | Insurance |`. The existing database schema ([models/purchase.py:58-63](file:///d:/Antigravity/Footwear%20app/backend/app/models/purchase.py#L58-L63)) already captures these four exact monetary components in integer paisa (`carrying_in_paisa`, `import_duty_paisa`, `china_carrying_paisa`, `insurance_paisa`) upon Goods Receipt Note (GRN) and capitalizes them into the raw material inventory rate (`effective_unit_rate_paisa`).
- **Exact Unresolved Question:**  
  > *"Should the 4 purchase expenses (Carrying-in, Import Duty/Tax, China Carrying-in, and Insurance) continue to be added into the valuation/cost of the received raw materials (capitalized landed cost), or should they be recorded in a separate standalone factory expense ledger without affecting raw material inventory valuation?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (UI Ledger Reporting View — Recommended):** Preserve current inventory capitalization math in `models/purchase.py` and build a dedicated "Landed Cost Ledger" tab in [PurchaseView.tsx](file:///d:/Antigravity/Footwear%20app/frontend/src/components/PurchaseView.tsx) displaying the client's exact handwritten column layout aggregating the existing GRN cost data.  
    *Trade-off:* Zero database schema duplication; preserves raw material valuation integrity and compliance with Nepal statutory accounting standards (NAS 2 / IAS 2) for imported inventory.
  - **Option 2 (Standalone General Expense Entry):** Decouple these expenses from purchase orders and require entering them into a new general expense subledger.  
    *Trade-off:* Violates accounting standards for imported inventory valuation; distorts Cost of Goods Sold (COGS); breaks existing landed-cost unit tests.
  - **Option 3 (Duplicate Tracking):** Record expenses both in PO landed costs and in an expense ledger.  
    *Trade-off:* High risk of double-counting freight/duty expenses in profit-and-loss statements.
- **Recommended Default & Rationale:**  
  **Option 1.** Render the 4 columns as a dedicated reporting and filtering ledger in `PurchaseView.tsx` directly from the existing purchase records.
- **Risks if Recommendation is Wrong:**  
  If the client pays freight carriers on separate credit terms months after PO receipt and requires separate voucher tracking, a dedicated accounts-payable subledger for logistics vendors would be required.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 6 (Workstream 3.2)** — Purchase ledger presentation vs. expense subledger schema.

---

### Decision C — Worker Citizenship Documents: Storage Security, Format & Access Policy
- **Current Evidence:**  
  The client requested storing worker citizenship photographs alongside temporary and permanent addresses. In the codebase, [models/worker.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/worker.py) already contains `temporary_address` and `permanent_address` columns, but lacks a document table. The public product gallery ([models/gallery.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/gallery.py)) serves product photos publicly via `/static/uploads/products`. Citizenship cards are sensitive government-issued Personally Identifiable Information (PII) under Nepal privacy law.
- **Exact Unresolved Question:**  
  > *"How should worker citizenship cards be captured (as two separate photos for Front & Back, or as a single document/PDF), and which specific organizational roles are authorized to view and download these identity documents: Factory Administrators only, or also Floor Supervisors/Editors?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (Secure Isolated Vault, Admin-Only — Recommended):** Create an isolated `worker_documents` table with non-public storage (`/storage/secure_docs/workers/`). Restrict read/write strictly to `require_admin`. Support dual-photo upload (`CITIZENSHIP_FRONT`, `CITIZENSHIP_BACK`) and single PDF. Audit log all downloads.  
    *Trade-off:* Maximum security and legal compliance; floor supervisors cannot view identity documents without admin credentials.
  - **Option 2 (Allow Floor Supervisors / Editors to View):** Permit users with the `editor` role to upload and view worker citizenship scans.  
    *Trade-off:* High insider threat risk; allows factory floor staff to access fellow workers' national identity credentials.
  - **Option 3 (Public Static Media Directory):** Store in `/static/uploads/workers/` accessible via public URL.  
    *Trade-off:* **CRITICAL SECURITY RISK.** Anyone with a link could scrape worker national identity cards. Unacceptable.
- **Recommended Default & Rationale:**  
  **Option 1.** Administrative-only access, non-public binary streaming, magic-byte MIME validation, and immutable access logging.
- **Risks if Recommendation is Wrong:**  
  If HR clerks or factory timekeepers need to verify citizenship during onboarding without having full company administrator privileges, a specialized `hr_clerk` RBAC role would need to be introduced.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 5 (Workstream 2.2)** — Document vault endpoints, authorization dependencies, and UI tab visibility.

---

### Decision D — Waste & Scrap Accounting: Double Deduction Prevention & Rejection Semantics
- **Current Evidence:**  
  The client requested a "Waste Material Management" section. Currently, [models/bom.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/bom.py) and [models/production.py](file:///d:/Antigravity/Footwear%20app/backend/app/models/production.py) define the Bill of Materials and material usages. When a batch is created, `ProductionMaterialUsage` records raw material consumption. If raw material stock is automatically deducted a second time when scrap is logged, physical warehouse stock will suffer duplicate deductions.
- **Exact Unresolved Question:**  
  > *"When leather, rubber, or EVA sole scrap is recorded on the factory floor, does this represent material that was ALREADY deducted from inventory when the production batch was issued, or is it an additional loss that must decrement warehouse stock? Furthermore, are rejected finished footwear pairs tracked under this same section, and does scrap have any salvage or resale value?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (Informational Floor Log Without Automated Stock Deduction — Recommended Initial Step):** Create a `waste_records` table linking to batch ID, material, quantity, and waste type (`RAW_MATERIAL_SCRAP` vs `FINISHED_PAIR_REJECT`). Provide full audit tracking without automatically writing negative stock ledger entries until the client confirms the accounting rule.  
    *Trade-off:* 100% safe against stock ledger corruption; captures floor scrap metrics immediately.
  - **Option 2 (Automated Warehouse Stock Deduction):** Automatically append a negative `RAW_MATERIAL_OUT` movement when scrap is logged.  
    *Trade-off:* **CRITICAL RISK OF INVENTORY DRIFT.** If the BOM already accounts for standard cutting scrap (e.g. 10% allowance), logging scrap will deduct the physical raw material twice.
- **Recommended Default & Rationale:**  
  **Option 1.** Keep waste tracking strictly informational until Decision D is confirmed in writing by factory management.
- **Risks if Recommendation is Wrong:**  
  If the client expected scrap logging to immediately reduce warehouse stock, warehouse balance will temporarily show more inventory than physically on hand until manual adjustments are made.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 4 (Workstream 1.3)** — Waste ledger stock integration is **COMPLETELY BLOCKED**. Only the non-mutating record schema is permitted.

---

### Decision E — Fixed Assets Register: Capital Inventory vs. Depreciation Amortization
- **Current Evidence:**  
  The client requested tracking fixed assets (machinery, moulds, vehicles, tools, furniture) with items, quantities, and total amount. The codebase currently has zero fixed asset tables or depreciation engines.
- **Exact Unresolved Question:**  
  > *"Is the Fixed Assets section intended strictly as an inventory register of factory machinery, moulds, vehicles, and equipment with their acquisition details and total purchase valuation, or does your business require automated monthly or annual depreciation calculations and write-offs?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (Asset Inventory Register with Integer-Paisa Valuation — Recommended):** Implement `fixed_assets` table with `asset_code`, `asset_name`, `category`, `purchase_date_ad`, `purchase_date_bs`, `purchase_cost_paisa` (`BigInteger`), `quantity`, and `location`. Display total asset valuation in real-time.  
    *Trade-off:* Simple, robust, meets the explicit client description without introducing speculative accounting schedules.
  - **Option 2 (Full Fiscal Depreciation Engine):** Implement Straight-Line and Written-Down Value (WDV) depreciation calculation engines, fiscal year closing rules, and accumulated depreciation ledgers.  
    *Trade-off:* Substantial implementation complexity, tax vs book depreciation reconciliation risks, and ongoing audit overhead without verified client demand.
- **Recommended Default & Rationale:**  
  **Option 1.** Basic capital asset register in integer paisa. Depreciation can be added in a future phase if requested by the client's auditor.
- **Risks if Recommendation is Wrong:**  
  If the client's accounting team requires book net asset value (NAV) for year-end reporting, the register will only reflect historical acquisition cost.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 6 (Workstream 3.3)** — Asset depreciation calculation logic is **BLOCKED**; basic register design is ready for review.

---

### Decision F — Automated Daily Backup: Production Host Environment & Offsite Target
- **Current Evidence:**  
  The repository contains [scripts/backup_nightly.sh](file:///d:/Antigravity/Footwear%20app/scripts/backup_nightly.sh) (which invokes `docker compose exec -T postgres pg_dump ...`), [backend/app/services/backup_service.py](file:///d:/Antigravity/Footwear%20app/backend/app/services/backup_service.py) (which supports S3/B2/R2 upload and AES encryption), and [docker-compose.yml](file:///d:/Antigravity/Footwear%20app/docker-compose.yml). However, no OS daemon or cron schedule is currently active or source-controlled.
- **Exact Unresolved Question:**  
  > *"What is the exact target production hosting environment (e.g., an Ubuntu Linux VPS running Docker Compose, a standalone bare-metal server, or a managed cloud environment), and which remote cloud storage service (Backblaze B2, Cloudflare R2, or AWS S3) is designated for encrypted offsite backup copies?"*
- **Available Options & Trade-Offs:**
  - **Option 1 (Systemd Host Timer Triggering Docker Script — Recommended for Linux VPS):** Commit `livo-backup.service` and `livo-backup.timer` triggering daily at 02:00 NPT, alongside in-app backup age telemetry monitoring in `/health`.  
    *Trade-off:* Robust OS-level execution on Linux; independent of web server restarts; requires host root access to install.
  - **Option 2 (Dedicated Docker Backup Sidecar Container):** Add an alpine-based `backup-cron` container to `docker-compose.yml` that shares the docker socket or database network.  
    *Trade-off:* 100% self-contained within Docker; works on any Docker host without systemd; requires container socket access.
  - **Option 3 (Application-Level Background Task):** Run an asyncio timer within the FastAPI web process.  
    *Trade-off:* **UNSAFE FOR PRODUCTION.** Dies whenever the web worker restarts; prone to thread starvation during large database dumps.
- **Recommended Default & Rationale:**  
  **Option 1** for VPS deployments with a fallback to **Option 2** for containerized hosts, coupled with active background telemetry in the Ops Cockpit.
- **Risks if Recommendation is Wrong:**  
  If the target environment does not use systemd (e.g. AWS ECS or managed PaaS), systemd timer units cannot be used.
- **Decision Status:** `AWAITING_CLIENT_CONFIRMATION`
- **Blocked Implementation Phases:**  
  **Phase 7 (Workstream 4.1)** — OS scheduler deployment unit configuration.

---

## 3. Summary of Implementation Blockers

| Ref | Requirement | Unresolved Decision Area | Reason Implementation is Blocked |
|---|---|---|---|
| **A1** | `PROD-01` (Batch Color) | Batch lot string vs. Master catalog SKU | Risk of master catalog pollution and SKU fragmentation |
| **B1** | `FIN-03` (Purchase Expenses) | Landed cost capitalization vs. Standalone expense | Risk of statutory inventory valuation error under NAS 2 |
| **C1** | `HR-02` (Citizenship Vault) | National ID format and viewing authorization | Risk of sensitive PII exposure under Nepal privacy rules |
| **D1** | `PROD-03` (Waste & Scrap) | Stock deduction semantics vs. BOM consumption | **CRITICAL RISK OF DOUBLE STOCK DEDUCTION** |
| **E1** | `FIN-04` (Fixed Assets) | Asset inventory register vs. Depreciation schedules | Accounting complexity and statutory fiscal closing rules |
| **F1** | `OPS-01` (Daily Backups) | Production hosting target (Systemd vs Docker vs Cloud) | Host scheduler incompatibility |
