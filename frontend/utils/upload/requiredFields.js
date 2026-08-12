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
// The effect-size and sample-size rules are separate, and the page still
// enforces both: beta OR oddsRatio, and an `n` column OR an effective N.
export const REQUIRED_FIELDS = [
  { name: "chromosome", value: "chromosome" },
  { name: "position", value: "position" },
  { name: "rsID", value: "rsid" },
  { name: "other_allele", value: "reference" },
  { name: "effect_allele", value: "alt" },
  { name: "pValue", value: "pValue" },
];

/** The required fields a col_map has not mapped yet, in display order. */
export function missingRequiredFields(colMap) {
  return REQUIRED_FIELDS.filter((field) => !(field.value in (colMap || {})));
}
