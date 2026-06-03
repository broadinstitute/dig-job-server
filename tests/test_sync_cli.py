import boto3
import pytest
from moto import mock_aws

from job_server import s3, sync_from_s3

BUCKET = s3.BUCKET_NAME


def test_dataset_without_user_errors(api_client):
    with pytest.raises(SystemExit):  # argparse error → exit 2
        sync_from_s3.main(["--dataset", "ds1"])


def test_nonlocal_db_returns_2(api_client, monkeypatch):
    monkeypatch.setenv("DIG_JOB_SERVER_DB", "mysql+pymysql://u:p@prod.example.com:3306/db")
    assert sync_from_s3.main([]) == 2


@mock_aws
def test_dry_run_returns_0(api_client):
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
    assert sync_from_s3.main(["--dry-run"]) == 0
