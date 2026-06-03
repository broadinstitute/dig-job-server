import boto3
import pytest
from moto import mock_aws

from job_server import falcon_tokens
from tests.fixtures import seed_dataset
from tests.test_api import get_token


BUCKET = "dig-ldsc-server"


@pytest.fixture
def auth_token(api_client):
    return get_token(api_client)


@mock_aws
def test_upload_urls_with_token(api_client):
    boto3.resource("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
    seed_dataset("ds1", username="testuser")
    token, _ = falcon_tokens.mint(1, "ds1")
    res = api_client.post(
        "/api/falcon/ds1/upload-urls",
        json={"files": [{"name": "results.tar.gz", "size": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "uploads" in res.json()
    assert res.json()["uploads"][0]["name"] == "results.tar.gz"


@mock_aws
def test_upload_urls_token_wrong_dataset_rejected(api_client):
    boto3.resource("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
    seed_dataset("ds1", username="testuser")
    seed_dataset("ds2", username="testuser")
    token, _ = falcon_tokens.mint(1, "ds1")
    res = api_client.post(
        "/api/falcon/ds2/upload-urls",
        json={"files": [{"name": "results.tar.gz", "size": 1}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


@mock_aws
def test_upload_urls_session_still_works(api_client, auth_token):
    boto3.resource("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
    seed_dataset("ds1", username="testuser")
    res = api_client.post(
        "/api/falcon/ds1/upload-urls",
        json={"files": [{"name": "results.tar.gz", "size": 1}]},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 200
