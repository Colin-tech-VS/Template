"""
Tests de performance pour vérifier l'optimisation Backend (Supabase/Postgres)
Vérifie que les endpoints répondent en moins de 500ms
"""

import time
import os
import sys
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5000')
API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY', '')
TARGET_RESPONSE_TIME = 500  # ms

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class PerformanceTest:
    """Classe pour tester les performances des endpoints"""
    
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.results = []
    
    def test_endpoint(self, name, path, method='GET', headers=None, expected_status=200):
        """
        Teste un endpoint et mesure son temps de réponse
        
        Args:
            name: Nom du test
            path: Chemin de l'endpoint
            method: Méthode HTTP (GET, POST, etc.)
            headers: Headers additionnels
            expected_status: Code de statut HTTP attendu
        
        Returns:
            dict: Résultats du test
        """
        url = f"{self.base_url}{path}"
        headers = headers or {}
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Méthode {method} non supportée")
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Vérifier le code de statut
            status_ok = response.status_code == expected_status
            
            # Vérifier le temps de réponse
            performance_ok = elapsed_ms < TARGET_RESPONSE_TIME
            
            result = {
                'name': name,
                'path': path,
                'elapsed_ms': elapsed_ms,
                'status_code': response.status_code,
                'expected_status': expected_status,
                'status_ok': status_ok,
                'performance_ok': performance_ok,
                'success': status_ok and performance_ok
            }
            
            self.results.append(result)
            return result
            
        except Exception as e:
            result = {
                'name': name,
                'path': path,
                'elapsed_ms': -1,
                'status_code': 0,
                'expected_status': expected_status,
                'status_ok': False,
                'performance_ok': False,
                'success': False,
                'error': str(e)
            }
            self.results.append(result)
            return result
    
    def print_result(self, result):
        """Affiche le résultat d'un test"""
        name = result['name']
        elapsed_ms = result['elapsed_ms']
        status = result['status_code']
        
        if result['success']:
            color = GREEN
            symbol = '✓'
        elif not result['performance_ok'] and result['status_ok']:
            color = YELLOW
            symbol = '⚠'
        else:
            color = RED
            symbol = '✗'
        
        if elapsed_ms >= 0:
            print(f"{color}{symbol} {name:40s} {elapsed_ms:6.0f}ms  (HTTP {status}){RESET}")
        else:
            error = result.get('error', 'Unknown error')
            print(f"{color}{symbol} {name:40s} ERREUR: {error}{RESET}")
    
    def print_summary(self):
        """Affiche le résumé des tests"""
        total = len(self.results)
        success = sum(1 for r in self.results if r['success'])
        perf_ok = sum(1 for r in self.results if r['performance_ok'])
        status_ok = sum(1 for r in self.results if r['status_ok'])
        
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}RÉSUMÉ DES TESTS DE PERFORMANCE{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        print(f"Total de tests: {total}")
        print(f"Tests réussis: {GREEN}{success}{RESET}/{total}")
        print(f"Performance OK (<{TARGET_RESPONSE_TIME}ms): {GREEN}{perf_ok}{RESET}/{total}")
        print(f"Status HTTP OK: {GREEN}{status_ok}{RESET}/{total}")
        
        # Temps moyen
        valid_times = [r['elapsed_ms'] for r in self.results if r['elapsed_ms'] >= 0]
        if valid_times:
            avg_time = sum(valid_times) / len(valid_times)
            min_time = min(valid_times)
            max_time = max(valid_times)
            print(f"\nTemps de réponse:")
            print(f"  Minimum: {GREEN}{min_time:.0f}ms{RESET}")
            print(f"  Moyen: {avg_time:.0f}ms")
            print(f"  Maximum: {RED if max_time > TARGET_RESPONSE_TIME else GREEN}{max_time:.0f}ms{RESET}")
        
        # Tests les plus lents
        slow_tests = [r for r in self.results if r['elapsed_ms'] > TARGET_RESPONSE_TIME]
        if slow_tests:
            print(f"\n{YELLOW}⚠ Tests trop lents (>{TARGET_RESPONSE_TIME}ms):{RESET}")
            for r in sorted(slow_tests, key=lambda x: x['elapsed_ms'], reverse=True)[:5]:
                print(f"  - {r['name']:40s} {r['elapsed_ms']:.0f}ms")
        
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        return success == total


def run_performance_tests():
    """Exécute tous les tests de performance"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TESTS DE PERFORMANCE - BACKEND SUPABASE/POSTGRES{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"URL de base: {BASE_URL}")
    print(f"Objectif de performance: <{TARGET_RESPONSE_TIME}ms par endpoint")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    tester = PerformanceTest(BASE_URL, API_KEY)
    
    # Tests des pages publiques
    print(f"{BLUE}📄 Pages publiques{RESET}")
    tester.test_endpoint("Page d'accueil", "/")
    tester.test_endpoint("Page à propos", "/about")
    tester.test_endpoint("Page boutique", "/boutique")
    tester.test_endpoint("Page expositions", "/expositions")
    tester.test_endpoint("Page créations sur mesure", "/creations-sur-mesure")
    
    for result in tester.results[-5:]:
        tester.print_result(result)
    
    # Tests des API endpoints (avec clé API)
    print(f"\n{BLUE}🔌 API Endpoints{RESET}")
    api_headers = {'X-API-Key': API_KEY} if API_KEY else {}
    
    if API_KEY:
        tester.test_endpoint("API - Settings", "/api/export/settings", headers=api_headers)
        tester.test_endpoint("API - Paintings", "/api/export/paintings", headers=api_headers)
        tester.test_endpoint("API - Users", "/api/export/users", headers=api_headers)
        tester.test_endpoint("API - Orders", "/api/export/orders", headers=api_headers)
        tester.test_endpoint("API - Stats", "/api/export/stats", headers=api_headers)
        tester.test_endpoint("API - Stripe PK", "/api/stripe-pk")
        
        for result in tester.results[-6:]:
            tester.print_result(result)
    else:
        print(f"{YELLOW}⚠ Pas de clé API - tests API ignorés{RESET}")
    
    # Tests spécifiques de performance
    print(f"\n{BLUE}⚡ Tests de charge{RESET}")
    
    # Test répété pour vérifier la stabilité du pool
    times = []
    for i in range(5):
        result = tester.test_endpoint(f"Page accueil (essai {i+1})", "/")
        times.append(result['elapsed_ms'])
        if i == 4:  # Afficher seulement le dernier
            tester.print_result(result)
    
    # Vérifier que le pool améliore les performances
    if len(times) >= 3:
        first_avg = sum(times[:2]) / 2
        last_avg = sum(times[-3:]) / 3
        improvement = ((first_avg - last_avg) / first_avg) * 100
        
        if improvement > 0:
            print(f"  {GREEN}✓ Pool de connexions efficace: {improvement:.1f}% plus rapide après warmup{RESET}")
        else:
            print(f"  {YELLOW}⚠ Pas d'amélioration notable avec le pool{RESET}")
    
    # Résumé final
    success = tester.print_summary()
    
    return 0 if success else 1


if __name__ == '__main__':
    try:
        exit_code = run_performance_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrompus par l'utilisateur{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Erreur lors des tests: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
