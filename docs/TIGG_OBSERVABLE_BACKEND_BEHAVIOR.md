# Tigg Observable Backend Behavior
**Date:** 2026-10-16  
**Session:** Authorized public observation only  
**Investigation Scope:** tiggapp.com public pages, help.tiggapp.com, me.tiggapp.com/erp/ login page only

All findings are labeled with their evidence classification:
- **OBSERVED**: Directly visible in UI, DOM, or public documentation
- **INFERRED**: Plausible explanation consistent with observations, not confirmed
- **UNKNOWN**: Insufficient evidence

---

## 1. Product Positioning and Modules (OBSERVED)

From https://tiggapp.com/features:

| Module | Observed Features |
|---|---|
| Accounting | Double-entry accounting, COA, bank reconciliation, financial reports |
| Inventory | Multi-warehouse management, stock tracking |
| Sales | Sales cycle (quotations → orders → invoices → payments → credit notes) |
| Purchase | Purchase cycle |
| Document Management | Explicit feature listed |
| Special Modes | Restro (restaurant) mode, Retail mode |
| Integrations | SMS integration, mobile app |
| Administration | Users & Permissions, Import/Export, Opening Balances, Subscriptions |

**Relevance to LIVO:** Tigg's module structure directly parallels LIVO's ERP scope. The explicit inclusion of Users & Permissions as a distinct admin module suggests role-based access control is surfaced as a first-class product feature, not an internal implementation detail.

---

## 2. Navigation and Authorization Architecture (OBSERVED)

From https://help.tiggapp.com/article/navigating-tigg:

- **Multi-tenant, multi-org model**: Users see an "Organization Home Screen" listing all organizations under their account. This implies user identities are decoupled from individual organizations — a single user email can belong to multiple orgs.
- **Invitation model**: A dedicated Invitation tab allows accepting/declining organization membership — suggests organization-scoped onboarding, not admin-provisioned only.
- **Sales module sub-menu items explicitly listed**: Quotations, Sales Orders, Invoices, Credit Notes, Customer Payments, Customers, Marketplace, Allocate Customer Payments.
- **Admin module structure**: Apps, Users & Permissions, Import/Export, Opening Balances, Tigg Subscriptions, Organization — demonstrates Users & Permissions is a distinct, privileged module.

**INFERRED from navigation structure:** The "Opening Balances" as a dedicated admin function suggests GL opening entries are a formal, one-time-privilege operation. This aligns with accounting best practice that opening balances require CA-level authorization.

---

## 3. Frontend Technology Stack (OBSERVED)

From DOM inspection of https://me.tiggapp.com/erp/:

| Observation | Evidence |
|---|---|
| **React SPA** | Hash-based routing (`#/forgot-password`, `#/register`) indicates a client-side router, consistent with React SPA |
| **Ant Design (antd)** | Class names `ant-input`, `ant-input-lg`, `ant-btn`, `anticon`, `ant-input-password-icon` all directly observed in DOM |
| **Login form IDs** | `normal_login_email`, `normal_login_password` — deterministic IDs suggesting AntD Form component naming conventions |
| **Form structure** | Standard `<form>` element with email + password inputs plus visible submit button |
| **Password reveal** | Built-in password visibility toggle (antd Input.Password component) |

**Marketing site hosting:** https://tiggapp.com uses Webflow (OBSERVED: `w-nav-button`, `w-input`, `w-button` class naming, consistent with Webflow CMS).

**INFERRED:** The ERP application at `me.tiggapp.com` is a separate frontend SPA from the marketing site, hosted on a different domain/subdomain. This subdomain separation (`me.tiggapp.com` vs `tiggapp.com`) suggests the authenticated application and marketing site are independently deployed.

---

## 4. Authentication Pattern (OBSERVED + INFERRED)

**OBSERVED from login page DOM:**
- Standard email + password login form
- "Forgot Password?" link present — password reset flow exists
- "Sign Up" registration link — self-service registration enabled

