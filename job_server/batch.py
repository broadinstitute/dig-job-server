import asyncio
import time

import boto3

from job_server import database_utils
from job_server.database import get_db

S3_REGION = 'us-east-1'

# Most methods share one image and one job definition, selected by a --method
# parameter. FALCON does not: it is a separate image on its own queue at 16 vCPU,
# and its entrypoint takes --username/--dataset directly.
_SHARED_METHODS_JOB = {
    'jobName': 'dig-sldsc-methods',
    'jobQueue': 'sldsc-methods-job-queue',
    'jobDefinition': 'dig-sldsc-methods',
}
_FALCON_JOB = {
    'jobName': 'falcon-rs-dataset-job',
    'jobQueue': 'falcon-queue',
    'jobDefinition': 'falcon-rs-dataset-job',
}

# The converter's exit contract. Deliberately not 2, which argparse uses for any
# usage error -- see falcon_prep/cli.py.
FALCON_EXIT_MEANINGS = {
    10: 'dataset not supported: check ancestry (EUR only), genome build, '
        'and that the upload has an rsID column',
    11: 'no variants passed the significance threshold, so there was nothing '
        'to model',
}


def job_config(method: str, username: str, dataset: str) -> dict:
    """Batch submit_job kwargs for one method run."""
    if method == 'falcon':
        return {**_FALCON_JOB,
                'parameters': {'username': username, 'dataset': dataset}}
    return {**_SHARED_METHODS_JOB,
            'parameters': {'username': username, 'dataset': dataset,
                           'method': method}}


def failure_detail(method: str, container: dict) -> str:
    """A human-readable reason for a failure, when the method defines one.

    Without this a FALCON job that legitimately declined a dataset is
    indistinguishable in the UI from one that crashed.
    """
    if method != 'falcon':
        return ''
    code = container.get('exitCode')
    meaning = FALCON_EXIT_MEANINGS.get(code)
    return f' ({meaning})' if meaning else ''

async def submit_and_await_job(job_config, user, dataset, method, job_queues, prefix=""):
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

            container = response['jobs'][0].get('container', {})
            status = f"{method} {job_status}{failure_detail(method, container)}"
            database_utils.log_job_end(get_db(), user, dataset, status, complete_log, prefix=prefix)
            job_id = database_utils.get_dataset_hash(dataset, user, prefix=prefix)
            if job_id in job_queues:
                await job_queues[job_id].put({
                    "status": status,
                    "dataset": dataset,
                    "method": method
                })
            return

        await asyncio.sleep(60)

