import { describe, it, expect } from "vitest";
import { FilterMatchMode, FilterService } from "@primevue/core/api";
import {
  visibleColumns,
  SIFTER_TABLE_COLUMNS,
  buildFilterModel,
  NUMERIC_FILTER_FIELDS,
} from "../../utils/sifter/associationsTableFormat.js";
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

describe("buildFilterModel", () => {
  it("builds one filter entry per visible column, in lockstep with visibleColumns", () => {
    const rows = decorateAssociationRows([ROW]);
    const model = buildFilterModel(rows);
    const columnFields = visibleColumns(rows).map((c) => c.field);
    expect(Object.keys(model).sort()).toEqual([...columnFields].sort());
  });

  // Mirrors visibleColumns' own field-presence tests (spec §5.1): the filter
  // set is driven by the same field-presence check as the column set, so a
  // Consequence filter can only appear once the deferred VEP join emits it.
  it("shows a Consequence filter only once rows carry consequence", () => {
    const withoutConsequence = buildFilterModel(decorateAssociationRows([ROW]));
    expect(withoutConsequence).not.toHaveProperty("Consequence");

    const withConsequence = buildFilterModel(
      decorateAssociationRows([{ ...ROW, consequence: "missense" }]),
    );
    expect(withConsequence).toHaveProperty("Consequence");
    expect(withConsequence.Consequence.matchMode).toBe(FilterMatchMode.CONTAINS);
  });

  it("assigns CONTAINS to text columns and a relational matchMode to numeric columns", () => {
    const rows = decorateAssociationRows([
      { ...ROW, stdErr: 0.05, zScore: 8, maf: 0.2, dbSNP: "rs1" },
    ]);
    const model = buildFilterModel(rows);

    for (const field of ["Variant ID", "rsID", "Ref/Alt"]) {
      expect(model[field].matchMode).toBe(FilterMatchMode.CONTAINS);
      expect(model[field].value).toBeNull();
    }

    expect(model["P-Value"].matchMode).toBe(FilterMatchMode.LESS_THAN_OR_EQUAL_TO);
    expect(model.Beta.matchMode).toBe(FilterMatchMode.GREATER_THAN_OR_EQUAL_TO);
    expect(model.MAF.matchMode).toBe(FilterMatchMode.GREATER_THAN_OR_EQUAL_TO);
    expect(model["Standard Error"].matchMode).toBe(FilterMatchMode.LESS_THAN_OR_EQUAL_TO);
    expect(model["Z Score"].matchMode).toBe(FilterMatchMode.GREATER_THAN_OR_EQUAL_TO);

    // Every numeric field name is classified statically, not by inspecting a
    // sampled row's typeof value (see NUMERIC_FILTER_FIELDS doc comment).
    for (const field of NUMERIC_FILTER_FIELDS) {
      if (field in model) expect(model[field].value).toBeNull();
    }
  });

  it("critical: a numeric filter still matches a decorated exact-zero STRING value", () => {
    // decorateRows.js coerces an exact 0 to the string "0" before assigning
    // (matching upstream's dataConvert "raw" rule) — confirm the matchMode we
    // assign doesn't silently drop that row via a typeof-based comparison.
    const [row] = decorateAssociationRows([{ ...ROW, beta: 0 }]);
    expect(row.Beta).toBe("0"); // pinning the upstream coercion this guards against
    expect(typeof row.Beta).toBe("string");

    const model = buildFilterModel([row]);
    const matchMode = model.Beta.matchMode; // GREATER_THAN_OR_EQUAL_TO
    const matches = FilterService.filters[matchMode](row.Beta, 0);
    expect(matches).toBe(true);
  });
});
