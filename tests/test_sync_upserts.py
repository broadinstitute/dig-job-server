import json

import bcrypt
from sqlalchemy import text

from job_server import sync_from_s3
from job_server.database import get_db
from job_server.database_utils import get_dataset_hash


def _pw_hash():
    return bcrypt.hashpw(b"falcon-dev", bcrypt.gensalt()).decode()


def test_upsert_user_inserts_then_skips(api_client):
    h = _pw_hash()
    assert sync_from_s3._upsert_user("alice", h, dry_run=False) == "inserted"
    assert sync_from_s3._upsert_user("alice", h, dry_run=False) == "skipped"
    with get_db() as con:
        row = con.execute(text("SELECT user_name FROM users WHERE user_name='alice'")).first()
    assert row is not None


def test_upsert_user_dry_run_does_not_write(api_client):
    assert sync_from_s3._upsert_user("ghost", _pw_hash(), dry_run=True) == "inserted"
    with get_db() as con:
        row = con.execute(text("SELECT 1 FROM users WHERE user_name='ghost'")).first()
    assert row is None


def test_upsert_dataset_inserts_then_updates(api_client):
    meta = json.dumps({"name": "ds1", "file": "gwas.tsv"})
    assert sync_from_s3._upsert_dataset("alice", meta, "ds1", dry_run=False) == "inserted"
    meta2 = json.dumps({"name": "ds1", "file": "gwas2.tsv"})
    assert sync_from_s3._upsert_dataset("alice", meta2, "ds1", dry_run=False) == "updated"
    ds_id = get_dataset_hash("ds1", "alice")
    with get_db() as con:
        row = con.execute(
            text("SELECT uploaded_by, metadata->>'$.file' FROM datasets WHERE id=:id"),
            {"id": ds_id},
        ).first()
    assert row[0] == "alice"
    assert row[1] == "gwas2.tsv"
