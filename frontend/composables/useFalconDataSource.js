// frontend/composables/useFalconDataSource.js
// Seam between "where data comes from" and the store. Reads FALCON outputs
// from S3 via /api/falcon/<dataset>/result-urls and caches parsed results
// in IndexedDB keyed by (dataset, filename, etag).
//
// File selection prefers the whole-genome aggregate (`.wg.<kind>`) when
// present; otherwise falls back to every per-chromosome file of that kind.
// FALCON may emit either layout depending on how it was invoked (e.g. a
// single-chromosome run produces only `<trait>-chr22.22.genes`).
import { useFalconFileLoader } from "~/composables/useFalconFileLoader";
import { useFalconLogParser }  from "~/composables/useFalconLogParser";

export function useFalconDataSource(store) {
  const { parseGenesFile, parseVariantsFile, parseV2gFile } = useFalconFileLoader();
  const { parseLog }                           = useFalconLogParser();

  // Fetch the result-url listing for a dataset and return cache-first helpers
  // for picking + loading file kinds. Shared by the eager load and the lazy
  // v2g load. Each file is keyed in IndexedDB by (dataset, filename, etag);
  // ETag is stable per S3 object version so a hit means the cached parsed
  // arrays are still good.
  async function makeLoader(dataset) {
    const { useUserStore } = await import("~/stores/UserStore");
    const { useIndexedDBCache } = await import("~/composables/useIndexedDBCache");
    const userStore = useUserStore();
    const cache = useIndexedDBCache();

    const urls = await userStore.getFalconResultUrls(dataset);
    const filesMap = urls.files || {};

    // Prefer `.wg.<kind>` if present; fall back to all per-chr `.<kind>` files.
    function pickNames(kind) {
      const wg = Object.keys(filesMap).find((n) => n.endsWith(`.wg.${kind}`));
      if (wg) return [wg];
      return Object.keys(filesMap).filter((n) => n.endsWith(`.${kind}`));
    }

    // Per-file helper: try the cache first; on miss fetch + parse + cache.
    async function loadFile(name, parseFn) {
      const info = filesMap[name];
      const key = `${dataset}::${name}::${info.etag}`;
      let parsed;
      try {
        parsed = await cache.get(key);
      } catch (e) {
        console.warn("IndexedDB get failed; falling through to network", e);
      }
      if (parsed !== undefined) return parsed;

      const resp = await fetch(info.url);
      if (!resp.ok) throw new Error(`fetch ${name}: ${resp.status}`);
      const blob = await resp.blob();
      const file = new File([blob], name);
      parsed = await parseFn(file);

      // Drop older ETag entries for this (dataset, name) so the cache
      // doesn't grow without bound when results are re-uploaded.
      try {
        await cache.deletePrefix(`${dataset}::${name}::`);
        await cache.set(key, parsed);
      } catch (e) {
        console.warn("IndexedDB write failed (continuing without cache)", e);
      }
      return parsed;
    }

    // Load every file of one kind, concatenating per-chr results.
    async function loadKind(names, parseFn) {
      if (names.length === 0) return null;
      if (names.length === 1) return loadFile(names[0], parseFn);
      const parts = await Promise.all(names.map((n) => loadFile(n, parseFn)));
      const data = [];
      const cols = new Set();
      for (const p of parts) {
        if (p?.data) data.push(...p.data);
        if (p?.columns) for (const c of p.columns) cols.add(c);
      }
      return { data, columns: Array.from(cols) };
    }

    return { filesMap, pickNames, loadFile, loadKind };
  }

  async function loadFromServer(dataset) {
    store.resetCaches();
    store.resetDatasets();
    store.folderName = dataset;
    store.status = "Loading FALCON results...";

    let loader;
    try {
      loader = await makeLoader(dataset);
    } catch (err) {
      console.error("getFalconResultUrls failed:", err);
      store.status = "Error: could not list FALCON results";
      return;
    }

    const genesNames = loader.pickNames("genes");
    const variantsNames = loader.pickNames("variants");
    const logNames = loader.pickNames("log");

    if (genesNames.length === 0 && variantsNames.length === 0 && logNames.length === 0) {
      store.status = "No FALCON outputs found for this dataset";
      return;
    }

    const jobs = [];

    if (genesNames.length > 0) {
      jobs.push(
        loader.loadKind(genesNames, parseGenesFile)
          .then((res) => {
            if (!res) return;
            store.datasets.genes.data = res.data;
            store.datasets.genes.columns = res.columns;
            store.datasets.genes.isLoaded = true;
          })
          .catch((err) => {
            console.error("genes load error:", err);
            store.status = "Error loading genes file(s)";
          }),
      );
    }
    if (variantsNames.length > 0) {
      jobs.push(
        loader.loadKind(variantsNames, parseVariantsFile)
          .then((res) => {
            if (!res) return;
            store.datasets.variants.data = res.data;
            store.datasets.variants.columns = res.columns;
            store.datasets.variants.isLoaded = true;
          })
          .catch((err) => {
            console.error("variants load error:", err);
            store.status = "Error loading variants file(s)";
          }),
      );
    }
    if (logNames.length > 0) {
      jobs.push(
        loader.loadFile(logNames[0], parseLog)
          .then((res) => {
            if (!res) return;
            store.datasets.log.data = res.data;
            store.datasets.log.preProcess = res.preProcess;
            store.datasets.log.chromosomes = res.chromosomes;
            store.datasets.log.totalTime = res.totalTime;
            store.datasets.log.isLoaded = true;
          })
          .catch((err) => console.error("log load error:", err)),
      );
    }
    // v2g is intentionally NOT loaded here — it's large (~100k rows) and only
    // the TDP zoom needs it. It's fetched lazily on first Run Analysis via
    // loadV2g() below.

    await Promise.all(jobs);
    if (!store.status.startsWith("Error")) store.status = "";
  }

  // Lazy v2g (cS2G variant→gene evidence): fetched on demand the first time
  // the zoom runs. Idempotent — marks isLoaded even when the dataset has no
  // v2g, so we don't re-list the bucket on every Run Analysis.
  async function loadV2g(dataset) {
    if (store.datasets.v2g.isLoaded || !dataset) return;

    let loader;
    try {
      loader = await makeLoader(dataset);
    } catch (err) {
      console.error("v2g load error (listing):", err);
      return;
    }

    // v2g is emitted per-chromosome only (no `.wg.v2g` aggregate) and is
    // optional — some datasets predate it.
    const v2gNames = loader.pickNames("v2g");
    if (v2gNames.length === 0) {
      store.datasets.v2g.isLoaded = true;
      return;
    }
    try {
      const res = await loader.loadKind(v2gNames, parseV2gFile);
      if (res) {
        store.datasets.v2g.data = res.data;
        store.datasets.v2g.columns = res.columns;
      }
      store.datasets.v2g.isLoaded = true;
    } catch (err) {
      console.error("v2g load error:", err);
    }
  }

  return { loadFromServer, loadV2g };
}
