// Ported verbatim from dig-dug-portal@5619cbfe1
// src/components/researchPortal/customComponents/kpVariantSifter/variantSifterAssociationsTableFormat.js
// Pure data — do not prune "custom table" / "tool tips" / "column formatting"
// even though we do not consume them yet; keeping them keeps this file
// diffable against upstream.
//
// buildFilterModel/visibleColumns below are our own additions (not part of
// the upstream port) — see their doc comments.
import { FilterMatchMode } from "@primevue/core/api";

/** GEM package table format for Variant Sifter associations. */
export const ASSOCIATIONS_TABLE_FORMAT = {
    "custom table": {
        name: "gem package",
        "Credible Set": { "key field": "Variant ID", PPA: "posteriorProbability" },
        Annotation: { "key field": "Position" },
        Tissue: { "key field": "Position" },
    },
    "data convert": [
        { type: "raw", "field name": "Ancestry", "raw field": "ancestry" },
        { type: "raw", "field name": "chromosome", "raw field": "chromosome" },
        { type: "raw", "field name": "Position", "raw field": "position" },
        { type: "raw", "field name": "ref", "raw field": "reference" },
        { type: "raw", "field name": "alt", "raw field": "alt" },
        { type: "raw", "field name": "Beta", "raw field": "beta" },
        { type: "raw", "field name": "MAF", "raw field": "maf" },
        { type: "raw", "field name": "Standard Error", "raw field": "stdErr" },
        { type: "raw", "field name": "Consequence", "raw field": "consequence" },
        { type: "raw", "field name": "Z Score", "raw field": "zScore" },
        { type: "raw", "field name": "P-Value", "raw field": "pValue" },
        { type: "raw", "field name": "rsID", "raw field": "dbSNP" },
        { type: "raw", "field name": "LDS", "raw field": "ldScore" },
        { type: "raw", "field name": "EAF", "raw field": "eaf" },
        {
            type: "join",
            "field name": "Ref/Alt",
            "fields to join": ["reference", "alt"],
            "join by": "/",
        },
        {
            type: "join",
            "field name": "Locus",
            "fields to join": ["chromosome", "position"],
            "join by": ":",
        },
        {
            type: "join multi",
            "field name": "Variant ID",
            "fields to join": ["chromosome", "position", "reference", "alt"],
            "join by": [":", "_", "/"],
        },
        { type: "raw", "field name": "chr", "raw field": "chromosome" },
        {
            type: "calculate",
            "field name": "-log10(P-Value)",
            "raw field": "pValue",
            "calculation type": "-log10",
        },
    ],
    "top rows": [
        "Variant ID",
        "rsID",
        "Ref/Alt",
        "P-Value",
        "Beta",
        "MAF",
        "Standard Error",
        "Z Score",
        "Consequence",
        "Ancestry",
    ],
    "tool tips": {
        "Variant ID": "chromosome:position (hg19)_ref/alt",
        rsID: "Variant ID from dbGaP",
        "Ref/Alt": "Reference allele/alternate allele",
        "P-Value": "Significance of association with the selected phenotype(s)",
        Beta: "Effect size",
        MAF: "Minor allele frequency",
        "Z Score": "Beta / Standard error",
        Consequence:
            "Impact of the variant for overlapping genes or transcripts, as predicted by the Ensembl Variant Effect Predictor (VEP)",
        "Credible Set":
            "Posterior Probability of Association for the variant in the selected credible set(s)",
        "Cred. sets":
            "Highest Posterior Probability of Association among mapped credible sets. Click to expand matched sets.",
    },
    "locus field": "Locus",
    "star column": "Variant ID",
    "column formatting": {
        "P-Value": { type: ["scientific notation"] },
        "Odds Ratio": { type: ["scientific notation"] },
        Beta: { type: ["scientific notation"] },
        EAF: { type: ["scientific notation"] },
        MAF: { type: ["scientific notation"] },
        "Standard Error": { type: ["scientific notation"] },
        "Z Score": { type: ["scientific notation"] },
        "Variant ID": {
            type: ["link"],
            "link to": "/variant.html?variant=",
            "new tab": "true",
        },
        rsID: {
            type: ["link"],
            "link to": "/variant.html?variant=",
            "new tab": "true",
        },
        "Target Gene": {
            type: ["link"],
            "link to": "/gene.html?gene=",
            "new tab": "true",
        },
    },
};

// Column order comes straight from upstream's "top rows" — do not maintain a
// second list here. Rows arriving at the table are already decorated (Task 3B),
// so these are display names, not raw bioindex field names.
//
// Columns render only when the data actually carries the field, so datasets
// whose col_map omits se/rsid show no blank columns — and the deferred VEP
// join's MAF/Consequence appear automatically once the pipeline emits them,
// with no frontend change.
export const SIFTER_TABLE_COLUMNS = ASSOCIATIONS_TABLE_FORMAT["top rows"]
    // Ancestry is a single value per GWAS-CE dataset, so the column is noise here.
    .filter((field) => field !== "Ancestry")
    .map((field) => ({ field, header: field }));

export function visibleColumns(rows) {
    const list = rows || [];
    return SIFTER_TABLE_COLUMNS.filter((col) =>
        list.some((row) => row[col.field] !== undefined && row[col.field] !== null),
    );
}

// Spec §5: filter semantics per field. Decorated rows can hold a numeric
// field as the STRING "0" (decorateRows.js coerces an exact 0 to "0" before
// assigning, matching upstream's dataConvert "raw" rule) — PrimeVue's built-in
// FilterMatchMode comparators (lte/gte/equals) use native <=/>=/== underneath,
// which already coerce "0" and 0 to equal, so no custom Number()-aware
// comparator is needed here. What *would* silently break this is classifying
// a column as numeric by inspecting a sampled row's `typeof` value instead of
// its field name — a column that happens to be all-zero would look like text
// and lose numeric filtering. So classification below is by field name only,
// never by inspecting row values.
//
// Directions mirror upstream (variantSifterAssociationsFilters.js) where a
// field overlaps: P-Value <=, Beta/Z Score >=. MAF/Standard Error aren't
// filterable upstream; MAF gets EAF's >= ("at least this frequency"), and
// Standard Error gets P-Value's <= ("at most this uncertain").
const NUMERIC_FILTER_MATCH_MODES = {
    "P-Value": FilterMatchMode.LESS_THAN_OR_EQUAL_TO,
    Beta: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO,
    MAF: FilterMatchMode.GREATER_THAN_OR_EQUAL_TO,
    "Standard Error": FilterMatchMode.LESS_THAN_OR_EQUAL_TO,
    "Z Score": FilterMatchMode.GREATER_THAN_OR_EQUAL_TO,
};

export const NUMERIC_FILTER_FIELDS = new Set(Object.keys(NUMERIC_FILTER_MATCH_MODES));

/**
 * PrimeVue DataTable `filters` model, built from visibleColumns(rows) so the
 * filter set stays in lockstep with the column set (spec §5.1: both are
 * driven by field presence in the data — a Consequence filter appears only
 * once the deferred VEP join starts emitting `consequence`).
 */
export function buildFilterModel(rows) {
    const model = {};
    visibleColumns(rows).forEach((col) => {
        model[col.field] = NUMERIC_FILTER_FIELDS.has(col.field)
            ? { value: null, matchMode: NUMERIC_FILTER_MATCH_MODES[col.field] }
            : { value: null, matchMode: FilterMatchMode.CONTAINS };
    });
    return model;
}
