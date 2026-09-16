import logging

import fastapi
import click
from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables by default
load_dotenv()

from job_server.api import router, top_router
from job_server.api import get_current_user
from job_server.user_service_auth import log_user_service_config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_app():
    app = fastapi.FastAPI(title='Dig Job Server', redoc_url=None)

    for route in router.routes:
        if route.name not in {
            'login', 'job_status', '_falcon_principal_probe',
            'falcon_dataset', 'falcon_upload_urls', 'falcon_finalize',
            # Public by design: the KP portal resolves a sifter GUID to its
            # phenotype and has no GWAS-CE session. Exempted here BY FUNCTION
            # NAME, so renaming the handler would silently re-authenticate it --
            # tests/test_variant_sifter.py asserts it answers without a token.
            'dataset_metadata',
        }:
            route.dependencies.append(Depends(get_current_user))

    app.include_router(router, prefix='/api', tags=['api'])
    app.include_router(top_router, tags=['top'])

    return app

@click.group()
@click.option('--env-file', '-e', type=str)
@click.pass_context
def cli(ctx, env_file):
    if env_file:
        load_dotenv(env_file)



# /api/metadata/{id} is read by the KP portal, whose hostname varies by
# environment, so the list is a wildcard. An origin list is not access control
# here -- anyone can curl this API regardless -- it only decides which pages may
# read a response. The one thing it would buy, stopping an attacker's page from
# riding a victim's ambient session, does not apply: this API has no ambient
# session. Auth is a Bearer token the frontend attaches explicitly, nothing here
# sets or reads a cookie, and no client sends credentialed requests.
CORS_ORIGINS = ["*"]


def add_cors(app):
    """Install the CORS policy. Split out of cli_serve so it can be tested."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        # MUST stay False while origins is a wildcard: Starlette reflects the
        # caller's origin verbatim when allow_all_origins meets a request
        # carrying a cookie, which would turn "*" into "any site you like" the
        # moment anything in this service starts using cookies.
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )


def configure_logging():
    """Give the root logger a formatted stderr handler, and enable INFO for
    this app's own loggers.

    Without this, the module logger in user_service_auth inherits the
    root's default WARNING level, so log_user_service_config()'s INFO line
    is silently dropped -- nothing before this in the serve path configures
    logging at all. basicConfig() is a no-op if the root logger already has
    handlers, so this is safe to call unconditionally. Root itself stays at
    WARNING (basicConfig's default) rather than INFO, so third-party INFO
    output (httpx logs a line per request, botocore) doesn't get switched on
    along with it -- only "job_server"'s own loggers are raised.
    """
    logging.basicConfig(format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("job_server").setLevel(logging.INFO)


@click.command(name='serve')
@click.option('--port', '-p', type=int, default=8000)
def cli_serve(port):
    import uvicorn
    app = create_app()
    add_cors(app)

    configure_logging()
    log_user_service_config()
    uvicorn.run(app, host="0.0.0.0", port=port)

cli.add_command(cli_serve)


if __name__ == "__main__":
    cli()
