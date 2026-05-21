"""Unit tests for job_server.falcon manifest validation."""
from __future__ import annotations

import pytest

from job_server import falcon


def _good_manifest(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "falcon_version": "0.4.1",
        "dataset_name": "T2D_EUR",
        "input_sha256": "a" * 64,
        "input_filename": "gwas.tsv.gz",
        "split_chromosomes": [1, 2, 22],
        "out_base_name": "run1",
        "created_at": "2026-05-19T14:32:11Z",
        "config_summary": {"sample-size": "625000"},
    }
    base.update(overrides)
    return base


class TestValidateManifest:
    def test_happy_path(self):
        m = _good_manifest()
        # Must NOT raise
        falcon.validate_manifest(
            m, expected_dataset_name="T2D_EUR", expected_gwas_sha256="a" * 64,
        )

    def test_missing_required_field(self):
        m = _good_manifest()
        del m["input_sha256"]
        with pytest.raises(falcon.FalconManifestError) as exc:
            falcon.validate_manifest(m, "T2D_EUR", "a" * 64)
        assert exc.value.code == "missing_manifest_field"
        assert "input_sha256" in str(exc.value)

    def test_unknown_schema_version(self):
        m = _good_manifest(schema_version=2)
        with pytest.raises(falcon.FalconManifestError) as exc:
            falcon.validate_manifest(m, "T2D_EUR", "a" * 64)
        assert exc.value.code == "unsupported_schema_version"

    def test_dataset_name_mismatch(self):
        m = _good_manifest(dataset_name="OTHER")
        with pytest.raises(falcon.FalconManifestError) as exc:
            falcon.validate_manifest(m, "T2D_EUR", "a" * 64)
        assert exc.value.code == "dataset_name_mismatch"

    def test_input_sha256_mismatch(self):
        m = _good_manifest(input_sha256="b" * 64)
        with pytest.raises(falcon.FalconManifestError) as exc:
            falcon.validate_manifest(m, "T2D_EUR", "a" * 64)
        assert exc.value.code == "input_sha256_mismatch"
        # Error payload exposes both values for the client's error dialog
        assert exc.value.expected == "a" * 64
        assert exc.value.got == "b" * 64

    def test_null_gwas_sha256_rejected(self):
        # When the dataset was uploaded before this column existed, we
        # can't verify the bind — refuse to accept FALCON results.
        m = _good_manifest()
        with pytest.raises(falcon.FalconManifestError) as exc:
            falcon.validate_manifest(m, "T2D_EUR", None)
        assert exc.value.code == "gwas_sha256_missing_on_dataset"
