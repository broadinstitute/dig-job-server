# dig-job-server

![Coverage](https://img.shields.io/badge/coverage-70%25-brightgreen)


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
DATASET=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''<data-set-name>'''))")
PRESIGNED_URL=$(curl "http://localhost:8000/api/get-pre-signed-url/$DATASET" \
     -H "Authorization: bearer <token_provided_by_login_response>" \
     | python3 -c "import sys, json; print(json.load(sys.stdin)['presigned_url'])")
curl -X PUT --upload-file <local-file-to-upload> $PRESIGNED_URL  
```

## Deployment
Both the front end and API deploy via github actions that fire upon a push to the main branch.  The front end deploys as a static site
served by our nginx server, and the API deploys to EC2 instance that runs the server as a python process.  The front end talks to the API via an nginx proxy.
