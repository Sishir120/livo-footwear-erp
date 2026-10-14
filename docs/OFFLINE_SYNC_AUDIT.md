# LIVO FOOTWEAR ERP — OFFLINE SYNCHRONIZATION AUDIT (CHECKPOINT 9)

**Audited At:** 2026-10-01  
**Target System:** LIVO Footwear ERP (Production, Sales, Inventory, Receivables, Offline Terminal Outbox)  
**Standard:** Enterprise Offline Synchronization, Conflict Resolution & Statutory Reconciliation  

---

## 1. Executive Summary

LIVO Footwear ERP is deployed across industrial manufacturing clusters in Biratnagar and distribution hubs in Kathmandu, Nepal. Factory floor networks experience frequent Wi-Fi packet drops, power cuts, and latency spikes. 

Prior to Checkpoint 9:
1. **Production Terminal Sync (`offlineDb.ts`)**: Built specifically for shop-floor production batch logging, utilizing IndexedDB database `livo_factory_offline_v1`. It buffered offline batch records with UUID idempotency keys, drained them sequentially via `POST /api/v1/production/sync/draft`, and logged results in `production_sync_logs`.
2. **Generic API Outbox (`offlineQueue.ts`)**: Intercepted mutating HTTP requests (`POST`, `PUT`, `PATCH`, `DELETE`) via `apiFetch` in `api.ts` when the browser is disconnected or experiences a network error mid-flight. Buffered requests in `LivoOfflineDB.livo_mutation_outbox`.

### Critical Vulnerabilities & Gaps Identified in Existing Implementation:
* **G-01: Silent Deletion on 4xx/409 (Data Loss Danger)**: In `offlineQueue.ts`, any response with status `409 Conflict` or `400..499` was immediately dequeued via `await dequeueMutation(item.id)`. This caused permanent data loss for invalid, conflicted, or schema-mismatched business transactions instead of routing them to a Dead-Letter / Conflict inspection state.
* **G-02: Missing Multi-Tenant Scoping in Local Outbox**: The IndexedDB store `livo_mutation_outbox` had no `company_id` partition. If an operator logged into Company A, queued offline transactions, and subsequently switched to Company B, replay would cross-synchronize Company A's payloads under Company B's session.
* **G-03: Auth Expiration Crash & Drop**: When network restored with an expired session token, server returned `401 Unauthorized`. The queue classified 401 as a 4xx error and permanently discarded the queued mutations. It did not pause synchronization or initiate token refresh/re-authentication.
* **G-04: Lack of Dependency Tracking (`depends_on`)**: The queue replayed solely by wall-clock timestamp `sort((a, b) => a.timestamp - b.timestamp)`. Dependent sequences (e.g. Sales Order -> Invoice -> Payment, or Stock In -> Stock Out) submitted out of order caused foreign key or state errors.
* **G-05: Missing Exponential Backoff & Jitter**: Replay loops had no bounded backoff policy, retrying immediately on network blips.
* **G-06: Unstructured Conflict Contract**: Server endpoints returned heterogeneous conflict messages without a standardized conflict envelope (`resource`, `operation_id`, `server_version`, `reason`, `resolution`).
* **G-07: Dual Queue Fragmentation**: Disconnected architecture between `offlineDb.ts` (production batches) and `offlineQueue.ts` (generic mutations), resulting in fragmented UI telemetry in `NetworkStatusBadge.tsx` and `AppShell.tsx`.

---

## 2. File & Component Inventory

