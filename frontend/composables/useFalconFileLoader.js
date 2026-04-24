// frontend/composables/useFalconFileLoader.js
// Port of FileLoader.parseFile from PEGS/src/dashboard/app.js:231-251.
// Parses .wg.genes / .wg.variants as tab-delimited files via PapaParse.
import Papa from "papaparse";

function parseTsv(file) {
  return new Promise((resolve, reject) => {
    const rows = [];
    let columns = [];
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      delimiter: "\t",
      chunk: (results) => {
        rows.push(...results.data);
        if (columns.length === 0 && results.meta.fields) {
          columns = results.meta.fields;
        }
      },
      complete: () => resolve({ data: rows, columns }),
      error: (err) => reject(err),
    });
  });
}

export function useFalconFileLoader() {
  return {
    parseGenesFile: (file) => parseTsv(file),
    parseVariantsFile: (file) => parseTsv(file),
  };
}
