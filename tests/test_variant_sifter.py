import time
from unittest.mock import AsyncMock, patch

import fastapi
import pytest
from starlette.testclient import TestClient

from job_server import database_utils, server, variant_sifter
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


def _insert_dataset(name: str, phenotype: str | None = "T2D") -> None:
    """Insert an owned dataset row for USER so ownership checks pass."""
    dataset = DatasetInfo(
        name=name, file="g.tsv", ancestry="EUR", separator="\t",
        genome_build="GRCh38", phenotype=phenotype, effective_n=1000,
        col_map={"rsid": "rsID"},
    )
    database_utils.insert_dataset(get_db(), USER, dataset)


def _log_sifter(name: str, status: str) -> None:
    """Drive this dataset's variant-sifter row to RUNNING/SUCCEEDED/FAILED.

    Goes through the same logging functions the Batch poller uses rather than
    writing workflow_jobs by hand, so the tests break if the stored status
    string ever stops being a bare word.
    """
    database_utils.log_job_start(
        get_db(), USER, name, f"RUNNING {variant_sifter.SIFTER_METHOD}")
    if status != "RUNNING":
        database_utils.log_job_end(
            get_db(), USER, name, f"{variant_sifter.SIFTER_METHOD} {status}", "log")


def _metadata_url(name: str) -> str:
    return f"/api/metadata/{database_utils.get_dataset_hash(name, USER)}"


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
    assert cfg["jobQueue"] == "indexer-job-queue"
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


# ---- Task 3: public dataset-metadata endpoint ----

NOT_FOUND = {"detail": "Not found"}
UNKNOWN_GUID = "0" * 64


def test_public_dataset_metadata_projects_the_three_public_fields():
    out = variant_sifter.public_dataset_metadata({
        "name": "myds", "file": "g.tsv", "ancestry": "EUR", "separator": "\t",
        "genome_build": "GRCh37", "phenotype": "T2D", "effective_n": 1000,
        "col_map": {"rsid": "rsID"},
    })
    assert out == {"phenotype": "T2D", "ancestry": "EUR", "genome_build": "GRCh37"}


def test_public_dataset_metadata_omits_the_dataset_name_and_uploader():
    # Asserted by absence so widening PUBLIC_METADATA_FIELDS breaks a test
    # rather than silently publishing who uploaded what.
    out = variant_sifter.public_dataset_metadata(
        {"name": "myds", "file": "g.tsv", "uploaded_by": USER})
    assert "name" not in out
    assert "file" not in out
    assert "uploaded_by" not in out


def test_public_dataset_metadata_keeps_its_shape_when_fields_are_absent():
    assert variant_sifter.public_dataset_metadata({}) == {
        "phenotype": None, "ancestry": None, "genome_build": None,
    }


def test_metadata_returns_the_public_fields_for_an_indexed_dataset(api_client: TestClient):
    ds = f"md_ok_{int(time.time())}"
    _insert_dataset(ds, phenotype="Type 2 diabetes")
    _log_sifter(ds, "SUCCEEDED")
    res = api_client.get(_metadata_url(ds))
    assert res.status_code == 200
    assert res.json() == {
        "phenotype": "Type 2 diabetes", "ancestry": "EUR", "genome_build": "GRCh38",
    }


def test_metadata_needs_no_authorization_header(api_client: TestClient):
    """server.py exempts this route from the blanket auth *by function name*.

    A rename would silently re-authenticate it and break the portal, so the
    exemption gets a test rather than a comment.
    """
    ds = f"md_noauth_{int(time.time())}"
    _insert_dataset(ds)
    _log_sifter(ds, "SUCCEEDED")
    res = api_client.get(_metadata_url(ds))
    assert res.status_code == 200


def test_metadata_404s_when_the_sifter_never_ran(api_client: TestClient):
    ds = f"md_norun_{int(time.time())}"
    _insert_dataset(ds)
    res = api_client.get(_metadata_url(ds))
    assert res.status_code == 404
    assert res.json() == NOT_FOUND


def test_metadata_404s_while_the_sifter_is_still_running(api_client: TestClient):
    ds = f"md_running_{int(time.time())}"
    _insert_dataset(ds)
    _log_sifter(ds, "RUNNING")
    assert api_client.get(_metadata_url(ds)).status_code == 404


def test_metadata_404s_when_the_sifter_failed(api_client: TestClient):
    ds = f"md_failed_{int(time.time())}"
    _insert_dataset(ds)
    _log_sifter(ds, "FAILED")
    assert api_client.get(_metadata_url(ds)).status_code == 404


def test_metadata_404s_identically_for_an_unknown_guid(api_client: TestClient):
    """The endpoint is public and the GUID is derivable from dataset+username,
    so it must not reveal which datasets exist or who has run the sifter."""
    ds = f"md_oracle_{int(time.time())}"
    _insert_dataset(ds)
    unpublished = api_client.get(_metadata_url(ds))
    unknown = api_client.get(f"/api/metadata/{UNKNOWN_GUID}")
    assert unknown.status_code == unpublished.status_code == 404
    assert unknown.json() == unpublished.json() == NOT_FOUND


def test_metadata_404s_on_a_malformed_guid(api_client: TestClient):
    res = api_client.get("/api/metadata/nope")
    assert res.status_code == 404
    assert res.json() == NOT_FOUND


def test_metadata_passes_a_null_phenotype_through(api_client: TestClient):
    # Publishing a dataset whose phenotype was never recorded is not an error;
    # the portal falls back to the GUID.
    ds = f"md_nullpheno_{int(time.time())}"
    _insert_dataset(ds, phenotype=None)
    _log_sifter(ds, "SUCCEEDED")
    res = api_client.get(_metadata_url(ds))
    assert res.status_code == 200
    assert res.json()["phenotype"] is None


def test_metadata_response_carries_no_dataset_name_or_uploader(api_client: TestClient):
    ds = f"md_leak_{int(time.time())}"
    _insert_dataset(ds)
    _log_sifter(ds, "SUCCEEDED")
    body = api_client.get(_metadata_url(ds)).json()
    assert set(body) == {"phenotype", "ancestry", "genome_build"}
    assert ds not in str(body)
    assert USER not in str(body)


def test_add_cors_allows_any_origin_and_no_credentials():
    """The wildcard is only safe while credentials are off -- Starlette reflects
    the caller's origin verbatim when allow_all_origins meets a cookie."""
    app = fastapi.FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    server.add_cors(app)
    res = TestClient(app).get("/ping", headers={"Origin": "https://portal.example"})
    assert res.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in res.headers
