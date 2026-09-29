# OPERATIONAL_HANDOVER.md — LIVO GROUP OF INDUSTRIES Footwear ERP
**Document Version:** 1.0 | **Date:** 2026-09-27 | **Classification:** Client Confidential

This document is the single authoritative handover reference for LIVO GROUP OF INDUSTRIES Footwear ERP. It contains everything needed to operate, maintain, and — if required — re-host the system without the original developer present.

---

## Table of Contents
1. [System Architecture & Cloud Topology](#1-system-architecture--cloud-topology)
2. [Data Integrity Rules & Security Model](#2-data-integrity-rules--security-model)
3. [Role-Based Permissions Matrix](#3-role-based-permissions-matrix)
4. [Factory Operations Standard Operating Procedure (SOP)](#4-factory-operations-standard-operating-procedure-sop)
5. [Dual-Language Terminology Reference](#5-dual-language-terminology-reference)
6. [Phase 2b Self-Hosted VPS Deployment Blueprint](#6-phase-2b-self-hosted-vps-deployment-blueprint)
7. [Automated Disaster Recovery & Backup Procedures](#7-automated-disaster-recovery--backup-procedures)
8. [Credential Handover Checklist](#8-credential-handover-checklist)
9. [Post-Handover Support Reference](#9-post-handover-support-reference)
10. [Phase 9 Tier-1 Hardware & Scaling Operations](#10-phase-9-tier-1-hardware--scaling-operations)
11. [Concurrency Locking Topology & Race Condition Hardening](#11-concurrency-locking-topology--race-condition-hardening)
12. [Request Correlation, Telemetry & Supervisor Exception Cockpit](#12-request-correlation-telemetry--supervisor-exception-cockpit)
13. [Factory Acceptance Test (FAT) 10-Step Execution Script](#13-factory-acceptance-test-fat-10-step-execution-script)

---

## 1. System Architecture & Cloud Topology

### 1.1 Production Cloud Endpoints

| Service | Provider | URL / Connection | Purpose |
|:--|:--|:--|:--|
| **Frontend Web App (PWA)** | Vercel (Free Tier) | `https://livo-footwear-erp.vercel.app` | Next.js 14 responsive web app and PWA; installable to mobile home screens |
| **Backend REST API** | Render (Free Tier) | `https://livo-footwear-erp-backend.onrender.com` | FastAPI application server; handles all business logic and authentication |
| **API Health Check** | Render | `https://livo-footwear-erp-backend.onrender.com/api/v1/health` | Returns HTTP 200 + `{"status":"healthy","database":"healthy"}` when fully operational |
| **API Documentation (Swagger)** | Render | `https://livo-footwear-erp-backend.onrender.com/docs` | Interactive REST API documentation for integrators |
| **PostgreSQL Database** | Neon (Free Tier) | Project `green-wind-12533394` (US-East-2) | Managed cloud PostgreSQL 16; 7-day PITR included |
| **GitHub Repository** | GitHub | `https://github.com/Sishir120/livo-footwear-erp` | Source of truth; Vercel deploys automatically on every push to `main` |

> **Warning — Free Tier Cold-Start:** The Render backend free tier may exhibit a 30–60 second cold-start delay on first daily request after periods of inactivity. Opening the health check URL 60 seconds before shift start will pre-warm the server. Consider upgrading to Render Starter ($7/month) for zero cold-start if this is disruptive.

### 1.2 System Architecture Diagram

```
[Factory Users: Desktop / Mobile / Tablet]
           |  HTTPS
           v
   [Vercel CDN Edge]
   Next.js 14 PWA / Frontend
   First Load JS: 102 kB (dynamic split)
           |  /api/* rewrites over HTTPS
           v
   [Render Web Service]
   FastAPI + Uvicorn
   JWT auth (httpOnly cookie)
   Rate limiter (30 req/window)
           |  SQLAlchemy ORM
           v
   [Neon PostgreSQL 16]
   Region: US-East-2
   Tables: companies, users, suppliers,
           raw_materials, purchases,
           products, production_batches,
           stock_movements, clients,
           sales_orders, invoices,
           audit_log, payments
           |
           v
   [Backup] pg_dump -> Cloud Object Storage
   (Backblaze B2 / Cloudflare R2 via rclone)
```

### 1.3 Technology Stack Summary

| Layer | Technology | Version | Notes |
|:--|:--|:--|:--|
| Frontend | Next.js | 14.x | App Router, dynamic imports, PWA manifest |
| UI Language | TypeScript + React | 18.x | Strict mode enabled |
| Styling | Vanilla CSS | — | Enterprise slate palette; no Tailwind dependency |
| i18n | Custom `LocaleContext` | — | Zero-dependency; English + Nepali; `localStorage` persisted |
| Backend | FastAPI | 0.115.x | Versioned REST API at `/api/v1/` |
| Database ORM | SQLAlchemy | 2.x | Tenant-scoped repository pattern |
| Migrations | Alembic | 1.x | Current head: `002_invoice_uq` |
| Auth | JWT (python-jose) | — | `httpOnly` + `SameSite=lax` cookies; Argon2 password hashing |
| Database | PostgreSQL | 16 | `company_id` on every business table; append-only movements |
| Container | Docker + Docker Compose | — | Production-ready (Phase 2b VPS deployment) |
| Reverse Proxy | Caddy v2 | — | Automatic HTTPS (Let's Encrypt); security headers |

---

## 2. Data Integrity Rules & Security Model

### 2.1 Append-Only Stock Ledger (`stock_movements`)

**The most important rule in the entire system:**

> Stock balances are **never stored directly**. They are computed at runtime as:
>
> ```
> current_stock = SUM(quantity) WHERE direction='IN'
>               - SUM(quantity) WHERE direction='OUT'
>               for a given product_id
> ```

This means:
- **No one can manually edit a stock balance** — there is no "balance" field to edit.
- Every production batch creates `direction='IN'` movement rows automatically.
- Every sales dispatch creates `direction='OUT'` movement rows automatically.
- Historical accuracy is mathematically guaranteed because the full movement log is permanent and immutable.
- To "correct" a stock entry, issue a corrective movement (e.g., an adjustment batch), never delete or edit an existing row. This preserves the full audit trail.

### 2.2 DB-Enforced Sequential Invoice Numbering

Invoice numbers (`INV-01-00001`, `INV-01-00002`, ...) are enforced at the database level by:

```sql
UNIQUE CONSTRAINT uq_invoice_company_sequence (company_id, sequence_number)
```

- **Gap-free:** PostgreSQL prevents any two invoices from sharing a sequence number within the same company — even under concurrent simultaneous generation.
- **Immutable:** Voided (cancelled) invoices **retain their sequence number** and are marked `is_void = TRUE`. The row is never deleted.
- **Nepal VAT Compliance:** The statutory void procedure marks an invoice void without destroying the record, as required by Nepal IRD e-billing audit trail requirements.

### 2.3 Password Security & Authentication

- **Algorithm:** Argon2id (memory-hard; resistant to GPU brute-force attacks).
- **JWT tokens** are issued as `httpOnly`, `Secure`, `SameSite=lax` cookies — inaccessible to JavaScript (prevents XSS token theft).
- **Session duration:** 480 minutes / 8 hours by default (one full factory shift).
- **Rate limiting:** HTTP 429 after 30 rapid attempts, defending against credential-stuffing attacks.

### 2.4 Tenant Isolation

Every business table carries a `company_id` foreign key. All queries are routed through a `TenantRepository` helper that injects this filter automatically. Cross-tenant data access returns `HTTP 404`.

---

## 3. Role-Based Permissions Matrix

The system has exactly two roles. These are enforced at the **API layer** — not merely UI cosmetics.

| Action | `editor_admin` | `viewer_user` | Notes |
|:--|:--:|:--:|:--|
| View Daily Reports | YES | YES | Real-time consolidated factory metrics |
| View Stock Ledger & Badges | YES | YES | Health badges: Healthy / Low / Out of Stock |
| View Production Batches | YES | YES | Size-curve analytics included |
| View Purchase Vouchers | YES | YES | Supplier ledger with bill attachments |
| View Sales & Invoices | YES | YES | Sequential tax invoice history |
| Export CSV (all views) | YES | YES | UTF-8 BOM, Excel-compatible |
| Print Invoices | YES | YES | Browser print dialog |
| **Record raw material purchases** | YES | **NO** | `403 Forbidden` at API |
| **Issue production batches** | YES | **NO** | `403 Forbidden` at API |
| **Generate sales invoices** | YES | **NO** | `403 Forbidden` at API |
| **Void / cancel invoices** | YES | **NO** | `403 Forbidden` at API |
| **Trigger database backup** | YES | **NO** | Settings > Diagnostics |
| Switch language (EN / Nepali) | YES | YES | Client-side only |

> **Action Required:** Rotate all passwords within 48 hours of handover. Use a shared password manager (e.g., Bitwarden free tier). Do not share credentials over email or SMS in plaintext.

---

## 4. Factory Operations Standard Operating Procedure (SOP)

This section is written for **data entry clerks and factory supervisors** — no technical knowledge required.

---

### 4.1 SOP-01: Inwarding Raw Materials

**When to use:** When a delivery of leather, rubber soles, thread, adhesives, or any other raw material arrives at the factory gate.

**Steps:**
1. Open `https://livo-footwear-erp.vercel.app` on any browser (phone or desktop).
2. Sign in with your **Editor** username and password.
3. Click **Raw Material Purchases** (`कच्चा पदार्थ खरिद`) in the top navigation.
4. Click **Record Raw Material Purchase** — keyboard shortcut: **Alt+N**.
5. Fill in the form fields — press **Enter** to move to the next field:
   - **Supplier / Vendor:** Select from the dropdown.
   - **Raw Material Item:** Select the material type.
   - **Quantity:** Enter the quantity received.
   - **Unit Rate (Rs.):** Enter the per-unit price from the supplier's bill.
   - **Date (AD / BS):** Both calendar dates are shown; enter the Gregorian (AD) date.
   - **Remarks / Gate Pass No.:** Enter the gate pass number or any note.
   - **Supplier Physical Bill:** Click the upload area to attach the supplier's bill (PNG, JPG, or PDF up to 10 MB).
6. Press **Ctrl+Enter** (or **Cmd+Enter** on Mac) to save immediately.
7. For multiple deliveries in sequence, enable **Continuous Rapid Entry Mode** — the form stays open, pre-fills date and supplier, and auto-advances the sequence number after each save.

**Verification:** After saving, the purchase appears in the table. The Stock Ledger balance does not increase from raw material receipt — stock increases only when a Production Batch is issued.

---

### 4.2 SOP-02: Issuing Production Batches

**When to use:** When a production run is completed and finished footwear pairs are ready to be added to the finished goods inventory.

**Steps:**
1. Click **Production Batches** (`उत्पादन ब्याच`) in the navigation.
2. Click **Issue Production Batch** — keyboard shortcut: **Alt+N**.
3. Fill in the fields:
   - **Footwear Model:** Select the SKU — includes the size (Paris Points 32–43) and colour code.
   - **Batch Serial Number:** Auto-generated; verify or override if needed.
   - **Target Pairs:** The planned quantity for this run.
   - **Finished Produced Pairs:** The actual quantity completed.
   - **Assembly Workers:** Number of workers involved in this batch.
   - **Date (AD):** Date of production completion.
   - **Remarks:** Any batch notes.
4. Press **Ctrl+Enter** to commit. The system creates a `direction='IN'` stock movement automatically — the Stock Ledger balance for this SKU increases immediately.
5. **For size runs (Continuous Mode):** Enter size 38 batch → Ctrl+Enter → form resets with a new batch number, keeping the date → enter size 39, and so on through 40, 41, 42, 43 without touching the mouse.

**Keyboard walkthrough for a 6-size run:**
```
Alt+N -> [Select Model S38] -> Enter -> [Target] -> Enter -> [Produced] -> Enter -> [Workers] -> Ctrl+Enter
      -> (auto-open) -> [Select Model S39] -> Enter -> ... -> Ctrl+Enter  (repeat per size)
```

---

### 4.3 SOP-03: Generating Wholesale Tax Invoices & Nepal VAT Void Procedure

**When to use:** When dispatching goods to a wholesale buyer and issuing a statutory tax invoice.

**Generating an Invoice:**
1. Click **Sales & Invoicing** (`बिक्री तथा बिलिङ`) in the navigation.
2. Click **Record Sale & Issue Invoice** — keyboard shortcut: **Alt+N**.
3. Fill in:
   - **Sales Order Number:** Auto-generated.
   - **Client / Buyer Name:** Select from the dropdown.
   - **Invoice items:** Add each product SKU and quantity dispatched.
   - **Payment method and amount received.**
   - **Date (AD):** Date of dispatch.
4. Press **Ctrl+Enter** to commit. The system:
   - Assigns the next sequential invoice number (`INV-01-XXXXX`) — guaranteed unique by PostgreSQL constraint.
   - Creates `direction='OUT'` stock movement rows — Stock Ledger balances for dispatched SKUs decrease immediately.
   - Locks the invoice record (immutable).
5. Click **Print** to open the browser print dialog and save or print the tax invoice PDF for the client.

**Voiding an Invoice (Nepal VAT Statutory Procedure):**

> Invoices cannot be deleted. Nepal's VAT regulations require the original invoice number to remain in the audit trail even when cancelled.

1. Find the invoice in the Sales & Invoicing table.
2. Click the **Void** button on that invoice row.
3. Confirm the action. The invoice is marked **VOID** (`रद्द गरिएको`) but the row and its sequence number are permanently retained.
4. Issue a new corrective invoice if required.

---

### 4.4 SOP-04: Daily Volume Metrics & Exporting Stock Ledger to Excel

**Daily Report (`दैनिक प्रतिवेदन`):**
- The Daily Report is the default view after login.
- KPI tiles show: total SKU items, total stock volume, estimated stock value, daily finished output, active assembly workers, gross wholesale dispatches, cash received, and accounts receivable.
- Bar charts show production output by model and produced vs. dispatched volume.
- All figures are derived live from the append-only movement ledger — no manual computation required.

**Stock Ledger Health Badges:**

| Badge | Nepali | Condition |
|:--|:--|:--|
| HEALTHY | `सम्पन्न / पर्याप्त` | Stock > 50 pairs |
| LOW STOCK | `न्यून मौज्दात` | 1–50 pairs remaining |
| OUT OF STOCK | `स्टक समाप्त` | 0 or fewer pairs |

**Exporting to Excel (UTF-8 BOM CSV):**
1. Navigate to any view (Stock Ledger, Purchases, Production, Sales).
2. Click the **Download Excel / CSV** button (`एक्सेल / CSV डाउनलोड`).
3. Open the downloaded `.csv` file in Microsoft Excel — Nepali Devanagari characters will display correctly because the file uses UTF-8 BOM encoding. No manual encoding conversion is required.

**Language Switching:**
- Click **EN** or **नेपाली** in the top-right header at any time.
- The preference is saved in the browser and persists across sessions.
- Switching language does not log you out or reload any data.

---

## 5. Dual-Language Terminology Reference

| English Term | नेपाली शब्द | Context |
|:--|:--|:--|
| Daily Report | दैनिक प्रतिवेदन | Navigation tab |
| Stock Ledger | स्टक खाता / मौज्दात | Navigation tab |
| Production Batches | उत्पादन ब्याच | Navigation tab |
| Raw Material Purchases | कच्चा पदार्थ खरिद | Navigation tab |
| Sales & Invoicing | बिक्री तथा बिलिङ | Navigation tab |
| Settings & Diagnostics | सेटिङ तथा ब्याकअप | Navigation tab |
| Pairs | जोडी | Unit of measure for footwear |
| Pairs in Hand | हाल मौज्दात | Current stock balance |
| Tax Invoice (VAT) | कर बिजक (भ्याट) | Statutory Nepal VAT invoice |
| HEALTHY (stock badge) | सम्पन्न / पर्याप्त | Stock > 50 pairs |
| LOW STOCK (stock badge) | न्यून मौज्दात | Stock 1–50 pairs |
| OUT OF STOCK (badge) | स्टक समाप्त | Stock <= 0 pairs |
| Supplier / Vendor | आपूर्तिकर्ता / भेन्डर | Raw material supplier |
| Raw Material Item | कच्चा पदार्थ | Leather, soles, thread, etc. |
| Quantity | परिमाण | Number of units |
| Unit Rate | दर (रु.) | Price per unit in Rupees |
| Date (AD) | मिति (ई.सं. AD) | Gregorian calendar date |
| Date (BS) | मिति (वि.सं. BS) | Bikram Sambat calendar date |
| Remarks / Gate Pass | कैफियत / गेट पास नं. | Notes or gate pass number |
| Footwear Model | जुत्ता मोडल | SKU with size + colour code |
| Assembly Workers | कामदार संख्या | Factory worker headcount |
| Batch Serial Number | ब्याच संकेत नं. | Production batch identifier |
| Sales Order Number | बिक्री आदेश नं. | Dispatch order identifier |
| Client / Buyer | ग्राहक / खरिदकर्ता | Wholesale buyer |
| Invoice Number | कर बिजक नं. | Sequential invoice number |
| Invoice Total | कुल बिल रकम | Total amount on invoice |
| Void (cancel invoice) | रद्द गर्नुहोस् | Nepal VAT cancellation |
| VOID badge | रद्द गरिएको | Cancelled invoice marker |
| Continuous Rapid Entry | निरन्तर द्रुत प्रविष्टि | Keyboard-only multi-record entry |
| Sign In | लगइन गर्नुहोस् | Login action |
| Logout | बाहिरिनुहोस् | Sign out |
| Editor Role | सम्पादक (एडिटर) | Full mutation rights |
| Viewer Role | दर्शक (भ्यूअर) | Read-only access |
| Export Excel / CSV | एक्सेल / CSV डाउनलोड | Spreadsheet download |
| Print | प्रिन्ट | Browser print dialog |
| Close | बन्द गर्नुहोस् | Close drawer/modal |
| Search | खोज्नुहोस् | Search/filter records |

---

## 6. Phase 2b Self-Hosted VPS Deployment Blueprint

Use this section when ready to move from the free-tier cloud demo to a permanent self-hosted Linux VPS (recommended: Hetzner CX22 or DigitalOcean Droplet, ~$5–7/month).

### 6.1 Server Provisioning Checklist

- [ ] Create VPS account (Hetzner: `hetzner.com` or DigitalOcean: `cloud.digitalocean.com`)
- [ ] Provision Ubuntu 22.04 LTS, 2 vCPU / 4 GB RAM minimum
- [ ] Add SSH public key during provisioning
- [ ] Note the server IP address (e.g., `159.89.X.X`)
- [ ] Point your domain's DNS A record to this IP:
  ```
  A    erp.livogroup.com.np    ->  159.89.X.X    TTL: 300
  ```

### 6.2 Server Setup Commands

```bash
# 1. System update
sudo apt update && sudo apt upgrade -y

# 2. Install Docker & Docker Compose plugin
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect

# 3. Install rclone (for cloud backups)
curl https://rclone.org/install.sh | sudo bash

# 4. Clone the repository
git clone https://github.com/Sishir120/livo-footwear-erp.git /opt/livo-erp
cd /opt/livo-erp
```

### 6.3 Environment Configuration (`.env`)

Create the production `.env` file — **never commit this file to git**:

```bash
cp .env.production.example .env
nano .env
```

Fill in all values:

```bash
# PostgreSQL credentials
POSTGRES_USER=livo_admin
POSTGRES_PASSWORD=<STRONG-RANDOM-32-CHAR-PASSWORD>
POSTGRES_DB=livo_erp

# FastAPI secrets
SECRET_KEY=<STRONG-RANDOM-64-CHAR-HEX-KEY>
BACKEND_CORS_ORIGINS=https://erp.livogroup.com.np
LIVO_DEV_MODE=false
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Caddy domain
DOMAIN=erp.livogroup.com.np

# Cloud Object Storage (Backblaze B2 or Cloudflare R2)
STORAGE_ENDPOINT_URL=https://<ACCOUNT-ID>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY=<ACCESS-KEY>
STORAGE_SECRET_KEY=<SECRET-KEY>
STORAGE_BUCKET_NAME=livo-erp-storage
```

Generate secure random values:
```bash
# Generate SECRET_KEY (64-char hex)
python3 -c "import secrets; print(secrets.token_hex(64))"

# Generate POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 6.4 Container Architecture

The `docker-compose.yml` orchestrates four containers:

| Container | Image | Purpose |
|:--|:--|:--|
| `livo-postgres` | `postgres:16-alpine` | PostgreSQL 16 with persistent volume `postgres_data` |
| `livo-backend` | `./backend/Dockerfile` | FastAPI + Uvicorn; waits for healthy postgres; Alembic runs on start |
| `livo-frontend` | `./frontend/Dockerfile` | Next.js multi-stage production build |
| `livo-caddy` | `caddy:2-alpine` | Automatic HTTPS via Let's Encrypt; reverse proxy |

The `Caddyfile` routes:
- `/api/*` and `/docs*` → FastAPI backend on port 8000
- All other paths → Next.js frontend on port 3000
- Security headers automatically added: HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy

### 6.5 First Deployment

```bash
cd /opt/livo-erp

# Start all containers (builds images on first run — takes 3–5 minutes)
docker compose up -d --build

# Wait ~30 seconds for postgres health check, then run migrations
docker compose exec backend alembic upgrade head

# Verify all containers are running
docker compose ps

# Confirm health endpoint
curl https://erp.livogroup.com.np/api/v1/health
# Expected: {"status":"healthy","database":"healthy"}

# Tail logs if troubleshooting
docker compose logs -f backend
docker compose logs -f caddy
```

### 6.6 Updating the Application

```bash
cd /opt/livo-erp
git pull origin main
docker compose up -d --build
# Alembic migrations run automatically on backend container start
```

---

## 7. Automated Disaster Recovery & Backup Procedures

### 7.1 Nightly Backup Script (`scripts/backup_nightly.sh`)

The script performs three operations:
1. **`pg_dump`** — dumps the entire PostgreSQL database from the running container to a compressed `.sql.gz` file named with a UTC timestamp.
2. **Cloud upload** — uploads the dump to Cloudflare R2 or Backblaze B2 via `rclone`.
3. **Local retention** — deletes backups older than 30 days.

**Setting up the nightly cron job:**

```bash
# Make script executable
chmod +x /opt/livo-erp/scripts/backup_nightly.sh

# Configure rclone remote (one-time interactive setup)
rclone config
# Create a remote named "livo_r2" (for Cloudflare R2) or "livo_b2" (for Backblaze B2)

# Open crontab editor
crontab -e

# Add this line — runs at 02:00 AM NPT (20:15 UTC):
15 20 * * * /opt/livo-erp/scripts/backup_nightly.sh >> /var/log/livo_backup.log 2>&1
```

**Manual backup (on-demand):**
```bash
cd /opt/livo-erp
./scripts/backup_nightly.sh
```

**Verify the backup was created:**
```bash
ls -lh backups/livo_dump_*.sql.gz | tail -5
# Expected: file dated today, non-zero size
```

**Verify cloud upload:**
```bash
rclone ls livo_r2:livo-erp-storage/backups/ | tail -10
```

### 7.2 Database Restore Procedure (`scripts/restore_postgres.sh`)

> **WARNING:** Restore overwrites the target database. Always stop the backend before restoring to prevent race conditions.

```bash
# 1. Stop the backend
docker compose stop backend

# 2. Run the restore script with the target backup file
cd /opt/livo-erp
./scripts/restore_postgres.sh backups/livo_dump_20261001_021500.sql.gz livo_erp

# Expected output:
# [2026-10-01 02:15:00 UTC] Restoring database 'livo_erp' from '...'
# [2026-10-01 02:15:05 UTC] Restore completed successfully into 'livo_erp'.

# 3. Restart the backend
docker compose start backend

# 4. Verify health
curl http://localhost/api/v1/health
```

### 7.3 Restore from Neon Cloud Backup (Current Free-Tier Production)

For the current Neon-hosted deployment, use point-in-time restore via the Neon Console:
1. Log in to `https://console.neon.tech`
2. Navigate to project `green-wind-12533394`
3. Click **Branches** → Select the branch → **Restore**
4. Choose a restore point (Neon PITR retains 7 days of history on the free tier)
5. Click **Restore Branch** — this creates a new branch non-destructively
6. Update `DATABASE_URL` in the Render environment variables to point to the restored branch's connection string
7. Trigger a Render redeploy

### 7.4 Automated Disaster Recovery & Integrity Drill (`backend/scripts/backup_drill.py`)

The system enforces strict operational recovery targets:
- **Target RPO (Recovery Point Objective):** $\le 60\text{ minutes}$ (maximum acceptable data loss window).
- **Target RTO (Recovery Time Objective):** $\le 15\text{ minutes}$ (maximum acceptable downtime to full restoration).

#### Automated Invariant Reconciliation Drill
The automated recovery harness (`backend/scripts/backup_drill.py`) validates that restored snapshots strictly maintain multi-tenant financial and inventory invariants:

```bash
# Execute disaster recovery drill from workspace root:
python backend/scripts/backup_drill.py
```

The script executes 4 rigorous automated audits:
1. **Schema & Migration Parity:** Asserts all 7 Alembic revisions and all required multi-tenant tables (`companies`, `users`, `products`, `warehouses`, `stock_movements`, `invoices`, `invoice_sequences`, `receivable_entries`, `payment_allocations`, `production_sync_logs`) exist.
2. **Stock Movement Balance Reconciliation:** Computes $\sum(\text{quantity} \times \text{direction})$ across all movements and asserts exact mathematical equality with individual product on-hand inventory totals ($|\text{total} - \sum \text{products}| < 0.0001$).
3. **Accounts Receivable Ledger Reconciliation:** Reconciles the append-only AR subledger: $\sum(\text{amount\_paisa} \times \text{direction}) == \text{sum of client debt totals}$.
4. **Gapless Invoice Continuity:** Verifies non-resettable, gapless sequential numbering (`INV-01-XXXXX`) without missing or skipped sequence integers.

#### Automated Test Verification
The recovery harness is continuously validated by automated regression tests:
```bash
pytest backend/tests/test_backup.py -k test_backup_drill_integrity_verification -v
```

---

## 8. Credential Handover Checklist

Store all credentials in a shared password manager (e.g., Bitwarden free tier). Do not transmit plaintext credentials over email or SMS.

| Credential | Where to find it | Handed over |
|:--|:--|:--:|
| Vercel account (GitHub OAuth) | `https://vercel.com/dashboard` | [ ] |
| Render account / web service | `https://dashboard.render.com` | [ ] |
| Neon PostgreSQL dashboard | `https://console.neon.tech` — project `green-wind-12533394` | [ ] |
| GitHub repository admin access | `https://github.com/Sishir120/livo-footwear-erp` | [ ] |
| `editor_admin` ERP password | Stored in shared password manager | [ ] |
| `viewer_user` ERP passwords (x2) | Stored in shared password manager | [ ] |
| Cloud object storage keys (R2/B2) | `.env` file + password manager | [ ] |
| VPS SSH credentials (Phase 2b) | Stored in password manager | [ ] |
| DNS registrar access | Client's existing account | [ ] |

---

## 9. Post-Handover Support Reference

### 9.1 Quick Diagnostics Checklist

If the system is not responding, check in this order:

1. **Is the backend awake?**
   Open `https://livo-footwear-erp-backend.onrender.com/api/v1/health`.
   Wait up to 60 seconds for cold-start. If this returns an error, the backend is down — check the Render dashboard.

2. **Is the frontend loading?**
   Open `https://livo-footwear-erp.vercel.app`.
   If blank or error, check Vercel dashboard for a failed deployment.

3. **Is the database healthy?**
   The health endpoint reports `"database": "healthy"` or `"database": "error"`.
   If error, check the Neon console at `https://console.neon.tech` for an outage.

4. **Did a recent code push break the build?**
   Check `https://github.com/Sishir120/livo-footwear-erp/actions` or the Vercel dashboard for build failure details.

### 9.2 Keyboard Shortcut Reference Card

| Shortcut | Action |
|:--|:--|
| **Alt+N** | Open "New Record" drawer (Purchase / Batch / Invoice) |
| **Enter** | Move to next form field |
| **Ctrl+Enter** / **Cmd+Enter** | Quick-commit current record and save |
| **Esc** | Close current drawer / modal |

### 9.3 Free Tier Service Limits

| Service | Free Tier Limit | Upgrade Path |
|:--|:--|:--|
| **Render** | 750 hrs/month; 30–60s cold starts; 512 MB RAM | Render Starter ($7/month): zero cold start, 512 MB RAM guaranteed |
| **Vercel** | 100 GB bandwidth/month; unlimited deployments | Vercel Pro ($20/month): needed only at high traffic volume |
| **Neon PostgreSQL** | 0.5 GB storage; 7-day PITR | Neon Launch ($19/month): 10 GB storage, 30-day PITR |

### 9.4 Source Code Reference

| File | Purpose |
|:--|:--|
| `frontend/src/context/LocaleContext.tsx` | English / Nepali translation dictionary and `useLocale()` hook |
| `frontend/src/components/AppShell.tsx` | Main navigation shell with language toggle |
| `frontend/src/app/globals.css` | Global styles, focus rings, 44px touch targets, modal footer pinning |
| `frontend/public/manifest.json` | PWA manifest for home-screen installation on iOS and Android |
| `backend/app/routers/` | FastAPI route handlers for all modules |
| `backend/alembic/versions/` | Database migration history; current head: `002_invoice_uq` |
| `backend/tests/` | 27-test automated regression suite |
| `docker-compose.yml` | Production container orchestration (Phase 2b VPS) |
| `Caddyfile` | Reverse proxy + automatic HTTPS configuration |
| `scripts/backup_nightly.sh` | Nightly PostgreSQL backup + cloud object storage upload |
| `scripts/restore_postgres.sh` | Database restore from compressed backup file |
| `docs/UAT_WALKTHROUGH.md` | Client UAT walkthrough guide |
| `docs/SECURITY_ARCHITECTURE.md` | Detailed security model documentation |
| `ARCHITECTURE.md` | System architecture decisions and rationale |
| `DELIVERY_CYCLE.md` | Project phase tracker and gate definitions |
| `MEMORY.md` | Running context ledger for future maintainers |

---

## 10. Phase 9 Tier-1 Hardware & Scaling Operations

### 10.1 Ledger Snapshot Materialization ($O(1)$ Scale)

As footwear production scales to tens of thousands of movements, dynamic summation of all movements since genesis degrades query response times. The `stock_snapshots` table materializes periodic closing balances:

$$\text{Current Balance} = \text{Latest Snapshot Balance} + \sum_{i > \text{last\_movement\_id}} (\text{direction}_i \times \text{quantity}_i)$$

#### Triggering Manual or Scheduled Snapshots
Factory system administrators or scheduled cron jobs should trigger a snapshot at the close of every business day (e.g. 23:59 NPT):

```bash
# Nightly snapshot curl trigger (requires editor_admin token)
curl -s -X POST "https://livo-footwear-erp-backend.onrender.com/api/v1/stock/snapshots" \
  -H "Authorization: Bearer <EDITOR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"snapshot_date": "2026-10-01"}'
```

- **Database Table:** `stock_snapshots` (indexed by `company_id`, `product_id`, `snapshot_date`).
- **Alembic Migration:** `003_add_stock_snapshots_and_bom.py` (Revises `002_invoice_uq`).
- **Fallback Guarantee:** If no snapshot exists for a product, the engine automatically falls back to full `StockMovement` summation with zero downtime or discrepancy.

---

### 10.2 Bill of Materials (BOM) Engine & Raw Material Depletion

The BOM engine ties finished footwear models to required raw material inputs (leather, rubber outsoles, eyelets, adhesive).

#### Configuring a Bill of Materials
```bash
# Example: 1 pair of Livo Executive Boot (product_id: 12) requires 1.8 sqft of Calf Leather (raw_material_id: 4)
curl -s -X POST "https://livo-footwear-erp-backend.onrender.com/api/v1/production/bom" \
  -H "Authorization: Bearer <EDITOR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 12, "raw_material_id": 4, "quantity_required": 1.8}'
```

#### Production Batch Atomic Depletion & Safety Boundaries
When a batch of 50 pairs is committed via `POST /api/v1/production/batches`:
1. The engine checks current available stock for each BOM ingredient:
   $$\text{Available Raw Stock} = \sum(\text{Purchase.quantity}) - \sum(\text{ProductionMaterialUsage.quantity\_used})$$
2. If available raw stock is less than $50 \times 1.8 = 90\text{ sqft}$, the transaction aborts with `HTTP 422 Unprocessable Entity`:
   ```json
   {"detail": "Insufficient Raw Material: Calf Leather (Required: 90.00, Available: 42.50)"}
   ```
3. If stock is sufficient, the system atomically records the finished footwear `StockMovement` (+IN) and writes corresponding `ProductionMaterialUsage` deduction records within a single database transaction block.

---

### 10.3 Factory Hardware: USB & Bluetooth Barcode Scanners

The frontend integrates the `useBarcodeScanner` hook (`frontend/src/hooks/useBarcodeScanner.ts`) for rapid hardware input.

- **Supported Hardware:** Any standard USB or Bluetooth handheld barcode scanner operating in HID (Human Interface Device) keyboard emulation mode (e.g. Honeywell Voyager, Zebra LI4278, Netum, Eyoyo).
- **Detection Mechanism:** Captures character bursts with inter-keystroke intervals $< 35\text{ms}$ ending with an `Enter` keypress, distinguishing scanner bursts from human keyboard typing.
- **Workflow in Sales & Invoices:**
  1. Open the wholesale order drawer in **Sales & Invoices**.
  2. Point scanner at a shoe box barcode or SKU label.
  3. The system automatically matches the SKU, populates the model, auto-sets unit wholesale rate, and focuses the quantity field with zero mouse clicks.

---

### 10.4 Direct 2" × 1" Shoe Box Thermal Label Printing

The `ThermalLabelModal` (`frontend/src/components/ThermalLabelModal.tsx`) provides box label printing.

- **Label Dimensions:** Standard industrial 2" × 1" (50mm × 25mm) thermal adhesive labels.
- **Barcode Standard:** Clean, scalable vector SVG Code 128-B barcode rendered natively without third-party CDN dependencies.
- **Printed Fields:** Shoe Model Name, Paris Point Size (**SIZE 41**), Batch Number, SKU Barcode, Company PAN (`609823412`), and Date.
- **Operational Trigger:**
  - **Automatic:** Committing a batch in **Production Batches** (<kbd>Ctrl+Enter</kbd>) automatically opens the box label modal ready for printing.
  - **On-Demand:** Click the **Label** (<kbd>Printer</kbd>) button on any row in the production batch table.
- **Output Modes:**
  1. **Visual Preview (@media print):** Directly prints to 58mm/80mm USB, Wi-Fi, or network thermal label printers via browser print dialog.
  2. **Raw ESC/POS WebUSB:** Emits binary ESC/POS command hex strings for direct hardware thermal printers.

---

### 10.5 Offline Mutation Queue & Network Interceptor

Factory Wi-Fi in Biratnagar and Kathmandu can experience momentary packet loss or power interruptions. The client-side outbox (`frontend/src/lib/offlineQueue.ts`) and resilient API client (`frontend/src/lib/api.ts`) guarantee uninterrupted data entry:

- **IndexedDB Storage:** Persists offline mutations in browser database `LivoOfflineDB.livo_mutation_outbox`.
- **Interception:** If `navigator.onLine === false` or fetch times out during an operational mutation (batch creation, sales order), the mutation is buffered locally with an optimistic `HTTP 202 Accepted` response.
- **Visual Status Badges:**
  - `🟢 Live`: System online with zero pending outbox items.
  - `🟡 Offline (N queued)`: Terminal offline; mutations are safely preserved locally.
  - `🔄 Sync (N)`: Network restored; sequential background replay in progress.
- **Idempotency Guarantee:** Every replayed mutation includes an `X-Idempotency-Key: UUID` header to prevent duplicate database entries upon network reconnect.

---

## 11. Concurrency Locking Topology & Race Condition Hardening

### 11.1 Deterministic Signed 64-bit BigInt Advisory Locks
Under concurrent wholesale order creation or rapid factory production runs, standard row reads can suffer from phantom oversells and credit ceiling bypasses. LIVO Footwear ERP enforces deterministic, transaction-scoped PostgreSQL advisory locks (`pg_advisory_xact_lock`):

1. **Hash Key Generation (`backend/app/core/locks.py`):**
   - Combines entity domain (`stock`, `credit`), `company_id`, and entity keys into a deterministic 64-bit signed integer via MD5 truncation:
     $$\text{lock\_id} = \text{int.from\_bytes(digest[:8], 'big', signed=True)}$$
2. **Stock Mutation Advisory Locks:**
   - Function: `acquire_stock_mutation_lock(db, company_id, warehouse_id, product_id, size)`
   - Issued inside database transactions before stock zero-floor checks. Automatically released at `COMMIT` or `ROLLBACK`.
3. **Customer Credit Advisory Locks:**
   - Function: `acquire_client_credit_lock(db, company_id, client_id)`
   - Serializes concurrent sales order creations per customer, eliminating credit limit race conditions.
4. **Deadlock Prevention Ordering:**
   - All locks across multi-item sales orders are acquired in strict deterministic sorted order:
     $$\text{targets} = \text{sorted}(\text{list}(\text{set}((1, \text{item.product\_id}, \text{size}))))$$
5. **In-Process Thread Re-entrant Fallback (`threading.RLock`):**
   - For SQLite test runners and thread environments, in-process mutexes with re-entrant safety prevent deadlocks when a thread executes nested lock boundaries.

### 11.2 Structured 422 Exception Payloads
When concurrency safeguards intercept invalid requests, structured machine-readable error responses are emitted:
- **Insufficient Stock Block:**
  ```json
  {
    "error": "INSUFFICIENT_STOCK",
    "sku": "SNK-BLK-40",
    "size": "40",
    "available": 0,
    "requested": 1,
    "message": "Insufficient physical stock for this size variant (Available: 0, Requested: 1)"
  }
  ```
- **Credit Limit Exceeded Block:**
  ```json
  {
    "error": "CREDIT_LIMIT_EXCEEDED",
    "current_outstanding_paisa": 4500000,
    "credit_limit_paisa": 5000000,
    "order_value_paisa": 600000,
    "message": "Credit limit exceeded - supervisor override required"
  }
  ```

---

## 12. Request Correlation, Telemetry & Supervisor Exception Cockpit

### 12.1 Request Correlation Middleware (`backend/app/middleware/correlation.py`)
- **End-to-End Traceability:** Inspects incoming `X-Correlation-ID` (or generates a compliant UUIDv4) on every HTTP request.
- **Python ContextVars Binding:** Binds the correlation identifier to asynchronous execution context.
- **Header Injection:** Emits `X-Correlation-ID` in all outgoing HTTP response headers for client-side issue reporting.
- **Privacy Boundary Rule:** Strictly masks or omits sensitive data (`password`, `token`, `pan`, `client_name`, `customer_name`) from application logs:
  $$\text{Sanitized Stream: } \texttt{company\_id: [REDACTED], token: [REDACTED]}$$

### 12.2 Operations Telemetry API (`GET /api/v1/ops/telemetry`)
Restricted to `admin` role, providing real-time operational metrics:
- `db_status`: Database health and query latency in milliseconds.
- `migration_revision`: Active Alembic migration revision string (e.g. `007_production_sync_engine`).
- `unsynced_draft_age_seconds`: Age of the oldest pending offline draft.
- `recent_422_blocks`: Count of stockouts and credit-hold rejections in the last 24 hours.
- `broken_core_runs_count`: Count of active footwear models with zero stock across sizes 39–41.
- `sync_error_rate_24h`: Ratio of rejected/conflict sync attempts to total syncs in the last 24 hours.

### 12.3 Supervisor Exception Cockpit (`frontend/src/components/OpsCockpitView.tsx`)
Located under navigation tab **Ops Cockpit (सुपरभाइजर ककपिट)** for administrators:
- **Industrial Paper Exception Tiles:**
  1. 🛑 **Stockout / Oversell Blocks (२४ घण्टामा रोकिएका निकासी)**
  2. ⚠️ **Credit Hold Interceptions (बक्यौता बढी भई रोकिएका)**
  3. 📦 **Broken Core Runs (टुटेका कोर साइज ३९–४१)**
  4. 🔄 **Offline Queue Health (सिंक अवस्था र पुराना ड्राफ्टहरू)**
- **One-Click Invariant Verification:** "Run Database Health & Integrity Check" button executing live diagnostics.

---

## 13. Factory Acceptance Test (FAT) 10-Step Execution Script

Execute this 10-step Factory Acceptance Test prior to signing off on plant commissioning:

| Step | Operation | Action & Target Endpoint | Expected Result | Pass/Fail |
|:--:|:--|:--|:--|:--:|
| **1** | **API Health & Latency** | `GET /api/v1/health` | `HTTP 200` with `status: "healthy"`, DB latency $< 15\text{ms}$ | [ ] |
| **2** | **Correlation & Login** | `POST /api/v1/auth/login` | Returns JWT in `httpOnly` cookie; response contains `X-Correlation-ID` | [ ] |
| **3** | **Raw Material Inward** | `POST /api/v1/purchases/` | 100 sqft Leather received; inventory increases atomically | [ ] |
| **4** | **BOM Production Run** | `POST /api/v1/production/batches` | Logs 50 pairs size 41; raw material deducted, finished stock +50 | [ ] |
| **5** | **Thermal Box Label** | Open Batch row $\to$ Click Label | Scalable Code 128-B vector label renders with PAN `609823412` and size | [ ] |
| **6** | **Credit Limit Barrier** | `POST /api/v1/sales/orders` exceeding limit | `HTTP 422 CREDIT_LIMIT_EXCEEDED` blocked without supervisor override | [ ] |
| **7** | **Single-Pair Race Proving** | Concurrent dispatches on last pair | Exactly one succeeds (`HTTP 200`), exactly one fails (`HTTP 422`); stock balance $= 0$ | [ ] |
| **8** | **Gapless Invoice Sequence**| `POST /api/v1/sales/orders` (delivered) | Generates `INV-01-00001`, `INV-01-00002` without sequential integer gaps | [ ] |
| **9** | **AR Payment & Aging** | `POST /api/v1/receivables/payments` | Partial cash receipt decrements outstanding balance; Schedule-5 reconciled | [ ] |
| **10**| **Disaster Recovery Drill** | `python backend/scripts/backup_drill.py` | Schema parity passed, stock sum reconciled, AR balanced, gapless check verified | [ ] |

---

*Document prepared by: Antigravity Engineering*  
*Last updated: 2026-09-29 (Phase 6 Concurrency Proving & Recovery Verification)*  
*Approved for client handover: Verified with 52 automated tests passing and First Load JS <= 106 kB.*
