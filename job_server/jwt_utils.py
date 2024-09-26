import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt

from job_server.model import User

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'test_key')
ALGORITHM = "HS256"
# one week
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(ZoneInfo('UTC')) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_encoded_jwt_data(user: User, expires_delta: timedelta = timedelta(days=10)):
    to_encode = user.model_dump()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)


def get_decoded_jwt_data(cookie_data: str) -> dict:
    return jwt.decode(cookie_data, JWT_SECRET_KEY, algorithms=[ALGORITHM])
