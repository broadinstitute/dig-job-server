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


def get_results(path):
    s3_client = boto3.client('s3')
    return s3_client.get_object(Bucket=BUCKET_NAME, Key=f"{path}/tissue.output.tsv")


def clear_dir(s3_path):
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=BUCKET_NAME, Prefix=s3_path)

    for page in page_iterator:
        if "Contents" in page:
            delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
            s3.delete_objects(Bucket=BUCKET_NAME, Delete=delete_keys)
