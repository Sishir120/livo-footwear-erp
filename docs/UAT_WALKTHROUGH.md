# LIVO GROUP OF INDUSTRIES — Footwear ERP
## User Acceptance Testing (UAT) Walkthrough Guide
**Document Version:** 1.0 (Phase 5 Baseline)  
**Target Audience:** Factory General Manager, Production Supervisors, Accounts & Invoicing Clerks  
**System URL:** [https://livo-footwear-erp.vercel.app](https://livo-footwear-erp.vercel.app)  
**API Health Status:** [https://livo-footwear-erp-backend.onrender.com/api/v1/health](https://livo-footwear-erp-backend.onrender.com/api/v1/health)

---

### Overview & Access Credentials

The LIVO Footwear ERP is built specifically for high-throughput shoe manufacturing and wholesale distribution. Access is role-guarded to ensure strict ledger integrity:

| Role Type | Username | Password | Operational Capabilities |
| :--- | :--- | :--- | :--- |
| **Editor / Administrator** | `editor_admin` | `LivoEditor2026!` | Full operational access: Procurement, batch issuance, sales bookings, invoice generation, voiding, and manual backups. |
| **Viewer / Auditor** | `viewer_user` | `LivoViewer2026!` | Read-only access: Executive daily summaries, size-curve distribution charts, stock ledgers, tax invoice viewing/printing, and Excel exports. All mutation buttons (<kbd>Alt+N</kbd>, New Batch, Void) are hidden. |

---

### Quick Navigation & Hands-Free Shortcuts

For rapid data entry clerks handling factory receipts and gate vouchers, the interface supports continuous mouse-free data entry:

* <kbd>Alt+N</kbd> — Open the data entry drawer on any active ledger tab.
* <kbd>Enter</kbd> — Advance cursor automatically to the next input field.
* <kbd>Ctrl+Enter</kbd> or <kbd>⌘+Enter</kbd> — Commit record immediately to the ledger from any field.
* <kbd>Esc</kbd> — Dismiss drawer/modal.
* **Continuous Rapid Entry Mode** — Keeps the entry drawer open after commit, auto-advances the serial number, and returns focus to the item selector for unbroken keyboard data entry.

---

### Scenario 1: Raw Material Procurement & Gate Inward

**Objective:** Log incoming raw materials (Synthetic PU Leather and Rubber Outsoles) received at the factory gate, attach digital bills, and verify supplier accounts.

1. **Sign In:** Navigate to [https://livo-footwear-erp.vercel.app](https://livo-footwear-erp.vercel.app) and sign in as `editor_admin`.
2. **Access Inward Tab:** Click the **Purchases** tab on the navigation bar.
3. **Launch Inward Drawer:** Press <kbd>Alt+N</kbd> (or click **+ Record Raw Material Purchase**).
4. **Enter Bill Details:**
   - **Supplier / Vendor:** Select `Reliance Leather Works (SUP-001)`.
   - **Raw Material Item:** Select `Black Synthetic PU Leather (meter)`.
   - **Quantity:** Enter `150.0`.
   - **Wholesale Unit Rate:** Enter `420.00`.
   - **Date (AD / BS):** Auto-fills today's date (e.g., `2026-09-27` AD / `2083-06-11` BS).
   - **Gate Pass / Bill Reference:** Enter `GP-8842 / BL-1092`.
   - **Physical Bill Attachment:** Click the upload zone to attach a photo or PDF voucher (mock simulated storage).
5. **Commit Record:** Press <kbd>Ctrl+Enter</kbd>.
6. **Verification Checklist:**
   - [ ] A green confirmation banner indicates the record is written to the append-only ledger.
   - [ ] The Purchases table displays the newly inwarded lot with monospace monetary formatting (`Rs. 63,000`).
   - [ ] Clicking the paperclip icon opens the secure bill preview modal.

---

### Scenario 2: Factory Production Run & Size-Assortment Curve

**Objective:** Issue a production batch for Men's Derby Formal Shoes across Paris Point sizes 38–43, automatically incrementing finished goods inventory.

1. **Access Production Tab:** Click the **Production** tab.
2. **Review Inventory Health Badges:** Inspect the tri-state health pills (`HEALTHY > 50`, `LOW ≤ 50`, `OUT OF STOCK ≤ 0`).
3. **Open Batch Drawer:** Press <kbd>Alt+N</kbd> (or click **+ Issue Production Batch**).
4. **Fill Batch Run Parameters:**
   - **Batch Serial Number:** Notice the suggested sequence (e.g., `BATCH-2026-027`).
   - **Footwear Model:** Select `Classic Oxford Derby - Black (PP-42)`.
   - **Target Output Pairs:** Enter `100`.
   - **Finished Pairs Produced:** Enter `100`.
   - **Active Assembly Workers:** Enter `8`.
   - **Raw Material Deduction:** Select `Black Synthetic PU Leather` and specify `80 meters` utilized.
5. **Commit Batch:** Press <kbd>Ctrl+Enter</kbd>.
6. **Verification Checklist:**
   - [ ] The batch appears immediately at the top of the **Production Batches** table.
   - [ ] Navigate to the **Stock Ledger** tab: locate `Classic Oxford Derby - Black (PP-42)` and verify that the stock balance reflects `+100` finished pairs.
   - [ ] Verify the **Footwear Size Curve Distribution** bar chart updates dynamically, illustrating balanced Paris Point assortments without broken sizing.

---

### Scenario 3: Wholesale Order Booking & Sequential Tax Invoicing

**Objective:** Book a wholesale order for a distributor, issue a Nepal VAT-compliant sequential invoice (`INV-01-00030`), inspect the printable tax format, and verify the statutory void mechanism.

1. **Access Sales Tab:** Click the **Sales & Invoicing** tab.
2. **Open Order Drawer:** Press <kbd>Alt+N</kbd> (or click **+ Record Sale & Issue Invoice**).
3. **Configure Wholesale Dispatch:**
   - **Client / Buyer:** Select `Kathmandu Footwear Emporium (CLI-001)`.
   - **Order Reference:** `ORD-2026-025`.
   - **Order Date (AD / BS):** Today's date.
   - **Line Items:** Select `Classic Oxford Derby - Black (PP-42)`, Quantity: `40 pairs`, Unit Wholesale Rate: `Rs. 2,400`.
   - **Cash Payment Received:** Enter `Rs. 50,000` (balance `Rs. 46,000` logged as accounts receivable).
4. **Issue Invoice:** Click **Commit Sale & Generate Invoice**.
5. **Inspect Immutable Sequential Invoice:**
   - Switch to the **Invoices** sub-tab.
   - Verify that the new invoice displays the strict non-resettable sequence `INV-01-00030`.
   - Verify the Nepal statutory 13% VAT calculation row:
     - Subtotal: `Rs. 96,000.00`
     - Statutory VAT (13%): `Rs. 12,480.00`
     - Total Gross Invoice Amount: `Rs. 108,480.00`
6. **Print Preview Verification:**
   - Click the **Tax Invoice** button.
   - A clean printable invoice opens in a new tab formatted with Factory Name, PAN number, size details, rate breakdown, and authorized signature lines.
7. **Nepal VAT Statutory Void Verification:**
   - As `editor_admin`, click the red **Void** button on invoice `INV-01-00030`.
   - Confirm the prompt.
   - Observe that the record displays a red `VOID` pill with a line-through on the invoice number. The invoice number is **never deleted**, preserving the sequential audit trail required by Nepal Inland Revenue Department (IRD) regulations.

---

### Scenario 4: Executive Overview & Spreadsheet Portability

**Objective:** Review the manager's Daily Operational Summary, verify role segregation, and export data to Microsoft Excel with proper UTF-8 BOM encoding.

1. **Access Daily Report:** Click the **Daily Report** tab.
2. **Review High-Level Factory KPI Tiles:**
   - Daily Finished Pairs Produced.
   - Total Active Assembly Workers.
   - Gross Wholesale Bookings (NPR).
   - Cash Received vs Accounts Receivable outstanding.
3. **Verify Interactive Analytics:** Hover over the Recharts **Dispatched vs Produced** comparison bars to view detailed volumetric tooltips.
4. **1-Click Spreadsheet Export:**
   - Navigate to the **Stock Ledger** tab.
   - Click the **Download Excel / CSV** button.
   - Open the downloaded file in Microsoft Excel or LibreOffice Calc.
   - Confirm all column headers (SKU Code, Paris Points, Health Status, Physical Pairs) display cleanly without character corruption.
5. **Role-Based Access Control (RBAC) Smoke Check:**
   - Click **Logout** in the user card.
   - Sign in as `viewer_user` (`LivoViewer2026!`).
   - Notice the top header indicates `VIEWER ROLE`.
   - Navigate to **Production**, **Purchases**, and **Sales Invoices**:
     - The **+ Record** buttons are hidden.
     - Pressing <kbd>Alt+N</kbd> does not open the drawer.
     - The **Void** button on invoices is completely absent.
     - All reports, stock curves, print layouts, and CSV exports remain accessible.

---

### UAT Sign-Off Record

| Reviewer Name | Role / Department | Status | Date | Notes / Feedback |
| :--- | :--- | :--- | :--- | :--- |
| **Factory Manager** | Operations & Logistics | [ ] Approved | 2026-09-27 | |
| **Head Accountant** | Finance & Taxation | [ ] Approved | 2026-09-27 | |
| **Data Entry Clerk** | Inward Gate & Dispatch | [ ] Approved | 2026-09-27 | |
