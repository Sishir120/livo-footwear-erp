# LIVO FOOTWEAR ERP — AUTHORIZATION & SECURITY ARCHITECTURE AUDIT

**Checkpoint:** Checkpoint 10 — Authentication, Authorization & Multi-Tenant Security  
**Audit Date:** October 2026  
**System Status:** Production Hardened & Formally Verified  
**Applies To:** Backend (FastAPI, SQLAlchemy 2.0, Pydantic v2), Frontend (Next.js 14 App Router, IndexedDB v2)

---

## 1. Executive Summary

This document establishes the authoritative security architecture of the LIVO Footwear ERP. In enterprise manufacturing and multi-tenant environments, security must be enforced exclusively on the server side:

```text
Authenticated Identity (JWT / HttpOnly Cookie)
              ↓
Server-Derived Security Context (User.company_id, User.role, User.active)
              ↓
Tenant Partitioning (Model.company_id == current_user.company_id)
              ↓
Role-Based Access Control (Admin > Editor > Viewer)
              ↓
Object-Level Authorization (IDOR Defense)
              ↓
Database-Enforced Scoping (TenantRepository / Parameterized SQL)
              ↓
Authorized Business Operation
```

The core invariant of LIVO ERP is:
> **A client-supplied `company_id` is never trusted. A valid JWT signature is never proof that a user may access arbitrary resources. A hidden frontend element is never an authorization boundary.**

---

## 2. Authentication Flow

### 2.1 Identity Verification
1. The client submits credentials (`username`, `password`) via `POST /api/v1/auth/login`.
2. The server queries the `users` table:
   ```python
   user = db.query(User).filter(User.username == request.username).first()
   ```
3. If the user does not exist or password verification fails, the server responds with:
   ```json
   { "detail": "Incorrect username or password" }
   ```
   **Account Enumeration Defense:** The identical HTTP 401 error message is returned whether the username is invalid or the password is incorrect. Constant-time Argon2 verification prevents timing-based enumeration attacks.
4. If the account is marked `active=False`, login is rejected with HTTP 403 Forbidden:
   ```json
   { "detail": "Account is inactive. Please contact administrator." }
   ```

### 2.2 Token Issuance & Transport
Upon successful credential verification:
1. An access token is generated signed with `HS256` using the server-secret key (`SECRET_KEY`):
   ```python
   token = create_access_token(
       data={
           "user_id": user.id,
           "company_id": user.company_id,
           "role": user.role,
           "sub": user.username
       }
   )
   ```
2. The token is transmitted to the client in an **`HttpOnly` session cookie** named `livo_access_token`:
   ```python
   response.set_cookie(
       key="livo_access_token",
       value=token,
       httponly=True,
       samesite="lax",
       secure=settings.COOKIE_SECURE,  # True in production; False only when LIVO_DEV_MODE=true
       max_age=86400  # 24 hours
   )
   ```
3. The response payload returns non-sensitive user metadata (`id`, `company_id`, `name`, `username`, `role`, `active`) for UI state synchronization, but **no secret credentials**.

---

## 3. Authorization Flow & Dependency Pipeline

Every incoming API request is processed through FastAPI dependency injection:

```python
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    # 1. Transport Extraction: HttpOnly cookie first; Bearer header fallback for CLI/automation
    token = request.cookies.get(COOKIE_NAME) or extract_bearer(request)
    if not token:
        raise HTTPException(401, "Not authenticated. Session cookie missing.")

    # 2. Cryptographic Verification & Expiration Check
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired session token.")

    # 3. Server-Authoritative Database Verification
    user_id = payload.get("user_id")
    company_id = payload.get("company_id")
    
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == company_id,
        User.active == True
    ).first()
    
    if not user:
        raise HTTPException(401, "User not found or inactive.")

    # 4. Contextual Correlation Propagation
    set_company_id(user.company_id)
    return user
```

### Key Security Guarantees:
- **Instant Revocation:** If an administrator sets `user.active = False`, the next API request from that user is immediately rejected with HTTP 401, regardless of JWT expiration time.
- **Tenant Affinity:** The database lookup checks `User.company_id == company_id`. If an attacker tampers with the JWT claims or is reassigned, access is severed immediately.
- **Correlation Propagation:** `set_company_id(user.company_id)` binds the active tenant to Python `contextvars`, guaranteeing that all logging, correlation headers, and audit trails automatically log the verified tenant ID.

