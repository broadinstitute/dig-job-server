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

class CredibleSetInfo(BaseModel):
    """The `metadata` object stored beside an uploaded credible set in S3.

    This is what the pipeline reads (name for display, slug for keys and set
    ids, col_map to canonicalise the file). The DB row exists for the UI.
    """
    name: str
    slug: str
    file: str
    separator: str
    col_map: dict
    uploaded_at: str  # ISO 8601, informational; status derivation uses the DB row

class AnalysisMethod(str, Enum):
    sldsc = "sldsc"
    magma = "magma"
    annot_sldsc = "annot-sldsc"
    pigean = "pigean"
    falcon = "falcon"

class AnalysisRequest(BaseModel):
    dataset: str
    method: AnalysisMethod

