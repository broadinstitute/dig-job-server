from enum import Enum

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

class AnalysisMethod(str, Enum):
    sumstats = "sumstats"
    sldsc = "sldsc"


class AnalysisRequest(BaseModel):
    dataset: str
    method: AnalysisMethod

