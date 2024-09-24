# dig-job-server
![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen)

# Project Setup and Running Server
1. Set up python virtual env using version 3.9 or later.  With [pyenv](https://github.com/pyenv/pyenv) installed you can do the following:
```bash 
pyenv install 3.10
pyenv local 3.10
pyenv virtualenv 3.10 dig-job-server
```
2. Install dependencies for the virtual env:
```bash
pip install -r requirements.txt 
```
3. Start mysql db via docker for local development:
```bash
 ./docker_db/docker_db.sh start <port>
```
4. Run db migrations:
```bash
alembic upgrade head
```
5. Start the server (you can set up a IDE runtime config for this too):
```bash
python -m uvicorn server:app --reload 
```
# Authentication
Once you start the server you can call the login method with a valid user and password in order to get an Oauth bearer token.
