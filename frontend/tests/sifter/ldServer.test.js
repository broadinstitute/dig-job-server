import { describe, it, expect, vi, afterEach } from "vitest";
import {
  resolveLdPopulation,
  rowToLdVariant,
  pickLeadVariantRow,
  buildLdScoresUrl,
  fetchLdScoreMapForRefRow,
  lookupLdScore,
  LD_SERVER_DEFAULTS,
} from "../../utils/sifter/ldServer.js";

describe("resolveLdPopulation", () => {
  it("passes GWAS-CE upload ancestry codes through unchanged", () => {
    // frontend/pages/upload/index.vue offers exactly these five.
    expect(resolveLdPopulation("EUR")).toBe("EUR");
    expect(resolveLdPopulation("AFR")).toBe("AFR");
    expect(resolveLdPopulation("EAS")).toBe("EAS");
    expect(resolveLdPopulation("SAS")).toBe("SAS");
    expect(resolveLdPopulation("AMR")).toBe("AMR");
  });

  it("defaults to ALL when ancestry is missing", () => {
    expect(resolveLdPopulation(null)).toBe("ALL");
    expect(resolveLdPopulation("")).toBe("ALL");
    expect(resolveLdPopulation("Mixed")).toBe("ALL");
  });
});

describe("rowToLdVariant", () => {
  it("converts a bioindex row to the GEM variant form", () => {
    expect(rowToLdVariant({ varId: "10:114758349:C:T" })).toBe("10:114758349_C/T");
  });

  it("prefers an existing Variant ID field", () => {
    expect(rowToLdVariant({ "Variant ID": "1:2_A/G" })).toBe("1:2_A/G");
  });

  it("returns null when there is nothing to convert", () => {
    expect(rowToLdVariant({})).toBeNull();
  });
});

describe("pickLeadVariantRow", () => {
  // Upstream reads row["P-Value"], NOT row.pValue — these must be DECORATED
  // rows (Task 3B). Passing raw bioindex rows silently returns rows[0].
  it("picks the row with the smallest P-Value", () => {
    const rows = [
      { Position: 1, "P-Value": 0.04 },
      { Position: 2, "P-Value": 1e-12 },
      { Position: 3, "P-Value": 0.2 },
    ];
    expect(pickLeadVariantRow(rows).Position).toBe(2);
  });

  it("returns rows[0] when no row carries a numeric P-Value", () => {
    const rows = [{ Position: 1 }, { Position: 2 }];
    expect(pickLeadVariantRow(rows).Position).toBe(1);
  });

  it("returns null for an empty set", () => {
    expect(pickLeadVariantRow([])).toBeNull();
  });
});

describe("buildLdScoresUrl", () => {
  it("targets GRCh37 and 1000G with the resolved population", () => {
    // Real upstream signature is { population, refVariant, region, ... }.
    // Read it from source; do not assume.
    const url = buildLdScoresUrl({
      population: "EUR",
      refVariant: "10:114758349_C/T",
      region: { chr: "10", start: 114700000, end: 114800000 },
    });
    expect(url).toContain("/genome_builds/GRCh37/");
    expect(url).toContain("/references/1000G/");
    expect(url).toContain("/populations/EUR/variants");
    expect(url).toContain("correlation=rsquare");
  });

  it("maps the reference variant, region bounds, and default limit into their own query params", () => {
    // Guards against a regression that drops variant/region/limit params, or
    // maps region.start/region.end onto the wrong (or the same) key, while
    // still passing the substring assertions above.
    const url = buildLdScoresUrl({
      population: "EUR",
      refVariant: "10:114758349_C/T",
      region: { chr: "10", start: 114700000, end: 114800000 },
    });

    const parsed = new URL(url);
    expect(parsed.searchParams.get("variant")).toBe("10:114758349_C/T");
    expect(parsed.searchParams.get("chrom")).toBe("10");
    // start and end use distinct values so a swap or duplicated bound fails.
    expect(parsed.searchParams.get("start")).toBe("114700000");
    expect(parsed.searchParams.get("stop")).toBe("114800000");
    expect(parsed.searchParams.get("limit")).toBe(String(LD_SERVER_DEFAULTS.limit));
    // Path segments (population + genome build) still correct via the URL parser.
    expect(parsed.pathname).toBe(
      "/ld/genome_builds/GRCh37/references/1000G/populations/EUR/variants"
    );
  });

  it("defaults the genome build to GRCh37 - GWAS-CE uploads are hg19", () => {
    expect(LD_SERVER_DEFAULTS.genomeBuild).toBe("GRCh37");
  });
});

