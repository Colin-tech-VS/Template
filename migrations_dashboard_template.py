#!/usr/bin/env python3
"""
Migration Dashboard: Ajouter site_id aux tables pour Template sync
À adapter et exécuter en prod
"""

import psycopg2
from psycopg2 import sql
import os
from datetime import datetime

DB_CONFIG = {
    'host': os.getenv('DATABASE_URL').split('@')[1].split(':')[0],
    'user': os.getenv('DATABASE_URL').split('://')[1].split(':')[0],
    'password': os.getenv('DATABASE_URL').split(':')[1].split('@')[0],
    'database': os.getenv('DATABASE_URL').split('/')[-1],
    'port': 5432
}

def connect():
    """Connexion à la BD"""
    return psycopg2.connect(**DB_CONFIG)

def column_exists(conn, table, column):
    """Vérifie si une colonne existe"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name=%s AND column_name=%s
        )
    """, (table, column))
    exists = cursor.fetchone()[0]
    cursor.close()
    return exists

def run_migration(conn, migration_name, sql_query):
    """Exécute une migration"""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        conn.commit()
        cursor.close()
        print(f"✅ {migration_name}")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ {migration_name}: {e}")
        return False

def migrate():
    """Exécute toutes les migrations"""
    conn = connect()
    print(f"\n🔄 Migration Dashboard - {datetime.now().isoformat()}\n")
    
    # 1. Ajouter site_id et template_id à paintings
    if not column_exists(conn, 'paintings', 'site_id'):
        run_migration(conn, "paintings: ADD site_id", """
            ALTER TABLE paintings ADD COLUMN site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE;
            ALTER TABLE paintings ADD COLUMN template_id INTEGER;
            CREATE INDEX idx_paintings_site ON paintings(site_id);
            CREATE UNIQUE INDEX idx_paintings_template ON paintings(site_id, template_id) 
                WHERE site_id IS NOT NULL AND template_id IS NOT NULL;
        """)
    else:
        print("⏭️  paintings.site_id déjà existe")
    
    # 2. Ajouter site_id et template_id à users
    if not column_exists(conn, 'users', 'site_id'):
        run_migration(conn, "users: ADD site_id", """
            ALTER TABLE users ADD COLUMN site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE;
            ALTER TABLE users ADD COLUMN template_id INTEGER;
            CREATE INDEX idx_users_site ON users(site_id);
            CREATE UNIQUE INDEX idx_users_template ON users(site_id, template_id) 
                WHERE site_id IS NOT NULL AND template_id IS NOT NULL;
        """)
    else:
        print("⏭️  users.site_id déjà existe")
    
    # 3. Ajouter site_id à orders
    if not column_exists(conn, 'orders', 'site_id'):
        run_migration(conn, "orders: ADD site_id", """
            ALTER TABLE orders ADD COLUMN site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE;
            CREATE INDEX idx_orders_site ON orders(site_id);
        """)
    else:
        print("⏭️  orders.site_id déjà existe")
    
    # 4. Créer table template_sync_log
    run_migration(conn, "CREATE template_sync_log", """
        CREATE TABLE IF NOT EXISTS template_sync_log (
            id SERIAL PRIMARY KEY,
            site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
            sync_type VARCHAR(50),
            status VARCHAR(20),
            records_processed INTEGER,
            errors INTEGER,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        );
    """)
    
    conn.close()
    print(f"\n✨ Migration terminée!\n")

if __name__ == '__main__':
    migrate()
