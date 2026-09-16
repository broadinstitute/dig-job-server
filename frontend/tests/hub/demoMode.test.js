import { describe, it, expect } from "vitest";
import { isHubDemo } from "../../utils/hub/demoMode.js";

describe("isHubDemo", () => {
    it("is on for ?mode=demo", () => {
        expect(isHubDemo({ mode: "demo" })).toBe(true);
    });

    it("is off for other values, other keys, and no query", () => {
        expect(isHubDemo({ mode: "Demo" })).toBe(false);
        expect(isHubDemo({ mode: "live" })).toBe(false);
        expect(isHubDemo({ demo: "true" })).toBe(false);
        expect(isHubDemo({})).toBe(false);
        expect(isHubDemo(undefined)).toBe(false);
    });

    // A repeated ?mode=demo&mode=demo arrives as an array; treat as off rather
    // than guessing.
    it("is off for a repeated param", () => {
        expect(isHubDemo({ mode: ["demo", "demo"] })).toBe(false);
    });
});
