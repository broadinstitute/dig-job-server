import boto3
import pytest
from moto import mock_aws
from starlette.testclient import TestClient

BUCKET = "dig-ldsc-server"
USER = "testuser"


def test_login(api_client: TestClient):
    res = api_client.post("/api/login", json={"username": f"{USER}", "password": "change.me"})
    assert res.status_code == 200
    assert "access_token" in res.json()
    return res.json()["access_token"]

@pytest.fixture
def auth_token(api_client: TestClient):
    return test_login(api_client)

def set_up_moto_bucket():
    # We need to create the bucket since this is all in Moto's 'virtual' AWS account
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="dig-ldsc-server")

@mock_aws
def test_file_upload_success(api_client: TestClient, auth_token: str):
    set_up_moto_bucket()
    files = {'file': ('testfile.gz', b'file_content')}
    headers = {'Filename': 'testfile.gz', 'Authorization': f"Bearer {auth_token}"}
    res = api_client.post("/api/upload", files=files, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"s3_path": f"s3://{BUCKET}/userdata/{USER}/testfile.gz"}

@mock_aws
def test_file_upload_no_filename(api_client: TestClient, auth_token: str):
    set_up_moto_bucket()
    files = {'file': ('testfile.gz', b'file_content')}
    headers = {'Authorization': f"Bearer {auth_token}"}
    res = api_client.post("/api/upload", files=files, headers=headers)
    assert res.status_code == 422

@mock_aws
def test_file_upload_empty_file(api_client: TestClient, auth_token: str):
    set_up_moto_bucket()
    files = {'file': ('testfile.gz', b'')}
    headers = {'Filename': 'testfile.gz', 'Authorization': f"Bearer {auth_token}"}
    res = api_client.post("/api/upload", files=files, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"s3_path": f"s3://{BUCKET}/userdata/{USER}/testfile.gz"}
