// frontend/composables/useFalconFileLoader.js
// Port of FileLoader.parseFile from PEGS/src/dashboard/app.js:231-251.
// Parses .wg.genes / .wg.variants as tab-delimited files via PapaParse.
import Papa from "papaparse";

function parseTsv(file) {
  // Read the whole file via `complete` rather than `chunk`. PapaParse 5.x's
  // chunked-streaming path for File inputs uses a hidden helper node that can
  // be torn down mid-parse and throw `DOMException: Node was not found`.
  // FALCON output files are MBs at most — streaming buys nothing here.
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      delimiter: "\t",
      complete: ({ data, meta }) =>
        resolve({ data, columns: meta.fields || [] }),
      error: (err) => reject(err),
    });
  });
}

export function useFalconFileLoader() {
  return {
    parseGenesFile: (file) => parseTsv(file),
    parseVariantsFile: (file) => parseTsv(file),
    // v2g (cS2G) files are tab-delimited with header `rsID\tGene\tValue`.
    parseV2gFile: (file) => parseTsv(file),
  };
}
