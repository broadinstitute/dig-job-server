import json
import boto3
from moto import mock_aws

from job_server import falcon_tokens, s3 as s3mod
from tests.fixtures import seed_dataset


BUCKET = "dig-ldsc-server"


def _put_manifest(s3_client, key):
    manifest = {
        "schema_version": 1,
        "falcon_version": "x",
        "dataset_name": "ds1",
        "input_sha256": "a" * 64,
        "input_filename": "gwas.tsv",
        "split_chromosomes": [22],
        "out_base_name": "results/run1",
    }
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(manifest).encode())


@mock_aws
def test_finalize_with_token(api_client):
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=BUCKET)
    seed_dataset("ds1", username="testuser", gwas_sha256="a" * 64)
    s3_client = boto3.client("s3", region_name="us-east-1")
    key = s3mod.get_falcon_s3_prefix("testuser", "ds1", "manifest.json")
    _put_manifest(s3_client, key)

    token, _ = falcon_tokens.mint(1, "ds1")
    res = api_client.post(
        "/api/falcon/ds1/finalize",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
