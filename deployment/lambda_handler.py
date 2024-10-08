import os
import socket

import boto3
from mangum import Mangum
from job_server.server import create_app

ssm = boto3.client('ssm')

def test_dns_resolution():
    try:
        ip = socket.gethostbyname('dig-bio-index.cxrzznxifeib.us-east-1.rds.amazonaws.com')
        print(f"RDS IP address: {ip}")
    except socket.gaierror:
        print("Unable to resolve RDS hostname")


def get_ssm_parameter(param_name):
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response['Parameter']['Value']

# Fetch the database URL from SSM Parameter Store
db_url_param_name = os.environ['SSM_DB_URL_PARAMETER']
os.environ['DIG_JOB_SERVER_DB'] = get_ssm_parameter(db_url_param_name)
print(f"DB URL: {os.environ['DIG_JOB_SERVER_DB']}")
test_dns_resolution()
# Set environment variable for Lambda
os.environ['RUNNING_IN_LAMBDA'] = 'True'

# Create the FastAPI app
app = create_app()

# Create the Lambda handler
handler = Mangum(app)
print("Lambda handler initialization complete")
