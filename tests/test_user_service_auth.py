"""Tests for user-service auth failure translation (get_current_user)."""
import asyncio
import logging

import fastapi
import httpx
import pytest

from job_server import api
from job_server.server import configure_logging
from job_server.user_service_auth import (
    DEFAULT_USER_GROUP,
    DEFAULT_USER_SERVICE_URL,
    SESSION_EXPIRED_DETAIL,
    auth_failure_exception,
    log_user_service_config,
    user_group,
    user_service_url,
)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# --- auth_failure_exception (pure) ---

def test_upstream_401_maps_to_session_expired():
    exc = auth_failure_exception(httpx.Response(401, json={
        "detail": "Given token not valid for any token type",
    }))
    assert exc.status_code == 401
    assert exc.detail == SESSION_EXPIRED_DETAIL


def test_upstream_403_error_body_is_forwarded():
    exc = auth_failure_exception(httpx.Response(403, json={
        "error": "Token was not issued for group: gwas-ce",
    }))
    assert exc.status_code == 401
    assert exc.detail == "Token was not issued for group: gwas-ce"


def test_upstream_403_detail_body_is_forwarded():
    exc = auth_failure_exception(httpx.Response(403, json={
        "detail": "User does not belong to group",
    }))
    assert exc.status_code == 401
    assert exc.detail == "User does not belong to group"


def test_upstream_non_json_falls_back_to_invalid_token():
    exc = auth_failure_exception(httpx.Response(500, text="<html>oops</html>"))
    assert exc.status_code == 401
    assert exc.detail == "Invalid token"


def test_upstream_non_dict_json_falls_back_to_invalid_token():
    exc = auth_failure_exception(httpx.Response(403, json=["unexpected", "list", "body"]))
    assert exc.status_code == 401
    assert exc.detail == "Invalid token"


# --- wiring into get_current_user ---

class FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self._exc is not None:
            raise self._exc
        return self._response


def _patch_client(monkeypatch, response):
    monkeypatch.setattr(api.httpx, "AsyncClient", lambda: FakeAsyncClient(response))


def test_get_current_user_forwards_group_error(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "false")
    _patch_client(monkeypatch, httpx.Response(403, json={
        "error": "Token was not issued for group: gwas-ce",
    }))
    with pytest.raises(fastapi.HTTPException) as exc_info:
        run(api.get_current_user(authorization="Bearer abc", token=None))
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token was not issued for group: gwas-ce"


def test_get_current_user_success_path_still_returns_user(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("USER_SERVICE_URL", "https://users.example.org")
    monkeypatch.setenv("USER_GROUP", "hcm")
    fake_client = FakeAsyncClient(httpx.Response(200, json={
        "user": {"username": "alice"},
    }))
    monkeypatch.setattr(api.httpx, "AsyncClient", lambda: fake_client)

    user = run(api.get_current_user(authorization="Bearer abc", token=None))

    assert user.username == "alice"
    assert len(fake_client.calls) == 1
    args, kwargs = fake_client.calls[0]
    assert args[0] == "https://users.example.org/api/auth/verify/"
    assert kwargs["params"] == {"group": "hcm"}
    assert kwargs["headers"]["Authorization"] == "Bearer abc"


def test_get_current_user_request_error_maps_to_service_unavailable(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "false")
    fake_client = FakeAsyncClient(exc=httpx.ConnectError("boom"))
    monkeypatch.setattr(api.httpx, "AsyncClient", lambda: fake_client)

    with pytest.raises(fastapi.HTTPException) as exc_info:
        run(api.get_current_user(authorization="Bearer abc", token=None))

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "User service unavailable"


# --- user_group() / user_service_url() env resolution ---

def test_user_group_honours_env_override(monkeypatch):
    monkeypatch.setenv("USER_GROUP", "custom-group")
    assert user_group() == "custom-group"


def test_user_group_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("USER_GROUP", raising=False)
    assert user_group() == DEFAULT_USER_GROUP


def test_user_service_url_honours_env_override(monkeypatch):
    monkeypatch.setenv("USER_SERVICE_URL", "https://example.test")
    assert user_service_url() == "https://example.test"


def test_user_service_url_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("USER_SERVICE_URL", raising=False)
    assert user_service_url() == DEFAULT_USER_SERVICE_URL


def test_user_service_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("USER_SERVICE_URL", "https://users.example.org/")
    assert user_service_url() == "https://users.example.org"


# --- log_user_service_config() ---

# NOTE: pytest_sessionstart in conftest.py runs alembic's `command.upgrade`,
# which loads logging config from alembic.ini via `fileConfig`. fileConfig
# defaults to disable_existing_loggers=True, which disables every logger
# already registered at that point -- including the module-level
# `job_server.user_service_auth` logger, since it's not listed in
# alembic.ini's [loggers]. A disabled logger drops records before caplog's
# handler ever sees them. So these tests pass a fresh, never-before-seen
# logger into `log_user_service_config(log=...)` instead of relying on the
# module default; a brand-new logger name was never in the manager's
# registry at fileConfig time, so it isn't disabled.

def test_log_user_service_config_logs_resolved_values(monkeypatch, caplog):
    monkeypatch.setenv("USER_GROUP", "hcm")
    monkeypatch.setenv("USER_SERVICE_URL", "https://example.org")
    test_logger = logging.getLogger("test_log_user_service_config_logs_resolved_values")
    with caplog.at_level(logging.INFO, logger=test_logger.name):
        log_user_service_config(log=test_logger)
    info_records = [r for r in caplog.records if r.levelno == logging.INFO]
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("hcm" in r.getMessage() and "https://example.org" in r.getMessage()
               for r in info_records)
    assert not warning_records


def test_log_user_service_config_warns_when_user_group_unset(monkeypatch, caplog):
    monkeypatch.delenv("USER_GROUP", raising=False)
    test_logger = logging.getLogger("test_log_user_service_config_warns_when_user_group_unset")
    with caplog.at_level(logging.INFO, logger=test_logger.name):
        log_user_service_config(log=test_logger)
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("USER_GROUP is not set" in r.getMessage() for r in warning_records)


# --- configure_logging() ---
#
# Fixes a defect found in review: with nothing else configuring logging in
# the serve path, the "job_server.user_service_auth" module logger inherits
# the root logger's default WARNING level, so log_user_service_config()'s
# INFO line was silently dropped in production (confirmed with a manual
# `python -c` check -- zero bytes on stdout/stderr). configure_logging()
# gives the root logger a formatted stderr handler via basicConfig() (a
# no-op if one is already installed) and raises only the "job_server"
# logger tree to INFO, deliberately leaving root at WARNING so third-party
# INFO logs (httpx per-request lines, botocore) stay off.
#
# conftest's alembic fileConfig call has already disabled some pre-existing
# loggers for this session (see the NOTE above), so this test asserts on
# the "job_server" parent logger's effective level, rather than on a
# disabled child logger actually emitting.

def test_configure_logging_enables_info_for_job_server_logger():
    job_server_logger = logging.getLogger("job_server")
    original_level = job_server_logger.level
    try:
        configure_logging()
        assert job_server_logger.isEnabledFor(logging.INFO)
    finally:
        job_server_logger.setLevel(original_level)
