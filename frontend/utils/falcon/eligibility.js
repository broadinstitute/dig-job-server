// Which datasets FALCON can be offered for.
//
// This mirrors ONE of the two checks in falcon_prep/cli.py. Keep it that way:
// the backend is the authority, and this exists only so the UI does not offer a
// run that is certain to be declined.
//
// Ancestry is decidable here. FALCON's LD reference is EUR-only and LD
// structure is ancestry-specific, so cli.py rejects anything else outright
// (exit 10) before it opens the upload.
//
// Genome build is NOT decidable here, and deliberately isn't checked. GRCh37 is
// always fine. GRCh38 is fine too *if* the file carries rsIDs — FALCON joins LD
// and S2G by rsID, which is build-independent, so a GRCh38 file with an rsID
// column needs no lifting. Whether that column exists can only be known by
// reading the file, which is the converter's job. Gating on build here would
// hide supported GRCh38 datasets; letting them through costs a job that exits
// 10 with an explanation, which is the better failure.

export const SUPPORTED_ANCESTRY = "EUR";

/**
 * @param {{ancestry?: string}} dataset - a row from GET /datasets
 * @returns {{eligible: boolean, reason: string}} `reason` is empty when
 *   eligible, and is user-facing text otherwise.
 */
export function falconEligibility(dataset) {
    const ancestry = dataset?.ancestry;

    // An unset ancestry is not a rejection we can justify to the user, and the
    // converter re-checks anyway. Offer it and let the job decide.
    if (!ancestry) {
        return { eligible: true, reason: "" };
    }

    if (ancestry !== SUPPORTED_ANCESTRY) {
        return {
            eligible: false,
            reason:
                `FALCON supports ${SUPPORTED_ANCESTRY} datasets only — its LD ` +
                `reference is ${SUPPORTED_ANCESTRY} and LD structure is ` +
                `ancestry-specific. This dataset is ${ancestry}.`,
        };
    }

    return { eligible: true, reason: "" };
}
