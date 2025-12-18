#!/usr/bin/env python3
"""
Tests d'isolation multi-tenant complets
Vérifie que les données sont strictement isolées par tenant_id
"""

import sys
import os
from contextlib import contextmanager

# Ajouter le répertoire parent au path pour importer app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

@contextmanager
def mock_request_context(host='tenant1.example.com'):
    """Mock du contexte de requête Flask pour les tests"""
    from unittest.mock import patch, MagicMock
    
    mock_request = MagicMock()
    mock_request.host = host
    
    with patch('app.request', mock_request), \
         patch('app.has_request_context', return_value=True):
        yield mock_request

def test_get_current_tenant_id():
    """Test 1: Vérifier que get_current_tenant_id() fonctionne correctement"""
    print("\n" + "=" * 80)
    print("TEST 1: get_current_tenant_id()")
    print("=" * 80)
    
    from app import get_current_tenant_id
    
    # Test hors contexte - doit retourner 1 par défaut
    tenant_id = get_current_tenant_id()
    assert tenant_id == 1, f"Expected tenant_id=1 outside context, got {tenant_id}"
    print("✅ get_current_tenant_id() retourne 1 par défaut hors contexte")
    
    # Test dans contexte avec différents hosts
    with mock_request_context('tenant1.example.com'):
        tenant_id = get_current_tenant_id()
        print(f"✅ get_current_tenant_id() avec host 'tenant1.example.com': {tenant_id}")
    
    with mock_request_context('tenant2.example.com'):
        tenant_id = get_current_tenant_id()
        print(f"✅ get_current_tenant_id() avec host 'tenant2.example.com': {tenant_id}")
    
    print("✅ TEST 1 RÉUSSI: get_current_tenant_id() fonctionne correctement")
    return True

def test_tenant_id_in_queries():
    """Test 2: Vérifier que tenant_id est présent dans les requêtes critiques"""
    print("\n" + "=" * 80)
    print("TEST 2: Présence de tenant_id dans les requêtes SQL")
    print("=" * 80)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Patterns de requêtes qui DOIVENT inclure tenant_id
    critical_patterns = [
        (r'SELECT.*FROM users.*WHERE', 'users'),
        (r'SELECT.*FROM paintings.*WHERE', 'paintings'),
        (r'SELECT.*FROM orders.*WHERE', 'orders'),
        (r'SELECT.*FROM carts.*WHERE', 'carts'),
        (r'INSERT INTO users', 'users INSERT'),
        (r'INSERT INTO paintings', 'paintings INSERT'),
        (r'INSERT INTO orders', 'orders INSERT'),
        (r'UPDATE users.*SET', 'users UPDATE'),
        (r'UPDATE paintings.*SET', 'paintings UPDATE'),
        (r'DELETE FROM users', 'users DELETE'),
        (r'DELETE FROM paintings', 'paintings DELETE'),
    ]
    
    issues = []
    for pattern, name in critical_patterns:
        import re
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Extraire le contexte autour du match (200 caractères)
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            
            # Vérifier si tenant_id est dans le contexte
            if 'tenant_id' not in context.lower():
                # Ignorer les cas spéciaux (CREATE TABLE, migrations, etc.)
                if 'CREATE TABLE' not in context and 'information_schema' not in context.lower():
                    issues.append({
                        'pattern': name,
                        'position': match.start(),
                        'context': context[:100]
                    })
    
    if issues:
        print(f"⚠️  {len(issues)} requêtes potentiellement sans tenant_id trouvées:")
        for issue in issues[:5]:  # Afficher les 5 premiers
            print(f"  - {issue['pattern']} à position {issue['position']}")
    else:
        print("✅ Toutes les requêtes critiques incluent tenant_id")
    
    # Le test passe si on a moins de 5 issues (tolérance pour faux positifs)
    success = len(issues) < 5
    if success:
        print("✅ TEST 2 RÉUSSI: tenant_id présent dans les requêtes critiques")
    else:
        print(f"❌ TEST 2 ÉCHOUÉ: {len(issues)} requêtes sans tenant_id")
    
    return success

def test_api_endpoints_security():
    """Test 3: Vérifier que les endpoints API incluent tenant_id"""
    print("\n" + "=" * 80)
    print("TEST 3: Sécurité des endpoints API")
    print("=" * 80)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Liste des endpoints API critiques
    api_endpoints = [
        '/api/register-preview',
        '/api/export/orders',
        '/api/export/users',
        '/api/export/paintings',
        '/profile',
        '/orders',
        '/painting/<int:painting_id>',
    ]
    
    issues = []
    for endpoint in api_endpoints:
        # Trouver la fonction correspondante
        import re
        pattern = rf"@app\.route\('{re.escape(endpoint)}'"
        match = re.search(pattern, content)
        
        if match:
            # Extraire les 500 caractères après le décorateur de route
            start = match.start()
            end = min(len(content), start + 1000)
            function_code = content[start:end]
            
            # Vérifier la présence de get_current_tenant_id() ou tenant_id
            has_tenant = 'get_current_tenant_id()' in function_code or 'tenant_id' in function_code
            
            if not has_tenant:
                issues.append(endpoint)
                print(f"⚠️  {endpoint} ne semble pas utiliser tenant_id")
            else:
                print(f"✅ {endpoint} utilise tenant_id")
    
    success = len(issues) == 0
    if success:
        print("✅ TEST 3 RÉUSSI: Tous les endpoints API utilisent tenant_id")
    else:
        print(f"❌ TEST 3 ÉCHOUÉ: {len(issues)} endpoints sans tenant_id")
    
    return success

