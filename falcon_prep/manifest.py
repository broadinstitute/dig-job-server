"""Emit the manifest dig-job-server already validates for local FALCON runs.

Cloud execution coexists with the local flow rather than replacing it, so it
produces the same artifacts. `job_server/falcon.py::validate_manifest` checks
schema_version, the required fields, dataset_name, and input_sha256 against the
dataset's stored gwas_sha256.

SCHEMA_VERSION is imported from that module rather than redeclared, so producer
and validator cannot drift. job_server/falcon.py is stdlib-only, which is why
the container can carry that one file without the rest of the web app.
"""
from __future__ import annotations

import hashlib

from job_server.falcon import SCHEMA_VERSION
_CHUNK = 1024 * 1024


def sha256_file(path: str) -> str:
    """SHA-256 of a file, streamed so a 1 GB upload does not land in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    dataset_name: str,
    falcon_version: str,
    input_path: str,
    input_filename: str,
    split_chromosomes: list[int],
    out_base_name: str,
    prep_summary: dict,
) -> dict:
    """Build a schema-v1 manifest binding this run to the dataset's GWAS file."""
    return {
        "schema_version": SCHEMA_VERSION,
        "falcon_version": falcon_version,
        "dataset_name": dataset_name,
        # Hash the bytes actually read -- that is what makes the binding mean
        # anything. Never copy a sha through from metadata.
        "input_sha256": sha256_file(input_path),
        "input_filename": input_filename,
        "split_chromosomes": list(split_chromosomes),
        "out_base_name": out_base_name,
        # Non-schema provenance. validate_manifest ignores unknown keys.
        "falcon": {
            "engine": "falcon-rs",
            "z_threshold": prep_summary.get("z_threshold"),
            "rsid_column": prep_summary.get("rsid_column"),
            "rsid_resolution_rate": prep_summary.get("resolution_rate"),
            "counts": prep_summary.get("counts", {}),
            "chromosomes": prep_summary.get("chromosomes", {}),
        },
    }
