"""Filter a (canonicalized) GWAS upload to its significant subset and shape it
into gwas-ce `associations` records, sorted by locus.

VEP annotations (consequence/nearest) and maf are deferred to a later iteration;
records here carry only upload-derived fields.
"""

import math
from collections.abc import Iterable

from .loci import variant_key

_LOCUS_FIELDS = ("chromosome", "position", "reference", "alt")


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _beta_of(row: dict):
    """beta from the upload, or ln(oddsRatio) for binary traits."""
    b = _to_float(row.get("beta"))
    if b is not None:
        return b
    orr = _to_float(row.get("oddsRatio"))
    if orr is not None and orr > 0:
        return math.log(orr)
    return None


def _pvalue_of(row: dict, beta, se):
    """pValue from the upload, else a two-sided p derived from z = beta/se."""
    p = _to_float(row.get("pValue"))
    if p is not None:
        return p
    if beta is not None and se not in (None, 0):
        z = beta / se
        return math.erfc(abs(z) / math.sqrt(2))
    return None


def build_associations(rows: Iterable[dict], guid: str,
                       p_threshold: float = 0.05,
                       ancestry: "str | None" = None,
                       effective_n: "float | None" = None) -> list[dict]:
    """Keep rows with pValue <= p_threshold (the filter that shrinks millions of
    variants to thousands), shape each survivor into a record keyed by
    phenotype=<guid>, and return them sorted by locus.

    Optional fields are emitted only when the upload actually carries them --
    the sifter's table columns and filters are driven by field presence, so an
    absent field simply hides its column rather than showing a blank one.

    `ancestry` and `effective_n` come from the dataset metadata rather than the
    file, and are the per-dataset fallbacks for the per-row `n` column.
    """
    out: list[dict] = []
    for r in rows:
        if any(r.get(k) in (None, "") for k in _LOCUS_FIELDS):
            continue
        beta = _beta_of(r)
        se = _to_float(r.get("se"))
        p = _pvalue_of(r, beta, se)
        if p is None or p > p_threshold:
            continue
        rec = {
            "phenotype": guid,
            "chromosome": str(r["chromosome"]),
            "position": int(r["position"]),
            "reference": r["reference"],
            "alt": r["alt"],
            "pValue": p,
        }
        if ancestry:
            rec["ancestry"] = ancestry
        if beta is not None:
            rec["beta"] = beta
        if se is not None:
            rec["stdErr"] = se
        # Prefer the derived z (consistent with beta/stdErr); fall back to a
        # z the upload supplied directly, which is common in munged sumstats
        # that carry no standard error.
        if beta is not None and se not in (None, 0):
            rec["zScore"] = beta / se
        else:
            z = _to_float(r.get("zScore"))
            if z is not None:
                rec["zScore"] = z
        if r.get("rsid") is not None:
            rec["dbSNP"] = r["rsid"]
        # Effect-allele frequency is ALT-relative like beta, so orienting a
        # variant rewrites it (see reference.orient_record). MAF is not --
        # the minor allele is the minor allele either way round.
        eaf = _to_float(r.get("eaf"))
        if eaf is not None:
            rec["eaf"] = eaf
        maf = _to_float(r.get("maf"))
        if maf is not None:
            rec["maf"] = maf
        n = _to_float(r.get("n"))
        if n is None:
            n = _to_float(effective_n)
        if n is not None:
            rec["n"] = n
        out.append(rec)
    out.sort(key=variant_key)
    return out
