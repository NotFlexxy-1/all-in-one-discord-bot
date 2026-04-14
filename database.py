import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS economy (
    user_id INTEGER PRIMARY KEY,
    cash INTEGER DEFAULT 0
)
""")

conn.commit()
