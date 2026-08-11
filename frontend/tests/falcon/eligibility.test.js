import { describe, it, expect } from "vitest";
import {
    falconEligibility,
    SUPPORTED_ANCESTRY,
} from "../../utils/falcon/eligibility.js";

describe("ancestry gate", () => {
    it("offers FALCON for the ancestry its LD reference covers", () => {
        expect(falconEligibility({ ancestry: "EUR" }).eligible).toBe(true);
    });

    it("declines every other ancestry", () => {
        // LD structure is ancestry-specific; running EUR LD against these would
        // produce numbers rather than an error, which is the dangerous case.
        for (const a of ["AFR", "AMR", "EAS", "SAS", "MID"]) {
            expect(falconEligibility({ ancestry: a }).eligible).toBe(false);
        }
    });

    it("names the dataset's actual ancestry in the reason", () => {
        // "Not supported" alone sends people to a support channel; naming the
        // mismatch lets them see why without asking.
        const { reason } = falconEligibility({ ancestry: "EAS" });
        expect(reason).toContain("EAS");
        expect(reason).toContain(SUPPORTED_ANCESTRY);
    });

    it("gives no reason when it is eligible", () => {
        expect(falconEligibility({ ancestry: "EUR" }).reason).toBe("");
    });
});

describe("what this gate deliberately does not decide", () => {
    it("allows GRCh38, which is supported when the file has rsIDs", () => {
        // rsIDs are build-independent and FALCON joins on them, so a GRCh38
        // file with an rsID column needs no lifting. Only the converter can
        // see whether that column exists.
        const ds = { ancestry: "EUR", genome_build: "GRCh38" };
        expect(falconEligibility(ds).eligible).toBe(true);
    });

    it("allows GRCh37", () => {
        const ds = { ancestry: "EUR", genome_build: "GRCh37" };
        expect(falconEligibility(ds).eligible).toBe(true);
    });

    it("ignores genome_build entirely, whatever it says", () => {
        // Guards against someone "helpfully" adding a build check here later:
        // it would hide the supported GRCh38-with-rsID datasets.
        for (const b of ["GRCh38", "GRCh37", "hg19", "hg38", "", undefined]) {
            expect(
                falconEligibility({ ancestry: "EUR", genome_build: b }).eligible,
            ).toBe(true);
        }
    });
});

describe("missing or malformed rows", () => {
    it("offers the run when ancestry is unset rather than hiding it", () => {
        // The converter re-checks. Hiding the action would leave the user with
        // no way to find out why.
        expect(falconEligibility({}).eligible).toBe(true);
        expect(falconEligibility({ ancestry: "" }).eligible).toBe(true);
    });

    it("does not throw on a null or undefined row", () => {
        expect(() => falconEligibility(null)).not.toThrow();
        expect(() => falconEligibility(undefined)).not.toThrow();
        expect(falconEligibility(null).eligible).toBe(true);
    });

    it("is case-sensitive, matching the backend's comparison", () => {
        // cli.py does `meta.ancestry != "EUR"` with no normalisation. If that
        // ever loosens, this test should fail and be updated in step with it --
        // a UI that accepts "eur" while the backend rejects it is worse than
        // one that declines early.
        expect(falconEligibility({ ancestry: "eur" }).eligible).toBe(false);
    });
});
