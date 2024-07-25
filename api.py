import fastapi
import smart_open
from fastapi import Depends, HTTPException
from starlette.requests import Request
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import S3Target

import s3
from database import get_db
from database_utils import authenticate_user
from jwt_utils import create_access_token
from model import UserCredentials

router = fastapi.APIRouter()


@router.post("/login")
def login(credentials: UserCredentials, db=Depends(get_db)):
    if not authenticate_user(db, credentials.username, credentials.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": credentials.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/upload")
async def upload_file(request: Request):
    filename = request.headers.get('Filename')
    parser = StreamingFormDataParser(request.headers)
    parser.register("file", GzipS3Target(s3.get_bucket_path("ldscore/uploads", filename), mode='wb'))
    file_size = 0
    async for chunk in request.stream():
        file_size += len(chunk)
        parser.data_received(chunk)
    return {"file_size": file_size, "s3_path": s3.get_bucket_path("ldscore/uploads", filename)}


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


