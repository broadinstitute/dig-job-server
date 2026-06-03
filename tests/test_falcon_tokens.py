from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from job_server import falcon_tokens
from job_server.database import get_db


def test_mint_token_returns_dft_prefixed_string(api_client):
    token, expires_at = falcon_tokens.mint(user_id=1, dataset_name="ds1", ttl_days=30)
    assert token.startswith("dft_")
    assert len(token) == 64  # "dft_" + 60 url-safe chars
    assert expires_at > datetime.now(tz=timezone.utc) + timedelta(days=29)


def test_lookup_returns_principal_for_valid_token(api_client):
    token, _ = falcon_tokens.mint(user_id=1, dataset_name="ds1", ttl_days=30)
    principal = falcon_tokens.lookup(token)
    assert principal.user_id == 1
    assert principal.dataset_name == "ds1"


def test_lookup_returns_none_for_unknown_token(api_client):
    assert falcon_tokens.lookup("dft_doesnotexist") is None


def test_lookup_returns_none_for_expired_token(api_client):
    token, _ = falcon_tokens.mint(user_id=1, dataset_name="ds1", ttl_days=30)
    with get_db() as con:
        con.execute(text(
            "UPDATE falcon_tokens SET expires_at = NOW() - INTERVAL 1 DAY "
            "WHERE token = :t"
        ), {"t": token})
        con.commit()
    assert falcon_tokens.lookup(token) is None


def test_lookup_returns_none_for_revoked_token(api_client):
    token, _ = falcon_tokens.mint(user_id=1, dataset_name="ds1", ttl_days=30)
    with get_db() as con:
        con.execute(text(
            "UPDATE falcon_tokens SET revoked_at = NOW() WHERE token = :t"
        ), {"t": token})
        con.commit()
    assert falcon_tokens.lookup(token) is None
