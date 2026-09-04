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


@pytest.mark.parametrize("filename,expected", [
    ("cs.tsv", "cs.tsv"),
    ("  cs.tsv  ", "cs.tsv"),
    ("", ValueError),
    ("metadata", ValueError),
    ("METADATA", ValueError),
    ("a/b.tsv", ValueError),
    ("x" * 256, ValueError),
])
def test_validate_filename(filename, expected):
    if expected is ValueError:
        with pytest.raises(ValueError):
            cs.validate_filename(filename)
    else:
        assert cs.validate_filename(filename) == expected


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


# ---- validate_file ----

import gzip
import json
from unittest.mock import patch

COL_MAP = {"chromosome": "CHR", "position": "POS", "reference": "REF", "alt": "ALT",
           "credibleSetId": "CS", "posteriorProbability": "PIP"}
HEADER = "CHR\tPOS\tREF\tALT\tCS\tPIP"


def _tsv(*rows, header=HEADER):
    return ("\n".join([header, *rows]) + "\n").encode()


def _validate(raw, col_map=COL_MAP, separator="\t", filename="cs.tsv"):
    return cs.validate_file(raw, filename, separator, col_map)


def test_valid_file_reports_counts_and_separator():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.6", "1\t200\tC\tT\t1\t0.4", "2\t300\tA\tC\t2\t0.9"))
    assert rep["ok"] is True
    assert rep["errors"] == []
    assert (rep["row_count"], rep["set_count"], rep["separator"]) == (3, 2, "\t")
    assert rep["sets_preview"][0] == {"credibleSetId": "1", "variants": 2, "pp_sum": 1.0}


def test_required_field_unmapped_is_an_error_before_parsing():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.6"), col_map={k: v for k, v in COL_MAP.items() if k != "alt"})
    assert rep["ok"] is False
    assert "alt" in rep["errors"][0]["message"]


def test_multi_character_separator_is_a_report_error():
    rep = cs.validate_file(_tsv("1\t100\tA\tG\t1\t0.6"), "cs.tsv", ";;", COL_MAP)
    assert rep["ok"] is False
    assert "single character" in rep["errors"][0]["message"]


def test_mapped_column_missing_from_header_is_an_error():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.6"), col_map={**COL_MAP, "pValue": "P"})
    assert rep["ok"] is False
    assert rep["errors"][0]["line"] == 1
    assert "P" in rep["errors"][0]["message"]


@pytest.mark.parametrize("row,fragment", [
    ("23\t100\tA\tG\t1\t0.6", "chromosome"),
    ("1\t0\tA\tG\t1\t0.6", "position"),
    ("1\tx\tA\tG\t1\t0.6", "position"),
    ("1\t100\tN\tG\t1\t0.6", "reference"),
    ("1\t100\tA\t-\t1\t0.6", "alt"),
    ("1\t100\tA\tG\t\t0.6", "credibleSetId"),
    ("1\t100\tA\tG\t1\t1.5", "posteriorProbability"),
    ("1\t100\tA\tG\t1\t0", "posteriorProbability"),
    ("1\t100\tA\tG\t1\tnan", "posteriorProbability"),
])
def test_row_level_errors_carry_the_line_number(row, fragment):
    rep = _validate(_tsv("1\t50\tA\tG\t1\t0.5", row))
    assert rep["ok"] is False
    assert rep["errors"][0]["line"] == 3
    assert fragment in rep["errors"][0]["message"]


def test_optional_fields_are_validated_when_mapped():
    col_map = {**COL_MAP, "pValue": "P", "beta": "B", "se": "SE", "n": "N"}
    header = HEADER + "\tP\tB\tSE\tN"
    ok = _validate(_tsv("1\t100\tA\tG\t1\t0.6\t1e-8\t0.1\t0.02\t1000", header=header), col_map)
    assert ok["ok"] is True
    bad = _validate(_tsv("1\t100\tA\tG\t1\t0.6\t0\t0.1\t-1\t0", header=header), col_map)
    messages = " | ".join(e["message"] for e in bad["errors"])
    assert "pValue" in messages and "se" in messages and "n" in messages


