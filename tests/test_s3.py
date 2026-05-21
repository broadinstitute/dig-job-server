"""Unit tests for job_server.s3 helpers."""
from __future__ import annotations

import hashlib

import boto3
import pytest
from moto import mock_aws

from job_server import s3

BUCKET = "dig-ldsc-server"


@mock_aws
class TestComputeObjectSha256:
    def _setup_bucket_with_object(self, key: str, body: bytes) -> None:
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        client.put_object(Bucket=BUCKET, Key=key, Body=body)

    def test_matches_hashlib_for_small_object(self):
        payload = b"hello falcon\n" * 1000
        self._setup_bucket_with_object("test/small.bin", payload)
        expected = hashlib.sha256(payload).hexdigest()

        assert s3.compute_object_sha256("test/small.bin") == expected

    def test_streams_large_object(self):
        # Exceeds the internal chunk size so we exercise streaming.
        payload = b"x" * (12 * 1024 * 1024)
        self._setup_bucket_with_object("test/big.bin", payload)
        expected = hashlib.sha256(payload).hexdigest()

        assert s3.compute_object_sha256("test/big.bin") == expected

    def test_raises_for_missing_object(self):
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        from botocore.exceptions import ClientError
        with pytest.raises(ClientError):
            s3.compute_object_sha256("does/not/exist")


class TestGetFalconS3Prefix:
    def test_returns_prefix_without_filename(self):
        # Mirrors the existing get_bed_s3_path / get_s3_path shape.
        assert (
            s3.get_falcon_s3_prefix("alice", "T2D_EUR")
            == "userdata/alice/genetic/T2D_EUR/falcon"
        )

    def test_returns_full_key_with_filename(self):
        assert (
            s3.get_falcon_s3_prefix("alice", "T2D_EUR", "run1.wg.genes")
            == "userdata/alice/genetic/T2D_EUR/falcon/run1.wg.genes"
        )
