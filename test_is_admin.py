#!/usr/bin/env python3
"""
Tests pour la fonction is_admin() 
Vérifie que la fonction gère correctement tous les cas limites
"""

import os
import sys
import tempfile
from contextlib import contextmanager

# Ajouter le répertoire courant au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration pour les tests (utiliser une DB de test)
os.environ['SUPABASE_DB_URL'] = os.environ.get('SUPABASE_DB_URL', 'postgresql://test:test@localhost:5432/test')

# Importer après avoir configuré l'environnement
from app import app, is_admin, get_db, adapt_query
from werkzeug.security import generate_password_hash

def setup_test_database():
    """Configure la base de données de test avec des utilisateurs"""
    print("📋 Configuration de la base de données de test...")
    
    conn = get_db()
    c = conn.cursor()
    
    # Nettoyer les utilisateurs de test existants
    try:
        c.execute(adapt_query("DELETE FROM users WHERE email IN (?, ?, ?)"),
                 ('test_admin@test.com', 'test_user@test.com', 'test_norole@test.com'))
        conn.commit()
    except Exception as e:
        print(f"   Note: Erreur nettoyage (normal en première exécution): {e}")
        conn.rollback()
    
    # Créer un utilisateur admin
    try:
        c.execute(adapt_query("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)"),
                 ('Admin Test', 'test_admin@test.com', generate_password_hash('password'), 'admin'))
        admin_id = c.lastrowid
        print(f"   ✓ Utilisateur admin créé (ID: {admin_id})")
    except Exception as e:
        # L'utilisateur existe peut-être déjà
        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), ('test_admin@test.com',))
        result = c.fetchone()
        admin_id = result[0] if result else None
        print(f"   ✓ Utilisateur admin existant (ID: {admin_id})")
    
    # Créer un utilisateur normal
    try:
        c.execute(adapt_query("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)"),
                 ('User Test', 'test_user@test.com', generate_password_hash('password'), 'user'))
        user_id = c.lastrowid
        print(f"   ✓ Utilisateur normal créé (ID: {user_id})")
    except Exception as e:
        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), ('test_user@test.com',))
        result = c.fetchone()
        user_id = result[0] if result else None
        print(f"   ✓ Utilisateur normal existant (ID: {user_id})")
    
    # Créer un utilisateur sans rôle (NULL)
    try:
        c.execute(adapt_query("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)"),
                 ('No Role Test', 'test_norole@test.com', generate_password_hash('password'), None))
        norole_id = c.lastrowid
        print(f"   ✓ Utilisateur sans rôle créé (ID: {norole_id})")
    except Exception as e:
        c.execute(adapt_query("SELECT id FROM users WHERE email=?"), ('test_norole@test.com',))
        result = c.fetchone()
        norole_id = result[0] if result else None
        print(f"   ✓ Utilisateur sans rôle existant (ID: {norole_id})")
    
    conn.commit()
    conn.close()
    
    return {
        'admin_id': admin_id,
        'user_id': user_id,
        'norole_id': norole_id
    }

def cleanup_test_database():
    """Nettoie la base de données après les tests"""
    print("\n🧹 Nettoyage de la base de données de test...")
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute(adapt_query("DELETE FROM users WHERE email IN (?, ?, ?)"),
                 ('test_admin@test.com', 'test_user@test.com', 'test_norole@test.com'))
        conn.commit()
        conn.close()
        print("   ✓ Nettoyage terminé")
    except Exception as e:
        print(f"   ⚠ Erreur lors du nettoyage: {e}")

def run_tests():
    """Exécute tous les tests de is_admin()"""
    print("\n" + "="*80)
    print("🧪 TESTS DE LA FONCTION is_admin()")
    print("="*80)
    
    # Configuration
    test_data = setup_test_database()
    
    # Compteurs de résultats
    passed = 0
    failed = 0
    
    with app.test_request_context():
        from flask import session
        
        # Test 1: Utilisateur admin
        print("\n📝 Test 1: Utilisateur avec rôle admin")
        try:
            session['user_id'] = test_data['admin_id']
            result = is_admin()
            if result is True:
                print("   ✅ PASS - is_admin() retourne True pour un admin")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de True")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 2: Utilisateur normal
        print("\n📝 Test 2: Utilisateur avec rôle 'user'")
        try:
            session['user_id'] = test_data['user_id']
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False pour un utilisateur normal")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 3: Utilisateur sans rôle (NULL)
        print("\n📝 Test 3: Utilisateur avec rôle NULL")
        try:
            session['user_id'] = test_data['norole_id']
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False pour un utilisateur sans rôle")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 4: Utilisateur inexistant
        print("\n📝 Test 4: Utilisateur inexistant (ID: 999999)")
        try:
            session['user_id'] = 999999
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False pour un utilisateur inexistant")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 5: Pas d'utilisateur en session
        print("\n📝 Test 5: Aucun utilisateur en session")
        try:
            session.clear()
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False sans utilisateur en session")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 6: user_id = None explicitement
        print("\n📝 Test 6: user_id = None")
        try:
            session['user_id'] = None
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False pour user_id = None")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
        
        # Test 7: user_id = 0
        print("\n📝 Test 7: user_id = 0")
        try:
            session['user_id'] = 0
            result = is_admin()
            if result is False:
                print("   ✅ PASS - is_admin() retourne False pour user_id = 0")
                passed += 1
            else:
                print(f"   ❌ FAIL - is_admin() retourne {result} au lieu de False")
                failed += 1
        except Exception as e:
            print(f"   ❌ FAIL - Exception levée: {e}")
            failed += 1
    
    # Nettoyage
    cleanup_test_database()
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    print(f"   ✅ Tests réussis: {passed}")
    print(f"   ❌ Tests échoués: {failed}")
    print(f"   📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
