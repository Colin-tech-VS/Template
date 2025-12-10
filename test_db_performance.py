"""
Test de performance de la base de données Supabase/Postgres
Vérifie la vitesse des connexions, requêtes et le fonctionnement du pool
"""

import time
import os
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
    execute_query,
    create_performance_indexes
)

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def measure_time(func, *args, **kwargs):
    """Mesure le temps d'exécution d'une fonction"""
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = (time.time() - start) * 1000
    return result, elapsed


def test_connection_pool():
    """Teste le pool de connexions"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 1: POOL DE CONNEXIONS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Initialiser le pool
    print("Initialisation du pool de connexions...")
    _, elapsed = measure_time(init_connection_pool, minconn=2, maxconn=10)
    print(f"  {GREEN}✓ Pool initialisé en {elapsed:.2f}ms{RESET}")
    
    # Test: Obtenir plusieurs connexions
    print("\nTest d'obtention de connexions depuis le pool...")
    times = []
    for i in range(10):
        _, elapsed = measure_time(get_db)
        times.append(elapsed)
        if i == 0:
            print(f"  Première connexion: {elapsed:.2f}ms")
        elif i == 9:
            print(f"  10ème connexion: {elapsed:.2f}ms")
    
    avg_time = sum(times) / len(times)
    print(f"  {GREEN}✓ Temps moyen: {avg_time:.2f}ms{RESET}")
    
    if avg_time < 10:
        print(f"  {GREEN}✓ Excellent: Pool très rapide (<10ms){RESET}")
    elif avg_time < 50:
        print(f"  {YELLOW}⚠ Acceptable: Pool modéré (<50ms){RESET}")
    else:
        print(f"  {RED}✗ Lent: Pool trop lent (>{avg_time:.0f}ms){RESET}")
    
    return avg_time < 50


def test_simple_queries():
    """Teste des requêtes simples"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 2: REQUÊTES SIMPLES{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    queries = [
        ("COUNT users", "SELECT COUNT(*) FROM users"),
        ("COUNT paintings", "SELECT COUNT(*) FROM paintings"),
        ("COUNT orders", "SELECT COUNT(*) FROM orders"),
        ("Settings lookup", "SELECT value FROM settings WHERE key = 'site_name'"),
        ("Recent paintings", "SELECT id, name FROM paintings ORDER BY id DESC LIMIT 5"),
    ]
    
    results = []
    for name, query in queries:
        try:
            _, elapsed = measure_time(execute_query, query, fetch_all=True)
            results.append((name, elapsed, True))
            
            if elapsed < 50:
                print(f"  {GREEN}✓ {name:25s} {elapsed:6.2f}ms{RESET}")
            elif elapsed < 100:
                print(f"  {YELLOW}⚠ {name:25s} {elapsed:6.2f}ms{RESET}")
            else:
                print(f"  {RED}✗ {name:25s} {elapsed:6.2f}ms{RESET}")
        except Exception as e:
            results.append((name, -1, False))
            print(f"  {RED}✗ {name:25s} ERREUR: {e}{RESET}")
    
    success_rate = sum(1 for _, _, ok in results if ok) / len(results) * 100
    avg_time = sum(t for _, t, ok in results if ok and t > 0) / sum(1 for _, _, ok in results if ok)
    
    print(f"\n  Taux de succès: {success_rate:.0f}%")
    print(f"  Temps moyen: {avg_time:.2f}ms")
    
    return success_rate == 100 and avg_time < 100


