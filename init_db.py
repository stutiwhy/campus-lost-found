
import sqlite3
from app import DATABASE, init_db

DATABASE.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(DATABASE, timeout=30) as db:
    db.execute("PRAGMA journal_mode = WAL")

init_db()

print("Database initialized successfully.")
