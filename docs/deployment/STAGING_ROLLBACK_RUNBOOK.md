# LIVO FOOTWEAR ERP — STAGING ROLLBACK & RECOVERY RUNBOOK

**Document Identifier:** `STAGING_ROLLBACK_RUNBOOK.md`  
**Document Path:** `docs/deployment/STAGING_ROLLBACK_RUNBOOK.md`  
**Purpose:** Standard Operating Procedure (SOP) for mitigating failed staging deployments, schema migration regressions, corrupted state, and unexpected downtime.  
**Authoring Team:** Database & Reliability Engineer / DevOps Lead  
**Date:** 2026-10-14  

---

## 1. INCIDENT CLASSIFICATION & ESCALATION MATRIX

| Incident Level | Symptoms | Trigger Conditions | Immediate Action |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Data corruption, financial rounding deviation, migration failure during deployment, complete API crash (500s on all routes). | Failed migrations, foreign key violation storms, `/health/ready` returns HTTP 503. | **Halt all demo activities.** Revert git deployment to last stable commit. Restore staging DB from pre-deployment snapshot. |
| **SEV-2 (High)** | Single module API failure (e.g. Sales dispatch fails, HR advances reject valid requests), CORS blockage on frontend. | Regression in API router or middleware; mismatched `NEXT_PUBLIC_API_URL`. | Rollback frontend or backend deployment individually. Inspect correlation IDs in logs. |
| **SEV-3 (Low)** | Styling glitch, datepicker formatting oddity, minor non-blocking UI layout misalignment. | Browser-specific CSS or client-side formatting issue. | Patch forward via hotfix branch without database rollback. |

---

## 2. DATABASE SCHEMA ROLLBACK PROCEDURE

### 2.1 Reversible vs Non-Reversible Migrations
- **Additive Migrations (Reversible):** Adding columns, indexes, or new standalone tables (e.g., `012_add_c15_indexes`, `020_fixed_assets_waste_and_expenses`) can be safely downgraded using `alembic downgrade -1`.
- **Destructive/Type-Altering Migrations:** Migrations altering data types (e.g., converting float to Numeric) or populating normalized foreign keys must NEVER be downgraded blindly in place if production or user data exists.
- **Rule:** Before any migration execution on staging, a snapshot of the database MUST be captured using `pg_dump`.

### 2.2 Downgrade Execution Command
To step backward by 1 migration:
```bash
cd backend
alembic downgrade -1
```

To target a specific verified revision (e.g., revision `019`):
```bash
cd backend
alembic downgrade 019_advance_installment_recovery_engine
```

### 2.3 Post-Downgrade Verification
Verify that the database catalog reflects the intended revision:
```bash
alembic current
```

---

## 3. FULL DATABASE RESTORATION FROM SNAPSHOT

If a schema migration fails mid-transaction or leaves orphaned constraints:

```bash
# 1. Stop backend application to terminate active connection pools
# (On Linux / VPS):
sudo systemctl stop livo-staging-backend
# (On Docker Compose):
docker compose stop backend

# 2. Drop existing corrupted staging database
dropdb -h <db_host> -U <db_user> livo_staging

# 3. Re-create empty staging database
createdb -h <db_host> -U <db_user> -O livo_staging_user livo_staging

# 4. Restore from latest verified SQL snapshot
psql -h <db_host> -U livo_staging_user -d livo_staging -f /var/backups/livo_staging/pre_deploy_snapshot.sql

# 5. Restart backend application
sudo systemctl start livo-staging-backend

# 6. Verify readiness
curl -f http://localhost:8000/health/ready
```

---

## 4. APPLICATION & FRONTEND ROLLBACK

### 4.1 Vercel Frontend Rollback
1. Open Vercel Project Dashboard -> **Deployments**.
2. Locate the previous successful deployment card.
3. Click the three dots `...` and select **Promote to Production**.
4. The edge CDN instantaneously redirects domain traffic to the previous immutable build artifact within 5 seconds.

### 4.2 Backend Rollback (Docker / Cloud PaaS)
1. **Render / Koyeb:** Navigate to **Deploys** -> Select the previous commit hash -> Click **Rollback to this deploy**.
2. **Git / Manual VPS:**
   ```bash
   git checkout <PREVIOUS_STABLE_COMMIT_HASH>
   # Restart ASGI process
   sudo systemctl restart livo-staging-backend
   ```

---

## 5. POST-ROLLBACK AUDIT CHECKLIST

- [ ] Liveness probe returns 200 OK (`GET /health/live`).
- [ ] Readiness probe returns 200 OK (`GET /health/ready`).
- [ ] User authentication succeeds (`POST /api/v1/auth/login`).
- [ ] Read test: Stock ledger and inventory views display accurate counts.
- [ ] Write test: Create synthetic draft invoice and confirm transaction commits without error.
- [ ] Document the root cause in `docs/INCIDENT_LOG.md`.
