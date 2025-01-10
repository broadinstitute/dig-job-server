import fastapi
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware


from job_server import api
from job_server.api import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_app():
    app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

    for route in api.router.routes:
        if route.name not in {'login', 'get_pre_signed_url'}:
            route.dependencies.append(Depends(get_current_user))

    app.include_router(api.router, prefix='/api', tags=['api'])

    return app

# This block will only run when executing server.py directly (local development)
if __name__ == "__main__":
    import uvicorn
    app = create_app()
    origins = [
        "http://localhost:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    uvicorn.run(app, host="0.0.0.0", port=8000)
