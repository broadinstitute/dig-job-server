from os import environ

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from database import get_db
from server import app

if environ.get('TEST_DIG_JOB_SERVER_DB'):
    environ['DIG_JOB_SERVER_DB'] = environ['TEST_DIG_JOB_SERVER_DB']
else:
    environ['DIG_JOB_SERVER_DB'] = 'mysql+mysqlconnector://job_server:job_server@localhost:3308/job_server'

client = TestClient(app)


def before_each_test():
    """
    runs before each test
    """
    with get_db() as con:
        con.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        con.execute(text("TRUNCATE TABLE users"))
        # password is change.me
        con.execute(text("INSERT INTO users (id, user_name, password, created_at) "
                         "values (1, 'testuser@broadinstitute.org', "
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
