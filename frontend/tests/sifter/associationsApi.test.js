import { describe, it, expect, vi } from "vitest";
import {
  ASSOCIATIONS_INDEX_LAYOUT,
  associationsIndexName,
  buildAssociationsUrl,
  fetchAllPages,
} from "../../utils/sifter/associationsApi.js";

const BASE = "https://gwas-ce.kpndataregistry.org/bioidx/api/bio/";
const GUID = "f83b34c1";

describe("associationsIndexName", () => {
  it("returns the shared index name under the shared layout", () => {
    expect(associationsIndexName(GUID, "shared")).toBe("associations");
  });

  it("returns a per-dataset index name under the per-dataset layout", () => {
    expect(associationsIndexName(GUID, "per-dataset")).toBe(`associations-${GUID}`);
  });
});

describe("buildAssociationsUrl", () => {
  // The deployed layout. The pipeline creates one index per dataset
  // (variant_sifter_pipeline/index_build.py), so this must stay in step with it —
  // flipping one without the other silently queries an index that does not exist.
  it("defaults to the per-dataset layout, matching what the pipeline creates", () => {
    expect(ASSOCIATIONS_INDEX_LAYOUT).toBe("per-dataset");
  });

  it("encodes q as <guid>,<region> with fmt=row", () => {
    expect(buildAssociationsUrl(BASE, GUID, "10:1-200")).toBe(
      `${BASE}query/associations-${GUID}?q=f83b34c1%2C10%3A1-200&fmt=row`,
    );
  });

  // Regression: bioindex returns continuation:null whenever limit is set,
  // which silently truncates a dense region to one page.
  it("never sends a limit param", () => {
    expect(buildAssociationsUrl(BASE, GUID, "1:1-50000000")).not.toContain("limit");
  });

  it("keeps the guid in q under the per-dataset layout so only the name varies", () => {
    const url = buildAssociationsUrl(BASE, GUID, "10:1-200", "per-dataset");
    expect(url).toContain(`query/associations-${GUID}?`);
    expect(url).toContain("q=f83b34c1%2C10%3A1-200");
  });
});

describe("fetchAllPages", () => {
  it("follows continuation tokens and concatenates data", async () => {
    const pages = [
      { ok: true, json: async () => ({ data: [{ position: 1 }], continuation: "t1" }) },
      { ok: true, json: async () => ({ data: [{ position: 2 }] }) },
    ];
    const fetchImpl = vi.fn().mockImplementation(() => Promise.resolve(pages.shift()));
    const rows = await fetchAllPages(BASE, "https://x/first", { fetchImpl });
    expect(rows).toEqual([{ position: 1 }, { position: 2 }]);
    expect(fetchImpl.mock.calls[1][0]).toContain("cont?token=t1");
  });

  it("throws on a non-ok response", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(fetchAllPages("b/", "u", { fetchImpl })).rejects.toThrow("500");
  });

  it("stops at maxPages", async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: [{}], continuation: "loop" }),
    });
    const rows = await fetchAllPages("b/", "u", { fetchImpl, maxPages: 3 });
    expect(rows).toHaveLength(3);
  });
});
