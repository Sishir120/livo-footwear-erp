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

## 📐 Enterprise Architecture, Lifecycles & Rookie Debugging Playbook

### 1. Cloud Production Architecture & DevOps Topology

> **Full-Stack Blueprint:** Follows requests from hardware barcode scanners through Vercel edge reverse proxying, Render containerized FastAPI with in-process concurrency mutexes, to Neon serverless PostgreSQL with 7-day point-in-time recovery.

![LIVO Cloud Architecture Blueprint](docs/diagrams/system_architecture_overview.visual-check.1440x900.dark.png)

<details>
<summary><b>🔍 View Interactive Topology Code & Subsystem Map (Click to Expand)</b></summary>

```mermaid
flowchart TB
    classDef client fill:#0b1329,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;
    classDef edge fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef backend fill:#022c22,stroke:#34d399,stroke-width:2px,color:#f8fafc;
    classDef security fill:#450a0a,stroke:#fb7185,stroke-width:2px,color:#fecaca;
    classDef db fill:#2e1065,stroke:#c084fc,stroke-width:2px,color:#f8fafc;
    classDef storage fill:#292524,stroke:#f59e0b,stroke-width:2px,color:#fef3c7;

    subgraph CLIENT ["🖥️ CLIENT LAYER (Factory Line & Tablet Terminals)"]
        SCANNER["Hardware Barcode Scanner<br/><code>HID USB/BT &lt;35ms Burst</code>"]:::client
        BROWSER["Next.js 14 Enterprise UI<br/><code>Tailwind Tokens · 103kB Bundle</code>"]:::client
        OFFLINE_DB[("Terminal IndexedDB Outbox<br/><code>Offline Queue · Zero Data Loss</code>")]:::client
        I18N["Bilingual Localizer<br/><code>English / Authentic Nepali</code>"]:::client
        PAISA["Integer Paisa Engine<br/><code>1 NPR = 100 Paisa (Zero Float Drift)</code>"]:::client
    end

    subgraph DEVOPS_EDGE ["🌐 DEVOPS EDGE & REVERSE PROXY (Vercel Anycast CDN)"]
        VERCEL_EDGE["Vercel Global Edge Network<br/><code>SSL Termination · DDoS Shield</code>"]:::edge
        PROXY_REWRITE["Internal Edge Proxy (/api/backend/*)<br/><code>First-Party Route Unification</code>"]:::edge
        COOKIES["First-Party Session Cookie<br/><code>SameSite=Lax · Secure · HttpOnly</code>"]:::edge
    end

    subgraph BACKEND_ENGINE ["⚡ BACKEND API ENGINE (Render Container / Python 3.12 FastAPI)"]
        CORR["Correlation Tracing Middleware<br/><code>X-Request-ID: req_xxxxxxxxxxxx</code>"]:::backend
        RBAC["JWT Security & RBAC Guard<br/><code>admin_demo (Write) / viewer_demo (Locked)</code>"]:::security
        MUTEX["Concurrency Mutex & Pessimistic Lock<br/><code>Product.with_for_update() Barrier</code>"]:::security
        BOM["Automated BOM Deduction Engine<br/><code>Raw Material Consumption (-KG)</code>"]:::backend
        VAT["Statutory Tax Engine<br/><code>Exact 13% Nepal VAT · Decimal ROUND_HALF_UP</code>"]:::backend
        SNAPSHOT["O(1) Snapshot Aggregator<br/><code>Stock = Snapshot + Delta Movements</code>"]:::backend
    end

    subgraph PERSISTENCE ["🗄️ PERSISTENCE & DISASTER RECOVERY (Neon Serverless PostgreSQL)"]
        NEON_DB[("Neon PostgreSQL Serverless<br/><code>Auto-Suspend · PgBouncer Pool</code>")]:::db
        STOCK_LEDGER[("stock_movements Table<br/><code>Signed Ledger (+1 IN / -1 OUT)</code>")]:::db
        INVOICE_SEQ[("invoices Table<br/><code>uq_invoice_company_sequence Lock</code>")]:::db
        SNAPSHOT_TBL[("stock_snapshots Table<br/><code>Materialized Balance &amp; last_id</code>")]:::db
        S3_BACKUP[("Cloudflare R2 / S3 Backups<br/><code>Nightly pg_dump · 7-Day PITR</code>")]:::storage
    end

    SCANNER -->|"Scan Keystrokes"| BROWSER
    BROWSER <-->|"Auto-Sync / Flush"| OFFLINE_DB
    BROWSER --- I18N
    BROWSER --- PAISA
    BROWSER -->|"HTTPS Calls"| VERCEL_EDGE
    VERCEL_EDGE --> PROXY_REWRITE
    PROXY_REWRITE -->|"Proxied Request"| CORR
    PROXY_REWRITE -.-> COOKIES
    CORR --> RBAC
    RBAC --> MUTEX
    MUTEX --> BOM
    BOM --> VAT
    VAT --> SNAPSHOT
    SNAPSHOT -->|"ACID Transaction"| NEON_DB
    NEON_DB --- STOCK_LEDGER
    NEON_DB --- INVOICE_SEQ
    NEON_DB --- SNAPSHOT_TBL
    NEON_DB -.->|"Automated WAL Sync"| S3_BACKUP

    linkStyle default stroke:#475569,stroke-width:2px;
```

