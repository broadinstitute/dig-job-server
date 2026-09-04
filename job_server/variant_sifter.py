"""Pure helpers for the GWAS-CE Variant Sifter feature.

FastAPI-free so they unit-test without the app/DB. Mirrors job_server/falcon.py:
feature logic lives here; HTTP routes stay in job_server/api.py.
"""

# Tracked as a workflow_jobs `method` (no hash prefix) so it surfaces alongside
# the other per-dataset workflows.
SIFTER_METHOD = "variant-sifter"

# Served unauthenticated to any holder of the GUID, so this is an allow-list,
# not a convenience projection. The dataset name and the uploader are excluded
# deliberately: the GUID is sha256("<dataset>-<username>"), so anyone who can
# derive it already knows those two strings, and echoing them back would confirm
# the guess. Widening this publishes whatever is added, to everyone.
PUBLIC_METADATA_FIELDS = ("phenotype", "ancestry", "genome_build")


def public_dataset_metadata(metadata: dict) -> dict:
    """Project a stored DatasetInfo dict down to the publicly served fields.

    `.get` rather than `[]` so the response shape is fixed regardless of what an
    older row happens to carry -- a missing field serves null instead of 500ing.
    """
    return {field: metadata.get(field) for field in PUBLIC_METADATA_FIELDS}


def build_sifter_url(base_url: str, guid: str, region: str | None = None) -> str:
    """Launch URL for the embedded research.html sifter, scoped to one dataset."""
    url = (
        f"{base_url.rstrip('/')}/research.html"
        f"?pageid=kp_variant_sifter&phenotype={guid}"
    )
    if region:
        url += f"&region={region}"
    return url


# `full` = associations + derived credible sets + every attached upload;
# `credible-sets` = attached uploads only, rebuilding just the two credible-set
# indexes. Both run the same job definition; the mode is a Batch parameter.
SIFTER_MODES = ("full", "credible-sets")


def sifter_job_config(username: str, dataset: str, guid: str, mode: str = "full") -> dict:
    """AWS Batch submit_job kwargs for the variant-sifter prep pipeline.

    Submitted onto the shared `indexer-job-queue` (its compute env reaches the
    aurora-giant-bioindex cluster); the job definition + IAM role are declared in
    deploy/cloudformation/variant-sifter-batch.yaml, whose Command passes
    `--mode Ref::mode`.
    """
    if mode not in SIFTER_MODES:
        raise ValueError(f"unknown sifter mode {mode!r}")
    return {
        "jobName": "gwas-ce-variant-sifter" if mode == "full" else "gwas-ce-credible-sets",
        "jobQueue": "indexer-job-queue",
        "jobDefinition": "gwas-ce-variant-sifter",
        "parameters": {
            "username": username,
            "dataset": dataset,
            "guid": guid,
            "mode": mode,
        },
    }
