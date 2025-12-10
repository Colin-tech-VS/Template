#!/usr/bin/env python3
"""
Script de migration des données SQLite vers Supabase/PostgreSQL
Ce script transfère toutes les données des bases SQLite locales vers Supabase
"""

import sqlite3
import psycopg2
import psycopg2.extras
import os
import sys
from urllib.parse import urlparse

# Configuration
SQLITE_DBS = ['paintings.db', 'app.db']  # Bases SQLite à migrer
SUPABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not SUPABASE_URL:
    print("❌ Erreur: Variable SUPABASE_DB_URL ou DATABASE_URL non définie")
    print("💡 Définissez-la avec: export SUPABASE_DB_URL='postgresql://postgres:password@host:5432/postgres'")
    sys.exit(1)

# Parser l'URL Supabase
try:
    result = urlparse(SUPABASE_URL)
    pg_config = {
        'host': result.hostname,
        'port': result.port or 5432,
        'database': result.path[1:] if result.path else 'postgres',
        'user': result.username,
        'password': result.password,
        'sslmode': 'require'
    }
    print(f"✅ Configuration Supabase: {pg_config['host']}/{pg_config['database']}")
except Exception as e:
    print(f"❌ Erreur parsing URL Supabase: {e}")
    sys.exit(1)

# Tables à migrer (ordre important pour respecter les contraintes)
TABLES_ORDER = [
    'users',
    'settings',
    'paintings',
    'exhibitions',
    'carts',
    'cart_items',
    'notifications',
    'orders',
    'order_items',
    'custom_requests',
    'stripe_events',
    'saas_sites'
]


def adapt_schema_for_postgres(create_sql):
    """Adapte le schéma SQLite pour PostgreSQL/Supabase"""
    if not create_sql:
        return create_sql
    
    create_sql = create_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    create_sql = create_sql.replace('AUTOINCREMENT', '')
    create_sql = create_sql.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
    create_sql = create_sql.replace('REAL', 'NUMERIC')
    
    return create_sql


