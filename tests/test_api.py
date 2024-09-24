from unittest.mock import patch

from starlette.testclient import TestClient


def test_foo(api_client: TestClient):
    res = api_client.post("/api/login", json={"username": "testuser@broadinstitute.org", "password": "change.me"})
    assert res.status_code == 200


def test_file_upload_success(api_client: TestClient):
    with patch("job_server.api.s3.get_bucket_path") as mock_get_bucket_path:
        mock_get_bucket_path.return_value = "s3://mocked_bucket/ldscore/uploads/testfile.gz"
        files = {'file': ('testfile.gz', b'file_content')}
        headers = {'Filename': 'testfile.gz'}
        res = api_client.post("/api/upload", files=files, headers=headers)
        assert res.status_code == 200
        assert res.json() == {"file_size": len(b'file_content'), "s3_path": "s3://mocked_bucket/ldscore/uploads/testfile.gz"}

def test_file_upload_no_filename(api_client: TestClient):
    files = {'file': ('testfile.gz', b'file_content')}
    res = api_client.post("/api/upload", files=files)
    assert res.status_code == 422

def test_file_upload_empty_file(api_client: TestClient):
    with patch("job_server.api.s3.get_bucket_path") as mock_get_bucket_path:
        mock_get_bucket_path.return_value = "s3://mocked_bucket/ldscore/uploads/testfile.gz"
        files = {'file': ('testfile.gz', b'')}
        headers = {'Filename': 'testfile.gz'}
        res = api_client.post("/api/upload", files=files, headers=headers)
        assert res.status_code == 200
        assert res.json() == {"file_size": 0, "s3_path": "s3://mocked_bucket/ldscore/uploads/testfile.gz"}
