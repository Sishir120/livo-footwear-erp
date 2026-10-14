# LIVO FOOTWEAR ERP — PRODUCTION MONITORING DESIGN
**Checkpoint 14 — Architecture, Metrics Specification & Telemetry Flow**  
*Date: 2026-10-01*

---

## 1. Observability Architecture Overview

The LIVO Footwear ERP monitoring subsystem follows a lightweight, high-performance architecture optimized for single-host or clustered container environments without introducing heavy external dependencies.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT REQUEST LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────────────────┘
      HTTP Request (Browser / PWA / API Client)
         │
         ▼
  [CorrelationIdMiddleware]
     ├── Sanitize X-Request-ID & X-Correlation-ID (Regex: ^[A-Za-z0-9_\-\.]{1,64}$)
     ├── Bind to contextvars (request_id_var, correlation_id_var)
     ├── Measure execution latency (perf_counter)
     └── Emit structured JSON access log
         │
         ▼
  [FastAPI Route Handler & Exception Handlers]
     ├── Normalized ErrorCode Taxonomy (VALIDATION_ERROR, RATE_LIMITED, etc.)
     ├── Sanitize 500 responses (Zero leakage of internal Python exception details)
     └── Emit business metrics to MetricsRegistry
         │
         ▼
  [SQLAlchemy Database Layer]
     ├── Event hooks: before_cursor_execute & after_cursor_execute
     ├── Slow query threshold (> 500ms) with parameter-masked SQL fingerprints
     ├── Connection pool checkout/checkin tracking & pool exhaustion alerts
     └── Rollback and DB execution error counting
         │
         ▼
  [MetricsRegistry (In-Memory Singleton)]
     ├── Thread-safe counter and gauge storage
     ├── Strictly bounded label cardinality (No IDs, SKUs, or customer names)
     └── Plain-text Prometheus exposition via GET /api/v1/metrics
```

---

## 2. Standard Metric Catalog

### 2.1 Authentication & Security Metrics
* `auth_attempts_total{status="success|failure"}`: Tracks successful logins and brute-force attempts.
* `rate_limited_requests_total{route="auth_login"}`: Tracks clients hitting sliding-window rate limits.

### 2.2 Business & Financial Ledger Metrics
* `sales_orders_total{status="created|failed"}`: Throughput of sales order issuance.
* `invoices_total{status="issued|failed"}`: Document sequencing and invoice creation operations.
* `inventory_movements_total{direction="in|out"}`: Movements appended to stock ledger.
* `receivables_payments_total{status="recorded|failed"}`: Customer payments applied against receivables.

### 2.3 Offline Synchronization & Idempotency Metrics
* `offline_sync_mutations_total{state="..."}`: Mutations partitioned by state machine status (`QUEUED`, `ACCEPTED`, `RETRYABLE_FAILURE`, `CONFLICT`, `VALIDATION_FAILURE`, `AUTH_FAILURE`, `PERMANENT_FAILURE`).
* `idempotency_requests_total{type="new|replayed|conflict"}`: Distinguishes fresh mutations, replayed requests, and fingerprint conflicts.

### 2.4 Database & Infrastructure Metrics
* `db_queries_total`: Total SQL queries executed by the application.
* `db_slow_queries_total`: Queries whose latency exceeded 500ms.
* `db_errors_total`: Database API errors and connection drops.
* `db_rollbacks_total`: Explicit transaction rollbacks executed.
* `db_pool_utilization`: Ratio of active checked-out connections to total pool capacity.

### 2.5 Backup & Disaster Recovery Metrics
* `backup_operations_total{status="success|failure"}`: Outcome of automated and manual backups.
* `backup_age_seconds`: Age in seconds since the most recent successful database dump.
* `backup_restore_verified`: Gauge flag (1.0 = verified, 0.0 = unverified) indicating restore test validity.

---

## 3. Log Formatting & Structured Fields

All log records are emitted as single-line JSON with the following canonical structure:

```json
{
  "timestamp": "2026-10-01T15:00:00.123456+00:00",
  "level": "INFO",
  "service": "livo-footwear-erp",
  "environment": "production",
  "logger": "livo_erp",
  "event": "http_request_complete",
  "request_id": "941ae243-32ff-46e7-88c0-3efab77044a2",
  "correlation_id": "941ae243-32ff-46e7-88c0-3efab77044a2",
  "company_id": "[REDACTED]",
  "user_id": 42,
  "route": "/api/v1/sales/orders",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 24.5,
  "error_code": null
}
```

### Privacy & PII Redaction
- Automatic recursion across nested JSON structures.
- Masked keywords: `password`, `token`, `secret`, `authorization`, `pan`, `pan_number`, `cookie`.
- Client names mapped to `[REDACTED_PII]`.
- Regex scrubbing of Bearer tokens (`Bearer [REDACTED]`) and connection string passwords.

---

## 4. Scraping & Integration Specification

1. **Prometheus Scraping Target:**
   ```yaml
   scrape_configs:
     - job_name: "livo-erp"
       scrape_interval: 15s
       metrics_path: "/api/v1/metrics"
       static_configs:
         - targets: ["backend:8000"]
   ```

2. **JSON Diagnostics Endpoint:**
   - URL: `GET /api/v1/metrics/json`
   - Purpose: Machine-readable snapshot for supervisor cockpits, automated health scripts, and internal monitoring dashboards.
