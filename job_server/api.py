import asyncio
import boto3
import gzip
import io
import json
import logging
import numpy as np
import os
import re
from asyncio import Queue
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional, TextIO

import fastapi
import httpx
import pandas as pd
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Header, UploadFile, Query, BackgroundTasks
from pydantic import BaseModel
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from job_server import s3, file_utils, batch, database_utils, falcon_tokens, variant_sifter
from job_server.auth_backend import AuthBackend
from job_server.database import get_db
from job_server.falcon_tokens import FalconPrincipal
from job_server.jwt_utils import create_access_token, get_decoded_jwt_data
from job_server.model import UserCredentials, User, DatasetInfo, AnalysisRequest, AnalysisMethod

router = fastapi.APIRouter()
JOB_SERVER_AUTH_COOKIE = 'js_auth'

def get_auth_backend() -> AuthBackend:
    # Replace with logic to select the appropriate backend
    from job_server.auth_mysql import MySQLAuthBackend
    return MySQLAuthBackend(get_db())


@router.post("/login")
async def login(credentials: UserCredentials, auth_backend: AuthBackend = Depends(get_auth_backend)):
    if not auth_backend.authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=403, detail="Incorrect username or password")

    access_token = create_access_token(data={"username": credentials.username})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(authorization: Optional[str] = Header(None), token: Optional[str] = Query(None)):
    # Handle both header and query param token
    auth_token = None

    if authorization:
        schema, _, auth_token = authorization.partition(' ')
        if schema.lower() != 'bearer' or not auth_token:
            raise fastapi.HTTPException(status_code=401, detail='Bearer token required')
    elif token:
        auth_token = token

    if not auth_token:
        raise fastapi.HTTPException(status_code=401, detail='Authorization token required')

    # For testing, use JWT authentication instead of external user service
    if os.getenv('TEST_MODE', 'false').lower() == 'true':
        data = get_decoded_jwt_data(auth_token)[0]
        if data:
            return User(**data)
        else:
            raise fastapi.HTTPException(status_code=401, detail='Invalid token')

    # Production: use external user service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{os.getenv('USER_SERVICE_URL', 'https://users.kpndataregistry.org')}/api/auth/verify/",
                params={"group": os.getenv('USER_GROUP', 'gwas-ce')},
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            if response.status_code == 200:
                user_data = response.json()
                user = user_data.get('user')
                return User(username=user.get('username'))
            else:
                raise fastapi.HTTPException(status_code=401, detail='Invalid token')
    except httpx.RequestError:
        raise fastapi.HTTPException(status_code=503, detail='User service unavailable')


@router.get('/is-logged-in')
def is_logged_in(user: User = Depends(get_current_user)):
    if user:
        return user
    else:
        raise fastapi.HTTPException(status_code=401, detail='Not logged in')


@router.get("/datasets")
async def get_datasets(user: User = Depends(get_current_user),
                       orderBy: str = Query(None, description="Field to order by"),
                       orderDir: str = Query(None, description="Sort direction (asc or desc)")):
    data_set_folders = s3.get_datasets(user.username)
    jobs_for_user = database_utils.get_jobs_for_user(get_db(), user.username)
    workflow_jobs_for_user = database_utils.get_workflow_jobs_for_user(get_db(), user.username)
    data_set_metadata = database_utils.get_dataset_metadata(get_db(), user.username)

    # Create the dataset list
    datasets = []
    for d in data_set_folders:
        dataset_id = database_utils.get_dataset_hash(d, user.username)
        workflows = workflow_jobs_for_user.get(dataset_id, {})

        datasets.append({
            'dataset': d,
            'uploaded_at': data_set_metadata.get(d, {}).get('uploaded_at', ''),
            'ancestry': data_set_metadata.get(d, {}).get('ancestry', ''),
            'file_name': data_set_metadata.get(d, {}).get('file', ''),
            'genome_build': data_set_metadata.get(d, {}).get('genome_build', ''),
            'phenotype': data_set_metadata.get(d, {}).get('phenotype', ''),
            'uploaded_by': user.username,
            'status': jobs_for_user.get(dataset_id, {}).get('status'),
            'workflows': workflows,  # New: detailed workflow status
            'id': dataset_id
        })

    # Sort datasets only if orderBy parameter is provided
    if orderBy and datasets:
        try:
            reverse = orderDir and orderDir.lower() == "desc"
            datasets.sort(key=lambda x: x.get(orderBy, ""), reverse=reverse)
        except Exception as e:
            # Log the error but continue without sorting
            print(f"Error sorting datasets: {str(e)}")

    return datasets

@router.get("/workflow-status/{dataset}")
async def get_workflow_status(dataset: str, user: User = Depends(get_current_user)):
    """Get detailed workflow status for a specific dataset"""
    return database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

@router.get("/log-info/{job_id}")
async def get_log_info(job_id: str, method_name: str = Query(None), user: User = Depends(get_current_user)):
    return database_utils.get_log_info(get_db(), user.username, job_id, method_name)

