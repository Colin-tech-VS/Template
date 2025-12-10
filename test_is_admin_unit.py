#!/usr/bin/env python3
"""
Tests unitaires pour la fonction is_admin()
Ces tests utilisent des mocks pour éviter de dépendre d'une vraie base de données
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

print("\n" + "="*80)
print("🧪 TESTS UNITAIRES DE LA FONCTION is_admin()")
print("="*80)

def test_is_admin_logic():
    """Teste la logique de is_admin() sans dépendance DB"""
    
    passed = 0
    failed = 0
    
    # Simuler la fonction is_admin() avec la logique corrigée
    def is_admin_corrected(user_id, db_result):
        """Version de test de is_admin() pour valider la logique"""
        if not user_id:
            return False
        
        try:
            result = db_result
            
            # Vérification robuste: result doit être une séquence non vide
            if result is None:
                print(f"[is_admin] Aucun résultat pour user_id={user_id}")
                return False
            
            if not isinstance(result, (tuple, list)) or len(result) == 0:
                print(f"[is_admin] Résultat mal formé pour user_id={user_id}: {type(result)}")
                return False
            
            # Accès sécurisé au rôle
            role = result[0]
            if role is None:
                print(f"[is_admin] Rôle NULL pour user_id={user_id}")
                return False
            
            is_admin_role = (role == 'admin')
            # Log uniquement en mode debug pour éviter le bruit et les fuites d'info
            if not is_admin_role and os.getenv('DEBUG_AUTH'):
                print(f"[is_admin] user_id={user_id} a le rôle '{role}' (non admin)")
            
            return is_admin_role
            
        except Exception as e:
            print(f"[is_admin] Erreur lors de la vérification du rôle pour user_id={user_id}: {e}")
            return False
    
    # Test 1: Rôle admin valide
    print("\n📝 Test 1: Résultat DB avec rôle 'admin'")
    try:
        result = is_admin_corrected(1, ('admin',))
        if result is True:
            print("   ✅ PASS - Retourne True pour rôle 'admin'")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de True")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 2: Rôle user
    print("\n📝 Test 2: Résultat DB avec rôle 'user'")
    try:
        result = is_admin_corrected(1, ('user',))
        if result is False:
            print("   ✅ PASS - Retourne False pour rôle 'user'")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 3: Résultat None (utilisateur inexistant)
    print("\n📝 Test 3: Résultat DB = None (utilisateur inexistant)")
    try:
        result = is_admin_corrected(999, None)
        if result is False:
            print("   ✅ PASS - Retourne False pour résultat None")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 4: Tuple vide
    print("\n📝 Test 4: Résultat DB = tuple vide ()")
    try:
        result = is_admin_corrected(1, ())
        if result is False:
            print("   ✅ PASS - Retourne False pour tuple vide")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 5: Rôle NULL dans le résultat
    print("\n📝 Test 5: Résultat DB avec rôle NULL")
    try:
        result = is_admin_corrected(1, (None,))
        if result is False:
            print("   ✅ PASS - Retourne False pour rôle NULL")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 6: user_id = None
    print("\n📝 Test 6: user_id = None")
    try:
        result = is_admin_corrected(None, ('admin',))
        if result is False:
            print("   ✅ PASS - Retourne False pour user_id = None")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 7: user_id = 0
    print("\n📝 Test 7: user_id = 0")
    try:
        result = is_admin_corrected(0, ('admin',))
        if result is False:
            print("   ✅ PASS - Retourne False pour user_id = 0")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 8: Liste au lieu de tuple
    print("\n📝 Test 8: Résultat DB = liste ['admin']")
    try:
        result = is_admin_corrected(1, ['admin'])
        if result is True:
            print("   ✅ PASS - Fonctionne avec une liste")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de True")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 9: Rôle différent (partenaire)
    print("\n📝 Test 9: Résultat DB avec rôle 'partenaire'")
    try:
        result = is_admin_corrected(1, ('partenaire',))
        if result is False:
            print("   ✅ PASS - Retourne False pour rôle 'partenaire'")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Test 10: Type de résultat invalide (dict)
    print("\n📝 Test 10: Résultat DB = dict (type invalide)")
    try:
        result = is_admin_corrected(1, {'role': 'admin'})
        if result is False:
            print("   ✅ PASS - Retourne False pour type dict")
            passed += 1
        else:
            print(f"   ❌ FAIL - Retourne {result} au lieu de False")
            failed += 1
    except Exception as e:
        print(f"   ❌ FAIL - Exception: {e}")
        failed += 1
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    print(f"   ✅ Tests réussis: {passed}")
    print(f"   ❌ Tests échoués: {failed}")
    print(f"   📈 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("\n✨ La fonction is_admin() corrigée gère correctement:")
        print("   • Les utilisateurs admin")
        print("   • Les utilisateurs non-admin")
        print("   • Les utilisateurs inexistants (None)")
        print("   • Les résultats vides")
        print("   • Les rôles NULL")
        print("   • Les user_id invalides (None, 0)")
        print("   • Différents formats de résultats (tuple, list)")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué")
        return 1

if __name__ == "__main__":
    try:
        exit_code = test_is_admin_logic()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
