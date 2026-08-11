"""Resolve rsIDs and GRCh37 positions for the significant variants.

FALCON joins LD and S2G by rsID (read_ld_sparse reads only the two ID columns
and R2), and compares positions against GRCh37 gene coordinates from
{chr}.genes.loc. So every variant needs an rsID and a GRCh37 position.

An rsID names a variant, not a coordinate, and is identical across builds --
which is why a GRCh38 upload carrying rsIDs needs no liftover. We look its
GRCh37 position up instead.

Position lookup needs no disambiguation: of 37,018,451 distinct rsIDs in
dbSNP_common_GRCh37.csv, zero map to more than one position. The 15.2% with
multiple rows are multi-allelic (one locus, several alt alleles).
"""
from __future__ import annotations

from dataclasses import dataclass

from .columns import Metadata
from .extract import Variant

SUPPORTED_BUILDS = ("GRCh37", "GRCh38")


class UnsupportedDataset(Exception):
    """The dataset cannot be converted; the caller should fail loudly."""


@dataclass
class ResolveStats:
    needed: int = 0
    resolved: int = 0
    duplicates: int = 0


def _with_pos(v: Variant, pos: int) -> Variant:
    """Return a copy of `v` with its position replaced (GRCh38 -> GRCh37)."""
    return Variant(
        rsid=v.rsid, chrom=v.chrom, pos=pos, ref=v.ref, alt=v.alt,
        beta=v.beta, se=v.se, z=v.z, n=v.n,
    )


def _dedupe_by_rsid(variants: list[Variant]) -> tuple[list[Variant], int]:
    """Keep one variant per rsID, the one with the largest |Z|.

    falcon-rs keys its sumstats maps by rsID, so a duplicate is last-write-wins
    and silently discards the other allele's effect. Deduping here makes the
    choice deterministic and keeps ResolveStats honest about what FALCON models.
    """
    best: dict[str, Variant] = {}
    dropped = 0
    for v in variants:
        prev = best.get(v.rsid)
        if prev is None:
            best[v.rsid] = v
        else:
            dropped += 1
            if abs(v.z) > abs(prev.z):
                best[v.rsid] = v
    return list(best.values()), dropped


def resolve(
    variants: list[Variant], meta: Metadata, dbsnp_path: str
) -> tuple[list[Variant], ResolveStats]:
    """Fill rsID and GRCh37 position, dropping variants that cannot be resolved."""
    build = meta.build
    has_rsid = meta.columns.rsid is not None

    if build not in SUPPORTED_BUILDS:
        raise UnsupportedDataset(
            f"unsupported genome build {build!r}; expected one of {SUPPORTED_BUILDS}"
        )
    if build == "GRCh38" and not has_rsid:
        raise UnsupportedDataset(
            "dataset is GRCh38 and carries no rsID column. FALCON's reference is "
            "GRCh37 and rsID-keyed, and no GRCh38->GRCh37 map is available. "
            "Re-upload with an rsID column."
        )

    stats = ResolveStats(needed=len(variants))
    if not variants:
        return [], stats

    if has_rsid:
        # Validate every rsID against the reference, picking up the GRCh37
        # position in the same pass. Validating matters even for GRCh37 uploads
        # that already carry positions: FALCON joins LD and S2G by rsID and
        # drops unmatched IDs silently, so an unvalidated resolution_rate would
        # report 100% while the run produced nothing.
        wanted = {v.rsid for v in variants if v.rsid}
        found: dict[str, int] = {}
        with open(dbsnp_path) as fh:
            fh.readline()
            for line in fh:
                rsid, _, var_id = line.partition("\t")
                if rsid in wanted and rsid not in found:
                    parts = var_id.strip().split(":")
                    if len(parts) >= 2:
                        try:
                            found[rsid] = int(parts[1])
                        except ValueError:
                            pass
        out = []
        for v in variants:
            pos = found.get(v.rsid)
            if pos is None:
                continue
            # GRCh37 uploads already carry correct coordinates; GRCh38 uploads
            # must take the reference's GRCh37 position instead of their own.
            out.append(v if build == "GRCh37" else _with_pos(v, pos))
        out, stats.duplicates = _dedupe_by_rsid(out)
        stats.resolved = len(out)
        return out, stats

    # GRCh37 without rsID: reverse lookup by chr:pos:ref:alt, both orientations.
    # Keyed by list index, not id() -- object identity is not a stable key.
    wanted: dict[str, int] = {}
    for i, v in enumerate(variants):
        wanted.setdefault(f"{v.chrom}:{v.pos}:{v.ref}:{v.alt}", i)
        wanted.setdefault(f"{v.chrom}:{v.pos}:{v.alt}:{v.ref}", i)
    found: dict[int, str] = {}
    with open(dbsnp_path) as fh:
        fh.readline()
        for line in fh:
            rsid, _, var_id = line.partition("\t")
            idx = wanted.get(var_id.strip())
            if idx is not None and idx not in found:
                found[idx] = rsid
    out = []
    for i, v in enumerate(variants):
        rsid = found.get(i)
        if rsid:
            v.rsid = rsid
            out.append(v)
    out, stats.duplicates = _dedupe_by_rsid(out)
    stats.resolved = len(out)
    return out, stats
