import hashlib
import zlib

import bcrypt
from sqlalchemy import text

from job_server.compress import LogCompressor


def authenticate_user(db, username, password):
    with db as connection:
        query = text("SELECT password FROM users WHERE user_name = :username")
        db_password = connection.execute(query, {"username": username}).fetchone()
        if db_password and bcrypt.checkpw(password.encode('utf-8'), db_password[0].encode('utf-8')):
            return True
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
        query = text("SELECT job_log FROM dataset_jobs WHERE id=:id and user=:username")
        log_content = connection.execute(query, {"id": job_id, "username": username}).fetchone()[0]
        return {'log': log_content.decode('latin1')}
