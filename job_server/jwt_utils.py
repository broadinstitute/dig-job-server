import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt

ALGORITHM = "HS256"
# one week
ACCESS_TOKEN_EXPIRE_MINUTES = 60*24*7

_jwt_secret = None

def get_jwt_secret():
    global _jwt_secret
    if _jwt_secret is None:
        _jwt_secret = os.getenv('JWT_SECRET_KEY', 'test_key')
    return _jwt_secret


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(ZoneInfo('UTC')) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt


def get_decoded_jwt_data(cookie_data: str) -> dict:
    return jwt.decode(cookie_data, get_jwt_secret(), algorithms=[ALGORITHM])
