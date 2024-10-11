from typing import Optional

import fastapi
import smart_open
from fastapi import Depends, HTTPException, Header
from starlette.requests import Request
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import S3Target

from job_server import s3
from job_server.auth_backend import AuthBackend
from job_server.jwt_utils import create_access_token, get_decoded_jwt_data
from job_server.model import UserCredentials, User

router = fastapi.APIRouter()
JOB_SERVER_AUTH_COOKIE = 'js_auth'

def get_auth_backend() -> AuthBackend:
    # Replace with logic to select the appropriate backend
    from job_server.auth_mysql import MySQLAuthBackend
    from job_server.database import get_db
    return MySQLAuthBackend(get_db())

@router.post("/login")
async def login(credentials: UserCredentials, auth_backend: AuthBackend = Depends(get_auth_backend)):
    if not auth_backend.authenticate_user(credentials.username, credentials.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"username": credentials.username})
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(request: Request, authorization: Optional[str] = Header(None)):
    auth_cookie = request.cookies.get(JOB_SERVER_AUTH_COOKIE)
    if auth_cookie:
        data = get_decoded_jwt_data(auth_cookie)
        if data:
            user = User(**data)
            user.api_token = auth_cookie
            return user

    if authorization:
        schema, _, token = authorization.partition(' ')
        if schema.lower() == 'bearer' and token:
            data = get_decoded_jwt_data(token)
            if data:
                return User(**data)

    raise fastapi.HTTPException(status_code=401, detail='Not logged in')

@router.post("/upload")
async def upload_file(request: Request, user: User = Depends(get_current_user)):
    filename = request.headers.get('Filename')
    if not filename:
        raise HTTPException(status_code=422, detail="Filename header is required")
    parser = StreamingFormDataParser(request.headers)
    parser.register("file", GzipS3Target(s3.get_bucket_path(f"userdata/{user.username}", filename), mode='wb'))
    async for chunk in request.stream():
        parser.data_received(chunk)
    return {"s3_path": s3.get_bucket_path(f"userdata/{user.username}", filename)}





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


