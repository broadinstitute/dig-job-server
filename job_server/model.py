from enum import Enum
from typing import Union

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
    phenotype: Union[str, None]
    effective_n: Union[float, None]
    col_map: dict

class AnalysisMethod(str, Enum):
    sldsc = "sldsc"
    magma = "magma"
    annot_sldsc = "annot-sldsc"

class AnalysisRequest(BaseModel):
    dataset: str
    method: AnalysisMethod

