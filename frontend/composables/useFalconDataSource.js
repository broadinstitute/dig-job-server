// frontend/composables/useFalconDataSource.js
// Seam between "where data comes from" and the store.
// v1: loadFromLocalFiles (user's browser folder). v2: loadFromServer (stub).
import { useFalconFileLoader } from "~/composables/useFalconFileLoader";
import { useFalconLogParser }  from "~/composables/useFalconLogParser";

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

    const geneFile    = files.find((f) => f.name.endsWith(".wg.genes"));
    const variantFile = files.find((f) => f.name.endsWith(".wg.variants"));
    const logFile     = files.find((f) => f.name.endsWith(".wg.log"));

    store.status = (!geneFile && !variantFile)
      ? "Notice: Missing standard .wg files. FALCON Zoom will still work if trait files exist."
      : "Loading datasets...";

    const jobs = [];

    if (geneFile) {
      jobs.push(
        parseGenesFile(geneFile)
          .then(({ data, columns }) => {
            store.datasets.genes.data = data;
            store.datasets.genes.columns = columns;
            store.datasets.genes.isLoaded = true;
          })
          .catch((err) => {
            console.error("genes parse error:", err);
            store.status = "Error parsing .wg.genes";
          }),
      );
    }
    if (variantFile) {
      jobs.push(
        parseVariantsFile(variantFile)
          .then(({ data, columns }) => {
            store.datasets.variants.data = data;
            store.datasets.variants.columns = columns;
            store.datasets.variants.isLoaded = true;
          })
          .catch((err) => {
            console.error("variants parse error:", err);
            store.status = "Error parsing .wg.variants";
          }),
      );
    }
    if (logFile) {
      jobs.push(
        parseLog(logFile)
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