def test_complex_queries():
    """Teste des requêtes complexes avec JOINs"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 3: REQUÊTES COMPLEXES (JOINS){RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    queries = [
        ("Orders with items", """
            SELECT o.id, o.customer_name, COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id, o.customer_name
            LIMIT 10
        """),
        ("Cart items with paintings", """
            SELECT ci.id, ci.quantity, p.name, p.price
            FROM cart_items ci
            JOIN paintings p ON ci.painting_id = p.id
            LIMIT 20
        """),
        ("Users with order count", """
            SELECT u.id, u.name, COUNT(o.id) as order_count
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            GROUP BY u.id, u.name
            LIMIT 20
        """),
    ]
    
    results = []
    for name, query in queries:
        try:
            _, elapsed = measure_time(execute_query, query, fetch_all=True)
            results.append((name, elapsed, True))
            
            if elapsed < 100:
                print(f"  {GREEN}✓ {name:30s} {elapsed:6.2f}ms{RESET}")
            elif elapsed < 200:
                print(f"  {YELLOW}⚠ {name:30s} {elapsed:6.2f}ms{RESET}")
            else:
                print(f"  {RED}✗ {name:30s} {elapsed:6.2f}ms (trop lent){RESET}")
        except Exception as e:
            results.append((name, -1, False))
            print(f"  {RED}✗ {name:30s} ERREUR: {e}{RESET}")
    
    success_rate = sum(1 for _, _, ok in results if ok) / len(results) * 100
    valid_times = [t for _, t, ok in results if ok and t > 0]
    avg_time = sum(valid_times) / len(valid_times) if valid_times else -1
    
    print(f"\n  Taux de succès: {success_rate:.0f}%")
    if avg_time > 0:
        print(f"  Temps moyen: {avg_time:.2f}ms")
    
    return success_rate == 100 and avg_time < 200


def test_indexes():
    """Vérifie que les indexes sont créés"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 4: INDEXES DE PERFORMANCE{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    try:
        print("Création/vérification des indexes...")
        _, elapsed = measure_time(create_performance_indexes)
        print(f"  {GREEN}✓ Indexes vérifiés en {elapsed:.2f}ms{RESET}")
        
        # Vérifier quelques indexes clés
        query = """
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            indexes = cursor.fetchall()
        
        print(f"\n  {len(indexes)} indexes trouvés:")
        
        # Grouper par table
        indexes_by_table = {}
        for idx in indexes:
            idx_name = idx[0]
            table_name = idx[1]
            if table_name not in indexes_by_table:
                indexes_by_table[table_name] = []
            indexes_by_table[table_name].append(idx_name)
        
        for table, idx_list in sorted(indexes_by_table.items()):
            print(f"    {table}: {len(idx_list)} index(es)")
        
        # Vérifier les indexes critiques
        critical_indexes = [
            'idx_users_email',
            'idx_paintings_status',
            'idx_orders_status',
            'idx_settings_key'
        ]
        
        all_idx_names = [idx[0] for idx in indexes]
        missing = [idx for idx in critical_indexes if idx not in all_idx_names]
        
        if not missing:
            print(f"\n  {GREEN}✓ Tous les indexes critiques sont présents{RESET}")
            return True
        else:
            print(f"\n  {RED}✗ Indexes critiques manquants: {', '.join(missing)}{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}✗ Erreur lors de la vérification des indexes: {e}{RESET}")
        return False


def test_concurrent_access():
    """Teste l'accès concurrent au pool"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 5: ACCÈS CONCURRENT{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    print("Simulation d'accès concurrents...")
    
    # Ouvrir plusieurs connexions simultanément
    connections = []
    times = []
    
    try:
        for i in range(5):
            conn, elapsed = measure_time(get_db)
            connections.append(conn)
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"  {len(connections)} connexions ouvertes simultanément")
        print(f"  Temps moyen: {avg_time:.2f}ms")
        print(f"  Temps max: {max_time:.2f}ms")
        
        # Fermer toutes les connexions
        for conn in connections:
            conn.close()
        
        if avg_time < 20:
            print(f"  {GREEN}✓ Excellent: Accès concurrent très rapide{RESET}")
            return True
        elif avg_time < 50:
            print(f"  {YELLOW}⚠ Acceptable: Accès concurrent modéré{RESET}")
            return True
        else:
            print(f"  {RED}✗ Lent: Accès concurrent trop lent{RESET}")
            return False
            
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        # Nettoyer les connexions en cas d'erreur
        for conn in connections:
            try:
                conn.close()
            except:
                pass
        return False


def run_all_tests():
    """Exécute tous les tests de performance de la DB"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TESTS DE PERFORMANCE - BASE DE DONNÉES SUPABASE/POSTGRES{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = {
        'Connection Pool': test_connection_pool(),
        'Requêtes simples': test_simple_queries(),
        'Requêtes complexes': test_complex_queries(),
        'Indexes': test_indexes(),
        'Accès concurrent': test_concurrent_access(),
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
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Certains tests ont échoué{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1
    
    # Fermer le pool à la fin
    close_connection_pool()


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