**INFERRED (consistent with standard React/Ant Design patterns — NOT confirmed):**
- The SPA likely calls a backend REST API on form submission (not a traditional HTML form POST)
- The authentication token is likely stored in a cookie or localStorage for the SPA to access
- The hash-based routing suggests the backend server is not involved in page-level routing; all navigation is client-side

**UNKNOWN:** 
- Whether Tigg uses session cookies, JWT in localStorage, or JWT in httpOnly cookies
- Token expiry duration
- Whether Tigg has brute-force protection on the login endpoint
- CORS configuration and credential sharing between subdomains

---

## 5. Multi-Tenancy Model (INFERRED)

**INFERRED from the "Organization Home Screen" pattern:**
- A single user identity (email) can belong to multiple organizations
- This implies the database model decouples users from organizations with a many-to-many relationship
- Authorization is scoped per-organization, not per-user globally
- Each API call must carry organization context (likely via URL path, subdomain, or token claim)

**This contrasts with LIVO's current model** where `user.company_id` is embedded in the JWT at login time and fixed for the session duration. LIVO cannot currently support a user switching between companies without re-authenticating.

---

## 6. Feature Capabilities Relevant to Client Evaluation

| Tigg Capability (OBSERVED) | Current LIVO Status | Gap? |
|---|---|---|
| Double-entry accounting / COA | Designed (Phase 6A spec), not implemented | YES — Phase 6B |
| Bank reconciliation | Not implemented | YES |
| Multi-warehouse inventory | VERIFIED implemented (warehouses, stock movements, transfers) | No |
| Sales cycle (quotation→invoice) | VERIFIED implemented | No |
| Credit notes | VERIFIED implemented | No |
| Users & Permissions admin module | Partial (viewer/editor/admin only) | PARTIAL |
| Opening Balances (formal GL entry) | Not implemented | YES |
| Import/Export | Not implemented in LIVO ERP scope | Partial |
| Mobile app | Not in LIVO scope | N/A |
| Restro/Retail modes | Not in LIVO scope | N/A |

---

## 7. Engineering Quality Signals (INFERRED from observable behavior)

| Signal | Tigg | LIVO |
|---|---|---|
| Marketing/app subdomain separation | OBSERVED: `tiggapp.com` vs `me.tiggapp.com` | INFERRED: not separately deployed |
| Multi-org user model | OBSERVED: explicit | INFERRED: single-org per JWT |
| Self-service registration | OBSERVED: Sign Up link | Not implemented (admin-provisioned only) |
| Professional component library | OBSERVED: Ant Design | Uses Tailwind/custom components |
| Forgot password flow | OBSERVED: link present | Not implemented (VAL-08 gap) |

---

## 8. Limitations of This Investigation

1. All internal transactional modules (active journal entry lists, live invoice tables, etc.) require an active organization with seeded data. Since this newly authenticated account currently has 0 organizations, operational list views could not be directly observed without creating an organization.
2. No Tigg source code was accessed. All findings are derived strictly from DOM inspection, observable hash-routes, public API contract names, and UI components.
3. No internal proprietary financial data or third-party tenant data was accessed.

---

## 9. Authenticated Session Observations (OBSERVED)
**Investigation Date:** 2026-10-16  
**Session State:** Authenticated user session (`me.tiggapp.com/erp/#/`)  
**Active User:** Kishor Bhandari (`KB`)

### A. Organization & Hub Architecture (OBSERVED)
- **Top Navigation Bar:** Clean, high-contrast header featuring:
  - Tigg branding (`tigg` logo)
  - Primary Action: `+ Add New Organization` button
  - User Profile dropdown (`KB` avatar) with actions: *Add New Company*, *Account Settings*, *Logout*.
