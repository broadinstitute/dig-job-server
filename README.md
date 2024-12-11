# dig-job-server
![Coverage](https://img.shields.io/badge/coverage-67%25-brightgreen)

## Project Setup and Running Server Locally
1. Set up python virtual env using version 3.9 or later.  With [pyenv](https://github.com/pyenv/pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) installed you can do the following:
```bash 
pyenv install 3.9
pyenv local 3.9
pyenv virtualenv 3.9 dig-job-server
```
2. Install dependencies for the virtual env:
```bash
pip install -r requirements.txt 
```
3. Start mysql db via docker for local development (code defaults to port 3308):
```bash
 ./docker_db/docker_db.sh start <port>
```
4. Run db migrations:
```bash
alembic upgrade head
```

5. Run tests (this will create a user in your local db, while also verifying everything is set up):
```bash
pytest
```

6. Start the server (you can set up a IDE runtime config for this too):
```bash
python -m job_server.main
```

7. Start using the server:
```bash
curl -H "Content-Type: application/json" -X POST http://localhost:8000/api/login \
-d '{"username": "testuser", "password": "change.me"}'
```
```bash
curl -X POST http://localhost:8000/api/upload \
     -F "file=@/<path_to_local_file>" \
     -H "Content-Type: multipart/form-data" \
     -H "FileName: <file_name>" \
     -H "DatasetName: <dataset_name>" \
     -H "Authorization: bearer <token_provided_by_login_response>"
```

## Deployment
This project uses [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) to deploy this project as an AWS Lambda. 
Install it locally if you haven't already.
1. Run build_lambda.py 
```bash
 python scripts/build_lambda.py
```
2. Deploy the lambda using the AWS SAM CLI using one of the two samconfig-<env>.toml files in the deployment directory.
```bash
cd deployment; sam deploy --config-file samconfig-<env>.toml 
```
