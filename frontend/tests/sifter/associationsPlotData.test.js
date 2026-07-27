import { describe, it, expect } from "vitest";
import {
  buildPlotPoints,
  LD_LEGEND_ENTRIES,
} from "../../utils/sifter/associationsPlotData.js";
import { VKS_LD_DOT_COLORS, getLdDotColor } from "../../utils/sifter/plotShared.js";
import { computeRegionPlotWidth } from "../../utils/sifter/genesTrackRender.js";

const REGION = { chr: "10", start: 0, end: 1000 };
const LAYOUT = { width: 1000, height: 120, margin: { top: 10, right: 10, bottom: 20, left: 40 } };

describe("LD_LEGEND_ENTRIES", () => {
  it("covers every colour bin getLdDotColor can return, in descending r2 order", () => {
    // One entry per bin (6) plus "No data".
    expect(LD_LEGEND_ENTRIES).toHaveLength(VKS_LD_DOT_COLORS.length + 1);
    // The r2 === 1 band must be present — it is the top bin and easy to slice off.
    expect(LD_LEGEND_ENTRIES[0].color).toBe(getLdDotColor(1));
    expect(LD_LEGEND_ENTRIES[0].label).toContain("1");
    // Descending: the last colour band is the lowest r2, then No data.
    expect(LD_LEGEND_ENTRIES[5].color).toBe(getLdDotColor(0));
    expect(LD_LEGEND_ENTRIES[6].color).toBe(getLdDotColor(null));
    expect(LD_LEGEND_ENTRIES[6].label).toBe("No data");
  });

  it("maps each mid-bin r2 onto the legend entry that claims it", () => {
    // getLdDotColor bins by floor(r2 * 5); legend is descending, so bin i sits
    // at legend index (5 - i).
    for (const [r2, binIndex] of [[0.1, 0], [0.3, 1], [0.5, 2], [0.7, 3], [0.9, 4], [1, 5]]) {
      expect(getLdDotColor(r2)).toBe(LD_LEGEND_ENTRIES[5 - binIndex].color);
    }
  });
});

describe("buildPlotPoints", () => {
  it("maps position to x and -log10(p) to y", () => {
    const rows = [{ position: 500, pValue: 0.1 }];
    const [p] = buildPlotPoints(rows, REGION, LAYOUT);
    expect(p.x).toBeGreaterThan(LAYOUT.margin.left);
    expect(p.x).toBeLessThan(LAYOUT.width - LAYOUT.margin.right);
    expect(p.y).toBeGreaterThan(0);
  });

  it("places a more significant variant higher on the canvas", () => {
    const [weak, strong] = buildPlotPoints(
      [{ position: 100, pValue: 0.05 }, { position: 200, pValue: 1e-20 }],
      REGION, LAYOUT,
    );
    expect(strong.y).toBeLessThan(weak.y); // canvas y grows downward
  });

  it("colours by LD score", () => {
    const [p] = buildPlotPoints([{ position: 100, pValue: 0.01, LDS: 1 }], REGION, LAYOUT);
    expect(p.color).toBe(VKS_LD_DOT_COLORS[5]);
  });

  it("uses the no-data colour when LD is absent", () => {
    const [p] = buildPlotPoints([{ position: 100, pValue: 0.01 }], REGION, LAYOUT);
    expect(p.color).toBe("#00000030");
  });

  it("drops rows with a non-positive or missing pValue", () => {
    const points = buildPlotPoints(
      [{ position: 1, pValue: 0 }, { position: 2 }, { position: 3, pValue: -1 },
       { position: 4, pValue: 0.5 }],
      REGION, LAYOUT,
    );
    expect(points).toHaveLength(1);
    expect(points[0].row.position).toBe(4);
  });

  it("excludes rows outside the visible region", () => {
    const points = buildPlotPoints(
      [{ position: 5000, pValue: 0.01 }, { position: 500, pValue: 0.01 }],
      REGION, LAYOUT,
    );
    expect(points).toHaveLength(1);
    expect(points[0].row.position).toBe(500);
  });

  it("shares its x-scale with the genes track (computeRegionPlotWidth), not width - left - right", () => {
    // Regression guard for the two-stacked-canvases x-scale mismatch: the
    // genes track's plot width is canvasWidth - margin.left * 2 (asymmetric
    // by upstream design). buildPlotPoints must use the same formula so a
    // variant renders under the gene it actually sits in. LAYOUT has
    // right: 10 !== left: 40, so the two formulas diverge and this would
    // fail under the old `width - left - right` computation.
    const rows = [{ position: 500, pValue: 0.1 }];
    const [p] = buildPlotPoints(rows, REGION, LAYOUT);
    const plotWidth = computeRegionPlotWidth(LAYOUT.width, LAYOUT.margin);
    const expectedX =
      LAYOUT.margin.left +
      ((500 - REGION.start) / (REGION.end - REGION.start)) * plotWidth;
    expect(p.x).toBeCloseTo(expectedX);
    // Sanity check that this actually pins down a formula, not a coincidence:
    // the old, wrong formula would have produced a different x.
    const oldPlotWidth = LAYOUT.width - LAYOUT.margin.left - LAYOUT.margin.right;
    const oldX =
      LAYOUT.margin.left +
      ((500 - REGION.start) / (REGION.end - REGION.start)) * oldPlotWidth;
    expect(p.x).not.toBeCloseTo(oldX);
  });
});
