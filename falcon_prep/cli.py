"""Convert a dig-job-server GWAS upload into FALCON per-chromosome sumstats.

    python3 -m falcon_prep.cli --raw-dir RAW --out-dir OUT --dbsnp MAP

Prints a JSON summary on stdout. Exit codes:
    0   success
    10  dataset unsupported (ancestry, build, or missing rsID)
    11  no variants survived -- nothing for FALCON to model

Deliberately not 2: argparse exits 2 on any usage error, so a harness bug
passing a bad argument would otherwise be indistinguishable from a genuine
"this dataset cannot be processed", and a caller branching on the code would
mark a perfectly good dataset unsupported.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import sys
from typing import IO, Optional

from .columns import parse_metadata
from .extract import UnmappedColumns, extract_significant
from .resolve import UnsupportedDataset, resolve
from .writer import write_sumstats

SUPPORTED_ANCESTRY = "EUR"

EXIT_UNSUPPORTED = 10
EXIT_NO_VARIANTS = 11


def _open_upload(raw_dir: str, filename: Optional[str]) -> tuple[IO[str], str]:
    """Open the GWAS upload in `raw_dir`, and return (handle, path) as a pair.

    The dataset metadata's `file` field names the upload authoritatively, so
    prefer it. Fall back to the sole non-metadata file, sorted for determinism --
    an unordered glob would let a stray file be read instead of the real upload.

    The caller reports `path` in its summary so downstream consumers (e.g. the
    manifest) attest the file this converter actually read, not one picked by
    a separate, less careful rule.
    """
    path = os.path.join(raw_dir, filename) if filename else None
    if not path or not os.path.exists(path):
        candidates = sorted(
            p for p in glob.glob(os.path.join(raw_dir, "*"))
            if os.path.basename(p) != "metadata"
        )
        if not candidates:
            raise UnsupportedDataset(f"no upload file found in {raw_dir}")
        path = candidates[0]
    if path.endswith(".gz"):
        return gzip.open(path, "rt", errors="replace"), path
    return open(path, "r", errors="replace"), path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dbsnp", required=True)
    ap.add_argument("--z-threshold", type=float, default=5.0)
    args = ap.parse_args(argv)

    try:
        with open(os.path.join(args.raw_dir, "metadata")) as fh:
            raw_meta = json.load(fh)
        if not isinstance(raw_meta, dict):
            raise ValueError("metadata is not a JSON object")
        meta = parse_metadata(raw_meta)
    except (OSError, ValueError) as exc:
        # json.JSONDecodeError subclasses ValueError, so this covers malformed
        # JSON, a non-object payload, and any filesystem error in one place.
        print(f"UNSUPPORTED: cannot read {args.raw_dir}/metadata: {exc}", file=sys.stderr)
        return EXIT_UNSUPPORTED

    try:
        if meta.ancestry != SUPPORTED_ANCESTRY:
            raise UnsupportedDataset(
                f"ancestry {meta.ancestry!r} is not supported; FALCON's LD "
                f"reference is {SUPPORTED_ANCESTRY}-only and LD structure is "
                "ancestry-specific."
            )
        fh, upload_path = _open_upload(args.raw_dir, raw_meta.get("file"))
        with fh:
            variants, xstats, meta = extract_significant(fh, meta, args.z_threshold)
        variants, rstats = resolve(variants, meta, args.dbsnp)
    except (UnsupportedDataset, UnmappedColumns) as exc:
        print(f"UNSUPPORTED: {exc}", file=sys.stderr)
        return EXIT_UNSUPPORTED

    counts = write_sumstats(variants, args.out_dir)

    rate = (rstats.resolved / rstats.needed) if rstats.needed else 0.0
    summary = {
        "build": meta.build,
        "ancestry": meta.ancestry,
        "rsid_column": meta.columns.rsid,
        "z_threshold": args.z_threshold,
        "upload_file": os.path.basename(upload_path),
        "counts": {
            "total": xstats.total,
            "significant": xstats.significant,
            "unparseable": xstats.unparseable,
            "resolved": rstats.resolved,
            "duplicates": rstats.duplicates,
        },
        "resolution_rate": round(rate, 4),
        "chromosomes": {str(k): v for k, v in counts.items()},
    }
    print(json.dumps(summary))

    if not variants:
        # Which of the two happened matters: one is a thin trait, the other is a
        # reference-coverage problem, and they need different responses.
        if xstats.significant:
            msg = (
                f"{xstats.significant} variant(s) passed |Z| >= {args.z_threshold} "
                f"but none resolved against the dbSNP reference"
            )
        else:
            msg = (
                f"no variants passed |Z| >= {args.z_threshold} "
                f"(of {xstats.total} read, {xstats.unparseable} unparseable)"
            )
        print(msg, file=sys.stderr)
        return EXIT_NO_VARIANTS
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
