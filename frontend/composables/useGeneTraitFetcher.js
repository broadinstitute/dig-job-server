// frontend/composables/useGeneTraitFetcher.js
// Loads a pre-built EGL index from /data/falcon-egl-index.json (built by
// scripts/build_falcon_egl_index.py) and serves per-gene trait lookups from
// an in-memory hashmap. No external API calls; no per-gene network traffic.

const INDEX_URL = "/data/falcon-egl-index.json";

let indexData = null;
let indexPromise = null;

async function loadIndex(signal) {
  if (indexData) return indexData;
  if (indexPromise) return indexPromise;

  indexPromise = (async () => {
    const res = await fetch(INDEX_URL, { signal });
    if (!res.ok) throw new Error(`egl index: HTTP ${res.status}`);
    indexData = await res.json();
    return indexData;
  })().finally(() => {
    indexPromise = null;
  });
  return indexPromise;
}

export function useGeneTraitFetcher(store) {
  async function fetchCatalog(signal) {
    await loadIndex(signal);
  }

  async function fetchTraits(geneNames, signal, options = {}) {
    const { onProgress } = options;

    let data;
    try {
      data = await loadIndex(signal);
    } catch (err) {
      if (err.name === "AbortError") throw err;
      console.error("[useGeneTraitFetcher] index load failed:", err);
      geneNames.forEach((g) => {
        const key = (g || "").toUpperCase().trim();
        if (key && !store.caches.traitLookup[key]) {
          store.caches.traitLookup[key] = [];
        }
      });
      return;
    }

    const unique = Array.from(
      new Set(geneNames.map((g) => g.toUpperCase().trim()).filter(Boolean)),
    );

    onProgress?.({ processed: 0, total: unique.length, currentGene: null });

    unique.forEach((g, i) => {
      if (signal?.aborted) {
        const e = new Error("Aborted");
        e.name = "AbortError";
        throw e;
      }
      if (store.caches.traitLookup[g] === undefined) {
        store.caches.traitLookup[g] = data.index[g] || [];
      }
      onProgress?.({ processed: i + 1, total: unique.length, currentGene: g });
    });
  }

  return { fetchCatalog, fetchTraits };
}
