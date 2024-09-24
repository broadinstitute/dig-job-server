from sqlalchemy import text
from job_server.auth_backend import AuthBackend
import bcrypt

class MySQLAuthBackend(AuthBackend):
    def __init__(self, db):
        self.db = db

    def authenticate_user(self, username: str, password: str) -> bool:
        with self.db as connection:
            query = text("SELECT password FROM users WHERE user_name = :username")
            db_password = connection.execute(query, {"username": username}).fetchone()
            return db_password and bcrypt.checkpw(password.encode('utf-8'), db_password[0].encode('utf-8'))
