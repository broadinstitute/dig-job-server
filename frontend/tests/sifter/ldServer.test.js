import { describe, it, expect } from "vitest";
import {
  resolveLdPopulation,
  rowToLdVariant,
  pickLeadVariantRow,
  buildLdScoresUrl,
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

  it("defaults the genome build to GRCh37 - GWAS-CE uploads are hg19", () => {
    expect(LD_SERVER_DEFAULTS.genomeBuild).toBe("GRCh37");
  });
});
