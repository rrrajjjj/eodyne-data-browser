import pandas as pd
import mysql.connector
import json

# CONFIG
DB_CONFIG = {'user': 'globalprod', 'password': 'SLf67X94:@5/', 'host': 'rgsweb.eodyne.com', 'database': 'global_prod'}

def get_profile():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Get Schema
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s
    """, (DB_CONFIG['database'],))
    schema = cursor.fetchall()
    
    # 2. Get Sample Data (The Magic Step)
    # We group by table to minimize queries
    tables = set(x['TABLE_NAME'] for x in schema)
    table_samples = {}
    
    print("Sampling data (this provides the context)...")
    for table in tables:
        try:
            # Fetch 3 rows to guess content
            query = f"SELECT * FROM {table} LIMIT 3"
            cursor.execute(query)
            rows = cursor.fetchall()
            
            # Convert datetime/decimals to string for JSON serialization
            sanitized_rows = []
            for row in rows:
                sanitized_rows.append({k: str(v) for k, v in row.items()})
            table_samples[table] = sanitized_rows
        except Exception as e:
            print(f"Skipping {table}: {e}")
            table_samples[table] = []

    conn.close()
    
    # 3. Structure the data
    output = {
        "schema": schema, # List of {TABLE_NAME, COLUMN_NAME, ...}
        "samples": table_samples # Dict of {table: [{row1}, {row2}]}
    }
    
    with open('raw_profile.json', 'w') as f:
        json.dump(output, f, default=str)
    print("Profile saved to raw_profile.json")

if __name__ == "__main__":
    get_profile()