@router.post("/preview-delimited-file")
async def preview_file(file: UploadFile, user: User = Depends(get_current_user)):
    """
    Preview delimited file with automatic delimiter detection.
    Supports any file extension with .gz compression.
    """
    # Read first bytes to check for gzip compression
    contents = await file.read(100)
    await file.seek(0)

    # Get sample lines (handles both compressed and uncompressed)
    if contents.startswith(b'\x1f\x8b'):
        sample_lines = await file_utils.get_compressed_sample(file)
    else:
        sample_lines = await file_utils.get_text_sample(file)

    # Check if we got any content
    if not sample_lines or not any(line.strip() for line in sample_lines):
        raise fastapi.HTTPException(
            status_code=400,
            detail="File appears to be empty or contains no data"
        )

    # Create StringIO from sample
    sample_content = io.StringIO('\n'.join(sample_lines))

    # Infer delimiter from content (not filename) and parse file
    try:
        delimiter = file_utils.infer_delimiter(sample_content)

        # Parse file with detected delimiter
        sample_content.seek(0)  # Reset position
        df = await file_utils.parse_file(sample_content, delimiter=delimiter)

        # Check for duplicate columns
        dupes = file_utils.find_dupe_cols(sample_lines[0], delimiter == ",", df.columns)
        if len(dupes) > 0:
            duped_col_str = ', '.join(set([re.sub(r"\.\d+$", '', dupe) for dupe in dupes]))
            raise ValueError(f"{duped_col_str} specified more than once")

    except ValueError as e:
        raise fastapi.HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception:
        # Catch any pandas parsing errors or other issues
        raise fastapi.HTTPException(
            status_code=400,
            detail="File must be comma or tab delimited"
        )

    return {
        "columns": [column for column in df.columns],
        "delimiter": delimiter
    }


@router.post("/validate-bed-file")
async def validate_bed_file(file: UploadFile, user: User = Depends(get_current_user)):
    """Validate a complete BED file format and return validation results.

    Args:
        file: The uploaded BED file to validate
        user: Current authenticated user

    Returns:
        dict: Validation results including errors, warnings, and sample regions
    """
    # Check file extension
    filename = file.filename.lower()
    if not (filename.endswith('.bed') or filename.endswith('.tsv')):
        raise fastapi.HTTPException(
            status_code=400,
            detail="File must be a BED or TSV file (.bed or .tsv)"
        )

    try:
        file_content = await file.read()
        file_size = len(file_content)

        is_compressed = file_content.startswith(b'\x1f\x8b')
        if is_compressed:
            raise fastapi.HTTPException(
                status_code=400,
                detail="Compressed files are not supported. Please upload uncompressed .bed or .tsv files."
            )

        try:
            decompressed_content = file_content.decode('utf-8')
        except UnicodeDecodeError as e:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Error decoding file as UTF-8: {str(e)}"
            )

        # Split into lines
        lines = decompressed_content.split('\n')

        # Remove the last empty line if it exists
        if lines and not lines[-1].strip():
            lines = lines[:-1]

        # Validate BED format for the entire file
        validation_result = file_utils.validate_bed_content(lines)

        # Add file metadata
        validation_result['filename'] = file.filename
        validation_result['file_size_bytes'] = file_size
        validation_result['is_compressed'] = is_compressed
        validation_result['decompressed_size_bytes'] = len(decompressed_content)

        # Calculate some statistics
        if validation_result['data_lines'] > 0:
            total_region_length = sum(region['length'] for region in validation_result['sample_regions'])
            if validation_result['sample_regions']:
                validation_result['avg_region_length'] = total_region_length / len(validation_result['sample_regions'])

        return validation_result

    except fastapi.HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Error validating BED file: {str(e)}"
        )


@router.get("/get-bed-presigned-url/{dataset}")
async def get_bed_presigned_url(dataset: str, filename: str = Query(None), user: User = Depends(get_current_user)):
    """Generate presigned URL for BED file upload to annotation path."""
    s3_path = s3.get_bed_s3_path(user.username, dataset, filename)
    try:
        presigned_url = s3.generate_presigned_url(
            'put_object',
            params={'Bucket': s3.BUCKET_NAME, 'Key': s3_path},
            expires_in=7200
        )
    except ClientError as e:
        raise fastapi.HTTPException(status_code=500, detail="Failed to generate presigned URL") from e
    return {"presigned_url": presigned_url, "s3_path": s3_path}


@router.post("/finalize-bed-upload")
async def finalize_bed_upload(dataset_name: str, filename: str, user: User = Depends(get_current_user)):
    try:
        # Validate that it's a .bed or .tsv file
        if not (filename.lower().endswith('.bed') or filename.lower().endswith('.tsv')):
            raise fastapi.HTTPException(status_code=400, detail="Only .bed and .tsv files are allowed")

        # Get the full S3 path for the uploaded file
        s3_path = s3.get_bed_s3_path(user.username, dataset_name, filename)

        # Upload metadata file to S3
        s3.upload_bed_metadata(user.username, dataset_name, filename)

        # Insert record into database
        success = database_utils.insert_bed_file(
            get_db(),
            user.username,
            dataset_name,
            filename,
            s3_path
        )

        if not success:
            raise fastapi.HTTPException(
                status_code=409,
                detail=f"Dataset name '{dataset_name}' already exists for this user"
            )

        return Response(status_code=200)
    except fastapi.HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=f"Failed to finalize upload: {str(e)}")


