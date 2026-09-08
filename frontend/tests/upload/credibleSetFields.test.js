// frontend/tests/upload/credibleSetFields.test.js
import { describe, it, expect } from "vitest";
import {
  CS_REQUIRED_FIELDS,
  CS_OPTIONAL_FIELDS,
  CS_COL_OPTIONS,
  CREDIBLE_SET_COLUMN_ALIASES,
  missingCredibleSetFields,
  suggestCredibleSetMap,
} from "../../utils/upload/credibleSetFields.js";
import { selectedFieldsToColMap } from "../../utils/upload/colMap.js";

describe("field lists", () => {
  it("requires exactly the pipeline's required fields, in display order", () => {
    expect(CS_REQUIRED_FIELDS.map((f) => f.value)).toEqual([
      "chromosome", "position", "reference", "alt", "credibleSetId", "posteriorProbability",
    ]);
  });
  it("offers the optional fields and nothing GWAS-only", () => {
    expect(CS_OPTIONAL_FIELDS.map((f) => f.value)).toEqual(["pValue", "beta", "se", "n", "rsid"]);
    const offered = CS_COL_OPTIONS.map((o) => o.value);
    expect(offered).not.toContain("oddsRatio");
    expect(offered).not.toContain("eaf");
    expect(offered).not.toContain("maf");
    expect(offered).not.toContain("zScore");
  });
});

describe("suggestCredibleSetMap", () => {
  it("recognises fine-mapping headers", () => {
    expect(suggestCredibleSetMap(["CHR", "BP", "A2", "A1", "CS_ID", "PIP"])).toEqual({
      CHR: "chromosome", BP: "position", A2: "reference", A1: "alt",
      CS_ID: "credibleSetId", PIP: "posteriorProbability",
    });
  });
  it("accepts the SuSiE / FINEMAP spellings", () => {
    expect(suggestCredibleSetMap(["cs", "prob"])).toEqual({ cs: "credibleSetId", prob: "posteriorProbability" });
    expect(suggestCredibleSetMap(["signal", "posterior_prob"])).toEqual({
      signal: "credibleSetId", posterior_prob: "posteriorProbability",
    });
    expect(suggestCredibleSetMap(["credible_set", "pp"])).toEqual({
      credible_set: "credibleSetId", pp: "posteriorProbability",
    });
  });
  it("keeps the GWAS allele orientation (effect allele is alt)", () => {
    expect(suggestCredibleSetMap(["effect_allele", "other_allele"])).toEqual({
      effect_allele: "alt", other_allele: "reference",
    });
  });
  it("never proposes a GWAS-only field even when the header names one", () => {
    expect(suggestCredibleSetMap(["maf", "OR"])).toEqual({});
  });
  it("inherits the GWAS alias table minus the GWAS-only targets", () => {
    expect(CREDIBLE_SET_COLUMN_ALIASES.pval).toBe("pValue");
    expect(CREDIBLE_SET_COLUMN_ALIASES.maf).toBeUndefined();
  });
  it("never fuzzy-matches the set id or the probability", () => {
    // Neither header is an alias; both would otherwise fuzzy-match their
    // field. A wrong guess here silently reshuffles sets or corrupts
    // probabilities, so both must be alias-only.
    expect(suggestCredibleSetMap(["credibleset_identifier", "posterior_probs"])).toEqual({});
  });
  it("still maps explicit aliases for both", () => {
    expect(suggestCredibleSetMap(["probability", "cs_id"])).toEqual({
      probability: "posteriorProbability", cs_id: "credibleSetId",
    });
  });
});

describe("missingCredibleSetFields", () => {
  it("lists unmapped required fields in display order", () => {
    expect(missingCredibleSetFields({ chromosome: "CHR", alt: "A1" }).map((f) => f.value)).toEqual([
      "position", "reference", "credibleSetId", "posteriorProbability",
    ]);
    expect(missingCredibleSetFields(undefined)).toHaveLength(6);
  });
});

describe("selectedFieldsToColMap", () => {
  it("transposes {column: field} to {field: column} and drops nulls", () => {
    expect(selectedFieldsToColMap({ CHR: "chromosome", junk: null, PIP: "posteriorProbability" })).toEqual({
      chromosome: "CHR", posteriorProbability: "PIP",
    });
  });
});
