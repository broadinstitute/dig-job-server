"""Pure helpers for user-uploaded credible sets.

FastAPI-free so they unit-test without the app (mirrors job_server/variant_sifter.py):
feature logic lives here; HTTP routes stay in job_server/api.py.
"""

import re
from datetime import datetime

from job_server.variant_sifter import SIFTER_METHOD

# Tracked as a workflow_jobs `method` under the dataset's id, beside `variant-sifter`.
CREDIBLE_SETS_METHOD = "credible-sets"
# Both of these jobs ingest every attached upload, so either one's success
# after an upload means the upload is indexed.
INGEST_METHODS = (CREDIBLE_SETS_METHOD, SIFTER_METHOD)

NAME_MAX_LEN = 30
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Key-safe form of a display name: lowercase [a-z0-9-], non-empty.

    Used in S3 keys, bioindex object names and namespaced credibleSetIds, so it
    must never contain '/', ':' or ','.
    """
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise ValueError("name must contain at least one letter or digit")
    return slug[:NAME_MAX_LEN].rstrip("-")


def validate_name(name: str) -> str:
    """The trimmed display name, or ValueError with a user-facing message."""
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    if len(name) > NAME_MAX_LEN:
        raise ValueError(f"name must be at most {NAME_MAX_LEN} characters")
    slugify(name)  # raises when the name has no letter or digit
    return name


def derive_status(uploaded_at: datetime, jobs: "list[dict]") -> str:
    """One of pending | indexing | indexed | failed for an upload made at
    `uploaded_at`, given the dataset's workflow_jobs rows
    ({"method", "status", "updated_at"}; other methods are ignored).

    Both timestamps come from MySQL NOW() so they compare directly.
    """
    relevant = [j for j in jobs if j["method"] in INGEST_METHODS]
    if any(j["status"] == "RUNNING" for j in relevant):
        return "indexing"
    if any(j["status"] == "SUCCEEDED" and j["updated_at"] >= uploaded_at for j in relevant):
        return "indexed"
    latest = max(relevant, key=lambda j: j["updated_at"], default=None)
    if latest and latest["status"] == "FAILED" and latest["updated_at"] >= uploaded_at:
        return "failed"
    return "pending"


def jobs_from_workflows(workflows: dict) -> "list[dict]":
    """Flatten database_utils.get_workflow_jobs_for_user's per-dataset value
    ({method: {method: {status, updated_at}}}) into derive_status's job list."""
    return [
        {"method": method, "status": inner[method]["status"], "updated_at": inner[method]["updated_at"]}
        for method, inner in workflows.items()
        if method in inner
    ]


def records_with_status(rows: "list[dict]", jobs: "list[dict]") -> "list[dict]":
    """Copy each credible_sets row and add its derived `status`."""
    return [{**row, "status": derive_status(row["uploaded_at"], jobs)} for row in rows]