@router.get("/bed-files")
async def get_bed_files(user: User = Depends(get_current_user)):
    try:
        bed_files = database_utils.get_bed_files_for_user(get_db(), user.username)
        workflow_jobs_for_user = database_utils.get_workflow_jobs_for_user(get_db(), user.username)

        # Add workflow status to each BED file, similar to /datasets endpoint
        for bed_file in bed_files:
            bed_file['workflows'] = workflow_jobs_for_user.get(bed_file['id'], {})

        return bed_files
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=f"Failed to retrieve BED files: {str(e)}")


@router.get("/bed-files/{dataset_name}/download")
async def download_bed_file(dataset_name: str, user: User = Depends(get_current_user)):
    """Download a BED file by generating a presigned URL."""
    try:
        # Get BED file info from database
        bed_files = database_utils.get_bed_files_for_user(get_db(), user.username)
        bed_file = next((f for f in bed_files if f['dataset_name'] == dataset_name), None)

        if not bed_file:
            raise fastapi.HTTPException(status_code=404, detail="BED file not found")

        # Generate presigned URL for download with content-disposition to force download
        try:
            presigned_url = s3.generate_presigned_url(
                'get_object',
                params={
                    'Bucket': s3.BUCKET_NAME,
                    'Key': bed_file['s3_path'],
                    'ResponseContentDisposition': f"attachment; filename=\"{bed_file['filename']}\""
                },
                expires_in=3600
            )
        except ClientError as e:
            raise fastapi.HTTPException(status_code=500, detail="Failed to generate download URL") from e

        # Return the presigned URL for the frontend to download
        return JSONResponse({
            "download_url": presigned_url,
            "filename": bed_file['filename']
        })

    except fastapi.HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=f"Failed to download BED file: {str(e)}")


@router.delete("/bed-files/{dataset_name}")
async def delete_bed_file_endpoint(dataset_name: str, user: User = Depends(get_current_user)):
    try:
        # Delete from database
        success = database_utils.delete_bed_file(get_db(), user.username, dataset_name)

        if not success:
            raise fastapi.HTTPException(status_code=404, detail="BED file not found")

        # Delete S3 files (both the BED file and metadata)
        s3_base_path = s3.get_bed_s3_path(user.username, dataset_name)
        s3.clear_dir(s3_base_path)

        return Response(status_code=200)
    except fastapi.HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=f"Failed to delete BED file: {str(e)}")


class FalconUploadFile(BaseModel):
    name: str
    size: int


class FalconUploadUrlsRequest(BaseModel):
    files: list[FalconUploadFile]


class FalconRunTokenRequest(BaseModel):
    dataset_name: str


_RUN_SH_TMPL = Path(__file__).parent.parent / "static" / "run.sh.tmpl"

# Mounted at the application root (not under /api), so it lives on its own
# router. The auth-injection loop in create_app() iterates `router.routes`
# and does not touch this one, so no exclusion-set bookkeeping is needed.
top_router = fastapi.APIRouter()


@top_router.get("/run.sh", include_in_schema=False)
async def serve_run_sh(request: Request):
    body = _RUN_SH_TMPL.read_text().replace(
        "{{GWAS_CE_BASE_URL}}", str(request.base_url).rstrip("/")
    )
    return Response(content=body, media_type="text/x-shellscript")


def get_s3_path(dataset: str, user: User, filename: str = None) -> str:
    return s3.get_gwas_s3_key(user.username, dataset, filename)

@router.get("/get-pre-signed-url/{dataset}")
async def get_hermes_pre_signed_url(dataset: str, filename: str = Query(None), user: User = Depends(get_current_user)):
    s3_path = get_s3_path(dataset, user, filename)
    try:
        presigned_url = s3.generate_presigned_url(
            'put_object',
            params={'Bucket': s3.BUCKET_NAME, 'Key': s3_path},
            expires_in=7200
        )
    except ClientError as e:
        raise fastapi.HTTPException(status_code=500, detail="Failed to generate presigned URL") from e
    return {"presigned_url": presigned_url, "s3_path": s3_path}

