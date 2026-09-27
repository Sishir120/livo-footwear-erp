# CRITICAL_DEBUGGING_RUNBOOK.md — LIVO GROUP OF INDUSTRIES Footwear ERP
**Classification:** Manager / On-Call Field Manual | **Version:** 1.0 | **Date:** 2026-09-27

> This is your **live-pitch survival guide**. Every section is written to be read in under 60 seconds under pressure. No background theory — only actions, commands, and expected outcomes.

---

## QUICK TRIAGE — 5-Second Failure Isolation

Open three tabs before the presentation starts:

| Tab | URL | Expected Status |
|:--|:--|:--|
| 1. Backend Health | `https://livo-footwear-erp-backend.onrender.com/api/v1/health` | `{"status":"healthy","database":"healthy"}` |
| 2. Vercel Frontend | `https://livo-footwear-erp.vercel.app` | Loads login screen |
| 3. Neon Console | `https://console.neon.tech` | Project `green-wind-12533394` active |

---

## Component Triage Matrix

```
Something is broken. Which component?

Step 1: Does https://livo-footwear-erp.vercel.app load at all?
        NO  --> Problem is (A) Client browser / network or (B) Vercel CDN
        YES --> Go to Step 2

Step 2: Does the health check return {"status":"healthy","database":"healthy"}?
        NO  --> Problem is (C) Render backend or (D) Neon PostgreSQL
        YES --> Go to Step 3

Step 3: Does login succeed but data mutations fail with a 5xx error?
        YES --> (C) Render backend is partially degraded
        NO  --> (D) PostgreSQL connection issue -- check Neon console

Step 4: Does login fail with 401 / no session on iOS Safari?
        YES --> (B) Safari SameSite cookie issue -- see Protocol 2
```

### Symptom-to-Protocol Index

| Symptom | Likely Cause | Protocol |
|:--|:--|:--|
| Page blank / DNS error / "site can't be reached" | (A) Local network or (B) Vercel outage | Check `vercelstatus.com`; switch to mobile hotspot |
| Login screen loads, API calls time out with 504 | (C) Render cold-start | Protocol 1 |
| Login screen loads, API calls return 502 / 503 | (C) Render container crash | Protocol 1 |
| Login fails on Safari iOS; works on Chrome desktop | SameSite cookie block | Protocol 2 |
| `POST /purchase` returns HTTP 422 | Pydantic validation -- intentional boundary guard | Protocol 3 |
| `POST /sales/orders` returns HTTP 409 Conflict | Invoice sequence collision | Protocol 4 |
| Page loads, all API calls return `{"database":"error"}` | (D) Neon PostgreSQL down | Check Neon console |

---

## Protocol 1: Backend Latency / 504 Gateway Timeout

**Root cause:** Render free-tier containers spin down after 15 minutes of inactivity. Cold-start takes 30-60 seconds on first request. A 504 Gateway Timeout from the Next.js proxy is the most common presentation symptom.

### Immediate Fix (60 seconds, no tools required)

1. Open `https://livo-footwear-erp-backend.onrender.com/api/v1/health` directly in a new tab.
2. Wait. If cold-starting, this page hangs for up to 60 seconds, then returns:
   ```json
   {"status": "healthy", "database": "healthy"}
   ```
3. Once the health check responds, switch back to the main app and reload. Responses will now be instant.

### Pre-Warm Before Every Presentation

Open this URL **5 minutes before the presentation**:
```
https://livo-footwear-erp-backend.onrender.com/api/v1/health
```
Confirm the response is healthy. The backend stays warm for 15 minutes of activity.

### If the Health Check Never Responds (Container Crash)

1. Open `https://dashboard.render.com` -> your web service -> **Logs** tab.
2. Common crash reasons:
   - `SECRET_KEY must be set` -> Check environment variables in Render dashboard.
   - `psycopg2.OperationalError` -> Neon DB is unreachable (see Protocol 4).
   - `OOMKilled` -> Memory limit hit; restart manually with **Manual Deploy**.
3. Click **Manual Deploy -> Deploy Latest Commit** to force a fresh container start.

### Health Check Commands

**PowerShell (Windows):**
```powershell
Invoke-RestMethod -Uri "https://livo-footwear-erp-backend.onrender.com/api/v1/health" -Method GET
# Expected: @{status=healthy; database=healthy}
```

