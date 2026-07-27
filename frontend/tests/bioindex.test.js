import { describe, it, expect, vi } from "vitest";
import { buildAssociationsUrl, fetchAllPages } from "../utils/bioindex.js";

describe("buildAssociationsUrl", () => {
  it("encodes q as <guid>,<region> with fmt=row", () => {
    const url = buildAssociationsUrl("https://x/gwas-ce/api/bio/", "g1", "10:1-200");
    expect(url).toBe("https://x/gwas-ce/api/bio/query/associations?q=g1%2C10%3A1-200&fmt=row");
  });

  // Regression: bioindex returns `continuation: null` whenever `limit` is set,
  // which silently truncates a dense region to one page. Verified against the
  // live gwas-ce index: a 50Mb region with &limit=5000 returned count=5000 and
  // no continuation, while the same region without a limit paged correctly.
  it("never sends a limit param, which would suppress continuation tokens", () => {
    const url = buildAssociationsUrl("https://x/gwas-ce/api/bio/", "g1", "1:1-50000000");
    expect(url).not.toContain("limit");
  });
});

describe("fetchAllPages", () => {
  it("follows continuation tokens and concatenates data", async () => {
    const pages = [
      { ok: true, json: async () => ({ data: [{ position: 1 }], continuation: "t1" }) },
      { ok: true, json: async () => ({ data: [{ position: 2 }] }) },
    ];
    const fetchImpl = vi.fn().mockImplementation(() => Promise.resolve(pages.shift()));
    const recs = await fetchAllPages("https://x/gwas-ce/api/bio/", "https://x/first", { fetchImpl });
    expect(recs).toEqual([{ position: 1 }, { position: 2 }]);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(fetchImpl.mock.calls[1][0]).toContain("cont?token=t1");
  });

  it("throws on a non-ok response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(fetchAllPages("b/", "u", { fetchImpl })).rejects.toThrow("500");
  });

  it("stops at maxPages to guard runaway regions", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: [{}], continuation: "loop" }),
    });
    const recs = await fetchAllPages("b/", "u", { fetchImpl, maxPages: 3 });
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(recs).toHaveLength(3);
  });
});
