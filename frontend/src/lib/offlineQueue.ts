/**
 * LIVO Footwear ERP - Offline Mutation Queue
 * Manages client-side terminal outbox in browser IndexedDB.
 * Survives factory Wi-Fi dropouts and replays sequentially with idempotency keys upon reconnection.
 */

export interface QueuedMutation {
  id: string;
  endpoint: string;
  method: string;
  payload: any;
  timestamp: number;
}

const DB_NAME = "LivoOfflineDB";
const STORE_NAME = "livo_mutation_outbox";
const DB_VERSION = 1;

let dbPromise: Promise<IDBDatabase> | null = null;
const listeners = new Set<(count: number) => void>();

function getDB(): Promise<IDBDatabase> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("IndexedDB unavailable in SSR context"));
  }
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  return dbPromise;
}

export async function enqueueMutation(
  item: Omit<QueuedMutation, "id" | "timestamp">
): Promise<QueuedMutation> {
  const db = await getDB();
  const mutation: QueuedMutation = {
    id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `mut_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    endpoint: item.endpoint,
    method: item.method,
    payload: item.payload,
    timestamp: Date.now(),
  };

  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.add(mutation);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });

  notifyListeners();
  return mutation;
}

export async function getQueuedMutations(): Promise<QueuedMutation[]> {
  try {
    const db = await getDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();
      req.onsuccess = () => {
        const sorted = (req.result as QueuedMutation[]).sort((a, b) => a.timestamp - b.timestamp);
        resolve(sorted);
      };
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

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

export async function getQueueCount(): Promise<number> {
  try {
    const db = await getDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return 0;
  }
}

export async function clearOfflineQueue(): Promise<void> {
  try {
    const db = await getDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
    notifyListeners();
  } catch (err) {
    console.error("Failed to clear offline queue:", err);
  }
}

async function notifyListeners() {
  const count = await getQueueCount();
  listeners.forEach((listener) => listener(count));
}

export function subscribeQueueChange(listener: (count: number) => void): () => void {
  listeners.add(listener);
  getQueueCount().then(listener);
  return () => {
    listeners.delete(listener);
  };
}

let isReplaying = false;

export async function replayQueue(
  onProgress?: (remaining: number) => void
): Promise<{ processed: number; failed: number }> {
  if (isReplaying) return { processed: 0, failed: 0 };
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return { processed: 0, failed: 0 };
  }

  isReplaying = true;
  let processed = 0;
  let failed = 0;

  try {
    const queue = await getQueuedMutations();
    for (const item of queue) {
      try {
        const res = await fetch(item.endpoint, {
          method: item.method,
          headers: {
            "Content-Type": "application/json",
            "X-Idempotency-Key": item.id,
          },
          body: item.payload ? JSON.stringify(item.payload) : undefined,
        });

        if (res.ok || res.status === 409) {
          // 2xx Success or 409 Conflict (already applied) -> dequeue
          await dequeueMutation(item.id);
          processed++;
        } else if (res.status >= 400 && res.status < 500) {
          // Permanent validation error -> dequeue to prevent blocking outbox
          console.error("Outbox permanent failure (discarded):", item, await res.text());
          await dequeueMutation(item.id);
          failed++;
        } else {
          // 5xx Server or network error -> stop replaying, wait for stable connection
          failed++;
          break;
        }
      } catch (err) {
        failed++;
        break; // Network still down, abort replay loop
      }

      if (onProgress) {
        const remaining = await getQueueCount();
        onProgress(remaining);
      }
    }
  } finally {
    isReplaying = false;
    notifyListeners();
  }

  return { processed, failed };
}

// Auto-wire online sync listener on client side
if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    replayQueue();
  });
}
