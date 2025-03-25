import asyncio
import time

import boto3

from job_server import database_utils
from job_server.database import get_db

S3_REGION = 'us-east-1'

async def submit_and_await_job(job_config, user, dataset, method, job_queues):
    batch_client = boto3.client('batch', region_name=S3_REGION)

    response = batch_client.submit_job(**job_config)
    job_id = response['jobId']
    logs_client = boto3.client('logs', region_name=S3_REGION)
    while True:
        response = batch_client.describe_jobs(jobs=[job_id])
        job_status = response['jobs'][0]['status']
        if job_status in ['SUCCEEDED', 'FAILED']:
            log_stream_name = response['jobs'][0]['container']['logStreamName']
            log_group_name = '/aws/batch/job'
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name
            )
            log_messages = [event['message'] for event in log_events['events']]
            complete_log = '\n'.join(log_messages)
            status = f"{method} {job_status}"
            database_utils.log_job_end(get_db(), user, dataset, status, complete_log)
            job_id = database_utils.get_dataset_hash(dataset, user)
            if job_id in job_queues:
                await job_queues[job_id].put({
                    "status": status,
                    "dataset": dataset,
                    "method": method
                })
            return

        await asyncio.sleep(60)

