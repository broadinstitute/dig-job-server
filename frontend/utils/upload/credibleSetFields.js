// What a credible-set upload must and may carry. The contract is the
// aggregator's own for user credible sets (dig-aggregator-methods
// credible-sets/credibleSets.py::convert_credible_set) minus the fields we take
// from the parent GWAS (phenotype, ancestry, dataset). Mirrored server-side in
// job_server/credible_sets.py REQUIRED_FIELDS / OPTIONAL_FIELDS.
import { GWAS_COLUMN_ALIASES, suggestColumnMap, NEVER_FUZZY_MATCH } from "./suggestColumnMap";

export const CS_REQUIRED_FIELDS = [
  { name: "chromosome", value: "chromosome" },
  { name: "position", value: "position" },
  { name: "other_allele", value: "reference" },
  { name: "effect_allele", value: "alt" },
  { name: "credible set id", value: "credibleSetId" },
  { name: "posterior probability", value: "posteriorProbability" },
];

export const CS_OPTIONAL_FIELDS = [
  { name: "pValue", value: "pValue" },
  { name: "beta", value: "beta" },
  { name: "se", value: "se" },
  { name: "n", value: "n" },
  { name: "rsID", value: "rsid" },
];

export const CS_COL_OPTIONS = [...CS_REQUIRED_FIELDS, ...CS_OPTIONAL_FIELDS];

// GWAS aliases whose targets a credible set never carries; offering them would
// let `maf` or `OR` headers claim a field the server then rejects.
const GWAS_ONLY_TARGETS = new Set(["oddsRatio", "eaf", "maf", "zScore"]);

const CS_ONLY_ALIASES = {
  // credible set id
  cs: "credibleSetId", cs_id: "credibleSetId", credible_set: "credibleSetId",
  credible_set_id: "credibleSetId", credibleset: "credibleSetId",
  crediblesetid: "credibleSetId", set: "credibleSetId", set_id: "credibleSetId",
  signal: "credibleSetId", signal_id: "credibleSetId", locus: "credibleSetId",
  locus_id: "credibleSetId", cluster: "credibleSetId",
  // posterior probability
  pip: "posteriorProbability", pp: "posteriorProbability",
  posterior: "posteriorProbability", posterior_prob: "posteriorProbability",
  posterior_probability: "posteriorProbability", prob: "posteriorProbability",
  posteriorprobability: "posteriorProbability", cs_pip: "posteriorProbability",
  pip_cs: "posteriorProbability", probability: "posteriorProbability",
};

export const CREDIBLE_SET_COLUMN_ALIASES = {
  ...Object.fromEntries(
    Object.entries(GWAS_COLUMN_ALIASES).filter(([, target]) => !GWAS_ONLY_TARGETS.has(target)),
  ),
  ...CS_ONLY_ALIASES,
};

const CS_TARGETS = CS_COL_OPTIONS.map((o) => o.value);

// A wrong guess here silently reshuffles which variants belong to which
// credible set, or corrupts the reported posterior probability; server
// validation cannot detect a plausible-looking wrong column. Alias only.
export const CS_NEVER_FUZZY_MATCH = new Set([
  ...NEVER_FUZZY_MATCH, "credibleSetId", "posteriorProbability",
]);

/** The required fields a col_map has not mapped yet, in display order. */
export function missingCredibleSetFields(colMap) {
  return CS_REQUIRED_FIELDS.filter((field) => !(field.value in (colMap || {})));
}

/** Best-guess {column: field} for a credible-set file's headers. */
export function suggestCredibleSetMap(columns) {
  return suggestColumnMap(columns, CS_TARGETS, CREDIBLE_SET_COLUMN_ALIASES, CS_NEVER_FUZZY_MATCH);
}
