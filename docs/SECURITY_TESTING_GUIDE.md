# LIVO FOOTWEAR ERP — SECURITY TESTING GUIDE & ADVERSARIAL RUNBOOK

**Standard:** NIST SP 800-115 (Technical Guide to Information Security Testing and Assessment)  
**Target:** LIVO Footwear ERP (FastAPI + SQLAlchemy + PostgreSQL + Next.js)  
**Classification:** Internal Security QA / Adversarial Testing Reference

---

## 1. Overview & Testing Philosophy

This guide details the exact procedures and commands required to execute, reproduce, and verify the security boundaries of LIVO Footwear ERP.

The security model is verified under an **adversarial framework**:
$$\text{Inspect} \longrightarrow \text{Threat-model} \longrightarrow \text{Attack} \longrightarrow \text{Observe Failure} \longrightarrow \text{Fix} \longrightarrow \text{Regression-test} \longrightarrow \text{Re-attack} \longrightarrow \text{Document Evidence}$$

Never assume an endpoint is secure because code review looks benign. Every boundary must be empirically attacked with malicious/hostile payloads.

---

## 2. Prerequisites & Environment Setup

All commands must be executed from the `backend/` directory using the project virtual environment.

```bash
cd "backend"
# Verify Python 3.11+ and dependencies
venv\Scripts\python --version
venv\Scripts\python -m pytest --version
```

### PostgreSQL Environment (Embedded Postgres)
The PostgreSQL test suite uses embedded PostgreSQL 18.6 binaries bundled with the project. No external PostgreSQL service is required:
```bash
# Verify psycopg2 and embedded-postgres installation
venv\Scripts\python -c "import psycopg2, embedded_postgres; print('Postgres testing environment READY')"
```

---

## 3. Running Focused Security Suites

### 3.1 All Checkpoint 16 Security Tests
To run all 20 adversarial security tests across all 6 security test modules:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_security.py tests/test_checkpoint_16_tenant_isolation.py tests/test_checkpoint_16_idor.py tests/test_checkpoint_16_rbac.py tests/test_checkpoint_16_business_security.py tests/test_checkpoint_16_postgres.py -v
```

### 3.2 Multi-Tenant Isolation Suite
Attacks cross-company boundaries between Company A and Company B:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_tenant_isolation.py -v
```
**Attacks executed:**
- Cross-company product, client, warehouse, order, invoice, and worker reading via direct ID (Expected: `404 Not Found`).
- Cross-company collection filtering (Expected: 0 records leaked from foreign company).
- Cross-company sales order creation referencing foreign client (Expected: `404/422`).
- Cross-company invoice generation referencing foreign order (Expected: `404`).
- Cross-company stock adjustment targeting foreign warehouse (Expected: `404`).
- Cross-company deletion of media/records (Expected: `404`).

### 3.3 IDOR / BOLA Regression Suite
Attacks every endpoint accepting an object identifier by substituting foreign entity IDs:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_idor.py -v
```
**Endpoints attacked:**
- `/api/v1/production/products/{id}`
- `/api/v1/sales/clients/{id}`
- `/api/v1/stock/warehouses/{id}`
- `/api/v1/sales/orders/{id}`
- `/api/v1/invoices/{id}`
- `/api/v1/invoices/{id}/printable`
- `/api/v1/purchase/suppliers/{id}`
- `/api/v1/purchase/raw-materials/{id}`
- `/api/v1/purchase/purchases/{id}`
- `/api/v1/hr/workers/{id}/history`
- `/api/v1/hr/workers/{id}` (PATCH)
- `/api/v1/production/{order_id}`
- `/api/v1/production/{order_id}/complete`
- `/api/v1/gallery/images/{id}/download`
- `/api/v1/gallery/{id}` (DELETE)

### 3.4 RBAC & Privilege Escalation Suite
Attacks role boundaries and token verification:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_rbac.py -v
```
**Scenarios tested:**
- `viewer` role attempting write mutations (Expected: `403 Forbidden`).
- `editor` role attempting admin telemetry `/ops/telemetry` (Expected: `403 Forbidden`).
- `editor` role attempting database backup trigger `/backup/run` (Expected: `403 Forbidden`).
- `editor` role attempting downward stock adjustment without supervisor token (Expected: `403 Forbidden`).
- Expired JWT token submission (Expected: `401 Unauthorized`).
- Tampered JWT signature submission (Expected: `401 Unauthorized`).
- Token signed with foreign/attacker key (Expected: `401 Unauthorized`).
- Token missing `user_id` or `company_id` claims (Expected: `401 Unauthorized`).
- Inactive user token submission (Expected: `401 Unauthorized`).
- Mass assignment / `company_id` injection in creation payloads (Expected: injected values overridden with authenticated tenant ID).

### 3.5 Business Logic & Statutory Invariants Suite
Attacks ERP domain invariants:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_business_security.py -v
```
**Invariants verified:**
- Stock zero-floor invariant (dispatching more stock than on-hand fails with `422 INSUFFICIENT_STOCK`).
- Negative and zero quantity rejection (`400/422`).
- Credit limit dispatch safeguard (orders exceeding customer credit limit rejected with `422 CREDIT_LIMIT_EXCEEDED`).
- Statutory Nepal IRD VAT invoice uniqueness (duplicate active VAT invoices for same sales order rejected with `409 Conflict`).
- AR payment allocation sum boundary (allocations exceeding receipt amount rejected with `422`).
- Information disclosure audit (verifying 4xx/5xx responses do not leak stack traces, database credentials, or filesystem paths).

### 3.6 PostgreSQL Security Suite
Executes real PostgreSQL security validation via embedded-postgres 18.6:
```bash
venv\Scripts\python -m pytest tests/test_checkpoint_16_postgres.py -v
```
**PostgreSQL controls tested:**
- Database-level unique constraints (`uq_company_worker_code`, `uq_invoice_company_sequence`).
- Distributed advisory lock tenant keyspace isolation: `(company_id << 32) | id` keyspace separation.
- SQL injection immunity in parameterized ORM queries.

---

## 4. Full Regression Verification

To verify that no previous checkpoint (Checkpoints 1 through 15.2) has regressed:

```bash
# 1. Full Backend Test Suite (All 250 tests)
venv\Scripts\python -m pytest tests/ -v

# 2. Frontend TypeScript Check
cd "../frontend"
npx tsc --noEmit

# 3. Frontend Production Build
npm run build

# 4. Alembic Migration Health
cd "../backend"
venv\Scripts\python -m alembic heads
venv\Scripts\python -m alembic current

# 5. Deployment Preflight Check
python scripts/deploy_preflight.py
```

---

## 5. Security Regression Checklist for Future Features

Before merging any new API endpoint or database migration:
1. **Tenant Scoping:** Does every query filter by `Model.company_id == current_user.company_id`?
2. **Never Trust Payload IDs:** Does the handler verify that foreign keys (`warehouse_id`, `client_id`, `product_id`, `invoice_id`) belong to `current_user.company_id`?
3. **Role Enforcement:** Is the endpoint guarded by `require_admin`, `require_editor`, or `get_current_user`?
4. **Input Constraints:** Are numeric quantities constrained to `gt=0`? Are string inputs sanitized against XSS?
5. **Advisory Locks:** Does mutable stock or financial state acquire PostgreSQL advisory locks?
6. **Error Sanitization:** Does the endpoint return clean Pydantic/HTTPException structures without raw exception tracebacks?
