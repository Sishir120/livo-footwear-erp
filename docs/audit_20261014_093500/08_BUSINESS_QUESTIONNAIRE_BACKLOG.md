# LIVO FOOTWEAR ERP — BUSINESS QUESTIONNAIRE BACKLOG

**Document Identifier:** `08_BUSINESS_QUESTIONNAIRE_BACKLOG.md`  
**Audit Directory:** `docs/audit_20261014_093500/`  
**Audit Execution Date:** 2026-10-14 09:35:00 +05:45 (Nepal Standard Time)  
**Primary Principle:** Do not infer accounting treatment or operational policy where the business rules are unspecified. Separate approved client decisions from technical recommendations.

---

## 1. EXECUTIVE QUESTIONNAIRE SUMMARY

This backlog contains 8 critical business decisions that require formal sign-off from the factory management / client owner of LIVO GROUP OF INDUSTRIES. These decisions directly affect data structures, financial ledger calculations, tax compliance, and user interface workflows.

---

## 2. PRIORITIZED DECISION ITEMS

### BQ-01: VAT Applicability on Wholesale Invoicing & Tax Exemptions
- **Module:** Sales & Invoicing (`invoices.py`, `SalesInvoiceView.tsx`).
- **Current Behavior with Evidence:**  
  Following the October 12 hotfix (Transcript `1849f93e` Step 10498), `backend/app/api/v1/invoices.py:110-126` enforces a mandatory statutory 13% Nepal VAT on all generated tax invoices. Invoices cannot be submitted with 0% VAT unless the `is_tax_exempt` flag is explicitly passed with registered tax-exempt documentation.
- **What Remains Uncertain:**  
  Are all LIVO footwear products sold to registered wholesalers subject to 13% VAT, or does the factory issue non-VAT challans / estimate bills (निकासी बिल / कच्चा बिल) for small retail parties?
- **Exact Question to Ask Client:**  
  *"Does LIVO GROUP issue official 13% VAT Tax Invoices for all wholesale dispatches, or does your operation require issuing non-VAT delivery challans / cash estimate bills for certain parties without charging 13% VAT?"*
- **Clear Options:**
  - **Option A (Strict Statutory IRD Compliance):** All sales invoices mandate 13% VAT; zero VAT strictly prohibited.
  - **Option B (Dual Billing Mode):** Support both official 13% VAT Tax Invoices (`कर बीजक`) and non-VAT Delivery Challans (`चलानी / कच्चा बिल`), with separate sequence numbering.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Adopt **Option B** with clear role permissions. Footwear manufacturers in Nepal frequently move wholesale lots on delivery challans prior to final monthly VAT bill consolidation.
- **Consequences:**  
  If Option A is enforced without client agreement, operators will be blocked from recording deliveries for unregistered parties. If Option B is adopted, `InvoiceSequence` must maintain separate series for Tax Invoices and Delivery Challans.
- **Affected Artifacts:** `invoices.py`, `sales.py`, `SalesInvoiceView.tsx`, IRD tax report queries.
- **Priority:** **HIGH / DEMO BLOCKER**.
- **Implementation Status:** Unblocked for demo with 13% VAT default, but client sign-off required before live pilot data entry.

---

### BQ-02: Chart of Accounts & UI Placement for General Factory Expenses
- **Module:** Factory Expenses (`factory_expenses.py`, `AppShell.tsx`).
- **Current Behavior with Evidence:**  
  `backend/app/api/v1/factory_expenses.py` accepts expenses under generic categories (`RENT`, `ELECTRICITY`, `FUEL`, `MAINTENANCE`, `SUPPLIES`, `TEA_SNACKS`, `OTHER`). However, there is no UI component in the frontend.
- **What Remains Uncertain:**  
  Where should factory operators record daily tea/snack and maintenance costs? Does the factory maintain a formal Chart of Accounts, or is a simple category-based cash-out voucher ledger preferred?
- **Exact Question to Ask Client:**  
  *"What categories do you use to record daily factory operational expenses (such as generator diesel, machinery repairs, rent, electricity, and worker canteen/tea expenses), and who should be authorized to record them?"*
- **Clear Options:**
  - **Option A (Dedicated Sidebar View):** Add a top-level sidebar tab *"Factory Expenses (कारखाना खर्च)"* with daily voucher entry and category filters.
  - **Option B (Sub-Tab in Settings):** Embed factory expenses as an administrative tab inside the Settings modal.
  - **Option C (Unified Expense Ledger):** Merge Sales Expenses, Purchase Landed Costs, and Factory Expenses into a single master *"Expenses (खर्च हिसाब)"* module.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Adopt **Option A**. Factory floor managers need quick daily access to record diesel and maintenance costs without entering administrative settings.
