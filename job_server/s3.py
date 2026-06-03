import boto3
import hashlib
import json
import os
from botocore.config import Config

BUCKET_NAME = os.getenv('JOB_SERVER_BUCKET', 'dig-ldsc-server')
_S3_CONFIG = Config(signature_version='s3v4')


def get_bucket_path(path: str, file_name: str) -> str:
    return f"s3://{BUCKET_NAME}/{path}/{file_name}"


def get_datasets(user_name: str) -> list[str]:
    client = boto3.client('s3')

    folder_names = []

    response = client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=f"userdata/{user_name}/genetic/", Delimiter='/')

    if 'CommonPrefixes' in response:
        for prefix in response['CommonPrefixes']:
            folder = prefix['Prefix'][len(f"userdata/{user_name}/genetic/"):-1]
            folder_names.append(folder)

    return folder_names


def generate_presigned_url(param, params, expires_in):
    s3_client = boto3.client('s3', config=_S3_CONFIG)
    return s3_client.generate_presigned_url(param, Params=params, ExpiresIn=expires_in)


def upload_metadata(metadata, path):
    s3_client = boto3.client('s3')
    s3_client.put_object(Bucket=BUCKET_NAME, Key=f"{path}/metadata", Body=json.dumps(metadata.dict()).encode('utf-8'))


def get_results(path, file):
    s3_client = boto3.client('s3')
    return s3_client.get_object(Bucket=BUCKET_NAME, Key=f"{path}/{file}")


def clear_dir(s3_path):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_path)

    for page in page_iterator:
        if "Contents" in page:
            delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
            s3.delete_objects(Bucket=BUCKET_NAME, Delete=delete_keys)


def get_bed_s3_path(user: str, dataset_name: str, filename: str = None) -> str:
    """Get S3 path for BED file uploads.
    
    Args:
        user: Username
        dataset_name: Name of the dataset
        filename: Optional filename to append to path
        
    Returns:
        S3 path for BED file storage
    """
    base_path = f"userdata/{user}/annotation/{dataset_name}/raw"
    if filename:
        return f"{base_path}/{filename}"
    return base_path


def upload_bed_metadata(user: str, dataset_name: str, filename: str):
    """Upload BED metadata file to S3.

    Args:
        user: Username
        dataset_name: Name of the dataset
        filename: Name of the BED file
    """
    s3_client = boto3.client('s3')

    # Create metadata object
    metadata = {
        "file": filename,
        "file_type": "bed",
        "ancestry": "EUR"
    }

    # Upload metadata file
    metadata_path = get_bed_s3_path(user, dataset_name, "metadata")
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=metadata_path,
        Body=json.dumps(metadata).encode('utf-8'),
        ContentType='application/json'
    )


_CHUNK_BYTES = 8 * 1024 * 1024  # 8 MB; matches the PEGS docker hasher


def compute_object_sha256(key: str) -> str:
    """Stream-hash an S3 object and return its hex SHA256.

    Mirrors the PEGS docker entrypoint's hasher (`manifest.sha256_of_file`)
    so the bytes we hash on the server are exactly the bytes a user gets
    from the presigned download URL. That equivalence is what allows
    FALCON's manifest input_sha256 to match this server-computed value.
    """
    s3_client = boto3.client('s3')
    obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
    h = hashlib.sha256()
    for chunk in obj['Body'].iter_chunks(chunk_size=_CHUNK_BYTES):
        h.update(chunk)
    return h.hexdigest()


def get_gwas_s3_key(user: str, dataset: str, filename: str | None = None) -> str:
    """S3 prefix (or full key when filename given) for a dataset's raw GWAS upload.

    Single source of truth for the `userdata/{user}/genetic/{dataset}/raw`
    convention used by both the upload path (api.get_s3_path) and the
    local-dev sync tool.
    """
    base = f"userdata/{user}/genetic/{dataset}/raw"
    return f"{base}/{filename}" if filename else base


def get_falcon_s3_prefix(user: str, dataset: str, filename: str = None) -> str:
    """S3 prefix (or full key when filename given) for FALCON result objects.

    Lives under the dataset's genetic prefix so the same dataset's GWAS and
    FALCON results share a tree. Mirrors get_s3_path / get_bed_s3_path.
    """
    base = f"userdata/{user}/genetic/{dataset}/falcon"
    return f"{base}/{filename}" if filename else base
