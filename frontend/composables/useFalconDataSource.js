// frontend/composables/useFalconDataSource.js
// Seam between "where data comes from" and the store.
// v1: loadFromLocalFiles (user's browser folder). v2: loadFromServer (stub).
import { useFalconFileLoader } from "~/composables/useFalconFileLoader";
import { useFalconLogParser }  from "~/composables/useFalconLogParser";

// Prefer the whole-genome combined file when present; otherwise fall back to
// every per-chromosome file of that kind. FALCON may emit either layout
// depending on how it was invoked (e.g. a single-chromosome run produces only
// `<trait>-chr22.22.genes`, never `.wg.genes`).
function pickKind(files, kind) {
  const wg = files.find((f) => f.name.endsWith(`.wg.${kind}`));
  if (wg) return [wg];
  return files.filter((f) => f.name.endsWith(`.${kind}`));
}

async function loadKind(files, parseOne) {
  if (files.length === 1) return parseOne(files[0]);
  const parts = await Promise.all(files.map(parseOne));
  const data = [];
  const cols = new Set();
  for (const p of parts) {
    if (p?.data) data.push(...p.data);
    if (p?.columns) for (const c of p.columns) cols.add(c);
  }
  return { data, columns: Array.from(cols) };
}

export function useFalconDataSource(store) {
  const { parseGenesFile, parseVariantsFile } = useFalconFileLoader();
  const { parseLog }                           = useFalconLogParser();

  async function loadFromLocalFiles(fileList) {
    const files = Array.from(fileList);
    if (files.length === 0) return;

    store.resetCaches();
    store.resetDatasets();

    store.rawFiles = files;
    store.folderName = files[0]?.webkitRelativePath?.split("/")[0] || "(unknown folder)";

    const geneFiles    = pickKind(files, "genes");
    const variantFiles = pickKind(files, "variants");
    const logFiles     = pickKind(files, "log");

    store.status = (geneFiles.length === 0 && variantFiles.length === 0)
      ? "Notice: No .genes or .variants files found in this folder."
      : "Loading datasets...";

    const jobs = [];

    if (geneFiles.length > 0) {
      jobs.push(
        loadKind(geneFiles, parseGenesFile)
          .then(({ data, columns }) => {
            store.datasets.genes.data = data;
            store.datasets.genes.columns = columns;
            store.datasets.genes.isLoaded = true;
          })
          .catch((err) => {
            console.error("genes parse error:", err);
            store.status = "Error parsing genes file(s)";
          }),
      );
    }
    if (variantFiles.length > 0) {
      jobs.push(
        loadKind(variantFiles, parseVariantsFile)
          .then(({ data, columns }) => {
            store.datasets.variants.data = data;
            store.datasets.variants.columns = columns;
            store.datasets.variants.isLoaded = true;
          })
          .catch((err) => {
            console.error("variants parse error:", err);
            store.status = "Error parsing variants file(s)";
          }),
      );
    }
    if (logFiles.length > 0) {
      jobs.push(
        parseLog(logFiles[0])
          .then((logData) => {
            store.datasets.log.data        = logData.data;
            store.datasets.log.preProcess  = logData.preProcess;
            store.datasets.log.chromosomes = logData.chromosomes;
            store.datasets.log.totalTime   = logData.totalTime;
            store.datasets.log.isLoaded    = true;
          })
          .catch((err) => console.error("log parse error:", err)),
      );
    }

    await Promise.all(jobs);
    if (!store.status.startsWith("Error")) store.status = "";
  }

  async function loadFromServer(/* datasetId */) {
    throw new Error("loadFromServer is not implemented in v1");
  }

  return { loadFromLocalFiles, loadFromServer };
}