- **Consequences:** Determines navigation hierarchy in `AppShell.tsx` and structure of new React component.
- **Priority:** **MEDIUM**.
- **Implementation Status:** Blocked until client selects UI placement.

---

### BQ-03: Fixed Assets Depreciation Methodology & Posting Frequency
- **Module:** Fixed Assets (`assets.py`, `models/asset.py`).
- **Current Behavior with Evidence:**  
  `backend/app/api/v1/assets.py` implements a straight-line monthly depreciation calculation endpoint (`POST /assets/{id}/depreciation`) that decrements `book_value_paisa` and increments `accumulated_depreciation_paisa`.
- **What Remains Uncertain:**  
  Does the client depreciate factory machinery (shoe sole injection molds, hydraulic cutting presses, vulcanizing ovens) monthly, or do they follow Nepal Income Tax Act Block-based declining balance depreciation once per fiscal year (Asadh)?
- **Exact Question to Ask Client:**  
  *"How do you calculate and record depreciation on your factory machinery and footwear molds? Do you calculate monthly depreciation for management reports, or annual declining-balance depreciation per Nepal Tax Blocks (Block B: 25%, Block D: 15%)?"*
- **Clear Options:**
  - **Option A (Monthly Management Straight-Line):** Auto-post monthly straight-line depreciation for managerial cost accounting.
  - **Option B (Annual Statutory Declining Balance):** Record asset acquisition costs only; compute statutory tax depreciation at the close of the Nepali fiscal year (Asadh).
  - **Option C (Asset Register Only):** Maintain asset tags, locations, and acquisition costs only, without automated depreciation journal entries.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Adopt **Option C** for the initial rollout, with Option B added for fiscal year-end reporting. Footwear factories prioritize tracking where molds and presses are located over monthly book depreciation.
- **Consequences:** Option A requires automated monthly background depreciation postings; Option C simplifies the module to an asset tracking register.
- **Priority:** **LOW**.
- **Implementation Status:** Backend already supports Option A; frontend can display simple asset ledger.

---

### BQ-04: Scrap & Waste Material Revenue Accounting
- **Module:** Waste Management (`waste.py`, `models/waste.py`).
- **Current Behavior with Evidence:**  
  `backend/app/api/v1/waste.py` accepts waste records (`quantity`, `unit`, `waste_reason`, `disposal_method`, `scrap_revenue_paisa`).
- **What Remains Uncertain:**  
  When leather trimmings, rubber flashings, or defective EVA sheets are sold to recyclers, should the realized cash reduce raw material consumption costs (COGS) or be credited to Miscellaneous Income?
- **Exact Question to Ask Client:**  
  *"When you sell scrap leather or rubber trimmings, how should the cash received be treated in reports? Should it reduce the net cost of raw materials used, or be recorded as separate miscellaneous factory income?"*
- **Clear Options:**
  - **Option A (COGS Offset):** Scrap revenue directly credits and reduces raw material expense for the associated footwear batch.
  - **Option B (Other Operating Income):** Scrap revenue posts as a credit to Miscellaneous Factory Income in the Daily Factory Report.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Adopt **Option B**. Linking scrap sales directly back to specific batch COGS is complex and prone to operator error on the factory floor.
- **Consequences:** Directly affects calculation formulas in `backend/app/api/v1/reports.py`.
- **Priority:** **LOW**.
- **Implementation Status:** Unblocked.

---

### BQ-05: Worker Standard Working Hours & Overtime Rate Policy
- **Module:** HR & Payroll (`hr.py`, `company_hr_settings`).
- **Current Behavior with Evidence:**  
  `backend/app/models/worker.py` and `company_hr_settings` default standard monthly working hours to 208 hours (26 days × 8 hours) with an overtime multiplier of 1.5× hourly wage.
- **What Remains Uncertain:**  
  Does LIVO factory operate on a 26-day or 30-day salary cycle? Is overtime paid at 1.5× (Nepal Labor Act standard), or at single-rate flat hourly wages (common in small manufacturing)?
- **Exact Question to Ask Client:**  
  *"What is the standard monthly working hour base for salaried workers (e.g., 208 hours = 26 working days), and at what rate is overtime calculated (1.5x regular wage or flat 1.0x)?"*
- **Clear Options:**
  - **Option A (Statutory Nepal Labor Act):** 208 hours/month base, 1.5× overtime multiplier.
  - **Option B (Flat Factory Custom):** Configurable per-worker standard hours with flat 1.0× overtime wage.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Adopt **Option A** as company default, but allow overriding the overtime rate multiplier in `CompanyHRSettings`.
