import time
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from job_server import database_utils, variant_sifter
from job_server.database import get_db
from job_server.model import DatasetInfo

USER = "testuser"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_token(api_client: TestClient) -> str:
    res = api_client.post("/api/login", json={"username": USER, "password": "change.me"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture
def auth_token(api_client: TestClient) -> str:
    return get_token(api_client)


def _insert_dataset(name: str) -> None:
    """Insert an owned dataset row for USER so ownership checks pass."""
    dataset = DatasetInfo(
        name=name, file="g.tsv", ancestry="EUR", separator="\t",
        genome_build="GRCh38", phenotype="T2D", effective_n=1000,
        col_map={"rsid": "rsID"},
    )
    database_utils.insert_dataset(get_db(), USER, dataset)


# ---- Task 1: pure helpers ----

def test_sifter_method_constant():
    assert variant_sifter.SIFTER_METHOD == "variant-sifter"


def test_build_sifter_url_without_region():
    url = variant_sifter.build_sifter_url("https://sifter.example", "abc123")
    assert url == (
        "https://sifter.example/research.html"
        "?pageid=kp_variant_sifter&phenotype=abc123"
    )


def test_build_sifter_url_with_region_and_trailing_slash():
    url = variant_sifter.build_sifter_url("https://sifter.example/", "abc123", region="1:100-200")
    assert url == (
        "https://sifter.example/research.html"
        "?pageid=kp_variant_sifter&phenotype=abc123&region=1:100-200"
    )


def test_sifter_job_config_shape():
    cfg = variant_sifter.sifter_job_config("testuser", "myds", "guid123")
    assert cfg["jobName"] == "gwas-ce-variant-sifter"
    assert cfg["jobQueue"] == "gwas-ce-variant-sifter-job-queue"
    assert cfg["jobDefinition"] == "gwas-ce-variant-sifter"
    assert cfg["parameters"] == {
        "username": "testuser", "dataset": "myds", "guid": "guid123",
    }


# ---- Task 2: run endpoint ----

def test_run_requires_auth(api_client: TestClient):
    res = api_client.post("/api/variant-sifter/run/anyds")
    assert res.status_code == 401


def test_run_unknown_dataset_404(api_client: TestClient, auth_token: str):
    res = api_client.post("/api/variant-sifter/run/no_such_ds", headers=_auth(auth_token))
    assert res.status_code == 404


def test_run_starts_job_and_logs_running(api_client: TestClient, auth_token: str):
    ds = f"vs_run_{int(time.time())}"
    _insert_dataset(ds)
    with patch("job_server.batch.submit_and_await_job", new=AsyncMock()) as mock_wait:
        res = api_client.post(f"/api/variant-sifter/run/{ds}", headers=_auth(auth_token))
    assert res.status_code == 200
    assert res.json()["job_id"] == database_utils.get_dataset_hash(ds, USER)
    with get_db() as conn:
        from sqlalchemy import text
        row = conn.execute(text(
            "SELECT status FROM workflow_jobs WHERE id=:id AND method='variant-sifter'"
        ), {"id": database_utils.get_dataset_hash(ds, USER)}).fetchone()
    assert row is not None and row[0] == "RUNNING"
    assert mock_wait.await_count == 1
    args, kwargs = mock_wait.await_args
    assert args[0]["jobDefinition"] == "gwas-ce-variant-sifter"
    assert args[3] == "variant-sifter"
