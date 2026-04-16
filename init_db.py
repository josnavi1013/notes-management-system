import sqlite3

conn=sqlite3.connect('notedb.db')

with open("schema.sql") as f:
    conn.executescript(f.read())

conn.commit()
conn.close()

print("Database initialized successfully")