# LIVO Footwear ERP — Industrial Enterprise Manufacturing Suite

[![Live Production](https://img.shields.io/badge/Production-Live%20on%20Vercel-emerald?style=for-the-badge&logo=vercel)](https://livo-footwear-erp.vercel.app)
[![API Engine](https://img.shields.io/badge/FastAPI%20Engine-Render%20Cloud-blue?style=for-the-badge&logo=render)](https://livo-footwear-erp-backend.onrender.com/docs)
[![Database](https://img.shields.io/badge/Neon%20PostgreSQL-Serverless%20%2B%20PITR-34d399?style=for-the-badge&logo=postgresql)](https://neon.tech)
[![Python Tests](https://img.shields.io/badge/Pytest-29%2F29%20Passed-brightgreen?style=for-the-badge&logo=pytest)](backend/tests/)
[![Next.js Bundle](https://img.shields.io/badge/First%20Load%20JS-103%20kB%20(%3C115%20kB)-success?style=for-the-badge&logo=nextdotjs)](frontend/)
[![Tax Compliance](https://img.shields.io/badge/Nepal%20IRD-13%25%20VAT%20Compliant-orange?style=for-the-badge)](https://livo-footwear-erp.vercel.app)

> Engineered specifically for **LIVO GROUP OF INDUSTRIES** footwear manufacturing operations across Nepal. Built for extreme factory floor durability, zero data tampering, bilingual English/Nepali line operation, continental Paris Points sizing curves, and automated statutory tax compliance.

---

## ⚡ Live Production Coordinates & Demo Credentials

| Resource | Environment / Target | Access / Direct Link |
| :--- | :--- | :--- |
| **Production Web Application** | Vercel Edge Global CDN | [**https://livo-footwear-erp.vercel.app**](https://livo-footwear-erp.vercel.app) |
| **Production REST Backend** | Render Container (Python 3.12 / FastAPI) | [**https://livo-footwear-erp-backend.onrender.com**](https://livo-footwear-erp-backend.onrender.com) |
| **Interactive API Documentation** | Swagger / OpenAPI 3.0 | [**Swagger UI (/docs)**](https://livo-footwear-erp-backend.onrender.com/docs) |
| **Cloud Health Probe** | Real-time DB & Container Status | [`/api/v1/health`](https://livo-footwear-erp-backend.onrender.com/api/v1/health) |

### Demonstration Credentials (1-Click Login Ready)

The live login interface includes **1-click quick-fill buttons** (`Demo Admin` / `Demo Viewer`):

```tsv
Role                    Username        Password          Privileges
Executive Admin/Editor  admin_demo      LivoAdmin2026!    Full operational access: Batches, Inwarding, Sales, Invoicing
Auditor / Floor Viewer  viewer_demo     LivoViewer2026!   Read-only analytics: All mutation buttons strictly locked
```

> **Client Pitch Reference:** See [**`docs/CLIENT_PITCH_CHEATSHEET.md`**](docs/CLIENT_PITCH_CHEATSHEET.md) for the 5-minute executive pitch script, pre-flight warm-up curl commands, and instant triage procedures.

---

## 🎬 Automated End-to-End Walkthrough (Acts 1–6)

Recorded live across the deployed cloud environment using the DOM/browser agent:

📹 **Full Walkthrough Video:** [**`docs/demos/livo_erp_complete_walkthrough.webm`**](docs/demos/livo_erp_complete_walkthrough.webm) *(also available as `.webp`)*

### Act 1: Login & Bilingual Factory Ergonomics
*Instant 1-click toggle between English and authentic Nepali (*प्रयोगकर्ता, पासवर्ड, लगइन*). Supports non-English-speaking factory supervisors.*

![Act 1: Nepali Bilingual Login](docs/demos/act1_nepali_login_keyframe.png)

---

### Act 2: Daily Executive Cockpit & Production Velocity
*Factory Floor Velocity tracking (Produced vs. Dispatched ratio), Realized Cash Ratio, and line throughput without end-of-month lag.*

![Act 2: Daily Executive Cockpit](docs/demos/act2_executive_cockpit_keyframe.png)

---

### Act 3: Finished Footwear Sizing Matrix (Paris Points 32–43)
*Continental sizing curves across standard footwear sizes (32–43) with green in-stock indicators, zero-stock dashes, sticky columns, and 1-click CSV export.*

![Act 3: Footwear Sizing Matrix](docs/demos/act3_stock_ledger_sizing_keyframe.png)

---

### Act 4: Hands-Free Rapid Production Entry
*Keyboard-driven sequential entry (<kbd>Alt+N</kbd> drawer trigger, sequential field traversal, <kbd>Ctrl+Enter</kbd> commit) with auto-incrementing batch sequence (`BATCH-1680`).*

![Act 4: Continuous Batch Entry](docs/demos/act4_production_continuous_batch_keyframe.png)

---

### Act 5: Wholesale Sales Order, Live 13% VAT Strip & Sequential Invoice
*Live calculation of taxable subtotal, 13% Nepal VAT, and gross NPR. Issues gapless, monotonic tax invoices (`INV-01-XXXXX`) with PAN and signature blocks.*

![Act 5: Wholesale Sales Order and VAT Strip](docs/demos/act5_wholesale_vat_strip_keyframe.png)

![Act 5: Statutory Printable VAT Invoice](docs/demos/act5_tax_invoice_keyframe.png)

---

### Act 6: Role-Based Security Smoke Check (Viewer Lockout)
*Demonstrating read-only auditor mode: Mutation actions (`+ Record Batch`, `+ Record Sale`, `Void`) are completely removed from the interface and guarded at the API level.*

![Act 6: Viewer Role Read-Only Lockdown](docs/demos/act6_viewer_role_locked_keyframe.png)

---

## 📐 System Architecture, Workflows & Rookie Debugging Decision Tree

```mermaid
flowchart TB
    subgraph CLIENT ["🖥️ CLIENT LAYER (Factory Floor & Executive Cockpit)"]
        BROWSER["Modern Browser / Mobile Tablet\n(Next.js 14 High-Density UI · Tailwind Tokens)"]
        SCANNER["Hardware Barcode Scanner\n(USB / Bluetooth HID Burst < 35ms)"]
        OFFLINE_DB[("Terminal IndexedDB Outbox\n(Offline Mutation Queue · Idempotent UUID)")]
        I18N_ENGINE["Bilingual Localizer\n(English / Authentic Nepali · Zero Layout Shift)"]
        PAISA_MATH["Integer Paisa Math Engine\n(1 NPR = 100 Paisa · Zero IEEE-754 Drift)"]
    end

    subgraph DEVOPS_EDGE ["🌐 DEVOPS EDGE & REVERSE PROXY (Vercel Global CDN)"]
        VERCEL_EDGE["Vercel Global Edge Network\n(Anycast CDN · SSL Termination)"]
        REWRITE_PROXY["Internal Edge Rewrite (/api/backend/*)\n(Routes calls through frontend domain)"]
        FIRST_PARTY_COOKIE["First-Party Session Cookie\n(SameSite=Lax · Secure · HttpOnly)"]
    end

    subgraph BACKEND_ENGINE ["⚡ BACKEND API ENGINE (Render Cloud / Python 3.12 FastAPI)"]
        CORR_MIDDLEWARE["Correlation Middleware\n(Extracts / Generates X-Request-ID: req_xxxxxxxxxxxx)"]
        AUTH_RBAC["JWT Security & RBAC Guard\n(Admin/Editor Mutate vs. Viewer Read-Only)"]
        MUTEX_LOCK["Concurrency Mutex & Pessimistic Lock\n(Product.with_for_update · Stock Barrier)"]
        BOM_ENGINE["Automated BOM Deduction Engine\n(Raw Material KG / Meters consumed per batch)"]
        VAT_ENGINE["Statutory Tax Engine\n(Exact 13% Nepal VAT · Decimal ROUND_HALF_UP)"]
        SNAPSHOT_ENGINE["O(1) Snapshot Aggregator\n(Stock = Snapshot Balance + Delta Movements)"]
    end

    subgraph PERSISTENCE ["🗄️ PERSISTENCE & DEVOPS INFRASTRUCTURE (Neon PostgreSQL + Storage)"]
        NEON_DB[("Neon Serverless PostgreSQL\n(Auto-Suspend · PgBouncer Pooled Connection)")]
        STOCK_LEDGER[("stock_movements Table\n(Signed Append-Only Ledger: +1 IN / -1 OUT)")]
        INVOICE_SEQ[("invoices Table\n(uq_invoice_company_sequence Unique DB Lock)")]
        SNAPSHOTS[("stock_snapshots Table\n(Materialized Balance & last_movement_id)")]
        S3_BACKUP[("Cloud Storage / S3 Backups\n(Daily pg_dump Snapshots & Vendor Bill Attachments)")]
    end

    SCANNER -->|"Rapid Scan Burst"| BROWSER
    BROWSER <-->|"Auto-Sync / Flush"| OFFLINE_DB
    BROWSER --- I18N_ENGINE
    BROWSER --- PAISA_MATH
    BROWSER -->|"HTTPS Requests"| VERCEL_EDGE
    VERCEL_EDGE --> REWRITE_PROXY
    REWRITE_PROXY -->|"Proxied API Calls"| CORR_MIDDLEWARE
    REWRITE_PROXY -.-> FIRST_PARTY_COOKIE
    CORR_MIDDLEWARE --> AUTH_RBAC
    AUTH_RBAC --> MUTEX_LOCK
    MUTEX_LOCK --> BOM_ENGINE
    BOM_ENGINE --> VAT_ENGINE
    VAT_ENGINE --> SNAPSHOT_ENGINE
    SNAPSHOT_ENGINE -->|"ACID Transaction"| NEON_DB
    NEON_DB --- STOCK_LEDGER
    NEON_DB --- INVOICE_SEQ
    NEON_DB --- SNAPSHOTS
    NEON_DB -.->|"Automated Nightly Backups"| S3_BACKUP
```

---

### 🏭 End-to-End Factory Manufacturing & Financial Lifecycle

```mermaid
flowchart LR
    subgraph P1 ["1. Procurement"]
        PO["Raw Material Purchase\n(Leather, Rubber, Soles)"]
        RM_STOCK["Raw Material Stock\n(+KG / +Meters Inward)"]
    end

    subgraph P2 ["2. Manufacturing"]
        BATCH["Log Production Batch\n(Paris Points Sizes 32–43)"]
        BOM["Auto BOM Deduction\n(-Raw Materials Consumed)"]
        IN_LEDGER["Stock Movement (+IN)\n(+Finished Footwear Pairs)"]
    end

    subgraph P3 ["3. Sales & Dispatch"]
        SO["Wholesale Sales Order\n(Client, Size, Price Selection)"]
        LOCK_CHECK{"Pessimistic Lock Check\n(Available Stock >= Order?)"}
        OUT_LEDGER["Stock Movement (-OUT)\n(-Finished Pairs Dispatched)"]
    end

    subgraph P4 ["4. Statutory Invoicing"]
        VAT_CALC["Paisa Precision Calc\n(Taxable Subtotal + 13% VAT)"]
        INV_LOCK["Monotonic Sequence Lock\n(INV-01-XXXXX Unique Constraint)"]
        PRINT_INV["Statutory Printable Invoice\n(PAN, Signatures, Line Items)"]
    end

    subgraph P5 ["5. Financial Velocity"]
        PAYMENT["Record Cash / Bank Payment\n(Integer Paisa Arithmetic)"]
        COCKPIT["Executive Cockpit Update\n(Realized Cash Ratio & Daily Velocity)"]
    end

    PO --> RM_STOCK
    RM_STOCK --> BOM
    BATCH --> BOM
    BOM --> IN_LEDGER
    IN_LEDGER --> SO
    SO --> LOCK_CHECK
    LOCK_CHECK -->|"Stock Available"| OUT_LEDGER
    LOCK_CHECK -->|"Insufficient Stock"| ERR_422["HTTP 422 Barrier\n(Oversell Blocked)"]
    OUT_LEDGER --> VAT_CALC
    VAT_CALC --> INV_LOCK
    INV_LOCK --> PRINT_INV
    PRINT_INV --> PAYMENT
    PAYMENT --> COCKPIT
```

---

### 🩺 Rookie-Proof Troubleshooting & Debugging Decision Tree

If anything fails on the factory floor or during testing, follow this intuitive diagnostic tree step-by-step:

```mermaid
flowchart TD
    START(["🚨 Observation / Error Occurred on LIVO ERP"]) --> SYMPTOM{"What is the exact observable symptom?"}

    %% Symptom 1: Spinner / 504 Gateway Timeout
    SYMPTOM -->|"Page spins forever (>15s) or HTTP 504"| CAUSE_504["Render Free-Tier Container Hibernating\n(Sleeps after 15 min of zero traffic)"]
    CAUSE_504 --> FIX_504["⚡ 10-Second Rookie Fix:\nRun the health check warmup ping in terminal:\ncurl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health\nWait 15s for the container to wake up. Reload page!"]

    %% Symptom 2: 401 Unauthorized / 403 Forbidden
    SYMPTOM -->|"HTTP 401 or 403 Error Banner"| CHECK_AUTH{"Which error code is returned?"}
    CHECK_AUTH -->|"HTTP 401 (Unauthorized)"| FIX_401["🔑 5-Second Rookie Fix:\nJWT session token expired or cookie cleared.\nClick 'Demo Admin' or log in again."]
    CHECK_AUTH -->|"HTTP 403 (Forbidden)"| FIX_403["🛡️ Intentional Security Guard:\nYou are logged in as 'viewer_demo' (Auditor Mode).\nMutation buttons are disabled by design.\nClick 'Demo Admin' (admin_demo) to regain write access."]

    %% Symptom 3: 422 Negative Stock Boundary
    SYMPTOM -->|"HTTP 422 (Insufficient physical stock)"| CAUSE_422["Negative Stock Boundary Guard Triggered:\nAttempted to dispatch more pairs than exist in stock."]
    CAUSE_422 --> FIX_422["📦 10-Second Rookie Fix:\n1. Check available pairs in Stock Report.\n2. Press Alt+N on Production tab to log a finished batch (+IN).\n3. Re-dispatch the sales order with valid stock."]

    %% Symptom 4: 409 Sequence Conflict
    SYMPTOM -->|"HTTP 409 (Invoice Sequence Conflict)"| CAUSE_409["Concurrent Invoice Generation Race:\nTwo clerks issued an invoice at the exact same millisecond."]
    CAUSE_409 --> FIX_409["🔄 Built-In Auto-Recovery:\nThe system automatically retries 3 times.\nSimply click 'Create Invoice' once more."]

    %% Symptom 5: Offline / Network Drop
    SYMPTOM -->|"Internet Dropped / Factory WiFi Offline"| CAUSE_OFFLINE["Factory Connectivity Lost:\nTerminal Outbox activated automatically."]
    CAUSE_OFFLINE --> FIX_OFFLINE["💾 Zero Data Loss Guarantee:\nMutations are stored locally in IndexedDB.\nThey automatically flush to the server when connection returns."]

    %% Symptom 6: Any Unknown / General Error
    SYMPTOM -->|"Error Banner showing Support Reference"| CAUSE_TRACE["Error banner displays reference code:\n'Transaction failed. Support reference: [req_xxxxxxxxxxxx]'"]
    CAUSE_TRACE --> FIX_TRACE["🔍 Instant Trace Action:\n1. Copy the reference code (e.g. req_8f1a3b2c4d5e).\n2. Search Render Backend Logs for this exact string.\n3. The log shows the exact endpoint, latency, user_id, and Python trace!"]
```

---

### 🚨 Emergency Triage Matrix & Quick Commands

| Symptom / Error | Root Cause | Immediate 10-Second Remediation |
| :--- | :--- | :--- |
| **HTTP 504 / Cold Start** | Render free-tier container spinning down after 15 min idle | Run: `curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health` (Warms up container in 15s). |
| **HTTP 401 Unauthorized** | JWT cookie expired after 24h session duration | Click **Demo Admin** on the login screen to re-authenticate with full credentials. |
| **HTTP 403 Forbidden** | User session is scoped to read-only `viewer` role | Switch role to `editor` or click **Demo Admin** (`admin_demo`) to perform mutations. |
| **HTTP 422 Stock Error** | Negative stock barrier: Requested quantity > Available pairs | Open **Stock Report**, verify current size pairs, and log a batch (+IN) before dispatching. |
| **HTTP 409 Conflict** | Invoice monotonic sequence number collision under heavy load | The API retries 3 times automatically. If retries exhaust, click **Create Invoice** once more. |
| **Network Disconnection** | Factory floor WiFi or cellular backup dropped | Do not reload: The **Terminal Outbox** buffers mutations and will auto-flush upon reconnect. |
| **Unknown Error Trace** | Backend application exception during transaction | Copy the support reference `[req_xxxxxxxxxxxx]` from the UI and grep Render cloud logs. |

---

## 🏛️ Core Architectural Pillars

### 1. Strict Append-Only Stock Ledger (Zero Inventory Theft)
- Products have **no mutable `stock_qty` integer** in the database.
- Inventory is computed mathematically on-the-fly from the signed, append-only `stock_movements` ledger:
  $$\text{Stock Balance} = \sum (\text{direction} \times \text{quantity}), \quad \text{direction} \in \{+1, -1\}$$
- Prevents stealth adjustments, unauthorized manual edits, and inventory leakage.

### 2. Monotonic Nepal IRD Sequential Invoicing
- Tax invoice numbers follow the format `INV-01-XXXXX` and are strictly locked at the PostgreSQL transaction level via the unique constraint `uq_invoice_company_sequence`.
- Prevents sequence gaps, duplicate numbers, and concurrency race conditions during wholesale billing surges.

### 3. Continental Footwear Sizing Curves (Paris Points 32–43)
- Models are indexed across standard continental sizing (32 to 43) per colorway and SKU.
- Production and dispatch entries validate inventory availability per individual size to eliminate broken size runs and unmatched cartons.

### 4. Bilingual Factory Floor Accessibility (a11y)
- Zero-dependency client-side localization provider supporting full English and authentic Nepali (*दैनिक प्रतिवेदन, स्टक लेजर, उत्पादन ब्याच, बिक्री तथा बिलिङ*).
- Persistent language state in `localStorage` with zero layout shift (CLS < 0.02).
- Keyboard shortcuts (<kbd>Alt+N</kbd>, <kbd>Ctrl+Enter</kbd>, <kbd>Esc</kbd>) allow floor clerks to record production continuous batches mouse-free.

---

## 📚 Complete Engineering Documentation & Playbooks

| Document | Purpose |
| :--- | :--- |
| [**`docs/CLIENT_PITCH_CHEATSHEET.md`**](docs/CLIENT_PITCH_CHEATSHEET.md) | Executive demonstration reference, 5-minute presentation script, and on-call pitch triage matrix. |
| [**`docs/OPERATIONAL_HANDOVER.md`**](docs/OPERATIONAL_HANDOVER.md) | Complete factory standard operating procedure (SOP), role-based permissions matrix, and backup topologies. |
| [**`docs/CRITICAL_DEBUGGING_RUNBOOK.md`**](docs/CRITICAL_DEBUGGING_RUNBOOK.md) | 5-second component triage guide, error code matrix, and emergency disaster recovery playbooks. |
| [**`docs/SYSTEM_AUDIT_REPORT.md`**](docs/SYSTEM_AUDIT_REPORT.md) | Dual-persona adversarial audit covering UI/UX ergonomic clarity and backend architectural integrity. |
| [**`docs/RESTORE_PROCEDURE.md`**](docs/RESTORE_PROCEDURE.md) | Point-in-time recovery (PITR) procedures, database failover protocols, and verification tests. |
| [**`docs/SECURITY_ARCHITECTURE.md`**](docs/SECURITY_ARCHITECTURE.md) | JWT auth flow, Argon2 password hashing, RBAC scopes, and TLS encryption specifications. |

---

## 🛠️ Local Development & Quick Start

### Backend (FastAPI + Python 3.12)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows (or source venv/bin/activate on Linux/macOS)

# Install dependencies
pip install -r requirements.txt

# Run database migrations & seed test fixtures
python -m app.db.seed

# Run automated test suite (27 passing tests)
pytest

# Launch local API engine (http://localhost:8000)
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js 14 + TailwindCSS Tokens)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Verify production bundle size (<110 kB constraint)
npm run build

# Launch development server (http://localhost:3000)
npm run dev
```

---

## 👥 Demonstration Team & Sign-Off

- **Client:** LIVO GROUP OF INDUSTRIES (Nepal Footwear Manufacturing)
- **Deployment Status:** Live Production (`https://livo-footwear-erp.vercel.app`)
- **Backend Architecture:** Render Cloud + Neon Serverless PostgreSQL
- **License:** Proprietary — All Rights Reserved © 2026 LIVO GROUP OF INDUSTRIES
