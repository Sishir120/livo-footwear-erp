# MASTER AUDIT

## 1. Frontend Architecture
- **Framework**: Next.js 14.2 (React 18.2)
- **Routing**: App Router (found `app/` structure traces in output)
- **State Management & Offline Storage**: IndexedDB for offline resilience (implied by previous notes and requirements).
- **Authentication State**: Assumed JWT or session cookie based on backend.
- **Styling**: Industrial Paper design system (`#F8FAFC`).
- **Build Specs**: First Load JS budget < 115 kB (Actual: 109 kB).

## 2. Backend Architecture
- **Framework**: FastAPI (Python)
- **Database ORM**: SQLAlchemy (models located in `app/models/`).
- **Migrations**: Alembic (`migrations/`).
- **Testing**: pytest (64/64 passing, covers HR, gallery, offline sync, stock ledger, concurrency race).
- **Concurrency**: `pg_advisory_xact_lock` used for stock/credit limits concurrency.
- **Audit Logging**: Handled via `test_security_audit.py` (meaning an audit system exists).

## 3. Database Schema
- **DBMS**: PostgreSQL.
- **Financial Types**: **CRITICAL FINDING** - Many financial fields currently use `Float` (e.g., `unit_price`, `credit_limit`, `total_amount`, `subtotal`, `vat_rate`, `vat_amount`, `received_amount`, `receivable_amount` in `stock.py`, `sales.py`, `invoice.py`, `purchase.py`, `worker.py`). These must be migrated to `Numeric/Decimal`.
- **Tenant Boundaries**: `company_id` is used across models (multi-tenant scoping).
- **Sequences**: `invoice_sequences` utilized for gapless monotonicity.

## 4. Infrastructure & Deployment
- **Deployment**: `docker-compose.yml`, `Caddyfile`, `render.yaml` present.
- **Database Hosting**: PostgreSQL (local `pg_binaries.zip` and `livo_dev.db` SQLite trace found, though PG is the production target).

## 5. Next Steps for Hardening
- **Phase 1: Financial Types**: Convert all `Float` to `Numeric` for monetary fields across models and schemas. Generate and apply alembic migration.
- **Phase 2: Concurrency & Transactions**: Verify explicit transaction boundaries (`BEGIN`, `COMMIT`, `ROLLBACK`) and locking order (advisory locks).
- **Phase 3: Idempotency**: Verify idempotency keys for operations like dispatch and payment.
- **Phase 4: Document Numbering**: Verify PostgreSQL sequences usage.
- **Phase 5: Audit System**: Verify immutable audit trails.
- **Phase 6: Auth/Tenant Isolation**: Verify RBAC and `company_id` filters in all API endpoints.