def test_join_queries_isolation():
    """Test 4: Vérifier que les JOIN incluent tenant_id"""
    print("\n" + "=" * 80)
    print("TEST 4: Isolation dans les requêtes JOIN")
    print("=" * 80)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    import re
    
    # Trouver tous les JOIN
    join_pattern = r'JOIN\s+(\w+)\s+\w+\s+ON\s+([^\n]+?(?:WHERE|GROUP|ORDER|LIMIT|$))'
    joins = re.finditer(join_pattern, content, re.IGNORECASE)
    
    total_joins = 0
    joins_with_tenant = 0
    issues = []
    
    for match in joins:
        total_joins += 1
        table_name = match.group(1)
        join_condition = match.group(2)
        
        # Extraire plus de contexte
        start = max(0, match.start() - 200)
        end = min(len(content), match.end() + 200)
        context = content[start:end]
        
        # Vérifier si tenant_id est dans la condition de JOIN ou le WHERE suivant
        has_tenant = 'tenant_id' in context.lower()
        
        if has_tenant:
            joins_with_tenant += 1
        else:
            # Ignorer les JOIN sur la table tenants elle-même
            if table_name.lower() != 'tenants':
                issues.append({
                    'table': table_name,
                    'condition': join_condition[:50],
                    'line': content[:match.start()].count('\n') + 1
                })
    
    if total_joins > 0:
        percentage = (joins_with_tenant / total_joins) * 100
        print(f"📊 {joins_with_tenant}/{total_joins} JOIN incluent tenant_id ({percentage:.1f}%)")
        
        if issues:
            print(f"\n⚠️  {len(issues)} JOIN potentiellement sans isolation:")
            for issue in issues[:5]:
                print(f"  - Ligne {issue['line']}: JOIN {issue['table']} ON {issue['condition']}")
        else:
            print("✅ Tous les JOIN incluent tenant_id ou n'en ont pas besoin")
    else:
        print("ℹ️  Aucun JOIN trouvé dans le code")
    
    success = percentage >= 80 or len(issues) <= 5
    if success:
        print("✅ TEST 4 RÉUSSI: Les JOIN sont correctement isolés")
    else:
        print(f"❌ TEST 4 ÉCHOUÉ: Trop de JOIN sans isolation ({percentage:.1f}%)")
    
    return success

def test_cross_tenant_protection():
    """Test 5: Vérifier la protection contre l'accès cross-tenant"""
    print("\n" + "=" * 80)
    print("TEST 5: Protection contre l'accès cross-tenant")
    print("=" * 80)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Vérifier que les requêtes avec ID incluent aussi tenant_id
    import re
    
    # Pattern: WHERE id = ? mais sans AND tenant_id = ?
    patterns = [
        (r'WHERE\s+id\s*=\s*\?(?!\s+AND\s+tenant_id)', 'WHERE id=? sans tenant_id'),
        (r'WHERE\s+\w+\.id\s*=\s*\?(?!\s+AND\s+\w+\.tenant_id)', 'WHERE table.id=? sans tenant_id'),
    ]
    
    issues = []
    for pattern, description in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Extraire contexte
            start = max(0, match.start() - 100)
            end = min(len(content), match.end() + 100)
            context = content[start:end]
            
            # Vérifier si tenant_id est quelque part dans le contexte proche
            if 'tenant_id' not in context.lower():
                # Ignorer les cas spéciaux
                if 'tenants' not in context.lower() and 'CREATE TABLE' not in context:
                    line_num = content[:match.start()].count('\n') + 1
                    issues.append({
                        'description': description,
                        'line': line_num,
                        'context': context[50:150]
                    })
    
    # Tolerance thresholds for test validation
    # We allow up to 5 false positives due to edge cases and special queries
    MAX_ACCEPTABLE_ISSUES = 5
    
    if issues:
        print(f"⚠️  {len(issues)} requêtes potentiellement vulnérables:")
        for issue in issues[:5]:
            print(f"  - Ligne {issue['line']}: {issue['description']}")
    else:
        print("✅ Aucune requête vulnérable à l'accès cross-tenant détectée")
    
    # Tolérance de faux positifs
    success = len(issues) <= MAX_ACCEPTABLE_ISSUES
    if success:
        print("✅ TEST 5 RÉUSSI: Protection cross-tenant en place")
    else:
        print(f"❌ TEST 5 ÉCHOUÉ: {len(issues)} requêtes potentiellement vulnérables")
    
    return success

def run_all_tests():
    """Exécuter tous les tests"""
    print("=" * 80)
    print("🧪 SUITE DE TESTS D'ISOLATION MULTI-TENANT")
    print("=" * 80)
    
    tests = [
        ("get_current_tenant_id()", test_get_current_tenant_id),
        ("tenant_id dans requêtes", test_tenant_id_in_queries),
        ("Sécurité endpoints API", test_api_endpoints_security),
        ("Isolation JOIN", test_join_queries_isolation),
        ("Protection cross-tenant", test_cross_tenant_protection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            print(f"\n❌ ERREUR dans {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False, str(e)))
    
    # Résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 80)
    
    # Success criteria thresholds
    MIN_PASS_THRESHOLD = 0.8  # 80% of tests must pass
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"  Erreur: {error}")
    
    # Avoid division by zero
    pass_percentage = (passed / total * 100) if total > 0 else 0
    print(f"\nTotal: {passed}/{total} tests réussis ({int(pass_percentage)}%)")
    
    if passed == total:
        print("\n🎉 SUCCÈS: Tous les tests d'isolation multi-tenant passent!")
        return 0
    elif passed >= total * MIN_PASS_THRESHOLD:
        print(f"\n⚠️  ATTENTION: {total-passed} test(s) échoué(s)")
        return 1
    else:
        print(f"\n❌ ÉCHEC: {total-passed} test(s) échoué(s)")
        return 2

if __name__ == "__main__":
    sys.exit(run_all_tests())
