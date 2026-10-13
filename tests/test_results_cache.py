"""The results endpoints cache parsed result files in memory. That cache must
follow the object in S3: a dataset deleted and re-created under the same name
(or a method re-run) writes a new file at the same key, and the page must show
the new file, not whatever was loaded for the old one."""
from __future__ import annotations

import boto3
from moto import mock_aws
from starlette.testclient import TestClient

from job_server import api

BUCKET = "dig-ldsc-server"
USER = "testuser"


def _login(api_client: TestClient) -> dict:
    res = api_client.post("/api/login", json={"username": USER, "password": "change.me"})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _tissue_row(annotation: str, p: str) -> bytes:
    return f"{annotation}\tadipose\tsubcutaneous\t8.5\t{p}\n".encode()


@mock_aws
def test_get_cached_results_reloads_when_the_object_changes():
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET)
    path = f"userdata/{USER}/genetic/cache-unit/sldsc/sldsc"
    client.put_object(Bucket=BUCKET, Key=f"{path}/tissue.output.tsv", Body=_tissue_row("enhancer", "1e-5"))
    first = api.get_cached_results(path, "tissue.output.tsv", "sldsc", False)
    assert first["annotation"].tolist() == ["enhancer"]

    client.put_object(Bucket=BUCKET, Key=f"{path}/tissue.output.tsv", Body=_tissue_row("promoter", "2e-5"))

    second = api.get_cached_results(path, "tissue.output.tsv", "sldsc", False)
    assert second["annotation"].tolist() == ["promoter"]


@mock_aws
def test_results_follow_a_dataset_recreated_under_the_same_name(api_client: TestClient):
    """The jarbesfe case: view results, delete the dataset, upload a different
    GWAS under the same name, run the method again, view results."""
    headers = _login(api_client)
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket=BUCKET)
    ds = "cache-recreated"
    key = f"userdata/{USER}/genetic/{ds}/sldsc/sldsc/tissue.output.tsv"

    client.put_object(Bucket=BUCKET, Key=key, Body=_tissue_row("old-gwas", "1e-5"))
    res = api_client.get(f"/api/results/{ds}", headers=headers)
    assert res.status_code == 200
    assert [r["annotation"] for r in res.json()["items"]] == ["old-gwas"]

    res = api_client.delete(f"/api/delete-dataset/{ds}", headers=headers)
    assert res.status_code == 200
    client.put_object(Bucket=BUCKET, Key=key, Body=_tissue_row("new-gwas", "3e-5"))

    res = api_client.get(f"/api/results/{ds}", headers=headers)
    assert res.status_code == 200
    assert [r["annotation"] for r in res.json()["items"]] == ["new-gwas"]
