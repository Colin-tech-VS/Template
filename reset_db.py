import sqlite3

DB_PATH = 'paintings.db'

def reset_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Sauvegarder le compte admin s'il existe (par défaut email admin@admin.com)
    c.execute("SELECT name, email, password, create_date FROM users WHERE email = ?", ("admin@admin.com",))
    admin_user = c.fetchone()

    # Supprimer toutes les tables si elles existent
    tables = ["order_items", "orders", "cart_items", "carts", "users", "paintings"]
    for table in tables:
        c.execute(f"DROP TABLE IF EXISTS {table}")

    # Recréation des tables

    # Peintures
    c.execute('''
        CREATE TABLE paintings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 0,
            create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Utilisateurs
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            create_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Réinsérer le compte admin si sauvegardé
    if admin_user:
        c.execute("INSERT INTO users (name, email, password, create_date) VALUES (?, ?, ?, ?)", admin_user)

    # Commandes
    c.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            total_price REAL NOT NULL,
            order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'En cours',
            user_id INTEGER
        )
    ''')

    # Articles de commande
    c.execute('''
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    ''')

    # Panier persistant
    c.execute('''
        CREATE TABLE carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            user_id INTEGER
        )
    ''')

    c.execute('''
        CREATE TABLE cart_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id INTEGER NOT NULL,
            painting_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(cart_id) REFERENCES carts(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("Base de données réinitialisée avec succès ! (compte admin conservé si existant)")

if __name__ == "__main__":
    confirm = input("ATTENTION : Toutes les données seront supprimées ! Tapez 'OUI' pour continuer : ")
    if confirm == "OUI":
        reset_database()
    else:
        print("Annulé.")
