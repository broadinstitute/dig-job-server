// frontend/composables/useClinicalTrials.js
// Port of ClinicalTrialsManager (PEGS/src/dashboard/app.js:1696-1754).
// CSV columns expected: Gene_Name, Drug_ID, Indication_Name, Phase.
import Papa from "papaparse";

export function useClinicalTrials(store) {
  function loadCsv(file) {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          try {
            const byGene = {};
            results.data.forEach((row) => {
              const raw = row.Gene_Name;
              if (!raw) return;
              const key = raw.toUpperCase().trim();
              if (!byGene[key]) byGene[key] = [];
              byGene[key].push({
                drugId: row.Drug_ID,
                indication: row.Indication_Name,
                phase: row.Phase,
              });
            });
            store.clinicalTrials.byGene = byGene;
            store.clinicalTrials.isLoaded = true;
            resolve();
          } catch (err) {
            reject(err);
          }
        },
        error: (err) => reject(err),
      });
    });
  }

  return { loadCsv };
}
