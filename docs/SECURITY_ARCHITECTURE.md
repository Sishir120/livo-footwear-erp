# SECURITY_ARCHITECTURE.md - LIVO GROUP OF INDUSTRIES Footwear ERP

> This document describes the security architecture, data-integrity guarantees, and operational safeguards of the LIVO Footwear ERP system.

---

## 1. Database Engine - ACID Compliance

PostgreSQL was chosen over SQLite for ACID compliance, MVCC concurrency control, per-row locking, and consistent pg_dump backups without session locking.

## 2. Ledger Principle - Append-Only Stock Integrity

The Product model has NO stock_qty column. Stock is always computed as SUM(direction * quantity) from the stock_movements table. No API endpoint exists to directly set stock. See backend/app/models/stock.py and backend/app/api/v1/stock.py.

## 3. Invoice Immutability

Database-level UniqueConstraint on (company_id, sequence_number) prevents duplicate invoices. Voided invoices retain their sequence number (void-without-reuse). Concurrent collisions handled via IntegrityError retry loop. See backend/app/models/invoice.py.

## 4. Multi-Tenant Isolation

All business queries go through TenantRepository which injects company_id filtering on every operation. The company_id comes from the JWT token, not request body. Zero un-scoped business queries exist in the codebase. See backend/app/db/repository.py.

## 5. Credential and Session Security

Passwords hashed with Argon2 (OWASP recommended). Sessions use httpOnly, Secure, SameSite cookies - not localStorage. SECRET_KEY crash-on-empty enforcement at startup. Role enforcement at API layer, not just UI. See backend/app/core/security.py and backend/app/api/v1/auth.py.

## 6. Transport Security - SSL/TLS

All hosted PostgreSQL connections enforce sslmode=require. HTTPS provided by Render/Vercel edge TLS and Caddy auto-HTTPS for VPS. See backend/app/db/session.py.

## 7. Audit Trail

Every mutating HTTP request logged in append-only audit_log table via middleware. No UPDATE or DELETE endpoints on audit_log. See backend/app/middleware/audit.py.

## 8. Rate Limiting

30 requests per minute per IP on login endpoint. CORS locked to explicit frontend origin allowlist, never wildcard. See backend/app/middleware/rate_limit.py.

## 9. Backup and Recovery

Automated pg_dump with rclone cloud upload. 30-day local retention. Documented restore procedure tested at 100 percent table and row match. See scripts/backup_nightly.sh and scripts/restore_postgres.sh.

## 10. Privilege Model

No superuser privileges required. All migrations use standard DDL via Alembic. No CREATE EXTENSION or ALTER SYSTEM used.

## 11. Secrets Management

Fail-fast ValueError on empty SECRET_KEY. All secrets via environment variables, never committed. .gitignore excludes all .env files.

## 12. Test Coverage

13/13 tests passing: stock math, invoicing, auth, tenant isolation, e2e flow, security module.
