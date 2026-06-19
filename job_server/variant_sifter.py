"""Pure helpers for the GWAS-CE Variant Sifter feature.

FastAPI-free so they unit-test without the app/DB. Mirrors job_server/falcon.py:
feature logic lives here; HTTP routes stay in job_server/api.py.
"""

# Tracked as a workflow_jobs `method` (no hash prefix) so it surfaces alongside
# the other per-dataset workflows.
SIFTER_METHOD = "variant-sifter"


def build_sifter_url(base_url: str, guid: str, region: str | None = None) -> str:
    """Launch URL for the embedded research.html sifter, scoped to one dataset."""
    url = (
        f"{base_url.rstrip('/')}/research.html"
        f"?pageid=kp_variant_sifter&phenotype={guid}"
    )
    if region:
        url += f"&region={region}"
    return url


def sifter_job_config(username: str, dataset: str, guid: str) -> dict:
    """AWS Batch submit_job kwargs for the variant-sifter prep pipeline."""
    return {
        "jobName": "gwas-ce-variant-sifter",
        "jobQueue": "gwas-ce-variant-sifter-job-queue",
        "jobDefinition": "gwas-ce-variant-sifter",
        "parameters": {
            "username": username,
            "dataset": dataset,
            "guid": guid,
        },
    }
