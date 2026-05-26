#!/usr/bin/env python
"""List all tables in database."""
import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("Tables in database:")
for row in cur.fetchall():
    print(f"  {row[0]}")
conn.close()
