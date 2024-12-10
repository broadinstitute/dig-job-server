import io
from typing import Optional

import fastapi
import re
import smart_open
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, Header, UploadFile, Query
from starlette.requests import Request
from starlette.responses import Response
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import S3Target

from job_server import s3, file_utils
from job_server.auth_backend import AuthBackend
from job_server.jwt_utils import create_access_token, get_decoded_jwt_data, get_encoded_jwt_data
from job_server.model import UserCredentials, User, DatasetInfo

router = fastapi.APIRouter()
JOB_SERVER_AUTH_COOKIE = 'js_auth'

def get_auth_backend() -> AuthBackend:
    # Replace with logic to select the appropriate backend
    from job_server.auth_mysql import MySQLAuthBackend
    from job_server.database import get_db
    return MySQLAuthBackend(get_db())


@router.post("/login")
async def login(response: Response, credentials: UserCredentials, auth_backend: AuthBackend = Depends(get_auth_backend)):
    if not auth_backend.authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=403, detail="Incorrect username or password")

    response.set_cookie(key=JOB_SERVER_AUTH_COOKIE, httponly=True,
                        value=get_encoded_jwt_data(User(username=credentials.username)),
                        domain='localhost', samesite='strict',
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

@router.post("/upload")
async def upload_file(request: Request, user: User = Depends(get_current_user)):
    filename = request.headers.get('Filename')
    dataset = request.headers.get('DatasetName')
    if not filename:
        raise HTTPException(status_code=422, detail="Filename header is required")
    if not dataset:
        raise HTTPException(status_code=422, detail="Dataset name header is required")
    parser = StreamingFormDataParser(request.headers)
    s3_path = s3.get_bucket_path(f"userdata/{user.username}/genetic/{dataset}/raw", filename)
    parser.register("file", GzipS3Target(s3_path, mode='wb'))
    async for chunk in request.stream():
        parser.data_received(chunk)
    return {"s3_path": s3_path}

@router.post("/preview-delimited-file")
async def preview_files(file: UploadFile):
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
    return {"columns": [column for column in df.columns]}


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



class GzipS3Target(S3Target):
    def __init__(self, path, mode='wb', transport_params=None):
        super().__init__(path, mode, transport_params)

    def on_start(self):
        self._fd = smart_open.open(
            self._file_path,
            self._mode,
            compression='disable',
            transport_params=self._transport_params,
        )


