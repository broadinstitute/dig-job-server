import {
  getLdDotColor,
  normalizePlotMargin,
  VKS_LD_DOT_COLORS,
  VKS_LD_REFERENCE_COLOR,
} from "./plotShared.js";
import { computeRegionPlotWidth } from "./genesTrackRender.js";

// Legend for the LD colour scale, mirroring the KP sifter: descending r2, then
// "No data". getLdDotColor bins by Math.floor(r2 * 5), so index 5 is reached
// only by exactly r2 === 1 — slicing it off would drop that band from the key.
export const LD_NO_DATA_COLOR = "#00000030";

export const LD_LEGEND_ENTRIES = [
  { color: VKS_LD_DOT_COLORS[5], label: "r² = 1" },
  { color: VKS_LD_DOT_COLORS[4], label: "1 > r² ≥ 0.8" },
  { color: VKS_LD_DOT_COLORS[3], label: "0.8 > r² ≥ 0.6" },
  { color: VKS_LD_DOT_COLORS[2], label: "0.6 > r² ≥ 0.4" },
  { color: VKS_LD_DOT_COLORS[1], label: "0.4 > r² ≥ 0.2" },
  { color: VKS_LD_DOT_COLORS[0], label: "0.2 > r² > 0" },
  { color: LD_NO_DATA_COLOR, label: "No data" },
];

export const LD_REFERENCE_COLOR = VKS_LD_REFERENCE_COLOR;

// Rows -> canvas points. Kept separate from the component so plot geometry is
// unit-testable without mounting anything.
export function buildPlotPoints(rows, visibleRegion, { width, height, margin } = {}) {
  const m = normalizePlotMargin(margin);
  // Share the genes track's x-scale (canvasWidth - margin.left * 2, asymmetric
  // by upstream design) so the two stacked canvases agree on where a given
  // position lands horizontally.
  const plotWidth = computeRegionPlotWidth(width, m);
  const plotHeight = height - m.top - m.bottom;
  const span = visibleRegion.end - visibleRegion.start || 1;

  const usable = (rows || []).filter(
    (r) =>
      Number(r?.pValue) > 0 &&
      r.position >= visibleRegion.start &&
      r.position <= visibleRegion.end,
  );
  if (!usable.length) return [];

  const yValues = usable.map((r) => -Math.log10(Number(r.pValue)));
  const yMax = Math.max(...yValues, 1);

  return usable.map((row, i) => ({
    x: m.left + ((row.position - visibleRegion.start) / span) * plotWidth,
    y: m.top + (plotHeight - (yValues[i] / yMax) * plotHeight),
    // LD enrichment writes `LDS` (see enrichAssociationRowsWithLdScoresForRef).
    color: getLdDotColor(row.LDS ?? null),
    row,
  }));
}
