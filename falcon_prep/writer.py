"""Write FALCON's per-chromosome sumstats files.

FALCON's sumstats reader resolves `{chr}.sumstats` inside the folder named by
`sumstats-folder` (see falcon-rs/src/io/readers.rs::resolve_paths) and requires
a header row.
"""
from __future__ import annotations

import os
from collections import defaultdict

from .extract import Variant

SUMSTATS_HEADER = ("rsID", "BETA", "SE", "Z", "CHROM", "POS", "REF", "ALT", "N")

# Characters that would break a tab-separated row. Nothing upstream removes
# them: an upload whose separator is a comma can carry a literal tab inside
# a field, and a tab in ALT would shift every later column, silently
# corrupting N. rsID and allele values are alphanumeric, so stripping these
# cannot alter a well-formed value.
_ROW_BREAKING = str.maketrans("", "", "\t\r\n")


def _clean(value: str) -> str:
    """Remove characters that would corrupt the tab-separated row."""
    return value.translate(_ROW_BREAKING)


def write_sumstats(variants: list[Variant], out_dir: str) -> dict[int, int]:
    """Write one {chr}.sumstats per chromosome present. Returns counts per chrom.

    Precondition: every variant carries a non-None rsID. `resolve()` guarantees
    this by dropping anything it cannot resolve. A None would be written as the
    literal string "None", which FALCON would treat as an ID matching nothing in
    the LD reference and drop without warning -- so callers must resolve first.

    Text fields (rsID, REF, ALT) are sanitized here to remove row-breaking
    characters (tab, carriage return, newline). Nothing upstream validates
    alleles, and an upload with a comma separator can carry tabs inside fields;
    a tab in ALT would shift every later column, silently corrupting N.

    Float fields use repr(), which round-trips exactly in Python 3, so no
    precision is lost between the converter and FALCON.
    """
    os.makedirs(out_dir, exist_ok=True)

    by_chrom: dict[int, list[Variant]] = defaultdict(list)
    for v in variants:
        by_chrom[v.chrom].append(v)

    counts: dict[int, int] = {}
    for chrom, rows in sorted(by_chrom.items()):
        rows.sort(key=lambda v: v.pos)
        path = os.path.join(out_dir, f"{chrom}.sumstats")
        with open(path, "w") as fh:
            fh.write("\t".join(SUMSTATS_HEADER) + "\n")
            for v in rows:
                fh.write(
                    f"{_clean(v.rsid)}\t{v.beta!r}\t{v.se!r}\t{v.z!r}\t"
                    f"{v.chrom}\t{v.pos}\t{_clean(v.ref)}\t{_clean(v.alt)}\t{v.n!r}\n"
                )
        counts[chrom] = len(rows)
    return counts
