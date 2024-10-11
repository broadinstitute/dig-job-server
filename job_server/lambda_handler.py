import os

import boto3
from mangum import Mangum
from job_server.server import create_app

env = os.getenv('ENVIRONMENT', 'qa')
db_url = boto3.client('secretsmanager').get_secret_value(SecretId=f"dig-job-server/{env}/db-url")['SecretString']
os.environ['DIG_JOB_SERVER_DB'] = db_url


app = create_app()

handler = Mangum(app)