**curl (Linux / Mac / WSL / Git Bash):**
```bash
curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health | python3 -m json.tool
# Expected: { "status": "healthy", "database": "healthy" }

# Full latency timing diagnosis
curl -o /dev/null -s -w "DNS: %{time_namelookup}s  Connect: %{time_connect}s  TTFB: %{time_starttransfer}s  Total: %{time_total}s\n" https://livo-footwear-erp-backend.onrender.com/api/v1/health
# Cold start: Total ~45s | Warm: Total ~0.3s
```

---

## Protocol 2: Session Drop / Authentication Rejection

**Root cause:** Safari on iOS and macOS applies stricter SameSite cookie policies than Chrome. When the frontend (vercel.app) and backend (onrender.com) are on different origins, Safari may block the httpOnly auth cookie, causing 401 Unauthorized even after a successful login.

### Diagnosis: Is This a Safari/Cookie Issue?

1. Does login work on Chrome or Firefox on the same network?
   - YES -> Confirmed Safari SameSite cookie issue.
   - NO -> Not a cookie issue; check backend health (Protocol 1) first.

2. On the affected Safari browser, open Developer Tools (Safari Settings -> Advanced -> Show Develop menu):
   - Navigate to Storage -> Cookies
   - Look for `access_token` cookie on `livo-footwear-erp-backend.onrender.com`
   - If missing after login -> cookie is being blocked cross-origin.

### Immediate Workarounds (Presentation Day)

**Option A (Preferred):** Switch the presentation device to Chrome or Firefox. The ERP is fully verified on Chrome desktop and mobile Chrome.

**Option B:** Use the ERP as a full-screen PWA (Add to Home Screen):
   - On iOS Safari: Share -> Add to Home Screen -> Open the icon from home screen.
   - PWA mode uses a dedicated origin context that relaxes the SameSite restriction.

**Option C:** Switch to a different network (mobile hotspot). Corporate/campus proxy networks can strip cookies or modify SameSite headers.

### Root Technical Cause

The backend sets:
```
SameSite=lax; HttpOnly; Secure
```
SameSite=lax allows cookies on same-site top-level GET navigations but blocks them on cross-site POST requests. Safari's ITP (Intelligent Tracking Prevention) classifies `onrender.com` as a third-party domain after inactivity periods.

**Long-term fix:** Phase 2b VPS deployment puts both frontend and backend on the same domain (`erp.livogroup.com.np`), making all cookies same-site by definition.

### PowerShell HTTPS + HSTS Verification
```powershell
$r = Invoke-WebRequest -Uri "https://livo-footwear-erp-backend.onrender.com/api/v1/health" -Method GET -UseBasicParsing
$r.StatusCode           # Expected: 200
$r.Headers["Strict-Transport-Security"]  # Expected: max-age=63072000; includeSubDomains; preload
```

---

## Protocol 3: Ledger Validation Rejections (Intentional Guard — Not a Bug)

**Root cause:** The ERP enforces strict boundary validation on all mutation endpoints. These are intentional data-integrity guards enforced by Pydantic. A client or tester entering boundary values (0, -1, very large numbers) will trigger HTTP 422 responses.

### What Triggers a 422 Unprocessable Entity

| Field | Constraint | Error if violated |
|:--|:--|:--|
| `quantity` (purchases, batches) | Must be > 0 | 422: quantity must be greater than 0 |
| `produced_pairs` | Must be >= 0 | 422: value must be non-negative |
| `unit_price` | Must be > 0 | 422: unit price must be positive |
| `worker_count` | Must be >= 0 | 422: value out of range |
| `vat_rate` | Between 0 and 100 | 422: outside VAT percentage range |
| String fields (remarks, names) | Max 500 chars | 422: string too long |

### Why This Is Correct Behavior

The stock ledger uses append-only arithmetic:
```
current_stock = SUM(IN movements) - SUM(OUT movements)
```
If negative quantities were allowed, a single bad entry would corrupt the entire ledger permanently -- there is no "edit" operation. The 422 guard prevents this at the API boundary before data reaches PostgreSQL.

### How to Explain This to the Client

> "The system is protecting your accounts. You cannot enter a zero or negative quantity -- the same way you cannot issue a zero-pair invoice to a customer. This is by design: it prevents accidental data corruption in the stock ledger."

