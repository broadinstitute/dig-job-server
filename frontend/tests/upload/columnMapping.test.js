import { describe, it, expect } from "vitest";
import { isOptionDisabled, resetMapping, withField } from "../../utils/upload/columnMapping.js";

describe("isOptionDisabled", () => {
  const selected = { CHR: "chromosome", POS: "position", X: null };
  it("disables a field already claimed by another column", () => {
    expect(isOptionDisabled(selected, "chromosome", "POS")).toBe(true);
  });
  it("keeps a column's own current choice enabled so it can be re-picked or cleared", () => {
    expect(isOptionDisabled(selected, "chromosome", "CHR")).toBe(false);
  });
  it("leaves unclaimed fields enabled", () => {
    expect(isOptionDisabled(selected, "alt", "X")).toBe(false);
  });
});

describe("resetMapping / withField", () => {
  it("resets every column to null", () => {
    expect(resetMapping(["A", "B"])).toEqual({ A: null, B: null });
  });
  it("returns a new object with one column changed, coercing undefined to null", () => {
    const before = { A: "alt", B: null };
    const after = withField(before, "B", "beta");
    expect(after).toEqual({ A: "alt", B: "beta" });
    expect(before).toEqual({ A: "alt", B: null });
    expect(withField(before, "A", undefined)).toEqual({ A: null, B: null });
  });
});
