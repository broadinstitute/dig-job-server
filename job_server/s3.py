import json

import boto3
import os

BUCKET_NAME = os.getenv('JOB_SERVER_BUCKET', 'dig-ldsc-server')


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
    s3_client = boto3.client('s3')
    return s3_client.generate_presigned_url(param, Params=params, ExpiresIn=expires_in)


def upload_metadata(metadata, path):
    s3_client = boto3.client('s3')
    s3_client.put_object(Bucket=BUCKET_NAME, Key=f"{path}/metadata", Body=json.dumps(metadata.dict()).encode('utf-8'))
