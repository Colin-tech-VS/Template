#!/usr/bin/env python3
"""
Script de vérification de la migration SQLite → Supabase
Valide que:
1. Toutes les tables Supabase existent
2. app.py n'utilise que Supabase (pas de SQLite)
3. La configuration est correcte
"""

import os
import sys
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

# Configuration Supabase
DATABASE_URL = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERREUR: SUPABASE_DB_URL ou DATABASE_URL non définie")
    sys.exit(1)

# Parser l'URL
try:
    result = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': result.hostname,
        'port': result.port or 5432,
        'database': result.path[1:] if result.path else '',
        'user': result.username,
        'password': result.password,
        'sslmode': 'require'
    }
except Exception as e:
    print(f"❌ ERREUR parsing DATABASE_URL: {e}")
    sys.exit(1)

# Tables attendues
REQUIRED_TABLES = [
    'users',
    'settings',
    'paintings',
    'exhibitions',
    'carts',
    'cart_items',
    'orders',
    'order_items',
    'notifications',
    'custom_requests'
]

def check_supabase_connection():
    """Vérifie la connexion Supabase"""
    print("\n🔍 VÉRIFICATION 1: Connexion Supabase")
    print("-" * 80)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Connexion Supabase établie")
        print(f"   PostgreSQL version: {version[:50]}...")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erreur connexion Supabase: {e}")
        return False

def check_required_tables():
    """Vérifie que toutes les tables requises existent"""
    print("\n🔍 VÉRIFICATION 2: Tables requises")
    print("-" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        missing = []
        for table in REQUIRED_TABLES:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table,))
            
            exists = cursor.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"   {status} {table}")
            
            if not exists:
                missing.append(table)
        
        conn.close()
        
        if missing:
            print(f"\n⚠️  {len(missing)} tables manquantes: {', '.join(missing)}")
            print("\n💡 Exécutez: python migrate_sqlite_to_supabase.py")
            return False
        else:
            print(f"\n✅ Toutes les tables requises existent!")
            return True
            
    except Exception as e:
        print(f"❌ Erreur vérification tables: {e}")
        return False

def check_table_contents():
    """Affiche le nombre de lignes par table"""
    print("\n🔍 VÉRIFICATION 3: Contenu des tables")
    print("-" * 80)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        total_rows = 0
        for table in REQUIRED_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                status = "✅" if count > 0 else "⚠️ "
                print(f"   {status} {table}: {count} lignes")
                total_rows += count
            except:
                print(f"   ⚠️  {table}: Impossible de compter")
        
        print(f"\n   Total: {total_rows} lignes dans Supabase")
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur vérification contenu: {e}")

def check_sqlite_files():
    """Vérifie si les fichiers SQLite existent toujours"""
    print("\n🔍 VÉRIFICATION 4: Fichiers SQLite (à supprimer)")
    print("-" * 80)
    
    sqlite_files = ['paintings.db', 'app.db', 'database.db']
    found = []
    
    for f in sqlite_files:
        if os.path.exists(f):
            found.append(f)
            print(f"   ⚠️  {f} (existe)")
        else:
            print(f"   ✅ {f} (supprimé)")
    
    if found:
        print(f"\n⚠️  {len(found)} fichiers SQLite doivent être supprimés:")
        for f in found:
            print(f"   rm {f}")
    else:
        print(f"\n✅ Aucun fichier SQLite trouvé!")
    
    return len(found) == 0

def check_app_py_sqlite_references():
    """Vérifie qu'app.py n'a pas de références SQLite"""
    print("\n🔍 VÉRIFICATION 5: Références SQLite dans app.py")
    print("-" * 80)
    
    dangerous_patterns = [
        'import sqlite3',
        'sqlite3.connect',
        "connect('",
        ".db'",
        'sqlite3.',
        'Connection('
    ]
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
        
        found_patterns = []
        for pattern in dangerous_patterns:
            if pattern in content:
                found_patterns.append(pattern)
        
        if found_patterns:
            print(f"❌ Références SQLite détectées: {', '.join(found_patterns)}")
            return False
        else:
            print(f"✅ Aucune référence SQLite dans app.py")
            return True
            
    except Exception as e:
        print(f"❌ Erreur lecture app.py: {e}")
        return False

def check_database_py():
    """Vérifie que database.py est configuré correctement"""
    print("\n🔍 VÉRIFICATION 6: Configuration database.py")
    print("-" * 80)
    
    try:
        with open('database.py', 'r') as f:
            content = f.read()
        
        checks = {
            'psycopg2': 'import psycopg2' in content,
            'RealDictCursor': 'RealDictCursor' in content,
            'IS_POSTGRES = True': 'IS_POSTGRES = True' in content,
            'ConnectionPool': 'ThreadedConnectionPool' in content
        }
        
        all_ok = True
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"   {status} {check}")
            if not result:
                all_ok = False
        
        return all_ok
        
    except Exception as e:
        print(f"❌ Erreur lecture database.py: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 80)
    print("🔍 AUDIT DE MIGRATION SQLITE → SUPABASE")
    print("=" * 80)
    
    results = {
        'Connexion Supabase': check_supabase_connection(),
        'Tables requises': check_required_tables(),
        'Fichiers SQLite': check_sqlite_files(),
        'Références SQLite': check_app_py_sqlite_references(),
        'Configuration database.py': check_database_py(),
    }
    
    check_table_contents()
    
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DE L'AUDIT")
    print("=" * 80)
    
    for check, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {check}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ MIGRATION COMPLÈTE!")
        print("\nLe projet Template est maintenant 100% Supabase:")
        print("   • Toutes les tables Supabase existent")
        print("   • Aucune référence SQLite dans le code")
        print("   • Configuration PostgreSQL/Supabase validée")
        print("\n🎉 Vous pouvez déployer en production!")
        sys.exit(0)
    else:
        print("⚠️  MIGRATION INCOMPLÈTE")
        print("\n💡 Actions requises:")
        if not results['Connexion Supabase']:
            print("   1. Configurez SUPABASE_DB_URL")
        if not results['Tables requises']:
            print("   2. Exécutez: python migrate_sqlite_to_supabase.py")
        if not results['Fichiers SQLite']:
            print("   3. Supprimez les fichiers .db")
        if not results['Références SQLite']:
            print("   4. Supprimez les références SQLite d'app.py")
        print()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
