import sqlite3
import argparse
from werkzeug.security import generate_password_hash

def create_users_table(conn):
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    conn.commit()

def add_user(conn, username, password):
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    cursor.execute("INSERT OR REPLACE INTO users (username, password_hash) VALUES (?, ?)",
                   (username, password_hash))
    conn.commit()

def main():
    parser = argparse.ArgumentParser(description="Populate SQLite database with user credentials")
    parser.add_argument("--db_path", default="users.db", help="Path to the SQLite database file")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    create_users_table(conn)

    while True:
        username = input("Enter username (or 'q' to quit): ")
        if username.lower() == 'q':
            break
        password = input("Enter password: ")
        add_user(conn, username, password)
        print(f"User {username} added successfully.")

    conn.close()
    print("Database population complete.")

if __name__ == "__main__":
    main()
