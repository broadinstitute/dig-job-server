// Tiny IndexedDB wrapper backed by the native API. Each "store" is keyed by
// a string and stores any structured-cloneable JS value. We use this for
// caching parsed FALCON tables keyed by `${dataset}::${filename}::${etag}`,
// so opening a dataset whose ETags haven't changed is a free hit.
//
// Why hand-rolled instead of idb-keyval: zero new deps, ~30 lines, and we
// only need the most basic operations.

const DB_NAME = "gwas-ce";
const DB_VERSION = 1;
const STORE = "falcon-cache";

let _dbPromise = null;

function openDb() {
  if (_dbPromise) return _dbPromise;
  _dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB not available"));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return _dbPromise;
}

async function tx(mode, fn) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode);
    const store = t.objectStore(STORE);
    const result = fn(store);
    t.oncomplete = () => resolve(result);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

export function useIndexedDBCache() {
  async function get(key) {
    let value;
    await tx("readonly", (store) => {
      const r = store.get(key);
      r.onsuccess = () => { value = r.result; };
    });
    return value;
  }

  async function set(key, value) {
    await tx("readwrite", (store) => store.put(value, key));
  }

  async function del(key) {
    await tx("readwrite", (store) => store.delete(key));
  }

  /** Delete every key starting with `prefix`. Used to evict old ETag
   * entries for a (dataset, filename) pair when its ETag changes. */
  async function deletePrefix(prefix) {
    await tx("readwrite", (store) => {
      const req = store.openCursor();
      req.onsuccess = () => {
        const cursor = req.result;
        if (!cursor) return;
        if (typeof cursor.key === "string" && cursor.key.startsWith(prefix)) {
          cursor.delete();
        }
        cursor.continue();
      };
    });
  }

  return { get, set, del, deletePrefix };
}
