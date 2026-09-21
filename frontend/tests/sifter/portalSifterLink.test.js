import { describe, it, expect } from "vitest";
import { buildPortalSifterUrl } from "../../utils/sifter/portalSifterLink.js";

const PORTAL = "https://dev.hugeamp.org/research.html?pageid=kp_variant_sifter_26&project=gwas-ce";

describe("buildPortalSifterUrl", () => {
  it("appends token to the configured URL and preserves existing params", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c" }));
    expect(url.searchParams.get("pageid")).toBe("kp_variant_sifter_26");
    expect(url.searchParams.get("project")).toBe("gwas-ce");
    expect(url.searchParams.get("token")).toBe("3e9b2a5c");
  });

  it("appends region after token when given", () => {
    const out = buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c", region: "4:72500000-72800000" });
    const url = new URL(out);
    expect(url.searchParams.get("token")).toBe("3e9b2a5c");
    expect(url.searchParams.get("region")).toBe("4:72500000-72800000");
    // token appears before region in the query string
    expect(out.indexOf("token=")).toBeLessThan(out.indexOf("region="));
  });

  it("does not append region when not given", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c" }));
    expect(url.searchParams.has("region")).toBe(false);
  });

  it("appends ancestry after token when given", () => {
    const out = buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c", ancestry: "Mixed" });
    const url = new URL(out);
    expect(url.searchParams.get("token")).toBe("3e9b2a5c");
    expect(url.searchParams.get("ancestry")).toBe("Mixed");
    // token appears before ancestry in the query string
    expect(out.indexOf("token=")).toBeLessThan(out.indexOf("ancestry="));
  });

  it("does not append ancestry when not given", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c" }));
    expect(url.searchParams.has("ancestry")).toBe(false);
  });

  it("does not append ancestry when it is an empty string", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "3e9b2a5c", ancestry: "" }));
    expect(url.searchParams.has("ancestry")).toBe(false);
  });

  it("URL-encodes a token containing characters needing escaping", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "a b/c" }));
    expect(url.searchParams.get("token")).toBe("a b/c");
    expect(url.toString()).toContain("token=a+b%2Fc");
  });

  it("trims whitespace from the token", () => {
    const url = new URL(buildPortalSifterUrl(PORTAL, { token: "  3e9b2a5c  " }));
    expect(url.searchParams.get("token")).toBe("3e9b2a5c");
  });

  it("throws TypeError on an empty token", () => {
    expect(() => buildPortalSifterUrl(PORTAL, { token: "" })).toThrow(TypeError);
  });

  it("throws TypeError on a missing token", () => {
    expect(() => buildPortalSifterUrl(PORTAL, {})).toThrow(TypeError);
  });

  it("throws TypeError on a whitespace-only token", () => {
    expect(() => buildPortalSifterUrl(PORTAL, { token: "   " })).toThrow(TypeError);
  });

  it("throws TypeError on a garbage portal URL", () => {
    expect(() => buildPortalSifterUrl("not a url", { token: "3e9b2a5c" })).toThrow(TypeError);
  });

  it("throws TypeError on an empty portal URL", () => {
    expect(() => buildPortalSifterUrl("", { token: "3e9b2a5c" })).toThrow(TypeError);
  });
});
