import json
import time
from unittest.mock import AsyncMock, patch

from sqlalchemy import text
from starlette.testclient import TestClient

from job_server import database_utils
from job_server.database import get_db
from job_server.model import DatasetInfo

USER = "testuser"
COL_MAP = {"chromosome": "CHR", "position": "POS", "reference": "REF", "alt": "ALT",
           "credibleSetId": "CS", "posteriorProbability": "PIP"}
GOOD = b"CHR\tPOS\tREF\tALT\tCS\tPIP\n1\t100\tA\tG\t1\t0.6\n1\t200\tC\tT\t1\t0.4\n"
BAD = b"CHR\tPOS\tREF\tALT\tCS\tPIP\n1\t0\tA\tG\t1\t0.6\n"


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _token(api_client):
    res = api_client.post("/api/login", json={"username": USER, "password": "change.me"})
    assert res.status_code == 200
    return res.json()["access_token"]


def _dataset(name):
    database_utils.insert_dataset(get_db(), USER, DatasetInfo(
        name=name, file="g.tsv", ancestry="EUR", separator="\t", genome_build="GRCh37",
        phenotype="T2D", effective_n=1000, col_map={"rsid": "rsID"}))
    return database_utils.get_dataset_hash(name, USER)


def _sifted(name):
    database_utils.log_job_start(get_db(), USER, name, "RUNNING variant-sifter")
    database_utils.log_job_end(get_db(), USER, name, "variant-sifter SUCCEEDED", "log")


def _multipart(name="SuSiE v1", content=GOOD, col_map=COL_MAP, filename="cs.tsv"):
    return {"files": {"file": (filename, content, "text/plain")},
            "data": {"name": name, "col_map": json.dumps(col_map), "separator": "\t"}}


def _patched():
    """Patch S3 + Batch so no test touches AWS."""
    return (patch("job_server.s3.put_credible_set"),
            patch("job_server.s3.delete_credible_set_dir"),
            patch("job_server.s3.credible_set_download_url", return_value="https://signed"),
            patch("job_server.batch.submit_and_await_job", new=AsyncMock()))


def _ds(prefix):
    return f"{prefix}_{int(time.time() * 1000)}"


# ---- validate ----

def test_validate_requires_auth(api_client: TestClient):
    res = api_client.post("/api/credible-sets/validate", **_multipart())
    assert res.status_code == 401


def test_validate_needs_no_dataset_and_returns_a_report(api_client: TestClient):
    res = api_client.post("/api/credible-sets/validate", **_multipart(), headers=_auth(_token(api_client)))
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True and body["row_count"] == 2 and body["set_count"] == 1


def test_validate_reports_errors_with_200(api_client: TestClient):
    res = api_client.post("/api/credible-sets/validate", **_multipart(content=BAD),
                          headers=_auth(_token(api_client)))
    assert res.status_code == 200
    assert res.json()["ok"] is False and res.json()["errors"][0]["line"] == 2


def test_validate_rejects_malformed_col_map(api_client: TestClient):
    payload = _multipart()
    payload["data"]["col_map"] = "not json"
    res = api_client.post("/api/credible-sets/validate", **payload, headers=_auth(_token(api_client)))
    assert res.status_code == 400


def test_multi_character_separator_is_a_400(api_client: TestClient):
    token = _token(api_client)
    payload = _multipart()
    payload["data"]["separator"] = ";;"
    res = api_client.post("/api/credible-sets/validate", **payload, headers=_auth(token))
    assert res.status_code == 400

    ds = _ds("csapi_sep")
    _dataset(ds)
    put, delete_dir, _, submit = _patched()
    payload2 = _multipart()
    payload2["data"]["separator"] = ";;"
    with put, delete_dir, submit:
        res2 = api_client.post(f"/api/credible-sets/{ds}", **payload2, headers=_auth(token))
    assert res2.status_code == 400


# ---- create ----

def test_create_404s_for_a_dataset_the_user_does_not_own(api_client: TestClient):
    res = api_client.post("/api/credible-sets/no_such_ds", **_multipart(), headers=_auth(_token(api_client)))
    assert res.status_code == 404