- **Consequences:** Formulas in `_calculate_payroll_snapshot()` (`hr.py:681`) rely on these parameters.
- **Priority:** **HIGH / PAYROLL ACCURACY**.
- **Implementation Status:** CompanyHRSettings already permits configuration; client must provide exact values.

---

### BQ-06: Production Batch Color Master Synchronization
- **Module:** Production (`production.py`, `ProductionView.tsx`).
- **Current Behavior with Evidence:**  
  Floor lot custom colors are entered as free-text strings on `production_batches.color` without adding new SKUs to the `Product` table.
- **What Remains Uncertain:**  
  When an operator invents a successful new color on the floor (e.g., "Olive Green"), should the system offer a one-click action to promote that color to a formal catalog SKU?
- **Exact Question to Ask Client:**  
  *"Should custom footwear colors typed on the factory floor remain strictly tied to that specific production batch, or would you like an option to promote a new color into the master footwear catalog for future orders?"*
- **Clear Options:**
  - **Option A (Strict Separation):** Floor batch colors never affect the master SKU catalog (Current).
  - **Option B (Catalog Promotion Action):** Provide an Admin button: *"Add this color as new permanent SKU"*.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Retain **Option A** for pilot, and introduce Option B in Phase 2 if requested.
- **Priority:** **LOW**.
- **Implementation Status:** Option A currently fully implemented and verified.

---

### BQ-07: Backup Cloud Storage Target & Secret Credentials
- **Module:** Backup Service (`backup_service.py`, `.env`).
- **Current Behavior with Evidence:**  
  Backups default to local storage in `backend/backups/`. Cloud upload via `boto3` is prepared in code but remains unconfigured due to missing S3/B2 credentials.
- **What Remains Uncertain:**  
  Does the client have an existing cloud storage account (AWS S3, Backblaze B2, Cloudflare R2), or should the backup infrastructure be provisioned on a dedicated factory backup server?
- **Exact Question to Ask Client:**  
  *"Where should automated daily encrypted backups be stored offsite? Do you have an existing AWS S3 or Backblaze B2 account, or should we provision an encrypted offsite backup bucket for LIVO GROUP?"*
- **Clear Options:**
  - **Option A (Client-Provided Cloud Bucket):** Client provides S3/B2 bucket name, endpoint, and access keys.
  - **Option B (Managed Production VPS Storage):** Store daily backups on a secondary offsite VPS via SSH/rsync.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  Provision a Backblaze B2 bucket (~$0.006/GB/month) for automated daily snapshots.
- **Priority:** **HIGH / PRODUCTION BLOCKER**.
- **Implementation Status:** Blocked until storage destination is selected and credentials provisioned.

---

### BQ-08: Long-Term Hosting Model: Managed Cloud vs. Dedicated Factory VPS
- **Module:** DevOps & Deployment (`docker-compose.yml`, `Caddyfile`, Render/Vercel).
- **Current Behavior with Evidence:**  
  Demo runs on Vercel/Render free tiers with container spin-down delays (~45s sleep wakeup). Production manifests (`Caddyfile`, `docker-compose.yml`) are designed for an Ubuntu VPS.
- **What Remains Uncertain:**  
  The client expressed preference for a one-time payment rather than recurring monthly cloud bills (`PRD.md` §5). Will the client approve a $7–10/month VPS (e.g., DigitalOcean, Linode, Hetzner), or do they insist on hosting the server locally inside the factory on a dedicated PC?
- **Exact Question to Ask Client:**  
  *"Will LIVO GROUP host the ERP on a secure cloud VPS (~$7–10/month) with automated backups and 99.9% uptime, or do you intend to run the server entirely on an in-factory physical computer with local network access?"*
- **Clear Options:**
  - **Option A (Cloud VPS - Strongly Recommended):** High reliability, accessible from mobile phones and home offices, zero factory power-outage risk.
  - **Option B (Local Factory Mini-PC):** Zero recurring monthly hosting cost, but inaccessible outside factory Wi-Fi, vulnerable to power cuts, and requires local hardware maintenance.
- **Auditor Recommendation (RECOMMENDATION ONLY):**  
  **Option A (Cloud VPS).** A footwear factory in Nepal experiences frequent electrical load shedding and power fluctuations that will corrupt local database files if run without an industrial UPS.
- **Priority:** **CRITICAL / RELEASE BLOCKER**.
- **Implementation Status:** Awaiting client infrastructure approval.
