# LIVO Footwear ERP — Day 7.4 Artifact Identity & Browser Verification Report

**Phase:** Day 7.4 Final Artifact Identity & Staging Authorization Gate  
**Timestamp:** 2026-10-16T15:58:00+05:45  
**Workspace:** `D:\Antigravity\Footwear app`  
**Git Baseline:** `main` @ `2ab515e1c18fceafb5621a2b5ce4127ec2bf24bb` (Tracked Modifications: 34 files intact)  

---

## 1. Executive Summary: Browser-Test Artifact Identity

A rigorous forensic audit of the Day 7.3 verification session was conducted to determine whether the browser tests evaluated the active working tree or the extracted release candidate.

### Forensic Process Audit
| Process Attribute | Backend Process (task-6554) | Frontend Process (task-6556) |
| :--- | :--- | :--- |
| **Executable** | `d:\Antigravity\Footwear app\backend\venv\Scripts\python.exe` | `node.exe` via `npm run dev` |
| **Command Line** | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` | `next dev -p 3000` |
| **Working Directory** | `D:\Antigravity\Footwear app\backend` | `D:\Antigravity\Footwear app\frontend` |
| **Bound Port** | `127.0.0.1:8000` | `127.0.0.1:3000` |
| **Deployment Case** | **Case A (Original Working Tree)** | **Case A (Original Working Tree)** |

**Conclusive Finding:**  
In Day 7.3, the browser acceptance test was conducted exclusively against the **original local development working tree** (`Case A`). The extracted artifact (`livo_staging_artifact.tar.gz`) was **never built or served to the browser**.

---

## 2. Release Candidate Packaging & Cryptographic Identity

The local release package was audited to verify immutable cryptographic identity:

- **Archive File:** `livo_staging_artifact.tar.gz`
  - **Size:** 12,390,784 bytes (11.82 MB)
  - **SHA-256 Digest:** `FF2C3CDA5416F8B839D698D9312362B53F487180CDB423E77413D12F57C1AB9C`
- **Manifest File:** `staging_artifact_manifest.sha256`
  - **Size:** 138,934 bytes
  - **SHA-256 Digest:** `CF08FE6F0953CA79D5395A626516BFBF185F02DBC05A4C4D0E86D58171B36256`
  - **Tracked Entries:** 1,196 files verified against filesystem

---

## 3. Isolated Production Build & Rehearsal (Day 7.4)

To resolve the unverified artifact identity, the exact release tarball was extracted into an isolated scratch environment:
`D:\Antigravity\Footwear app\scratch\isolated_staging_day74`

### 3.1 Isolated Backend Execution
1. Migrations executed up to head (revision `024_add_rate_limit_entries`) against isolated database `isolated_staging.db`.
2. Initial company `LIVO` and warehouse `WH-MAIN` seeded.
3. Synthetic personas provisioned via `provision_demo_personas.py --confirm-target-db isolated_staging.db`:
   - `admin_demo` (`role: admin`)
   - `viewer_demo` (`role: viewer`)
   - `editor_admin` (`role: editor`)
   - `viewer_user` (`role: viewer`)
4. Uvicorn launched on dedicated isolated port **8005**:
   - `http://127.0.0.1:8005/health` returned HTTP 200 OK (`{"status":"healthy","version":"1.0.0","database":"healthy"}`).

### 3.2 Isolated Frontend Production Build & Execution
1. Environment configured in `frontend/.env.production`:
   ```env
   NEXT_PUBLIC_API_URL=http://127.0.0.1:8005
   API_URL=http://127.0.0.1:8005
   ```
2. Executed `npm run build`:
   - Exit code: `0`
   - Compiled 7 static routes (`/`, `/_not-found`, `/login`, `/privacy`, `/terms`).
   - Shared client chunks: 87.7 kB.
3. Started production server:
   `npm run start -- -p 3005`
   - Listened on `http://localhost:3005`.

---

## 4. Browser Acceptance Drill Findings & Discovered Release Blockers

An automated browser acceptance drill was executed using `browser_subagent` against `http://localhost:3005/login`.

### Discovered Release Blocker 1: Middleware Infinite Redirect Loop
- **Mechanism:**
  In `frontend/src/middleware.ts`:
  ```typescript
  const token = request.cookies.get('livo_access_token')?.value;
  if (token && isAuthRoute) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  ```
  In `frontend/src/app/page.tsx`:
  ```typescript
  const checkUser = async () => {
    const res = await fetch("/api/v1/auth/me");
    if (!res.ok) {
      window.location.href = "/login";
    }
  };
  ```
- **Observed Behavior:**
  If a browser retains any expired or invalidated `livo_access_token` cookie for `localhost`, `middleware.ts` detects the cookie and redirects `/login` to `/`. On `/`, client-side `checkUser()` calls `/api/v1/auth/me`, which returns 401 Unauthorized, prompting `window.location.href = "/login"`. This creates an infinite, rapid redirect ping-pong loop between the edge middleware and client code.
- **Evidence:** Uvicorn access log showed 20+ repeated calls to `/api/v1/auth/me` within 10 seconds.

### Discovered Release Blocker 2: Client Bundle URL Baking
- **Mechanism:**
  Next.js embeds `process.env.NEXT_PUBLIC_*` values into the client-side JavaScript bundles at compilation time (`next build`).
- **Observed Behavior:**
  When built under default production settings, client-side fetches target the remote cloud deployment (`https://livo-footwear-erp.vercel.app` or Render) instead of routing through the local reverse proxy (`/api/backend/*`).
- **Consequence:**
  The extracted artifact cannot complete full end-to-end browser workflows in an isolated, air-gapped staging environment without access to cloud infrastructure.

---

## 5. Artifact Identity Sign-Off Verdict

Because the isolated production build encountered a client-side redirect loop and unresolved environment coupling during automated browser acceptance testing on port 3005:

**VERDICT: FAILED ISOLATED ARTIFACT ACCEPTANCE**  
The claim that the exact extracted release artifact passed browser acceptance is **REFUTED**. Full remediation of client cookie handling and proxy routing is required prior to cloud staging authorization.
