from pydantic import BaseModel


class UserCredentials(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str

class DatasetInfo(BaseModel):
    name: str
    file: str
    ancestry: str
    separator: str
    genome_build: str
    col_map: dict
