from unittest.mock import MagicMock, patch

import pytest

from job_server import s3, variant_sifter
from job_server.model import CredibleSetInfo


def _info():
    return CredibleSetInfo(name="SuSiE v1", slug="susie-v1", file="cs.tsv.gz", separator="\t",
                           col_map={"chromosome": "CHR"}, uploaded_at="2026-09-03T12:00:00")


def test_prefix_lives_under_the_datasets_genetic_folder():
    """delete_dataset clears userdata/{u}/genetic/{d}/ -- uploads must sit inside it."""
    assert s3.get_credible_set_s3_prefix("u", "d", "susie-v1") == \
        "userdata/u/genetic/d/credible_sets/susie-v1/raw"
    assert s3.get_credible_set_s3_prefix("u", "d", "susie-v1", "cs.tsv.gz") == \
        "userdata/u/genetic/d/credible_sets/susie-v1/raw/cs.tsv.gz"


def test_put_writes_the_file_and_the_metadata():
    client = MagicMock()
    with patch.object(s3.boto3, "client", return_value=client):
        s3.put_credible_set("u", "d", _info(), b"bytes")
    keys = {kw["Key"]: kw for _, kw in client.put_object.call_args_list}
    assert keys["userdata/u/genetic/d/credible_sets/susie-v1/raw/cs.tsv.gz"]["Body"] == b"bytes"
    meta = keys["userdata/u/genetic/d/credible_sets/susie-v1/raw/metadata"]
    assert CredibleSetInfo.model_validate_json(meta["Body"]) == _info()
    assert all(kw["Bucket"] == s3.BUCKET_NAME for kw in keys.values())


def test_delete_clears_only_that_slugs_folder():
    """Prefix must end with '/' or slug 'a' would also wipe 'a-b'."""
    with patch.object(s3, "clear_dir") as clear:
        s3.delete_credible_set_dir("u", "d", "a")
    clear.assert_called_once_with("userdata/u/genetic/d/credible_sets/a/")


def test_download_url_is_a_presigned_get_on_the_raw_file():
    with patch.object(s3, "generate_presigned_url", return_value="https://signed") as gen:
        url = s3.credible_set_download_url("u", "d", "susie-v1", "cs.tsv.gz")
    assert url == "https://signed"
    gen.assert_called_once_with(
        "get_object",
        params={"Bucket": s3.BUCKET_NAME,
                "Key": "userdata/u/genetic/d/credible_sets/susie-v1/raw/cs.tsv.gz"},
        expires_in=900)


def test_job_config_defaults_to_full_mode():
    cfg = variant_sifter.sifter_job_config("u", "d", "g")
    assert cfg["jobName"] == "gwas-ce-variant-sifter"
    assert cfg["parameters"]["mode"] == "full"


def test_job_config_credible_sets_mode_is_distinguishable_in_the_console():
    cfg = variant_sifter.sifter_job_config("u", "d", "g", mode="credible-sets")
    assert cfg["jobName"] == "gwas-ce-credible-sets"
    assert cfg["jobDefinition"] == "gwas-ce-variant-sifter"     # same definition
    assert cfg["parameters"] == {"username": "u", "dataset": "d", "guid": "g", "mode": "credible-sets"}


def test_job_config_rejects_unknown_modes():
    with pytest.raises(ValueError):
        variant_sifter.sifter_job_config("u", "d", "g", mode="nope")
