import fastapi
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from job_server import api
from job_server.api import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



for route in api.router.routes:
    if route.name not in {'login'}:
        route.dependencies.append(Depends(get_current_user))

app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

app.include_router(api.router, prefix='/api', tags=['api'])
