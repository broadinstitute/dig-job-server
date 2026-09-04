"""Orchestrator entrypoint for the `gwas-ce-variant-sifter` Batch job.

Reads one uploaded GWAS, builds the p-value-filtered `associations` records for
that dataset, writes them to the gwas-ce bucket keyed by GUID, and indexes them
in-process. Plan 1's API submits this via sifter_job_config:

    python -m variant_sifter_pipeline.run --username U --dataset D --guid G

First slice = associations only. Harmonization/liftover and VEP annotation are
deferred (see the design spec); this assumes the upload is already on the
reference build.

`--mode` selects what the job does: `full` (the default) builds associations
and derived credible sets and syncs uploaded credible sets, indexing all of
it; `credible-sets` only syncs uploaded credible sets and rebuilds the two
credible-set indexes, leaving associations and derived sets untouched.
"""

import argparse
import contextlib
import csv
import gzip
import io
import json
import os

import boto3

from .associations import build_associations
from .canonicalize import canonicalize
from .credible_sets import write_derived_credible_sets
from .index_build import (associations_key, index_associations,
                          index_credible_sets, index_credible_variants)
from .reference import ReferenceGenome, ensure_local_reference, orient_records
from .uploaded_credible_sets import sync_uploaded_credible_sets

# Where GWAS-CE stores user uploads (same default as job_server.s3).
USER_DATA_BUCKET = os.getenv("JOB_SERVER_BUCKET", "dig-ldsc-server")
# The gwas-ce bioindex bucket (also read by bioindex via BIOINDEX_S3_BUCKET).
GWAS_CE_BUCKET = os.getenv("BIOINDEX_S3_BUCKET", "dig-gwas-ce-bioindex")
P_THRESHOLD = float(os.getenv("VS_P_THRESHOLD", "0.05"))
# Orient alleles to the reference genome so variant ids match what the LD server
# and KP's annotation index key on. Escape hatch in case the reference download
# is ever unavailable -- a run with this off still produces queryable data, just
# with the pre-existing id-orientation problem.
ORIENT_ALLELES = os.getenv("VS_ORIENT_ALLELES", "1") != "0"

# `full`: associations + derived credible sets + attached uploads, all indexed.
# `credible-sets`: attached uploads only; rebuilds just the credible-set indexes.
# Submitted by job_server.variant_sifter.sifter_job_config via the Batch `mode`
# parameter (deploy/cloudformation/variant-sifter-batch.yaml).
MODES = ("full", "credible-sets")


def _raw_prefix(username: str, dataset: str) -> str:
    return f"userdata/{username}/genetic/{dataset}/raw"


def _read_metadata(s3, username: str, dataset: str) -> dict:
    """The DatasetInfo dict written at upload (has col_map, file, separator)."""
    key = f"{_raw_prefix(username, dataset)}/metadata"
    obj = s3.get_object(Bucket=USER_DATA_BUCKET, Key=key)
    return json.loads(obj["Body"].read())


def _iter_rows(s3, username: str, dataset: str, filename: str, sep: str):
    key = f"{_raw_prefix(username, dataset)}/{filename}"
    obj = s3.get_object(Bucket=USER_DATA_BUCKET, Key=key)
    # Uploads are commonly gzipped (e.g. cIMT.for_ldsc.tsv.gz); decompress on the
    # fly so we stream rows rather than buffering the whole file.
    body = obj["Body"]
    stream = gzip.GzipFile(fileobj=body) if filename.endswith(".gz") else body
    text = io.TextIOWrapper(stream, encoding="utf-8")
    yield from csv.DictReader(text, delimiter=sep)


def _build_and_index_associations(s3, meta: dict, username: str, dataset: str,
                                  guid: str, genome) -> list:
    """The associations slice: read, filter, orient, write, index. Returns the records."""
    col_map = meta["col_map"]
    sep = meta.get("separator") or "\t"
    rows = (
        canonicalize(r, col_map)
        for r in _iter_rows(s3, username, dataset, meta["file"], sep)
    )
    # ancestry and effective_n live in the dataset metadata, not the file; the
    # sifter needs ancestry on the records and n is often only known per-dataset.
    records = build_associations(
        rows, guid, p_threshold=P_THRESHOLD,
        ancestry=meta.get("ancestry"), effective_n=meta.get("effective_n"),
    )
    # Orient alleles AFTER the p-value filter: only the survivors are ever
    # queried, and this way the reference lookups scale with the kept records
    # rather than with every row in the upload.
    if genome is not None:
        records, counts = orient_records(records, genome)
        print("allele orientation: "
              + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    # The key must sit under the prefix index_build indexes, so it comes from
    # there rather than being spelled out twice.
    key = associations_key(guid)
    body = "".join(json.dumps(r) + "\n" for r in records)
    s3.put_object(Bucket=GWAS_CE_BUCKET, Key=key, Body=body.encode())
    print(f"wrote {len(records)} associations -> {GWAS_CE_BUCKET}/{key}")

    index_associations(guid)
    print(f"indexed associations into the gwas-ce bioindex as associations-{guid}")
    return records


def run(username: str, dataset: str, guid: str, mode: str = "full") -> int:
    """Build + write + index the dataset's objects for `mode`. Returns the
    number of association records written (0 in credible-sets mode)."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    s3 = boto3.client("s3")
    meta = _read_metadata(s3, username, dataset)
    ancestry = meta.get("ancestry")

    # One reference genome for both associations and uploaded credible sets, so
    # their variant ids agree. None when orientation is switched off.
    genome_cm = ReferenceGenome(ensure_local_reference()) if ORIENT_ALLELES else contextlib.nullcontext()
    with genome_cm as genome:
        n = 0
        if mode == "full":
            records = _build_and_index_associations(s3, meta, username, dataset, guid, genome)
            n = len(records)
            # Derived credible sets are an enhancement (PLINK clumping + ABF, the
            # portal's own recipe): any failure here must not take down the
            # associations the user came for.
            try:
                n_cred = write_derived_credible_sets(
                    s3, GWAS_CE_BUCKET, records, guid, dataset=dataset, ancestry=ancestry)
                print(f"wrote {n_cred} derived credible-set variants for {guid}")
            except Exception as exc:
                print(f"WARNING: credible-set derivation failed; "
                      f"associations are unaffected: {exc}")

        # Uploaded sets are the user's own data, validated at upload time: a
        # failure here is a bug and must fail the job rather than vanish.
        counts = sync_uploaded_credible_sets(
            s3, USER_DATA_BUCKET, GWAS_CE_BUCKET, username, dataset, guid,
            ancestry=ancestry, genome=genome)
        print(f"synced uploaded credible sets: {counts}")

    # One index build per credible-set index, after every writer has run.
    index_credible_variants(guid)
    index_credible_sets(guid)
    print(f"indexed credible-variants-{guid} / credible-sets-{guid}")
    return n


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="variant-sifter-run")
    p.add_argument("--username", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--guid", required=True)
    p.add_argument("--mode", choices=MODES, default="full")
    args = p.parse_args(argv)
    run(args.username, args.dataset, args.guid, mode=args.mode)


if __name__ == "__main__":
    main()
