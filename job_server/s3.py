import os

BUCKET_NAME = os.getenv('JOB_SERVER_BUCKET', 'dig-ldsc-server')


def get_bucket_path(path: str, file_name: str) -> str:
    return f"s3://{BUCKET_NAME}/{path}/{file_name}"
