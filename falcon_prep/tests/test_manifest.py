import hashlib
import json
import pytest
from falcon_prep.manifest import SCHEMA_VERSION, build_manifest, sha256_file

PREP = {"build": "GRCh37", "ancestry": "EUR", "rsid_column": "rsid",
        "z_threshold": 5.0,
        "counts": {"total": 100, "significant": 10, "unparseable": 1, "resolved": 9},
        "resolution_rate": 0.9, "chromosomes": {"1": 9, "7": 3}}


@pytest.fixture
def gwas(tmp_path):
    p = tmp_path / "g.tsv.gz"
    p.write_bytes(b"some gwas bytes")
    return p


def _build(gwas):
    return build_manifest(
        dataset_name="ds1", falcon_version="abc123",
        input_path=str(gwas), input_filename="g.tsv.gz",
        split_chromosomes=[1, 7], out_base_name="s3://b/u/g/ds1/falcon/out",
        prep_summary=PREP,
    )


def test_has_every_field_validate_manifest_requires(gwas):
    m = _build(gwas)
    for field in ("schema_version", "falcon_version", "dataset_name",
                  "input_sha256", "input_filename", "split_chromosomes",
                  "out_base_name"):
        assert field in m, f"missing required field {field}"


def test_schema_version_matches_the_server(gwas):
    assert _build(gwas)["schema_version"] == SCHEMA_VERSION == 1


def test_input_sha256_is_of_the_bytes_actually_read(gwas):
    expected = hashlib.sha256(b"some gwas bytes").hexdigest()
    assert _build(gwas)["input_sha256"] == expected
    assert sha256_file(str(gwas)) == expected


def test_carries_prep_provenance_alongside_required_fields(gwas):
    m = _build(gwas)
    assert m["falcon"]["rsid_resolution_rate"] == 0.9
    assert m["falcon"]["z_threshold"] == 5.0
    assert m["falcon"]["counts"]["significant"] == 10


def test_split_chromosomes_reflects_what_was_run(gwas):
    assert _build(gwas)["split_chromosomes"] == [1, 7]


def test_is_json_serialisable(gwas):
    json.dumps(_build(gwas))


def test_schema_version_is_the_validators_own_constant():
    """The producer must not declare its own copy -- that is how they drift."""
    from job_server import falcon as validator
    from falcon_prep import manifest
    assert manifest.SCHEMA_VERSION is validator.SCHEMA_VERSION
