from moto import mock_aws
from sqlalchemy import text

from job_server.database import get_db
from job_server import falcon_tokens
from tests.fixtures import seed_dataset
from tests.test_api import get_token


# /api/falcon/dataset generates a presigned GWAS URL; without AWS creds
# botocore raises NoCredentialsError (not ClientError, so the endpoint's
# except doesn't swallow it). @mock_aws supplies fake creds like every
# other S3-touching test in this suite.
@mock_aws
def test_returns_metadata_for_valid_token(api_client):
    seed_dataset("ds1", username="testuser", gwas_sha256="a" * 64, gwas_filename="gwas.tsv")
    token, _ = falcon_tokens.mint(1, "ds1")
    res = api_client.get(
        "/api/falcon/dataset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["dataset_name"] == "ds1"
    assert body["expected_gwas_sha256"] == "a" * 64
    assert body["gwas_filename"] == "gwas.tsv"
    assert body["sample_size"] == 625000
    assert body["inf_heritability"] == 0.1212
    assert body["chr_to_update"] == "1-22"
    assert body["image"] == "sagehen03/falcon:latest"
    assert body["web_app_base_url"].startswith("http")


def test_rejects_jwt_session_token(api_client):
    auth_token = get_token(api_client)
    res = api_client.get(
        "/api/falcon/dataset",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert res.status_code == 401


def test_rejects_expired_token(api_client):
    seed_dataset("ds1", username="testuser", gwas_sha256="a" * 64, gwas_filename="gwas.tsv")
    token, _ = falcon_tokens.mint(1, "ds1")
    with get_db() as con:
        con.execute(text("UPDATE falcon_tokens SET expires_at = NOW() - INTERVAL 1 DAY"))
        con.commit()
    res = api_client.get(
        "/api/falcon/dataset",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code in (401, 410)


@mock_aws
def test_returns_sumstats_columns_from_col_map(api_client):
    seed_dataset(
        "ds1", username="testuser", gwas_sha256="a" * 64,
        col_map={"chromosome": "CHR", "position": "BP", "rsid": "ID", "beta": "BETA",
                 "se": "SE", "reference": "OA", "alt": "EA", "n": "N"},
    )
    token, _ = falcon_tokens.mint(1, "ds1")
    res = api_client.get(
        "/api/falcon/dataset", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    sc = res.json()["sumstats_columns"]
    assert sc["sumstats-chr-col"] == "CHR"
    assert sc["sumstats-id-col"] == "ID"
    assert sc["sumstats-se-col"] == "SE"
    assert sc["sumstats-z-col"] == "None"
    assert "sumstats-freq-col" not in sc
