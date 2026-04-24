// frontend/composables/useFalconSummary.js
// Port of SummaryModule aggregation (PEGS/src/dashboard/app.js:734-1089).
// Produces top-per-clump and lead-per-chromosome signals for genes and
// variants. Preserves original quirk: strict-filter toggle does NOT affect
// this output (see spec §11).
import { useFalconFilters } from "~/composables/useFalconFilters";

export function useFalconSummary(store) {
  const { getNegP, normalizedClumpId } = useFalconFilters(store);

  function processDataset(name /* 'genes' | 'variants' */) {
    const isVariants = name === "variants";
    const data = store.datasets[name].data;
    const keyName = isVariants ? "VARIANT" : "GENE";
    const keyLead = isVariants ? "LEAD_SNP" : "NEAREST_TO_LEAD";

    const topPerClump = new Map();
    const leadsByChr = {};

    data.forEach((row, idx) => {
      const prob = parseFloat(row["PROBABILITY"]);
      const negP = getNegP(row, isVariants);
      if (isNaN(prob) || isNaN(negP)) return;

      const chr = row["CHR"] ? row["CHR"].toString().trim() : "";
      const clumpId = normalizedClumpId(row);
      const itemName = row[keyName] || row["RSID"] || row["SNP"] || "Unknown";
      const leadRaw = String(row[keyLead] || "").toLowerCase().trim();
      const isLead = leadRaw === "true" || leadRaw === "1" || leadRaw === "yes";

      const summary = {
        index: idx,
        name: itemName,
        chr,
        clumpId,
        prob,
        negP,
        isLead,
        start: parseFloat(row["START"]),
        end: parseFloat(row["END"]),
        raw: row,
        traits: null,
        isNovel: null,
        clinicalTrials: [],
      };

      if (clumpId !== "Unassigned (No Clump)") {
        if (!topPerClump.has(clumpId) || prob > topPerClump.get(clumpId).prob) {
          topPerClump.set(clumpId, summary);
        }
      }

      if (isLead && chr) {
        if (!leadsByChr[chr]) leadsByChr[chr] = [];
        leadsByChr[chr].push(summary);
      }
    });

    const top = Array.from(topPerClump.values()).sort((a, b) => b.prob - a.prob);
    const lead = [];
    Object.keys(leadsByChr).forEach((chr) => {
      leadsByChr[chr].sort((a, b) => b.prob - a.prob);
      lead.push(...leadsByChr[chr]);
    });

    return { top, lead };
  }

  function computeTopAndLeadSignals() {
    return {
      genes: store.datasets.genes.isLoaded
        ? processDataset("genes")
        : { top: [], lead: [] },
      variants: store.datasets.variants.isLoaded
        ? processDataset("variants")
        : { top: [], lead: [] },
    };
  }

  function attachClinicalTrials(rows) {
    if (!store.clinicalTrials.isLoaded) return;
    rows.forEach((row) => {
      const hits = store.clinicalTrials.byGene[row.name?.toUpperCase?.()] || [];
      row.clinicalTrials = hits;
    });
  }

  async function attachNoveltyFlags(rows, signal) {
    const { useGeneTraitFetcher } = await import("~/composables/useGeneTraitFetcher");
    const fetcher = useGeneTraitFetcher(store);
    const targets = rows.filter((r) => r.isNovel == null).map((r) => r.name);
    if (targets.length === 0) return;
    await fetcher.fetchTraits(targets, signal);
    rows.forEach((row) => {
      const key = row.name?.toUpperCase?.() || "";
      const traits = store.caches.traitLookup[key] || [];
      row.traits = traits;
      row.isNovel = traits.length === 0;
    });
  }

  return { computeTopAndLeadSignals, attachClinicalTrials, attachNoveltyFlags };
}
