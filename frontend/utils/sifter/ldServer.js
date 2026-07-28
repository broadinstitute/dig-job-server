// Ported from dig-dug-portal@5619cbfe1
//   src/components/researchPortal/customComponents/kpVariantSifter/variantSifterLdServer.js
//
// NOT VERBATIM. This file carries one deliberate GWAS-CE divergence, marked
// inline as "GWAS-CE DIVERGENCE (allele orientation)" in variantAliasKeys() and
// fetchLdScoreMapForRefRow(). Upstream consumes KP-warehouse varIds that are
// already canonicalised to the reference genome's REF/ALT, so allele order
// always agrees with the U-M LD server. GWAS-CE builds variant IDs from the
// "other"/"effect" allele columns of a user upload, which are oriented the
// other way for roughly half of datasets -- observed live: t2d-alex-test got
// zero LD colouring while the demo dataset was fine. Everything else here
// should still diff cleanly against upstream.
import variantUtils from "./_portal/variantUtils.js";

const LD_SERVER_BASE_URL = "https://portaldev.sph.umich.edu/ld/";

/**
 * KP ancestry codes → 1000G LD server population IDs.
 * Matches BYOR gem package "ld server".populations mapping.
 */
export const KP_ANCESTRY_LD_POPULATIONS = {
    Mixed: "ALL",
    EU: "EUR",
    EA: "EAS",
    SA: "SAS",
    AA: "AFR",
    HS: "AMR",
    SSAF: "AFR",
    ALL: "ALL",
    EUR: "EUR",
    EAS: "EAS",
    SAS: "SAS",
    AFR: "AFR",
    AMR: "AMR",
};

export const LD_SERVER_DEFAULTS = {
    baseUrl: LD_SERVER_BASE_URL.replace(/\/$/, ""),
    genomeBuild: "GRCh37",
    reference: "1000G",
    correlation: "rsquare",
    limit: 100000,
};

/**
 * Resolve the 1000G population for the U-M LD server from search ancestry.
 */
export function resolveLdPopulation(ancestry) {
    if (!ancestry || ancestry === "Mixed") {
        return KP_ANCESTRY_LD_POPULATIONS.Mixed;
    }
    return KP_ANCESTRY_LD_POPULATIONS[ancestry] || KP_ANCESTRY_LD_POPULATIONS.Mixed;
}

/**
 * LD server expects GEM-style variant IDs (chr:pos_ref/alt), not BioIndex varId
 * (chr:pos:ref:alt). See variantUtils.gaitVariant and ResearchRegionPlot.
 */
export function rowToLdVariant(row) {
    if (row?.["Variant ID"]) {
        return row["Variant ID"];
    }
    if (row?.varId) {
        return variantUtils.gaitVariant(row.varId);
    }
    return null;
}

function gemVariantToVarId(variantId) {
    const match = String(variantId).match(
        /^((?:\d+|X|Y|MT)):(\d+)_([^/]+)\/(.+)$/i
    );
    if (!match) {
        return variantId;
    }
    return `${match[1]}:${match[2]}:${match[3]}:${match[4]}`;
}

// GWAS-CE DIVERGENCE (allele orientation) -- see the file header.
// Upstream matches KP-warehouse varIds, already canonicalised to the reference
// genome's REF/ALT, so allele order always agrees with the LD server. GWAS-CE
// builds variant IDs from whatever "other"/"effect" allele columns the uploader
// supplied, and those are oriented the opposite way for roughly half of
// datasets. Emitting BOTH orientations makes partner matching order-agnostic.
// Two variants at one position with swapped alleles are the same variant, so
// the extra keys cannot collide with a genuinely different variant.
function variantAliasKeys(variant) {
    if (variant == null || variant === "") {
        return [];
    }

    const keys = new Set([String(variant), String(variant).toLowerCase()]);
    const asString = String(variant);

    // The two ID spellings are mutually exclusive: GEM has one colon, varId three.
    const parts =
        asString.match(/^((?:\d+|X|Y|MT)):(\d+)_([^/]+)\/(.+)$/i) ||
        asString.match(/^((?:\d+|X|Y|MT)):(\d+):([^:]+):(.+)$/i);
    if (parts) {
        const [, chr, pos, ref, alt] = parts;
        [[ref, alt], [alt, ref]].forEach(([a, b]) => {
            keys.add(`${chr}:${pos}:${a}:${b}`);
            keys.add(`${chr}:${pos}:${a}:${b}`.toLowerCase());
            keys.add(`${chr}:${pos}_${a}/${b}`);
            keys.add(`${chr}:${pos}_${a}/${b}`.toLowerCase());
        });
    }

    keys.add(gemVariantToVarId(asString));
    return Array.from(keys);
}

/**
 * Swap ref/alt in a GEM-style (chr:pos_ref/alt) variant id; null if unparseable.
 */
function flipVariantAlleles(variant) {
    const match = String(variant).match(/^((?:\d+|X|Y|MT)):(\d+)_([^/]+)\/(.+)$/i);
    if (!match) {
        return null;
    }
    const [, chr, pos, ref, alt] = match;
    return `${chr}:${pos}_${alt}/${ref}`;
}

export function pickLeadVariantRow(rows) {
    if (!rows?.length) {
        return null;
    }

    let lead = rows[0];
    rows.forEach((row) => {
        const pValue = row["P-Value"];
        const leadP = lead["P-Value"];
        if (typeof pValue === "number" && (leadP == null || pValue < leadP)) {
            lead = row;
        }
    });
    return lead;
}

