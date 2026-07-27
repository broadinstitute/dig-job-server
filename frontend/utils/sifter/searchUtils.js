// Ported from dig-dug-portal@5619cbfe1
//   src/components/researchPortal/customComponents/kpVariantSifter/variantSifterSearchUtils.js
// Region parsing/expansion and gene-symbol lookup only. Upstream's phenotype
// and ancestry helpers (VARIANT_SIFTER_ANCESTRY_OPTIONS, ancestryLabel,
// normalizeAncestryCode, parseSubAncestriesParam, formatSubAncestriesParam,
// filterPhenotypes, formatSearchSessionLabel) are omitted: GWAS-CE has no
// phenotype picker and takes ancestry from dataset metadata.
//
// Upstream's `BIO_INDEX_HOST`/`match` (from @/utils/bioIndexUtils) aren't
// vendored here; gene lookups hit KP_BIOINDEX_HOST directly via an injectable
// fetchImpl instead so this module stays testable without a live network call.
import variantUtils from "./_portal/variantUtils.js";

// Public KP bioindex. Region- and symbol-keyed reference data only — no
// GWAS-CE data is ever sent here. Verified CORS-open (ACAO: *) 2026-07-27.
export const KP_BIOINDEX_HOST = "https://bioindex.hugeamp.org";

export const REGION_EXPAND_OPTIONS = [
    { value: null, label: "Gene / variant bounds only" },
    { value: 50000, label: "± 50 kb" },
    { value: 100000, label: "± 100 kb" },
    { value: 150000, label: "± 150 kb" },
];

const REGION_RANGE_REGEXP =
    /^(?:chr)?(1\d?|2[0-2]?|[3-9]|x|y|xy|mt?)[:_](\d+)\s*-\s*(\d+)$/i;

/** Single genomic coordinate, e.g. `chr1:100000` or `1:100000`. */
const REGION_LOCATION_REGEXP =
    /^(?:chr)?(1\d?|2[0-2]?|[3-9]|x|y|xy|mt?)[:_](\d+)$/i;

function isRegionRangeQuery(query) {
    return REGION_RANGE_REGEXP.test(String(query || "").trim().replace(/,/g, ""));
}

function isRegionLocationQuery(query) {
    return REGION_LOCATION_REGEXP.test(String(query || "").trim().replace(/,/g, ""));
}

function isVariantQuery(query) {
    const trimmed = query.trim();
    return (
        /^rs\d+/i.test(trimmed) ||
        variantUtils.parseVariant(trimmed) != null ||
        (/[:_]/.test(trimmed) &&
            /\d/.test(trimmed) &&
            !isRegionRangeQuery(trimmed) &&
            !isRegionLocationQuery(trimmed))
    );
}

/** True when the locus field should offer gene symbol autocomplete. */
export function isGeneLookupQuery(query) {
    const trimmed = String(query || "").trim();
    if (trimmed.length < 2) {
        return false;
    }
    return (
        !isRegionRangeQuery(trimmed) &&
        !isRegionLocationQuery(trimmed) &&
        !isVariantQuery(trimmed)
    );
}

/** Gene symbol autocomplete via the KP bioindex `gene` index (symbol-keyed). */
export async function lookupGeneMatches(query, limit = 10, host = KP_BIOINDEX_HOST, fetchImpl = fetch) {
    const trimmed = String(query || "").trim();
    if (!isGeneLookupQuery(trimmed)) {
        return [];
    }

    try {
        const response = await fetchImpl(
            `${host}/api/bio/query/gene?q=${encodeURIComponent(trimmed)}&fmt=row&limit=${limit}`
        );
        if (!response.ok) {
            return [];
        }
        const json = await response.json();
        return Array.isArray(json?.data) ? json.data : [];
    } catch (error) {
        console.warn("Variant Sifter gene lookup failed", error);
        return [];
    }
}

export function applyRegionExpand(region, expandBp) {
    if (!region || !expandBp) {
        return region;
    }

    const half = Math.floor(expandBp / 2);
    return {
        ...region,
        start: Math.max(0, region.start - half),
        end: region.end + half,
    };
}