def get_all_tables(sqlite_conn):
    """Récupère toutes les tables SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]


def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migre une table de SQLite vers Supabase"""
    print(f"\n🔄 Migration de la table '{table_name}'...")
    
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    # Récupérer le schéma SQLite
    sqlite_cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    schema_row = sqlite_cursor.fetchone()
    
    if not schema_row:
        print(f"⚠️  Table '{table_name}' introuvable dans SQLite, passage...")
        return
    
    # Créer la table dans Supabase (si elle n'existe pas)
    pg_create_sql = adapt_schema_for_postgres(schema_row[0])
    try:
        # Vérifier si la table existe déjà
        pg_cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table_name,))
        
        table_exists = pg_cursor.fetchone()[0]
        
        if not table_exists:
            pg_cursor.execute(pg_create_sql)
            pg_conn.commit()
            print(f"   ✅ Schéma créé dans Supabase")
        else:
            print(f"   ℹ️  Table existe déjà dans Supabase")
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
    
    # Compter les données existantes dans Supabase
    pg_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    existing_count = pg_cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"   ⚠️  {existing_count} lignes déjà présentes dans Supabase")
        response = input(f"   ❓ Voulez-vous supprimer les données existantes? (y/N): ")
        if response.lower() == 'y':
            pg_cursor.execute(f"DELETE FROM {table_name}")
            pg_conn.commit()
            print(f"   ✅ Données existantes supprimées")
        else:
            print(f"   ⏭️  Conservation des données existantes, fusion...")
    
    # Insérer les données dans Supabase
    placeholders = ', '.join(['%s'] * len(columns))
    columns_str = ', '.join(columns)
    
    # Pour les tables avec ID auto-incrémenté, on garde l'ID source
    insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    
    try:
        migrated_count = 0
        for row in rows:
            try:
                pg_cursor.execute(insert_sql, row)
                migrated_count += 1
            except Exception as e:
                print(f"   ⚠️  Erreur insertion ligne: {e}")
                continue
        
        pg_conn.commit()
        print(f"   ✅ {migrated_count}/{len(rows)} lignes migrées vers Supabase")
        
        # Réinitialiser la séquence SERIAL pour PostgreSQL
        if 'id' in columns:
            try:
                pg_cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table_name}', 'id'), 
                        COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                        true
                    )
                """)
                pg_conn.commit()
                print(f"   ✅ Séquence ID réinitialisée")
            except Exception as e:
                print(f"   ⚠️  Erreur réinitialisation séquence: {e}")
        
    except Exception as e:
        print(f"   ❌ Erreur insertion données: {e}")
        pg_conn.rollback()


def main():
    """Fonction principale de migration"""
    print("="*80)
    print("🚀 MIGRATION SQLITE → SUPABASE/POSTGRESQL")
    print("="*80)
    print()
    
    # Connexion Supabase
    try:
        pg_conn = psycopg2.connect(**pg_config)
        print("✅ Connexion Supabase établie")
    except Exception as e:
        print(f"❌ Erreur connexion Supabase: {e}")
        print(f"💡 Vérifiez vos identifiants et que la base existe")
        sys.exit(1)
    
    # Parcourir toutes les bases SQLite
    all_tables_found = set()
    
    for sqlite_db in SQLITE_DBS:
        if not os.path.exists(sqlite_db):
            print(f"⚠️  Base SQLite '{sqlite_db}' introuvable, passage...")
            continue
        
        print(f"\n📂 Traitement de {sqlite_db}...")
        
        try:
            sqlite_conn = sqlite3.connect(sqlite_db)
            print(f"✅ Connexion SQLite établie")
            
            # Récupérer toutes les tables
            tables = get_all_tables(sqlite_conn)
            all_tables_found.update(tables)
            print(f"📊 {len(tables)} tables trouvées: {', '.join(tables)}")
            
            sqlite_conn.close()
            
        except Exception as e:
            print(f"❌ Erreur lecture {sqlite_db}: {e}")
            continue
    
    # Migrer les tables dans l'ordre défini
    print(f"\n{'='*80}")
    print(f"🔄 DÉBUT DE LA MIGRATION DES DONNÉES")
    print(f"{'='*80}")
    
    for table in TABLES_ORDER:
        if table in all_tables_found:
            # Reconnecter à chaque fois pour éviter les timeouts
            for sqlite_db in SQLITE_DBS:
                if not os.path.exists(sqlite_db):
                    continue
                
                try:
                    sqlite_conn = sqlite3.connect(sqlite_db)
                    
                    # Vérifier si la table existe dans cette DB
                    cursor = sqlite_conn.cursor()
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        migrate_table(sqlite_conn, pg_conn, table)
                    
                    sqlite_conn.close()
                except Exception as e:
                    print(f"⚠️  Erreur traitement {table} dans {sqlite_db}: {e}")
    
    # Migrer les tables non listées (tables additionnelles)
    remaining_tables = all_tables_found - set(TABLES_ORDER)
    if remaining_tables:
        print(f"\n⚠️  Tables supplémentaires détectées: {', '.join(remaining_tables)}")
        for table in remaining_tables:
            for sqlite_db in SQLITE_DBS:
                if not os.path.exists(sqlite_db):
                    continue
                try:
                    sqlite_conn = sqlite3.connect(sqlite_db)
                    cursor = sqlite_conn.cursor()
                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if cursor.fetchone():
                        migrate_table(sqlite_conn, pg_conn, table)
                    sqlite_conn.close()
                except Exception as e:
                    print(f"⚠️  Erreur traitement {table}: {e}")
    
    # Fermer la connexion Supabase
    pg_conn.close()
    
    print()
    print("="*80)
    print("🎉 MIGRATION TERMINÉE!")
    print("="*80)
    print()
    print("📝 Prochaines étapes:")
    print("   1. Vérifiez les données dans Supabase (app.supabase.com)")
    print("   2. Testez l'application avec Supabase")
    print("   3. Si tout fonctionne, supprimez les fichiers .db")
    print("   4. Déployez sur votre plateforme de production")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
