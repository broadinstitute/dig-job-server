// Ported from dig-dug-portal@5619cbfe1
//   src/components/researchPortal/customComponents/kpVariantSifter/variantSifterGenes.js
//
// Permitted deviations (per task-7 brief):
//   - Import rewritten to ./searchUtils.js (formatRegion).
//   - Trailing `fetchImpl = fetch` parameter appended to fetchGenesTrackData
//     so it is testable without a live network call. The first three
//     parameters are unchanged from upstream:
//     fetchGenesTrackData(region, genomeReference = "GRCh37", host = null, fetchImpl = fetch).
//     The same fetchImpl is threaded through fetchAllGeneAnnotations into
//     fetchGenesAnnotationBatch so both fetch stages (KP bioindex region
//     query, PortalDev annotation batch) are mockable in tests.
//   - fetchGenesTrackData catches every error path and always resolves to
//     [] rather than throwing. Upstream ALREADY guaranteed this (both
//     fetchGenesTrackData and fetchGenesAnnotationBatch wrapped their fetch
//     calls in try/catch and returned [] on failure) — not a behavior change,
//     just confirmation the same guarantee holds after the port.
//
// Everything else — including the two-stage fetch (KP bioindex `genes` index
// for gene names, then PortalDev `annotation/genes` batched by name for the
// deduped/annotated records), GENE_ANNOTATION_BATCH_SIZE = 40, and the
// .then(resp => resp.text()) + JSON.parse pattern (not .json()) — is a
// verbatim port. Dropping the annotation stage is NOT a permitted deviation:
// without it the track renders duplicate alias rows with no gene_name,
// strand, or exons.
import { formatRegion } from "./searchUtils.js";

const GENE_ANNOTATION_BATCH_SIZE = 40;

function resolveGenesAnnotationUrl(geneNames, genomeReference) {
    if (!geneNames.length) {
        return null;
    }
    const filter = `gene_name in ${geneNames.map((name) => `'${name}'`).join(",")}`;
    if (genomeReference === "GRCh38") {
        return `https://portaldev.sph.umich.edu/api/v1/annotation/genes/?filter=source in 1 and ${filter}`;
    }
    return `https://portaldev.sph.umich.edu/api/v1/annotation/genes/?filter=source in 3 and ${filter}`;
}

async function fetchGenesAnnotationBatch(geneNames, genomeReference, fetchImpl = fetch) {
    const url = resolveGenesAnnotationUrl(geneNames, genomeReference);
    if (!url) {
        return [];
    }

    try {
        const genesDataText = await fetchImpl(url).then((resp) => resp.text());
        const genesData = JSON.parse(genesDataText);

        if (genesData?.error != null || !Array.isArray(genesData?.data)) {
            return [];
        }

        return genesData.data;
    } catch (error) {
        console.warn("Variant Sifter gene annotation batch failed", error);
        return [];
    }
}

async function fetchAllGeneAnnotations(geneNames, genomeReference, fetchImpl = fetch) {
    const uniqueNames = [...new Set(geneNames.filter(Boolean))];
    if (!uniqueNames.length) {
        return [];
    }

    const batches = [];
    for (let index = 0; index < uniqueNames.length; index += GENE_ANNOTATION_BATCH_SIZE) {
        batches.push(uniqueNames.slice(index, index + GENE_ANNOTATION_BATCH_SIZE));
    }

    const batchResults = await Promise.all(
        batches.map((batch) => fetchGenesAnnotationBatch(batch, genomeReference, fetchImpl))
    );

    const genesByName = new Map();
    batchResults.flat().forEach((gene) => {
        const name = gene?.gene_name;
        if (name && !genesByName.has(name)) {
            genesByName.set(name, gene);
        }
    });

    return Array.from(genesByName.values()).sort(
        (left, right) => Number(left.start) - Number(right.start)
    );
}

/**
 * Fetch gene track annotation for a genomic region (full locus, not zoom window).
 * Annotation lookups are batched to avoid URL length limits on large loci.
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
        const genesText = await fetchImpl(queryUrl).then((resp) => resp.text());
        const genesInRegion = JSON.parse(genesText);

        if (genesInRegion?.error != null || !Array.isArray(genesInRegion?.data)) {
            return [];
        }

        const geneNames = genesInRegion.data.map((gene) => gene.name).filter(Boolean);
        return fetchAllGeneAnnotations(geneNames, genomeReference, fetchImpl);
    } catch (error) {
        console.warn("Variant Sifter genes in region query failed", error);
        return [];
    }
}
