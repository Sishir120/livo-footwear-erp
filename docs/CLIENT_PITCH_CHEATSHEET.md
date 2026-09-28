# LIVO Footwear ERP — Executive Client Demonstration Playbook
**Confidential — For Pitch Lead & Technical Presenters Only**  
*Target Client: LIVO GROUP OF INDUSTRIES (Nepal Footwear Manufacturing)*  
*System Deployment: Production Cloud (Vercel + Render + Neon PostgreSQL)*

---

## 1. Quick Access Cloud Coordinates & Credentials

| Role | Username | Password | Direct Application URL |
| :--- | :--- | :--- | :--- |
| **Executive Admin / Editor** | `admin_demo` | `LivoAdmin2026!` | [https://livo-footwear-erp.vercel.app](https://livo-footwear-erp.vercel.app) |
| **Auditor / Floor Viewer** | `viewer_demo` | `LivoViewer2026!` | [https://livo-footwear-erp.vercel.app](https://livo-footwear-erp.vercel.app) |
| **Backend REST API** | — | Bearer JWT | [https://livo-footwear-erp-backend.onrender.com](https://livo-footwear-erp-backend.onrender.com) |
| **Health Probe Endpoint** | — | Open | `/api/v1/health` |
| **Interactive Lifecyle Diagram** | — | Local / Standalone | `docs/diagrams/workflow_complete_erp_lifecycle.html` |
| **Triage Flowchart Diagram** | — | Local / Standalone | `docs/diagrams/workflow_critical_debugging_triage.html` |

> **Pro-Tip:** The login card features 1-click **"Demo Admin"** and **"Demo Viewer"** quick-fill pill buttons. Use them to avoid typos during screen-sharing.

---

## 2. T-Minus 5 Minutes: Pre-Flight Warmup Checklist

Render containers sleep after 15 minutes of zero inbound HTTP traffic. Run this exact warmup command 3 minutes before opening Zoom/Google Meet:

```bash
# 1-Liner Warmup Ping (powershell or bash)
curl -s "https://livo-footwear-erp-backend.onrender.com/api/v1/health"
```
- **Expected Return:** `{"status":"healthy","database":"connected","version":"1.0.0"}`
- **Edge Warmup:** Open `https://livo-footwear-erp.vercel.app` in Chrome Incognito. Verify login card renders in < 200ms.
- **Audio/Display Setting:** Ensure browser zoom is locked at 100% or 110% (1440x900 or 1920x1080 display).

---

## 3. High-Impact 5-Minute Executive Pitch Script

```
[00:00 - 00:45] ACT 1: LOCALIZATION & FACTORY FLOOR REALITY
"Namaste. Footwear manufacturing in Biratnagar and Kathmandu doesn't fail on strategy — it fails on the factory floor when software is too foreign or complex for daily line supervisors. Notice our interface: 1 click toggles the entire terminal into authentic Nepali (लगइन, स्टक लेजर, उत्पादन ब्याच). Our high-density UI eliminates fluff and maximizes data rows per screen."
Action: Toggle EN -> नेपाली -> EN. Click 'Demo Admin' -> Login.

[00:45 - 01:45] ACT 2: EXECUTIVE COCKPIT & LIVE VELOCITY
"Here is your morning cockpit: The Industrial Velocity Strip tracks pairs produced vs. dispatched in real-time, coupled with your Realized Cash Ratio. No more waiting for end-of-month accountant spreadsheets. You know before lunch if Line 2 is bottlenecking or if wholesale receivables are lagging behind shipments."
Action: Point to Factory Floor Velocity bar, hover over Daily Output charts, show Cash vs. Credit split.

[01:45 - 02:45] ACT 3: PARIS POINTS SIZING MATRIX (SIZE 32–43)
"The #1 reason generic ERPs fail shoe factories: Shoes aren't generic commodities. A model comes in size curves. Notice our Stock Ledger: Every SKU expands into a Paris Points 32 to 43 matrix. Green pills show immediate ready-to-ship stock; clean dashes signal stockouts. Column headers stay sticky while scrolling, and exporting to CSV takes exactly 1 click."
Action: Navigate to Stock Ledger, show horizontal Paris Points grid, filter 'Sneaker', click Export CSV.

[02:45 - 03:45] ACT 4: RAPID PRODUCTION & CONTINUOUS ENTRY
"Factory operators hate mice. In our system, they press Alt+N from anywhere. Watch: Enter SKU, Tab/Enter through Size, Pairs, Line. Ctrl+Enter commits the batch. The drawer stays open, autoincrements to the next batch number, and updates the append-only ledger in 40ms without a page reload."
Action: Press Alt+N, demonstrate keyboard-only batch entry, hit Ctrl+Enter, highlight instant ledger count update.

[03:45 - 04:30] ACT 5: WHOLESALE ORDER, 13% NEPAL VAT & SEQUENTIAL INVOICE
"When wholesale buyers order 100 cartons, manual tax calculation creates audit nightmares. In our Record Sale strip: Enter pairs and rate — the system automatically computes taxable subtotal, 13% Nepal VAT, and gross NPR. The generated invoice uses strict database sequences (uq_invoice_company_sequence) so tax numbers never skip, featuring company PAN and signature blocks."
Action: Open Record Sale, enter sample order, show live VAT calculation, click Print/View Invoice.

[04:30 - 05:00] ACT 6: BULLETPROOF SECURITY & AUDIT LOCKOUT
"Finally, total peace of mind against internal tampering. Watch what happens when an auditor or viewer logs in: The Alt+N shortcut, New Batch button, Record Sale trigger, and Void buttons vanish completely. Read-only means strictly read-only at both the UI and API levels."
Action: Logout -> Click 'Demo Viewer' -> Login -> Show clean read-only state across tables.
```

---

## 4. Emergency Instant Triage Matrix (Pitch Fail-Safe)

| Anomaly During Pitch | Root Cause | Instant On-Call Mitigation (What To Do & Say) |
| :--- | :--- | :--- |
| **First page load shows spinner for > 10s** | Render backend cold start wake-up | **Say:** *"Our microservice container is spinning up with isolated encrypted memory."*<br>**Action:** Keep speaking for 12 seconds; it will auto-resolve. Or run the warmup curl in background. |
| **Mutation returns 403 Forbidden** | Accidental session under `viewer_demo` | **Say:** *"Notice our role-based security in action: Viewer accounts are strictly forbidden from altering production records."*<br>**Action:** Log out and click 'Demo Admin' pill button. |
| **Sale submission returns 422 Unprocessable** | Requested quantity exceeds size ledger balance | **Say:** *"The system refuses to sell phantom inventory. Our append-only ledger strictly prevents negative warehouse stock."*<br>**Action:** Select a size with positive green badge balance (e.g. Size 40/41). |
| **Local Wi-Fi drops or network latency** | Client venue connection stutter | **Say:** *"Let's review our compiled architecture lifecycle sequence diagram while the local venue Wi-Fi packet clears."*<br>**Action:** Open standalone `docs/diagrams/workflow_complete_erp_lifecycle.html` offline in browser. |

---

## 5. Architectural Talking Points For C-Suite & Technical Directors

1. **Append-Only Ledger (No Silent Edits):** We do not have a mutable `stock_qty` integer in the database. Stock is computed dynamically from `stock_movements` (+1 for production, -1 for dispatch). Nobody can secretly doctor inventory numbers.
2. **Monotonic Nepal IRD Sequence:** Every invoice sequence is locked at the PostgreSQL transaction level (`uq_invoice_company_sequence`), guaranteeing zero duplicate bills and full audit compliance.
3. **Enterprise Sizing Curve Engine:** Handles Continental / Paris Points (32 to 43) natively, eliminating Excel spreadsheets and mismatched carton packing slips.
