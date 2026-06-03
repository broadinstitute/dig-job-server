"""Populate the local dev DB from the real S3 bucket.

One-way and idempotent: reads dataset metadata + GWAS files out of S3
(`dig-ldsc-server`) and upserts `users` + `datasets` rows into the local
docker MySQL, so a developer can drive real datasets against a locally-run
API (notably the FALCON CLI installer flow).

Manual command only — never wired into app startup. Run via:

    python -m job_server.sync_from_s3 [--user U ...] [--dataset D] \\
        [--recompute-sha] [--dry-run] [--i-know-its-not-local]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from urllib.parse import urlparse

import bcrypt
import boto3
from botocore.exceptions import ClientError
from sqlalchemy import text

from job_server import database, s3
from job_server.database import get_db
from job_server.database_utils import (
    get_dataset_gwas_sha256,
    get_dataset_hash,
    set_dataset_gwas_sha256,
)

log = logging.getLogger(__name__)

DEV_PASSWORD_ENV = "SYNC_DEV_PASSWORD"
DEFAULT_DEV_PASSWORD = "falcon-dev"
USERDATA_PREFIX = "userdata/"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


class NonLocalDatabaseError(RuntimeError):
    """Raised when the configured DB is not local and no override was given."""


@dataclass
class SyncReport:
    users_inserted: int = 0
    users_skipped: int = 0
    datasets_inserted: int = 0
    datasets_updated: int = 0
    datasets_skipped: int = 0
    sha_computed: int = 0
    sha_skipped: int = 0
    sha_failed: int = 0

    def summary(self) -> str:
        return (
            f"users: +{self.users_inserted} ({self.users_skipped} existing) | "
            f"datasets: +{self.datasets_inserted} ~{self.datasets_updated} "
            f"({self.datasets_skipped} skipped) | "
            f"sha256: {self.sha_computed} computed, {self.sha_skipped} skipped, "
            f"{self.sha_failed} failed"
        )


def _dev_password() -> str:
    return os.environ.get(DEV_PASSWORD_ENV, DEFAULT_DEV_PASSWORD)


def _assert_local_db(allow_nonlocal_db: bool) -> None:
    url = os.environ.get("DIG_JOB_SERVER_DB") or database.SQLALCHEMY_DATABASE_URL
    host = (urlparse(url).hostname or "")
    if host in _LOCAL_HOSTS:
        return
    if allow_nonlocal_db:
        log.warning("DIG_JOB_SERVER_DB host %r is not local; proceeding due to override", host)
        return
    raise NonLocalDatabaseError(
        f"refusing to write: DIG_JOB_SERVER_DB host {host!r} is not local. "
        "This command writes to the DB while reading the real S3 bucket. "
        "Pass --i-know-its-not-local to override."
    )


def _list_user_names(client) -> list[str]:
    """Return the usernames that have a userdata/ prefix in the bucket.

    Capped at 1,000 results; pagination is not implemented (dev tool only).
    """
    resp = client.list_objects_v2(
        Bucket=s3.BUCKET_NAME, Prefix=USERDATA_PREFIX, Delimiter="/"
    )
    names = []
    for cp in resp.get("CommonPrefixes", []):
        names.append(cp["Prefix"][len(USERDATA_PREFIX):].rstrip("/"))
    return names


def _read_metadata(client, user: str, name: str) -> dict | None:
    """Return the parsed dataset metadata object, or None if absent/unparseable."""
    key = f"{s3.get_gwas_s3_key(user, name)}/metadata"
    try:
        obj = client.get_object(Bucket=s3.BUCKET_NAME, Key=key)
    except ClientError:
        return None
    body = obj["Body"]
    try:
        return json.loads(body.read())
    except (ValueError, KeyError):
        return None
    finally:
        body.close()


def _upsert_user(username: str, pw_hash: str, dry_run: bool) -> str:
    """Insert a users row (password set only on insert). Returns 'inserted'|'skipped'."""
    with get_db() as con:
        exists = con.execute(
            text("SELECT 1 FROM users WHERE user_name = :u"), {"u": username}
        ).first()
        if exists:
            return "skipped"
        if not dry_run:
            con.execute(
                text("INSERT INTO users (user_name, password, created_at) "
                     "VALUES (:u, :pw, NOW())"),
                {"u": username, "pw": pw_hash},
            )
            con.commit()
        return "inserted"


def _upsert_dataset(username: str, metadata_json: str, name: str, dry_run: bool) -> str:
    """Insert/update a datasets row from S3 metadata. Returns 'inserted'|'updated'."""
    ds_id = get_dataset_hash(name, username)
    with get_db() as con:
        exists = con.execute(
            text("SELECT 1 FROM datasets WHERE id = :id"), {"id": ds_id}
        ).first()
        if exists:
            if not dry_run:
                con.execute(
                    text("UPDATE datasets SET uploaded_by = :u, metadata = :m WHERE id = :id"),
                    {"u": username, "m": metadata_json, "id": ds_id},
                )
                con.commit()
            return "updated"
        if not dry_run:
            con.execute(
                text("INSERT INTO datasets (id, uploaded_by, metadata, uploaded_at) "
                     "VALUES (:id, :u, :m, NOW())"),
                {"id": ds_id, "u": username, "m": metadata_json},
            )
            con.commit()
        return "inserted"


def sync(
    users: list[str] | None = None,
    dataset: str | None = None,
    *,
    recompute_sha: bool = False,
    dry_run: bool = False,
    allow_nonlocal_db: bool = False,
) -> SyncReport:
    """Read S3 and upsert users + datasets (incl. gwas_sha256) into the local DB."""
    _assert_local_db(allow_nonlocal_db)
    report = SyncReport()
    client = boto3.client("s3")
    pw_hash = bcrypt.hashpw(_dev_password().encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    user_names = users if users is not None else _list_user_names(client)
    for user in user_names:
        if _upsert_user(user, pw_hash, dry_run) == "inserted":
            report.users_inserted += 1
        else:
            report.users_skipped += 1

        names = [dataset] if dataset else s3.get_datasets(user)
        for name in names:
            meta = _read_metadata(client, user, name)
            if not meta or "name" not in meta or "file" not in meta:
                log.warning("no usable metadata for %s/%s; skipping", user, name)
                report.datasets_skipped += 1
                continue

            meta_name = meta["name"]
            if _upsert_dataset(user, json.dumps(meta), meta_name, dry_run) == "inserted":
                report.datasets_inserted += 1
            else:
                report.datasets_updated += 1

            existing = get_dataset_gwas_sha256(get_db(), user, meta_name)
            if existing and not recompute_sha:
                report.sha_skipped += 1
                continue
            if dry_run:
                report.sha_computed += 1  # would compute
                continue

            # GWAS file lives under the S3 folder we read metadata from (`name`);
            # name == meta["name"] in practice, but the folder is authoritative for S3.
            gwas_key = s3.get_gwas_s3_key(user, name, meta["file"])
            try:
                sha = s3.compute_object_sha256(gwas_key)
            except ClientError:
                log.warning("could not hash GWAS at %s; gwas_sha256 left NULL", gwas_key)
                report.sha_failed += 1
                continue
            set_dataset_gwas_sha256(get_db(), user, meta_name, sha)
            report.sha_computed += 1

    return report


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        prog="python -m job_server.sync_from_s3",
        description="Sync the local dev DB from the real S3 bucket (one-way).",
    )
    parser.add_argument("--user", action="append", dest="users",
                        help="sync only this user (repeatable)")
    parser.add_argument("--dataset", help="sync only this dataset (requires exactly one --user)")
    parser.add_argument("--recompute-sha", action="store_true",
                        help="re-hash GWAS even if gwas_sha256 is already set")
    parser.add_argument("--dry-run", action="store_true", help="log planned changes, write nothing")
    parser.add_argument("--i-know-its-not-local", action="store_true", dest="allow_nonlocal_db",
                        help="bypass the localhost safety guard")
    args = parser.parse_args(argv)

    if args.dataset and (not args.users or len(args.users) != 1):
        parser.error("--dataset requires exactly one --user")

    try:
        report = sync(
            users=args.users,
            dataset=args.dataset,
            recompute_sha=args.recompute_sha,
            dry_run=args.dry_run,
            allow_nonlocal_db=args.allow_nonlocal_db,
        )
    except NonLocalDatabaseError as exc:
        log.error("%s", exc)
        return 2

    log.info("%s%s", "[dry-run] " if args.dry_run else "", report.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
