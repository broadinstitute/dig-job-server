"""FALCON-specific server-side helpers.

The result-upload flow's correctness rests on the binding between a
dataset's GWAS file (hashed at upload time) and a FALCON run's manifest
(hashed inside the docker container). This module owns the schema +
validation logic for that binding.
"""
from __future__ import annotations

SCHEMA_VERSION = 1

_REQUIRED_FIELDS = (
    "schema_version",
    "falcon_version",
    "dataset_name",
    "input_sha256",
    "input_filename",
    "split_chromosomes",
    "out_base_name",
)


class FalconManifestError(ValueError):
    """Raised when a FALCON manifest fails validation against a dataset.

    `code` is a stable machine-readable identifier suitable for returning
    in an HTTP 409 body so the frontend can render the right dialog.
    `expected` / `got` carry the offending values for `input_sha256_mismatch`
    and `dataset_name_mismatch`.
    """

    def __init__(self, code: str, message: str, *, expected=None, got=None):
        super().__init__(message)
        self.code = code
        self.expected = expected
        self.got = got


def validate_manifest(
    manifest: dict,
    expected_dataset_name: str,
    expected_gwas_sha256: "str | None",
) -> None:
    """Raise FalconManifestError if the manifest doesn't bind to the dataset.

    Order of checks (most actionable first):
    1. Schema-version supported.
    2. All required fields present.
    3. dataset_name matches the URL slug.
    4. The dataset has a stored gwas_sha256.
    5. input_sha256 matches the dataset's gwas_sha256.
    """
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise FalconManifestError(
            "unsupported_schema_version",
            f"manifest schema_version={manifest.get('schema_version')!r}, "
            f"server supports {SCHEMA_VERSION}",
        )

    missing = [k for k in _REQUIRED_FIELDS if k not in manifest]
    if missing:
        raise FalconManifestError(
            "missing_manifest_field",
            f"manifest is missing required field(s): {', '.join(missing)}",
        )

    if manifest["dataset_name"] != expected_dataset_name:
        raise FalconManifestError(
            "dataset_name_mismatch",
            f"manifest dataset_name={manifest['dataset_name']!r} does not "
            f"match URL dataset {expected_dataset_name!r}",
            expected=expected_dataset_name,
            got=manifest["dataset_name"],
        )

    if expected_gwas_sha256 is None:
        raise FalconManifestError(
            "gwas_sha256_missing_on_dataset",
            "this dataset was uploaded before FALCON support existed and "
            "has no recorded GWAS SHA256; re-upload the GWAS to enable FALCON",
        )

    if manifest["input_sha256"] != expected_gwas_sha256:
        raise FalconManifestError(
            "input_sha256_mismatch",
            f"manifest input_sha256={manifest['input_sha256']!r} does not "
            f"match dataset gwas_sha256={expected_gwas_sha256!r}",
            expected=expected_gwas_sha256,
            got=manifest["input_sha256"],
        )
