// Which /api/download `result_type` serves each results-page tab. A tab with
// no entry has no download: this used to fall back to SLDSC, which disabled
// "Download FALCON Results" on FALCON-only datasets and, where SLDSC had also
// run, downloaded the SLDSC table under the FALCON label.
const RESULT_TYPES = {
    sldsc: "ldsc",
    magma: "magma",
    pigean: "pigean",
    falcon: "falcon",
};

export function downloadResultType(tab) {
    return RESULT_TYPES[tab] ?? null;
}
