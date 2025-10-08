import asyncio
import gzip
import io
import json
import os
import re
from asyncio import Queue
from functools import lru_cache
from typing import Dict, Optional, TextIO

import fastapi
import httpx
import pandas as pd
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Header, UploadFile, Query, BackgroundTasks
from sse_starlette import EventSourceResponse
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from job_server import s3, file_utils, batch, database_utils
from job_server.auth_backend import AuthBackend
from job_server.database import get_db
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
    contents = await file.read(100)
    await file.seek(0)

    if contents.startswith(b'\x1f\x8b'):
        sample_lines = await file_utils.get_compressed_sample(file)
    else:
        sample_lines = await file_utils.get_text_sample(file)

    df = await file_utils.parse_file(io.StringIO('\n'.join(sample_lines)), file.filename)
    dupes = file_utils.find_dupe_cols(sample_lines[0], ".csv" in file.filename, df.columns)
    if len(dupes) > 0:
        duped_col_str = ', '.join(set([re.sub(r"\.\d+$", '', dupe) for dupe in dupes]))
        raise fastapi.HTTPException(detail=f"{duped_col_str} specified more than once", status_code=400)
    return {"columns": [column for column in df.columns], "delimiter": "\t" if ".tsv" in file.filename else ","}


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

        # Generate presigned URL for download
        try:
            presigned_url = s3.generate_presigned_url(
                'get_object',
                params={'Bucket': s3.BUCKET_NAME, 'Key': bed_file['s3_path']},
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


def get_s3_path(dataset: str, user: User, filename: str=None) -> str:
    if filename:
        return f"userdata/{user.username}/genetic/{dataset}/raw/{filename}"
    else:
        return f"userdata/{user.username}/genetic/{dataset}/raw"

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
    return Response(status_code=200)

@router.delete("/delete-dataset/{dataset}")
async def delete_dataset(dataset: str, user: User = Depends(get_current_user)):
    s3_path = get_s3_path(dataset, user).replace('/raw', '')
    s3.clear_dir(s3_path)
    database_utils.delete_dataset(get_db(), user.username, dataset)
    return Response(status_code=200)

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



def get_s3_results_path(dataset: str, user: User, method_group: str, method: str) -> str:
    return f"userdata/{user.username}/genetic/{dataset}/{method_group}/{method}"


@router.get("/download/{dataset}")
async def download_hermes_file(dataset: str, result_type: str = Query('sldsc', description="Type of results to download"), user: User = Depends(get_current_user)):
    if result_type.lower() == 'magma':
        s3_path = get_s3_results_path(dataset, user, 'magma', 'genes')
        df = get_cached_results(s3_path, 'associations.genes.json.gz', 'magma', True)
        filename = f"{dataset}_magma_results.tsv"
    else:
        s3_path = get_s3_results_path(dataset, user, 'sldsc', 'sldsc')
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
    elif file_type == 'magma':
        return pd.DataFrame.from_records(map(json.loads, data.readlines()))


@lru_cache(maxsize=16)
def get_cached_results(s3_path: str, file: str, file_type: str, is_compressed: bool) -> pd.DataFrame:
    try:
        if is_compressed:
            with gzip.open(s3.get_results(s3_path, file)['Body'], 'rt') as f:
                df = get_dataframe(f, file_type)
        else:
            df = get_dataframe(s3.get_results(s3_path, file)['Body'], file_type)
        df['pValue'] = pd.to_numeric(df['pValue'])
        return df
    except ClientError as e:
        raise fastapi.HTTPException(status_code=500, detail="Failed to fetch results") from e


def filter_results(
        df: pd.DataFrame,
        request: Request,
        sort_field: Optional[str] = Query(None, description="Field to sort by"),
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

    if sort_field:
        ascending = sort_order == 1
        df = df.sort_values(by=sort_field, ascending=ascending)
    else:
        df = df.sort_values(by='pValue')
    return df


@router.get("/results/{dataset}")
async def get_results(
        dataset: str,
        request: Request,
        first: int = Query(0, description="First record index"),
        rows: int = Query(10, description="Number of rows per page"),
        sort_field: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'sldsc', 'sldsc')

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
        sort_field: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: int = Query(1, description="Sort order (1 for ascending, -1 for descending)"),
        user: User = Depends(get_current_user)
):
    s3_path = get_s3_results_path(dataset, user, 'magma', 'genes')

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