</details>

---

### 2. End-to-End Manufacturing & Financial Lifecycle Workflow

> **Factory Operations Lifeline:** Tracks raw material inwarding, automated BOM deductions, finished Paris Points batch creation, wholesale orders, monotonic VAT invoicing, and daily executive rollups.

![Complete ERP Lifecycle Lifeline](docs/diagrams/workflow_complete_erp_lifecycle.visual-check.1440x900.dark.png)

<details>
<summary><b>🔍 View Sequential Pipeline Chart (Click to Expand)</b></summary>

```mermaid
flowchart LR
    classDef step fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef action fill:#022c22,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef check fill:#2e1065,stroke:#a855f7,stroke-width:2px,color:#f8fafc;
    classDef reject fill:#450a0a,stroke:#ef4444,stroke-width:2px,color:#fecaca;
    classDef finish fill:#1e1b4b,stroke:#06b6d4,stroke-width:2px,color:#f8fafc;

    subgraph S1 ["Phase 1: Procurement"]
        PO["Raw Material Purchase Order<br/>(Synthetic Leather, Soles, Glue)"]:::step
        RM_LEDGER["Raw Material Ledger<br/>(+KG / +Meters Inward)"]:::action
    end

    subgraph S2 ["Phase 2: Manufacturing"]
        BATCH["Log Production Batch<br/>(Paris Points 32–43 Sizing)"]:::step
        BOM["Auto BOM Engine<br/>(-Raw Material Consumed)"]:::action
        IN_LEDGER["Stock Movement (+IN)<br/>(+Pairs Finished Footwear)"]:::action
    end

    subgraph S3 ["Phase 3: Wholesale Dispatch"]
        SO["Wholesale Sales Order<br/>(Client &amp; SKU Selection)"]:::step
        LOCK_CHECK{"Pessimistic Lock Check<br/>(Stock &gt;= Quantity?)"}:::check
        OUT_LEDGER["Stock Movement (-OUT)<br/>(-Pairs Dispatched)"]:::action
        ERR_422["HTTP 422 Barrier<br/>(Oversell Prevented)"]:::reject
    end

    subgraph S4 ["Phase 4: Statutory Invoicing"]
        VAT_CALC["Paisa Precision Calc<br/>(Subtotal + 13% Statutory VAT)"]:::step
        INV_LOCK["Monotonic Sequence Lock<br/>(INV-01-XXXXX DB Constraint)"]:::action
        PRINT_INV["Statutory Printable Invoice<br/>(PAN, Signatures, Line Items)"]:::finish
    end

    subgraph S5 ["Phase 5: Financial Velocity"]
        PAYMENT["Record Payment<br/>(Cash / Bank Transfer)"]:::step
        COCKPIT["Executive Cockpit<br/>(Realized Cash &amp; Factory Velocity)"]:::finish
    end

    PO --> RM_LEDGER
    RM_LEDGER --> BOM
    BATCH --> BOM
    BOM --> IN_LEDGER
    IN_LEDGER --> SO
    SO --> LOCK_CHECK
    LOCK_CHECK -->|"Stock Verified"| OUT_LEDGER
    LOCK_CHECK -->|"Deficit Detected"| ERR_422
    OUT_LEDGER --> VAT_CALC
    VAT_CALC --> INV_LOCK
    INV_LOCK --> PRINT_INV
    PRINT_INV --> PAYMENT
    PAYMENT --> COCKPIT

    linkStyle default stroke:#64748b,stroke-width:2px;
```

</details>

---

### 3. Critical Debugging Triage Flowchart & Emergency Lifelines

> **On-Call Pitch & Production Diagnostic Matrix:** Maps edge timeouts, JWT expiration, viewer role lockouts, sequence collisions, and negative stock barriers directly to 10-second solutions.

![Critical Debugging Triage Lifeline](docs/diagrams/workflow_critical_debugging_triage.visual-check.1440x900.dark.png)

---

### 🩺 Rookie-Proof Troubleshooting Decision Tree

Follow this exact diagnostic tree whenever diagnosing an error or unexpected state:

