"""Pure credible-set helpers: no HTTP, no S3. (The autouse DB fixture still
runs; that is a conftest property, not a dependency of this module.)"""
from datetime import datetime, timedelta

import pytest

from job_server import credible_sets as cs
from job_server.model import CredibleSetInfo

T0 = datetime(2026, 9, 3, 12, 0, 0)


def _job(method, status, minutes):
    return {"method": method, "status": status, "updated_at": T0 + timedelta(minutes=minutes)}


# ---- names and slugs ----

def test_method_constant_and_ingest_methods():
    assert cs.CREDIBLE_SETS_METHOD == "credible-sets"
    assert cs.INGEST_METHODS == ("credible-sets", "variant-sifter")


@pytest.mark.parametrize("name,slug", [
    ("SuSiE v1", "susie-v1"),
    ("  FINEMAP  ", "finemap"),
    ("a__b--c", "a-b-c"),
    ("-leading and trailing-", "leading-and-trailing"),
    ("MixedCASE 42", "mixedcase-42"),
])
def test_slugify(name, slug):
    assert cs.slugify(name) == slug


def test_slugify_rejects_names_without_a_letter_or_digit():
    with pytest.raises(ValueError):
        cs.slugify("---")


def test_validate_name_trims_and_bounds_length():
    assert cs.validate_name("  SuSiE v1 ") == "SuSiE v1"
    with pytest.raises(ValueError):
        cs.validate_name("")
    with pytest.raises(ValueError):
        cs.validate_name("x" * 31)
    assert cs.validate_name("x" * 30) == "x" * 30


# ---- derive_status ----

def test_status_pending_when_nothing_ran():
    assert cs.derive_status(T0, []) == "pending"


def test_status_pending_when_only_older_jobs_succeeded():
    assert cs.derive_status(T0, [_job("variant-sifter", "SUCCEEDED", -5)]) == "pending"


def test_status_indexing_while_either_ingest_method_runs():
    assert cs.derive_status(T0, [_job("credible-sets", "RUNNING", 1)]) == "indexing"
    assert cs.derive_status(T0, [_job("variant-sifter", "RUNNING", 1),
                                 _job("credible-sets", "SUCCEEDED", -1)]) == "indexing"


def test_status_indexed_when_a_later_job_of_either_method_succeeded():
    assert cs.derive_status(T0, [_job("credible-sets", "SUCCEEDED", 2)]) == "indexed"
    assert cs.derive_status(T0, [_job("variant-sifter", "SUCCEEDED", 2)]) == "indexed"
    # exactly at the upload time counts (the job could not have missed the file)
    assert cs.derive_status(T0, [_job("credible-sets", "SUCCEEDED", 0)]) == "indexed"


def test_status_failed_when_the_latest_job_after_upload_failed():
    assert cs.derive_status(T0, [_job("credible-sets", "FAILED", 3),
                                 _job("variant-sifter", "SUCCEEDED", -10)]) == "failed"


def test_status_indexed_wins_over_an_older_failure():
    assert cs.derive_status(T0, [_job("credible-sets", "FAILED", 1),
                                 _job("variant-sifter", "SUCCEEDED", 2)]) == "indexed"


def test_status_ignores_unrelated_methods():
    assert cs.derive_status(T0, [_job("magma", "RUNNING", 1), _job("sldsc", "FAILED", 2)]) == "pending"


# ---- adapters ----

def test_jobs_from_workflows_flattens_the_datasets_endpoint_shape():
    workflows = {
        "variant-sifter": {"variant-sifter": {"status": "SUCCEEDED", "updated_at": T0}},
        "magma": {"magma": {"status": "RUNNING", "updated_at": T0}},
    }
    assert cs.jobs_from_workflows(workflows) == [
        {"method": "variant-sifter", "status": "SUCCEEDED", "updated_at": T0},
        {"method": "magma", "status": "RUNNING", "updated_at": T0},
    ]
    assert cs.jobs_from_workflows({}) == []


def test_records_with_status_adds_status_without_mutating_input():
    rows = [{"name": "a", "slug": "a", "filename": "a.tsv", "row_count": 1,
             "set_count": 1, "uploaded_at": T0}]
    out = cs.records_with_status(rows, [_job("credible-sets", "SUCCEEDED", 1)])
    assert out[0]["status"] == "indexed"
    assert "status" not in rows[0]


def test_credible_set_info_roundtrips_json():
    info = CredibleSetInfo(name="SuSiE v1", slug="susie-v1", file="cs.tsv", separator="\t",
                           col_map={"chromosome": "CHR"}, uploaded_at="2026-09-03T12:00:00")
    assert CredibleSetInfo.model_validate_json(info.model_dump_json()) == info
