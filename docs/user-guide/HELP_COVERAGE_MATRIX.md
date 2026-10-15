# LIVO FOOTWEAR ERP — CONTEXTUAL HELP & BILINGUAL COVERAGE MATRIX
## Complete English / Nepali Guidance Architecture for Footwear Manufacturing

**Project:** LIVO Footwear ERP  
**Document:** Contextual Help & Bilingual Coverage Specification  
**Status:** Approved for Implementation (Phase 2 & 8)  
**Author:** Coordinated UX & Technical Writing Team  

---

## 1. Help Architecture Overview

The LIVO Footwear ERP serves factory supervisors, storekeepers, wholesale salesmen, accountants, and company administrators across Nepal.
Many floor workers are novice ERP users who require clear, non-jargon guidance in their native language (**नेपाली** and **English**).

### Core Principles
1. **Never Document Fictional UI:** Help articles document strictly active buttons, inputs, and business rules.
2. **Contextual & Non-Destructive:** Clicking `? Help` opens a sliding drawer or modal that preserves user form inputs without reload or navigation loss.
3. **Dual Language Toggle:** Every article and help tooltip is available in English and authentic Nepali (bilingual toggle in-app).
4. **Footwear-Specific Examples:** All examples use real footwear terms (e.g., Article 801, Upper Leather, EVA Sheet Outsole, Cutting Line 1, Size 41, Cognac Brown, Nepali Bikram Sambat dates).

---

## 2. Complete Module & Workflow Coverage Inventory

Every screen, tab, form, and dialog in the ERP is mapped to a required help article:

| Module / Screen | Sub-Tab / Dialog | Operation / Workflow | Article ID | Target Audience | Consequential Impact |
|---|---|---|---|---|---|
| **Authentication** | Login Screen | Login & Password Recovery | `AUTH-01` | All Users | Failed lockouts after 5 attempts |
| **Dashboard** | Daily Operations | Reading Daily Production, Sales & Cash Flow | `DASH-01` | Supervisor / Admin | High-level operational awareness |
| **Stock Ledger** | Physical Balances | Viewing Stock by Article, Size & Warehouse | `STK-01` | Storekeeper / Sales | Real-time available pairs |
| **Stock Ledger** | Movement Ledger | Audit Trail of Inward/Outward Movements | `STK-02` | Storekeeper / Auditor | Traceability of all movements |
| **Stock Ledger** | Stock Adjustment Modal | Physical Count Discrepancy & Delta Correction | `STK-03` | Admin / Supervisor | Adjusts physical stock balance |
| **Stock Ledger** | Warehouse Switcher | Multi-Store & Branch Inventory Views | `STK-04` | Storekeeper / Branch Mgr | Multi-store inventory visibility |
| **Sales & Invoicing** | Order Entry Modal | Creating Wholesale Sales Order | `SALES-01` | Sales Staff / Editor | Client credit limit validation |
| **Sales & Invoicing** | Deferred Dispatch Modal | Warehouse Physical Handover to Carrier | `SALES-02` | Dispatch Clerk | **Deducts Physical Warehouse Stock** |
| **Sales & Invoicing** | Statutory Tax Invoice | Generating Gapless Sequential 13% VAT Bill | `SALES-03` | Accountant / Billing | Irreversible sequential tax invoice |
| **Sales & Invoicing** | Sales Expenses Subledger | Recording Delivery Freight & Packing Costs | `SALES-04` | Sales Staff / Billing | Deducts from net sales realization |
| **AR Aging** | Client Aging Table | Tracking Overdue Receivables (0-30, 31-60, 90+) | `AR-01` | Accountant / Admin | Client credit risk management |
| **Production** | Batch Entry Modal | Recording Assembly Run, Line & Typable Color | `PROD-01` | Production Supervisor | **Increments Finished Goods Stock** |
| **Production** | BOM Issuance Drawer | Automatic Deduction of Leather/Soles | `PROD-02` | Supervisor / Storekeeper | **Deducts Raw Material Stock** |
| **Production** | Daily Shift Hours | Logging Shift Hours, Output Pairs & Ratios | `PROD-03` | Production Supervisor | Worker productivity metrics |
| **Purchasing** | PO Creation Modal | Placing Material Order to Supplier | `PURCH-01` | Purchasing Manager | Records order commitment (no stock add) |
| **Purchasing** | Goods Receipt Drawer | Receiving Material & Allocating GRN Voucher | `PURCH-02` | Receiving Clerk | **Increments Raw Material Stock** |
| **Purchasing** | Landed Costs Ledger | 4-Column Carrying, Duty, China Exp, Insurance | `PURCH-03` | Accountant / Purchasing | **Capitalizes Raw Material Unit Cost** |
| **Purchasing** | Raw Material Ledger | Append-Only Material Stock Card & Adjustments | `PURCH-04` | Storekeeper | Material stock balance reconciliation |
| **HR & Payroll** | Worker Master Form | Adding Worker, Photos, Temp/Perm Addresses | `HR-01` | HR Manager / Admin | Worker identity records |
| **HR & Payroll** | Citizenship Vault | Confidential Admin-Only Citizenship Document | `HR-02` | Admin Only | Sensitive PII storage & RBAC |
| **HR & Payroll** | Active/Inactive Modal | Soft Deactivation Recording Date & Reason | `HR-03` | HR Manager | Preserves historical payroll |
| **HR & Payroll** | Advance Modal | Issuing Salary Advance & Tracking Due Balance | `HR-04` | Cashier / HR Manager | Cash disbursement |
| **HR & Payroll** | Monthly Payroll Drawer | Logging Hours, OT, & FIFO Advance Recovery | `HR-05` | Accountant / HR Manager | **Disburses Net Salary via Cash/Bank** |
| **Product Gallery** | Media Upload Modal | Associating High-Res Photos with Batch & SKU | `GAL-01` | Marketing / Production | Visual catalog card generation |
| **Fixed Assets** | Asset Register Form | Logging Machinery, Molds, Lasts, Computers | `ASSET-01` | Accountant / Admin | Capital equipment asset register |
| **Waste & Scrap** | Scrap Entry Modal | Logging Cutting Scraps & Defective Shoes | `WASTE-01` | Quality Supervisor | Factory floor scrap audit log |
| **Factory Expenses** | Operating Expense Form | Logging Factory Rent, Power, Fuel, Supplies | `EXP-01` | Accountant / Admin | Operating overhead cost ledger |
| **Transfers (New)** | Transfer Request Modal | Initiating Inter-Store / Branch Stock Transfer | `TRF-01` | Storekeeper | Reserves stock for transfer |
| **Transfers (New)** | Dispatch Confirmation | Dispatching Goods to Carrier (En Route) | `TRF-02` | Dispatch Clerk | **Deducts Source, Adds to In-Transit** |
| **Transfers (New)** | Branch Receipt Modal | Destination Physical Verification & Acceptance | `TRF-03` | Branch Manager | **Deducts Transit, Adds to Branch** |
| **Traceability (New)**| Traceability Explorer | Tracing Batch from Leather Purchase to Sale | `TRACE-01`| Auditor / Admin / Manager | Complete audit history lookup |
| **Date Converter** | Dual AD/BS Converter | Bikram Sambat 1979–2100 Calendar Converter | `DATE-01` | All Users | Date validation & conversion |
| **Settings** | Backup & Diagnostics | Manual Backup Trigger & Integrity Status | `SYS-01` | Admin Only | Disaster recovery & snapshots |

