import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env")

SQLALCHEMY_DATABASE_URL = os.getenv('DIG_JOB_SERVER_DB',
                                    'mysql+pymysql://job_server:job_server@localhost:3308/job_server')

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)


@contextmanager
def get_db():
    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()