@router.post("/finalize-upload")
async def finalize_upload(request: DatasetInfo, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    s3_path = get_s3_path(request.name, user)
    s3.upload_metadata(request, s3_path)
    if not database_utils.insert_dataset(get_db(), user.username, request):
        raise fastapi.HTTPException(status_code=409, detail="Failed to insert dataset")

    # Capture the GWAS file's SHA256 for FALCON cryptographic binding.
    # Synchronous — typical GWAS files are tens to a few hundred MB and
    # hash in seconds. Larger files can be moved to a background task later.
    gwas_key = get_s3_path(request.name, user, request.file)
    try:
        gwas_sha256 = s3.compute_object_sha256(gwas_key)
        database_utils.set_dataset_gwas_sha256(
            get_db(), user.username, request.name, gwas_sha256,
        )
    except ClientError:
        # The dataset row is in; we just don't have a hash. FALCON for this
        # dataset will be gated with a "re-upload to enable" banner per spec.
        # Logging only — do not fail the upload.
        logging.warning(
            "could not hash uploaded GWAS at %s; gwas_sha256 left NULL", gwas_key,
        )

    return Response(status_code=200)

@router.delete("/delete-dataset/{dataset}")
async def delete_dataset(dataset: str, user: User = Depends(get_current_user)):
    s3_path = get_s3_path(dataset, user).replace('/raw', '')
    s3.clear_dir(s3_path)
    database_utils.delete_dataset(get_db(), user.username, dataset)
    return Response(status_code=200)


def _require_owned_dataset(user: User, dataset: str) -> None:
    """Raise 404 if the user does not own a dataset with this name."""
    from sqlalchemy import text
    with get_db() as conn:
        row = conn.execute(text(
            "SELECT 1 FROM datasets WHERE id=:id AND uploaded_by=:user"
        ), {
            "id": database_utils.get_dataset_hash(dataset, user.username),
            "user": user.username,
        }).fetchone()
    if row is None:
        raise fastapi.HTTPException(
            status_code=404, detail=f"dataset {dataset!r} not found for this user",
        )


def _lookup_user_id(username: str) -> int:
    """Return the users.id for a given user_name, or raise 401 if missing."""
    from sqlalchemy import text
    with get_db() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE user_name = :u"),
            {"u": username},
        ).fetchone()
    if row is None:
        raise fastapi.HTTPException(status_code=401, detail="user not found")
    return int(row[0])


def _username_for(user_id: int) -> str:
    """Return the user_name for a given users.id, or raise 404 if missing."""
    from sqlalchemy import text
    with get_db() as conn:
        row = conn.execute(
            text("SELECT user_name FROM users WHERE id = :u"),
            {"u": user_id},
        ).first()
    if not row:
        raise fastapi.HTTPException(status_code=404, detail="user not found")
    return row.user_name