def test_create_stores_inserts_and_is_pending_when_not_sifted(api_client: TestClient):
    ds = _ds("csapi_create")
    _dataset(ds)
    put, delete_dir, _, submit = _patched()
    with put as put_mock, delete_dir, submit as submit_mock:
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(_token(api_client)))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["name"] == "SuSiE v1" and body["slug"] == "susie-v1"
    assert (body["row_count"], body["set_count"], body["status"], body["job_id"]) == (2, 1, "pending", None)
    (user, dataset, info, raw), _ = put_mock.call_args
    assert (user, dataset, info.slug, info.file, info.separator, info.col_map) == \
        (USER, ds, "susie-v1", "cs.tsv", "\t", COL_MAP)
    assert raw == GOOD
    submit_mock.assert_not_awaited()
    assert [r["slug"] for r in database_utils.get_credible_sets_for_dataset(get_db(), USER, ds)] == ["susie-v1"]


def test_create_submits_the_credible_sets_job_when_sifted(api_client: TestClient):
    ds = _ds("csapi_sifted")
    dataset_id = _dataset(ds)
    _sifted(ds)
    put, delete_dir, _, submit = _patched()
    with put, delete_dir, submit as submit_mock:
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(_token(api_client)))
    assert res.status_code == 200, res.text
    assert res.json()["job_id"] == dataset_id
    assert res.json()["status"] == "indexing"
    assert submit_mock.await_count == 1
    args, _ = submit_mock.await_args
    assert args[0]["jobName"] == "gwas-ce-credible-sets"
    assert args[0]["parameters"]["mode"] == "credible-sets"
    assert args[3] == "credible-sets"
    with get_db() as conn:
        row = conn.execute(text("SELECT status FROM workflow_jobs WHERE id=:id AND method='credible-sets'"),
                           {"id": dataset_id}).fetchone()
    assert row[0] == "RUNNING"


def test_create_400s_with_the_report_and_stores_nothing(api_client: TestClient):
    ds = _ds("csapi_bad")
    _dataset(ds)
    put, delete_dir, _, submit = _patched()
    with put as put_mock, delete_dir, submit:
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(content=BAD),
                              headers=_auth(_token(api_client)))
    assert res.status_code == 400
    assert res.json()["detail"]["ok"] is False
    put_mock.assert_not_called()
    assert database_utils.get_credible_sets_for_dataset(get_db(), USER, ds) == []


def test_create_400s_on_a_bad_name(api_client: TestClient):
    ds = _ds("csapi_name")
    _dataset(ds)
    put, delete_dir, _, submit = _patched()
    with put, delete_dir, submit:
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(name="---"),
                              headers=_auth(_token(api_client)))
    assert res.status_code == 400


def test_create_400s_on_a_reserved_or_bad_filename(api_client: TestClient):
    ds = _ds("csapi_fname")
    _dataset(ds)
    token = _token(api_client)
    put, delete_dir, _, submit = _patched()
    with put as put_mock, delete_dir, submit:
        res1 = api_client.post(f"/api/credible-sets/{ds}", **_multipart(filename="metadata"),
                               headers=_auth(token))
        res2 = api_client.post(f"/api/credible-sets/{ds}", **_multipart(filename="x" * 300),
                               headers=_auth(token))
    assert res1.status_code == 400
    assert res2.status_code == 400
    put_mock.assert_not_called()
    assert database_utils.get_credible_sets_for_dataset(get_db(), USER, ds) == []


def test_create_409s_on_a_duplicate_name(api_client: TestClient):
    ds = _ds("csapi_dupe")
    _dataset(ds)
    put, delete_dir, _, submit = _patched()
    token = _token(api_client)
    with put, delete_dir, submit:
        assert api_client.post(f"/api/credible-sets/{ds}", **_multipart(name="SuSiE v1"),
                               headers=_auth(token)).status_code == 200
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(name="susie V1"), headers=_auth(token))
    assert res.status_code == 409


def test_create_rolls_back_the_row_when_s3_fails(api_client: TestClient):
    from botocore.exceptions import ClientError
    ds = _ds("csapi_s3fail")
    _dataset(ds)
    err = ClientError({"Error": {"Code": "500", "Message": "boom"}}, "PutObject")
    with patch("job_server.s3.put_credible_set", side_effect=err), \
         patch("job_server.batch.submit_and_await_job", new=AsyncMock()):
        res = api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(_token(api_client)))
    assert res.status_code == 500
    assert database_utils.get_credible_sets_for_dataset(get_db(), USER, ds) == []


# ---- list / download / delete / reindex ----

