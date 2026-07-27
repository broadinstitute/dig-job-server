import { describe, it, expect, vi } from "vitest";
import { createFakeCtx } from "../helpers/fakeCanvasContext.js";
import { fetchGenesTrackData } from "../../utils/sifter/genes.js";
import {
  layoutGenesInLanes,
  computeGeneTrackHitRegions,
  findGeneHitAtCanvasPoint,
  computeGenesTrackCanvasHeight,
  renderGenesTrack,
  VKS_GENE_TRACK_ROW_HEIGHT,
} from "../../utils/sifter/genesTrackRender.js";

// layoutGenesInLanes takes xPosByPixel as a plain pixels-per-basepair
// number (gene.start - xMin) * xPosByPixel — not a callback. This matches
// how production code computes it (computeGeneTrackHitRegions:
// `plotWidth / (xMax - xMin || 1)`). All layoutGenesInLanes calls below use
// xMin=0, xMax=100000, so this is pixels-per-bp for a 1000px-wide plot over
// that span.
const xPosByPixel = 1000 / 100000;

const REGION = { chr: "10", start: 0, end: 100000 };
const MARGIN = { top: 10, right: 20, bottom: 10, left: 0 };

describe("fetchGenesTrackData", () => {
  it("queries the region-keyed KP genes index", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: [{ name: "TCF7L2", start: 1, end: 2, chromosome: "10" }] }),
    });
    const genes = await fetchGenesTrackData(
      { chr: "10", start: 114700000, end: 114800000 },
      "GRCh37",
      null,
      fetchImpl,
    );
    expect(genes).toHaveLength(1);
    expect(fetchImpl.mock.calls[0][0]).toContain("query/genes?q=");
    expect(fetchImpl.mock.calls[0][0]).toContain("10%3A114700000-114800000");
  });

  it("returns an empty array when the genes source fails, never throws", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    await expect(
      fetchGenesTrackData({ chr: "10", start: 1, end: 2 }, "GRCh37", null, fetchImpl),
    ).resolves.toEqual([]);
  });

  it("returns an empty array when the fetch rejects outright", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("network"));
    await expect(
      fetchGenesTrackData({ chr: "10", start: 1, end: 2 }, "GRCh37", null, fetchImpl),
    ).resolves.toEqual([]);
  });
});

describe("layoutGenesInLanes", () => {
  // Returns { layouts, laneCount } — NOT an array of lanes.
  it("puts non-overlapping genes in one lane", () => {
    const genes = [
      { name: "A", start: 100, end: 200 },
      { name: "B", start: 90000, end: 95000 },
    ];
    const { layouts, laneCount } = layoutGenesInLanes(genes, 0, 100000, 0, xPosByPixel);
    expect(layouts).toHaveLength(2);
    expect(laneCount).toBe(1);
    expect(layouts.every((l) => l.lane === 0)).toBe(true);
  });

  it("pushes overlapping genes onto separate lanes", () => {
    const genes = [
      { name: "A", start: 1000, end: 50000 },
      { name: "B", start: 2000, end: 51000 },
    ];
    const { layouts, laneCount } = layoutGenesInLanes(genes, 0, 100000, 0, xPosByPixel);
    expect(laneCount).toBeGreaterThan(1);
    expect(layouts[1].lane).toBeGreaterThan(layouts[0].lane);
  });

  it("returns no layouts and zero lanes for no genes", () => {
    expect(layoutGenesInLanes([], 0, 1000, 0, xPosByPixel)).toEqual({
      layouts: [], laneCount: 0,
    });
  });

  it("drops genes entirely outside the region", () => {
    const genes = [{ name: "Far", start: 500000, end: 600000 }];
    const { layouts, laneCount } = layoutGenesInLanes(genes, 0, 100000, 0, xPosByPixel);
    expect(layouts).toHaveLength(0);
    expect(laneCount).toBe(0);
  });
});

describe("computeGenesTrackCanvasHeight", () => {
  it("is margin.top plus one row height per lane", () => {
    expect(computeGenesTrackCanvasHeight(MARGIN, 1)).toBe(MARGIN.top + VKS_GENE_TRACK_ROW_HEIGHT);
    expect(computeGenesTrackCanvasHeight(MARGIN, 2)).toBe(MARGIN.top + VKS_GENE_TRACK_ROW_HEIGHT * 2);
  });

  it("is zero when there are no lanes", () => {
    expect(computeGenesTrackCanvasHeight(MARGIN, 0)).toBe(0);
  });
});

describe("computeGeneTrackHitRegions / findGeneHitAtCanvasPoint", () => {
  // Hit regions carry left/right/top/bottom/centerX/centerY — not x/y/width/height.
  const genes = [{ name: "TCF7L2", start: 40000, end: 60000 }];

  it("produces a region with the documented bounds shape", () => {
    const ctx = createFakeCtx();
    const [region] = computeGeneTrackHitRegions(genes, REGION, MARGIN, 1000, ctx);
    for (const key of ["gene", "left", "right", "top", "bottom", "centerX", "centerY"]) {
      expect(region).toHaveProperty(key);
    }
    expect(region.gene.name).toBe("TCF7L2");
    expect(region.right).toBeGreaterThan(region.left);
    expect(region.bottom).toBeGreaterThan(region.top);
  });

  it("finds the gene whose box contains the point", () => {
    const ctx = createFakeCtx();
    const regions = computeGeneTrackHitRegions(genes, REGION, MARGIN, 1000, ctx);
    const hit = findGeneHitAtCanvasPoint(regions, regions[0].centerX, regions[0].centerY);
    expect(hit?.gene.name).toBe("TCF7L2");
  });

  it("returns null well outside any box", () => {
    const ctx = createFakeCtx();
    const regions = computeGeneTrackHitRegions(genes, REGION, MARGIN, 1000, ctx);
    expect(findGeneHitAtCanvasPoint(regions, 99999, 99999)).toBeNull();
  });
});

describe("renderGenesTrack", () => {
  it("issues drawing calls and labels each gene", () => {
    const ctx = createFakeCtx();
    renderGenesTrack(ctx, {
      genes: [{ name: "TCF7L2", start: 40000, end: 60000, exons: [] }],
      visibleRegion: REGION,
      margin: MARGIN,
      canvasWidth: 1000,
      canvasHeight: computeGenesTrackCanvasHeight(MARGIN, 1),
    });
    expect(ctx.calls.length).toBeGreaterThan(0);
    expect(ctx.calls.some((c) => c.fn === "fillText")).toBe(true);
  });

  it("draws nothing for an empty gene list", () => {
    const ctx = createFakeCtx();
    renderGenesTrack(ctx, {
      genes: [], visibleRegion: REGION, margin: MARGIN, canvasWidth: 1000, canvasHeight: 0,
    });
    expect(ctx.calls.some((c) => c.fn === "fillText")).toBe(false);
  });
});
