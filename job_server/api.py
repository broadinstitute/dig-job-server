import asyncio
import io
import json
import re
from asyncio import Queue
from functools import lru_cache
from typing import Optional, Dict

import fastapi
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

    if authorization:
        schema, _, token = authorization.partition(' ')
        if schema.lower() == 'bearer' and token:
            data = get_decoded_jwt_data(token)[0]
            if data:
                return User(**data)

    if token:
        data = get_decoded_jwt_data(token)[0]
        if data:
            return User(**data)

    raise fastapi.HTTPException(status_code=401, detail='Not logged in')


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
    data_set_metadata = database_utils.get_dataset_metadata(get_db(), user.username)

    # Create the dataset list
    datasets = [{'dataset': d,
             'uploaded_at': data_set_metadata.get(d, {}).get('uploaded_at', ''),
             'ancestry': data_set_metadata.get(d, {}).get('ancestry', ''),
             'file_name': data_set_metadata.get(d, {}).get('file', ''),
             'genome_build': data_set_metadata.get(d, {}).get('genome_build', ''),
             'phenotype': data_set_metadata.get(d, {}).get('phenotype', ''),
             'uploaded_by': user.username,
             'status': jobs_for_user.get(database_utils.get_dataset_hash(d, user.username), {}).get('status'),
             'id': database_utils.get_dataset_hash(d, user.username)
             } for d in data_set_folders]

    # Sort datasets only if orderBy parameter is provided
    if orderBy and datasets:
        try:
            reverse = orderDir and orderDir.lower() == "desc"
            datasets.sort(key=lambda x: x.get(orderBy, ""), reverse=reverse)
        except Exception as e:
            # Log the error but continue without sorting
            print(f"Error sorting datasets: {str(e)}")

    return datasets

@router.get("/log-info/{job_id}")
async def get_log_info(job_id: str, user: User = Depends(get_current_user)):
    return database_utils.get_log_info(get_db(), user.username, job_id)

@router.post("/preview-delimited-file")
async def preview_file(file: UploadFile):
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
    await start_job(user, request.name, AnalysisMethod.sumstats.value, background_tasks)
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

async def start_job(user: User, dataset: str, method: str, background_tasks: BackgroundTasks):
    database_utils.log_job_start(get_db(), user.username, dataset, f"RUNNING {method}")
    background_tasks.add_task(batch.submit_and_await_job, {
        'jobName': 'dig-ldsc-methods',
        'jobQueue': 'ldsc-methods-job-queue',
        'jobDefinition': 'dig-ldsc-methods',
        'parameters': {
            'username': user.username,
            'dataset': dataset,
            'method': method
        }}, user.username, dataset, method, job_queues)

@router.post("/start-analysis")
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks,
                         user: User = Depends(get_current_user)):
    job_id = database_utils.get_dataset_hash(request.dataset, user.username)
    if job_id not in job_queues:
        job_queues[job_id] = Queue()
    await start_job(user, request.dataset, request.method.value, background_tasks)
    return {"job_id": job_id}


def get_s3_results_path(dataset: str, user: User) -> str:
    return f"userdata/{user.username}/genetic/{dataset}/sldsc/sldsc"

@router.get("/download/{dataset}")
async def download_hermes_file(dataset: str, user: User = Depends(get_current_user)):
    s3_path = get_s3_results_path(dataset, user)
    df = get_cached_results(s3_path)
    return Response(content=df.to_csv(sep='\t', index=False),
                       media_type='text/tab-separated-values',
                       headers={
                           'Content-Disposition': f'attachment; filename="{dataset}_results.tsv"'
                       })


@lru_cache(maxsize=16)
def get_cached_results(s3_path: str) -> pd.DataFrame:
    try:
        wrapped_text = io.TextIOWrapper(s3.get_results(s3_path)['Body'])
        df = pd.read_csv(wrapped_text, sep='\t',
                         names=['annotation', 'tissue', 'biosample', 'enrichment', 'pValue'])
        df['pValue'] = pd.to_numeric(df['pValue'])
        return df
    except ClientError as e:
        raise fastapi.HTTPException(status_code=500, detail="Failed to fetch tissue results") from e

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
    s3_path = get_s3_results_path(dataset, user)

    try:
        df = get_cached_results(s3_path)

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
            "annotations": annotations
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
