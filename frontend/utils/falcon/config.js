// Port of PEGS/src/dashboard/app.js AppConfig.
// Tab ids map to route query param ?tab=<id>.
// `requires` is the dataset that must be loaded for the tab to enable
// (null = always enabled, e.g. TDP works on trait files alone).

export const FALCON_TABS = [
  { id: "summary", label: "Executive Summary", requires: "genes" },
  { id: "tdp", label: "FALCON Zoom", requires: null },
  { id: "genes", label: "Genes Plot", requires: "genes" },
  { id: "variants", label: "Variants Plot", requires: "variants" },
  { id: "table", label: "Data Table", requires: "genes" },
  { id: "log", label: "Execution Time", requires: "log" },
];

export const FALCON_ROWS_PER_PAGE = 15;

// Strict thresholds for "top per clump" calculation — independent from the
// user-controlled global filter (which lives in the store).
export const STRICT_TOP_MIN_PROB = 0.05;
export const STRICT_TOP_MIN_NEGP = 1;
