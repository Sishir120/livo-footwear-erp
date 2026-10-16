# LIVO ERP — Day 2 Authorization & Capability-Based Access Control Design

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Standard:** NIST SP 800-53 AC-3 (Access Enforcement) / AC-6 (Least Privilege) / OWASP API Security Top 10 2023  
**Target:** LIVO Footwear ERP Backend & API Gateway

---

## 1. Architectural Principles

1. **Principle of Least Privilege:** Users receive only the minimum capabilities necessary to execute their operational duties. Operational staff (`editor`) cannot unilaterally reverse financial transactions or alter corporate structures.
2. **Separation of Duties (SoD):**
   - **View vs. Mutate:** Separation between non-mutating inspection and state-altering operations.
   - **Create vs. Approve/Reverse:** Operations that reverse fiscal documents (tax invoices, credit notes, ledger movements) or write off balance-sheet assets require managerial or administrative authorization.
3. **Protection of Sensitive Confidential Data:** Worker compensation details (hourly rates, monthly gross pay, cash advances) and citizenship identity documents are segregated from general operational read access.
4. **Zero-Trust Identity & Scope Validation:**
   - Client-supplied `company_id` is never accepted; all queries scope strictly to `current_user.company_id`.
   - Client-supplied `warehouse_id` or `branch_id` must be validated against caller tenant ownership before processing.
5. **Non-Disruptive Backward Compatibility:**
   - Existing roles (`admin`, `editor`, `viewer`) continue functioning without breaking existing workflow tests.
   - The capability model maps seamlessly onto `User.role` (type `String(50)`), requiring **zero schema migrations**.

---

## 2. Canonical Capability Definitions

| Capability Identifier | Description & Scope | Associated Operations |
|---|---|---|
| `OPERATIONAL_READ` | Read non-sensitive business records | View products, catalog, stock balances, orders, general operational reports |
| `OPERATIONAL_MUTATE` | Create and execute normal business workflows | Create sales orders, draft invoices, stock movements, purchase POs, goods receipts, production batches, attendance |
| `FISCAL_REVERSE` | Cancel, void, or reverse statutory financial transactions | Void finalized VAT invoices (`cancel`), issue Schedule-10 credit notes (`credit-note`) |
| `INVENTORY_REVERSE` | Reverse or void physical stock movements | Void stock movement entries (`/stock/reversals/{id}`) |
| `INVENTORY_ADJUST_DOWN` | Write down inventory for loss, damage, or audit shrinkage | Downward stock adjustments (`/stock/adjustments` with `quantity_delta < 0`) |
| `HR_COMPENSATION_READ` | Access confidential wage, salary, and advance records | View worker pay rates, monthly payroll history, outstanding advance balances |
| `HR_COMPENSATION_MUTATE` | Finalize payroll payouts and modify compensation rates | Process monthly payroll, disburse advances, update worker pay rates |
| `HR_CITIZENSHIP_MANAGE` | Manage government identity documents | Upload, view, and delete worker citizenship documents |
| `ASSET_DELETE` | Write off capitalized fixed assets | Delete fixed assets from the asset register |
| `BRANCH_MANAGE` | Restructure organizational operating units | Create branches, toggle branch status, assign/unlink warehouses |
| `USER_MANAGE` | Provision and administer tenant users and roles | Create users, update roles, toggle active status |

---

## 3. Role-to-Capability Assignment Matrix

| Capability | `admin` | `manager` | `editor` | `viewer` |
|---|:---:|:---:|:---:|:---:|
| `OPERATIONAL_READ` | ✅ | ✅ | ✅ | ✅ |
| `OPERATIONAL_MUTATE` | ✅ | ✅ | ✅ | ❌ |
| `FISCAL_REVERSE` | ✅ | ✅ | ❌ | ❌ |
| `INVENTORY_REVERSE` | ✅ | ✅ | ❌ | ❌ |
| `INVENTORY_ADJUST_DOWN` | ✅ | ✅ | ⚠️ *(Supervisor token only)* | ❌ |
| `HR_COMPENSATION_READ` | ✅ | ✅ | ❌ *(Masked / Redacted)* | ❌ *(Masked / Redacted)* |
| `HR_COMPENSATION_MUTATE` | ✅ | ✅ | ❌ | ❌ |
| `HR_CITIZENSHIP_MANAGE` | ✅ | ❌ | ❌ | ❌ |
| `ASSET_DELETE` | ✅ | ✅ | ❌ | ❌ |
| `BRANCH_MANAGE` | ✅ | ✅ | ❌ | ❌ |
| `USER_MANAGE` | ✅ | ❌ | ❌ | ❌ |

