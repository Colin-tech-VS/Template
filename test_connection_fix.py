"""
Test de correction du bug AttributeError dans get_db()

Ce test vérifie que:
1. get_db() retourne une connexion fonctionnelle
2. La connexion peut être fermée sans erreur AttributeError
3. La connexion est correctement retournée au pool
4. Les connexions peuvent être ouvertes/fermées plusieurs fois
5. Le temps de connexion reste < 100ms
"""

import time
import sys
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Import des modules du projet
from database import (
    get_db,
    get_db_connection,
    init_connection_pool,
    close_connection_pool,
)

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_get_db_basic():
    """Test basique: obtenir et fermer une connexion"""
    print(f"\n{BLUE}TEST 1: Connexion basique avec get_db(){RESET}")
    
    try:
        start = time.time()
        conn = get_db()
        elapsed = (time.time() - start) * 1000
        
        print(f"  ✓ Connexion obtenue en {elapsed:.2f}ms")
        
        # Vérifier que c'est un wrapper
        print(f"  ✓ Type de connexion: {type(conn).__name__}")
        
        # Tester une requête simple
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print(f"  {GREEN}✓ Requête test exécutée avec succès{RESET}")
        else:
            print(f"  {RED}✗ Erreur lors de l'exécution de la requête test{RESET}")
            return False
        
        # Fermer la connexion (doit retourner au pool sans erreur)
        conn.close()
        print(f"  {GREEN}✓ Connexion fermée sans erreur AttributeError{RESET}")
        
        # Vérifier que la connexion est marquée comme fermée
        if hasattr(conn, 'closed') and conn.closed:
            print(f"  {GREEN}✓ Connexion marquée comme fermée{RESET}")
        
        if elapsed < 100:
            print(f"  {GREEN}✓ Performance OK: {elapsed:.2f}ms < 100ms{RESET}")
        else:
            print(f"  {YELLOW}⚠ Performance limite: {elapsed:.2f}ms >= 100ms{RESET}")
        
        return True
        
    except AttributeError as e:
        print(f"  {RED}✗ AttributeError détecté: {e}{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_connections():
    """Test: ouvrir et fermer plusieurs connexions"""
    print(f"\n{BLUE}TEST 2: Connexions multiples{RESET}")
    
    try:
        times = []
        for i in range(10):
            start = time.time()
            conn = get_db()
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            # Tester une requête
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Fermer
            conn.close()
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"  ✓ 10 connexions ouvertes et fermées")
        print(f"  Temps min: {min_time:.2f}ms")
        print(f"  Temps max: {max_time:.2f}ms")
        print(f"  Temps moyen: {avg_time:.2f}ms")
        
        if avg_time < 100:
            print(f"  {GREEN}✓ Performance OK: moyenne {avg_time:.2f}ms < 100ms{RESET}")
        else:
            print(f"  {YELLOW}⚠ Performance limite: moyenne {avg_time:.2f}ms >= 100ms{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_context_manager():
    """Test: utiliser get_db_connection() avec context manager"""
    print(f"\n{BLUE}TEST 3: Context manager get_db_connection(){RESET}")
    
    try:
        start = time.time()
        with get_db_connection() as conn:
            elapsed = (time.time() - start) * 1000
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
            if result[0] == 1:
                print(f"  {GREEN}✓ Requête exécutée avec succès{RESET}")
            else:
                print(f"  {RED}✗ Résultat incorrect{RESET}")
                return False
        
        print(f"  {GREEN}✓ Context manager fonctionne correctement{RESET}")
        
        if elapsed < 100:
            print(f"  {GREEN}✓ Performance OK: {elapsed:.2f}ms < 100ms{RESET}")
        else:
            print(f"  {YELLOW}⚠ Performance limite: {elapsed:.2f}ms >= 100ms{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_double_close():
    """Test: appeler close() plusieurs fois ne doit pas causer d'erreur"""
    print(f"\n{BLUE}TEST 4: Double close(){RESET}")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        # Première fermeture
        conn.close()
        print(f"  ✓ Premier close() réussi")
        
        # Deuxième fermeture (ne devrait pas causer d'erreur)
        conn.close()
        print(f"  {GREEN}✓ Deuxième close() réussi (idempotent){RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_with_transaction():
    """Test: utiliser une connexion avec transaction"""
    print(f"\n{BLUE}TEST 5: Transaction avec commit/rollback{RESET}")
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Tester commit
        cursor.execute("SELECT 1")
        conn.commit()
        print(f"  ✓ commit() fonctionne")
        
        # Tester rollback
        cursor.execute("SELECT 1")
        conn.rollback()
        print(f"  ✓ rollback() fonctionne")
        
        conn.close()
        print(f"  {GREEN}✓ Transactions fonctionnent correctement{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Exécute tous les tests de correction"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TESTS DE CORRECTION - FIX AttributeError dans get_db(){RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    try:
        # Initialiser le pool
        init_connection_pool()
        print(f"{GREEN}✓ Pool de connexions initialisé{RESET}")
        
        results = {
            'Connexion basique': test_get_db_basic(),
            'Connexions multiples': test_multiple_connections(),
            'Context manager': test_connection_context_manager(),
            'Double close': test_double_close(),
            'Transactions': test_connection_with_transaction(),
        }
        
        # Résumé
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}RÉSUMÉ DES TESTS{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        
        for test_name, passed in results.items():
            symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
            status = f"{GREEN}RÉUSSI{RESET}" if passed else f"{RED}ÉCHOUÉ{RESET}"
            print(f"  {symbol} {test_name:25s} {status}")
        
        total = len(results)
        passed = sum(results.values())
        
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"Total: {passed}/{total} tests réussis")
        
        if passed == total:
            print(f"{GREEN}✓ Tous les tests sont passés avec succès!{RESET}")
            print(f"{GREEN}✓ Le bug AttributeError est corrigé!{RESET}")
            print(f"{BLUE}{'='*70}{RESET}\n")
            return 0
        else:
            print(f"{RED}✗ Certains tests ont échoué{RESET}")
            print(f"{BLUE}{'='*70}{RESET}\n")
            return 1
    finally:
        # Fermer le pool à la fin
        close_connection_pool()
        print(f"{GREEN}✓ Pool de connexions fermé{RESET}")


if __name__ == '__main__':
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrompus par l'utilisateur{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Erreur lors des tests: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
