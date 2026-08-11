"""Select the LD chunks a run actually needs.

FALCON models only variants at |Z| >= zero-snp-thr, and falcon-rs's
`read_ld_sparse` keeps an LD row only when BOTH of its SNPs are in that set --
it looks each one up in `snps_in_region_index` and discards the row otherwise.
The LD reference is published twice: as whole-chromosome `{N}.ld.sorted` files
(39 GB total) and as 1 Mb windows under `ld_chunks/chr{N}/`, byte-identical in
format including the header.

A run therefore needs only the windows holding its significant variants. On a
real dataset that was 4.15 GB against 38.7 GB, and staging LD cost more wall
clock than running FALCON did.

Only windows containing significant variants are needed, with no neighbours: a
row is stored in the window of its first position, and since both of a kept
row's SNPs are significant, that window necessarily holds a significant variant.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict

CHUNK_SIZE = 1_000_000

_SUMSTATS_RE = re.compile(r"^(\d+)\.sumstats$")


def window_start(pos: int) -> int:
    """Start coordinate of the 1 Mb window containing `pos`."""
    return (pos // CHUNK_SIZE) * CHUNK_SIZE


def chunk_filename(chrom: int, start: int) -> str:
    """Name of the chunk covering [start, start + CHUNK_SIZE) on `chrom`."""
    return f"chr{chrom}_{start}_{start + CHUNK_SIZE}.ld"


def positions_in(sumstats_path: str) -> list[int]:
    """Read the POS column out of a FALCON sumstats file."""
    out: list[int] = []
    with open(sumstats_path) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        try:
            pos_i = header.index("POS")
        except ValueError:
            return out
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if pos_i < len(cols):
                try:
                    out.append(int(cols[pos_i]))
                except ValueError:
                    continue
    return out


def load_available(path: str) -> set[str]:
    """Read the chunk keys that actually exist, one per line."""
    with open(path) as fh:
        return {os.path.basename(line.strip()) for line in fh if line.strip()}


def plan(sumstats_dir: str) -> dict[int, list[str]]:
    """Map each chromosome to the chunk filenames its variants need.

    Chromosomes are taken from the sumstats files actually written, so a
    chromosome with no significant variants contributes nothing.
    """
    by_chrom: dict[int, set[str]] = defaultdict(set)
    for name in sorted(os.listdir(sumstats_dir)):
        m = _SUMSTATS_RE.match(name)
        if not m:
            continue
        chrom = int(m.group(1))
        for pos in positions_in(os.path.join(sumstats_dir, name)):
            by_chrom[chrom].add(chunk_filename(chrom, window_start(pos)))
    return {c: sorted(v) for c, v in sorted(by_chrom.items())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sumstats-dir", required=True)
    ap.add_argument(
        "--prefix",
        default="s3://falcon-data-center/ld_chunks",
        help="base of the chunked LD reference",
    )
    ap.add_argument(
        "--available",
        help=(
            "file listing the chunk keys that exist. Windows without a chunk "
            "are dropped rather than requested, and counted on stderr."
        ),
    )
    args = ap.parse_args(argv)

    selected = plan(args.sumstats_dir)
    if not selected:
        print("no chromosomes with significant variants", file=sys.stderr)
        return 3

    skipped = 0
    if args.available:
        # Not every 1 Mb window has a published chunk: chromosome ends stop
        # short, and some interior windows hold no LD at all. A window with no
        # chunk has no LD data, so its variants would be dropped by FALCON
        # regardless -- but say so rather than failing the download or, worse,
        # skipping silently.
        have = load_available(args.available)
        pruned: dict[int, list[str]] = {}
        for chrom, names in selected.items():
            keep = [n for n in names if n in have]
            skipped += len(names) - len(keep)
            if keep:
                pruned[chrom] = keep
        selected = pruned
        if not selected:
            print("no requested LD chunk exists", file=sys.stderr)
            return 3

    # One "<source> <chromosome>" line per chunk, for the entrypoint to consume.
    for chrom, names in selected.items():
        for name in names:
            print(f"{args.prefix}/chr{chrom}/{name}\t{chrom}")
    total = sum(len(v) for v in selected.values())
    msg = f"selected {total} LD chunks across {len(selected)} chromosomes"
    if skipped:
        msg += f"; {skipped} window(s) have no published chunk and were skipped"
    print(msg, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