---

## 4. Shared Dependency & Service Architecture

Rather than scattering ad-hoc `if current_user.role != "admin"` checks across 20 modules, authorization is centralized in `backend/app/api/deps.py`:

```python
def require_editor(current_user: User = Depends(get_current_user)) -> User:
    """Enforces editor, manager, or admin role for standard operational mutations."""
    if current_user.role not in ("editor", "manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Role 'editor', 'manager', or 'admin' is required.",
        )
    return current_user

def require_manager(current_user: User = Depends(get_current_user)) -> User:
    """Enforces manager or admin role for supervisory, fiscal reversal, and HR payroll actions."""
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Role 'manager' or 'admin' is required for this operation.",
        )
    return current_user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Enforces admin role for tenant configuration, identity docs, and user administration."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied. Role 'admin' is required for this operation.",
        )
    return current_user
```

---

## 5. Specific Vulnerability Mitigations

### 5.1 Mitigation for VULN-01: Stock Adjustment Downward Write-Off Bypass
- **Defect:** An editor could write off arbitrary quantities of stock without supervisor approval by supplying `reason_code = "RECOUNT"`.
- **Fix:** Remove the recount bypass. If `quantity_delta < 0` and `current_user.role not in ("admin", "manager")`, a valid supervisor token is strictly required regardless of reason code.

### 5.2 Mitigation for VULN-02: Admin Self-Demotion & Lockout
- **Defect:** An administrator updating their own user record via `PATCH /api/v1/auth/users/{user_id}` could set `active = False` or `role = "viewer"`, causing a tenant lockout.
- **Fix:** If `user_id == current_user.id`, prevent modifying `active` to `False` or demoting `role` away from `"admin"`. Return `HTTP 400 Bad Request` with an explicit notice.

### 5.3 Mitigation for VULN-04: Confidential Worker Compensation Leakage
- **Defect:** `GET /api/v1/hr/workers/{worker_id}/history` and `GET /api/v1/hr/workers` revealed salaries, pay rates, and advance balances to unprivileged `viewer` roles.
- **Fix:**
  - Restrict `GET /api/v1/hr/workers/{worker_id}/history` to `require_manager` (managers and admins).
  - In `GET /api/v1/hr/workers`, if `current_user.role not in ("admin", "manager")`, redact `basic_rate_paisa`, `outstanding_advance_paisa`, and `current_month` financial details.

### 5.4 Mitigation for VULN-05: Unrestricted Reversals, Credit Notes, and Asset Deletions
- **Defect:** `POST /api/v1/invoices/{id}/cancel`, `POST /api/v1/invoices/{id}/credit-note`, `POST /api/v1/stock/reversals/{id}`, and `DELETE /api/v1/fixed-assets/{id}` allowed basic `editor` roles to execute financial cancellations.
- **Fix:** Upgrade route dependencies to `require_manager` (or `require_admin` where appropriate).

### 5.5 Mitigation for VULN-06: Branch Structural Administration
- **Defect:** Operational editors could create branches, deactivate operational units, and unlink warehouses.
- **Fix:** Restrict mutating branch endpoints in `backend/app/api/v1/branches.py` to `require_admin`.

---

## 6. Compatibility & Migration Strategy

1. **Database Schema:** `User.role` is `Column(String(50))` in SQLAlchemy. No schema migration is required to support the new capability model.
2. **User Schemas:** Update `UserCreate` and `UserUpdate` in `backend/app/schemas/auth.py` regex pattern to `^(admin|manager|editor|viewer)$`.
3. **Existing Deployments:** All pre-existing `admin`, `editor`, and `viewer` users retain their capabilities without modification. No broader permissions are silently granted.
