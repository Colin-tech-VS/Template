import sqlite3

db_path = 'paintings.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(settings)")
    columns = cursor.fetchall()
    print("Settings table schema:")
    for col in columns:
        print(f"  {col}")
    print()
    
    cursor.execute("SELECT * FROM settings WHERE key LIKE 'stripe%' OR key = 'export_api_key'")
    rows = cursor.fetchall()
    
    print("Stripe-related settings stored:")
    print("-" * 70)
    for row in rows:
        print(f"  Row: {row}")
        if len(row) >= 2:
            key = row[1] if len(row) > 1 else row[0]
            value = row[2] if len(row) > 2 else row[1]
            if 'sk_' in str(value) or 'secret' in key.lower():
                masked_value = value[:6] + '...' + value[-4:] if len(value) > 10 else '***'
            else:
                masked_value = value
            print(f"    Key: {key}")
            print(f"    Value: {masked_value}")
    print()
    
    if not rows:
        print("  No stripe settings found in database")
    
    conn.close()
    
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
