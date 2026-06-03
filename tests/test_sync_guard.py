import pytest

from job_server import sync_from_s3
from job_server.sync_from_s3 import NonLocalDatabaseError, _assert_local_db, _dev_password


def test_local_db_url_passes(monkeypatch):
    monkeypatch.setenv("DIG_JOB_SERVER_DB", "mysql+pymysql://u:p@localhost:3305/job_server")
    _assert_local_db(allow_nonlocal_db=False)  # must not raise


def test_nonlocal_db_url_raises(monkeypatch):
    monkeypatch.setenv("DIG_JOB_SERVER_DB", "mysql+pymysql://u:p@prod.example.com:3306/job_server")
    with pytest.raises(NonLocalDatabaseError):
        _assert_local_db(allow_nonlocal_db=False)


def test_nonlocal_db_url_override_allows(monkeypatch):
    monkeypatch.setenv("DIG_JOB_SERVER_DB", "mysql+pymysql://u:p@prod.example.com:3306/job_server")
    _assert_local_db(allow_nonlocal_db=True)  # must not raise


def test_dev_password_default(monkeypatch):
    monkeypatch.delenv("SYNC_DEV_PASSWORD", raising=False)
    assert _dev_password() == "falcon-dev"


def test_dev_password_override(monkeypatch):
    monkeypatch.setenv("SYNC_DEV_PASSWORD", "hunter2")
    assert _dev_password() == "hunter2"


def test_report_summary_is_a_string():
    assert isinstance(sync_from_s3.SyncReport().summary(), str)
