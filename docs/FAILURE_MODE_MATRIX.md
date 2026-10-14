# LIVO FOOTWEAR ERP — FAILURE MODE & GRACEFUL DEGRADATION MATRIX
**Checkpoint 12 — Observability, Performance, Reliability & Operational Readiness**  
*Document Version: 1.0.0 | Date: 2026-10-01*

---

## 1. Overview & Objective

This matrix documents the systematic failure modes, graceful degradation strategies, rollback policies, and data integrity guarantees of LIVO Footwear ERP across infrastructure, network, and application faults.

---

## 2. Failure Mode Analysis

| Failure Scenario | User-Visible Behavior | Server Behavior | Rollback Behavior | Retry Policy | Logging & Alerting | Data Integrity Invariant |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Database Temporarily Unavailable** | Toast error: "System temporarily unavailable. Please retry." | Readiness probe `/health/ready` returns HTTP 503; API endpoints return HTTP 500 with `request_id`. | Active transactions aborted immediately. | Client exponential backoff (1s, 2s, 4s). | ERROR logged with `correlation_id`; DB connection alert triggered. | Zero partial writes; uncommitted records wiped by DB rollback. |
| **2. Database Slow / High Latency** | Loading skeleton / spinner remains active; no duplicate submit possible. | Connection pool holds connection up to `pool_timeout=10s`; statement timeout aborts queries > 30s. | Aborted queries roll back automatically. | Safe read retries; mutations retry only with identical idempotency key. | WARN logged for requests > 500ms; latency telemetry captured. | Invariants protected by row locks and transaction boundaries. |
| **3. Authentication Service / Token Expiration** | User redirected to `/login` with notification: "Session expired. Please log in again." | API returns HTTP 401 Unauthorized with detail `"Invalid or expired session token."`. | N/A (Read-only authentication check). | Re-login required; queued offline mutations retained in IndexedDB. | WARN logged in access stream; failed logins tracked. | Unauthenticated requests cannot mutate any state. |
| **4. Network Interruption Mid-Request** | Offline banner displays: "Working offline. Changes queued locally." | Server transaction completes or rolls back cleanly depending on TCP socket disconnect timing. | If commit succeeded, state is saved; if interrupted before commit, rolled back. | Client replays request using cached `X-Idempotency-Key`. | Access log records connection drop or HTTP status. | **Exactly-once:** Idempotency middleware deduplicates retry. |
| **5. Frontend Device Completely Offline** | UI switches to Offline Mode; orders/movements save to local IndexedDB. | Server receives no traffic. | N/A | Queue pauses; automatic drain resumes upon connectivity restoration. | Client console logs offline queue additions. | Tenant-partitioned queue with conflict preservation. |
| **6. Background Backup Subprocess Failure** | Admin dashboard Settings tab flags: "Last backup failed: [error]". | `run_database_backup()` catches exception, writes failure JSON to `latest_status.json`, logs error. | Backup file discarded or cleaned up. | SRE manual trigger or scheduled hourly retry. | ERROR logged in `app.backup`; alert dispatched. | Operational database is unaffected; continues serving traffic. |
| **7. Cloud Storage (R2/B2) Unreachable** | Admin dashboard reports: "Local backup succeeded; Cloud sync warning." | Backup saved to local disk `backend/backups/`; warning attached to status report. | Local snapshot retained. | Retries cloud upload during next scheduled window. | WARN logged with cloud connection error. | Zero data loss; local snapshot remains fully recoverable. |
| **8. Malformed Inbound Request Body** | HTTP 422 Unprocessable Content with specific field validation error. | Pydantic model rejects payload before database transaction opens. | No transaction opened; zero DB mutation. | Client must correct payload before retrying. | INFO/WARN logged in access log. | Invalid data can never enter database. |
| **9. Expired Idempotency Lease** | Subsequent request re-claims expired processing lease safely. | Idempotency middleware inspects `locked_until`; stale processing state transitions to new attempt. | Old aborted transaction was already rolled back. | Allowed after lease expiry (60s). | INFO logged: "Recovered stale idempotency lease". | Prevents permanent deadlock of abandoned client operations. |
| **10. Concurrent Conflicting Mutation (Stock/Credit)** | HTTP 422 or 409 Conflict with detailed resolution message. | Pessimistic lock or advisory lock detects violation; raises HTTPException. | Transaction rolls back immediately. | User reviews fresh balance and adjusts requested quantity. | WARN logged with conflict details. | **Zero negative stock:** On-hand balance cannot breach zero. |
| **11. Accidental Table Deletion** | System placed into maintenance mode. | SRE initiates Neon Point-in-Time Recovery (PITR) to exact minute prior to deletion. | Whole branch restored from WAL history. | Automated restoration drill harness verifies 100% parity. | Critical alert; incident post-mortem filed. | Full ledger parity restored within target RTO <= 15m. |
