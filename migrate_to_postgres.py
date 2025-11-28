"""
Script de migration de SQLite vers PostgreSQL pour Render
Ce script transfère toutes les données de la base SQLite locale vers PostgreSQL
"""

import sqlite3
import psycopg2
import psycopg2.extras
import os
from urllib.parse import urlparse

# Configuration
SQLITE_DB = 'paintings.db'
POSTGRES_URL = os.environ.get('DATABASE_URL')

if not POSTGRES_URL:
    print("❌ Erreur: La variable d'environnement DATABASE_URL n'est pas définie")
    print("💡 Définissez-la avec: export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
    exit(1)

# Parser l'URL PostgreSQL
result = urlparse(POSTGRES_URL)
pg_config = {
    'host': result.hostname,
    'port': result.port,
    'database': result.path[1:],
    'user': result.username,
    'password': result.password
}

print(f"📊 Migration de SQLite vers PostgreSQL")
print(f"   Source: {SQLITE_DB}")
print(f"   Destination: {pg_config['host']}/{pg_config['database']}")
print()

# Tables à migrer (dans l'ordre pour respecter les contraintes de clés étrangères)
TABLES = [
    'users',
    'settings',
    'paintings',
    'exhibitions',
    'notifications',
    'orders',
    'order_items',
    'custom_requests',
    'favorites'
]

def adapt_schema_for_postgres(create_sql):
    """Adapte le schéma SQLite pour PostgreSQL"""
    create_sql = create_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    create_sql = create_sql.replace('AUTOINCREMENT', '')
    create_sql = create_sql.replace('TEXT', 'TEXT')
    create_sql = create_sql.replace('REAL', 'NUMERIC')
    return create_sql

def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migre une table de SQLite vers PostgreSQL"""
    print(f"🔄 Migration de la table '{table_name}'...")
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Récupérer le schéma SQLite
    sqlite_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    create_sql = sqlite_cursor.fetchone()
    
    if not create_sql:
        print(f"⚠️  Table '{table_name}' introuvable dans SQLite, passage...")
        return
    
    # Créer la table dans PostgreSQL
    pg_create_sql = adapt_schema_for_postgres(create_sql[0])
    try:
        pg_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        pg_cursor.execute(pg_create_sql)
        pg_conn.commit()
        print(f"   ✅ Schéma créé")
    except Exception as e:
        print(f"   ⚠️  Erreur création schéma: {e}")
        pg_conn.rollback()
        return
    
    # Récupérer les données SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"   ℹ️  Aucune donnée à migrer")
        return
    
    # Récupérer les noms de colonnes
    columns = [description[0] for description in sqlite_cursor.description]
    
    # Insérer les données dans PostgreSQL
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
    
    try:
        # Filtrer la colonne id AUTOINCREMENT pour PostgreSQL
        if 'id' in columns and table_name != 'settings':
            # Ne pas insérer l'id, laisser SERIAL le générer
            columns_without_id = [col for col in columns if col != 'id']
            columns_str = ', '.join(columns_without_id)
            placeholders = ', '.join(['%s'] * len(columns_without_id))
            insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
            
            # Retirer l'id de chaque ligne
            id_index = columns.index('id')
            rows = [tuple(val for i, val in enumerate(row) if i != id_index) for row in rows]
        
        psycopg2.extras.execute_batch(pg_cursor, insert_sql, rows)
        pg_conn.commit()
        print(f"   ✅ {len(rows)} lignes migrées")
        
        # Réinitialiser la séquence SERIAL pour PostgreSQL
        if 'id' in columns:
            try:
                pg_cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), (SELECT MAX(id) FROM {table_name}))")
                pg_conn.commit()
            except:
                pass
        
    except Exception as e:
        print(f"   ❌ Erreur insertion données: {e}")
        pg_conn.rollback()

def main():
    # Connexion SQLite
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        print("✅ Connexion SQLite établie")
    except Exception as e:
        print(f"❌ Erreur connexion SQLite: {e}")
        return
    
    # Connexion PostgreSQL
    try:
        pg_conn = psycopg2.connect(**pg_config)
        print("✅ Connexion PostgreSQL établie")
        print()
    except Exception as e:
        print(f"❌ Erreur connexion PostgreSQL: {e}")
        print(f"💡 Vérifiez vos identifiants et que la base existe")
        return
    
    # Migrer chaque table
    for table in TABLES:
        migrate_table(sqlite_conn, pg_conn, table)
        print()
    
    # Fermer les connexions
    sqlite_conn.close()
    pg_conn.close()
    
    print("=" * 60)
    print("🎉 Migration terminée avec succès!")
    print("=" * 60)
    print()
    print("📝 Prochaines étapes:")
    print("   1. Vérifiez les données dans PostgreSQL")
    print("   2. Définissez DATABASE_URL sur Render")
    print("   3. Déployez l'application")

if __name__ == "__main__":
    main()
