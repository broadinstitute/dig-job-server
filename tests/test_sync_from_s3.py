import hashlib
import json

import boto3
from moto import mock_aws
from sqlalchemy import text

from job_server import s3, sync_from_s3
from job_server.database import get_db
from job_server.database_utils import (
    authenticate_user,
    get_dataset_gwas_sha256,
    get_dataset_hash,
    set_dataset_gwas_sha256,
)

BUCKET = s3.BUCKET_NAME
GWAS_BODY = b"chr\tpos\tpval\n1\t100\t0.5\n"
GWAS_SHA = hashlib.sha256(GWAS_BODY).hexdigest()


def _client():
    return boto3.client("s3", region_name="us-east-1")


def _seed(client, user, name, file="gwas.tsv", body=GWAS_BODY, with_gwas=True):
    meta = {
        "name": name, "file": file, "ancestry": "EUR", "separator": "\t",
        "genome_build": "GRCh38", "phenotype": None, "effective_n": None, "col_map": {},
    }
    base = s3.get_gwas_s3_key(user, name)
    client.put_object(Bucket=BUCKET, Key=f"{base}/metadata", Body=json.dumps(meta).encode())
    if with_gwas:
        client.put_object(Bucket=BUCKET, Key=f"{base}/{file}", Body=body)


@mock_aws
def test_happy_path(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")

    report = sync_from_s3.sync()

    assert report.users_inserted == 1
    assert report.datasets_inserted == 1
    assert report.sha_computed == 1
    ds_id = get_dataset_hash("ds1", "alice")
    with get_db() as con:
        row = con.execute(
            text("SELECT uploaded_by, gwas_sha256, metadata->>'$.name' FROM datasets WHERE id=:id"),
            {"id": ds_id},
        ).first()
    assert row[0] == "alice"
    assert row[1] == GWAS_SHA
    assert row[2] == "ds1"


@mock_aws
def test_user_can_log_in_with_dev_password(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")
    sync_from_s3.sync()
    assert authenticate_user(get_db(), "alice", "falcon-dev") is True


@mock_aws
def test_idempotent_rerun(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")
    sync_from_s3.sync()
    report = sync_from_s3.sync()
    assert report.users_skipped == 1
    assert report.users_inserted == 0
    assert report.datasets_updated == 1
    assert report.datasets_inserted == 0
    assert report.sha_skipped == 1
    assert report.sha_computed == 0


@mock_aws
def test_filters_to_one_user_and_dataset(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")
    _seed(client, "alice", "ds2")
    _seed(client, "bob", "ds9")
    report = sync_from_s3.sync(users=["alice"], dataset="ds1")
    assert report.users_inserted == 1
    assert report.datasets_inserted == 1
    with get_db() as con:
        n = con.execute(text("SELECT COUNT(*) FROM datasets")).scalar()
    assert n == 1


@mock_aws
def test_missing_metadata_is_skipped(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    client.put_object(Bucket=BUCKET, Key="userdata/alice/genetic/ds1/raw/gwas.tsv", Body=GWAS_BODY)
    report = sync_from_s3.sync(users=["alice"])
    assert report.datasets_skipped == 1
    assert report.datasets_inserted == 0


@mock_aws
def test_missing_gwas_leaves_sha_null(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1", with_gwas=False)
    report = sync_from_s3.sync(users=["alice"])
    assert report.datasets_inserted == 1
    assert report.sha_failed == 1
    assert get_dataset_gwas_sha256(get_db(), "alice", "ds1") is None


@mock_aws
def test_dry_run_writes_nothing(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")
    report = sync_from_s3.sync(users=["alice"], dry_run=True)
    # dry-run returns "inserted"/"updated" to report would-be changes; no rows written
    assert report.users_inserted == 1
    assert report.datasets_inserted == 1
    with get_db() as con:
        assert con.execute(text("SELECT COUNT(*) FROM datasets")).scalar() == 0
        assert con.execute(text("SELECT 1 FROM users WHERE user_name='alice'")).first() is None


@mock_aws
def test_recompute_sha_overwrites_existing(api_client):
    client = _client(); client.create_bucket(Bucket=BUCKET)
    _seed(client, "alice", "ds1")
    sync_from_s3.sync(users=["alice"])  # first sync sets the correct sha
    # Simulate a stale/wrong stored hash.
    set_dataset_gwas_sha256(get_db(), "alice", "ds1", "0" * 64)

    report = sync_from_s3.sync(users=["alice"], recompute_sha=True)

    assert report.sha_computed == 1
    assert report.sha_skipped == 0
    assert get_dataset_gwas_sha256(get_db(), "alice", "ds1") == GWAS_SHA
