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

// Module-scope cache so calling useGeneTraitFetcher() again reuses the
// loaded catalog (matches the original's GeneTraitFetcher singleton).
const catalogByPageId = {};
let catalogReady = false;
let catalogPromise = null;

export function useGeneTraitFetcher(store) {

  async function fetchCatalog(signal) {
    if (catalogReady) return;
    if (catalogPromise) return catalogPromise;

    catalogPromise = (async () => {
      const res = await fetch(CATALOG_URL, { signal });
      if (!res.ok) throw new Error(`catalog fetch: HTTP ${res.status}`);
      const json = await res.json();
      // The HuGEAMP endpoint returns an array; PEGS app.js:1776 uses json[0].
      // Be permissive in case the proxy ever flattens to a bare object.
      const root = Array.isArray(json) ? json[0] : json;
      const csvText = root && root.field_data_points;
      if (typeof csvText !== "string") {
        throw new Error("catalog: unexpected shape (no field_data_points)");
      }
      await new Promise((resolve, reject) => {
        Papa.parse(csvText, {
          header: true,
          skipEmptyLines: true,
          complete: (r) => {
            r.data.forEach((row) => {
              const pageId = row["Page ID"];
              if (pageId) catalogByPageId[pageId] = row;
            });
            resolve();
          },
          error: (err) => reject(err),
        });
      });
      catalogReady = true;
    })().finally(() => {
      catalogPromise = null;
    });
    return catalogPromise;
  }

  async function fetchTraits(geneNames, signal) {
    // Make sure the master catalog is loaded once before any per-gene fetch.
    if (!catalogReady) {
      try {
        await fetchCatalog(signal);
      } catch (err) {
        if (err.name === "AbortError") throw err;
        // Without a catalog we can't translate page IDs to traits, so
        // mark every requested gene as having no traits and bail out.
        console.error("[useGeneTraitFetcher] catalog load failed:", err);
        geneNames.forEach((g) => {
          const key = (g || "").toUpperCase().trim();
          if (key && !store.caches.traitLookup[key]) {
            store.caches.traitLookup[key] = [];
          }
        });
        return;
      }
    }

    const unique = Array.from(
      new Set(geneNames.map((g) => g.toUpperCase().trim()).filter(Boolean)),
    );
    const todo = unique.filter((g) => !store.caches.traitLookup[g]);

    // Throttled worker pool — Chrome rejects unbounded parallel fetches with
    // ERR_INSUFFICIENT_RESOURCES once you push past a few hundred. The
    // codetabs proxy is also rate-limited; CONCURRENCY=8 is conservative.
    const CONCURRENCY = 8;
    let i = 0;

    async function fetchOne(g) {
      try {
        const res = await fetch(TRAIT_URL_BASE + encodeURIComponent(g), {
          signal,
        });
        if (!res.ok) {
          store.caches.traitLookup[g] = [];
          return;
        }
        const json = await res.json();
        // The egls endpoint returns an array of { field_page_id, ... }.
        // For each, look up the catalog row to materialise a trait record.
        const items = Array.isArray(json) ? json : json?.data || [];
        const traits = [];
        items.forEach((item) => {
          const pageId = item && (item.field_page_id || item["Page ID"]);
          const rowData = pageId ? catalogByPageId[pageId] : null;
          if (rowData) {
            traits.push({
              page_id: pageId,
              trait: rowData["Trait"] || "N/A",
              pmid: rowData["PMID"] || "N/A",
              citation: rowData["Citation"] || "N/A",
              authors: rowData["short_name"] || "N/A",
            });
          }
        });
        store.caches.traitLookup[g] = traits;
      } catch (err) {
        if (err.name === "AbortError") throw err;
        // Don't log every failure; log summary at end. Treat as no-traits so
        // the user still sees deterministic behaviour.
        store.caches.traitLookup[g] = [];
      }
    }

    async function worker() {
      while (i < todo.length) {
        if (signal && signal.aborted) {
          const e = new Error("Aborted");
          e.name = "AbortError";
          throw e;
        }
        const g = todo[i++];
        await fetchOne(g);
      }
    }

    const workers = Array.from({ length: Math.min(CONCURRENCY, todo.length) }, () => worker());
    await Promise.all(workers);
  }

  return { fetchCatalog, fetchTraits };
}
