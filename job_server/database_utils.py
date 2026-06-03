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
def log_job_start(db, username, dataset, status, prefix=""):
    # Parse status like "RUNNING sldsc" to extract method
    if status.startswith("RUNNING "):
        method = status.replace("RUNNING ", "")
        with db as connection:
            query = text("INSERT INTO workflow_jobs (id, user, method, status, started_at, updated_at) "
                         "VALUES (:id, :username, :method, 'RUNNING', NOW(), NOW()) "
                         "ON DUPLICATE KEY UPDATE status='RUNNING', updated_at=NOW(), job_log=NULL")
            connection.execute(query, {
                "id": get_dataset_hash(dataset, username, prefix=prefix),
                "username": username,
                "method": method
            })
            connection.commit()

def log_job_end(db, username, dataset, status, job_log, prefix=""):
    # Parse status like "sldsc SUCCEEDED" to extract method and result
    parts = status.split()
    if len(parts) >= 2:
        method = parts[0]
        result = parts[1]
        with db as connection:
            query = text("UPDATE workflow_jobs SET status=:status, job_log=:job_log, updated_at=NOW() "
                         "WHERE id=:id AND method=:method")
            connection.execute(query, {
                "id": get_dataset_hash(dataset, username, prefix=prefix),
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

def get_dataset_hash(dataset: str, username: str, prefix: str = "") -> str:
    identifier = f"{prefix}{dataset}-{username}" if prefix else f"{dataset}-{username}"
    return hashlib.sha256(identifier.encode('utf-8')).hexdigest()

def delete_dataset(db, username, dataset):
    with db as connection:
        dataset_hash = get_dataset_hash(dataset, username)
        query = text("DELETE FROM workflow_jobs WHERE id=:id")
        connection.execute(query, {"id": dataset_hash})
        query = text("DELETE FROM datasets WHERE id=:id")
        connection.execute(query, {"id": dataset_hash})
        connection.commit()

def get_log_info(db, username, job_id, method_name):
    with db as connection:
        # Check if this is a BED file job (annot-sldsc method uses bed: prefix)
        if method_name == "annot-sldsc" or (job_id and job_id.startswith("bed:")):
            # Join with bed_files table for BED file workflows
            query = text("""
                SELECT w.job_log, b.dataset_name as ds_name, w.method, w.status
                FROM workflow_jobs w
                JOIN bed_files b ON w.id = b.id
                WHERE w.id=:id and w.user=:username and w.method = :method
            """)
        else:
            # Join with datasets table for regular GWAS workflows
            query = text("""
                SELECT w.job_log, d.metadata->>'$.name' as ds_name, w.method, w.status
                FROM workflow_jobs w
                JOIN datasets d ON w.id = d.id
                WHERE w.id=:id and w.user=:username and w.method = :method
            """)
        
        row = connection.execute(query, {"id": job_id, "username": username, "method": method_name}).fetchone()
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
            SELECT method, status, updated_at, id
            FROM workflow_jobs
            WHERE id = :id AND user = :username
            ORDER BY method
        """)
        results = connection.execute(query, {
            "id": get_dataset_hash(dataset, username),
            "username": username
        }).fetchall()

        workflows = {}
        for method, status, updated_at, job_id in results:
            # Use method as both workflow and method for frontend compatibility
            if method not in workflows:
                workflows[method] = {}
            workflows[method][method] = {
                "status": status,
                "updated_at": updated_at,
                "job_id": job_id
            }

        return workflows


def insert_bed_file(db, username: str, dataset_name: str, filename: str, s3_path: str) -> bool:
    """Insert a BED file record into the bed_files table"""
    try:
        with db as connection:
            # Generate hash with bed: prefix to avoid collisions with GWAS datasets
            bed_id = get_dataset_hash(dataset_name, username, prefix="bed:")
            query = text(
                "INSERT INTO bed_files (id, user, dataset_name, filename, s3_path, uploaded_at) "
                "VALUES (:id, :user, :dataset_name, :filename, :s3_path, NOW())"
            )
            connection.execute(query, {
                "id": bed_id,
                "user": username,
                "dataset_name": dataset_name,
                "filename": filename,
                "s3_path": s3_path
            })
            connection.commit()
            return True
    except IntegrityError:
        return False


def get_bed_files_for_user(db, username: str) -> list:
    """Get all BED files uploaded by a user"""
    with db as connection:
        query = text(
            "SELECT id, dataset_name, filename, s3_path, uploaded_at "
            "FROM bed_files WHERE user = :username "
            "ORDER BY uploaded_at DESC"
        )
        results = connection.execute(query, {"username": username}).fetchall()
        return [{
            "id": row[0],
            "dataset_name": row[1],
            "filename": row[2],
            "s3_path": row[3],
            "uploaded_at": row[4]
        } for row in results]


def delete_bed_file(db, username: str, dataset_name: str) -> bool:
    """Delete a BED file record and associated workflow jobs"""
    try:
        with db as connection:
            # Generate the same hash used when creating the BED file
            bed_id = get_dataset_hash(dataset_name, username, prefix="bed:")

            # Delete workflow jobs associated with this BED file
            workflow_query = text("DELETE FROM workflow_jobs WHERE id = :id")
            connection.execute(workflow_query, {"id": bed_id})

            # Delete the BED file record
            query = text(
                "DELETE FROM bed_files WHERE user = :user AND dataset_name = :dataset_name"
            )
            result = connection.execute(query, {
                "user": username,
                "dataset_name": dataset_name
            })
            connection.commit()
            return result.rowcount > 0
    except Exception:
        return False


def set_dataset_gwas_sha256(db, username: str, dataset: str, sha256_hex: str) -> None:
    """Persist the SHA256 of the uploaded GWAS into the dataset row.

    Called from finalize-upload once the file is in S3. The hash is the
    binding key for FALCON result uploads: PEGS computes the same hash
    inside the docker container and records it in its manifest, which the
    finalize endpoint validates against this column.
    """
    with db as connection:
        query = text(
            "UPDATE datasets SET gwas_sha256 = :sha256 "
            "WHERE id = :id AND uploaded_by = :username"
        )
        connection.execute(query, {
            "sha256": sha256_hex,
            "id": get_dataset_hash(dataset, username),
            "username": username,
        })
        connection.commit()


def get_dataset_gwas_sha256(db, username: str, dataset: str) -> "str | None":
    """Return the dataset's stored gwas_sha256, or None if not set / no row."""
    with db as connection:
        query = text(
            "SELECT gwas_sha256 FROM datasets "
            "WHERE id = :id AND uploaded_by = :username"
        )
        row = connection.execute(query, {
            "id": get_dataset_hash(dataset, username),
            "username": username,
        }).fetchone()
    if row is None:
        return None
    return row[0]


def get_dataset_falcon_meta(db, username: str, name: str) -> "tuple[str | None, str | None, dict]":
    """Return (gwas_sha256, gwas_filename, col_map) for the named dataset.

    gwas_filename and col_map both live inside the datasets.metadata JSON
    (keys 'file' and 'col_map'). col_map maps standard field names to the
    user's GWAS column names and drives FALCON's sumstats config. Returns
    (None, None, {}) when the dataset row is absent.
    """
    with db as connection:
        row = connection.execute(text(
            "SELECT gwas_sha256, metadata->>'$.file' AS file_name, "
            "metadata->>'$.col_map' AS col_map "
            "FROM datasets WHERE id = :id AND uploaded_by = :u"
        ), {"id": get_dataset_hash(name, username), "u": username}).fetchone()
    if row is None:
        return None, None, {}
    col_map = json.loads(row[2]) if row[2] else {}
    return row[0], row[1], col_map


def record_falcon_success(db, username: str, dataset: str) -> None:
    """Insert/upsert a SUCCEEDED workflow_jobs row for method='falcon'.

    FALCON differs from the other methods in that there's no batch job to
    track — the user runs it locally and the success signal is the manifest
    upload finalize. We just record the terminal state directly.
    """
    with db as connection:
        query = text(
            "INSERT INTO workflow_jobs "
            "  (id, user, method, status, started_at, updated_at) "
            "VALUES (:id, :username, 'falcon', 'SUCCEEDED', NOW(), NOW()) "
            "ON DUPLICATE KEY UPDATE status='SUCCEEDED', updated_at=NOW(), job_log=NULL"
        )
        connection.execute(query, {
            "id": get_dataset_hash(dataset, username),
            "username": username,
        })
        connection.commit()
