// frontend/composables/useClinicalTrials.js
import Papa from "papaparse";

export function useClinicalTrials(store) {
  function loadCsv(fileOrString) {
    return new Promise((resolve, reject) => {
      Papa.parse(fileOrString, {
        header: true,
        skipEmptyLines: true,
        // BULLETPROOFING: Strip invisible BOM characters and spaces from headers
        transformHeader: (header) => header.replace(/^\uFEFF/, '').trim(),
        complete: (results) => {
          try {

            const byGene = {};
            results.data.forEach((row) => {
              // Try exact match, but also fallbacks just in case
              const raw = row.Gene_Name || row.gene_name || row.target_symbol; 
              
              if (!raw) return; // Skips row if the column is entirely missing
              
              const key = raw.toUpperCase().trim();
              if (!byGene[key]) byGene[key] = [];
              
              byGene[key].push({
                drugId: row.Drug_ID || row.drug_id,
                indication: row.Indication_Name || row.indication_name,
                phase: row.Phase || row.phase,
              });
            });
            
            store.clinicalTrials.byGene = byGene;
            store.clinicalTrials.isLoaded = true;
            
            console.log(`[useClinicalTrials] Success! Loaded ${Object.keys(byGene).length} unique genes.`);
            resolve();
          } catch (err) {
            console.error("[useClinicalTrials] Processing error:", err);
            reject(err);
          }
        },
        error: (err) => {
          console.error("[useClinicalTrials] PapaParse error:", err);
          reject(err);
        },
      });
    });
  }

  return { loadCsv };
}