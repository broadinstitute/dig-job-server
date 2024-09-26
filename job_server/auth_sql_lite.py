import sqlite3
from job_server.auth_backend import AuthBackend
from werkzeug.security import check_password_hash

class SQLiteAuthBackend(AuthBackend):
    def __init__(self, db_path):
        self.db_path = db_path

    def authenticate_user(self, username, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result:
            stored_password_hash = result[0]
            return check_password_hash(stored_password_hash, password)
        return False
