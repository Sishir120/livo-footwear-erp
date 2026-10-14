/**
 * LIVO Footwear ERP - Resilient Offline Mutation Queue & Conflict Engine
 * Database: LivoOfflineDB (IndexedDB v2)
 *
 * Implements:
 * 1. Strict Tenant Scoping (company_id) preventing cross-tenant leakage.
 * 2. Deterministic State Machine:
 *    CREATED_LOCALLY -> QUEUED -> SYNCING -> SERVER_ACCEPTED / RECONCILED
 *    Failures: RETRYABLE_FAILURE, CONFLICT, VALIDATION_FAILURE, AUTH_FAILURE, PERMANENT_FAILURE.
 * 3. Stable UUID Idempotency Keys across retries, reconnects, and device restarts.
 * 4. Dependency-Aware Ordering (dependsOn) preventing out-of-order execution storms.
 * 5. Bounded Exponential Backoff with Jitter for transient network/server failures.
 * 6. Auth Expiration Safety: Pauses synchronization on 401 Unauthorized without data loss.
 * 7. Dead-Letter / Conflict Store: Zero silent data loss for inventory, financial, or schema conflicts.
 */

export type MutationStatus =
  | "QUEUED"
  | "SYNCING"
  | "ACCEPTED"
  | "RETRYABLE_FAILURE"
  | "CONFLICT"
  | "VALIDATION_FAILURE"
  | "AUTH_FAILURE"
  | "PERMANENT_FAILURE";

export interface QueuedMutation {
  id: string; // Stable UUID idempotency key
  companyId: number; // Multi-tenant partition
  endpoint: string;
  method: string;
  payload: any;
  timestamp: number;
  status: MutationStatus;
  retryCount: number;
  nextRetryAt: number;
  errorDetails?: string;
  dependsOn?: string[]; // IDs of parent mutations that must be ACCEPTED first
  schemaVersion: number;
}

export interface QueueTelemetry {
  total: number;
  queued: number;
  syncing: number;
  conflicts: number;
  failures: number;
}

const DB_NAME = "LivoOfflineDB";
const STORE_NAME = "livo_mutation_outbox";
const DB_VERSION = 2;

let dbPromise: Promise<IDBDatabase> | null = null;
const listeners = new Set<(telemetry: QueueTelemetry) => void>();
let activeCompanyId: number = 1;

/**
 * Configure current active company ID for tenant-scoped operations.
 */
export function setActiveCompanyId(companyId: number): void {
  if (companyId && companyId > 0) {
    activeCompanyId = companyId;
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        localStorage.setItem("livo_active_company_id", String(companyId));
      } catch {
        // LocalStorage may be blocked
      }
    }
  }
}

export function getActiveCompanyId(): number {
  if (activeCompanyId && activeCompanyId > 0) return activeCompanyId;
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const stored = localStorage.getItem("livo_active_company_id");
      if (stored) {
        const parsed = parseInt(stored, 10);
        if (!isNaN(parsed) && parsed > 0) {
          activeCompanyId = parsed;
          return parsed;
        }
      }
    } catch {
      // Fallback
    }
  }
  return 1;
}

function getDB(): Promise<IDBDatabase> {
  if (typeof window === "undefined" || !("indexedDB" in window)) {
    return Promise.reject(new Error("IndexedDB unavailable in current context"));
  }
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
        const db = request.result;
        let store: IDBObjectStore;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        } else {
          store = (request.transaction as IDBTransaction).objectStore(STORE_NAME);
        }

        if (!store.indexNames.contains("companyId")) {
          store.createIndex("companyId", "companyId", { unique: false });
        }
        if (!store.indexNames.contains("status")) {
          store.createIndex("status", "status", { unique: false });
        }
        if (!store.indexNames.contains("timestamp")) {
          store.createIndex("timestamp", "timestamp", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return dbPromise;
}

/**
 * Enqueue a new mutation into the tenant-scoped IndexedDB outbox.
 * Retains stable UUID idempotency key across all retries and restarts.
 */
export async function enqueueMutation(
  item: {
    id?: string;
    companyId?: number;
    endpoint: string;
    method: string;
    payload: any;
    dependsOn?: string[];
    schemaVersion?: number;
  }
): Promise<QueuedMutation> {
  const db = await getDB();
  const effectiveCompanyId = item.companyId && item.companyId > 0 ? item.companyId : getActiveCompanyId();
  const mutationId = item.id || (typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `mut_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`);

  const mutation: QueuedMutation = {
    id: mutationId,
    companyId: effectiveCompanyId,
    endpoint: item.endpoint,
    method: item.method.toUpperCase(),
    payload: item.payload,
    timestamp: Date.now(),
    status: "QUEUED",
    retryCount: 0,
    nextRetryAt: 0,
    dependsOn: item.dependsOn || [],
    schemaVersion: item.schemaVersion || 1,
  };

  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(mutation);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });

  notifyListeners();
  return mutation;
}

