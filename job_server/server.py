import fastapi
import click
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware


from job_server.api import router
from job_server.api import get_current_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_app():
    app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

    for route in router.routes:
        if route.name not in {'login'}:
            route.dependencies.append(Depends(get_current_user))

    app.include_router(router, prefix='/api', tags=['api'])

    return app

@click.group()
@click.option('--env-file', '-e', type=str)
@click.pass_context
def cli(ctx, env_file):
    if env_file:
        load_dotenv(env_file)



@click.command(name='serve')
@click.option('--port', '-p', type=int, default=8000)
def cli_serve(port):
    import uvicorn
    app = create_app()
    origins = [
        "http://localhost:3000",
        "http://local.kpndataregistry.org:3000",
        "https://ldserver.kpndataregistry.org"
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    uvicorn.run(app, host="0.0.0.0", port=port)

cli.add_command(cli_serve)


if __name__ == "__main__":
    cli()