def test_list_download_delete_roundtrip(api_client: TestClient):
    ds = _ds("csapi_round")
    _dataset(ds)
    token = _token(api_client)
    put, delete_dir, download, submit = _patched()
    with put, delete_dir as delete_mock, download, submit as submit_mock:
        api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(token))

        listed = api_client.get(f"/api/credible-sets/{ds}", headers=_auth(token))
        assert listed.status_code == 200
        assert [r["slug"] for r in listed.json()] == ["susie-v1"]
        assert listed.json()[0]["status"] == "pending"

        dl = api_client.get(f"/api/credible-sets/{ds}/susie-v1/download", headers=_auth(token))
        assert dl.status_code == 200
        assert dl.json() == {"url": "https://signed", "filename": "cs.tsv"}
        assert api_client.get(f"/api/credible-sets/{ds}/nope/download", headers=_auth(token)).status_code == 404

        gone = api_client.delete(f"/api/credible-sets/{ds}/susie-v1", headers=_auth(token))
        assert gone.status_code == 200 and gone.json() == {"job_id": None}
        delete_mock.assert_called_once_with(USER, ds, "susie-v1")
        submit_mock.assert_not_awaited()
        assert api_client.delete(f"/api/credible-sets/{ds}/susie-v1", headers=_auth(token)).status_code == 404
    assert api_client.get(f"/api/credible-sets/{ds}", headers=_auth(token)).json() == []


def test_delete_reconciles_the_index_when_sifted(api_client: TestClient):
    ds = _ds("csapi_delsifted")
    dataset_id = _dataset(ds)
    _sifted(ds)
    token = _token(api_client)
    put, delete_dir, _, submit = _patched()
    with put, delete_dir, submit as submit_mock:
        api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(token))
        res = api_client.delete(f"/api/credible-sets/{ds}/susie-v1", headers=_auth(token))
    assert res.json() == {"job_id": dataset_id}
    assert submit_mock.await_count == 2      # one for create, one for delete


def test_delete_keeps_the_row_when_s3_fails(api_client: TestClient):
    from botocore.exceptions import ClientError
    ds = _ds("csapi_delfail")
    _dataset(ds)
    token = _token(api_client)
    put, delete_dir, _, submit = _patched()
    with put, delete_dir, submit:
        api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(token))
    err = ClientError({"Error": {"Code": "500", "Message": "boom"}}, "DeleteObjects")
    with patch("job_server.s3.delete_credible_set_dir", side_effect=err):
        res = api_client.delete(f"/api/credible-sets/{ds}/susie-v1", headers=_auth(token))
    assert res.status_code == 500
    assert [r["slug"] for r in database_utils.get_credible_sets_for_dataset(get_db(), USER, ds)] == ["susie-v1"]


def test_reindex_409s_unless_sifted_and_idle(api_client: TestClient):
    ds = _ds("csapi_reindex")
    dataset_id = _dataset(ds)
    token = _token(api_client)
    with patch("job_server.batch.submit_and_await_job", new=AsyncMock()) as submit_mock:
        assert api_client.post(f"/api/credible-sets/{ds}/reindex", headers=_auth(token)).status_code == 409
        _sifted(ds)
        database_utils.log_job_start(get_db(), USER, ds, "RUNNING credible-sets")
        assert api_client.post(f"/api/credible-sets/{ds}/reindex", headers=_auth(token)).status_code == 409
        database_utils.log_job_end(get_db(), USER, ds, "credible-sets FAILED", "log")
        res = api_client.post(f"/api/credible-sets/{ds}/reindex", headers=_auth(token))
    assert res.status_code == 200 and res.json() == {"job_id": dataset_id}
    assert submit_mock.await_count == 1


def test_datasets_listing_carries_credible_sets_with_status(api_client: TestClient):
    ds = _ds("csapi_listing")
    _dataset(ds)
    token = _token(api_client)
    put, delete_dir, _, submit = _patched()
    with put, delete_dir, submit, patch("job_server.s3.get_datasets", return_value=[ds]):
        api_client.post(f"/api/credible-sets/{ds}", **_multipart(), headers=_auth(token))
        res = api_client.get("/api/datasets", headers=_auth(token))
    assert res.status_code == 200
    row = next(r for r in res.json() if r["dataset"] == ds)
    assert [c["slug"] for c in row["credible_sets"]] == ["susie-v1"]
    assert row["credible_sets"][0]["status"] == "pending"
