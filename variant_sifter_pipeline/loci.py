"""Genomic locus helpers: canonical chromosome ordering + a variant sort key.

The variant_key is the within-file sort order the bioindex requires (locus
order), and is reused as the GWAS↔reference join key elsewhere.
"""

_CHROM_ORDER = {str(i): i for i in range(1, 23)}
_CHROM_ORDER.update({"X": 23, "Y": 24, "XY": 25, "MT": 26, "M": 26})


def chrom_rank(chrom: str) -> int:
    c = str(chrom).upper().removeprefix("CHR")
    return _CHROM_ORDER.get(c, 99)


def variant_key(row: dict) -> tuple:
    return (chrom_rank(row["chromosome"]), int(row["position"]),
            row["reference"], row["alt"])
