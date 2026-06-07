'''import sqlite3

conn = sqlite3.connect("database/tx_tracker.db")

cursor = conn.cursor()

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name;
""")

tables = cursor.fetchall()

print("\nTables Found:\n")

for table in tables:
    print(table[0])

conn.close()'''

import sqlite3

conn = sqlite3.connect(
    "database/tx_tracker.db"
)

cursor = conn.cursor()

cursor.execute("""
SELECT
tx_hash,
current_status,
current_block_number
FROM transactions
""")

for row in cursor.fetchall():
    print(row)