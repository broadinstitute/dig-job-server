import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from database_utils import authenticate_user
from jwt_utils import create_access_token, JWT_SECRET_KEY, ALGORITHM
from model import UserCredentials

app = FastAPI()

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


@app.post("/login")
def login(credentials: UserCredentials, db=Depends(get_db)):
    if not authenticate_user(db, credentials.username, credentials.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": credentials.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me")
def upload_file(current_user: str = Depends(get_current_user)):
    return {"user": current_user}
