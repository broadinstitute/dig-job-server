import { describe, it, expect } from "vitest";
import { buildAssociationsScatter } from "../utils/sifterPlot.js";

describe("buildAssociationsScatter", () => {
  it("plots position vs -log10(pValue) as a scattergl trace", () => {
    const { data } = buildAssociationsScatter(
      [{ chromosome: "10", position: 100, reference: "A", alt: "G", pValue: 0.01 }],
      { region: "10:1-200" },
    );
    expect(data[0].type).toBe("scattergl");
    expect(data[0].x).toEqual([100]);
    expect(data[0].y[0]).toBeCloseTo(2, 6);
  });

  it("drops non-positive/invalid pValues", () => {
    const { data } = buildAssociationsScatter([
      { position: 1, pValue: 0 },
      { position: 2, pValue: 1e-8 },
    ]);
    expect(data[0].x).toEqual([2]);
  });

  it("drops records with missing/undefined pValue", () => {
    const { data } = buildAssociationsScatter([
      { position: 1 }, // undefined pValue
      { position: 2, pValue: 1e-8 },
    ]);
    expect(data[0].x).toEqual([2]);
  });

  it("drops records with non-numeric string pValue", () => {
    const { data } = buildAssociationsScatter([
      { position: 1, pValue: "NA" },
      { position: 2, pValue: 1e-8 },
    ]);
    expect(data[0].x).toEqual([2]);
  });
});
