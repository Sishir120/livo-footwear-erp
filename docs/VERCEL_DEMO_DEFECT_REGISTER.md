# LIVO FOOTWEAR ERP — VERCEL DEMO DEFECT REGISTER

**Sprint:** Vercel Demo Forensic Audit & Targeted Remediation  
**Target Deployment:** `https://livo-footwear-erp.vercel.app`  
**Backend Origin:** `https://livo-footwear-erp-backend.onrender.com`  
**Baseline Commit:** `5caa3f471e92aece268d0fa519a920e7cc7dc512`  

---

### Defect Register Summary

| Defect ID | Severity | Category | Status | Component | Description |
| :--- | :---: | :--- | :---: | :--- | :--- |
| **DEF-01** | **P2** | `FRONTEND_RUNTIME` / `UI_STATE` | **FIXED** | `frontend/src/components/ProductGalleryView.tsx` | Uncaught `TypeError: (t.ledger \|\| t \|\| []).map is not a function` when opening Gallery product selection. |
| **DEF-02** | **P2** | `DEPLOYMENT_CONFIGURATION` | **FIXED** | `frontend/next.config.js` | Production rewrite defaulted `apiBase` to loopback `http://127.0.0.1:8000` when env vars were missing. |
| **DEF-03** | **P1** | `DEPLOYMENT_CONFIGURATION` / `DESYNC` | **DOCUMENTED / BLOCKED** | Vercel & Render Cloud Hosting | Deployed cloud demo runs commit `aab3d4a` (Sept 29); Phase 4B & 4B.4 features reside uncommitted locally. |
| **DEF-04** | **P3** | `EXTERNAL_DEPENDENCY` | **MITIGATED / RUNBOOK** | Cloud Backend (Render Free Tier) | Backend container spins down after 15m inactivity, requiring 45–50s spin-up delay on initial client connection. |

---

## Detailed Defect Records

### DEF-01: Product Gallery Upload Dropdown Runtime Exception
- **Defect ID:** `DEF-01`
- **Severity:** P2 (High Functional Defect in Product Gallery)
- **Category:** `FRONTEND_RUNTIME` / `DATA_VALIDATION`
- **Status:** **REMEDIATED & VERIFIED LOCALLY**
- **Affected File:** `frontend/src/components/ProductGalleryView.tsx` (lines 109–127)
- **Browser Reproduction Steps:**
  1. Log into ERP demo at `https://livo-footwear-erp.vercel.app`.
  2. Navigate to **Product Gallery** tab.
  3. Inspect browser console or click upload modal.
  4. Notice error in console: `TypeError: (t.ledger || t || []).map is not a function`.
- **Expected Behavior:**
  The product dropdown loads valid SKU/model options without throwing unhandled exceptions.
- **Actual Behavior:**
  The component called `fetch("/api/v1/stock/ledger")`. The backend `/stock/ledger` endpoint returns a paginated dictionary `{ total: number, items: StockLedgerItem[], limit: number, offset: number }`. The frontend code attempted `(data.ledger || data || []).map(...)`. Because `data.ledger` is `undefined` and `data` is a truthy object (not an array), calling `.map()` threw a runtime `TypeError`, leaving the product selector unpopulated.
- **Root Cause:**
  Endpoint mismatch and unsafe array assumption: `/stock/ledger` returns `{ total, items }`, not a bare list or `{ ledger: [...] }`. Additionally, product options should be retrieved from `/api/v1/production/products` which directly provides the tenant product catalog.
- **Remediation Implemented:**
  1. Updated `fetchProducts` in `ProductGalleryView.tsx` to target `/api/v1/production/products`.
  2. Added defensive array resolution: `const rawList: any[] = Array.isArray(data) ? data : (data.items || data.ledger || []);`.
  3. Mapped `rawList` safely into `ProductOption[]`.
- **Regression Testing:**
  `npm run build` passed with zero TypeScript and linting errors.

---

### DEF-02: Next.js Production Proxy Fallback to Loopback Address
- **Defect ID:** `DEF-02`
- **Severity:** P2 (Deployment Architecture Risk)
- **Category:** `DEPLOYMENT_CONFIGURATION` / `API_BASE_URL`
- **Status:** **REMEDIATED & VERIFIED LOCALLY**
- **Affected File:** `frontend/next.config.js` (line 1)
- **Reproduction & Mechanism:**
  `const apiBase = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://127.0.0.1:8000';`
  If Vercel build environment variables do not include `NEXT_PUBLIC_API_URL` or `API_URL`, Next.js rewrites compiled during `next build` route `/api/backend/:path*` and `/api/:path*` to `http://127.0.0.1:8000`. On Vercel edge/serverless functions, `127.0.0.1:8000` is unreachable, yielding HTTP 500 / 504 proxy errors.
