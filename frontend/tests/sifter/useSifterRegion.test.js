import { describe, it, expect, vi } from "vitest";
import {
  createSifterRegionResolver,
  MAX_REGION_SPAN_BP,
} from "../../composables/useSifterRegion.js";

describe("createSifterRegionResolver", () => {
  it("resolves coordinates without any network call", async () => {
    const fetchImpl = vi.fn();
    const { resolve } = createSifterRegionResolver({ fetchImpl });
    expect(await resolve("10:1-2", 0)).toEqual({ chr: "10", start: 1, end: 2 });
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it("resolves a gene symbol and applies the expand", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      // The KP `gene` index returns records keyed `chromosome`; the resolver
      // maps that onto a region's `chr`. Verified against the live API.
      json: async () => ({ data: [{ chromosome: "10", start: 200000, end: 300000 }] }),
    });
    const { resolve } = createSifterRegionResolver({ fetchImpl });
    // Expand applies HALF the value per side: 50000 -> 25000 either way.
    expect(await resolve("TCF7L2", 50000)).toEqual({
      chr: "10", start: 175000, end: 325000,
    });
  });

  it("surfaces a lookup service failure distinctly from a missing gene", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    const { resolve } = createSifterRegionResolver({ fetchImpl });
    await expect(resolve("TCF7L2", 0)).rejects.toThrow(/503/);
  });

  it("rejects an empty query with a user-facing message", async () => {
    const { resolve } = createSifterRegionResolver({ fetchImpl: vi.fn() });
    await expect(resolve("   ", 0)).rejects.toThrow(/region or gene/i);
  });

  it("wraps a rejected fetch (network failure) in a friendly message instead of propagating it raw", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const { resolve } = createSifterRegionResolver({ fetchImpl });
    await expect(resolve("TCF7L2", 0)).rejects.toThrow(/Gene lookup failed/);
    // Distinct from the non-ok-status message, which names an HTTP status.
    await expect(resolve("TCF7L2", 0)).rejects.not.toThrow(/HTTP/);
  });

  describe("locus-scale span cap", () => {
    it("resolves a region comfortably within the cap", async () => {
      const fetchImpl = vi.fn();
      const { resolve } = createSifterRegionResolver({ fetchImpl });
      expect(await resolve("10:1000000-2000000", 0)).toEqual({
        chr: "10",
        start: 1000000,
        end: 2000000,
      });
      expect(fetchImpl).not.toHaveBeenCalled();
    });

    it("rejects a region well over the cap, naming both the actual span and the limit", async () => {
      const { resolve } = createSifterRegionResolver({ fetchImpl: vi.fn() });
      // 1:1-49000001 spans exactly 49,000,000 bp (49.0 Mb).
      await expect(resolve("1:1-49000001", 0)).rejects.toThrow(
        /49\.0 Mb.*3\.0 Mb/s
      );
    });

    it("resolves a region exactly at the cap (boundary is inclusive)", async () => {
      const { resolve } = createSifterRegionResolver({ fetchImpl: vi.fn() });
      const start = 1000000;
      const end = start + MAX_REGION_SPAN_BP;
      expect(await resolve(`5:${start}-${end}`, 0)).toEqual({
        chr: "5",
        start,
        end,
      });
    });

    it("rejects a region just 1 bp over the cap", async () => {
      const { resolve } = createSifterRegionResolver({ fetchImpl: vi.fn() });
      const start = 1000000;
      const end = start + MAX_REGION_SPAN_BP + 1;
      await expect(resolve(`5:${start}-${end}`, 0)).rejects.toThrow(
        /Region spans 3\.0 Mb/
      );
    });

    it("rejects a gene lookup whose bounds plus expand exceed the cap, proving the check runs after expansion", async () => {
      const fetchImpl = vi.fn().mockResolvedValue({
        ok: true,
        // Raw gene span is 2.5 Mb (500000 -> 3000000), comfortably under the
        // cap on its own. Only once the ±500 kb expand is added (half of the
        // 1,000,000 expandBp) does the span cross 3 Mb, so this only fails if
        // the cap check runs AFTER expansion is applied.
        json: async () => ({ data: [{ chromosome: "7", start: 500000, end: 3000000 }] }),
      });
      const { resolve } = createSifterRegionResolver({ fetchImpl });
      await expect(resolve("BIGGENE", 1000000)).rejects.toThrow(/Region spans 3\.5 Mb/);
      expect(fetchImpl).toHaveBeenCalled();
    });
  });
});
