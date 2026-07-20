"""Orchestrator entrypoint for the `gwas-ce-variant-sifter` Batch job.

Reads one uploaded GWAS, builds the p-value-filtered `associations` records for
that dataset, writes them to the gwas-ce bucket keyed by GUID, and indexes them
in-process. Plan 1's API submits this via sifter_job_config:

    python -m variant_sifter_pipeline.run --username U --dataset D --guid G

First slice = associations only. Harmonization/liftover and VEP annotation are
deferred (see the design spec); this assumes the upload is already on the
reference build.
"""

import argparse
import csv
import gzip
import io
import json
import os

import boto3

from .associations import build_associations
from .canonicalize import canonicalize
from .index_build import index_associations

# Where GWAS-CE stores user uploads (same default as job_server.s3).
USER_DATA_BUCKET = os.getenv("JOB_SERVER_BUCKET", "dig-ldsc-server")
# The gwas-ce bioindex bucket (also read by bioindex via BIOINDEX_S3_BUCKET).
GWAS_CE_BUCKET = os.getenv("BIOINDEX_S3_BUCKET", "dig-gwas-ce-bioindex")
P_THRESHOLD = float(os.getenv("VS_P_THRESHOLD", "0.05"))


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


def run(username: str, dataset: str, guid: str) -> int:
    """Build + write + index the dataset's associations. Returns record count."""
    s3 = boto3.client("s3")
    meta = _read_metadata(s3, username, dataset)
    col_map = meta["col_map"]
    sep = meta.get("separator") or "\t"

    rows = (
        canonicalize(r, col_map)
        for r in _iter_rows(s3, username, dataset, meta["file"], sep)
    )
    records = build_associations(rows, guid, p_threshold=P_THRESHOLD)

    body = "".join(json.dumps(r) + "\n" for r in records)
    s3.put_object(
        Bucket=GWAS_CE_BUCKET, Key=f"associations/{guid}.json", Body=body.encode(),
    )
    print(f"wrote {len(records)} associations -> {GWAS_CE_BUCKET}/associations/{guid}.json")

    index_associations()
    print("indexed associations into the gwas-ce bioindex")
    return len(records)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="variant-sifter-run")
    p.add_argument("--username", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--guid", required=True)
    args = p.parse_args(argv)
    run(args.username, args.dataset, args.guid)


if __name__ == "__main__":
    main()
