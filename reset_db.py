import os
import psycopg2

def reset_database():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL n'est pas défini.")
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()

    # Supprimer toutes les tables si elles existent
    tables = ["order_items", "orders", "cart_items", "carts", "users", "paintings", "settings", "favorites"]
    for table in tables:
        c.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Recréation des tables
    c.execute('''
        CREATE TABLE paintings (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            image TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE settings (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE favorites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            total_price REAL NOT NULL,
            order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'En cours',
            user_id INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE order_items (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')

    c.execute('''
        CREATE TABLE carts (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            user_id INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE cart_items (
            id SERIAL PRIMARY KEY,
            cart_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(cart_id) REFERENCES carts(id)
        )
    ''')

    # Sauvegarder le compte admin s'il existe (par défaut email admin@admin.com)
    # (après création de la table users)
    try:
        c.execute("SELECT name, email, password, create_date FROM users WHERE email = %s", ("admin@admin.com",))
        admin_user = c.fetchone()
        if admin_user:
            c.execute("INSERT INTO users (name, email, password, create_date) VALUES (%s, %s, %s, %s)", admin_user)
    except Exception as e:
        print(f"Aucun admin à réinsérer ou erreur : {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_database()
