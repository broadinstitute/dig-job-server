import { describe, it, expect, vi } from "vitest";
import { createSifterRegionResolver } from "../../composables/useSifterRegion.js";

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
});
