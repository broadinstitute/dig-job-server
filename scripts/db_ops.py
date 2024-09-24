import typer
import bcrypt
from sqlalchemy import text

from job_server.database import get_db

app = typer.Typer()

@app.command()
def add_user(name: str, password: str):
    db = get_db()
    with db as connection:
        connection.execute(text("insert into users(user_name, password, created_at) values(:user, :pass, NOW())"),
                           {"user": name, "pass": bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())})
        connection.commit()


@app.command()
def remove_user(name: str):
    db = get_db()
    with db as connection:
        connection.execute(text("delete from users where user_name = :user"), {"user": name})
        connection.commit()

if __name__ == "__main__":
    app()
