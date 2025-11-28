import sqlite3

DB_PATH = "paintings.db"

def migrate_orders_remove_address():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Vérifier si la colonne "address" existe
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    if "address" in columns:
        print("Migration : suppression de la colonne 'address' dans orders...")
        
        # 1) Renommer l’ancienne table
        c.execute("ALTER TABLE orders RENAME TO orders_old")
        
        # 2) Recréer la table sans 'address'
        c.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                total_price REAL NOT NULL,
                order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                status TEXT NOT NULL DEFAULT 'En cours'
            )
        """)
        
        # 3) Copier les anciennes données (sans 'address')
        c.execute("""
            INSERT INTO orders (id, customer_name, email, total_price, order_date, user_id, status)
            SELECT id, customer_name, email, total_price, order_date, user_id, status
            FROM orders_old
        """)
        
        # 4) Supprimer l’ancienne table
        c.execute("DROP TABLE orders_old")
        conn.commit()
        print("Migration terminée.")
    else:
        print("Migration non nécessaire : colonne 'address' absente.")
    
    conn.close()

# Appeler la migration une seule fois
migrate_orders_remove_address()
