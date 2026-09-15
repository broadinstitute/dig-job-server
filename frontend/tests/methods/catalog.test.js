import { describe, it, expect } from "vitest";
import { METHODS, getMethod, methodPath } from "../../utils/methods/catalog.js";

// PrimeVue 4 Tag severities. An unknown severity renders unstyled, which is
// easy to miss visually.
const TAG_SEVERITIES = [
    "primary",
    "secondary",
    "success",
    "info",
    "warn",
    "danger",
    "contrast",
];

describe("METHODS catalog", () => {
    it("lists the methods in the order the landing page shows them", () => {
        expect(METHODS.map((m) => m.slug)).toEqual([
            "sldsc",
            "magma",
            "cojo",
            "pigean",
            "falcon",
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
            expect(m.icon).toMatch(/^pi pi-/);
            expect(typeof m.iconWrapClass).toBe("string");
            expect(typeof m.iconClass).toBe("string");
            expect(Array.isArray(m.tags)).toBe(true);
            expect(typeof m.implemented).toBe("boolean");
            for (const tag of m.tags) {
                expect(typeof tag.value).toBe("string");
                expect(TAG_SEVERITIES).toContain(tag.severity);
            }
        }
    });

    // COJO has no workflow in the app yet; the card must say so.
    it("marks COJO as not implemented", () => {
        expect(getMethod("cojo").implemented).toBe(false);
    });

    it("marks the methods with a results tab as implemented", () => {
        for (const slug of ["sldsc", "magma", "pigean", "falcon"]) {
            expect(getMethod(slug).implemented).toBe(true);
        }
    });
});

describe("getMethod", () => {
    it("returns the entry for a known slug", () => {
        expect(getMethod("sldsc").title).toBe("SLDSC");
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