async def get_falcon_token_principal(request: Request) -> FalconPrincipal:
    """Token-only auth dependency for FALCON CLI endpoints with no dataset
    path param (e.g. `GET /api/falcon/dataset`).

    Unlike `get_falcon_principal`, this rejects session JWTs outright — the
    token's bound dataset is the only way to identify the dataset, so a
    bearer JWT carries no useful binding here.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise fastapi.HTTPException(status_code=401, detail="missing bearer token")
    raw = auth.split(" ", 1)[1].strip()
    if not raw.startswith(falcon_tokens.PREFIX):
        raise fastapi.HTTPException(status_code=401, detail="expected falcon token")
    principal = falcon_tokens.lookup(raw)
    if principal is None:
        raise fastapi.HTTPException(status_code=401, detail="invalid or expired token")
    return principal


async def get_falcon_principal(
    dataset: str,
    request: Request,
) -> FalconPrincipal:
    """Auth dependency that accepts either a session JWT or a `dft_` CLI token.

    Both paths enforce dataset ownership: the token path requires the token's
    bound dataset to match the path param, and the JWT path requires the
    authenticated user to own the dataset (via `_require_owned_dataset`).
    """
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise fastapi.HTTPException(status_code=401, detail="missing bearer token")
    raw = auth.split(" ", 1)[1].strip()

    if raw.startswith(falcon_tokens.PREFIX):
        principal = falcon_tokens.lookup(raw)
        if principal is None:
            raise fastapi.HTTPException(status_code=401, detail="invalid or expired token")
        if principal.dataset_name != dataset:
            raise fastapi.HTTPException(status_code=403, detail="token not valid for this dataset")
        return principal

    # JWT path — reuse existing session auth.
    # get_current_user is a FastAPI dependency that accepts the Authorization
    # header value (Optional[str]); call it directly with the same value.
    user = await get_current_user(authorization=auth)
    _require_owned_dataset(user, dataset)
    return FalconPrincipal(user_id=_lookup_user_id(user.username), dataset_name=dataset)


# Test-only probe route — exists only to exercise the dependency in tests.
if os.environ.get("TEST_MODE") == "true":
    @router.get("/_falcon_principal_probe/{dataset}")
    async def _falcon_principal_probe(
        dataset: str,
        principal: FalconPrincipal = Depends(get_falcon_principal),
    ):
        return {"user_id": principal.user_id, "dataset_name": principal.dataset_name}


@router.post("/falcon/run-token")
async def falcon_run_token(
    request: FalconRunTokenRequest,
    user: User = Depends(get_current_user),
):
    """Mint a dataset-scoped CLI token for the FALCON installer.

    Ownership of the dataset is enforced.
    """
    _require_owned_dataset(user, request.dataset_name)
    user_id = _lookup_user_id(user.username)
    token, expires_at = falcon_tokens.mint(user_id, request.dataset_name)
    # expires_at is tz-aware (UTC); isoformat() yields "...+00:00"
    return {"token": token, "expires_at": expires_at.isoformat()}


@router.get("/falcon/dataset")
async def falcon_dataset(
    request: Request,
    principal: FalconPrincipal = Depends(get_falcon_token_principal),
):
    """Return the metadata `run.sh` needs for a FALCON installer run.

    Token-auth only — the bound token identifies both user and dataset.
    v1 ships hardcoded constants for `sample_size`, `inf_heritability`,
    and `chr_to_update`; these were previously hardcoded in the Vue
    panel that the CLI installer replaces.
    """
    username = _username_for(principal.user_id)
    sha, gwas_filename, col_map = database_utils.get_dataset_falcon_meta(
        get_db(), username=username, name=principal.dataset_name,
    )
    base_url = str(request.base_url).rstrip("/")
    gwas_key = s3.get_gwas_s3_key(username, principal.dataset_name, gwas_filename or "gwas.tsv")
    try:
        gwas_download_url = s3.generate_presigned_url(
            "get_object", {"Bucket": s3.BUCKET_NAME, "Key": gwas_key}, 7200,
        )
    except ClientError:
        gwas_download_url = None
    from job_server import falcon as falcon_mod
    return {
        "dataset_name": principal.dataset_name,
        "gwas_filename": gwas_filename or "gwas.tsv",
        "expected_gwas_sha256": sha,
        "gwas_download_url": gwas_download_url,
        "sumstats_columns": falcon_mod.col_map_to_sumstats_columns(col_map),
        "sample_size": 625000,
        "inf_heritability": 0.1212,
        "chr_to_update": "1-22",
        "image": "sagehen03/falcon:latest",
        "web_app_base_url": base_url,
    }


@router.post("/falcon/{dataset}/upload-urls")
async def falcon_upload_urls(
    dataset: str,
    request: FalconUploadUrlsRequest,
    principal: FalconPrincipal = Depends(get_falcon_principal),
):
    """Return one presigned PUT URL per filename for FALCON result objects."""
    uploads = []
    for f in request.files:
        key = s3.get_falcon_s3_prefix(_username_for(principal.user_id),
                                       principal.dataset_name, f.name)
        try:
            url = s3.generate_presigned_url(
                'put_object',
                params={'Bucket': s3.BUCKET_NAME, 'Key': key},
                expires_in=7200,
            )
        except ClientError as e:
            raise fastapi.HTTPException(
                status_code=500, detail="Failed to generate presigned URL",
            ) from e
        uploads.append({"name": f.name, "url": url})
    return {"uploads": uploads}


@router.post("/falcon/{dataset}/finalize")
async def falcon_finalize(
    dataset: str,
    principal: FalconPrincipal = Depends(get_falcon_principal),
):
    """Validate the uploaded FALCON manifest and mark FALCON SUCCEEDED.

    Reads the manifest from s3://.../falcon/manifest.json, validates it
    against the dataset's gwas_sha256, then writes a workflow_jobs row
    with method='falcon', status='SUCCEEDED'. On validation failure,
    deletes the uploaded falcon/ prefix and returns a structured 409.
    """
    from job_server import falcon as falcon_mod
    username = _username_for(principal.user_id)

    manifest_key = s3.get_falcon_s3_prefix(username, dataset, "manifest.json")
    s3_client = boto3.client("s3")
    try:
        obj = s3_client.get_object(Bucket=s3.BUCKET_NAME, Key=manifest_key)
        manifest = json.loads(obj["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "NoSuchKey":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "missing_manifest",
                    "detail": (
                        "No manifest.json found at the falcon prefix. Your "
                        "FALCON image may be too old; pull sagehen03/falcon:latest."
                    ),
                },
            )
        raise fastapi.HTTPException(
            status_code=500, detail="Failed to read manifest",
        ) from e
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_manifest_json", "detail": str(e)},
        )

    gwas_sha = database_utils.get_dataset_gwas_sha256(get_db(), username, dataset)
    try:
        falcon_mod.validate_manifest(manifest, dataset, gwas_sha)
    except falcon_mod.FalconManifestError as e:
        # Validation failed — clean up the uploaded falcon/ objects so
        # they don't accumulate as orphans. The dataset's GWAS at
        # raw/<file> is untouched (different prefix).
        falcon_prefix = s3.get_falcon_s3_prefix(username, dataset)
        try:
            s3.clear_dir(falcon_prefix)
        except ClientError:
            logging.warning(
                "failed to clean up falcon/ prefix after validation error",
                exc_info=True,
            )
        return JSONResponse(
            status_code=409,
            content={
                "error": e.code,
                "detail": str(e),
                "expected": e.expected,
                "got": e.got,
            },
        )

    database_utils.record_falcon_success(get_db(), username, dataset)
    return {"status": "SUCCEEDED"}


@router.get("/falcon/{dataset}/result-urls")
async def falcon_result_urls(
    dataset: str,
    user: User = Depends(get_current_user),
):
    """Return a map of filename → presigned GET URL + ETag + size for each
    FALCON result object stored for this dataset.

    The ETag lets the frontend cache parsed `.wg.*` data in IndexedDB keyed
    by (dataset, file, etag) and skip the network round-trip when nothing
    has changed.
    """
    _require_owned_dataset(user, dataset)

    prefix = s3.get_falcon_s3_prefix(user.username, dataset) + "/"
    s3_client = boto3.client("s3")
    files: dict = {}
    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=s3.BUCKET_NAME, Prefix=prefix):
            for obj in page.get("Contents", []):
                name = obj["Key"][len(prefix):]
                if not name:
                    continue
                url = s3.generate_presigned_url(
                    "get_object",
                    params={"Bucket": s3.BUCKET_NAME, "Key": obj["Key"]},
                    expires_in=7200,
                )
                files[name] = {
                    "url": url,
                    "etag": obj.get("ETag", "").strip('"'),
                    "size": obj.get("Size", 0),
                }
    except ClientError as e:
        raise fastapi.HTTPException(
            status_code=500, detail="Failed to list FALCON results",
        ) from e

    return {"files": files}


job_queues: Dict[str, Queue] = {}

@router.get("/job-status/{job_id}")
async def job_status(job_id: str):
    if job_id not in job_queues:
        job_queues[job_id] = Queue()

    async def event_generator():
        try:
            while True:
                try:
                    if job_id not in job_queues:
                        status = database_utils.get_job_status(get_db(), job_id)
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "status": status,
                                "dataset": job_id,
                            })
                        }
                        break
                    data = await asyncio.wait_for(job_queues[job_id].get(), timeout=30.0)
                    yield {
                        "event": "message",
                        "data": json.dumps(data)
                    }
                    if data["status"].endswith("SUCCEEDED") or data["status"].endswith("FAILED"):
                        break
                except asyncio.TimeoutError:
                    yield {
                        "event": "keepalive",
                        "data": ""
                    }
        finally:
            if job_queues.get(job_id) and job_queues[job_id].empty():
                del job_queues[job_id]

    return EventSourceResponse(event_generator())

async def start_job(user: User, dataset: str, method: str, background_tasks: BackgroundTasks, prefix: str = ""):
    database_utils.log_job_start(get_db(), user.username, dataset, f"RUNNING {method}", prefix=prefix)
    background_tasks.add_task(batch.submit_and_await_job, {
        'jobName': 'dig-sldsc-methods',
        'jobQueue': 'sldsc-methods-job-queue',
        'jobDefinition': 'dig-sldsc-methods',
        'parameters': {
            'username': user.username,
            'dataset': dataset,
            'method': method
        }}, user.username, dataset, method, job_queues, prefix)

@router.post("/start-analysis")
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks,
                         user: User = Depends(get_current_user)):
    prefix = "bed:" if request.method == AnalysisMethod.annot_sldsc else ""
    job_id = database_utils.get_dataset_hash(request.dataset, user.username, prefix=prefix)
    if job_id not in job_queues:
        job_queues[job_id] = Queue()
    await start_job(user, request.dataset, request.method.value, background_tasks, prefix=prefix)
    return {"job_id": job_id}


async def start_sifter_job(user: User, dataset: str, background_tasks: BackgroundTasks):
    """Kick off the variant-sifter prep pipeline for one dataset (Batch job).

    Mirrors start_job: log RUNNING synchronously, then submit + await in the
    background. Uses the unprefixed dataset hash as both the GUID and the
    job_queues key, so the existing /job-status/{job_id} SSE streams progress.
    """
    database_utils.log_job_start(
        get_db(), user.username, dataset, f"RUNNING {variant_sifter.SIFTER_METHOD}",
    )
    guid = database_utils.get_dataset_hash(dataset, user.username)
    background_tasks.add_task(
        batch.submit_and_await_job,
        variant_sifter.sifter_job_config(user.username, dataset, guid),
        user.username, dataset, variant_sifter.SIFTER_METHOD, job_queues, "",
    )


@router.post("/variant-sifter/run/{dataset}")
async def run_variant_sifter(dataset: str, background_tasks: BackgroundTasks,
                             user: User = Depends(get_current_user)):
    _require_owned_dataset(user, dataset)
    job_id = database_utils.get_dataset_hash(dataset, user.username)
    if job_id not in job_queues:
        job_queues[job_id] = Queue()
    await start_sifter_job(user, dataset, background_tasks)
    return {"job_id": job_id}


def get_s3_results_path(dataset: str, user: User, dataset_type: str, method_group: str, method: str) -> str:
    return f"userdata/{user.username}/{dataset_type}/{dataset}/{method_group}/{method}"


@router.get("/download/{dataset}")
async def download_hermes_file(dataset: str, result_type: str = Query('sldsc', description="Type of results to download"), user: User = Depends(get_current_user)):
    result_type_lower = result_type.lower()
    if result_type_lower == 'magma':
        s3_path = get_s3_results_path(dataset, user, 'genetic', 'magma', 'genes')
        df = get_cached_results(s3_path, 'associations.genes.json.gz', 'magma', True)
        filename = f"{dataset}_magma_results.tsv"
    elif result_type_lower == 'pigean':
        s3_path = get_s3_results_path(dataset, user, 'genetic', 'pigean', 'pigean')
        df = get_cached_results(s3_path, 'gene_stats.json.gz', 'pigean', True)
        filename = f"{dataset}_pigean_gene_results.tsv"
    else:
        s3_path = get_s3_results_path(dataset, user, 'genetic', 'sldsc', 'sldsc')
        df = get_cached_results(s3_path, 'tissue.output.tsv', 'sldsc', False)
        filename = f"{dataset}_ldsc_results.tsv"

    return Response(content=df.to_csv(sep='\t', index=False),
                       media_type='text/tab-separated-values',
                       headers={
                           'Content-Disposition': f'attachment; filename="{filename}"'
                       })


def get_dataframe(data: TextIO, file_type: str) -> pd.DataFrame:
    if file_type == 'sldsc':
        return pd.read_csv(data, sep='\t', names=['annotation', 'tissue', 'biosample', 'enrichment', 'pValue'])
    if file_type == 'annot-sldsc':
        return pd.read_csv(data, sep='\t', names=['phenotype', 'ancestry', 'annotation', 'enrichment', 'pValue'])
    elif file_type in ['magma', 'pigean']:
        return pd.DataFrame.from_records(map(json.loads, data.readlines()))


@lru_cache(maxsize=16)
def get_cached_results(s3_path: str, file: str, file_type: str, is_compressed: bool) -> pd.DataFrame:
    try:
        if is_compressed:
            with gzip.open(s3.get_results(s3_path, file)['Body'], 'rt') as f:
                df = get_dataframe(f, file_type)
        else:
            df = get_dataframe(s3.get_results(s3_path, file)['Body'], file_type)
        if 'pValue' in df.columns:
            df['pValue'] = pd.to_numeric(df['pValue'])
        return df
    except ClientError as e:
        raise fastapi.HTTPException(status_code=500, detail="Failed to fetch results") from e


def filter_results(
        df: pd.DataFrame,
        request: Request,
        sort_field: str = Query('pValue', description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
):
    filter_params = {}
    for param, value in request.query_params.items():
        if param.startswith("filter_") and value:
            column_name = param.replace("filter_", "")
            filter_params[column_name] = value

    for column, value in filter_params.items():
        if column in df.columns:
            if df[column].dtype.kind in 'ifc':
                try:
                    if value.startswith(">="):
                        df = df[df[column] >= float(value[2:])]
                    elif value.startswith("<="):
                        df = df[df[column] <= float(value[2:])]
                    elif value.startswith(">"):
                        df = df[df[column] > float(value[1:])]
                    elif value.startswith("<"):
                        df = df[df[column] < float(value[1:])]
                    else:
                        df = df[df[column] == float(value)]
                except ValueError:
                    pass
            else:
                if value.startswith("eq:"):
                    df = df[df[column].astype(str).str.lower() == value[3:].lower()]
                elif value.startswith("contains:"):
                    df = df[df[column].astype(str).str.contains(value[9:], case=False, na=False)]
                else:
                    df = df[df[column].astype(str).str.contains(value, case=False, na=False)]

    ascending = sort_order == 1
    df = df.sort_values(by=sort_field, ascending=ascending)
    return df


@router.get("/results/{dataset}")
async def get_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('pValue', description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'genetic', 'sldsc', 'sldsc')

    try:
        # Get workflow status to extract job ID
        workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

        # Try to get job ID from SLDSC or LDSC workflow
        job_id = None
        if 'sldsc' in workflow_status and 'sldsc' in workflow_status['sldsc']:
            job_id = workflow_status['sldsc']['sldsc'].get('job_id')
        elif 'ldsc' in workflow_status and 'ldsc' in workflow_status['ldsc']:
            job_id = workflow_status['ldsc']['ldsc'].get('job_id')

        # Fallback to dataset name if no specific job ID found
        if not job_id:
            job_id = dataset

        df = get_cached_results(s3_path, 'tissue.output.tsv', 'sldsc', False)
        df = filter_results(df, request, sort_field, sort_order)

        total_records = len(df)
        tissues = df['tissue'].unique().tolist()
        biosamples = df['biosample'].unique().tolist()
        annotations = df['annotation'].unique().tolist()
        df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "tissues": tissues,
            "biosamples": biosamples,
            "annotations": annotations,
            "jobId": job_id,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/magma-results/{dataset}")
async def get_magma_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('pValue', description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'genetic', 'magma', 'genes')

    try:
        # Get workflow status to extract job ID
        workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

        # Try to get job ID from MAGMA workflow
        job_id = None
        if 'magma' in workflow_status and 'magma' in workflow_status['magma']:
            job_id = workflow_status['magma']['magma'].get('job_id')

        # Fallback to dataset name if no specific job ID found
        if not job_id:
            job_id = dataset

        df = get_cached_results(s3_path, 'associations.genes.json.gz', 'magma', True)
        df = filter_results(df, request, sort_field, sort_order)

        total_records = len(df)
        genes = df['gene'].unique().tolist()
        df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "genes": genes,
            "jobId": job_id,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/annot-sldsc-results/{dataset}")
async def get_annot_sldsc_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('pValue', description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'annotation', 'sldsc', 'annot-sldsc')

    # Get workflow status to extract job ID
    workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

    # Try to get job ID from MAGMA workflow
    job_id = None
    if 'annot-sldsc' in workflow_status and 'annot-sldsc' in workflow_status['annot-sldsc']:
        job_id = workflow_status['annot-sldsc']['annot-sldsc'].get('job_id')

    # Fallback to dataset name if no specific job ID found
    if not job_id:
        job_id = dataset

    try:
        df = get_cached_results(s3_path, 'custom.output.tsv', 'annot-sldsc', False)
        df = filter_results(df, request, sort_field, sort_order)

        total_records = len(df)
        phenotypes = df['phenotype'].unique().tolist()
        df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "phenotypes": phenotypes,
            "jobId": job_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/magma-pathways-results/{dataset}")
async def get_magma_pathways_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('pValue', description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    # Correct S3 path with all 5 parameters
    s3_path = get_s3_results_path(dataset, user, 'genetic', 'magma', 'genes')

    try:
        # Get workflow status to extract job ID
        workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

        # Try to get job ID from MAGMA workflow
        job_id = None
        if 'magma' in workflow_status and 'magma' in workflow_status['magma']:
            job_id = workflow_status['magma']['magma'].get('job_id')

        # Fallback to dataset name if no specific job ID found
        if not job_id:
            job_id = dataset

        df = get_cached_results(s3_path, 'associations.pathways.json.gz', 'magma', True)
        df = filter_results(df, request, sort_field, sort_order)

        total_records = len(df)
        pathways = df['pathwayName'].unique().tolist()
        df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "pathways": pathways,
            "jobId": job_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pigean-gene-results/{dataset}")
async def get_pigean_gene_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('combined', description="Field to sort by"),
        sort_order: int = Query(-1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'genetic', 'pigean', 'pigean')

    # Get workflow status to extract job ID
    workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

    # Try to get job ID from MAGMA workflow
    job_id = None
    if 'pigean' in workflow_status and 'pigean' in workflow_status['pigean']:
        job_id = workflow_status['pigean']['pigean'].get('job_id')

    # Fallback to dataset name if no specific job ID found
    if not job_id:
        job_id = dataset

    try:
        df = get_cached_results(s3_path, 'gene_stats.json.gz', 'pigean', True)
        df = filter_results(df, request, sort_field, sort_order)

        # Replace inf/-inf/nan with None for JSON serialization
        df = df.replace([np.inf, -np.inf], np.nan).replace({np.nan: None})

        total_records = len(df)
        genes = df['gene'].unique().tolist()

        # Apply pagination (skip if rows=-1 to return all)
        if rows != -1:
            df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        gene_gene_set_records = {}
        sub_df = get_cached_results(s3_path, 'gene_gene_set_stats.json.gz', 'pigean', True) \
            .replace([np.inf, -np.inf], np.nan) \
            .replace({np.nan: None}) \
            .groupby('gene')
        for row in results:
            if row['gene'] in sub_df.groups:
                row['gene_sets'] = sub_df.get_group(row['gene']).to_dict('records')
            else:
                row['gene_sets'] = []

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "genes": genes,
            "jobId": job_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pigean-gene-set-results/{dataset}")
async def get_pigean_gene_set_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: str = Query('beta_uncorrected', description="Field to sort by"),
        sort_order: int = Query(-1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'genetic', 'pigean', 'pigean')

    # Get workflow status to extract job ID
    workflow_status = database_utils.get_workflow_status_summary(get_db(), user.username, dataset)

    # Try to get job ID from MAGMA workflow
    job_id = None
    if 'pigean' in workflow_status and 'pigean' in workflow_status['pigean']:
        job_id = workflow_status['pigean']['pigean'].get('job_id')

    # Fallback to dataset name if no specific job ID found
    if not job_id:
        job_id = dataset

    try:
        df = get_cached_results(s3_path, 'gene_set_stats.json.gz', 'pigean', True)
        df = filter_results(df, request, sort_field, sort_order)

        # Replace inf/-inf/nan with None for JSON serialization
        df = df.replace([np.inf, -np.inf], np.nan).replace({np.nan: None})

        total_records = len(df)
        gene_sets = df['gene_set'].unique().tolist()

        # Apply pagination (skip if rows=-1 to return all)
        if rows != -1:
            df = df.iloc[first:first + rows]
        results = df.to_dict('records')

        sub_df = get_cached_results(s3_path, 'gene_gene_set_stats.json.gz', 'pigean', True) \
            .replace([np.inf, -np.inf], np.nan) \
            .replace({np.nan: None}) \
            .groupby('gene_set')
        for row in results:
            if row['gene_set'] in sub_df.groups:
                row['genes'] = sub_df.get_group(row['gene_set']).to_dict('records')
            else:
                row['genes'] = []

        return JSONResponse({
            "items": results,
            "totalRecords": total_records,
            "geneSets": gene_sets,
            "jobId": job_id
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
