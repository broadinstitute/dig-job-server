import fastapi
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from job_server import api
from job_server.api import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_app():
    app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

    for route in api.router.routes:
        if route.name in {'upload'}:
            route.dependencies.append(Depends(get_current_user))

    app.include_router(api.router, prefix='/api', tags=['api'])

    return app

# This block will only run when executing server.py directly (local development)
if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)
