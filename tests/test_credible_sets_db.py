# tests/test_credible_sets_db.py
import time

from sqlalchemy import text

from job_server import database_utils
from job_server.database import get_db
from job_server.model import CredibleSetInfo, DatasetInfo

USER = "testuser"


def _dataset(name: str) -> str:
    database_utils.insert_dataset(get_db(), USER, DatasetInfo(
        name=name, file="g.tsv", ancestry="EUR", separator="\t", genome_build="GRCh37",
        phenotype="T2D", effective_n=1000, col_map={"rsid": "rsID"}))
    return database_utils.get_dataset_hash(name, USER)


def _info(name="SuSiE v1", slug="susie-v1"):
    return CredibleSetInfo(name=name, slug=slug, file="cs.tsv", separator="\t",
                           col_map={"chromosome": "CHR"}, uploaded_at="2026-09-03T12:00:00")


def test_insert_and_list_for_dataset():
    ds = f"csdb_list_{int(time.time() * 1000)}"
    _dataset(ds)
    assert database_utils.insert_credible_set(get_db(), USER, ds, _info(), 312, 14)
    rows = database_utils.get_credible_sets_for_dataset(get_db(), USER, ds)
    assert len(rows) == 1
    row = rows[0]
    assert (row["name"], row["slug"], row["filename"], row["row_count"], row["set_count"]) == \
        ("SuSiE v1", "susie-v1", "cs.tsv", 312, 14)
    assert row["uploaded_at"] is not None


def test_duplicate_name_is_rejected_case_insensitively():
    ds = f"csdb_dupe_{int(time.time() * 1000)}"
    _dataset(ds)
    assert database_utils.insert_credible_set(get_db(), USER, ds, _info("SuSiE v1", "susie-v1"), 1, 1)
    assert not database_utils.insert_credible_set(get_db(), USER, ds, _info("susie V1", "susie-v1"), 1, 1)
    # a different name that slugs the same is also a collision
    assert not database_utils.insert_credible_set(get_db(), USER, ds, _info("SuSiE-v1", "susie-v1"), 1, 1)


def test_same_name_on_two_datasets_is_fine():
    a, b = (f"csdb_a_{int(time.time() * 1000)}", f"csdb_b_{int(time.time() * 1000)}")
    _dataset(a); _dataset(b)
    assert database_utils.insert_credible_set(get_db(), USER, a, _info(), 1, 1)
    assert database_utils.insert_credible_set(get_db(), USER, b, _info(), 1, 1)


def test_list_for_user_groups_by_dataset_id():
    a, b = (f"csdb_ua_{int(time.time() * 1000)}", f"csdb_ub_{int(time.time() * 1000)}")
    ida, idb = _dataset(a), _dataset(b)
    database_utils.insert_credible_set(get_db(), USER, a, _info("one", "one"), 1, 1)
    database_utils.insert_credible_set(get_db(), USER, a, _info("two", "two"), 1, 1)
    database_utils.insert_credible_set(get_db(), USER, b, _info("three", "three"), 1, 1)
    grouped = database_utils.get_credible_sets_for_user(get_db(), USER)
    assert [r["slug"] for r in grouped[ida]] == ["one", "two"]
    assert [r["slug"] for r in grouped[idb]] == ["three"]


def test_delete_returns_whether_a_row_went_away():
    ds = f"csdb_del_{int(time.time() * 1000)}"
    _dataset(ds)
    database_utils.insert_credible_set(get_db(), USER, ds, _info(), 1, 1)
    assert database_utils.delete_credible_set(get_db(), USER, ds, "susie-v1") is True
    assert database_utils.delete_credible_set(get_db(), USER, ds, "susie-v1") is False
    assert database_utils.get_credible_sets_for_dataset(get_db(), USER, ds) == []


def test_rows_cascade_when_the_dataset_is_deleted():
    ds = f"csdb_cascade_{int(time.time() * 1000)}"
    dataset_id = _dataset(ds)
    database_utils.insert_credible_set(get_db(), USER, ds, _info(), 1, 1)
    database_utils.delete_dataset(get_db(), USER, ds)
    with get_db() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM credible_sets WHERE dataset_id=:id"),
                         {"id": dataset_id}).scalar()
    assert n == 0


def test_workflow_jobs_for_dataset_lists_every_method():
    ds = f"csdb_jobs_{int(time.time() * 1000)}"
    dataset_id = _dataset(ds)
    database_utils.log_job_start(get_db(), USER, ds, "RUNNING variant-sifter")
    database_utils.log_job_end(get_db(), USER, ds, "variant-sifter SUCCEEDED", "log")
    database_utils.log_job_start(get_db(), USER, ds, "RUNNING credible-sets")
    jobs = database_utils.get_workflow_jobs_for_dataset(get_db(), dataset_id)
    assert {(j["method"], j["status"]) for j in jobs} == {
        ("variant-sifter", "SUCCEEDED"), ("credible-sets", "RUNNING")}
    assert all(j["updated_at"] is not None for j in jobs)