describe("LD allele orientation (GWAS-CE divergence)", () => {
  // Live regression from t2d-alex-test. GWAS-CE builds variant IDs from the
  // uploader's other/effect allele columns; the U-M LD server keys on the
  // reference genome's REF/ALT. When they disagree the server answers with an
  // EMPTY BUT NON-ERROR payload, so the whole dataset rendered grey and nothing
  // anywhere reported a failure. Verified live: 22:50356302_T/C returned 0
  // partners, 22:50356302_C/T returned 571.
  const REGION = { chr: "22", start: 50350000, end: 50450000 };
  const SESSION = { ancestry: "AMR", region: REGION };
  const REF_ROW = { "Variant ID": "22:50356302_T/C" }; // uploaded orientation

  const EMPTY = { error: null, data: { variant1: [], variant2: [], correlation: [] } };
  const POPULATED = {
    error: null,
    data: {
      variant1: ["22:50356302_C/T", "22:50356302_C/T"],
      // As the server really returns them - reference-genome orientation.
      variant2: ["22:50350302_C/T", "22:50351977_G/A"],
      correlation: [0.42, 0.87],
    },
  };

  function stubFetch(responses) {
    const calls = [];
    globalThis.fetch = vi.fn((url) => {
      calls.push(url);
      return Promise.resolve({
        json: () => Promise.resolve(responses[calls.length - 1]),
      });
    });
    return calls;
  }

  afterEach(() => {
    delete globalThis.fetch;
  });

  it("retries with flipped alleles when the uploaded orientation returns nothing", async () => {
    const calls = stubFetch([EMPTY, POPULATED]);
    const { scoreMap } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);

    expect(calls).toHaveLength(2);
    expect(calls[0]).toContain("22%3A50356302_T%2FC");
    expect(calls[1]).toContain("22%3A50356302_C%2FT");
    expect(scoreMap.size).toBeGreaterThan(0);
  });

  it("does not make a second request when the first orientation works", async () => {
    const calls = stubFetch([POPULATED]);
    await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);
    expect(calls).toHaveLength(1);
  });

  it("reports the row's own variant id, not the flip the server answered", async () => {
    // The plot locates the reference dot by matching this against our rows,
    // which carry the uploaded orientation.
    stubFetch([EMPTY, POPULATED]);
    const { refVariant } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);
    expect(refVariant).toBe("22:50356302_T/C");
  });

  it("scores rows whose alleles are flipped relative to the server's", async () => {
    stubFetch([EMPTY, POPULATED]);
    const { scoreMap } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);

    expect(lookupLdScore(scoreMap, { "Variant ID": "22:50350302_T/C" })).toBe(0.42);
    expect(lookupLdScore(scoreMap, { "Variant ID": "22:50351977_A/G" })).toBe(0.87);
  });

  it("still scores rows that already match the server's orientation", async () => {
    stubFetch([POPULATED]);
    const { scoreMap } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);

    expect(lookupLdScore(scoreMap, { "Variant ID": "22:50350302_C/T" })).toBe(0.42);
    expect(lookupLdScore(scoreMap, { varId: "22:50351977:G:A" })).toBe(0.87);
  });

  it("does not match a different position just because alleles line up", async () => {
    stubFetch([POPULATED]);
    const { scoreMap } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);
    expect(lookupLdScore(scoreMap, { "Variant ID": "22:99999999_T/C" })).toBeNull();
  });

  it("gives up after both orientations come back empty", async () => {
    const calls = stubFetch([EMPTY, EMPTY]);
    const { scoreMap } = await fetchLdScoreMapForRefRow(REF_ROW, SESSION, REGION);

    expect(calls).toHaveLength(2);
    expect(scoreMap.size).toBe(0);
  });
});
