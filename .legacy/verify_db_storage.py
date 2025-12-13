import sqlite3

db_path = 'paintings.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    print()
    
    cursor.execute("SELECT * FROM settings WHERE key LIKE 'stripe%' OR key = 'export_api_key'")
    rows = cursor.fetchall()
    
    print("Stripe-related settings in database:")
    print("-" * 70)
    for row in rows:
        key, value = row
        if 'sk_' in str(value) or 'secret' in key.lower():
            masked_value = value[:6] + '...' + value[-4:] if len(value) > 10 else '***'
        else:
            masked_value = value
        print(f"  {key}: {masked_value}")
    print()
    
    if not rows:
        print("  No stripe settings found in database")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
