// Best-guess mapping from an uploaded GWAS's column headers to our canonical
// field names. Adapted from data-registry-api's suggest_column_map
// (dataregistry/api/mskkp.py, dataregistry/api/hcm.py), with two deliberate
// divergences noted below.
//
// GWAS-CE CONVENTION, and it is the opposite of one of the two upstream tables:
//   `reference` = the NON-EFFECT / other allele  (reference-genome REF)
//   `alt`       = the EFFECT allele              (reference-genome ALT)
// hcm.py agrees ('ref' -> non_effect_allele); mskkp.py does NOT
// ('ref' -> effectAllele, 'alt' -> nonEffectAllele). Following mskkp here would
// swap every allele pair, and because the pipeline now canonicalises against the
// reference genome -- swapping alleles AND negating beta -- an inverted mapping
// would not merely mislabel columns, it would invert reported effect directions.
// So hcm's convention is the one encoded here.

export const GWAS_COLUMN_ALIASES = {
  // chromosome
  chr: "chromosome", chrom: "chromosome", "#chr": "chromosome",
  "#chrom": "chromosome", chromosome: "chromosome",
  // position
  bp: "position", pos: "position", position: "position", genpos: "position",
  base_pair_location: "position", bp_pos: "position",
  // rsID
  snp: "rsid", snpid: "rsid", rsid: "rsid", rs: "rsid", rs_id: "rsid",
  variant: "rsid", variant_id: "rsid", markername: "rsid", markerid: "rsid",
  // NON-effect allele
  a2: "reference", other_allele: "reference", non_effect_allele: "reference",
  allele2: "reference", nea: "reference", ref: "reference", reference: "reference",
  // EFFECT allele
  a1: "alt", ea: "alt", effect_allele: "alt", effectallele: "alt",
  allele1: "alt", coded_allele: "alt", alt: "alt",
  // p-value
  p: "pValue", pval: "pValue", pvalue: "pValue", p_value: "pValue",
  "p-value": "pValue", p_val: "pValue",
  // effect size
  beta: "beta", effect: "beta", effect_size: "beta", b: "beta",
  or: "oddsRatio", odds_ratio: "oddsRatio", oddsratio: "oddsRatio",
  // standard error
  se: "se", stderr: "se", standard_error: "se", sebeta: "se",
  std_err: "se", se_beta: "se",
  // sample size
  n: "n", n_total: "n", total_n: "n", sample_size: "n",
  samplesize: "n", neff: "n",
  // effect allele frequency. NB: hcm.py folds 'maf' in here; we do not --
  // MAF is by definition <= 0.5 and EAF is not, so conflating them would
  // silently corrupt whichever one the file actually holds.
  eaf: "eaf", freq: "eaf", frq: "eaf", freq1: "eaf", af: "eaf",
  a1freq: "eaf", a1_freq: "eaf", allele_frequency: "eaf",
  effect_allele_frequency: "eaf",
  // minor allele frequency
  maf: "maf", minor_allele_frequency: "maf",
  // z score
  z: "zScore", zscore: "zScore", z_score: "zScore", zstat: "zScore",
};

// Fields where a wrong guess is silently destructive rather than merely wrong:
// alleles decide effect direction, and beta/oddsRatio ARE the effect. These are
// matched by explicit alias only -- never by string similarity.
export const NEVER_FUZZY_MATCH = new Set(["reference", "alt", "beta", "oddsRatio"]);

export const SIMILARITY_THRESHOLD = 0.6;

/** Dice coefficient over character bigrams. 1 = identical, 0 = nothing shared. */
export function similarity(a, b) {
  if (a === b) return 1;
  if (a.length < 2 || b.length < 2) return 0;
  const bigrams = (s) => {
    const out = new Map();
    for (let i = 0; i < s.length - 1; i += 1) {
      const g = s.slice(i, i + 2);
      out.set(g, (out.get(g) || 0) + 1);
    }
    return out;
  };
  const ga = bigrams(a);
  const gb = bigrams(b);
  let shared = 0;
  ga.forEach((count, g) => {
    if (gb.has(g)) shared += Math.min(count, gb.get(g));
  });
  return (2 * shared) / (a.length - 1 + b.length - 1);
}

const normalize = (s) => String(s).toLowerCase().trim();

/**
 * Suggest {columnName: canonicalField} for the given file columns.
 *
 * Pass 1 matches by alias then by exact name; pass 2 fuzzy-matches whatever is
 * left, skipping the destructive fields. A target is claimed at most once, so
 * a file carrying both `A1` and `effect_allele` yields one effect-allele
 * mapping rather than two competing ones.
 */
export function suggestColumnMap(columns, targetFields, aliases = GWAS_COLUMN_ALIASES) {
  const targets = new Set(targetFields);
  const suggested = {};
  const claimed = new Set();

  (columns || []).forEach((col) => {
    const key = normalize(col);
    const aliasTarget = aliases[key];
    if (aliasTarget && targets.has(aliasTarget) && !claimed.has(aliasTarget)) {
      suggested[col] = aliasTarget;
      claimed.add(aliasTarget);
      return;
    }
    const exact = targetFields.find((t) => normalize(t) === key && !claimed.has(t));
    if (exact) {
      suggested[col] = exact;
      claimed.add(exact);
    }
  });

  (columns || []).forEach((col) => {
    if (suggested[col]) return;
    const key = normalize(col);
    let best = null;
    let bestScore = 0;
    targetFields.forEach((t) => {
      if (claimed.has(t) || NEVER_FUZZY_MATCH.has(t)) return;
      const score = similarity(key, normalize(t));
      if (score > bestScore) {
        bestScore = score;
        best = t;
      }
    });
    if (best && bestScore >= SIMILARITY_THRESHOLD) {
      suggested[col] = best;
      claimed.add(best);
    }
  });

  return suggested;
}
