from sqlalchemy import inspect

from job_server.database import get_db


def test_falcon_tokens_table_shape(api_client):
    with get_db() as con:
        insp = inspect(con)
        assert "falcon_tokens" in insp.get_table_names()
        cols = {c["name"]: c for c in insp.get_columns("falcon_tokens")}
        assert set(cols) >= {
            "id", "token", "user_id", "dataset_name",
            "expires_at", "revoked_at", "created_at",
        }
        # token column is CHAR(64): 4-char "dft_" prefix + 60 url-safe chars
        assert "char(64)" in str(cols["token"]["type"]).lower()