| Component / Layer | File Path | Existing Role & Audit Assessment |
| :--- | :--- | :--- |
| **Generic Outbox Queue** | `frontend/src/lib/offlineQueue.ts` | **Flawed**. Stores `QueuedMutation` in IndexedDB. Discards 4xx/409. Lacks tenant isolation, backoff, dependency metadata, and lifecycle states. |
| **Production Draft Store** | `frontend/src/lib/offlineDb.ts` | **Partially Hardened**. Stores `ProductionDraft` in IndexedDB `livo_factory_offline_v1`. Handles `POST /api/v1/production/sync/draft`. Has rudimentary status transitions. |
| **API Client Interceptor** | `frontend/src/lib/api.ts` | **Active**. Wraps fetch, attaches stable UUID idempotency keys, intercepts offline/dropped mutating requests, returns optimistic 202 Accepted. |
| **Network Status Badge** | `frontend/src/components/NetworkStatusBadge.tsx` | **Partial**. Displays online/offline/syncing badge and draft drawer. Only monitored `offlineDb.ts`, blind to `offlineQueue.ts`. |
| **App Shell & Auto-Sync** | `frontend/src/components/AppShell.tsx` | **Active**. Auto-wires `online` event listener to trigger `replayQueue()`. |
| **Server Idempotency** | `backend/app/middleware/idempotency.py` | **Hardened (CP8)**. Intercepts incoming `Idempotency-Key`, acquires advisory lock, enforces payload SHA-256 fingerprinting, caches responses. |
| **Production Sync Endpoint** | `backend/app/api/v1/production.py` | **Hardened (CP8)**. `POST /sync/draft` verifies payload hash, rejects non-integer sizes, allocates batch number, appends stock movements. |
| **Stock Ledger Engine** | `backend/app/api/v1/stock.py` | **Hardened (CP6)**. Enforces non-negative stock balance via row lock (`with_for_update`) and advisory lock. Raises 422 `INSUFFICIENT_STOCK`. |
| **AR & Invoices Engine** | `backend/app/api/v1/invoices.py`, `receivables.py` | **Hardened (CP6/7)**. Monotonic sequence allocation, double-entry AR subledger, prevents duplicate active VAT invoices (409 Conflict). |

---

## 3. State Machine Analysis & Formalization

### 3.1 Offline Operation Lifecycle

```
[Local Mutation Initiated]
          │
          ▼
   CREATED_LOCALLY (Assigned stable UUID idempotency_key, tenant_id, schema_version)
          │
          ▼
       QUEUED (Persisted in tenant-scoped IndexedDB store)
          │
     ┌────┴─────────────────────────────┐
     ▼                                  ▼
[Offline/Waiting]             [Network Detected & Online]
     │                                  │
     │                                  ▼
     │                               SYNCING (Leased, active in-flight request)
     │                                  │
     │         ┌────────────────────────┼────────────────────────┐
     │         ▼                        ▼                        ▼
     │   [HTTP 2xx/201]           [HTTP 409/Conflict]     [Network Drop/503]
     │         │                        │                        │
     │         ▼                        ▼                        ▼
     │  SERVER_ACCEPTED              CONFLICT            RETRYABLE_FAILURE
     │         │                        │                        │
     │         ▼                        │                (Apply Exponential
     │    ACKNOWLEDGED                  │                 Backoff + Jitter)
     │         │                        │                        │
     │         ▼                        │                        ▼
     │    RECONCILED                    │                     QUEUED
     │ (Dequeued / Archived)            │
     │                                  ▼
     │                     DEAD-LETTER / FAILED QUEUE
     │                     (Requires Operator Review)
     │                                  │
     │         ┌────────────────────────┴────────────────────────┐
     │         ▼                                                 ▼
     │   Manual Retry                                         Discard
     └─────────┘
```

### 3.2 Error & Failure State Classification

| Failure State | HTTP / Error Codes | System Action | Terminal Action |
| :--- | :--- | :--- | :--- |
| `RETRYABLE_FAILURE` | Network drop, 502, 503, 504, Timeout | Increment `retry_count`, compute exponential backoff with jitter, retain in queue. | Remains `QUEUED` until max retry limit (e.g. 10 attempts). |
| `AUTH_FAILURE` | 401 Unauthorized | **PAUSE SYNC IMMEDIATELY**. Do not discard. Notify user to renew session or refresh token. | Unpause and retry after re-authentication. |
| `CONFLICT` | 409 Conflict, 422 Insufficient Stock | Move to `CONFLICT`. Preserve payload, record server rejection reason and version snapshot. | Operator review via Offline Drawer: resolve or discard. |
| `VALIDATION_FAILURE` | 400 Bad Request, 422 Unprocessable (Schema) | Mark as `VALIDATION_FAILURE`. Move to Dead-Letter. Do not retry automatically. | Operator inspection. |
| `PERMANENT_FAILURE` | 403 Forbidden, 404 Missing Resource | Mark as `PERMANENT_FAILURE`. Move to Dead-Letter. | Operator inspection. |
| `EXPIRED` | TTL exceeded (> 7 days without sync) | Mark as `EXPIRED`. Quarantine for audit. | Super-admin purge or manual force-sync. |