- **Root Cause:**
  Hardcoded default fallback was assumed for local development without checking `process.env.NODE_ENV === 'production'`.
- **Remediation Implemented:**
  Updated `next.config.js` to intelligently fall back to the live Render backend URL when running in production:
  ```js
  const apiBase =
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.API_URL ||
    (process.env.NODE_ENV === 'production'
      ? 'https://livo-footwear-erp-backend.onrender.com'
      : 'http://127.0.0.1:8000');
  ```
- **Regression Testing:**
  Verified build artifact generation and edge rewrite routes in Next.js 14.2.35.

---

### DEF-03: Deployed Cloud Infrastructure Desynchronization
- **Defect ID:** `DEF-03`
- **Severity:** P1 (Demo Scope Discrepancy)
- **Category:** `DEPLOYMENT_CONFIGURATION` / `DESYNC`
- **Status:** **DOCUMENTED / BLOCKED (Deployment authorization required)**
- **Affected Systems:** Vercel Global Edge & Render Cloud Service
- **Reproduction Steps:**
  1. Inspect OpenAPI specification on deployed backend:
     `curl https://livo-footwear-erp-backend.onrender.com/api/v1/openapi.json`
  2. Inspect endpoints: 50 endpoints present.
  3. Inspect local OpenAPI specification: 90 endpoints present.
  4. Request Phase 4B endpoint on deployed backend:
     `curl https://livo-footwear-erp-backend.onrender.com/api/v1/hr/settings` $\rightarrow$ **HTTP 404 Not Found**.
     `curl https://livo-footwear-erp-backend.onrender.com/api/v1/purchases/1/receive` $\rightarrow$ **HTTP 404 Not Found**.
- **Root Cause:**
  Vercel and Render are connected via continuous deployment to GitHub repository `Sishir120/livo-footwear-erp` on branch `main` at commit `aab3d4a` (Sept 29). All newly developed Phase 4A and Phase 4B features (worker photo upload, confidential citizenship documents, worker deactivation lifecycle, advance installment recovery, landed cost ledger, duplicate purchase receipt locking) reside strictly as uncommitted local files in the active workspace.
- **Consequence for Client Demo:**
  The live Vercel demo works for all pre-existing Phase 1–3 and early Phase 4 features (Dashboard, Stock Ledger, Sales Orders, Tax Invoicing, Production Batches, Vendor Purchases, Worker Directory, Wage Records, AR Aging, Product Gallery, Analytics, Settings). However, newly added Phase 4B features (citizenship cards, photo uploads, deactivation guards) cannot be demonstrated on Vercel until a git commit and push are authorized.
- **Recommended Remediation:**
  Maintain clear demo boundaries: Present Phase 1–4 core features on Vercel; if Phase 4B worker identity/citizenship and advance installment engine are required by the client, demonstrate them via the containerized local environment (`docker compose up`) or authorize a staged release to GitHub `main`.

---

### DEF-04: Render Free-Tier Backend Container Sleep & Latency
- **Defect ID:** `DEF-04`
- **Severity:** P3 (User Experience / Operational Latency)
- **Category:** `EXTERNAL_DEPENDENCY`
- **Status:** **MITIGATED IN UI / RUNBOOK DOCUMENTED**
- **Affected Systems:** `https://livo-footwear-erp-backend.onrender.com`
- **Observation:**
  When no HTTP requests have been processed for 15 minutes, Render spins down the free-tier backend container. The first inbound request takes approximately 45–50 seconds to complete while the container boots, runs Alembic migrations, and seeds initial records.
- **Existing Mitigation:**
  The login page displays an explicit banner: *"Cloud backend operates on standard container scaling. If sleeping after inactivity, initial connection takes ~45s."* Furthermore, `frontend/src/app/page.tsx` issues a background pre-warm ping to `/health`.
- **Operational Recommendation for Demo:**
  Prior to demonstrating the system to the client, the demonstrator must open `https://livo-footwear-erp.vercel.app/api/backend/v1/health` in a browser tab 60 seconds beforehand to ensure warm container status.
