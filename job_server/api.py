import io
import os
from typing import Optional

import fastapi
import re
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Header, UploadFile, Query, BackgroundTasks
from starlette.requests import Request
from starlette.responses import Response

from job_server import s3, file_utils, batch
from job_server.auth_backend import AuthBackend
from job_server.jwt_utils import create_access_token, get_decoded_jwt_data, get_encoded_jwt_data
from job_server.model import UserCredentials, User, DatasetInfo, AnalysisRequest

router = fastapi.APIRouter()
JOB_SERVER_AUTH_COOKIE = 'js_auth'

def get_auth_backend() -> AuthBackend:
    # Replace with logic to select the appropriate backend
    from job_server.auth_mysql import MySQLAuthBackend
    from job_server.database import get_db
    return MySQLAuthBackend(get_db())


_cookie_domain_cache = None

def get_cookie_domain():
    global _cookie_domain_cache
    if _cookie_domain_cache is None:
        _cookie_domain_cache = os.getenv('COOKIE_DOMAIN', 'localhost')
    return _cookie_domain_cache

@router.post("/login")
async def login(response: Response, credentials: UserCredentials, auth_backend: AuthBackend = Depends(get_auth_backend)):
    if not auth_backend.authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=403, detail="Incorrect username or password")

    response.set_cookie(key=JOB_SERVER_AUTH_COOKIE, httponly=True,
                        value=get_encoded_jwt_data(User(username=credentials.username)),
                        domain=get_cookie_domain(), samesite='strict',
                        secure=False)

    access_token = create_access_token(data={"username": credentials.username})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(request: Request, authorization: Optional[str] = Header(None)):
    auth_cookie = request.cookies.get(JOB_SERVER_AUTH_COOKIE)
    if auth_cookie:
        data = get_decoded_jwt_data(auth_cookie)
        if data:
            user = User(**data)
            return user

    if authorization:
        schema, _, token = authorization.partition(' ')
        if schema.lower() == 'bearer' and token:
            data = get_decoded_jwt_data(token)
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
async def get_datasets(user: User = Depends(get_current_user)):
    data_set_folders = s3.get_datasets(user.username)
    return [{'dataset': d} for d in data_set_folders]

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
async def finalize_upload(request: DatasetInfo, user: User = Depends(get_current_user)):
    s3_path = get_s3_path(request.name, user)
    s3.upload_metadata(request, s3_path)
    return Response(status_code=200)

@router.post("/start-analysis")
async def start_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks,
                         user: User = Depends(get_current_user)):
    background_tasks.add_task(batch.submit_and_await_job, {
        'jobName': 'dig-ldsc-methods',
        'jobQueue': 'ldsc-methods-job-queue',
        'jobDefinition': 'dig-ldsc-methods',
        'parameters': {
            'username': user.username,
            'dataset': request.dataset,
            'method': request.method.value,
        }})
    return Response(status_code=202)