def test_duplicate_variant_within_a_set_is_an_error():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.5", "1\t100\ta\tg\t1\t0.5"))
    assert rep["ok"] is False
    assert "duplicate" in rep["errors"][0]["message"]
    assert rep["errors"][0]["line"] == 3


def test_same_variant_in_two_sets_is_allowed():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.5", "1\t100\tA\tG\t2\t0.5"))
    assert rep["ok"] is True


def test_set_spanning_two_chromosomes_is_an_error():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.5", "2\t100\tA\tG\t1\t0.5"))
    assert rep["ok"] is False
    assert "chromosome" in rep["errors"][0]["message"]


def test_gzip_input_and_delimiter_inference():
    raw = gzip.compress(_tsv("1,100,A,G,1,0.6", header="CHR,POS,REF,ALT,CS,PIP"))
    rep = _validate(raw, separator=None, filename="cs.csv.gz")
    assert rep["ok"] is True
    assert rep["separator"] == ","


def test_gzip_decompressed_size_is_capped():
    # Identical rows compress far smaller than they decompress (a gzip
    # bomb's shape): compressed stays well under MAX_BYTES=64 while the
    # decompressed payload is well over it, so this exercises the
    # decompressed-size cap rather than the pre-decode raw-length check.
    raw = gzip.compress(_tsv(*(["1\t100\tA\tG\t1\t0.5"] * 30)))
    with patch.object(cs, "MAX_BYTES", 64):
        rep = _validate(raw, separator=None, filename="cs.tsv.gz")
    assert rep["ok"] is False
    assert "MB" in rep["errors"][0]["message"]


def test_undetectable_delimiter_is_an_error():
    rep = _validate(b"CHR|POS|REF|ALT|CS|PIP\n1|100|A|G|1|0.6\n", separator=None)
    assert rep["ok"] is False


def test_empty_file_is_an_error():
    rep = _validate(_tsv())
    assert rep["ok"] is False
    assert "No data rows" in rep["errors"][0]["message"]


def test_warnings_for_pp_sum_single_variant_and_chr_prefix():
    rep = _validate(_tsv("chr1\t100\tA\tG\t1\t0.2", "1\t200\tC\tT\t2\t0.9"))
    assert rep["ok"] is True
    messages = " | ".join(w["message"] for w in rep["warnings"])
    assert "sum to 0.200" in messages          # set 1 renormalised later
    assert "single variant" in messages
    assert "normalised" in messages


def test_pp_sum_inside_tolerance_does_not_warn():
    rep = _validate(_tsv("1\t100\tA\tG\t1\t0.55", "1\t200\tC\tT\t1\t0.55"))
    assert not any("sum to" in w["message"] for w in rep["warnings"])


def test_size_limit():
    with patch.object(cs, "MAX_BYTES", 10):
        rep = _validate(_tsv("1\t100\tA\tG\t1\t0.6"))
    assert rep["ok"] is False and "MB" in rep["errors"][0]["message"]


def test_row_limit():
    rows = [f"1\t{i}\tA\tG\t1\t0.5" for i in range(1, 5)]
    with patch.object(cs, "MAX_ROWS", 3):
        rep = _validate(_tsv(*rows))
    assert rep["ok"] is False and "3 data rows" in rep["errors"][0]["message"]


def test_set_limit():
    rows = [f"1\t{i}\tA\tG\t{i}\t1" for i in range(1, 5)]
    with patch.object(cs, "MAX_SETS", 3):
        rep = _validate(_tsv(*rows))
    assert rep["ok"] is False and "3 credible sets" in rep["errors"][0]["message"]


def test_errors_are_capped_with_a_summary_line():
    rows = [f"1\t0\tA\tG\t1\t0.5" for _ in range(25)]
    rep = _validate(_tsv(*rows))
    assert len(rep["errors"]) == cs.MAX_ERRORS + 1
    assert rep["errors"][-1] == {"line": None, "message": "... and 5 more errors"}


def test_report_is_json_serialisable():
    json.dumps(_validate(_tsv("1\t100\tA\tG\t1\t0.6")))
