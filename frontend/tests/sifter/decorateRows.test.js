import { describe, it, expect } from "vitest";
import { decorateAssociationRows } from "../../utils/sifter/decorateRows.js";

const RAW = {
  chromosome: "10", position: 114758349, reference: "C", alt: "T",
  pValue: 1e-9, beta: 0.4, stdErr: 0.05,
};

describe("decorateAssociationRows", () => {
  it("maps raw bioindex fields onto upstream display names", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r["P-Value"]).toBe(1e-9);
    expect(r.Position).toBe(114758349);
    expect(r.Beta).toBe(0.4);
    expect(r["Standard Error"]).toBe(0.05);
  });

  it("builds Variant ID with the chr:pos_ref/alt join", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r["Variant ID"]).toBe("10:114758349_C/T");
  });

  it("builds Ref/Alt and Locus", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r["Ref/Alt"]).toBe("C/T");
    expect(r.Locus).toBe("10:114758349");
  });

  it("calculates -log10(P-Value)", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r["-log10(P-Value)"]).toBeCloseTo(9, 10);
  });

  it("copies chromosome through to both chromosome and chr", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r.chromosome).toBe("10");
    expect(r.chr).toBe("10");
  });

  // Verified against the real dataConvert.js (dig-dug-portal@5619cbfe1): the
  // "raw" rule computes `rawValue = (!!d[field]) ? d[field] : ...`, then has a
  // separate guard `if (d[field] === 0) rawValue = "0"` before the `if
  // (!!rawValue)` assignment check. So an exact numeric 0 is NOT dropped — it
  // is coerced to the (truthy) string "0" and assigned. Confirmed by running
  // upstream's convertData() directly against `{ ...RAW, beta: 0 }`, which
  // yields `Beta: "0"`. (The task brief asserted the opposite — that beta: 0
  // yields no Beta field at all — which does not match upstream.)
  it("stringifies a raw field of exactly 0 rather than omitting it, per upstream's 0-to-\"0\" coercion", () => {
    const [r] = decorateAssociationRows([{ ...RAW, beta: 0 }]);
    expect(r.Beta).toBe("0");
  });

  it("omits a raw field whose value is a non-zero falsy value (null/undefined/empty string)", () => {
    const [r] = decorateAssociationRows([{ ...RAW, beta: undefined }]);
    expect(r.Beta).toBeUndefined();
  });

  it("derives Z Score from Beta / Standard Error when absent", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r["Z Score"]).toBeCloseTo(8, 10);
  });

  it("keeps an existing Z Score rather than recomputing", () => {
    const [r] = decorateAssociationRows([{ ...RAW, zScore: 42 }]);
    expect(r["Z Score"]).toBe(42);
  });

  it("does not derive Z Score when stdErr is absent or zero", () => {
    expect(decorateAssociationRows([{ ...RAW, stdErr: undefined }])[0]["Z Score"]).toBeUndefined();
    expect(decorateAssociationRows([{ ...RAW, stdErr: 0 }])[0]["Z Score"]).toBeUndefined();
  });

  it("preserves the raw fields alongside the decorated ones", () => {
    const [r] = decorateAssociationRows([RAW]);
    expect(r.pValue).toBe(1e-9);
    expect(r.position).toBe(114758349);
  });

  it("returns [] for empty or non-array input", () => {
    expect(decorateAssociationRows([])).toEqual([]);
    expect(decorateAssociationRows(null)).toEqual([]);
  });

  it("stringifies undefined/null as literal text in join, matching upstream (regression: Array.join renders them as empty)", () => {
    const [r] = decorateAssociationRows([{ ...RAW, reference: undefined }]);
    expect(r["Ref/Alt"]).toBe("undefined/T");
  });
});
