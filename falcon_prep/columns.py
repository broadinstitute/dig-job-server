"""Column discovery for dig-job-server GWAS uploads.

The job server stores a `col_map` in each dataset's raw/metadata, but it maps
only the columns the existing methods need -- it never records rsID. FALCON
requires one, because its LD and S2G references are rsID-keyed.

rsID detection is by CONTENT, not by column name. `variant_id` holds
`chr:pos:ref:alt` in one surveyed upload and rsIDs in another, so names alone
are not safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Column names worth sampling, lowercased. Content decides the winner.
_RSID_CANDIDATES = ("rsid", "rs_id", "rsids", "hm_rsid", "snp", "variant_id", "rs")
_RSID_PATTERN = re.compile(r"^rs\d+$", re.IGNORECASE)
_MISSING = {"", "na", "n/a", "nan", "null", "none", "."}
# Fraction of sampled values that must look like rsIDs.
_RSID_MIN_HIT_RATE = 0.9


@dataclass(frozen=True)
class Columns:
    # All optional: a col_map may omit any of these, and detection or
    # derivation fills the gaps. Callers must handle None.
    chrom: Optional[str]
    pos: Optional[str]
    ref: Optional[str]
    alt: Optional[str]
    beta: Optional[str] = None
    odds_ratio: Optional[str] = None
    se: Optional[str] = None
    pvalue: Optional[str] = None
    zscore: Optional[str] = None
    n: Optional[str] = None
    rsid: Optional[str] = None


@dataclass(frozen=True)
class Metadata:
    columns: Columns
    # Optional: meta.get() yields None for a malformed metadata file. Tasks 4
    # and 6 reject None cleanly (not in SUPPORTED_BUILDS; not "EUR"), so the
    # error surfaces at the right boundary rather than as a late AttributeError.
    build: Optional[str]
    ancestry: Optional[str]
    effective_n: Optional[float]
    separator: str


def parse_metadata(meta: dict) -> Metadata:
    """Turn a job-server raw/metadata dict into a typed Metadata."""
    # Key names come from job_server/falcon.py::COLMAP_TO_SUMSTATS, which is the
    # authority on what the upload form emits. `rsid` and `se` are supported for
    # current uploads; historical datasets predate them, which is why Task 3
    # falls back to content-based rsID detection.
    cm = meta.get("col_map") or {}
    columns = Columns(
        chrom=cm.get("chromosome"),
        pos=cm.get("position"),
        ref=cm.get("reference"),
        alt=cm.get("alt"),
        beta=cm.get("beta"),
        odds_ratio=cm.get("oddsRatio"),
        se=cm.get("se"),
        pvalue=cm.get("pValue"),
        zscore=cm.get("zScore"),
        n=cm.get("n"),
        rsid=cm.get("rsid"),
    )
    n_eff = meta.get("effective_n")
    return Metadata(
        columns=columns,
        build=meta.get("genome_build"),
        ancestry=meta.get("ancestry"),
        effective_n=float(n_eff) if n_eff is not None else None,
        separator=meta.get("separator", "\t"),
    )


def detect_rsid_column(header: list[str], sample_rows: list[list[str]]) -> Optional[str]:
    """Return the header entry whose sampled values look like rsIDs, else None."""
    for idx, name in enumerate(header):
        if name.strip().lower() not in _RSID_CANDIDATES:
            continue
        values = [r[idx] for r in sample_rows if idx < len(r)]
        present = [v for v in values if v.strip().lower() not in _MISSING]
        if not present:
            continue
        hits = sum(1 for v in present if _RSID_PATTERN.match(v.strip()))
        if hits / len(values) >= _RSID_MIN_HIT_RATE:
            return name
    return None
