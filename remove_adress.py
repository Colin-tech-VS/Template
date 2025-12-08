def migrate_orders_remove_address():
    import os
    import psycopg2
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini.")
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    # Vérifier si la colonne "address" existe
    c.execute("""
        SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='address'
    """)
    if c.fetchone():
        print("Migration : suppression de la colonne 'address' dans orders...")
        # 1) Renommer l’ancienne table
        c.execute("ALTER TABLE orders RENAME TO orders_old")
        # 2) Recréer la table sans 'address'
        c.execute("""
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                total_price REAL NOT NULL,
                order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                status TEXT NOT NULL DEFAULT 'En cours'
            )
        """)
        # 3) Copier les données
        c.execute("""
            INSERT INTO orders (id, customer_name, email, total_price, order_date, user_id, status)
            SELECT id, customer_name, email, total_price, order_date, user_id, status FROM orders_old
        """)
        # 4) Supprimer l’ancienne table
        c.execute("DROP TABLE orders_old")
        conn.commit()
    conn.close()
        
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
