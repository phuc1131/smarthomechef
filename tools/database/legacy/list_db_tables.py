import sqlite3
con=sqlite3.connect('db.sqlite3')
c=con.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print('\n'.join(r[0] for r in c.fetchall()))
con.close()
