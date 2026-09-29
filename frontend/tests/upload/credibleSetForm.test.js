import { describe, it, expect } from "vitest";
import {
  canValidate,
  isReady,
  buildFormData,
  summarizeReport,
  describeUploadError,
  credibleSetSlug,
} from "../../utils/upload/credibleSetForm.js";

const FULL_MAP = {
  chromosome: "CHR", position: "POS", reference: "A2", alt: "A1",
  credibleSetId: "CS", posteriorProbability: "PIP",
};
const file = { name: "cs.tsv" };

class FakeFormData {
  constructor() { this.entries = []; }
  append(k, v, name) { this.entries.push([k, v, name]); }
}

describe("canValidate / isReady", () => {
  it("needs a name, a file and every required field", () => {
    expect(canValidate({ name: "x", file, colMap: FULL_MAP })).toBe(true);
    expect(canValidate({ name: "  ", file, colMap: FULL_MAP })).toBe(false);
    expect(canValidate({ name: "x", file: null, colMap: FULL_MAP })).toBe(false);
    expect(canValidate({ name: "x", file, colMap: { ...FULL_MAP, alt: undefined } })).toBe(false);
  });
  it("is ready only with a passing report", () => {
    expect(isReady({ name: "x", file, colMap: FULL_MAP, report: { ok: true } })).toBe(true);
    expect(isReady({ name: "x", file, colMap: FULL_MAP, report: { ok: false } })).toBe(false);
    expect(isReady({ name: "x", file, colMap: FULL_MAP, report: null })).toBe(false);
    expect(isReady(null)).toBe(false);
  });
});

describe("buildFormData", () => {
  it("sends the file, trimmed name, JSON col_map and the separator", () => {
    const fd = buildFormData({ name: " SuSiE v1 ", file, separator: "\t", colMap: FULL_MAP }, FakeFormData);
    expect(fd.entries).toEqual([
      ["file", file, "cs.tsv"],
      ["name", "SuSiE v1", undefined],
      ["col_map", JSON.stringify(FULL_MAP), undefined],
      ["separator", "\t", undefined],
    ]);
  });
  it("omits the separator when unknown so the server infers it", () => {
    const fd = buildFormData({ name: "x", file, separator: null, colMap: FULL_MAP }, FakeFormData);
    expect(fd.entries.map((e) => e[0])).toEqual(["file", "name", "col_map"]);
  });
});

describe("summarizeReport", () => {
  it("reads 'Valid · N sets · M variants'", () => {
    expect(summarizeReport({ ok: true, set_count: 14, row_count: 312 })).toBe("Valid · 14 sets · 312 variants");
    expect(summarizeReport({ ok: true, set_count: 1, row_count: 1 })).toBe("Valid · 1 set · 1 variant");
  });
});

describe("describeUploadError", () => {
  it("uses a string detail as-is", () => {
    expect(describeUploadError({ response: { data: { detail: "A credible set named 'x' already exists" } } }))
      .toBe("A credible set named 'x' already exists");
  });
  it("uses the first error of a validation report detail", () => {
    const error = { response: { data: { detail: { ok: false, errors: [{ line: 3, message: "bad position" }] } } } };
    expect(describeUploadError(error)).toBe("line 3: bad position");
  });
  it("falls back to the error message", () => {
    expect(describeUploadError(new Error("Network Error"))).toBe("Network Error");
  });
});

describe("credibleSetSlug", () => {
  // Same cases as tests/test_credible_sets_pure.py::test_slugify: the form
  // previews the prefix the server puts on every uploaded credibleSetId, so the
  // two must agree.
  it.each([
    ["SuSiE v1", "susie-v1"],
    ["  FINEMAP  ", "finemap"],
    ["a__b--c", "a-b-c"],
    ["-leading and trailing-", "leading-and-trailing"],
    ["MixedCASE 42", "mixedcase-42"],
  ])("slugs %j as %j, like the server", (name, slug) => {
    expect(credibleSetSlug(name)).toBe(slug);
  });
  it("is empty for a name with no letter or digit, which the server rejects", () => {
    expect(credibleSetSlug("---")).toBe("");
    expect(credibleSetSlug("")).toBe("");
    expect(credibleSetSlug(undefined)).toBe("");
  });
});
