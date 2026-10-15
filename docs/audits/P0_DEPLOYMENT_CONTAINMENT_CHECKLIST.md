# LIVO FOOTWEAR ERP — P0 DEPLOYMENT CONTAINMENT CHECKLIST

**Document Version:** 1.0.0  
**Effective Date:** October 14, 2026  
**Auditor / Security Role:** Independent Application Security Engineer & Release Manager  
**Target Environment:** Staging & Production Deployment Containers (Render / Vercel)  

---

## 1. PURPOSE & APPLICABILITY

This checklist specifies the exact, non-destructive sequence of operational steps required for an authorized human operator to contain compromised demo credentials, verify deployment configuration, and securely publish the P0 security remediation candidate.

> [!WARNING]
> Do NOT execute these containment steps against production infrastructure without explicit, recorded authorization from the system owner.

---

## 2. OPERATIONAL CONTAINMENT CHECKLIST

### Step 1: Disable or Rotate Exposed Demo Accounts in Database
Because baseline commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` unconditionally created `admin_demo`, `viewer_demo`, `editor_admin`, and `viewer_user`, any database deployed from that commit contains known accounts.

An authorized operator with direct database access must execute:
```sql
-- Connect to staging / production database via secure psql console
-- 1. Check if exposed demo accounts exist
SELECT id, company_id, username, role, active, created_at 
FROM users 
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');

-- 2. Deactivate exposed accounts immediately (Soft Deactivation - Preserves Foreign Keys)
UPDATE users 
SET active = FALSE, 
    updated_at = NOW() 
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');

-- 3. Scramble existing password hashes to prevent authentication even if account is re-enabled
UPDATE users 
SET password_hash = '$2b$12$REVOKED_AND_DISABLED_' || substr(md5(random()::text), 1, 32)
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
```

---

### Step 1: Provision Legitimate Administrative Account via Secure CLI (PRE-REQUISITE)
Before deactivating existing accounts or rotating secrets, the operator must provision a new, secure administrative user with a strong unique password. This prevents accidental administrator lockout:

```bash
# Run on the server container or via one-off task
python backend/scripts/create_admin.py \
  --username sysadmin_ops \
  --email operations@livogroup.com \
  --name "Senior Operations Administrator"
# Enter a strong password (minimum 16 characters) when prompted
```

---

### Step 2: Disable Exposed Demo Accounts in Database (Immediate Account Lockout)
Because baseline commit `47cf8f58e84c94c86f84c06fe8b5a974f2e47ea4` unconditionally created `admin_demo`, `viewer_demo`, `editor_admin`, and `viewer_user`, any database deployed from that commit contains known accounts.

An authorized operator with direct database access must execute:
```sql
-- Connect to staging / production database via secure psql console
-- 1. Check if exposed demo accounts exist
SELECT id, company_id, username, role, active, created_at 
FROM users 
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');

-- 2. Deactivate exposed accounts immediately (Soft Deactivation - Preserves Foreign Keys)
UPDATE users 
SET active = FALSE, 
    updated_at = NOW() 
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');

