"""Shared helpers for tests that need a real seeded dataset.

The `datasets` table uses a content-derived hash as its PK
(`database_utils.get_dataset_hash`), and stores the user-friendly name +
original GWAS filename inside a JSON `metadata` column. Tests that exercise
endpoints which look up datasets by name need to seed via this helper so
the hash convention matches the production code path.
"""
from __future__ import annotations

import json

from sqlalchemy import text

from job_server.database import get_db
from job_server.database_utils import get_dataset_hash


def seed_dataset(
    name: str,
    username: str = "testuser",
    gwas_sha256: str | None = None,
    gwas_filename: str = "gwas.tsv",
    col_map: dict | None = None,
) -> str:
    """Insert a row into `datasets` and return the computed dataset id (hash)."""
    dataset_id = get_dataset_hash(name, username)
    metadata = {"name": name, "file": gwas_filename}
    if col_map is not None:
        metadata["col_map"] = col_map
    with get_db() as con:
        con.execute(text(
            "INSERT INTO datasets (id, uploaded_by, metadata, gwas_sha256, uploaded_at) "
            "VALUES (:id, :user, :meta, :sha, NOW())"
        ), {
            "id": dataset_id,
            "user": username,
            "meta": json.dumps(metadata),
            "sha": gwas_sha256,
        })
        con.commit()
    return dataset_id
