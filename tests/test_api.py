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

def test_preview_any_extension_csv(api_client: TestClient, auth_token: str):
    """Test that .txt file with CSV content is accepted"""
    csv_content = "col1,col2,col3\n1,2,3\n4,5,6"
    csv_file = io.BytesIO(csv_content.encode())
    files = {"file": ("data.txt", csv_file, "text/plain")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": ","
    }

def test_preview_any_extension_tsv(api_client: TestClient, auth_token: str):
    """Test that .dat file with TSV content is accepted"""
    tsv_content = "col1\tcol2\tcol3\n1\t2\t3\n4\t5\t6"
    tsv_file = io.BytesIO(tsv_content.encode())
    files = {"file": ("data.dat", tsv_file, "application/octet-stream")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": "\t"
    }

def test_preview_gzipped_any_extension(api_client: TestClient, auth_token: str):
    """Test that .gz file with any base extension works"""
    import gzip
    csv_content = "col1,col2,col3\n1,2,3\n4,5,6"
    gzipped_content = gzip.compress(csv_content.encode())
    gz_file = io.BytesIO(gzipped_content)
    files = {"file": ("data.txt.gz", gz_file, "application/gzip")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json() == {
        "columns": ["col1", "col2", "col3"],
        "delimiter": ","
    }

def test_preview_delimiter_inference_tab(api_client: TestClient, auth_token: str):
    """Test delimiter inference from content for tab-delimited file with .csv extension"""
    tsv_content = "chromosome\tposition\treference\talt\tpValue\n1\t12345\tA\tG\t0.001"
    tsv_file = io.BytesIO(tsv_content.encode())
    # Use .csv extension but tab-delimited content - should infer tab
    files = {"file": ("genetic_data.csv", tsv_file, "text/csv")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    assert response.json()["delimiter"] == "\t"
    assert "chromosome" in response.json()["columns"]

def test_preview_quoted_fields_with_embedded_delimiter(api_client: TestClient, auth_token: str):
    """Test that quoted fields with embedded delimiters are handled correctly"""
    csv_content = 'name,description,notes\n"John Smith","Works at ACME, Inc.","Has a PhD, MSc"\n"Jane Doe","Engineer at XYZ, LLC","Expert in AI, ML"'
    csv_file = io.BytesIO(csv_content.encode())
    files = {"file": ("data.csv", csv_file, "text/csv")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    result = response.json()
    assert result["delimiter"] == ","
    # Should correctly parse 3 columns, not be confused by embedded commas
    assert len(result["columns"]) == 3
    assert result["columns"] == ["name", "description", "notes"]

def test_preview_quoted_fields_tab_delimited(api_client: TestClient, auth_token: str):
    """Test that quoted fields with embedded tabs in TSV are handled correctly"""
    tsv_content = 'name\tdescription\tnotes\n"John Smith"\t"Data:\tTab separated"\t"Note:\tImportant"\n"Jane Doe"\t"Info:\tTab test"\t"Test:\tOK"'
    tsv_file = io.BytesIO(tsv_content.encode())
    files = {"file": ("data.tsv", tsv_file, "text/tab-separated-values")}
    response = api_client.post("api/preview-delimited-file", files=files, headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    result = response.json()
    assert result["delimiter"] == "\t"
    # Should correctly parse 3 columns, not be confused by embedded tabs
    assert len(result["columns"]) == 3
    assert result["columns"] == ["name", "description", "notes"]

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


def test_validate_bed_file_valid(api_client: TestClient, auth_token: str):
    # Valid BED file content
    bed_content = "chr1\t1000\t2000\tregion1\t100\t+\nchr2\t3000\t4000\tregion2\t200\t-"
    bed_file = io.BytesIO(bed_content.encode())
    files = {"file": ("test.bed", bed_file, "text/plain")}
    
    response = api_client.post("/api/validate-bed-file", files=files, 
                              headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    
    result = response.json()
    assert result['valid'] is True
    assert result['data_lines'] == 2
    assert result['filename'] == "test.bed"
    assert len(result['sample_regions']) == 2
    assert 'chr1' in result['chromosomes']
    assert 'chr2' in result['chromosomes']


def test_validate_bed_file_invalid_extension(api_client: TestClient, auth_token: str):
    bed_content = "chr1\t1000\t2000"
    bed_file = io.BytesIO(bed_content.encode())
    files = {"file": ("test.txt", bed_file, "text/plain")}
    
    response = api_client.post("/api/validate-bed-file", files=files,
                              headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 400
    assert "File must be a BED or TSV file" in response.json()["detail"]


def test_validate_bed_file_invalid_format(api_client: TestClient, auth_token: str):
    # Invalid BED file - missing required fields
    bed_content = "chr1\t1000\nchr2"
    bed_file = io.BytesIO(bed_content.encode())
    files = {"file": ("test.bed", bed_file, "text/plain")}
    
    response = api_client.post("/api/validate-bed-file", files=files,
                              headers={"Authorization": f"Bearer {auth_token}"})
    # This should return 200 but with validation errors in the result
    assert response.status_code == 200
    
    result = response.json()
    assert result['valid'] is False
    assert len(result['errors']) > 0


def test_validate_tsv_file(api_client: TestClient, auth_token: str):
    # Valid TSV file content
    tsv_content = "chr1\t1000\t2000\tregion1\nchr2\t3000\t4000\tregion2"
    tsv_file = io.BytesIO(tsv_content.encode())
    files = {"file": ("test.tsv", tsv_file, "text/tab-separated-values")}
    
    response = api_client.post("/api/validate-bed-file", files=files,
                              headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    
    result = response.json()
    assert result['valid'] is True
    assert result['is_compressed'] is False
    assert result['data_lines'] == 2
    assert result['filename'] == "test.tsv"


def test_validate_compressed_file_rejected(api_client: TestClient, auth_token: str):
    import gzip
    # Valid BED file content but compressed (name it .bed to pass extension check)
    bed_content = "chr1\t1000\t2000\tregion1\nchr2\t3000\t4000\tregion2"
    gzipped_content = gzip.compress(bed_content.encode())
    gz_file = io.BytesIO(gzipped_content)
    files = {"file": ("test.bed", gz_file, "application/gzip")}
    
    response = api_client.post("/api/validate-bed-file", files=files,
                              headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 400
    assert "Compressed files are not supported" in response.json()["detail"]


@mock_aws
def test_finalize_bed_upload(api_client: TestClient, auth_token: str):
    import time
    # Set up mocked S3 bucket
    set_up_moto_bucket()
    
    # Test finalizing a BED upload with unique dataset name
    unique_dataset_name = f"test_bed_dataset_{int(time.time())}"
    response = api_client.post(
        "/api/finalize-bed-upload",
        params={
            "dataset_name": unique_dataset_name,
            "filename": "test.bed"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200


@mock_aws
def test_get_bed_files(api_client: TestClient, auth_token: str):
    # Set up mocked S3 bucket
    set_up_moto_bucket()
    
    # Test retrieving BED files
    response = api_client.get(
        "/api/bed-files",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    bed_files = response.json()
    assert isinstance(bed_files, list)


def test_validate_non_genomic_file_rejected(api_client: TestClient, auth_token: str):
    # Non-genomic TSV file with quoted headers (like the user's example)
    non_genomic_content = '"sys_name"\t"attr1"\t"attr2"\n"sample1"\t"text"\t"more_text"'
    tsv_file = io.BytesIO(non_genomic_content.encode())
    files = {"file": ("test.tsv", tsv_file, "text/tab-separated-values")}
    
    response = api_client.post("/api/validate-bed-file", files=files,
                              headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    
    result = response.json()
    # Should be invalid because no valid genomic data lines found
    assert result['valid'] is False
    # Both lines with non-numeric positions should be treated as headers
    assert result['header_lines'] == 2
    assert result['data_lines'] == 0
    # Should have "No valid BED data lines found" error
    assert "No valid BED data lines found" in str(result['errors'])
