import os

from sqlalchemy import create_engine

SQLALCHEMY_DATABASE_URL = os.getenv('DIG_JOB_SERVER_DB')

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)


def get_db():
    with engine.connect() as connection:
        yield connection