---

## 4. Role Resolution & Hierarchy

LIVO implements a strict 3-tier Role-Based Access Control (RBAC) model:

```text
┌────────────────────────────────────────────────────────┐
│                        ADMIN                           │
│  - Full System & Financial Control                     │
│  - Operations Telemetry Cockpit (/ops/telemetry)       │
│  - Database Backup Triggers (/backup/run)              │
│  - User Provisioning & Role Administration (/auth/users)│
│  - Inherits all Editor and Viewer capabilities         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                       EDITOR                           │
│  - Factory Operations & Operational Mutations          │
│  - Create/Update Orders, Clients, Invoices, Payments   │
│  - Create/Update Production Batches & BOMs             │
│  - Stock Adjustments & Approved Reversals              │
│  - HR & Worker Management (/hr/workers)                │
│  - Inherits all Viewer capabilities                    │
│  - REJECTED from administrative endpoints (403)        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│                       VIEWER                           │
│  - Compliance Auditors, External Accountants, Viewers  │
│  - Read-Only Access across all business entities       │
│  - Daily, Stock, Receivables & Analytics Reports       │
│  - STRICTLY REJECTED from all mutations (403)          │
└────────────────────────────────────────────────────────┘
```

Role gating dependencies:
- `require_editor`: Enforces `current_user.role in ("editor", "admin")`. Rejects `viewer` with HTTP 403 Forbidden.
- `require_admin`: Enforces `current_user.role == "admin"`. Rejects both `viewer` and `editor` with HTTP 403 Forbidden.

---

## 5. Session Lifecycle & Logout Behavior

### 5.1 Token Expiration
- Access tokens expire after **24 hours** (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`).
- Expired tokens fail `jwt.decode` with `jwt.ExpiredSignatureError`, returning HTTP 401.

### 5.2 Logout Hardening
Reverse proxy infrastructures (Nginx, Cloudflare, Traefik, AWS ALB) frequently cache or ignore cookie deletions if headers are not set with exact matching attributes. LIVO implements multi-stage cookie revocation:
1. `response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)`
2. `response.set_cookie(key=COOKIE_NAME, value="", max_age=0, expires=0, path="/", httponly=True, samesite="lax", secure=settings.COOKIE_SECURE)`
This forces immediate eviction from all browser cookie stores.

---

## 6. Password Security Lifecycle

1. **Hashing Algorithm:** Dual-hasher pipeline managed by `pwdlib`:
   - Primary: **Argon2id** (memory-hard, resistant to GPU/ASIC cracking).
   - Secondary fallback: **Bcrypt** (for backwards-compatible migrations).
2. **Salts:** Cryptographically secure random salts are automatically generated per password hash.
3. **No Plaintext Storage:** Passwords are never stored, logged, or returned in API responses. The `password_hash` column is excluded from all Pydantic output schemas.

---

## 7. Transport Security, Cookies & Headers

### 7.1 Cookie Security Attributes
| Attribute | Production Value | Dev Value | Rationale |
|---|---|---|---|
| `HttpOnly` | `True` | `True` | Prevents document.cookie access from client JavaScript, defeating XSS token theft. |
| `Secure` | `True` | `False` | Mandates transmission exclusively over HTTPS in production. |
| `SameSite` | `Lax` | `Lax` | Neutralizes Cross-Site Request Forgery (CSRF) on state-changing requests while permitting top-level navigation. |
| `Path` | `/` | `/` | Scopes cookie across all API and page routes. |

### 7.2 HTTP Security Response Headers
Applied to every HTTP response via `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff`: Prevents MIME-type sniffing.
- `X-Frame-Options: DENY`: Defeats clickjacking attacks in iframes.
- `Referrer-Policy: strict-origin-when-cross-origin`: Restricts referrer information leakage.
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`: Blocks unwanted browser capabilities.

### 7.3 CORS Configuration
- Production CORS origins are explicitly white-listed in `BACKEND_CORS_ORIGINS`.
- `allow_origins = ["*"]` with `allow_credentials = True` is **strictly forbidden** (FastAPI will raise an exception if misconfigured).
- Credentialed requests (`credentials: 'include'`) only accept whitelisted origins (`http://localhost:3000`, `http://127.0.0.1:3000`, or production ERP domain).
