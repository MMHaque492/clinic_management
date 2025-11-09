import sqlite3
import getpass
from werkzeug.security import generate_password_hash
from database import get_db_connection

def create_user():
    """Securely creates a new staff user."""
    print("--- Create New Staff User ---")
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if not username:
        print("Username cannot be empty.")
        return

    if password != password_confirm:
        print("Passwords do not match.")
        return

    # Hash the password
    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                     (username, password_hash))
        conn.commit()
        conn.close()
        print(f"User '{username}' created successfully!")
    except sqlite3.IntegrityError:
        print(f"Error: Username '{username}' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_user()