export function findAssociationRefRow(rows, refVariant) {
    if (!rows?.length) {
        return null;
    }
    if (refVariant) {
        const match = rows.find(
            (row) =>
                row["Variant ID"] === refVariant || rowToLdVariant(row) === refVariant
        );
        if (match) {
            return match;
        }
    }
    return pickLeadVariantRow(rows);
}

/** Lead variant unless the user pinned a reference variant for LD. */
export function resolveLdReferenceRow(
    rows,
    { refVariant = null, refVariantUserSet = false } = {}
) {
    if (!rows?.length) {
        return null;
    }
    if (refVariantUserSet) {
        return findAssociationRefRow(rows, refVariant);
    }
    return pickLeadVariantRow(rows);
}

export function buildLdScoresUrl({
    population,
    refVariant,
    region,
    genomeBuild = LD_SERVER_DEFAULTS.genomeBuild,
    reference = LD_SERVER_DEFAULTS.reference,
    correlation = LD_SERVER_DEFAULTS.correlation,
    limit = LD_SERVER_DEFAULTS.limit,
    baseUrl = LD_SERVER_DEFAULTS.baseUrl,
}) {
    const params = new URLSearchParams({
        correlation,
        variant: refVariant,
        chrom: String(region.chr),
        start: String(region.start),
        stop: String(region.end),
        limit: String(limit),
    });

    return (
        `${baseUrl}/genome_builds/${genomeBuild}/references/${reference}/populations/` +
        `${population}/variants?${params.toString()}`
    );
}

function buildLdScoreMap(ldJson) {
    const scoreMap = new Map();
    if (!ldJson?.data?.variant2 || !ldJson?.data?.correlation) {
        return scoreMap;
    }

    ldJson.data.variant2.forEach((variant, index) => {
        const score = ldJson.data.correlation[index];
        variantAliasKeys(variant).forEach((key) => {
            scoreMap.set(key, score);
        });
    });

    return scoreMap;
}

export function lookupLdScore(scoreMap, row) {
    const candidates = [row.varId, row["Variant ID"]].filter(Boolean);
    for (const candidate of candidates) {
        for (const key of variantAliasKeys(candidate)) {
            if (scoreMap.has(key)) {
                return scoreMap.get(key);
            }
        }
    }
    return null;
}

/**
 * Fetch LD r² scores for a locus relative to the lead variant.
 */
export async function fetchLdScoreMap(rows, session) {
    if (!Array.isArray(rows) || !rows.length || !session?.region) {
        return { scoreMap: new Map(), refVariant: null };
    }

    const leadRow = pickLeadVariantRow(rows);
    return fetchLdScoreMapForRefRow(leadRow, session, session.region);
}

/**
 * Fetch LD r² scores for a locus relative to a user-selected reference variant.
 */
export async function fetchLdScoreMapForRefRow(refRow, session, region) {
    if (!refRow || !session || !region) {
        return { scoreMap: new Map(), refVariant: null };
    }

    const refVariant = rowToLdVariant(refRow);
    if (!refVariant) {
        return { scoreMap: new Map(), refVariant: null };
    }

    const population = resolveLdPopulation(session.ancestry);

    // GWAS-CE DIVERGENCE (allele orientation): try the uploaded orientation, then
    // the flip. The LD server answers the wrong orientation with an empty but
    // NON-error payload, which is indistinguishable from "this locus has no LD
    // data" -- so without the retry a whole dataset renders grey and nothing
    // anywhere reports a problem. The second call only happens when the first
    // yields nothing.
    const candidates = [refVariant, flipVariantAlleles(refVariant)].filter(Boolean);

    for (const candidate of candidates) {
        const ldUrl = buildLdScoresUrl({
            population,
            refVariant: candidate,
            region,
        });

        try {
            const ldJson = await fetch(ldUrl).then((response) => response.json());
            if (ldJson?.error != null || !ldJson?.data?.variant1?.length) {
                continue;
            }

            // The ORIGINAL refVariant is returned even when the flip is what the
            // server answered: callers use it to find the reference dot among our
            // own rows, which carry the uploaded orientation.
            return {
                scoreMap: buildLdScoreMap(ldJson),
                refVariant,
            };
        } catch (error) {
            // A transport failure will not resolve differently for the flip.
            console.warn("Variant Sifter LD score fetch failed", error);
            return { scoreMap: new Map(), refVariant };
        }
    }

    return { scoreMap: new Map(), refVariant };
}

export async function enrichAssociationRowsWithLdScoresForRef(rows, session, refRow, region) {
    if (!Array.isArray(rows) || !rows.length || !refRow) {
        return rows;
    }

    const { scoreMap } = await fetchLdScoreMapForRefRow(
        refRow,
        session,
        region || session.region
    );
    if (!scoreMap.size) {
        return rows;
    }

    return rows.map((row) => {
        const ldScore = lookupLdScore(scoreMap, row);
        if (ldScore == null) {
            return { ...row, LDS: null };
        }
        return {
            ...row,
            LDS: ldScore,
        };
    });
}

/**
 * Fetch LD r² scores for a locus and merge into association rows as LDS.
 */
export async function enrichAssociationRowsWithLdScores(rows, session) {
    if (!Array.isArray(rows) || !rows.length || !session?.region) {
        return rows;
    }

    const { scoreMap } = await fetchLdScoreMap(rows, session);
    if (!scoreMap.size) {
        return rows;
    }

    return rows.map((row) => {
        const ldScore = lookupLdScore(scoreMap, row);
        if (ldScore == null) {
            return row;
        }
        return {
            ...row,
            LDS: ldScore,
        };
    });
}
