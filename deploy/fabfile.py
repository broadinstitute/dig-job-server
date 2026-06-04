from fabric import task

# The Python the service runs under. Must be installed on the host
# (e.g. `sudo dnf install -y python3.12` on Amazon Linux 2023). The venv
# is (re)built against this by ensure_venv below.
PYTHON_BIN = "python3.12"
VENV_VERSION = "3.12"


@task
def deploy(c, commit=None):
    """
    Deploy the application to the specified environment.

    Parameters:
        c: The connection context.
        commit: The commit to deploy. If not specified, the latest commit on main.
    """
    c.forward_agent = True
    update_source(c, commit)
    ensure_venv(c)
    migrate(c)
    restart(c)


@task
def ensure_venv(c):
    """
    Ensure ./venv exists and runs the target Python, rebuilding it otherwise.

    Idempotent: the first deploy after bumping PYTHON_BIN rebuilds the venv
    on the new interpreter; later deploys see the right version and no-op.
    """
    directory = get_checkout_directory()
    with c.cd(directory):
        # Fail fast (without touching the working venv) if the target
        # interpreter isn't installed on the host.
        c.run(
            f"command -v {PYTHON_BIN} >/dev/null 2>&1 || "
            f'{{ echo "{PYTHON_BIN} not found; run: sudo dnf install -y {PYTHON_BIN}"; exit 1; }}'
        )
        # Rebuild only when the venv is missing or on the wrong Python.
        # Build into venv.new and swap, so a failed build never destroys a
        # working venv.
        c.run(
            "if [ ! -x venv/bin/python ] || "
            f'! venv/bin/python --version 2>&1 | grep -q "Python {VENV_VERSION}"; then '
            f"rm -rf venv.new && {PYTHON_BIN} -m venv venv.new && rm -rf venv && mv venv.new venv; fi"
        )
        c.run("./venv/bin/python -m pip install --upgrade pip")


@task
def update_source(c, commit=None):
    """
    Update the environment's source code to either the latest in main or a specified commit.
    """
    directory = get_checkout_directory()
    with c.cd(directory):
        c.run("git pull")


@task
def restart(c):
    """
    Restart the server by terminating existing screen sessions and starting a new session.

    Parameters:
        c: The connection context.
    """
    directory = get_checkout_directory()
    screen_session = "ldserver-api"
    port = 5000

    with c.cd(directory):
        # terminate running screen sessions
        c.run(
            f"screen -ls | grep -o '[0-9]*\.{screen_session}' | while read -r line; do screen -S \"${{line}}\" -X quit; done")
        c.run("./venv/bin/python -m pip install -r requirements.txt")
        c.run(
            f"screen -dmS {screen_session} bash -c './venv/bin/python -m job_server.server -e .env serve --port {port}'")


def get_checkout_directory():
    return "/home/ec2-user/ldserver-api"


@task
def migrate(c):
    """
    Run db migrations.
    """
    directory = get_checkout_directory()
    with c.cd(directory):
        c.run("./venv/bin/pip install -r requirements.txt")
        c.run("./venv/bin/python -m alembic upgrade head")
