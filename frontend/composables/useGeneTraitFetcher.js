// frontend/composables/useGeneTraitFetcher.js
// Port of GeneTraitFetcher (PEGS/src/dashboard/app.js:1759-1839) with cancellation.
// v1: preserves original's client-side codetabs proxy (spec §9 decision 8).
// v2 candidate: migrate behind a Python backend endpoint.
import Papa from "papaparse";

const CATALOG_URL =
  "https://api.codetabs.com/v1/proxy?quest=" +
  encodeURIComponent("https://hugeampkpncms.org/rest/data?pageid=Gene_page_PEGLs_475");

const TRAIT_URL_BASE =
  "https://api.codetabs.com/v1/proxy?quest=" +
  encodeURIComponent("https://hugeampkpncms.org/rest/egls?gene=");

export function useGeneTraitFetcher(store) {
  async function fetchCatalog(signal) {
    const res = await fetch(CATALOG_URL, { signal });
    if (!res.ok) throw new Error(`catalog fetch: HTTP ${res.status}`);
    const json = await res.json();
    const csvText = json.field_data_points;
    if (typeof csvText !== "string") throw new Error("catalog: unexpected shape");
    return new Promise((resolve, reject) => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        complete: (r) => {
          r.data.forEach((row) => {
            const g = (row.Gene || "").toUpperCase().trim();
            if (!g) return;
            if (!store.caches.traitLookup[g]) store.caches.traitLookup[g] = [];
            store.caches.traitLookup[g].push(row);
          });
          resolve();
        },
        error: (err) => reject(err),
      });
    });
  }

  async function fetchTraits(geneNames, signal) {
    const unique = Array.from(
      new Set(geneNames.map((g) => g.toUpperCase().trim()).filter(Boolean)),
    );
    const todo = unique.filter((g) => !store.caches.traitLookup[g]);
    await Promise.all(
      todo.map(async (g) => {
        try {
          const res = await fetch(TRAIT_URL_BASE + encodeURIComponent(g), { signal });
          if (!res.ok) {
            store.caches.traitLookup[g] = [];
            return;
          }
          const json = await res.json();
          store.caches.traitLookup[g] = Array.isArray(json) ? json : json?.data || [];
        } catch (err) {
          if (err.name === "AbortError") throw err;
          store.caches.traitLookup[g] = [];
        }
      }),
    );
  }

  return { fetchCatalog, fetchTraits };
}
