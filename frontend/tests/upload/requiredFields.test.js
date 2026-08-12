import { describe, it, expect } from "vitest";
import {
  REQUIRED_FIELDS,
  missingRequiredFields,
} from "../../utils/upload/requiredFields.js";

const values = () => REQUIRED_FIELDS.map((f) => f.value);

// A PGC-style case/control GWAS: odds ratio and p-value, no beta, no standard
// error. This is the shape the form used to reject.
const OR_AND_P_ONLY = {
  chromosome: "CHR",
  position: "BP",
  rsid: "SNP",
  reference: "A2",
  alt: "A1",
  pValue: "P",
  oddsRatio: "OR",
};

describe("REQUIRED_FIELDS", () => {
  it("does not require se", () => {
    // No method reads it -- sLDSC derives Z from p and the sign of beta, MAGMA
    // and PIGEAN carry only (variant, p, n), and falcon_prep recovers SE as
    // |beta/z|. Requiring it made OR+p uploads impossible.
    expect(values()).not.toContain("se");
  });

  it("requires exactly the fields every method consumes", () => {
    expect(values()).toEqual([
      "chromosome",
      "position",
      "rsid",
      "reference",
      "alt",
      "pValue",
    ]);
  });

  it("does not require the effect size or the sample size", () => {
    // Both are real requirements, but neither is a single named column: the
    // page checks beta-or-oddsRatio and n-or-effectiveN separately. Listing
    // either here would demand one specific column and reject the other form.
    expect(values()).not.toContain("beta");
    expect(values()).not.toContain("oddsRatio");
    expect(values()).not.toContain("n");
  });
});

describe("missingRequiredFields", () => {
  it("accepts an odds-ratio GWAS with no beta and no se", () => {
    expect(missingRequiredFields(OR_AND_P_ONLY)).toEqual([]);
  });

  it("still accepts a mapping that happens to include se", () => {
    // Dropping se from the required list must not make it forbidden -- most
    // uploads do carry one.
    expect(missingRequiredFields({ ...OR_AND_P_ONLY, se: "SE" })).toEqual([]);
  });

  it("reports each unmapped field by its display name", () => {
    const { pValue, rsid, ...rest } = OR_AND_P_ONLY;
    expect(missingRequiredFields(rest).map((f) => f.name)).toEqual([
      "rsID",
      "pValue",
    ]);
  });

  it("reports every field for an empty or absent col_map", () => {
    expect(missingRequiredFields({})).toHaveLength(REQUIRED_FIELDS.length);
    expect(missingRequiredFields(undefined)).toHaveLength(
      REQUIRED_FIELDS.length,
    );
  });

  it("treats a mapped-but-empty column as mapped", () => {
    // Matches the `in` check the page has always used here; formIncomplete
    // applies the stricter truthiness test separately.
    expect(missingRequiredFields({ ...OR_AND_P_ONLY, pValue: "" })).toEqual([]);
  });
});
