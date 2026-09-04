import { describe, it, expect } from "vitest";
import { statusTag, hasFailed } from "../../utils/credibleSets/statusTag.js";

describe("statusTag", () => {
  it("maps every derived status to a tag", () => {
    expect(statusTag("pending").severity).toBe("secondary");
    expect(statusTag("indexing").severity).toBe("warn");
    expect(statusTag("indexing").icon).toContain("pi-spin");
    expect(statusTag("indexed").severity).toBe("success");
    expect(statusTag("failed").severity).toBe("danger");
  });
  it("treats an unknown status as pending rather than crashing the row", () => {
    expect(statusTag(undefined)).toEqual(statusTag("pending"));
  });
});

describe("hasFailed", () => {
  it("is true when any attached set failed", () => {
    expect(hasFailed([{ status: "indexed" }, { status: "failed" }])).toBe(true);
    expect(hasFailed([{ status: "indexed" }])).toBe(false);
    expect(hasFailed(undefined)).toBe(false);
  });
});
