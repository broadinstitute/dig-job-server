"""Mint and look up dataset-scoped FALCON CLI tokens.

Tokens are URL-safe strings prefixed `dft_` so an auth dependency can
distinguish them from JWTs without a DB round-trip on the JWT path.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from job_server.database import get_db


PREFIX = "dft_"
_TOKEN_BODY_LEN = 60  # secrets.token_urlsafe(45) → 60 chars; PREFIX(4) + 60 = 64


@dataclass(frozen=True)
class FalconPrincipal:
    user_id: int
    dataset_name: str


def mint(user_id: int, dataset_name: str, ttl_days: int = 30) -> tuple[str, datetime]:
    raw = secrets.token_urlsafe(45)
    assert len(raw) == _TOKEN_BODY_LEN, f"unexpected token body length {len(raw)}"
    token = PREFIX + raw
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=ttl_days)
    with get_db() as con:
        con.execute(text(
            "INSERT INTO falcon_tokens (token, user_id, dataset_name, "
            "expires_at, created_at) VALUES (:t, :u, :d, :e, NOW())"
        ), {"t": token, "u": user_id, "d": dataset_name, "e": expires_at})
        con.commit()
    return token, expires_at


def lookup(token: str) -> FalconPrincipal | None:
    if not token or not token.startswith(PREFIX):
        return None
    with get_db() as con:
        row = con.execute(text(
            "SELECT user_id, dataset_name FROM falcon_tokens "
            "WHERE token = :t AND revoked_at IS NULL AND expires_at > NOW()"
        ), {"t": token}).first()
    if not row:
        return None
    return FalconPrincipal(user_id=row.user_id, dataset_name=row.dataset_name)
