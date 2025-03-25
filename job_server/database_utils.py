import hashlib
import json
import zlib

import bcrypt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from job_server.compress import LogCompressor
from job_server.model import DatasetInfo


def authenticate_user(db, username, password):
    with db as connection:
        query = text("SELECT password FROM users WHERE user_name = :username")
        db_password = connection.execute(query, {"username": username}).fetchone()
        if db_password and bcrypt.checkpw(password.encode('utf-8'), db_password[0].encode('utf-8')):
            return True
        return False

def insert_dataset(db, username: str, dataset: DatasetInfo) -> bool:
    try:
        with db as connection:
            query = text("INSERT INTO datasets (id, uploaded_by, metadata, uploaded_at) "
                         "VALUES (:id, :username, :metadata, NOW())")
            connection.execute(query, {"id": get_dataset_hash(dataset.name, username),
                                       "username": username,
                                       "metadata": dataset.model_dump_json()})
            connection.commit()
            return True
    except IntegrityError:
        return False

def log_job_start(db, username, dataset, status):
    with db as connection:
        query = text("INSERT INTO dataset_jobs (id, user, status, updated_at) VALUES (:id, :username, :status, NOW()) "
                     "ON DUPLICATE KEY UPDATE user=:username, status=:status, updated_at=NOW(), job_log=NULL")
        connection.execute(query, {"id": get_dataset_hash(dataset, username), "username": username, "status": status})
        connection.commit()

def log_job_end(db, username, dataset, status, job_log):
    with db as connection:
        query = text("UPDATE dataset_jobs SET status=:status, job_log=:job_log, updated_at=NOW() WHERE id=:id")
        connection.execute(query, {"id": get_dataset_hash(dataset, username), "status": status, "job_log": LogCompressor.compress(job_log)})
        connection.commit()

def get_jobs_for_user(db, username):
    with db as connection:
        query = text("SELECT id, status, updated_at FROM dataset_jobs WHERE user = :username")
        results = connection.execute(query, {"username": username}).fetchall()
        return {row[0]: {"status": row[1], "updated_at": row[2]} for row in results}

def get_dataset_hash(dataset: str, username: str) -> str:
    return hashlib.sha256(f"{dataset}-{username}".encode('utf-8')).hexdigest()


def delete_dataset(db, username, dataset):
    with db as connection:
        query = text("DELETE FROM dataset_jobs WHERE id=:id")
        connection.execute(query, {"id": get_dataset_hash(dataset, username)})
        connection.commit()


def get_log_info(db, username, job_id):
    with db as connection:
        query = text("SELECT job_log, metadata->>'$.name' as ds_name FROM dataset_jobs dj join datasets d "
                     "on dj.id = d.id WHERE dj.id=:id and dj.user=:username")
        row = connection.execute(query, {"id": job_id, "username": username}).fetchone()
        log_content, dataset = row if row else (None, None)
        return {'log': log_content.decode('latin1'), 'dataset': dataset}


def get_dataset_metadata(db, username) -> dict:
    with db as connection:
        query = text("SELECT metadata, metadata->>'$.name', uploaded_at as ds_name FROM datasets WHERE uploaded_by = :username")
        results = connection.execute(query, {"username": username}).fetchall()
        return {row[1]: {**json.loads(row[0]), "uploaded_at": row[2]} for row in results}