```mermaid
flowchart TD
    classDef startNode fill:#0f172a,stroke:#64748b,stroke-width:2px,color:#f8fafc;
    classDef decision fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
    classDef cause fill:#312e81,stroke:#a78bfa,stroke-width:2px,color:#f8fafc;
    classDef fix fill:#022c22,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef defense fill:#450a0a,stroke:#fb7185,stroke-width:2px,color:#fecaca;
    classDef trace fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;

    START(["🚨 Observation / Error Occurred on LIVO ERP"]):::startNode --> SYMPTOM{"What is the observable symptom?"}:::decision

    %% Branch 1: Spinner / 504 Gateway Timeout
    SYMPTOM -->|"Page spins &gt;15s or HTTP 504 Timeout"| C_504["Render Free-Tier Container Hibernating<br/>(Sleeps after 15 minutes of zero traffic)"]:::cause
    C_504 --> F_504["⚡ 10-Second Warmup Fix:<br/>Run curl warmup ping in terminal:<br/><code>curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health</code><br/>Wait 15s for the container to wake up. Reload page!"]:::fix

    %% Branch 2: 401 Unauthorized / 403 Forbidden
    SYMPTOM -->|"HTTP 401 or 403 Error Banner"| CHECK_AUTH{"Which HTTP status code?"}:::decision
    CHECK_AUTH -->|"HTTP 401 (Unauthorized)"| F_401["🔑 5-Second Auth Fix:<br/>JWT session cookie expired after 24h.<br/>Click 'Demo Admin' button or log in again."]:::fix
    CHECK_AUTH -->|"HTTP 403 (Forbidden)"| F_403["🛡️ Intentional Security Guard:<br/>You are logged in as 'viewer_demo' (Auditor Mode).<br/>Mutation buttons (+ Batch, + Order, Void) are locked by design.<br/>Click 'Demo Admin' (admin_demo) to regain write privileges."]:::defense

    %% Branch 3: 422 Negative Stock Boundary
    SYMPTOM -->|"HTTP 422 (Insufficient physical stock)"| C_422["Negative Stock Barrier Triggered:<br/>'Insufficient physical stock for this size variant (Available: X, Requested: Y)'"]:::defense
    C_422 --> F_422["📦 10-Second Inventory Fix:<br/>1. Open Stock Report to see in-stock size pairs.<br/>2. Press Alt+N on Production tab to log a finished batch (+IN).<br/>3. Re-dispatch the sales order with valid stock."]:::fix

    %% Branch 4: 409 Sequence Conflict
    SYMPTOM -->|"HTTP 409 (Invoice Sequence Conflict)"| C_409["Concurrent Invoice Sequence Collision:<br/>Two clerks generated an invoice at the exact same millisecond."]:::cause
    C_409 --> F_409["🔄 Built-In Auto-Recovery:<br/>The API retry loop recovers automatically (up to 3 retries).<br/>Simply click 'Create Invoice' once more."]:::fix

    %% Branch 5: Offline / Network Drop
    SYMPTOM -->|"Internet Dropped / Factory WiFi Cut"| C_OFF["Factory Connectivity Offline:<br/>Terminal Outbox activated automatically."]:::cause
    C_OFF --> F_OFF["💾 Zero Data Loss Guarantee:<br/>Mutations are safely buffered in local IndexedDB.<br/>They automatically flush to the cloud when WiFi reconnects."]:::fix

    %% Branch 6: Any Unknown / General Error
    SYMPTOM -->|"Error Banner with Support Reference"| C_TRACE["Error banner displays reference code:<br/><code>Transaction failed. Support reference: [req_xxxxxxxxxxxx]</code>"]:::trace
    C_TRACE --> F_TRACE["🔍 Instant Cloud Trace Action:<br/>1. Copy reference code (e.g. <code>req_8f1a3b2c4d5e</code>).<br/>2. Open Render Cloud Backend Logs.<br/>3. Search for <code>request_id</code> to view the full structured JSON trace and Python exception!"]:::trace

    linkStyle default stroke:#475569,stroke-width:2px;
```

---

### 🚨 Emergency Triage Matrix & Quick Commands

| Error / State | Root Cause | Immediate 10-Second Remediation |
| :--- | :--- | :--- |
| <kbd>HTTP 504</kbd> **Cold Start** | Render free-tier container suspended after 15 min idle | Run: `curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health` (Warms container in 15s). |
| <kbd>HTTP 401</kbd> **Session Expired** | JWT session token expired after 24h session window | Click **Demo Admin** on the login screen to re-authenticate with full credentials. |
| <kbd>HTTP 403</kbd> **Viewer Lockout** | User session is scoped to read-only `viewer` role | Switch persona to `editor` or click **Demo Admin** (`admin_demo`) to perform mutations. |
| <kbd>HTTP 422</kbd> **Stock Barrier** | Pessimistic stock boundary: Requested quantity > Available pairs | Open **Stock Report**, check size inventory, and log a production batch (+IN) before dispatch. |
| <kbd>HTTP 409</kbd> **Sequence Conflict** | Monotonic invoice sequence collision under simultaneous billing | The API retries 3 times automatically. If retries exhaust, click **Create Invoice** once more. |
| <kbd>OFFLINE</kbd> **Network Dropped** | Factory floor WiFi or cellular backup dropped | Do not reload: The **Terminal Outbox** buffers mutations and will auto-flush upon reconnect. |
| <kbd>TRACE</kbd> **Unknown Exception** | Backend application exception during transaction | Copy support reference `[req_xxxxxxxxxxxx]` from the UI and grep Render cloud logs. |

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
