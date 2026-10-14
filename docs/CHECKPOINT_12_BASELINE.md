# LIVO FOOTWEAR ERP — CHECKPOINT 12 BASELINE RECONNAISSANCE
**Checkpoint 12 — Observability, Performance, Reliability & Operational Readiness**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Executive Baseline & System Architecture

LIVO Footwear ERP is an industrial multi-tenant enterprise resource planning system tailored for footwear manufacturing.

```
+--------------------------------------------------------------------------------------------------------+
|                                  LIVO ERP SYSTEM TOPOLOGY                                              |
+--------------------------------------------------------------------------------------------------------+
|                                                                                                        |
|  [Next.js 14 Web Frontend]                                                                             |
|    - App Router, React 18, Tailwind CSS, TypeScript                                                    |
|    - Local-first offline transaction queue (IndexedDB)                                                 |
|    - Client-side Money/Paisa representation                                                            |
|                                                                                                        |
|         │ (HTTPS / REST API JSON / Cookie & Bearer JWT)                                                |
|         ▼                                                                                              |
|                                                                                                        |
|  [FastAPI Backend Gateway & API]                                                                       |
|    - Middlewares: Idempotency, SecurityHeaders, CorrelationId, AuditLog, BasicRateLimit                |
|    - Multi-tenant isolation: TenantRepository scoping by company_id                                    |
|    - Strict Decimal arithmetic & integer paisa ledger posting                                          |
|                                                                                                        |
|         │ (SQLAlchemy 2.0 ORM / Connection Pool / Advisory Locks)                                       |
|         ▼                                                                                              |
|                                                                                                        |
|  [Relational Database Tier]                                                                            |
|    - Production: PostgreSQL 15+ (Hosted on Neon Serverless, WAL Streaming, TLS 1.3)                    |
|    - Development: SQLite 3 (WAL journal mode, busy_timeout=30s, foreign_keys=ON)                      |
|                                                                                                        |
|         │ (boto3 S3 API)                                                                               |
|         ▼                                                                                              |
|  [Cloud Storage Tier]                                                                                  |
|    - Cloudflare R2 / Backblaze B2 (Encrypted database backups & product media uploads)                  |
+--------------------------------------------------------------------------------------------------------+
```

---

## 2. Runtime & Component Specifications

| Dimension | Specification | Verification Evidence |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.14.7 | Virtual environment: `.\venv\Scripts\python.exe` |
| **Backend Framework** | FastAPI 0.110.0+ on Starlette / AnyIO | Fully asynchronous ASGI request pipeline |
| **ORM / Data Access** | SQLAlchemy 2.0.28+ with Alembic 1.13.1 | `TenantRepository[T]` with company_id enforcement |
| **Frontend Runtime** | Node.js 20+ | Next.js 14.2.35 (React 18.3.1) |
| **Frontend Artifacts** | Static export & SSR | 7 static pages compiled; First Load JS: 111 kB |
| **Database Engines** | PostgreSQL 15+ (Prod) / SQLite 3 (Dev) | `backend/app/db/session.py` |
| **Active Test Baseline** | **124 passing tests** (Pytest 9.1.1) | Zero test failures, zero regressions from Checkpoints 6–11 |

---

## 3. Current Observability Baseline

Prior to Checkpoint 12, observability capabilities across the application were evaluated:

1. **Structured Logging:**
   * Handled by [`CorrelationIdMiddleware`](file:///d:/Antigravity/Footwear%20app/backend/app/middleware/correlation.py).
   * Generates single-line JSON log events containing `timestamp`, `level`, `correlation_id`, `request_id`, `endpoint`, `method`, `status_code`, and `latency_ms`.
   * Privacy boundary masks passwords, tokens, PAN numbers, and customer names (`[REDACTED]`, `[REDACTED_PII]`).
2. **Request Correlation:**
   * Injects `X-Correlation-ID` and `X-Request-ID` into request headers and outgoing response headers.
   * Auto-generates standard UUIDv4 identifiers when headers are omitted.
3. **Health Endpoints:**
   * Baseline had a single `GET /api/v1/health` endpoint querying `SELECT 1`.
   * Lacked container-standard liveness vs. readiness probe separation (addressed in Checkpoint 12).
4. **Audit Logging:**
   * [`AuditLogMiddleware`](file:///d:/Antigravity/Footwear%20app/backend/app/middleware/audit.py) records mutating operations (`POST`, `PUT`, `DELETE`) with user identity into `audit_log` table.

---

## 4. Known Technical Debt & Production Assumptions

1. **Rate Limiting:**
   * `BasicRateLimitMiddleware` operates via in-memory sliding window per application instance.
   * **Production Requirement:** Multi-instance horizontal scaling requires distributed rate limiting via Redis or Cloudflare/AWS WAF edge protection.
2. **Asynchronous Background Processing:**
   * Database backups currently trigger synchronously via subprocess execution in `backend/app/services/backup_service.py`.
   * **Production Requirement:** Scheduled background task runner (e.g. Celery / ARQ / Temporal or cloud cron triggers) for offloading heavy jobs.
3. **Frontend Supply-Chain Notice:**
   * `npm audit` flagged Next.js 14.2.35 advisories (Windows path traversal and AVIF image optimization). Documented in `docs/DEPENDENCY_SECURITY_AUDIT.md`.
