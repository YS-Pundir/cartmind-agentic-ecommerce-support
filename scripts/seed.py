import sqlite3
import json
import pandas as pd

from src.rag.vector_store import build_storages

# Assuming ORDERS is available from the dataset.py run or re-import it
# For simplicity, we'll re-run the generator to ensure ORDERS is in scope
from scripts.dataset import generate_order_dataset
from src.config import db_loc
ORDERS, _, _ = generate_order_dataset(num_records=50, seed=42)

# Connect to an in-memory SQLite database for this example
# For persistent storage, replace ':memory:' with a file path like 'orders.db'
conn = sqlite3.connect(db_loc)
c = conn.cursor()

# Create the orders table
c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        record_id TEXT PRIMARY KEY,
        category TEXT,
        status TEXT,
        order_value_inr INTEGER,
        days_since_created INTEGER,
        delayed_shipment BOOLEAN
    )
''')
conn.commit()

# Insert data into the table
for order in ORDERS:
    c.execute('''
        INSERT OR REPLACE INTO orders (record_id, category, status, order_value_inr, days_since_created, delayed_shipment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        order['record_id'],
        order['category'],
        order['status'],
        order['order_value_inr'],
        order['days_since_created'],
        order['delayed_shipment']
    ))
conn.commit()

print("Orders data successfully loaded into 'orders.db' SQLite database.")

# Verify by querying some data
df_db = pd.read_sql_query("SELECT * FROM orders LIMIT 5", conn)
print(df_db)

conn.close()
print("Database connection closed.")

# seeding the knowledge database
build_storages()

