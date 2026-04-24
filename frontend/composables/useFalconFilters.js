// frontend/composables/useFalconFilters.js
// Port of the per-row filter logic from PlotModule.renderScatterPlot
// (PEGS/src/dashboard/app.js:558-619).

const UNASSIGNED = "Unassigned (No Clump)";

function getNegP(row, isVariants) {
  if (!isVariants) return parseFloat(row["NEG_LOG_P"]);
  let p = parseFloat(row["P_VALUE"]);
  if (isNaN(p)) return NaN;
  if (p === 0) p = Number.MIN_VALUE;
  return -Math.log10(p);
}

function normalizedClumpId(row) {
  const raw = row["CLUMP"] ? row["CLUMP"].toString().trim() : "";
  return raw === "" ? UNASSIGNED : raw;
}

function passesGlobalFilter(row, isVariants, globalFilter) {
  if (!globalFilter.active) return true;
  const prob = parseFloat(row["PROBABILITY"]);
  const negP = getNegP(row, isVariants);
  if (isNaN(prob) || prob < globalFilter.minProb) return false;
  if (isNaN(negP) || negP < globalFilter.minNegP) return false;
  return true;
}

function passesRegionFilter(row, regionFilter /* { chr, minStart, maxEnd } */) {
  if (!regionFilter || regionFilter.chr === "All" || regionFilter.chr == null) return true;
  const rowChr = row["CHR"] ? row["CHR"].toString().trim() : "";
  if (rowChr !== regionFilter.chr) return false;
  const rowStart = parseFloat(row["START"]);
  const rowEnd = parseFloat(row["END"]);
  if (regionFilter.maxEnd != null && !isNaN(rowStart) && rowStart > regionFilter.maxEnd) return false;
  if (regionFilter.minStart != null && !isNaN(rowEnd) && rowEnd < regionFilter.minStart) return false;
  return true;
}

export function useFalconFilters(store) {
  function filterDataset(name /* 'genes' | 'variants' */) {
    const rows = store.datasets[name].data;
    const isVariants = name === "variants";
    const region = name === "genes" ? store.plotFilters.genes : null;
    return rows.filter(
      (r) =>
        passesGlobalFilter(r, isVariants, store.globalFilter) &&
        passesRegionFilter(r, region),
    );
  }

  return { filterDataset, getNegP, normalizedClumpId };
}