### Resolution During Demo

1. A red banner appears at the top of the form with the validation message.
2. The form does NOT close -- your data stays in the fields.
3. Correct the invalid value and press Ctrl+Enter again.
4. The record will commit cleanly.

**Live API documentation:** Open `https://livo-footwear-erp-backend.onrender.com/docs` and expand any POST endpoint to see the exact Pydantic schema with all field constraints.

---

## Protocol 4: Invoice Sequence Conflict (HTTP 409)

**Root cause:** The `uq_invoice_company_sequence (company_id, sequence_number)` database constraint prevents two invoices from sharing the same number within the same company. Under normal conditions the backend generates these atomically and this never occurs. It can happen if two sessions submit at the exact same millisecond, or if a previous failed transaction left a partially-committed state.

### Diagnosis

- HTTP 409 Conflict from `POST /api/v1/sales/orders`
- Response body: `{"detail": "Invoice sequence conflict"}` or a unique constraint violation message

### Immediate Recovery Steps

**Step 1:** Retry the exact same form submission immediately. The backend re-queries `MAX(sequence_number) + 1` on each attempt, so the second attempt uses the correct next number.

**Step 2:** If retry still fails, check the current invoice count:
```
GET https://livo-footwear-erp-backend.onrender.com/api/v1/invoices/?limit=1
```
Note the highest `invoice_number` in the response.

**Step 3:** Close the form and open a new invoice form from scratch. The sequence counter recalculates on a fresh commit.

### PowerShell Sequence Verification
```powershell
# Verify last 3 invoices for sequence continuity (requires editor auth cookie)
Invoke-RestMethod -Uri "https://livo-footwear-erp-backend.onrender.com/api/v1/invoices/?limit=3" -Method GET |
  Select-Object -ExpandProperty invoices |
  Select-Object invoice_number, sequence_number, is_void
# Expected: consecutive numbers, no gaps, no duplicates
```

### Confirm the Constraint Is Working

The constraint guarantees:
- Invoice INV-01-00027 is always followed by INV-01-00028.
- No gaps exist (a voided invoice keeps its number, marked is_void: true).
- No duplicates can be inserted even under concurrent load.
- Verified by automated test: `test_concurrent_invoice_generation_api` in the regression suite (27/27 tests passing).

---

## Emergency Zero-Downtime Rollback Procedures

### Option A: Vercel Dashboard 1-Click Rollback (Fastest -- 90 seconds)

1. Open `https://vercel.com/dashboard`
2. Click the `livo-footwear-erp` project.
3. Go to the **Deployments** tab.
4. Find the deployment with commit hash `fa949cd` (Phase 5 verified baseline).
5. Click the "..." menu on that deployment -> **Promote to Production**.
6. Vercel instantly re-routes production traffic -- zero downtime, no rebuild required.

The `fa949cd` baseline is: bilingual Nepali/English localization, WCAG 2.1 AA accessibility, mobile PWA hardening. All 27 tests passing.

### Option B: Git Revert + Push (Re-triggers Vercel Build)

Use when a bad commit broke the frontend build itself:

```powershell
# In PowerShell
cd "d:\Antigravity\Footwear app"

# View recent commits
git log --oneline -10

# Revert the bad commit (creates a new commit that undoes it -- safe)
git revert HEAD --no-edit

# Push -- triggers automatic Vercel redeploy
git push origin main
```

To hard-pin to the known-safe baseline `fa949cd`:
```powershell
# Pin to safe baseline on a new branch, then promote via Vercel dashboard (Option A)
git checkout -b emergency-rollback fa949cd
git push origin emergency-rollback
# Then in Vercel dashboard: deploy from branch emergency-rollback
```

### Option C: Render Backend Manual Redeploy

1. Open `https://dashboard.render.com` -> your web service.
2. Click **Manual Deploy** -> **Deploy Latest Commit**.
3. Watch **Logs** tab for: `Uvicorn running on http://0.0.0.0:8000`.
4. Verify health: `https://livo-footwear-erp-backend.onrender.com/api/v1/health`

To roll back Render to a previous build:
1. Go to **Events** tab in the Render dashboard.
2. Find the last successful deployment event.
3. Click **Rollback to this deploy**.

### Option D: Database Restoration (Emergency Only)

