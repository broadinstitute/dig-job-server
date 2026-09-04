import { describe, it, expect } from "vitest";
import {
  suggestColumnMap,
  similarity,
  GWAS_COLUMN_ALIASES,
  NEVER_FUZZY_MATCH,
} from "../../utils/upload/suggestColumnMap.js";

// The canonical fields the upload form offers.
const TARGETS = [
  "chromosome", "position", "rsid", "reference", "alt", "pValue",
  "beta", "oddsRatio", "se", "n", "eaf", "maf", "zScore",
];

const suggest = (cols) => suggestColumnMap(cols, TARGETS);

describe("allele orientation", () => {
  // The single most destructive thing this file can get wrong. GWAS-CE treats
  // `alt` as the EFFECT allele and `reference` as the other allele; the pipeline
  // then canonicalises against the reference genome, swapping alleles AND
  // negating beta. An inverted mapping therefore inverts effect directions.
  it("maps the effect allele to `alt` and the other allele to `reference`", () => {
    expect(suggest(["A1", "A2"])).toEqual({ A1: "alt", A2: "reference" });
    expect(suggest(["effect_allele", "other_allele"])).toEqual({
      effect_allele: "alt",
      other_allele: "reference",
    });
    expect(suggest(["EA", "NEA"])).toEqual({ EA: "alt", NEA: "reference" });
  });

  it("treats REF as the other allele and ALT as the effect allele", () => {
    // data-registry-api's mskkp.py maps these the other way round; following it
    // would swap every allele pair in the dataset.
    expect(suggest(["REF", "ALT"])).toEqual({ REF: "reference", ALT: "alt" });
  });

  it("never fuzzy-matches an allele or effect field", () => {
    // "allele_thing" is close enough to trip a similarity match; it must not.
    const out = suggest(["allele_thing", "betamax"]);
    expect(out.allele_thing).toBeUndefined();
    expect(out.betamax).toBeUndefined();
    expect([...NEVER_FUZZY_MATCH].sort()).toEqual(
      ["alt", "beta", "oddsRatio", "reference"].sort(),
    );
  });
});

describe("EAF vs MAF", () => {
  // hcm.py folds `maf` into effect_allele_frequency. MAF is by definition <= 0.5
  // and EAF is not, so conflating them corrupts whichever the file actually has.
  it("keeps them distinct", () => {
    expect(suggest(["EAF", "MAF"])).toEqual({ EAF: "eaf", MAF: "maf" });
    expect(GWAS_COLUMN_ALIASES.maf).toBe("maf");
    expect(GWAS_COLUMN_ALIASES.eaf).toBe("eaf");
  });

  it("maps common frequency spellings to eaf", () => {
    expect(suggest(["Freq"])).toEqual({ Freq: "eaf" });
    expect(suggest(["A1FREQ"])).toEqual({ A1FREQ: "eaf" });
  });
});

describe("real upload headers", () => {
  it("maps the SLE file, whose SNP/SE/Freq columns were previously left unmapped", () => {
    const cols = ["SNP", "CHR", "POS", "A1", "A2", "Freq", "Beta",
                  "Pvalue", "SE", "Sample_Cases", "Sample_Controls"];
    expect(suggest(cols)).toMatchObject({
      SNP: "rsid", CHR: "chromosome", POS: "position",
      A1: "alt", A2: "reference", Freq: "eaf",
      Beta: "beta", Pvalue: "pValue", SE: "se",
    });
  });

  it("maps a GWAS-catalog style header", () => {
    const cols = ["chromosome", "base_pair_location", "effect_allele",
                  "other_allele", "beta", "standard_error", "p_value",
                  "effect_allele_frequency"];
    expect(suggest(cols)).toMatchObject({
      chromosome: "chromosome", base_pair_location: "position",
      effect_allele: "alt", other_allele: "reference", beta: "beta",
      standard_error: "se", p_value: "pValue", effect_allele_frequency: "eaf",
    });
  });
});

describe("claiming", () => {
  it("assigns each target at most once when columns compete", () => {
    // Both alias to the effect allele; only one may win, or the form would show
    // two columns mapped to the same field.
    const out = suggest(["A1", "effect_allele"]);
    const alts = Object.values(out).filter((v) => v === "alt");
    expect(alts).toHaveLength(1);
  });

  it("leaves unrecognised columns unmapped rather than guessing wildly", () => {
    const out = suggest(["Sample_Cases", "INFO", "weird_column_xyz"]);
    expect(out.weird_column_xyz).toBeUndefined();
  });

  it("is case and whitespace insensitive", () => {
    expect(suggest(["  ChRoM  "])).toEqual({ "  ChRoM  ": "chromosome" });
  });
});

describe("neverFuzzy parameter", () => {
  it("defaults to NEVER_FUZZY_MATCH, leaving GWAS behaviour unchanged, but a caller can widen it", () => {
    expect(suggestColumnMap(["chromosom"], TARGETS)).toEqual({ chromosom: "chromosome" });
    expect(
      suggestColumnMap(["chromosom"], TARGETS, GWAS_COLUMN_ALIASES, new Set([...NEVER_FUZZY_MATCH, "chromosome"])),
    ).toEqual({});
  });
});

describe("similarity", () => {
  it("scores identical strings 1 and unrelated strings low", () => {
    expect(similarity("position", "position")).toBe(1);
    expect(similarity("position", "zzzz")).toBeLessThan(0.3);
  });
});
