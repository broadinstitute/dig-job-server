import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import jwt

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
