#!/usr/bin/env python3
"""
Script de validation de la migration Supabase/PostgreSQL
Vérifie que toutes les fonctionnalités essentielles fonctionnent correctement
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_connection():
    """Test 1: Connexion à la base de données"""
    print("\n" + "="*80)
    print("TEST 1: Connexion à Supabase/PostgreSQL")
    print("="*80)
    
    try:
        from database import get_db, IS_POSTGRES, DB_CONFIG
        
        # Vérifier qu'on est bien en mode PostgreSQL
        assert IS_POSTGRES == True, "IS_POSTGRES devrait être True"
        print("✅ Mode PostgreSQL actif")
        
        # Vérifier la configuration
        print(f"✅ Configuration: {DB_CONFIG['host']}/{DB_CONFIG['database']}")
        
        # Tester la connexion
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connexion réussie: {version[0][:50]}...")
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tables_exist():
    """Test 2: Vérifier que toutes les tables existent"""
    print("\n" + "="*80)
    print("TEST 2: Vérification des tables")
    print("="*80)
    
    try:
        from database import get_db
        
        expected_tables = [
            'users', 'paintings', 'orders', 'order_items',
            'cart_items', 'carts', 'notifications', 'exhibitions',
            'custom_requests', 'settings', 'stripe_events', 'saas_sites'
        ]
        
        # get_db() returns connection with RealDictCursor, so we can use dict keys
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        rows = cursor.fetchall()
        # Access using dict keys (RealDictCursor)
        existing_tables = [row['table_name'] for row in rows]
        print(f"✅ Tables trouvées: {len(existing_tables)}")
        
        missing_tables = []
        for table in expected_tables:
            if table in existing_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ⚠️  {table} (manquante)")
                missing_tables.append(table)
        
        conn.close()
        
        if missing_tables:
            print(f"\n⚠️  Tables manquantes: {', '.join(missing_tables)}")
            print("💡 Exécutez init_database() ou le script de migration")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_crud_operations():
    """Test 3: Opérations CRUD basiques"""
    print("\n" + "="*80)
    print("TEST 3: Opérations CRUD (Create, Read, Update, Delete)")
    print("="*80)
    
    try:
        from database import get_db, adapt_query
        
        conn = get_db()
        cursor = conn.cursor()
        
        # CREATE - Insérer un paramètre de test
        print("🔄 Test INSERT...")
        test_key = "test_migration_key"
        test_value = "test_migration_value"
        
        cursor.execute(adapt_query("""
            INSERT INTO settings (key, value) 
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """), (test_key, test_value))
        conn.commit()
        print("✅ INSERT réussi")
        
        # READ - Lire le paramètre
        print("🔄 Test SELECT...")
        cursor.execute(adapt_query("SELECT value FROM settings WHERE key = %s"), (test_key,))
        result = cursor.fetchone()
        assert result is not None, "Aucun résultat trouvé"
        assert result['value'] == test_value, f"Valeur incorrecte: {result['value']}"
        print("✅ SELECT réussi")
        
        # UPDATE - Mettre à jour le paramètre
        print("🔄 Test UPDATE...")
        new_value = "updated_value"
        cursor.execute(adapt_query("UPDATE settings SET value = %s WHERE key = %s"), (new_value, test_key))
        conn.commit()
        
        cursor.execute(adapt_query("SELECT value FROM settings WHERE key = %s"), (test_key,))
        result = cursor.fetchone()
        assert result['value'] == new_value, "Valeur non mise à jour"
        print("✅ UPDATE réussi")
        
        # DELETE - Supprimer le paramètre
        print("🔄 Test DELETE...")
        cursor.execute(adapt_query("DELETE FROM settings WHERE key = %s"), (test_key,))
        conn.commit()
        
        cursor.execute(adapt_query("SELECT value FROM settings WHERE key = %s"), (test_key,))
        result = cursor.fetchone()
        assert result is None, "Enregistrement non supprimé"
        print("✅ DELETE réussi")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_imports():
    """Test 4: Vérifier que l'application peut s'importer"""
    print("\n" + "="*80)
    print("TEST 4: Import de l'application")
    print("="*80)
    
    try:
        # Tenter d'importer app.py
        print("🔄 Import de app.py...")
        import app
        print("✅ app.py importé avec succès")
        
        # Vérifier que les tables sont définies
        assert hasattr(app, 'TABLES'), "TABLES non défini dans app.py"
        print(f"✅ {len(app.TABLES)} tables définies dans TABLES")
        
        # Vérifier que Flask est initialisé
        assert hasattr(app, 'app'), "Application Flask non initialisée"
        print("✅ Application Flask initialisée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_schema():
    """Test 5: Vérifier le schéma de quelques tables critiques"""
    print("\n" + "="*80)
    print("TEST 5: Vérification du schéma des tables")
    print("="*80)
    
    try:
        from database import get_db
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Vérifier la table users
        print("🔄 Vérification table 'users'...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        user_columns = cursor.fetchall()
        expected_user_cols = ['id', 'name', 'email', 'password', 'create_date', 'role']
        found_cols = [col['column_name'] for col in user_columns]
        
        for col in expected_user_cols:
            if col in found_cols:
                print(f"   ✅ {col}")
            else:
                print(f"   ⚠️  {col} (manquant)")
        
        # Vérifier la table settings
        print("🔄 Vérification table 'settings'...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'settings'
            ORDER BY ordinal_position
        """)
        
        settings_columns = cursor.fetchall()
        expected_settings_cols = ['id', 'key', 'value']
        found_cols = [col['column_name'] for col in settings_columns]
        
        for col in expected_settings_cols:
            if col in found_cols:
                print(f"   ✅ {col}")
            else:
                print(f"   ⚠️  {col} (manquant)")
        
        conn.close()
        
        print("✅ Schéma vérifié")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécuter tous les tests"""
    print("\n" + "="*80)
    print("🧪 VALIDATION DE LA MIGRATION SUPABASE/POSTGRESQL")
    print("="*80)
    
    # Vérifier que SUPABASE_DB_URL est définie
    db_url = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
    if not db_url:
        print("\n❌ ERREUR: Variable SUPABASE_DB_URL ou DATABASE_URL non définie")
        print("💡 Définissez-la avec:")
        print("   export SUPABASE_DB_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'")
        sys.exit(1)
    
    print(f"✅ URL Supabase configurée")
    
    # Exécuter les tests
    tests = [
        ("Connexion", test_database_connection),
        ("Tables", test_tables_exist),
        ("CRUD", test_crud_operations),
        ("Import App", test_app_imports),
        ("Schéma", test_database_schema),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Erreur inattendue dans {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés! La migration est validée.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s). Corrigez les erreurs ci-dessus.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