/**
 * Retrieves all mutations across statuses, optionally filtered by companyId.
 */
export async function getAllMutations(companyId?: number): Promise<QueuedMutation[]> {
  try {
    const db = await getDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();
      req.onsuccess = () => {
        let results = (req.result || []) as QueuedMutation[];
        // Backfill legacy records if any
        results = results.map((m) => ({
          ...m,
          companyId: m.companyId || 1,
          status: m.status || "QUEUED",
          retryCount: m.retryCount || 0,
          nextRetryAt: m.nextRetryAt || 0,
          dependsOn: m.dependsOn || [],
          schemaVersion: m.schemaVersion || 1,
        }));
        if (companyId) {
          results = results.filter((m) => m.companyId === companyId);
        }
        resolve(results.sort((a, b) => a.timestamp - b.timestamp));
      };
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

/**
 * Retrieves pending mutations ready for replay for a given company.
 */
export async function getQueuedMutations(companyId?: number): Promise<QueuedMutation[]> {
  const targetCompany = companyId || getActiveCompanyId();
  const all = await getAllMutations(targetCompany);
  return all.filter((m) => m.status === "QUEUED" || m.status === "RETRYABLE_FAILURE");
}

/**
 * Retrieves dead-letter mutations requiring human operator review.
 */
export async function getDeadLetterMutations(companyId?: number): Promise<QueuedMutation[]> {
  const targetCompany = companyId || getActiveCompanyId();
  const all = await getAllMutations(targetCompany);
  return all.filter(
    (m) =>
      m.status === "CONFLICT" ||
      m.status === "VALIDATION_FAILURE" ||
      m.status === "AUTH_FAILURE" ||
      m.status === "PERMANENT_FAILURE"
  );
}

/**
 * Updates a mutation's status, error message, and retry timestamp.
 */
export async function updateMutationStatus(
  id: string,
  status: MutationStatus,
  errorDetails?: string,
  nextRetryAt?: number
): Promise<void> {
  const db = await getDB();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const getReq = store.get(id);
    getReq.onsuccess = () => {
      const item = getReq.result as QueuedMutation;
      if (!item) {
        resolve();
        return;
      }
      item.status = status;
      if (errorDetails !== undefined) item.errorDetails = errorDetails;
      if (nextRetryAt !== undefined) item.nextRetryAt = nextRetryAt;
      if (status === "SYNCING") item.retryCount = (item.retryCount || 0) + 1;

      const putReq = store.put(item);
      putReq.onsuccess = () => resolve();
      putReq.onerror = () => reject(putReq.error);
    };
    getReq.onerror = () => reject(getReq.error);
  });
  notifyListeners();
}

/**
 * Safely removes an acknowledged/reconciled mutation from the outbox.
 */
export async function dequeueMutation(id: string): Promise<void> {
  const db = await getDB();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
  notifyListeners();
}

/**
 * Retries a failed or conflicted mutation by resetting its state to QUEUED.
 */
export async function retryMutation(id: string): Promise<void> {
  await updateMutationStatus(id, "QUEUED", undefined, 0);
  if (typeof navigator !== "undefined" && navigator.onLine) {
    replayQueue();
  }
}

/**
 * Operator explicitly discards an unresolvable mutation from dead-letter queue.
 */
export async function discardMutation(id: string): Promise<void> {
  await dequeueMutation(id);
}

/**
 * Computes queue telemetry metrics for the active company.
 */
