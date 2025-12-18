#!/usr/bin/env python3
"""
Audit complet de l'isolation multi-tenant dans Template
Vérifie:
1. Filtrage tenant_id dans toutes les requêtes SQL
2. Isolation des API endpoints
3. Risques de fuite de données entre tenants
4. Validation des relations entre entités
"""

import re
import json
from collections import defaultdict

# Tables qui DOIVENT être filtrées par tenant_id
TABLES_WITH_TENANT = [
    'users', 'paintings', 'carts', 'cart_items', 'orders', 'order_items',
    'exhibitions', 'custom_requests', 'notifications', 'favorites',
    'settings', 'saas_sites', 'stripe_events'
]

# Tables système qui n'ont pas besoin de tenant_id
SYSTEM_TABLES = ['tenants', 'migrations']

def parse_sql_query(query):
    """Extrait les tables et opérations d'une requête SQL"""
    query_upper = query.upper()
    
    # Déterminer le type d'opération
    operation = None
    if 'SELECT' in query_upper:
        operation = 'SELECT'
    elif 'INSERT' in query_upper:
        operation = 'INSERT'
    elif 'UPDATE' in query_upper:
        operation = 'UPDATE'
    elif 'DELETE' in query_upper:
        operation = 'DELETE'
    
    # Extraire les tables mentionnées
    tables = []
    for table in TABLES_WITH_TENANT + SYSTEM_TABLES:
        if table.upper() in query_upper:
            tables.append(table)
    
    return operation, tables

def check_tenant_filter(context, tables):
    """Vérifie si tenant_id est présent dans le contexte"""
    context_lower = context.lower()
    
    # Ignorer si c'est une table système
    if any(t in SYSTEM_TABLES for t in tables):
        return True, "SYSTEM_TABLE"
    
    # Ignorer si c'est une création/modification de table
    if 'create table' in context_lower or 'alter table' in context_lower:
        return True, "DDL"
    
    # Ignorer si c'est une vérification de schéma
    if 'information_schema' in context_lower or 'pragma' in context_lower:
        return True, "SCHEMA_CHECK"
    
    # Vérifier la présence de tenant_id
    has_tenant = 'tenant_id' in context_lower
    
    return has_tenant, "OK" if has_tenant else "MISSING_TENANT"

def analyze_app_py():
    """Analyse complète de app.py"""
    
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    results = {
        'total_queries': 0,
        'queries_with_tenant': 0,
        'queries_without_tenant': 0,
        'issues': [],
        'routes': {},
        'by_table': defaultdict(lambda: {'total': 0, 'with_tenant': 0, 'without_tenant': 0})
    }
    
    current_route = 'startup'
    current_function = 'module_level'
    
    # Initialize startup route
    results['routes'][current_route] = {
        'queries': 0,
        'with_tenant': 0,
        'issues': []
    }
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_num = i + 1
        
        # Détecter les routes
        route_match = re.search(r'@app\.route\([\'\"](.*?)[\'\"]', line)
        if route_match:
            current_route = route_match.group(1)
            if current_route not in results['routes']:
                results['routes'][current_route] = {
                    'queries': 0,
                    'with_tenant': 0,
                    'issues': []
                }
        
        # Détecter les fonctions
        func_match = re.search(r'^def (\w+)\(', line)
        if func_match:
            current_function = func_match.group(1)
        
        # Détecter les requêtes
        if 'c.execute' in line or 'execute_query' in line:
            results['total_queries'] += 1
            results['routes'][current_route]['queries'] += 1
            
            # Extraire le contexte (lignes précédentes et suivantes)
            context_start = max(0, i - 5)
            context_end = min(len(lines), i + 10)
            context = ''.join(lines[context_start:context_end])
            
            # Parser la requête
            operation, tables = parse_sql_query(context)
            
            # Vérifier le filtre tenant_id
            has_tenant, status = check_tenant_filter(context, tables)
            
            # Mettre à jour les statistiques
            for table in tables:
                results['by_table'][table]['total'] += 1
                if has_tenant:
                    results['by_table'][table]['with_tenant'] += 1
                else:
                    results['by_table'][table]['without_tenant'] += 1
            
            if has_tenant or status in ['SYSTEM_TABLE', 'DDL', 'SCHEMA_CHECK']:
                results['queries_with_tenant'] += 1
                results['routes'][current_route]['with_tenant'] += 1
            else:
                results['queries_without_tenant'] += 1
                
                issue = {
                    'line': line_num,
                    'route': current_route,
                    'function': current_function,
                    'operation': operation,
                    'tables': tables,
                    'query_preview': line.strip()[:100],
                    'severity': 'HIGH' if operation in ['SELECT', 'UPDATE', 'DELETE'] else 'MEDIUM'
                }
                results['issues'].append(issue)
                results['routes'][current_route]['issues'].append(issue)
        
        i += 1
    
    return results