---

## 4. Multi-Tenant Scoping & Storage Security

### 4.1 Tenant Isolation
Browser storage is inherently shared across tabs on the same origin (`localhost` or `erp.livogroup.com`). When a user switches tenants or logs out:
- Each offline mutation **must** store `company_id`.
- The synchronization worker **must only replay mutations matching the current authenticated user's `company_id`**.
- Cross-tenant queue pollution is strictly prevented by IndexedDB compound index `[company_id + status]` and tenant-filtered cursors.

### 4.2 Security Threat Model for Local Offline Storage
* **Threat 1: Credential Theft from LocalStorage**: Never store plaintext passwords, session secrets, or long-lived refresh tokens in unencrypted client storage. Auth relies on HTTP-only, SameSite cookies.
* **Threat 2: Offline Data Tampering**: An attacker modifying local quantities before sync cannot bypass server validation: all business invariants (stock non-negativity, Nepal VAT rates, price integrity) are re-validated server-side upon arrival.
* **Threat 3: Cross-Tenant Payload Leakage**: Solved by strict tenant partitioning in IndexedDB and server-side tenant authentication validation.

---

## 5. Causal Ordering & Dependency Resolution

Operations in an ERP are inherently order-sensitive:
1. **Inventory Movements**: `Stock Receipt (+INWARD)` must execute before `Stock Issue (-OUTWARD)`. If issued offline before receipt is synced, server rejects with `422 INSUFFICIENT_STOCK`.
2. **Sales & Financials**: `Sales Order Create` must execute before `Invoice Generation`, which must execute before `Payment Receipt Allocation`.
3. **Production Cycle**: `Batch Creation` must execute before `Material Usage` and `Quality Approval`.

### Dependency Metadata Contract:
```typescript
export interface QueuedMutation {
  id: string;               // Stable UUID idempotency key
  company_id: number;       // Tenant isolation scope
  endpoint: string;
  method: string;
  payload: any;
  timestamp: number;
  status: "QUEUED" | "SYNCING" | "RETRYABLE_FAILURE" | "CONFLICT" | "FAILED" | "ACCEPTED";
  retry_count: number;
  next_retry_at: number;    // Backoff timestamp
  error_details?: string;
  depends_on?: string[];    // Array of parent mutation IDs
  schema_version: number;   // E.g. 1
}
```

Replay must evaluate dependencies: if mutation B depends on mutation A, and mutation A is still in `QUEUED` or has entered `CONFLICT` or `FAILED`, mutation B must be held in `QUEUED` and never dispatched out of order.

---

## 6. Audit Verdict & Hardening Plan

| Item | Requirement | Action Required |
| :--- | :--- | :--- |
| **Audit Doc** | Point 1 | Created `docs/OFFLINE_SYNC_AUDIT.md`. |
| **State Machine** | Point 2 | Formalized state transitions and error classifications. |
| **Stable Identity** | Point 3 | Guarantee client UUID preserved through retries, restarts, and network reconnects. |
| **Tenant Isolation** | Point 21 | Add `company_id` indexing and tenant-filtered replay in IndexedDB. |
| **No Silent Deletion** | Point 17 | Dead-letter / conflict store for failed/rejected operations. |
| **Auth Handling** | Point 22 | Pause queue on 401, resume upon re-auth. |
| **Dependency Reordering** | Point 7, 8 | Topological / dependency-aware ordering (`depends_on`). |
| **Backoff & Jitter** | Point 16 | Bounded exponential backoff policy: `min(30s, 1s * 2^retry + jitter)`. |
| **Conflict Contract** | Point 14 | Standardized conflict response schema in backend and client handler. |
| **Reconciliation Verification** | Point 9, 10, 25, 26 | Backend test suite for multi-device sync, stock conflict, financial ledger integrity. |
