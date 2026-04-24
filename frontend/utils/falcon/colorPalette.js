// Port of PEGS/src/dashboard/app.js ColorManager. Color-for-clump assignment
// is pure here — the caller passes in the Map (owned by FalconStore.caches.clumpColor)
// so dataset reloads reset cleanly via store.resetCaches().

export const FALCON_PALETTE = [
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
  "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
  "#c49c94", "#f7b6d2", "#c7c7c7", "#dbdb8d", "#9edae5",
];

export const UNASSIGNED_CLUMP_COLOR = "#d1d5db";
export const UNASSIGNED_CLUMP_ID = "Unassigned (No Clump)";

/**
 * Look up (and assign if missing) a color for a clump.
 * @param {Map<string, string>} clumpColorMap  store.caches.clumpColor
 * @param {string} clumpId
 * @returns {string} hex color
 */
export function getColorForClump(clumpColorMap, clumpId) {
  if (clumpId === UNASSIGNED_CLUMP_ID) return UNASSIGNED_CLUMP_COLOR;
  if (!clumpColorMap.has(clumpId)) {
    const idx = clumpColorMap.size % FALCON_PALETTE.length;
    clumpColorMap.set(clumpId, FALCON_PALETTE[idx]);
  }
  return clumpColorMap.get(clumpId);
}