---

## 3. Bilingual Terminology Dictionary (Footwear Domain)

Standardized vernacular terminology ensuring consistency between UI labels, database definitions, and help manuals:

| English Footwear Term | Nepali Standard Vernacular (नेपाली) | Domain Context |
|---|---|---|
| **Article / Footwear Model** | **आर्टिकल / जुत्ता मोडल** | The master footwear design code (e.g. ART-801). |
| **Size** | **साइज** | Footwear size (39, 40, 41, 42, 43, 44). |
| **Color** | **रंग** | Upper leather or sole color (Black, Brown, Red, Navy). |
| **Production Batch** | **उत्पादन ब्याच** | A specific manufacturing run produced on a shift. |
| **Raw Material** | **कच्चा पदार्थ** | Upper leather, lining rexine, rubber soles, adhesive, boxes. |
| **Leather (Upper)** | **छाला (अप्पर लेदर)** | Primary material measured in sq. ft. or kg. |
| **Outsole / Sole** | **सोल (तलुवा)** | Preformed rubber, PU, or TPR soles measured in pairs (pcs). |
| **Adhesive / Chemical Glue** | **गोंद / केमिकल ग्लु** | Bonding adhesives measured in litres. |
| **Goods Receipt Note (GRN)** | **दाखिला भौचर (GRN)** | Official voucher recording receipt of raw materials. |
| **Landed Cost** | **आयातित ढुवानी तथा भन्सार खर्च** | Carrying-in, import duty, China freight, insurance. |
| **Bill of Materials (BOM)** | **उत्पादन सामग्री अनुपात (BOM)** | Standard raw material recipe required per pair of shoes. |
| **Stock Ledger** | **मौज्दात खाता / स्टक लेजर** | Double-entry append-only record of footwear inventory. |
| **In-Transit Stock** | **मार्गमा रहेको मौज्दात (ट्रान्जिट)** | Goods dispatched by factory but not yet received by branch. |
| **Destination Receipt** | **गन्तव्य प्राप्ति पुष्टि** | Branch confirmation of physical pairs actually delivered. |
| **Discrepancy / Shortage** | **फरक / सामान नपुग (कमी)** | Variance between dispatched quantity and received quantity. |
| **Sales Dispatch** | **बिक्री चलानी / माल निकासी** | Warehouse release and dispatch of footwear to wholesale client. |
| **Tax Invoice (VAT)** | **कर विजक (मूल्य अभिवृद्धि कर १३%)** | Legal sequential invoice issued under Nepal IRD regulations. |
| **Advance (Salary)** | **पेश्की रकम** | Money given to worker ahead of monthly payroll. |
| **Overtime (OT)** | **अतिरिक्त समय (ओभरटाइम)** | Work hours exceeding the standard daily shift (1.5x rate). |
| **Citizenship Certificate** | **नागरिकता प्रमाण-पत्र** | Confidential identity document for factory workers. |
| **Fixed Assets** | **स्थिर सम्पत्ति** | Factory machinery, sole molding presses, sewing machines. |
| **Waste / Scrap Material** | **खेर गएको कच्चा पदार्थ / स्क्र्याप** | Offcut leather trimmings, rejected pairs, scrap sole rubber. |

