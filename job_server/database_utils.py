import bcrypt
from sqlalchemy import text


def authenticate_user(db, username, password):
    with db as connection:
        query = text("SELECT password FROM users WHERE user_name = :username")
        db_password = connection.execute(query, {"username": username}).fetchone()
        if db_password and bcrypt.checkpw(password.encode('utf-8'), db_password[0].encode('utf-8')):
            return True
        return False
