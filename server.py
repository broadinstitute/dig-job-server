import fastapi
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

import api
from jwt_utils import JWT_SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username


for route in api.router.routes:
    if route.name not in {'login'}:
        route.dependencies.append(Depends(get_current_user))

app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

app.include_router(api.router, prefix='/api', tags=['api'])
