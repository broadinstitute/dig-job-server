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

# Simplified job tracking functions (no workflow column needed)
def log_job_start(db, username, dataset, status):
    # Parse status like "RUNNING sldsc" to extract method
    if status.startswith("RUNNING "):
        method = status.replace("RUNNING ", "")
        with db as connection:
            query = text("INSERT INTO workflow_jobs (id, user, method, status, started_at, updated_at) "
                         "VALUES (:id, :username, :method, 'RUNNING', NOW(), NOW()) "
                         "ON DUPLICATE KEY UPDATE status='RUNNING', updated_at=NOW(), job_log=NULL")
            connection.execute(query, {
                "id": get_dataset_hash(dataset, username), 
                "username": username, 
                "method": method
            })
            connection.commit()

def log_job_end(db, username, dataset, status, job_log):
    # Parse status like "sldsc SUCCEEDED" to extract method and result
    parts = status.split()
    if len(parts) >= 2:
        method = parts[0]
        result = parts[1]
        with db as connection:
            query = text("UPDATE workflow_jobs SET status=:status, job_log=:job_log, updated_at=NOW() "
                         "WHERE id=:id AND method=:method")
            connection.execute(query, {
                "id": get_dataset_hash(dataset, username), 
                "method": method,
                "status": result, 
                "job_log": LogCompressor.compress(job_log)
            })
            connection.commit()

def get_jobs_for_user(db, username):
    """Returns jobs with legacy format for backward compatibility"""
    with db as connection:
        # Get the most recent status for each dataset by aggregating workflows
        query = text("""
            SELECT w.id, 
                   GROUP_CONCAT(
                       CASE 
                           WHEN w.status = 'RUNNING' THEN CONCAT('RUNNING ', w.method)
                           ELSE CONCAT(w.method, ' ', w.status)
                       END 
                       ORDER BY w.updated_at DESC SEPARATOR '; '
                   ) as status,
                   MAX(w.updated_at) as updated_at
            FROM workflow_jobs w 
            WHERE w.user = :username 
            GROUP BY w.id
        """)
        results = connection.execute(query, {"username": username}).fetchall()
        return {row[0]: {"status": row[1].split('; ')[0], "updated_at": row[2]} for row in results}

def get_workflow_jobs_for_user(db, username):
    """Returns detailed job information organized by method"""
    with db as connection:
        query = text("SELECT id, method, status, updated_at FROM workflow_jobs WHERE user = :username ORDER BY updated_at DESC")
        results = connection.execute(query, {"username": username}).fetchall()
        jobs_by_dataset = {}
        for row in results:
            dataset_id, method, status, updated_at = row
            if dataset_id not in jobs_by_dataset:
                jobs_by_dataset[dataset_id] = {}
            # Use method as both workflow and method for frontend compatibility
            if method not in jobs_by_dataset[dataset_id]:
                jobs_by_dataset[dataset_id][method] = {}
            jobs_by_dataset[dataset_id][method][method] = {
                "status": status, 
                "updated_at": updated_at
            }
        return jobs_by_dataset

def get_dataset_hash(dataset: str, username: str) -> str:
    return hashlib.sha256(f"{dataset}-{username}".encode('utf-8')).hexdigest()

def delete_dataset(db, username, dataset):
    with db as connection:
        dataset_hash = get_dataset_hash(dataset, username)
        query = text("DELETE FROM workflow_jobs WHERE id=:id")
        connection.execute(query, {"id": dataset_hash})
        query = text("DELETE FROM datasets WHERE id=:id")
        connection.execute(query, {"id": dataset_hash})
        connection.commit()

def get_log_info(db, username, job_id):
    with db as connection:
        # Get logs from all jobs for this dataset, most recent first
        query = text("""
            SELECT w.job_log, d.metadata->>'$.name' as ds_name, w.method, w.status
            FROM workflow_jobs w 
            JOIN datasets d ON w.id = d.id 
            WHERE w.id=:id and w.user=:username 
            ORDER BY w.updated_at DESC 
            LIMIT 1
        """)
        row = connection.execute(query, {"id": job_id, "username": username}).fetchone()
        if row:
            log_content, dataset, method, status = row
            return {
                'log': log_content.decode('latin1') if log_content else None, 
                'dataset': dataset,
                'workflow': method,  # Use method as workflow for backward compatibility
                'method': method,
                'status': status
            }
        return {'log': None, 'dataset': None}

def get_dataset_metadata(db, username) -> dict:
    with db as connection:
        query = text("SELECT metadata, metadata->>'$.name', uploaded_at as ds_name FROM datasets WHERE uploaded_by = :username")
        results = connection.execute(query, {"username": username}).fetchall()
        return {row[1]: {**json.loads(row[0]), "uploaded_at": row[2]} for row in results}

def get_job_status(db, job_id):
    """Returns a summary status for the dataset (most recent activity)"""
    with db as connection:
        query = text("""
            SELECT CASE 
                       WHEN status = 'RUNNING' THEN CONCAT('RUNNING ', method)
                       ELSE CONCAT(method, ' ', status)
                   END as status
            FROM workflow_jobs 
            WHERE id=:id 
            ORDER BY updated_at DESC 
            LIMIT 1
        """)
        result = connection.execute(query, {"id": job_id}).fetchone()
        return result[0] if result else None

def get_workflow_status_summary(db, username, dataset):
    """Get aggregated job status for a dataset"""
    with db as connection:
        query = text("""
            SELECT method, status, updated_at
            FROM workflow_jobs 
            WHERE id = :id AND user = :username 
            ORDER BY method
        """)
        results = connection.execute(query, {
            "id": get_dataset_hash(dataset, username), 
            "username": username
        }).fetchall()
        
        workflows = {}
        for method, status, updated_at in results:
            # Use method as both workflow and method for frontend compatibility
            if method not in workflows:
                workflows[method] = {}
            workflows[method][method] = {
                "status": status,
                "updated_at": updated_at
            }
            
        return workflows
