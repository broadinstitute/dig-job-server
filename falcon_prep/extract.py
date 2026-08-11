"""Stream a raw GWAS upload and keep only the variants FALCON will model.

FALCON's `zero_snp_thr` marks variants with |Z| >= threshold as `passed_z`, and
only that subset becomes `snps_in_region_index` -- the working set for both the
LD join and the model. Filtering here is equivalent and collapses a 30M-row
upload to a few hundred rows. See the parity check in docker/RESULTS.md.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import IO, Optional

from .columns import Metadata, detect_rsid_column
from .zscore import derive

_SAMPLE_ROWS = 200


class UnmappedColumns(Exception):
    """The upload's header lacks a column the run cannot proceed without."""
_MISSING = {"", "na", "n/a", "nan", "null", "none", "."}


@dataclass
class Variant:
    rsid: Optional[str]
    chrom: int
    pos: int
    ref: str
    alt: str
    beta: float
    se: float
    z: float
    n: float


@dataclass
class ExtractStats:
    total: int = 0
    significant: int = 0
    unparseable: int = 0


def _num(row: list[str], idx: Optional[int]) -> Optional[float]:
    if idx is None or idx >= len(row):
        return None
    raw = row[idx].strip()
    if raw.lower() in _MISSING:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _text(row: list[str], idx: Optional[int]) -> Optional[str]:
    if idx is None or idx >= len(row):
        return None
    raw = row[idx].strip()
    return None if raw.lower() in _MISSING else raw


def extract_significant(
    handle: IO[str], meta: Metadata, z_threshold: float
) -> tuple[list[Variant], ExtractStats, Metadata]:
    """Return significant variants, counts, and Metadata with rsID column filled."""
    sep = meta.separator
    header = handle.readline().rstrip("\n").rstrip("\r").split(sep)

    # Buffer a sample so rsID detection can inspect content, then replay it.
    sample: list[list[str]] = []
    for line in handle:
        sample.append(line.rstrip("\n").rstrip("\r").split(sep))
        if len(sample) >= _SAMPLE_ROWS:
            break

    # col_map's rsid mapping wins when it names a column that is actually
    # present; content detection is the fallback for datasets uploaded before
    # col_map recorded rsid.
    rsid_col = meta.columns.rsid
    if rsid_col is None or rsid_col not in header:
        rsid_col = detect_rsid_column(header, sample)
    meta = dataclasses.replace(
        meta, columns=dataclasses.replace(meta.columns, rsid=rsid_col)
    )

    def col(name: Optional[str]) -> Optional[int]:
        return header.index(name) if name and name in header else None

    c = meta.columns
    i_chrom, i_pos = col(c.chrom), col(c.pos)
    i_ref, i_alt = col(c.ref), col(c.alt)
    i_beta, i_or = col(c.beta), col(c.odds_ratio)
    i_se, i_p, i_z, i_n = col(c.se), col(c.pvalue), col(c.zscore), col(c.n)
    i_rsid = col(rsid_col)

    # Without these, every row is unparseable and the run reports "no variants
    # passed the threshold" -- which is false, and points at the trait rather
    # than at a column mapping that never matched the header.
    missing = [
        label
        for label, idx in (("chromosome", i_chrom), ("position", i_pos))
        if idx is None
    ]
    if i_beta is None and i_or is None and i_z is None:
        missing.append("beta/oddsRatio/zScore")
    if missing:
        raise UnmappedColumns(
            "these columns are not present in the upload's header: "
            + ", ".join(missing)
            + f". Header is: {', '.join(header[:12])}"
        )

    stats = ExtractStats()
    out: list[Variant] = []

    def handle_row(row: list[str]) -> None:
        stats.total += 1

        chrom_raw = _text(row, i_chrom)
        if chrom_raw is None:
            stats.unparseable += 1
            return
        chrom_raw = chrom_raw.lower().removeprefix("chr")
        try:
            chrom = int(chrom_raw)
        except ValueError:
            stats.unparseable += 1
            return
        if not 1 <= chrom <= 22:
            stats.unparseable += 1
            return

        pos = _num(row, i_pos)
        if pos is None:
            stats.unparseable += 1
            return

        beta = _num(row, i_beta)
        if beta is None:
            odds = _num(row, i_or)
            if odds is not None and odds > 0.0:
                beta = math.log(odds)

        triple = derive(beta, _num(row, i_se), _num(row, i_p), _num(row, i_z))
        if triple is None:
            stats.unparseable += 1
            return
        beta, se, z = triple

        if abs(z) < z_threshold:
            return

        n = _num(row, i_n)
        if n is None:
            n = meta.effective_n
        if n is None:
            stats.unparseable += 1
            return

        stats.significant += 1
        out.append(
            Variant(
                rsid=_text(row, i_rsid),
                chrom=chrom,
                pos=int(pos),
                ref=(_text(row, i_ref) or "NA").upper(),
                alt=(_text(row, i_alt) or "NA").upper(),
                beta=beta, se=se, z=z, n=n,
            )
        )

    for row in sample:
        handle_row(row)
    for line in handle:
        handle_row(line.rstrip("\n").rstrip("\r").split(sep))

    return out, stats, meta