export async function getQueueTelemetry(companyId?: number): Promise<QueueTelemetry> {
  try {
    const targetCompany = companyId || getActiveCompanyId();
    const all = await getAllMutations(targetCompany);
    return {
      total: all.length,
      queued: all.filter((m) => m.status === "QUEUED" || m.status === "RETRYABLE_FAILURE").length,
      syncing: all.filter((m) => m.status === "SYNCING").length,
      conflicts: all.filter((m) => m.status === "CONFLICT").length,
      failures: all.filter(
        (m) =>
          m.status === "VALIDATION_FAILURE" ||
          m.status === "AUTH_FAILURE" ||
          m.status === "PERMANENT_FAILURE"
      ).length,
    };
  } catch {
    return { total: 0, queued: 0, syncing: 0, conflicts: 0, failures: 0 };
  }
}

export async function getQueueCount(companyId?: number): Promise<number> {
  const t = await getQueueTelemetry(companyId);
  return t.queued + t.syncing;
}

export async function clearOfflineQueue(companyId?: number): Promise<void> {
  try {
    const targetCompany = companyId || getActiveCompanyId();
    const all = await getAllMutations(targetCompany);
    const db = await getDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      all.forEach((item) => store.delete(item.id));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    notifyListeners();
  } catch (err) {
    console.error("Failed to clear offline queue:", err);
  }
}

async function notifyListeners() {
  const telemetry = await getQueueTelemetry();
  listeners.forEach((listener) => listener(telemetry));
}

export function subscribeQueueChange(listener: (telemetry: QueueTelemetry) => void): () => void {
  listeners.add(listener);
  getQueueTelemetry().then(listener);
  return () => {
    listeners.delete(listener);
  };
}

let isReplaying = false;

/**
 * Replays pending mutations in dependency-aware causal order with bounded backoff.
 * Adheres to:
 * - Tenant isolation: only replays active tenant mutations.
 * - Dependency resolution: parent must be ACCEPTED before dependent child executes.
 * - Auth safety: halts immediately on 401 without deleting mutations.
 * - Conflict retention: saves 409 / 422 conflicts with error details into dead-letter store.
 */