**Neon PostgreSQL (current production -- no Docker required):**
1. Go to `https://console.neon.tech` -> project `green-wind-12533394`.
2. Click **Branches** -> main branch -> **Restore**.
3. Select a restore point from the 7-day PITR window.
4. Click **Restore Branch** -> update `DATABASE_URL` in Render environment variables.
5. Trigger a Render redeploy.

**VPS deployment (Phase 2b -- using pg_dump backup):**
```bash
docker compose stop backend
./scripts/restore_postgres.sh backups/livo_dump_YYYYMMDD_HHMMSS.sql.gz livo_erp
docker compose start backend
curl http://localhost/api/v1/health
```

---

## CI/CD and Production Health Pipeline Audit

### Active Automated Pipeline

```
Developer: git push origin main
                   |
                   v
         [GitHub] Receives push event
                   |
          +--------+--------+
          |                 |
          v                 v
    [Vercel]            [Render]
    Detects push         Detects push
    npm run build        docker build ./backend/
    (Next.js 14)         On start: alembic upgrade head
         |                    |
    Build OK?            Health check OK?
    YES -> promote       YES -> promote
    NO  -> old live      NO  -> old container lives
```

Zero-downtime by design: both Vercel and Render keep the previous deployment live until the new one passes its health check.

### Health Check Command Reference

**PowerShell (Windows -- no curl alias conflict):**
```powershell
# Backend full health
Invoke-RestMethod -Uri "https://livo-footwear-erp-backend.onrender.com/api/v1/health" -Method GET

# Frontend HTTP 200 check
(Invoke-WebRequest -Uri "https://livo-footwear-erp.vercel.app" -UseBasicParsing).StatusCode
# Expected: 200

# Auth guard verification (unauthenticated -- proves API is live)
try {
    Invoke-RestMethod -Uri "https://livo-footwear-erp-backend.onrender.com/api/v1/auth/me" -Method GET
} catch {
    $_.Exception.Response.StatusCode.value__
}
# Expected: 401
```

**curl (Linux / Mac / WSL / Git Bash):**
```bash
# Backend health
curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health | python3 -m json.tool

# Frontend status code
curl -s -o /dev/null -w "%{http_code}" https://livo-footwear-erp.vercel.app
# Expected: 200

# Auth guard (unauthenticated -- expects 401)
curl -s -o /dev/null -w "%{http_code}" https://livo-footwear-erp-backend.onrender.com/api/v1/auth/me
# Expected: 401
```

### Expected Healthy Payloads

**Backend Health:**
```json
{"status": "healthy", "database": "healthy"}
```

**Frontend:** HTTP 200, `Server: Vercel`, `X-Vercel-Cache: HIT` or `PRERENDER`

**Auth Guard (unauthenticated):** `{"detail": "Not authenticated"}` -- HTTP 401

**Viewer blocked from mutation:** `{"detail": "Insufficient permissions"}` -- HTTP 403

---

## Presentation Pre-Flight Checklist

Run this **10 minutes before** the client presentation:

- [ ] Health check URL returns `{"status":"healthy","database":"healthy"}`
- [ ] Log in as `editor_admin` -- confirm KPI tiles load on Daily Report
- [ ] Switch language to Nepali -- confirm navigation labels translate
- [ ] Open Stock Ledger -- confirm health badges render
- [ ] Open New Batch modal (Alt+N) -- confirm form opens; press Esc to close
- [ ] Try CSV export on Stock Ledger -- confirm file downloads
- [ ] Log out; log in as `viewer_user` -- confirm mutation buttons are hidden/disabled
- [ ] Log back in as `editor_admin`
- [ ] On a mobile device: confirm touch targets work, PWA installable from Share menu

---

## Known Safe Commit Baselines

| Commit | Description | Tests |
|:--|:--|:--|
| `fa949cd` | Phase 5: Bilingual Nepali/English, WCAG 2.1 AA, mobile PWA hardening | 27/27 PASS |
| `181697a` | Phase 4: IDOR remediation, FK boundary validation | 27/27 PASS |
| `d0e8254` | Phase 4: Security audit suite, dynamic bundle splitting | 27/27 PASS |

**Recommended emergency Vercel rollback target: `fa949cd`**

---

*Document prepared by: Antigravity Engineering | Last updated: 2026-09-27*
