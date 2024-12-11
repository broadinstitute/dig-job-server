import io
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws
from starlette.testclient import TestClient

BUCKET = "dig-ldsc-server"
USER = "testuser"


def get_token(api_client: TestClient):
    res = api_client.post("/api/login", json={"username": f"{USER}", "password": "change.me"})
    assert res.status_code == 200
    assert "access_token" in res.json()
    return res.json()["access_token"]

@pytest.fixture
def auth_token(api_client: TestClient):
    return get_token(api_client)

def set_up_moto_bucket():
    # We need to create the bucket since this is all in Moto's 'virtual' AWS account
    conn = boto3.resource("s3", region_name="us-east-1")
    conn.create_bucket(Bucket=BUCKET)

def test_bad_login(api_client: TestClient):
    res = api_client.post("/api/login", json={"username": "testuser", "password": "badpassword"})
    assert res.status_code == 403

def test_is_logged_in(api_client: TestClient, auth_token: str):
    res = api_client.get("/api/is-logged-in")
    assert res.status_code == 401
    res = api_client.get("/api/is-logged-in", headers={"Authorization": f"Bearer {auth_token}"})
    assert res.status_code == 200

def test_preview_csv(api_client: TestClient, auth_token: str):
    csv_content = "col1,col2,col3\n1,2,3\n4,5,6"
    csv_file = io.BytesIO(csv_content.encode())
    files = {"file": ("test.csv", csv_file, "text/csv")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": ","
    }

def test_preview_tsv(api_client: TestClient, auth_token: str):
    tsv_content = "col1\tcol2\tcol3\n1\t2\t3\n4\t5\t6"
    tsv_file = io.BytesIO(tsv_content.encode())
    files = {"file": ("test.tsv", tsv_file, "text/tab-separated-values")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": "\t"
    }

def test_duplicate_columns(api_client: TestClient, auth_token: str):
    csv_content_dupes = "col1,col1,col2\n1,2,3"
    csv_file_dupes = io.BytesIO(csv_content_dupes.encode())
    files = {"file": ("test.csv", csv_file_dupes, "text/csv")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 400
    assert response.json()["detail"] == "col1 specified more than once"

def test_gzip_csv(api_client: TestClient, auth_token: str):
    import gzip
    csv_content = "col1,col2,col3\n1,2,3\n4,5,6"
    gzipped_content = gzip.compress(csv_content.encode())
    gz_file = io.BytesIO(gzipped_content)
    files = {"file": ("test.csv.gz", gz_file, "application/gzip")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {get_token(api_client)}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": ","
    }

@mock_aws
def test_generate_presigned_url_success(api_client: TestClient, auth_token: str):
    mock_url = "https://fake-presigned-url.com/test"

    with patch('boto3.client') as mock_client:
        # Configure the mock
        mock_s3 = mock_client.return_value
        mock_s3.generate_presigned_url.return_value = mock_url
        response = api_client.get("/api/get-pre-signed-url/test-ds",
                                   headers={"Authorization": f"Bearer {auth_token}"})

        assert response.status_code == 200
        result = response.json()
        assert "test-ds" in result["s3_path"]
        assert mock_url == result["presigned_url"]
        mock_s3.generate_presigned_url.assert_called_once()


@mock_aws
def test_generate_presigned_url_failure(api_client: TestClient, auth_token: str):
    with patch('boto3.client') as mock_client:
        mock_s3 = mock_client.return_value
        mock_s3.generate_presigned_url.side_effect = ClientError(
            {'Error': {'Code': 'InvalidRequest', 'Message': 'Test error'}},
            'generate_presigned_url'
        )

        response = api_client.get("/api/get-pre-signed-url/test-ds",
                                   headers={"Authorization": f"Bearer {auth_token}"})
        assert response.status_code == 500
