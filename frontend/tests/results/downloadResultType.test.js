import { describe, it, expect } from "vitest";
import { downloadResultType } from "../../utils/results/downloadResultType.js";

describe("downloadResultType", () => {
  it.each([
    ["sldsc", "ldsc"],
    ["magma", "magma"],
    ["pigean", "pigean"],
    ["falcon", "falcon"],
  ])("maps the %s tab to result_type=%s", (tab, resultType) => {
    expect(downloadResultType(tab)).toBe(resultType);
  });

  it("has no download for an unknown tab rather than falling back to SLDSC", () => {
    // The fallback once served the SLDSC table under "Download FALCON Results".
    expect(downloadResultType("annot-sldsc")).toBeNull();
    expect(downloadResultType(undefined)).toBeNull();
  });
});