export function regionAroundPosition(chr, position, expandBp) {
    const half = expandBp ? Math.floor(expandBp / 2) : 50000;
    return {
        chr,
        start: Math.max(0, position - half),
        end: position + half,
    };
}

function parseRegionRange(query) {
    const match = query.trim().replace(/,/g, "").match(REGION_RANGE_REGEXP);
    if (!match) {
        return null;
    }

    const start = parseInt(match[2], 10);
    const end = parseInt(match[3], 10);
    if (Number.isNaN(start) || Number.isNaN(end) || end <= start) {
        return null;
    }

    return {
        chr: match[1],
        start,
        end,
    };
}

function parseRegionLocation(query) {
    const match = query.trim().replace(/,/g, "").match(REGION_LOCATION_REGEXP);
    if (!match) {
        return null;
    }

    const position = parseInt(match[2], 10);
    if (Number.isNaN(position)) {
        return null;
    }

    return {
        chr: match[1],
        position,
    };
}

/**
 * Resolve a gene symbol, chr:start-end range, or chr:position location into a
 * `{ chr, start, end }` region; optional expandBp widens the result further.
 *
 * REWRITTEN (not ported): Upstream delegates region resolution to an unvendored
 * `regionUtils.parseRegion` collaborator. This version reimplements the same
 * resolution order (range → location → gene lookup) directly against an injectable
 * `fetchImpl`, avoiding the need to vendor the upstream's `regionUtils` module.
 */
export async function resolveGeneOrVariantToRegion(
    query,
    { expandBp = null, host = KP_BIOINDEX_HOST, fetchImpl = fetch } = {}
) {
    const trimmed = String(query || "").trim();
    if (!trimmed) {
        return null;
    }

    if (isRegionRangeQuery(trimmed)) {
        const region = parseRegionRange(trimmed);
        return applyRegionExpand(region, expandBp);
    }

    if (isRegionLocationQuery(trimmed)) {
        const location = parseRegionLocation(trimmed);
        if (!location) {
            return null;
        }
        // Treat a point like a variant locus: expand around it (default ±50 kb).
        return regionAroundPosition(location.chr, location.position, expandBp || 100000);
    }

    const response = await fetchImpl(
        `${host}/api/bio/query/gene?q=${encodeURIComponent(trimmed)}&fmt=row&limit=1`
    );
    if (!response.ok) {
        throw new Error(`Gene lookup failed (HTTP ${response.status})`);
    }
    const json = await response.json();
    const row = json?.data?.[0];
    if (!row) {
        throw new Error(`No gene or region found for "${query}"`);
    }

    return applyRegionExpand({ chr: row.chromosome, start: row.start, end: row.end }, expandBp);
}

export function formatRegion(region) {
    if (!region) {
        return "";
    }
    return `${region.chr}:${region.start}-${region.end}`;
}

export function parseRegionParam(regionParam) {
    if (!regionParam) {
        return null;
    }

    const text = String(regionParam).trim();
    if (isRegionRangeQuery(text)) {
        return parseRegionRange(text);
    }

    if (isRegionLocationQuery(text)) {
        const location = parseRegionLocation(text);
        if (!location) {
            return null;
        }
        const region = regionAroundPosition(location.chr, location.position, 100000);
        return {
            ...region,
            sourceQuery: text,
            sourceType: "location",
        };
    }

    const colonSplit = text.split(":");
    if (colonSplit.length !== 2) {
        return null;
    }

    const range = colonSplit[1].split("-");
    if (range.length !== 2) {
        return null;
    }

    const start = parseInt(range[0], 10);
    const end = parseInt(range[1], 10);
    if (Number.isNaN(start) || Number.isNaN(end)) {
        return null;
    }

    return {
        chr: colonSplit[0].replace(/^chr/i, ""),
        start,
        end,
        sourceQuery: text,
        sourceType: "region",
    };
}
