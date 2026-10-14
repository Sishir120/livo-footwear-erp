# LIVO FOOTWEAR ERP — VERCEL DEMO TEST MATRIX

**Sprint:** Vercel Demo Forensic Audit & DOM Browser Testing  
**Target URL:** `https://livo-footwear-erp.vercel.app`  
**Backend API:** `https://livo-footwear-erp-backend.onrender.com`  
**Auditor:** AntiGravity Senior Engineering Team (DOM Agent, Lead QA, DevOps, Security)  
**Date:** 2026-10-12  

---

## 1. Live Deployment Acceptance Matrix

| ID | Module / Workflow | Test Case | Target State | Observed Result | Evidence Reference | Defect ID |
| :--- | :--- | :--- | :---: | :---: | :--- | :---: |
| **AUTH-01** | Authentication | Public landing page load | Redirect to `/login` | **PASS** | HTTP 307 $\rightarrow$ `/login` renders clean in <200ms. Title: *"LIVO ERP \| Production & Stock Ledger"*. | — |
| **AUTH-02** | Authentication | Empty submission validation | Form prevents submit | **PASS** | HTML5 validation tooltip: *"Please fill out this field."* No request sent. | — |
| **AUTH-03** | Authentication | Preset login (`admin_demo`) | Populate & submit form | **PASS** | Auto-populates `admin_demo` / `LivoAdmin2026!`. `POST /api/backend/v1/auth/login` returns HTTP 200. | — |
| **AUTH-04** | Authentication | Cookie & session security | `livo_access_token` set | **PASS** | `Set-Cookie: livo_access_token=...; HttpOnly; SameSite=lax; Secure; Max-Age=86400`. | — |
| **AUTH-05** | Authentication | Session validation (`/auth/me`)| Verify user context | **PASS** | `GET /api/backend/v1/auth/me` returns `{"user": {"id": 7, "role": "admin", "company_id": 1}}`. | — |
| **AUTH-06** | Authentication | Logout workflow | Terminate session | **PASS** | Click Log Out button; session cleared; cleanly redirects back to `/login`. | — |
| **API-01** | Network Architecture | Vercel rewrite to Render backend | Proxy transparently | **PASS** | `GET /api/backend/v1/health` returns HTTP 200 `{"status": "healthy", "database": "healthy"}`. | — |
| **DASH-01** | Executive Dashboard | Render metrics & charts | Floor velocity & cash ratio | **PASS** | Charts render with live SVG/Canvas: Factory Floor Velocity, Cash Realization, Line Efficiency. | — |
| **STOCK-01** | Finished Goods Stock | Stock ledger summary | Total pairs & SKU matrix | **PASS** | Displays 11 SKUs, 2,059 pairs inventory, Rs. 4,717,700 valuation, Finished Footwear Sizing Matrix. | — |
| **SALES-01** | Sales & Invoicing | Wholesale orders & invoices | Invoices & order records | **PASS** | Renders 30 statutory VAT tax invoices, 25 wholesale sales orders, IRD compliance details. | — |
| **PROD-01** | Production Batches | Manufacturing batch runs | Batch list & progress | **PASS** | Renders 28 batch records with size curves, target pairs, produced pairs, and worker allocation. | — |
| **PUR-01** | Procurement | Raw material inward records | Vendor inward ledger | **PASS** | Renders 29 inward vendor purchase orders with FIFO stock entries and unit costs. | — |
| **AR-01** | Receivables (AR) | Customer aging matrix | Aging subledger buckets | **PASS** | Customer credit ledger, current vs 30/60/90-day aging brackets render correctly. | — |
| **HR-01** | HR & Workers | Factory worker profiles | Workers table & wage rates | **PASS** | Worker profile table displays name, role, wage rate, advance balance, and overtime entries. | — |
| **HR-02** | HR & Workers | Phase 4B citizenship / settings | View/Upload documents | **BLOCKED** | Phase 4B endpoints (`/hr/settings`, `/hr/workers/{id}/citizenship`) return 404 on deployed cloud backend (uncommitted in git). | **DEF-03** |
| **GAL-01** | Product Gallery | Footwear catalog media | Visual product cards | **PASS** | Product gallery items, models, colorways, and catalog media cards render properly. | — |
| **GAL-02** | Product Gallery | Upload product select dropdown | Dropdown SKU options | **FAIL $\rightarrow$ PASS** | Observed `TypeError: map is not a function` on deployed JS bundle due to `/stock/ledger` format; fixed in local code. | **DEF-01** |
| **ANALYTICS-01**| Analytics & Ranks | Sales & production ranks | Leaderboards & metrics | **PASS** | Customer volume ranks, model production ratios, and operator leaderboards render accurately. | — |
| **SETTINGS-01** | System Settings | Company profile & backups | Backup status & sizing | **PASS** | Renders company details (PAN 600123456), sizing scale, VAT rate (13%), and backup configuration. | — |
| **I18N-01** | Localization | Bilingual toggle (EN / नेपाली) | In-place vernacular change | **PASS** | Header buttons toggle instantly between English and Nepali across all sidebar tabs, tables, and metrics. | — |
| **PWA-01** | Progressive Web App | Manifest & mobile responsive | Responsive drawer navigation | **PASS** | Manifest loaded (`/manifest.json`); responsive `.sidebar` and `.modal-drawer` operational. | — |

---

## 2. Testing Summary

- **Total Test Cases:** 21
- **Passed:** 19 (90.5%)
- **Failed (Remediated Locally):** 1 (4.8% — `GAL-02` / `DEF-01`)
- **Blocked / Not Deployed:** 1 (4.8% — `HR-02` / `DEF-03`)
- **Browser Execution Evidence:**
  - Recording: `vercel_login_recon_1791807778718.webp` (4.2 MB)
  - Recording: `vercel_workflows_audit_1791808000000.webp` (4.9 MB)
  - Screenshots: `stock_ledger_loaded_1791807855526.png`, `sales_invoicing_loaded_1791807866602.png`, `production_batches_loaded_1791807877441.png`, `raw_material_purchases_loaded_1791807889493.png`.