-- 3. Scramble existing password hashes to prevent authentication even if account is re-enabled
UPDATE users 
SET password_hash = '$2b$12$REVOKED_AND_DISABLED_' || substr(md5(random()::text), 1, 32)
WHERE username IN ('admin_demo', 'viewer_demo', 'editor_admin', 'viewer_user');
```
*Immediate Effect:* In `backend/app/api/deps.py`, `get_current_user` queries `User.active == True`. Setting `active = FALSE` causes all subsequent API requests with existing tokens from these accounts to immediately fail with `401 Unauthorized: User not found or inactive`.

---

### Step 3: Rotate JWT SECRET_KEY (Immediate Global Token Invalidation)
To guarantee that old cryptographic signatures on access tokens cannot be reused:

- Rotate `SECRET_KEY` in the hosting environment variables (Render Dashboard -> Environment -> `SECRET_KEY`).
*Immediate Effect:* `jwt.decode` in `backend/app/core/security.py` immediately rejects all previously minted tokens with `PyJWTError`, forcing all clients to re-authenticate.
*Lockout Prevention:* Because Step 1 provisioned `sysadmin_ops`, the operator can immediately authenticate with the new `SECRET_KEY`.

---

### Step 4: Verify Environment Configuration & Operator Proxy Procedure
In the cloud hosting management console (Render / AWS / Docker):

1. **Verify Environment Mode:**
   ```bash
   ENVIRONMENT=staging     # or production
   ```
2. **Confirm Demo Seeding is Disabled:**
   ```bash
   ENABLE_DEMO_SEEDING=false
   ```
   *(Note: Code fails closed if ENVIRONMENT is not in development list, but explicit setting is mandatory)*
3. **Proxy Trust Setting (Render Verification Procedure):**
   - Keep conservative default:
     ```bash
     TRUSTED_PROXIES=127.0.0.1,::1
     ```
   - **Operator Verification Procedure on Render:**
     Do NOT configure wildcard subnets (e.g. `10.0.0.0/8` or `*`) without verification.
     1. Make a curl request from a known operator IP to the backend.
     2. Inspect the application logs for the exact direct peer IP (`request.client.host`) and `X-Forwarded-For`.
     3. If Render connects from a specific, documented internal bridge IP or CIDR dedicated to the service, only then configure `TRUSTED_PROXIES` with that specific CIDR.
     4. Note that while `TRUSTED_PROXIES` remains `127.0.0.1,::1`, all staging traffic shares the 30 req/min login rate limit bucket.
4. **Confirm Database Auto-Migration Setting:**
   ```bash
   AUTO_MIGRATE=true       # for single container staging
   # Or set AUTO_MIGRATE=false if migrations are run via pre-deploy release job
   ```

---

### Step 5: Publish Reviewed Security Patch & Deploy
1. **Review Local Staged Changes:**
   Verify only the reviewed P0 security and startup-safety files are included in the release commit.
2. **Commit with Audit Reference:**
   ```bash
   git commit -m "fix(security): resolve P0 credential leakage, demo seeding, and rate limit spoofing"
   ```
3. **Push to Release Branch:**
   ```bash
   git push origin release/v1.0.0-staging
   ```
4. **Trigger Cloud Deployment:**
   - Vercel automatically deploys frontend upon push.
   - Render automatically builds and deploys Docker backend container.

---

### Step 6: Post-Deployment Smoke Verification & Telemetry Audit
Immediately following deployment, execute these non-destructive checks:

1. **Check Backend Deployment Telemetry:**
   ```bash
   curl -s https://livo-footwear-erp-backend.onrender.com/api/v1/health | jq .
   ```
   *Expected Response:*
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "commit": "<latest_8_char_sha>",
     "database": "healthy",
     "app_name": "LIVO Footwear ERP"
   }
   ```
   Verify that `"commit"` matches the deployed commit SHA.

2. **Verify Frontend Login Page Sanitization:**
   Open `https://livo-footwear-erp.vercel.app/login` in an Incognito browser window.
   - Assert: Form inputs are completely empty.
   - Assert: Zero "Admin Operator" or "Auditor Viewer" preset buttons exist.
   - Assert: No credentials autofill.

3. **Verify Rate Limiting with Spoofed Header:**
   ```bash
   # Send 10 rapid attempts with varying X-Forwarded-For headers from the same client IP
   for i in {1..10}; do
     curl -s -o /dev/null -w "%{http_code}\n" \
       -X POST https://livo-footwear-erp-backend.onrender.com/api/v1/auth/login \
       -H "Content-Type: application/json" \
       -H "X-Forwarded-For: 198.51.100.$i" \
       -d '{"username":"invalid_user","password":"wrong_password"}'
   done
   ```
   *Expected Result:* Responses transition from `401/404` to `429 Too Many Requests` regardless of the spoofed header.

4. **Verify Secure Admin Authentication:**
   Authenticate with the new administrator account created in Step 3. Confirm successful login and JWT receipt.
