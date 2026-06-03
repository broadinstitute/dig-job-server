from os import environ

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

if environ.get('TEST_DIG_JOB_SERVER_DB'):
    environ['DIG_JOB_SERVER_DB'] = environ['TEST_DIG_JOB_SERVER_DB']
else:
    # Local default uses a dedicated test database so a test run never
    # truncates the app's `job_server` data (the app and tests share the
    # same MySQL server on :3305). CI sets TEST_DIG_JOB_SERVER_DB explicitly.
    environ['DIG_JOB_SERVER_DB'] = 'mysql+pymysql://job_server:job_server@localhost:3305/job_server_test'

# Enable test mode for JWT authentication. Must be set BEFORE importing
# job_server.api (transitively via server) so module-level test-only routes
# (e.g. /_falcon_principal_probe) are registered on the router.
environ['TEST_MODE'] = 'true'

from job_server.database import get_db
from job_server.server import create_app

client = TestClient(create_app())


def before_each_test():
    """
    runs before each test
    """
    with get_db() as con:
        con.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        con.execute(text("TRUNCATE TABLE users"))
        # Clean bed_files table if it exists
        try:
            con.execute(text("TRUNCATE TABLE bed_files"))
        except Exception:
            # Table might not exist in older test environments
            pass
        try:
            con.execute(text("TRUNCATE TABLE falcon_tokens"))
        except Exception:
            pass
        try:
            con.execute(text("TRUNCATE TABLE datasets"))
        except Exception:
            pass
        # password is change.me
        con.execute(text("INSERT INTO users (id, user_name, password, created_at) "
                         "values (1, 'testuser', "
                         "'$2b$12$oA9o05xM7N9RQoJ1bYYXBumucprQC6D2U2Buzi1/vuryfI9W8QrlC', NOW())"))
        con.commit()
        con.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def pytest_sessionstart():
    """
    run db migrations before we start tests
    """
    alembic_cfg = Config("./alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(autouse=True)
def api_client():
    before_each_test()
    return client
