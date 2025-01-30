from fabric import task


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
    migrate(c)
    restart(c)


@task
def update_source(c, commit=None):
    """
    Update the environment's source code to either the latest in main or a specified commit.
    """
    directory = get_checkout_directory()
    with c.cd(directory):
        if commit:
            c.run("git fetch --all --tags")
            is_tag = c.run(f"git tag -l {commit}", warn=True).ok

            if is_tag:
                c.run(f"git checkout {commit}")
            else:
                c.run(f"git checkout {commit} && git pull")
        else:
            c.run("git checkout main && git pull")


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
        c.run("python3 -m pip install -r requirements.txt")
        c.run(
            f"screen -dmS {screen_session} bash -c 'python3 -m job_server.server serve --port {port}'")


def get_checkout_directory():
    return "/home/ec2-user/lsserver-api"


@task
def migrate(c):
    """
    Run db migrations.
    """
    directory = get_checkout_directory()
    with c.cd(directory):
        c.run("python3 -m pip install -r requirements.txt")
        c.run("python3 -m alembic upgrade head")
