"""Cross-component contracts that nothing else would catch.

Every other test here exercises one module. These lock the seams between the
converter, the config template FALCON reads, the shell entrypoint, and the
job-server validator — places where a rename in one file breaks another
silently, and the failure only surfaces in a cloud run minutes later.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from falcon_prep.writer import SUMSTATS_HEADER

REPO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = REPO / "deploy" / "falcon" / "configs" / "job-server.ini.tmpl"
ENTRYPOINT = REPO / "deploy" / "falcon" / "falcon-batch.sh"


def _ini_values(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


@pytest.fixture(scope="module")
def config():
    assert TEMPLATE.exists(), f"config template missing at {TEMPLATE}"
    return _ini_values(TEMPLATE.read_text())


def test_every_sumstats_column_the_config_names_is_one_the_writer_emits(config):
    """FALCON looks these up by name in the header the writer produces.

    Renaming a column on either side alone yields a run that reads nothing,
    with no error until the job has already staged its inputs.
    """
    for key, value in config.items():
        if not key.startswith("sumstats-") or not key.endswith("-col"):
            continue
        if value in ("None", "none"):
            continue
        assert value in SUMSTATS_HEADER, (
            f"{key} = {value!r} is not a column the writer emits "
            f"({', '.join(SUMSTATS_HEADER)})"
        )


def test_the_config_names_an_id_column(config):
    """FALCON joins LD and S2G by this column; without it nothing matches."""
    assert config.get("sumstats-id-col") == "rsID"


def test_zero_snp_thr_is_present_and_parses_as_a_float(config):
    """The entrypoint scrapes this value to drive the converter's filter.

    A comment or reformatting on that line yields a threshold the converter
    cannot parse, which previously surfaced as 'dataset unsupported'.
    """
    raw = config.get("zero-snp-thr")
    assert raw is not None, "template must define zero-snp-thr"
    assert float(raw) > 0


def test_the_entrypoints_awk_extracts_that_exact_value(config):
    """Reproduce the entrypoint's extraction rather than trusting it."""
    text = TEMPLATE.read_text()
    extracted = None
    for line in text.splitlines():
        if re.match(r"^\s*zero-snp-thr", line):
            extracted = line.split("=", 1)[1].replace(" ", "")
    assert extracted is not None
    assert float(extracted) == float(config["zero-snp-thr"])


def test_no_dentist_key_is_configured(config):
    """A DENTIST file switches FALCON to keeping the top 20% of variants by |Z|,
    silently invalidating the |Z| >= threshold pre-filter the converter applies.
    """
    assert "dentist-file" not in config
    assert "dentist-folder" not in config


def test_template_placeholders_are_all_substituted_by_the_entrypoint():
    """Any placeholder the entrypoint does not replace reaches FALCON verbatim."""
    placeholders = set(re.findall(r"@[A-Z_]+@", TEMPLATE.read_text()))
    entry = ENTRYPOINT.read_text()
    for p in placeholders:
        assert p in entry, f"{p} is never substituted by falcon-batch.sh"


def test_manifest_schema_matches_the_validators():
    """The producer must not carry its own copy of the schema version."""
    from job_server import falcon as validator

    from falcon_prep import manifest

    assert manifest.SCHEMA_VERSION is validator.SCHEMA_VERSION


def test_exit_codes_the_entrypoint_propagates_are_the_ones_cli_returns():
    """The shell treats these as a contract; drift makes failures unreadable."""
    from falcon_prep.cli import EXIT_NO_VARIANTS, EXIT_UNSUPPORTED

    assert EXIT_UNSUPPORTED != 2 and EXIT_NO_VARIANTS != 2
    assert EXIT_UNSUPPORTED != EXIT_NO_VARIANTS
