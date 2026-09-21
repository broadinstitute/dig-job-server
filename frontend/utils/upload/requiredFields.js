// The column mappings an upload cannot proceed without.
//
// `se` is deliberately ABSENT, and must stay absent. No analysis method reads
// it:
//   - sLDSC derives Z from the p-value and the sign of beta, and falls back to
//     ln(oddsRatio) when there is no beta
//     (dig-ldsc-methods src/ldsc/sumstats/main.py::get_beta, ::p_to_z)
//   - MAGMA and PIGEAN carry only (variant, pValue, n)
//     (src/magma/genes/sumstats.py, src/pigean/pigean/sumstats.py)
//   - FALCON recovers SE as |beta/z| when the upload has none
//     (falcon_prep/zscore.py::derive)
// Requiring it rejected every GWAS that publishes an odds ratio and a p-value
// but no standard error -- PGC and most case/control studies -- for a column
// nothing downstream consumes.
//
// `rsid` is likewise ABSENT (2026-09-21). No method in dig-ldsc-methods reads
// the upload's rsID column: sLDSC keys variants by chromosome:position:ref:alt
// and MAGMA/PIGEAN by chromosome:position, each resolving rsIDs from its own
// snpmap (src/ldsc/sumstats/main.py, src/magma/genes/sumstats.py,
// src/pigean/pigean/sumstats.py). The Variant Sifter's credible-set step fills
// a missing rsID from the aggregator's dbSNP map
// (variant_sifter_pipeline/credible_sets.py::dbsnp_rsid_lookup). FALCON prefers
// a mapped rsID column, auto-detects one otherwise
// (falcon_prep/extract.py), and only hard-requires it for GRCh38 uploads,
// where the job exits 10 with that explanation (falcon_prep/resolve.py).
// Mapping rsID is still offered as an optional field, and is worth doing for
// FALCON on GRCh38.
//
// The effect-size and sample-size rules are separate, and the page still
// enforces both: beta OR oddsRatio, and an `n` column OR an effective N.
export const REQUIRED_FIELDS = [
  { name: "chromosome", value: "chromosome" },
  { name: "position", value: "position" },
  { name: "other_allele", value: "reference" },
  { name: "effect_allele", value: "alt" },
  { name: "pValue", value: "pValue" },
];

/** The required fields a col_map has not mapped yet, in display order. */
export function missingRequiredFields(colMap) {
  return REQUIRED_FIELDS.filter((field) => !(field.value in (colMap || {})));
}
