// frontend/composables/useFalconSummary.js
// Port of SummaryModule aggregation (PEGS/src/dashboard/app.js:734-1089).
// Produces top-per-clump and lead-per-chromosome signals for genes and
// variants. Preserves original quirk: strict-filter toggle does NOT affect
// this output (see spec §11).
import { useFalconFilters } from "~/composables/useFalconFilters";
import { getColorForClump } from "~/utils/falcon/colorPalette";

const ROLE_TOP = "🏆 Top";
const ROLE_LEAD = "⭐ Lead";
const ROLE_BOTH = "🏆 Top & ⭐ Lead";

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
    if (!store.clinicalTrials.isLoaded) {
      console.warn("[attachClinicalTrials] Aborted: Store says clinical trials are not loaded.");
      return;
    }

    const availableKeys = Object.keys(store.clinicalTrials.byGene);

    rows.forEach((row) => {
      const lookupKey = row.name?.toUpperCase?.().trim() || "";
      
      const hits = store.clinicalTrials.byGene[lookupKey] || [];

      row.clinicalTrials = hits;
      row.hasClinicalTrials = hits.length > 0;
    });
  }

  // NEW ASYNC FETCHER: Downloads CSV over the network and reuses your parsing logic
  async function fetchAndAttachTrials(signal) {
    // 1. Fetch the file
    const response = await fetch('/data/clinical_trials.csv', { signal });
    if (!response.ok) {
        throw new Error('Failed to fetch clinical trials CSV from server.');
    }
    
    // 2. Extract the raw text directly
    const rawText = await response.text();

    // 3. Import the parser
    const { useClinicalTrials } = await import("~/composables/useClinicalTrials");
    const { loadCsv } = useClinicalTrials(store);
    
    // 4. Pass the raw string to PapaParse (it supports strings perfectly!)
    await loadCsv(rawText);
  }

  async function attachNoveltyFlags(rows, signal, onProgress) {
    const { useGeneTraitFetcher } = await import("~/composables/useGeneTraitFetcher");
    const fetcher = useGeneTraitFetcher(store);
    const targets = rows.filter((r) => r.isNovel == null).map((r) => r.name);
    if (targets.length === 0) return;
    await fetcher.fetchTraits(targets, signal, { onProgress });
    rows.forEach((row) => {
      const key = row.name?.toUpperCase?.() || "";
      const traits = store.caches.traitLookup[key] || [];
      row.traits = traits;
      row.isNovel = traits.length === 0;
    });
  }

  function computeSummaryRowsForPlots(name /* 'genes' | 'variants' */) {
    const dataset = store.datasets[name];
    if (!dataset || !dataset.isLoaded) {
      return { results: [], stats: { topOnly: 0, leadOnly: 0, both: 0 } };
    }

    const data = dataset.data;
    const isVariants = name === "variants";
    const keyName = isVariants ? "VARIANT" : "GENE";
    const keyLead = isVariants ? "LEAD_SNP" : "NEAREST_TO_LEAD";
    const keyNegP = isVariants ? "P_VALUE" : "NEG_LOG_P";

    // Pass 1: STRICT top-per-clump (prob >= 0.05 AND negP >= 1).
    const topPerClump = new Map();
    data.forEach((row, idx) => {
      const prob = parseFloat(row["PROBABILITY"]);
      const negP = getNegP(row, isVariants);
      if (isNaN(prob) || prob < 0.05) return;
      if (isNaN(negP) || negP < 1) return;
      const clumpId = row["CLUMP"] ? row["CLUMP"].toString().trim() : "Unassigned";
      if (!topPerClump.has(clumpId) || prob > topPerClump.get(clumpId).prob) {
        topPerClump.set(clumpId, { index: idx, prob });
      }
    });

    // Pass 2: emit flat rows under the user's global filter.
    const results = [];
    const stats = { topOnly: 0, leadOnly: 0, both: 0 };

    data.forEach((row, idx) => {
      const prob = parseFloat(row["PROBABILITY"]);
      const negP = getNegP(row, isVariants);
      if (store.globalFilter.active) {
        if (isNaN(prob) || prob < store.globalFilter.minProb) return;
        if (isNaN(negP) || negP < store.globalFilter.minNegP) return;
      }

      const clumpId = row["CLUMP"] ? row["CLUMP"].toString().trim() : "Unassigned";
      const isTop = topPerClump.get(clumpId)?.index === idx;
      const leadRaw = String(row[keyLead] || "").toLowerCase().trim();
      const isLead = leadRaw === "true" || leadRaw === "1" || leadRaw === "yes";
      if (!isTop && !isLead) return;

      let role;
      if (isTop && isLead) {
        role = ROLE_BOTH;
        stats.both++;
      } else if (isTop) {
        role = ROLE_TOP;
        stats.topOnly++;
      } else {
        role = ROLE_LEAD;
        stats.leadOnly++;
      }

      const rawSig = parseFloat(row[keyNegP]);
      const formattedSig = isVariants
        ? rawSig === 0
          ? "0.0"
          : isNaN(rawSig)
            ? ""
            : rawSig.toExponential(2)
        : isNaN(rawSig)
          ? ""
          : rawSig.toFixed(2);

      const itemName = row[keyName] || row["RSID"] || row["SNP"] || "Unknown";
      const trials = !isVariants && store.clinicalTrials.isLoaded
        ? store.clinicalTrials.byGene[itemName?.toUpperCase?.()] || []
        : [];
      const cachedTraits = store.caches.traitLookup[itemName?.toUpperCase?.()];

      results.push({
        clump: clumpId,
        color: getColorForClump(store.caches.clumpColor, clumpId),
        name: itemName,
        prob: prob.toFixed(4),
        rawProb: prob,
        rawSig,
        significance: formattedSig,
        role,
        hasClinicalTrials: trials.length > 0,
        clinicalTrials: trials,
        isNovel: cachedTraits ? cachedTraits.length === 0 : null,
        traits: cachedTraits || null,
      });
    });

    return { results, stats };
  }

  function computeOverlapStats(name) {
    return computeSummaryRowsForPlots(name).stats;
  }

  function computeDistances() {
    const distances = [];
    const leadDistances = [];
    if (!store.datasets.genes.isLoaded || !store.datasets.variants.isLoaded) {
      return { distances, leadDistances };
    }

    const rawGenes = store.datasets.genes.data;
    const rawVariants = store.datasets.variants.data;

    const leadGenes = new Set();
    rawGenes.forEach((row) => {
      const leadVal = String(row["NEAREST_TO_LEAD"] || "").toLowerCase().trim();
      if (leadVal === "true" || leadVal === "1" || leadVal === "yes") {
        const gName = row["GENE"] || row["ID"];
        if (gName) leadGenes.add(gName);
      }
    });

    const leadsByChr = {};

    rawVariants.forEach((row) => {
      const leadRaw = String(row["LEAD_SNP"] || "").toLowerCase().trim();
      const isLead = leadRaw === "true" || leadRaw === "1" || leadRaw === "yes";
      if (!isLead) return;

      const nearestGene = row["NEAREST_GENE"];
      if (nearestGene && leadGenes.has(nearestGene)) {
        const distStr = row["NEAREST_DISTANCE"];
        if (distStr !== undefined && distStr !== "") {
          const dist = parseFloat(distStr);
          if (!isNaN(dist)) {
            distances.push({
              dist: Math.abs(dist),
              gene: nearestGene,
              variant: row["VARIANT"] || row["RSID"] || row["SNP"] || "Unknown",
            });
          }
        }
      }

      const chr = row["CHR"] != null ? String(row["CHR"]).trim() : "";
      const posStr = row["POS"];
      if (chr && posStr !== undefined && posStr !== "") {
        const pos = parseInt(posStr, 10);
        if (!isNaN(pos)) {
          if (!leadsByChr[chr]) leadsByChr[chr] = [];
          leadsByChr[chr].push({
            pos,
            variant: row["VARIANT"] || row["RSID"] || row["SNP"] || "Unknown",
          });
        }
      }
    });

    Object.keys(leadsByChr).forEach((chr) => {
      const leads = leadsByChr[chr].sort((a, b) => a.pos - b.pos);
      for (let i = 1; i < leads.length; i++) {
        const dist = leads[i].pos - leads[i - 1].pos;
        leadDistances.push({
          dist,
          chr,
          v1: leads[i - 1].variant,
          v2: leads[i].variant,
        });
      }
    });

    return { distances, leadDistances };
  }

  return {
    computeTopAndLeadSignals,
    attachClinicalTrials,
    fetchAndAttachTrials,
    attachNoveltyFlags,
    computeSummaryRowsForPlots,
    computeOverlapStats,
    computeDistances,
  };
}