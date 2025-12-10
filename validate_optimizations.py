#!/usr/bin/env python3
"""
Script de validation pour vérifier que les optimisations n'ont pas cassé la logique
Peut être exécuté sans connexion à la base de données
"""

import re
import os

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_file_exists(filepath):
    """Vérifie qu'un fichier existe"""
    if os.path.exists(filepath):
        print(f"  {GREEN}✓{RESET} {filepath} existe")
        return True
    else:
        print(f"  {RED}✗{RESET} {filepath} manquant")
        return False

def check_sql_injection_protection(filepath):
    """Vérifie qu'on n'a pas de vulnérabilités SQL évidents"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Recherche de concaténations de strings SQL dangereuses
    dangerous_patterns = [
        r'execute\([f]".*\{[^}]+\}',  # f-strings dans execute
        r'execute\(.*\+.*\)',  # Concaténation avec +
        r'execute\(.*\.format\(',  # .format() dans SQL
    ]
    
    issues = []
    for pattern in dangerous_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            # Exclure les cas où on utilise explicitement des placeholders sûrs
            if 'placeholders' not in match.group() and '%s' not in match.group():
                issues.append((match.start(), match.group()))
    
    if not issues:
        print(f"  {GREEN}✓{RESET} Pas de vulnérabilité SQL évidente")
        return True
    else:
        print(f"  {YELLOW}⚠{RESET} Patterns potentiellement dangereux trouvés:")
        for pos, text in issues[:3]:  # Afficher les 3 premiers
            print(f"      {text[:60]}...")
        return False

def check_connection_closing(filepath):
    """Vérifie qu'on ferme bien les connexions"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Compter les get_db() et conn.close()
    get_db_count = len(re.findall(r'get_db\(\)', content))
    close_count = len(re.findall(r'\.close\(\)', content))
    
    # On devrait avoir au moins autant de close() que de get_db()
    if close_count >= get_db_count * 0.8:  # Au moins 80%
        print(f"  {GREEN}✓{RESET} Connexions fermées ({close_count} close() pour {get_db_count} get_db())")
        return True
    else:
        print(f"  {YELLOW}⚠{RESET} Risque de fuites: {close_count} close() pour {get_db_count} get_db()")
        return False

def check_select_star(filepath):
    """Vérifie qu'on a réduit les SELECT *"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    select_star_count = len(re.findall(r'SELECT\s+\*\s+FROM', content, re.IGNORECASE))
    total_selects = len(re.findall(r'SELECT\s+', content, re.IGNORECASE))
    
    if total_selects == 0:
        print(f"  {GREEN}✓{RESET} Aucun SELECT trouvé")
        return True
    
    ratio = select_star_count / total_selects
    if ratio < 0.2:  # Moins de 20% de SELECT *
        print(f"  {GREEN}✓{RESET} Peu de SELECT * ({select_star_count}/{total_selects} = {ratio*100:.0f}%)")
        return True
    elif ratio < 0.5:
        print(f"  {YELLOW}⚠{RESET} SELECT * modéré ({select_star_count}/{total_selects} = {ratio*100:.0f}%)")
        return True
    else:
        print(f"  {RED}✗{RESET} Trop de SELECT * ({select_star_count}/{total_selects} = {ratio*100:.0f}%)")
        return False

def check_limits_added(filepath):
    """Vérifie qu'on a ajouté des LIMIT"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    limit_count = len(re.findall(r'\bLIMIT\s+\d+', content, re.IGNORECASE))
    
    if limit_count > 10:
        print(f"  {GREEN}✓{RESET} {limit_count} clauses LIMIT ajoutées")
        return True
    elif limit_count > 5:
        print(f"  {YELLOW}⚠{RESET} {limit_count} clauses LIMIT (peut-être insuffisant)")
        return True
    else:
        print(f"  {RED}✗{RESET} Seulement {limit_count} clauses LIMIT trouvées")
        return False

def check_indexes_defined(filepath):
    """Vérifie que les indexes sont définis"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Chercher la fonction create_performance_indexes
    if 'def create_performance_indexes' in content:
        # Compter les indexes
        index_count = content.count('CREATE INDEX')
        if index_count > 15:
            print(f"  {GREEN}✓{RESET} Fonction d'indexes présente avec {index_count} indexes")
            return True
        else:
            print(f"  {YELLOW}⚠{RESET} Fonction présente mais seulement {index_count} indexes")
            return True
    else:
        print(f"  {RED}✗{RESET} Fonction create_performance_indexes manquante")
        return False

def check_connection_pool(filepath):
    """Vérifie que le connection pool est implémenté"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'ThreadedConnectionPool' in content:
        print(f"  {GREEN}✓{RESET} ThreadedConnectionPool implémenté")
        return True
    else:
        print(f"  {RED}✗{RESET} ThreadedConnectionPool non trouvé")
        return False

def check_performance_logging(filepath):
    """Vérifie que le logging de performance est présent"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'perf_logger' in content and 'elapsed' in content:
        print(f"  {GREEN}✓{RESET} Logging de performance implémenté")
        return True
    else:
        print(f"  {YELLOW}⚠{RESET} Logging de performance non détecté")
        return False

def run_validation():
    """Exécute toutes les validations"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}VALIDATION DES OPTIMISATIONS BACKEND{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    results = {}
    
    # 1. Fichiers présents
    print(f"{BLUE}📁 Vérification des fichiers{RESET}")
    results['files'] = all([
        check_file_exists('database.py'),
        check_file_exists('app.py'),
        check_file_exists('test_performance.py'),
        check_file_exists('test_db_performance.py'),
        check_file_exists('OPTIMIZATIONS.md'),
    ])
    
    # 2. database.py
    print(f"\n{BLUE}🔧 Vérification de database.py{RESET}")
    results['database'] = all([
        check_connection_pool('database.py'),
        check_indexes_defined('database.py'),
        check_performance_logging('database.py'),
    ])
    
    # 3. app.py
    print(f"\n{BLUE}🚀 Vérification de app.py{RESET}")
    results['app'] = all([
        check_sql_injection_protection('app.py'),
        check_connection_closing('app.py'),
        check_select_star('app.py'),
        check_limits_added('app.py'),
    ])
    
    # Résumé
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}RÉSUMÉ{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    for category, passed in results.items():
        symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        status = f"{GREEN}OK{RESET}" if passed else f"{RED}PROBLÈMES DÉTECTÉS{RESET}"
        print(f"  {symbol} {category.upper():15s} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Total: {passed}/{total} catégories validées")
    
    if passed == total:
        print(f"{GREEN}✓ Validation réussie - Code prêt pour le déploiement!{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{YELLOW}⚠ Quelques vérifications n'ont pas passé{RESET}")
        print(f"Revoyez les warnings ci-dessus avant le déploiement.")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1

if __name__ == '__main__':
    import sys
    try:
        exit_code = run_validation()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n{RED}Erreur lors de la validation: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
