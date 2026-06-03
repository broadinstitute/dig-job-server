import json

import boto3
from moto import mock_aws

from job_server import s3, sync_from_s3

BUCKET = s3.BUCKET_NAME


def _client():
    return boto3.client("s3", region_name="us-east-1")


def _seed_metadata(client, user, name, file="gwas.tsv"):
    meta = {
        "name": name, "file": file, "ancestry": "EUR", "separator": "\t",
        "genome_build": "GRCh38", "phenotype": None, "effective_n": None, "col_map": {},
    }
    base = s3.get_gwas_s3_key(user, name)  # userdata/{user}/genetic/{name}/raw
    client.put_object(Bucket=BUCKET, Key=f"{base}/metadata", Body=json.dumps(meta).encode())
    return meta


@mock_aws
def test_list_user_names():
    client = _client()
    client.create_bucket(Bucket=BUCKET)
    _seed_metadata(client, "alice", "ds1")
    _seed_metadata(client, "bob", "ds9")
    assert sorted(sync_from_s3._list_user_names(client)) == ["alice", "bob"]


@mock_aws
def test_read_metadata_present():
    client = _client()
    client.create_bucket(Bucket=BUCKET)
    meta = _seed_metadata(client, "alice", "ds1")
    assert sync_from_s3._read_metadata(client, "alice", "ds1") == meta


@mock_aws
def test_read_metadata_absent_returns_none():
    client = _client()
    client.create_bucket(Bucket=BUCKET)
    assert sync_from_s3._read_metadata(client, "alice", "ghost") is None
