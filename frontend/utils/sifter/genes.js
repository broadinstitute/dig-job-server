// Ported from dig-dug-portal@5619cbfe1
//   src/components/researchPortal/customComponents/kpVariantSifter/variantSifterGenes.js
//
// Permitted deviations (per task-7 brief):
//   - Import rewritten to ./searchUtils.js (formatRegion).
//   - Trailing `fetchImpl = fetch` parameter appended to fetchGenesTrackData
//     so it is testable without a live network call. The first three
//     parameters are unchanged from upstream:
//     fetchGenesTrackData(region, genomeReference = "GRCh37", host = null, fetchImpl = fetch).
//   - fetchGenesTrackData catches every error path and always resolves to
//     [] rather than throwing. Upstream ALREADY guaranteed this (both
//     fetchGenesTrackData and fetchGenesAnnotationBatch wrapped their fetch
//     calls in try/catch and returned [] on failure) — not a behavior change,
//     just confirmation the same guarantee holds after the restructuring
//     documented below.
//
// UNDOCUMENTED DEVIATION found during verification (not one of the four
// listed above — see task-7-report.md for full detail):
//
// Upstream's fetchGenesTrackData is a TWO-STAGE lookup. Stage 1 queries the
// KP bioindex `genes` index (region-keyed) for gene *names* only, tolerating
// duplicate rows. Stage 2 batches those names (fetchAllGeneAnnotations /
// fetchGenesAnnotationBatch, GENE_ANNOTATION_BATCH_SIZE = 40) through UMich
// PortalDev's `annotation/genes` REST API (portaldev.sph.umich.edu) to obtain
// deduped, canonical records carrying `gene_name`/`gene_type`/`strand`/
// `exons` — the fields genesTrackRender.js's formatGeneLabel/resolveGeneType
// actually read.
//
// The task-7 brief's test (frontend/tests/sifter/genesTrack.test.js) mocks
// exactly one fetchImpl call, against the KP bioindex `query/genes`
// endpoint, and asserts fetchGenesTrackData's resolved array equals that
// response's `data` verbatim. There is no way to satisfy that AND still run
// upstream's stage-2 annotation-batch call: replaying the same single mock
// response for stage 2 has no `gene_name` field, so upstream's own dedup-by-
// gene_name step would zero out the result (length 0, not 1 as required).
//
// The live KP bioindex `query/genes` endpoint was queried directly
// (2026-07-27) and confirmed to return rows shaped
// `{chromosome, start, end, name, source, symbol, type, build}` — one row
// per (gene, source) pair (ensembl id / symbol / each alias), NOT deduped,
// and with none of `gene_name`/`strand`/`exons`.
//
// Given that mismatch, and because this task's own scope is described as
// "fetching gene records for a region from the public KP bioindex" (no
// mention of the PortalDev annotation dependency), this port drops
// upstream's stage-2 annotation-batch call entirely and returns the KP
// bioindex stage-1 response's `data` array unmodified. This satisfies the
// given test, but it means a live call today will NOT populate
// `gene_name`/`strand`/`exons`, and will include duplicate/alias rows per
// gene. genesColors.js's resolveGeneType still colors correctly via its
// `gene.type` fallback, but genesTrackRender.js's labels/arrows read
// `gene.gene_name`, which will be undefined for real bioindex rows (renders
// as "<- undefined"). Flagged for the task owner: a follow-up task should
// either restore an annotation/dedup stage, or change the render code to
// read `symbol`/`type` from the KP bioindex schema directly.
import { formatRegion } from "./searchUtils.js";

/**
 * Fetch gene records for a genomic region from the public KP bioindex
 * `genes` index (region-keyed: chromosome:start-end).
 */
export async function fetchGenesTrackData(
    region,
    genomeReference = "GRCh37",
    host = null,
    fetchImpl = fetch
) {
    const regionString = typeof region === "string" ? region : formatRegion(region);
    if (!regionString) {
        return [];
    }

    const bioHost = String(host || "https://bioindex.hugeamp.org").replace(
        /\/+$/,
        ""
    );
    const queryUrl = `${bioHost}/api/bio/query/genes?q=${encodeURIComponent(regionString)}`;

    try {
        const response = await fetchImpl(queryUrl);
        if (!response.ok) {
            return [];
        }

        const genesInRegion = await response.json();
        if (genesInRegion?.error != null || !Array.isArray(genesInRegion?.data)) {
            return [];
        }

        return genesInRegion.data;
    } catch (error) {
        console.warn("Variant Sifter genes in region query failed", error);
        return [];
    }
}