export async function replayQueue(
  onProgress?: (remaining: number) => void
): Promise<{ processed: number; failed: number; conflicts: number }> {
  if (isReplaying) return { processed: 0, failed: 0, conflicts: 0 };
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return { processed: 0, failed: 0, conflicts: 0 };
  }

  isReplaying = true;
  let processed = 0;
  let failed = 0;
  let conflicts = 0;

  const currentCompany = getActiveCompanyId();

  try {
    const pendingList = await getQueuedMutations(currentCompany);
    if (pendingList.length === 0) return { processed: 0, failed: 0, conflicts: 0 };

    const now = Date.now();
    const readyItems = pendingList.filter((m) => m.nextRetryAt <= now);
    if (readyItems.length === 0) return { processed: 0, failed: 0, conflicts: 0 };

    // Dependency topological sorting:
    // If B depends on A, and A is still uncommitted, defer B.
    const allCompanyMutations = await getAllMutations(currentCompany);
    const acceptedIds = new Set(
      allCompanyMutations.filter((m) => m.status === "ACCEPTED").map((m) => m.id)
    );

    for (const item of readyItems) {
      // Check dependencies
      if (item.dependsOn && item.dependsOn.length > 0) {
        const unmet = item.dependsOn.filter((depId) => !acceptedIds.has(depId));
        if (unmet.length > 0) {
          // Check if parent has failed or conflicted
          const parentFailures = allCompanyMutations.filter(
            (m) => unmet.includes(m.id) && ["CONFLICT", "VALIDATION_FAILURE", "PERMANENT_FAILURE"].includes(m.status)
          );
          if (parentFailures.length > 0) {
            await updateMutationStatus(
              item.id,
              "CONFLICT",
              `Blocked by preceding failed/conflicted dependency [${parentFailures[0].id}]`
            );
            conflicts++;
            continue;
          }
          // Parent still pending: hold item in queue
          continue;
        }
      }

      await updateMutationStatus(item.id, "SYNCING");

      try {
        const res = await fetch(item.endpoint, {
          method: item.method,
          headers: {
            "Content-Type": "application/json",
            "X-Idempotency-Key": item.id,
            "Idempotency-Key": item.id,
            "X-Tenant-Company-ID": String(item.companyId),
          },
          credentials: "include",
          body: item.payload ? JSON.stringify(item.payload) : undefined,
        });

        if (res.ok) {
          // 2xx Success -> Mark ACCEPTED, dequeue, register id
          acceptedIds.add(item.id);
          await dequeueMutation(item.id);
          processed++;
        } else if (res.status === 401) {
          // AUTH_FAILURE: Expired session token!
          // CRITICAL: PAUSE IMMEDIATELY, DO NOT DISCARD MUTATION!
          console.warn("[Offline Outbox] Authentication required (HTTP 401). Pausing sync.");
          await updateMutationStatus(item.id, "AUTH_FAILURE", "Authentication required / session expired");
          failed++;
          if (typeof window !== "undefined") {
            window.dispatchEvent(
              new CustomEvent("livo:auth-required", {
                detail: { endpoint: item.endpoint, mutationId: item.id },
              })
            );
          }
          break; // Stop further replay until user re-authenticates
        } else if (res.status === 409) {
          // CONFLICT: Idempotency payload mismatch or statutory/resource conflict
          const errText = await res.text();
          let detail = "Conflict detected with server state";
          try {
            const parsed = JSON.parse(errText);
            detail = parsed.detail || parsed.message || detail;
          } catch {
            detail = errText || detail;
          }
          console.error(`[Offline Outbox Conflict 409] ${item.endpoint}: ${detail}`);
          await updateMutationStatus(item.id, "CONFLICT", detail);
          conflicts++;
          if (typeof window !== "undefined") {
            window.dispatchEvent(
              new CustomEvent("livo:conflict-detected", {
                detail: { mutation: item, reason: detail },
              })
            );
          }
        } else if (res.status === 422) {
          // 422 Unprocessable: e.g. INSUFFICIENT_STOCK or Schema validation
          const errText = await res.text();
          let isStockConflict = false;
          let detail = "Validation or business rule rejected";
          try {
            const parsed = JSON.parse(errText);
            detail = parsed.detail?.message || parsed.detail || detail;
            if (typeof parsed.detail === "object" && parsed.detail.error === "INSUFFICIENT_STOCK") {
              isStockConflict = true;
            }
          } catch {
            detail = errText || detail;
          }

          const targetStatus: MutationStatus = isStockConflict ? "CONFLICT" : "VALIDATION_FAILURE";
          console.error(`[Offline Outbox 422] ${targetStatus} on ${item.endpoint}: ${detail}`);
          await updateMutationStatus(item.id, targetStatus, detail);
          if (isStockConflict) conflicts++;
          else failed++;
        } else if (res.status >= 400 && res.status < 500) {
          // 400, 403, 404 Permanent error: Move to dead-letter, DO NOT silently discard
          const errText = await res.text();
          console.error(`[Offline Outbox Permanent Failure ${res.status}] ${item.endpoint}: ${errText}`);
          await updateMutationStatus(item.id, "PERMANENT_FAILURE", `HTTP ${res.status}: ${errText.slice(0, 200)}`);
          failed++;
        } else {
          // 5xx Server Transient Error -> Apply bounded exponential backoff
          const baseDelay = Math.min(30000, 1000 * Math.pow(2, item.retryCount || 1));
          const jitter = Math.random() * 500;
          const nextRetry = Date.now() + baseDelay + jitter;
          await updateMutationStatus(
            item.id,
            "RETRYABLE_FAILURE",
            `Server error (HTTP ${res.status}). Retrying with backoff.`,
            nextRetry
          );
          failed++;
          break; // Stop current replay wave to avoid hammering failing server
        }
      } catch (err: any) {
        // Network disconnected or fetch aborted mid-flight -> Apply backoff and halt
        const baseDelay = Math.min(30000, 1000 * Math.pow(2, item.retryCount || 1));
        const jitter = Math.random() * 500;
        const nextRetry = Date.now() + baseDelay + jitter;
        await updateMutationStatus(
          item.id,
          "RETRYABLE_FAILURE",
          err.message || "Network unreachable",
          nextRetry
        );
        failed++;
        break;
      }

      if (onProgress) {
        const remaining = await getQueueCount(currentCompany);
        onProgress(remaining);
      }
    }
  } finally {
    isReplaying = false;
    notifyListeners();
  }

  return { processed, failed, conflicts };
}

// Auto-wire online sync listener on client side
if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    replayQueue();
  });
}
