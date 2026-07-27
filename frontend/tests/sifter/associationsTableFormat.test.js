import { describe, it, expect } from "vitest";
import { visibleColumns, SIFTER_TABLE_COLUMNS } from "../../utils/sifter/associationsTableFormat.js";
import { decorateAssociationRows } from "../../utils/sifter/decorateRows.js";

const ROW = { chromosome: "10", position: 114758349, reference: "C", alt: "T",
              pValue: 1e-9, beta: 0.4 };

describe("SIFTER_TABLE_COLUMNS", () => {
  it("takes its order from upstream's top rows, minus Ancestry", () => {
    const fields = SIFTER_TABLE_COLUMNS.map((c) => c.field);
    expect(fields[0]).toBe("Variant ID");
    expect(fields).toContain("P-Value");
    expect(fields).not.toContain("Ancestry");
  });
});

describe("visibleColumns", () => {
  it("shows only columns with data present", () => {
    const fields = visibleColumns(decorateAssociationRows([ROW])).map((c) => c.field);
    expect(fields).toContain("P-Value");
    expect(fields).toContain("Beta");
    // demo dataset col_map has no se/rsid, so these must be omitted, not blank
    expect(fields).not.toContain("Standard Error");
    expect(fields).not.toContain("rsID");
    expect(fields).not.toContain("Z Score");
  });

  it("shows stdErr and zScore once the data carries them", () => {
    const fields = visibleColumns(decorateAssociationRows([{ ...ROW, stdErr: 0.05, zScore: 8 }]))
      .map((c) => c.field);
    expect(fields).toContain("Standard Error");
    expect(fields).toContain("Z Score");
  });

  // Forward compatibility with the deferred VEP join: no code change needed.
  it("shows MAF and Consequence automatically when VEP fields appear", () => {
    const fields = visibleColumns(decorateAssociationRows([{ ...ROW, maf: 0.2, consequence: "missense" }]))
      .map((c) => c.field);
    expect(fields).toContain("MAF");
    expect(fields).toContain("Consequence");
  });

  it("treats a column of all-null values as absent", () => {
    const fields = visibleColumns(decorateAssociationRows([{ ...ROW, stdErr: null }])).map((c) => c.field);
    expect(fields).not.toContain("Standard Error");
  });
});