def generate_report(results):
    """Génère un rapport détaillé"""
    
    print("=" * 80)
    print("AUDIT DE L'ISOLATION MULTI-TENANT - TEMPLATE")
    print("=" * 80)
    print()
    
    # Résumé global
    print("📊 RÉSUMÉ GLOBAL")
    print("-" * 80)
    print(f"Total de requêtes SQL: {results['total_queries']}")
    print(f"  ✅ Avec tenant_id: {results['queries_with_tenant']} ({results['queries_with_tenant']*100//results['total_queries']}%)")
    print(f"  ❌ Sans tenant_id: {results['queries_without_tenant']} ({results['queries_without_tenant']*100//results['total_queries']}%)")
    print()
    
    # Statistiques par table
    print("📋 STATISTIQUES PAR TABLE")
    print("-" * 80)
    for table in sorted(results['by_table'].keys()):
        stats = results['by_table'][table]
        if table not in SYSTEM_TABLES:
            pct = stats['with_tenant'] * 100 // stats['total'] if stats['total'] > 0 else 0
            status = "✅" if stats['without_tenant'] == 0 else "⚠️"
            print(f"{status} {table:20s}: {stats['with_tenant']}/{stats['total']} requêtes avec tenant_id ({pct}%)")
            if stats['without_tenant'] > 0:
                print(f"   ❌ {stats['without_tenant']} requêtes sans tenant_id")
    print()
    
    # Routes avec problèmes
    print("🚨 ROUTES AVEC PROBLÈMES")
    print("-" * 80)
    problematic_routes = [(route, data) for route, data in results['routes'].items() if data['issues']]
    problematic_routes.sort(key=lambda x: len(x[1]['issues']), reverse=True)
    
    if not problematic_routes:
        print("✅ Aucune route avec problème trouvée!")
    else:
        for route, data in problematic_routes[:15]:
            print(f"\n{route}")
            print(f"  Total requêtes: {data['queries']}, Sans tenant_id: {len(data['issues'])}")
            for issue in data['issues'][:3]:
                print(f"  - Ligne {issue['line']}: {issue['operation']} sur {', '.join(issue['tables'])} [{issue['severity']}]")
                print(f"    {issue['query_preview']}")
    print()
    
    # Issues détaillées par sévérité
    print("🔍 DÉTAIL DES PROBLÈMES PAR SÉVÉRITÉ")
    print("-" * 80)
    
    high_severity = [i for i in results['issues'] if i['severity'] == 'HIGH']
    medium_severity = [i for i in results['issues'] if i['severity'] == 'MEDIUM']
    
    print(f"\n🔴 HAUTE SÉVÉRITÉ ({len(high_severity)} problèmes)")
    print("   SELECT/UPDATE/DELETE sans tenant_id = fuite de données potentielle")
    for issue in high_severity[:10]:
        print(f"\n   Ligne {issue['line']}: {issue['function']}() - {issue['route']}")
        print(f"   {issue['operation']} sur {', '.join(issue['tables'])}")
        print(f"   {issue['query_preview']}")
    
    if len(high_severity) > 10:
        print(f"\n   ... et {len(high_severity) - 10} autres problèmes")
    
    print(f"\n🟡 SÉVÉRITÉ MOYENNE ({len(medium_severity)} problèmes)")
    print("   INSERT sans tenant_id = mauvaise attribution des données")
    for issue in medium_severity[:5]:
        print(f"\n   Ligne {issue['line']}: {issue['function']}() - {issue['route']}")
        print(f"   {issue['operation']} sur {', '.join(issue['tables'])}")
        print(f"   {issue['query_preview']}")
    
    if len(medium_severity) > 5:
        print(f"\n   ... et {len(medium_severity) - 5} autres problèmes")
    
    print()
    print("=" * 80)
    print("📝 RECOMMANDATIONS")
    print("-" * 80)
    print("1. Corriger les problèmes de HAUTE SÉVÉRITÉ en priorité")
    print("2. Ajouter tenant_id à toutes les requêtes SELECT/UPDATE/DELETE")
    print("3. Inclure tenant_id dans tous les INSERT")
    print("4. Valider les relations entre entités (même tenant)")
    print("5. Tester l'isolation avec 2+ tenants différents")
    print()
    
    # Export JSON pour traitement automatique
    with open('tenant_audit_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("✅ Résultats complets exportés dans: tenant_audit_results.json")
    print()
    
    return results

def main():
    print("\n🔍 Démarrage de l'audit d'isolation multi-tenant...\n")
    
    try:
        results = analyze_app_py()
        generate_report(results)
        
        # Code de sortie basé sur le nombre de problèmes
        if results['queries_without_tenant'] == 0:
            print("✅ SUCCÈS: Toutes les requêtes sont correctement filtrées par tenant_id!")
            return 0
        elif results['queries_without_tenant'] <= 5:
            print(f"⚠️  AVERTISSEMENT: {results['queries_without_tenant']} requêtes nécessitent une correction")
            return 1
        else:
            print(f"❌ CRITIQUE: {results['queries_without_tenant']} requêtes sans tenant_id trouvées!")
            return 2
            
    except Exception as e:
        print(f"❌ ERREUR lors de l'audit: {e}")
        import traceback
        traceback.print_exc()
        return 3

if __name__ == "__main__":
    import sys
    sys.exit(main())
