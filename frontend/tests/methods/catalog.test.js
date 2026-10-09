import { describe, it, expect } from "vitest";
import { METHODS, getMethod, methodPath } from "../../utils/methods/catalog.js";

describe("METHODS catalog", () => {
    it("lists the methods in the order the landing page shows them", () => {
        expect(METHODS.map((m) => m.slug)).toEqual([
            "sldsc",
            "magma",
            "pigean",
            "falcon",
            "variant-sifter",
        ]);
    });

    it("has unique slugs", () => {
        const slugs = METHODS.map((m) => m.slug);
        expect(new Set(slugs).size).toBe(slugs.length);
    });

    it("has every field MethodCard and /methods/[slug] read", () => {
        for (const m of METHODS) {
            expect(typeof m.title).toBe("string");
            expect(m.title.length).toBeGreaterThan(0);
            expect(typeof m.blurb).toBe("string");
            expect(m.blurb.length).toBeGreaterThan(0);
            expect(m.accent).toMatch(/^#[0-9a-f]{6}$/i);
            expect(m.fullName === null || typeof m.fullName === "string").toBe(
                true,
            );
            expect(typeof m.implemented).toBe("boolean");
        }
    });

    it("marks every method that runs from the Datasets page as implemented", () => {
        for (const slug of [
            "sldsc",
            "magma",
            "pigean",
            "falcon",
            "variant-sifter",
        ]) {
            expect(getMethod(slug).implemented).toBe(true);
        }
    });

    // Variant Sifter results open in the HuGeAMP portal, not in GWAS-CE.
    it("marks only Variant Sifter as external", () => {
        expect(METHODS.filter((m) => m.external).map((m) => m.slug)).toEqual([
            "variant-sifter",
        ]);
    });
});

describe("getMethod", () => {
    it("returns the entry for a known slug", () => {
        expect(getMethod("sldsc").title).toBe("S-LDSC");
    });

    it("returns undefined for an unknown slug", () => {
        expect(getMethod("nope")).toBeUndefined();
        expect(getMethod(undefined)).toBeUndefined();
    });
});

describe("methodPath", () => {
    it("builds the /methods route", () => {
        expect(methodPath("sldsc")).toBe("/methods/sldsc");
    });
});
