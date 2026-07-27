import { describe, it, expect, vi } from "vitest";
import {
  parseRegionParam,
  formatRegion,
  applyRegionExpand,
  regionAroundPosition,
  isGeneLookupQuery,
  resolveGeneOrVariantToRegion,
} from "../../utils/sifter/searchUtils.js";

describe("parseRegionParam", () => {
  it("parses chr:start-end", () => {
    expect(parseRegionParam("10:114700000-114800000")).toEqual({
      chr: "10", start: 114700000, end: 114800000,
    });
  });

  it("tolerates comma-grouped digits", () => {
    expect(parseRegionParam("10:114,700,000-114,800,000")).toEqual({
      chr: "10", start: 114700000, end: 114800000,
    });
  });

  it("returns null for a gene symbol", () => {
    expect(parseRegionParam("TCF7L2")).toBeNull();
  });
});

describe("formatRegion", () => {
  it("round-trips with parseRegionParam", () => {
    const r = { chr: "10", start: 1, end: 2 };
    expect(parseRegionParam(formatRegion(r))).toEqual(r);
  });
});

describe("applyRegionExpand", () => {
  // NB: upstream widens by HALF the expand value on each side
  // (`half = Math.floor(expandBp / 2)`), so the total width grows by expandBp.
  it("widens by half the expand value on each side", () => {
    expect(applyRegionExpand({ chr: "10", start: 100000, end: 200000 }, 50000))
      .toEqual({ chr: "10", start: 75000, end: 225000 });
  });

  it("clamps the start at 0, not 1", () => {
    expect(applyRegionExpand({ chr: "1", start: 100, end: 200 }, 50000))
      .toEqual({ chr: "1", start: 0, end: 25200 });
  });

  it("returns the region untouched when there is no expand", () => {
    const region = { chr: "10", start: 1, end: 2 };
    expect(applyRegionExpand(region, 0)).toBe(region);
  });
});

describe("regionAroundPosition", () => {
  // Same half-value convention as applyRegionExpand.
  it("builds a window of half the expand value either side of the point", () => {
    expect(regionAroundPosition("10", 114758349, 50000)).toEqual({
      chr: "10", start: 114733349, end: 114783349,
    });
  });

  it("falls back to a 50kb half-window when no expand is given", () => {
    expect(regionAroundPosition("10", 114758349, 0)).toEqual({
      chr: "10", start: 114708349, end: 114808349,
    });
  });
});

describe("isGeneLookupQuery", () => {
  it("treats a bare symbol as a gene lookup", () => {
    expect(isGeneLookupQuery("TCF7L2")).toBe(true);
  });

  it("does not treat coordinates as a gene lookup", () => {
    expect(isGeneLookupQuery("10:114700000-114800000")).toBe(false);
    expect(isGeneLookupQuery("10:114758349")).toBe(false);
  });
});

describe("resolveGeneOrVariantToRegion", () => {
  it("resolves a gene symbol to its bounds via the KP gene index", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        // The KP `gene` index returns records keyed `chromosome` (verified live).
        // resolveGeneOrVariantToRegion must map that onto a `chr` region.
        data: [{ chromosome: "10", start: 114710009, end: 114927437, name: "TCF7L2" }],
      }),
    });
    const region = await resolveGeneOrVariantToRegion("TCF7L2", { expandBp: 0, fetchImpl });
    expect(region).toEqual({ chr: "10", start: 114710009, end: 114927437 });
    expect(fetchImpl.mock.calls[0][0]).toContain("query/gene?q=TCF7L2");
  });

  it("applies the region expand to resolved gene bounds", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: [{ chromosome: "10", start: 200000, end: 300000 }] }),
    });
    // NB: a 1-character query is NOT treated as a gene lookup — isGeneLookupQuery
    // requires length >= 2. Use a real-looking symbol.
    // Expand applies HALF on each side: 50000 -> 25000 either way.
    const region = await resolveGeneOrVariantToRegion("PCSK9", { expandBp: 50000, fetchImpl });
    expect(region).toEqual({ chr: "10", start: 175000, end: 325000 });
  });

  it("passes coordinates straight through without a lookup", async () => {
    const fetchImpl = vi.fn();
    const region = await resolveGeneOrVariantToRegion("10:1-2", { expandBp: 0, fetchImpl });
    expect(region).toEqual({ chr: "10", start: 1, end: 2 });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("throws a useful error when the gene is unknown", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ data: [] }) });
    await expect(resolveGeneOrVariantToRegion("NOTAGENE", { fetchImpl }))
      .rejects.toThrow(/NOTAGENE/);
  });
});
