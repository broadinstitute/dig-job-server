"""Orient an upload's alleles to the reference genome (GRCh37 / b37).

An uploaded GWAS names its alleles "other" and "effect". That is NOT the
reference genome's REF and ALT, and whether they happen to coincide varies
PER VARIANT -- measured on t2d-alex-test, 88% of variants were the wrong way
round and 12% were already correct, within the same dataset. Everything
downstream that keys on a variant id uses reference-genome order: the U-M LD
server and KP's `variant` annotation index both return nothing for a reversed
id, with no error. One reversed lead variant is enough to blank a whole plot.

Orientation needs ONLY the reference genome -- no VEP, no annotation service,
no credentials. The base at chr:pos settles it: whichever uploaded allele equals
the reference base IS the reference allele. Verified against KP's own annotation
on 20 variants, 20/20 agreement.

Flipping a record is NOT just swapping two strings. `beta` is the effect size
per copy of the ALT allele, so when alt changes the sign must change with it,
and `zScore` (= beta/stdErr) with it. `pValue` and `stdErr` are direction-free.
Getting this wrong would invert reported effect directions -- far worse than the
missing-LD symptom this fixes.

Indels are left untouched: correct handling needs left-alignment and a
multi-base reference span, and they are a small minority. They are counted, not
silently dropped.
"""

import os

# Public, no credentials required (`--no-sign-request` / UNSIGNED).
DEFAULT_REFERENCE_BUCKET = "broad-references"
DEFAULT_REFERENCE_KEY = "hg19/v0/Homo_sapiens_assembly19.fasta"

# Outcome labels. Reported by orient_records so a run can be audited: a dataset
# that is mostly `neither-allele-matches` is on the opposite strand or the wrong
# genome build, which must be visible rather than quietly passed through.
ALREADY_CANONICAL = "already-canonical"
FLIPPED = "flipped"
INDEL_SKIPPED = "indel-skipped"
NO_REFERENCE_BASE = "no-reference-base"
NEITHER_MATCHES = "neither-allele-matches"

_CONTIG_ALIASES = {"M": "MT"}


def normalize_contig(chromosome) -> str:
    """Upload chromosome -> b37 FASTA contig name ('chr22' -> '22', 'M' -> 'MT')."""
    c = str(chromosome).strip().upper().removeprefix("CHR")
    return _CONTIG_ALIASES.get(c, c)


def parse_fai(text: str) -> dict:
    """Parse a samtools .fai into {contig: (length, offset, linebases, linewidth)}.

    Those five columns are all that is needed to compute the byte offset of any
    base, which is why this needs no pysam/pyfaidx dependency.
    """
    contigs = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        name, length, offset, linebases, linewidth = parts[:5]
        contigs[name] = (int(length), int(offset), int(linebases), int(linewidth))
    return contigs


def base_offset(contig_meta: tuple, position: int) -> int:
    """Byte offset of a 1-based position, accounting for FASTA line wrapping."""
    _, offset, linebases, linewidth = contig_meta
    i = position - 1
    return offset + (i // linebases) * linewidth + (i % linebases)


class ReferenceGenome:
    """Random access to a .fai-indexed FASTA by byte offset."""

    def __init__(self, fasta_path: str, fai_path: "str | None" = None):
        with open(fai_path or f"{fasta_path}.fai") as fh:
            self._contigs = parse_fai(fh.read())
        self._fh = open(fasta_path, "rb")

    def base_at(self, chromosome, position) -> "str | None":
        """Uppercase reference base, or None if the locus is not addressable."""
        meta = self._contigs.get(normalize_contig(chromosome))
        if meta is None:
            return None
        length = meta[0]
        try:
            pos = int(position)
        except (TypeError, ValueError):
            return None
        if not 1 <= pos <= length:
            return None
        self._fh.seek(base_offset(meta, pos))
        base = self._fh.read(1).decode("ascii", errors="ignore").upper()
        return base if base in ("A", "C", "G", "T", "N") else None

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def orient_record(record: dict, genome) -> tuple:
    """Return (record, outcome). The input record is never mutated."""
    ref, alt = record.get("reference"), record.get("alt")
    if not isinstance(ref, str) or not isinstance(alt, str):
        return record, NO_REFERENCE_BASE
    if len(ref) != 1 or len(alt) != 1:
        return record, INDEL_SKIPPED

    base = genome.base_at(record["chromosome"], record["position"])
    if base is None:
        return record, NO_REFERENCE_BASE
    if base == ref.upper():
        return record, ALREADY_CANONICAL
    if base != alt.upper():
        # Neither allele is the reference base: opposite strand, wrong build, or
        # a bad row. Leave it exactly as uploaded rather than guess.
        return record, NEITHER_MATCHES

    flipped = dict(record)
    flipped["reference"], flipped["alt"] = alt, ref
    # alt changed, so every ALT-relative quantity changes sign with it.
    for field in ("beta", "zScore"):
        value = flipped.get(field)
        if isinstance(value, (int, float)):
            flipped[field] = -value
    return flipped, FLIPPED


def orient_records(records, genome) -> tuple:
    """Orient every record. Returns (records, counts-by-outcome).

    Re-sorts, because `loci.variant_key` includes the alleles: flipping can
    reorder two variants at the same position, and bioindex requires its input
    in locus order.
    """
    from .loci import variant_key

    out, counts = [], {}
    for record in records:
        oriented, outcome = orient_record(record, genome)
        counts[outcome] = counts.get(outcome, 0) + 1
        out.append(oriented)
    out.sort(key=variant_key)
    return out, counts


def ensure_local_reference(dest_dir: str = "/tmp/reference") -> str:
    """Fetch the FASTA + .fai to local disk once; return the FASTA path.

    The bucket is public, so requests are unsigned -- the job's own role has no
    access to it and must not need any. Roughly 3.1 GB, well inside Fargate's
    default 20 GiB ephemeral storage, and a one-off cost against a job that
    already runs for minutes.

    Set VS_REFERENCE_FASTA to a local path to skip the download (tests, or a
    future shared EFS mount).
    """
    override = os.getenv("VS_REFERENCE_FASTA")
    if override:
        return override

    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config

    bucket = os.getenv("VS_REFERENCE_BUCKET", DEFAULT_REFERENCE_BUCKET)
    key = os.getenv("VS_REFERENCE_KEY", DEFAULT_REFERENCE_KEY)
    os.makedirs(dest_dir, exist_ok=True)
    fasta_path = os.path.join(dest_dir, os.path.basename(key))

    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
    for suffix in ("", ".fai"):
        target = fasta_path + suffix
        if not os.path.exists(target):
            s3.download_file(bucket, key + suffix, target)
    return fasta_path