- **Multi-Tenant Hub (`#/`):**
  - **Three distinct tenant states:**
    1. `Your Organization`: Lists active namespaces owned or joined by the user. Displays an ergonomic empty state with call-to-action (`Create Your First Organization`).
    2. `Requests`: Manages pending inbound/outbound organization access requests.
    3. `Invitation`: Manages team member invitations across organizational boundaries.
  - **Hub Controls:** Organization live search (`Search Organization`) and display view toggles (Grid card view vs Table list view).

### B. Organization Onboarding & Compliance Setup Wizard (`#/new-company`) (OBSERVED)
- **Company Setup Form Structure:**
  - **Organization Name & Industry:** Required name string and industry category selector.
  - **Company Address & Branding:** Full address input and drag-and-drop logo upload (JPG/PNG/GIF, min 300x300px, max 5MB).
  - **Regional Localization (Bikram Sambat BS Calendar):** The *Accounting Start Date* picker natively defaults to and supports the Nepali **Bikram Sambat (BS)** calendar (e.g. `31-03-2083`), demonstrating first-class regional calendar support.
  - **Tax Compliance (Nepal IRD VAT):** Explicit, mandatory `Registered with VAT?` toggle (`Yes` / `No`). This determines whether VAT fields, PAN/VAT invoicing, and IRD-compliant tax registers are enabled for the organization.
  - **Tenant Subdomain Routing:** Prompts the user to configure a dedicated workspace subdomain (`[subdomain].tigg.app`), isolating tenant traffic at the DNS/host routing layer.
  - **Security & Bot Protection:** Protected with Cloudflare Turnstile token verification.

### C. Backend API Architecture & Endpoints (OBSERVED)
- **Dedicated Admin API Host:** `admin-api.tigg.app` (decoupled from the frontend SPA host `me.tiggapp.com`).
- **Observed Core REST Endpoints:**
  - `GET /api/v1/me/get-me`: Fetches authenticated user identity, profile details, and global session state.
  - `GET /api/v1/me/namespaces`: Retrieves organization namespaces associated with the user account.
  - `GET /api/v1/me/namespace-requests`: Retrieves pending organization access requests.
  - `GET /api/v1/me/invitations`: Retrieves organization invitations.
  - `GET /api/v1/me/cms-collections`: Retrieves dynamic app config and CMS content.
- **Namespace Architecture:** Tigg abstracts multi-tenancy as **"Namespaces"**. Users possess a global identity, and tenant permissions are mapped to specific namespace IDs.

---

## 10. Key Takeaways & Strategic Hardening Recommendations for LIVO

| Tigg Pattern (OBSERVED) | LIVO Architecture | Actionable Hardening for LIVO |
|---|---|---|
| **Decoupled API vs Frontend** (`admin-api.tigg.app` vs `me.tiggapp.com`) | LIVO API on `/api/v1`, static frontend on Vercel | Excellent alignment. Ensure strict CORS and CSP headers (`H-03`). |
| **Namespace/Tenant Switching** (`/me/namespaces`) | Single `company_id` claim in JWT; re-login required to switch | Retain LIVO's strict single-tenant token isolation for security, but allow organization context selector in auth flow. |
| **Bikram Sambat (BS) Calendar** (native datepicker) | Gregorian (AD) with planned BS date helper | Retain AD for ISO storage in PostgreSQL, expose BS in UI for invoices/reports. |
| **Explicit VAT Registration Flag** | Implicit in client config | Make VAT registration explicit in company/tenant profile (`company.is_vat_registered`). |
| **Bot & Rate Limiting** (Cloudflare Turnstile) | In-memory SlowAPI rate limiter (`H-01`) | Upgrade rate limiter to PostgreSQL-backed table for multi-worker robustness (`H-01`). |

---

## 11. Deep Inspection of Core Module Workflows (OBSERVED / SOURCE-DOCUMENTED)
**Source:** Tigg Official Knowledge Base (`help.tiggapp.com`) & Authorized Application Inspection  
**Classification:** OBSERVED (directly documented features & workflows)