---

## 4. Contextual Help Framework Specification

### 4.1 UI Component Architecture
1. **Global Help Anchor:**
   - Every view header contains an accessible `? Help (सहयोग)` button in the top right.
2. **Contextual Drawer (`<HelpDrawer />`):**
   - Slides smoothly from the right side of the screen (`width: 480px`).
   - Contains:
     - Search input with instant keyword filtering.
     - English / Nepali language switcher toggle (`[ EN | NE ]`).
     - Structured article sections:
       - **उद्देश्य (Purpose):** What this screen accomplishes.
       - **आवश्यक भूमिका (Required Role):** Admin, Editor, or Viewer.
       - **चरणबद्ध निर्देशन (Step-by-Step Instructions):** Numbered procedure.
       - **फिल्डहरूको विवरण (Field Explanations):** Explaining each input.
       - **व्यावहारिक उदाहरण (Footwear Example):** Concrete sample data.
       - **महत्वपूर्ण चेतावनी (Critical Warnings):** Financial or inventory implications.
3. **Field-Level Help Icons (`<FieldHelp />`):**
   - Small `(?)` icon beside consequential fields (e.g., Landed Costs, Dispatched Date, Advance Deduction).
   - Hover / click popover explaining the exact calculation formula.

---

## 5. Practical Guides Roadmap (16 Verified Workflows)

The complete user manual will be compiled and verified under:
- `docs/user-guide/ENGLISH/`
- `docs/user-guide/NEPALI/`

### The 16 Mandatory Practical Manuals
1. **Guide 01:** Creating Footwear Articles, Sizes & Catalog Variants (`GUIDE_01_PRODUCT_CATALOG.md`)
2. **Guide 02:** Raw Material Purchase Orders & Goods Receipt (GRN) (`GUIDE_02_PROCUREMENT_GRN.md`)
3. **Guide 03:** Assigning Received Stock to Storage Racks & Bins (`GUIDE_03_LOCATION_STORAGE.md`)
4. **Guide 04:** Issuing Raw Materials to Production via BOM (`GUIDE_04_BOM_MATERIAL_ISSUE.md`)
5. **Guide 05:** Recording Production Batches & Finished Footwear Output (`GUIDE_05_PRODUCTION_BATCHES.md`)
6. **Guide 06:** Moving Finished Shoes into Central Factory Store (`GUIDE_06_FINISHED_GOODS_STORAGE.md`)
7. **Guide 07:** Dispatching Stock Transfers to Branch Stores (`GUIDE_07_BRANCH_TRANSFER_DISPATCH.md`)
8. **Guide 08:** Independent Branch Receiving Confirmation (`GUIDE_08_BRANCH_RECEIPT_CONFIRMATION.md`)
9. **Guide 09:** Handling Transfer Shortages, Damage & Discrepancies (`GUIDE_09_TRANSFER_DISCREPANCIES.md`)
10. **Guide 10:** Conducting Physical Stock Counts & Authorized Adjustments (`GUIDE_10_STOCK_ADJUSTMENTS.md`)
11. **Guide 11:** Wholesale Sales Invoicing & Warehouse Dispatch (`GUIDE_11_SALES_DISPATCH_INVOICING.md`)
12. **Guide 12:** Managing Customer Returns, Damaged Pairs & Waste (`GUIDE_12_RETURNS_AND_WASTE.md`)
13. **Guide 13:** Analyzing Stock Movements & Financial Receivables (`GUIDE_13_REPORTS_AND_AGING.md`)
14. **Guide 14:** Worker Profiles, Advances & Monthly Payroll Ledger (`GUIDE_14_HR_ADVANCE_PAYROLL.md`)
15. **Guide 15:** User Administration, Roles & Security Permissions (`GUIDE_15_USER_ADMIN_RBAC.md`)
16. **Guide 16:** Using the Dual Bikram Sambat (AD/BS) Calendar Converter (`GUIDE_16_NEPALI_DATE_CONVERTER.md`)
