/**
 * LIVO Footwear ERP - Factory Floor Offline Database (IndexedDB)
 * Database: livo_factory_offline_v1
 * Provides durable local storage for product catalogs and offline production drafts
 * with UUID idempotency keys to guarantee zero duplicate batches upon reconnection.
 */

export interface CatalogItem {
  skuId: number;
  modelName: string;
  category: string;
  sizes: string[];
  cachedAt: string;
}

export type DraftSyncStatus = "PENDING" | "SYNCING" | "ACCEPTED" | "CONFLICT" | "REJECTED";

export interface ProductionDraft {
  idempotencyKey: string;
  createdAtDevice: string;
  productId: number;
  modelName: string;
  line: string;
  shift: string;
  sizeQuantities: Record<string, number>;
  totalPairs: number;
  status: DraftSyncStatus;
  retryCount: number;
  errorDetails?: string;
  dateAd?: string;
  dateBs?: string;
  notes?: string;
}

const DB_NAME = "livo_factory_offline_v1";
const DB_VERSION = 1;
const STORE_CATALOG = "catalog_cache";
const STORE_DRAFTS = "production_drafts";

let dbInstance: IDBDatabase | null = null;
const listeners = new Set<(stats: { pending: number; rejected: number; syncing: number }) => void>();

export function openOfflineDb(): Promise<IDBDatabase> {
  if (typeof window === "undefined" || !("indexedDB" in window)) {
    return Promise.reject(new Error("IndexedDB is not supported in this environment"));
  }

  if (dbInstance) {
    return Promise.resolve(dbInstance);
  }

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;

      if (!db.objectStoreNames.contains(STORE_CATALOG)) {
        db.createObjectStore(STORE_CATALOG, { keyPath: "skuId" });
      }

      if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
        const draftStore = db.createObjectStore(STORE_DRAFTS, { keyPath: "idempotencyKey" });
        draftStore.createIndex("status", "status", { unique: false });
        draftStore.createIndex("createdAtDevice", "createdAtDevice", { unique: false });
      }
    };

    request.onsuccess = () => {
      dbInstance = request.result;
      resolve(dbInstance);
    };

    request.onerror = () => {
      reject(request.error);
    };
  });
}

// ----------------- Drafts Storage API -----------------

export async function saveDraft(draft: ProductionDraft): Promise<void> {
  const db = await openOfflineDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DRAFTS, "readwrite");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.put(draft);
    req.onsuccess = () => {
      notifyListeners();
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

export async function getDraft(idempotencyKey: string): Promise<ProductionDraft | null> {
  const db = await openOfflineDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DRAFTS, "readonly");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.get(idempotencyKey);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

export async function getAllDrafts(): Promise<ProductionDraft[]> {
  const db = await openOfflineDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DRAFTS, "readonly");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

export async function getPendingDrafts(): Promise<ProductionDraft[]> {
  const all = await getAllDrafts();
  return all.filter((d) => d.status === "PENDING" || d.status === "SYNCING");
}

export async function updateDraftStatus(
  idempotencyKey: string,
  status: DraftSyncStatus,
  errorDetails?: string
): Promise<void> {
  const draft = await getDraft(idempotencyKey);
  if (!draft) return;

  draft.status = status;
  if (errorDetails !== undefined) {
    draft.errorDetails = errorDetails;
  }
  if (status === "SYNCING") {
    draft.retryCount = (draft.retryCount || 0) + 1;
  }

  await saveDraft(draft);
}

export async function deleteDraft(idempotencyKey: string): Promise<void> {
  const db = await openOfflineDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_DRAFTS, "readwrite");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.delete(idempotencyKey);
    req.onsuccess = () => {
      notifyListeners();
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

export async function getDraftCounts(): Promise<{ pending: number; rejected: number; syncing: number }> {
  try {
    const drafts = await getAllDrafts();
    return {
      pending: drafts.filter((d) => d.status === "PENDING").length,
      syncing: drafts.filter((d) => d.status === "SYNCING").length,
      rejected: drafts.filter((d) => d.status === "REJECTED" || d.status === "CONFLICT").length,
    };
  } catch {
    return { pending: 0, rejected: 0, syncing: 0 };
  }
}

export function subscribeDraftChanges(
  listener: (stats: { pending: number; rejected: number; syncing: number }) => void
): () => void {
  listeners.add(listener);
  getDraftCounts().then(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notifyListeners() {
  getDraftCounts().then((stats) => {
    listeners.forEach((l) => l(stats));
  });
}

// ----------------- Catalog Cache API -----------------

export async function cacheCatalogItems(items: CatalogItem[]): Promise<void> {
  const db = await openOfflineDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_CATALOG, "readwrite");
    const store = tx.objectStore(STORE_CATALOG);
    items.forEach((item) => store.put(item));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getCachedCatalog(): Promise<CatalogItem[]> {
  try {
    const db = await openOfflineDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_CATALOG, "readonly");
      const store = tx.objectStore(STORE_CATALOG);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

// ----------------- Reconnection Sync Drain Worker -----------------

export async function drainPendingProductionDrafts(
  onProgress?: (current: number, total: number) => void
): Promise<{ success: number; failed: number }> {
  const pending = await getPendingDrafts();
  if (pending.length === 0) return { success: 0, failed: 0 };

  let successCount = 0;
  let failedCount = 0;

  for (let i = 0; i < pending.length; i++) {
    const draft = pending[i];
    if (onProgress) onProgress(i + 1, pending.length);

    await updateDraftStatus(draft.idempotencyKey, "SYNCING");

    try {
      const payload = {
        idempotency_key: draft.idempotencyKey,
        created_at_device: draft.createdAtDevice,
        product_id: draft.productId,
        warehouse_id: 1,
        line: draft.line || "Line 1",
        shift: draft.shift || "Shift 1",
        worker_count: 1,
        date_ad: draft.dateAd || new Date().toISOString().split("T")[0],
        date_bs: draft.dateBs || "2083-06-09",
        size_quantities: draft.sizeQuantities,
        notes: draft.notes || `Offline sync batch (${draft.modelName})`
      };

      const res = await fetch("/api/v1/production/sync/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        await updateDraftStatus(draft.idempotencyKey, "ACCEPTED");
        // Optionally remove resolved drafts or keep for audit: remove after success
        await deleteDraft(draft.idempotencyKey);
        successCount++;
      } else {
        const errJson = await res.json().catch(() => ({}));
        const detail = errJson.detail || res.statusText || "Reconciliation failed";
        if (res.status === 422) {
          await updateDraftStatus(draft.idempotencyKey, "REJECTED", detail);
        } else if (res.status === 409) {
          await updateDraftStatus(draft.idempotencyKey, "CONFLICT", detail);
        } else {
          // Network error or server transient: reset to PENDING for retry
          await updateDraftStatus(draft.idempotencyKey, "PENDING", detail);
        }
        failedCount++;
      }
    } catch (err: any) {
      // Offline / network failure: restore to PENDING
      await updateDraftStatus(draft.idempotencyKey, "PENDING", err.message || "Network unreachable");
      failedCount++;
    }
  }

  notifyListeners();
  return { success: successCount, failed: failedCount };
}