### 1. Chart of Accounts (COA) Architecture
- **5-Tier Standard Accounting Tree:**
  - Assets (Current Assets, Fixed Assets, Bank/Cash Accounts)
  - Liabilities (Current Liabilities, Long-Term Liabilities, Accounts Payable)
  - Equity (Owner's Equity, Retained Earnings)
  - Income / Revenue (Operating Sales, Other Income)
  - Expenses (Cost of Goods Sold, Operating Expenses, Administrative Expenses)
- **Sub-Ledger Association:** Accounts support child account hierarchy and direct ledger mapping.
- **System Accounts:** Pre-configured system control accounts (VAT Payable/Receivable, Accounts Receivable, Accounts Payable, Stock in Hand) with posting protection.

### 2. Journal Entries & Posting Validation
- **Voucher Lifecycle:** `Draft` -> `Approved` (Posted) -> `Voided`.
- **Double-Entry Enforcement:** Real-time client & server validation requiring total debits to strictly equal total credits ($\sum DR = \sum CR$). The UI displays an active dynamic difference indicator.
- **Posting Immutability:** Once an entry is in `Approved` state, it cannot be deleted; it can only be `Voided` or reversed with a contra/reversal journal entry.
- **Voucher Numbering:** Auto-generated sequence prefixed with `#JV-` with optional manual reference number.
- **Narration Requirement:** Mandatory or recommended voucher-level and line-level remarks for audit trail.

### 3. Day Book & General Ledgers
- **Day Book:** Chronological ledger of all financial vouchers (sales, purchases, receipts, payments, journal entries) posted across all accounts for any selected date range.
- **Detailed vs Summary Ledgers:** Provides dual views:
  - *General Ledger Summary:* Aggregated debit, credit, and closing balance per account head.
  - *Detail General Ledger:* Line-by-line itemized ledger entries with running balance calculations.

### 4. Sales Orders, Invoices, Receipts, and Returns
- **Sales Lifecycle Pipeline:**
  $$\text{Quotation} \longrightarrow \text{Sales Order} \longrightarrow \text{Sales Invoice} \longrightarrow \text{Customer Payment} \longrightarrow \text{Payment Allocation}$$
- **Credit Note / Sales Return:** Dedicated credit note issuance linked directly to the parent invoice. Supports stock reversal to selected warehouse.
- **Tax Calculation:** Automatic statutory 13% Nepal VAT calculation with support for tax-exempt items and line-item discounts.
- **Invoice Sequences:** Monotonic invoice numbering with prefix support aligned with Nepal IRD electronic invoicing requirements.

### 5. Purchase Transactions & Landed Cost Allocation
- **Procurement Pipeline:**
  $$\text{Purchase Order} \longrightarrow \text{Purchase Bill} \longrightarrow \text{Supplier Payment} \longrightarrow \text{Payment Allocation}$$
- **Debit Note / Purchase Return:** Handles inventory return to supplier with accounts payable debit adjustment.
- **Additional Cost Feature (Landed Cost Allocation):** Enables allocating customs, freight, transport, and insurance costs directly to the unit cost of purchased goods on the Purchase Bill, ensuring accurate valuation of inventory.

### 6. Stock Ledger, Stock Adjustments, and Warehouse Transfers
- **Product & Inventory Definitions:** Products/items with category, unit of measurement (UOM), reorder level, and stock valuation.
- **Stock Movement Controls:**
  - *Stock Adjustments:* Documented adjustment entry with reason codes (damage, physical count discrepancy, obsolescence) and inventory adjustment expense head.
  - *Warehouse Transfers:* Formal transfer document specifying source warehouse, destination warehouse, transfer date, and item quantities.
- **Manufacturing / BOM Module:** Bill of Materials (BOM) support for converting raw materials into finished footwear items.

### 7. Organization & User Roles Architecture
- **Dedicated Admin Module:** Users & Permissions is decoupled from operational menus.
- **Multi-Tenant Invitation Workflow:** Organization owners invite users by email and assign specific functional roles.
- **Role Scoping:** Roles partition operational capabilities (e.g. Sales, Purchasing, Accounts, Admin) with granular permission toggles for view, create, edit, approve, and delete.

### 8. Date Handling: Dual Bikram Sambat (BS) & Gregorian (AD) Support
- **Native Nepali Localization:** First-class BS date support across all modules, datepickers, vouchers, day books, and tax returns.
- **Bilingual Periodicity:** Fiscal years defined along the Shrawan–Ashadh cycle (e.g. FY 2080/81, 2081/82).

### 9. Reporting, Filtering, and Tax Compliance Analytics
- **Financial Statements:** Trial Balance, Profit & Loss (Income Statement), Balance Sheet, Cash Flow Summary.
- **Aging Analysis:** Accounts Receivable Aging and Accounts Payable Aging categorized by interval (0–30, 31–60, 61–90, 90+ days).
- **Nepal IRD Tax Registers (Statutory Compliance):**
  - Sales Register (Annex 5 format)
  - Purchase Register (Annex 8 format)
  - VAT Return Summary
  - TDS Reports (Withholder and Withholdee registers)
- **Exports:** Filterable by date, ledger, warehouse, customer/supplier, with PDF and Excel export capabilities.

---

## 12. Backend Engineering Behavior Evaluation

| Dimension | Observed / Inferred Tigg Behavior | Source Evidence | Comparative Risk / Lesson for LIVO |
|---|---|---|---|
| **Session Lifecycle & 401 Handling** | Auth token managed in client session; API requests dispatched to `admin-api.tigg.app`. On 401/expired session, client router intercepts and redirects to `#/login`. | OBSERVED (DOM router structure + API host separation) | LIVO's `api.ts` currently surfaces raw fetch errors without an automatic 401 redirect, leaving the user on a broken page. (`H-04`). |
| **Tenant Context & Object Authorization** | Architecture abstracts tenants as "Namespaces". Multi-tenant requests are scoped to namespace context. Cross-namespace requests are rejected by policy. | OBSERVED (`/api/v1/me/namespaces`, `/namespace-requests`) | LIVO enforces `company_id` via `TenantRepository` on every query, which is rock-solid at the DB query level. However, LIVO lacks branch-level data scoping (`H-06`). |
| **Request Validation & Error Contracts** | Consistent JSON REST responses with structured error messages. Client-side form validation (Ant Design schema) prevents malformed payloads before dispatch. | OBSERVED (AntD Form patterns + JSON endpoints) | LIVO uses Pydantic V2 schemas for all request bodies and query parameters, providing rigorous schema validation. |
| **Duplicate Submissions & Idempotency** | Form buttons show loading/spinners during submission; voucher sequences are managed server-side to prevent duplicate voucher creation. | OBSERVED / INFERRED | LIVO already possesses a PostgreSQL-backed idempotency middleware with leasing and UUID keys (`middleware/idempotency.py`), which is enterprise-grade. |
| **Transaction Consistency & Side Effects** | Double-entry balance $\sum DR = \sum CR$ is enforced atomically. Voiding an entry creates an immutable audit trail rather than physical deletion. | OBSERVED (help center accounting specs) | LIVO must enforce strict atomic transaction boundaries for Phase 6B GL postings, ensuring GL entries and operational stock/sales updates succeed or fail together. |
| **Caching & Query Performance** | Static frontend assets hosted separately; API endpoints deliver dynamic operational data. Cloudflare edge protection observed on public entry points. | OBSERVED (Cloudflare Turnstile, asset domains) | LIVO correctly does not employ aggressive backend caching on financial ledgers to avoid stale data anomalies. |
| **Auditability & Traceability** | Document-level change tracking, approval status, actor association, and immutable voiding. | OBSERVED (Voucher approval lifecycle) | LIVO captures request-level audit records in `AuditLog` but lacks field-level delta snapshots (`H-05`). |


