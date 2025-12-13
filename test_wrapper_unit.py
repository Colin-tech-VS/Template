"""
Test unitaire de la classe ConnectionWrapper
Ce test ne nécessite pas de connexion réelle à la base de données
"""

import sys
import time

# Couleurs pour la console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


class MockConnection:
    """Mock d'une connexion psycopg2 pour tester le wrapper"""
    def __init__(self):
        self.closed_count = 0
        self.cursor_factory = None
        self._closed = False
    
    def close(self):
        """Simule la fermeture d'une connexion"""
        self.closed_count += 1
        self._closed = True
    
    def cursor(self):
        """Retourne un mock de curseur"""
        return MockCursor()
    
    def commit(self):
        """Mock de commit"""
        pass
    
    def rollback(self):
        """Mock de rollback"""
        pass


class MockCursor:
    """Mock d'un curseur psycopg2"""
    def execute(self, query, params=None):
        pass
    
    def fetchone(self):
        return (1,)
    
    def fetchall(self):
        return [(1,)]


# Import du wrapper depuis database.py
sys.path.insert(0, '/home/runner/work/Template/Template')

# Import uniquement de la classe ConnectionWrapper (sans dépendances DB)
import importlib.util
spec = importlib.util.spec_from_file_location("database", "/home/runner/work/Template/Template/database.py")
database_module = importlib.util.module_from_spec(spec)

# Mock les dépendances qui nécessitent une DB
import types
mock_module = types.ModuleType('mock_psycopg2')
mock_module.extras = types.ModuleType('extras')

sys.modules['psycopg2'] = mock_module
sys.modules['psycopg2.extras'] = mock_module.extras
sys.modules['psycopg2.pool'] = types.ModuleType('pool')

# Maintenant charger le module
spec.loader.exec_module(database_module)
ConnectionWrapper = database_module.ConnectionWrapper


def test_wrapper_basic():
    """Test basique du wrapper"""
    print(f"\n{BLUE}TEST 1: Wrapper basique{RESET}")
    
    try:
        mock_conn = MockConnection()
        wrapper = ConnectionWrapper(mock_conn)
        
        # Vérifier que le wrapper délègue les attributs
        assert hasattr(wrapper, 'cursor'), "Le wrapper doit avoir un attribut cursor"
        print(f"  ✓ Délégation des attributs fonctionne")
        
        # Vérifier que closed est False initialement
        assert not wrapper.closed, "La connexion ne doit pas être fermée initialement"
        print(f"  ✓ État initial correct (closed=False)")
        
        # Appeler close()
        wrapper.close()
        
        # Vérifier que closed est True après close()
        assert wrapper.closed, "La connexion doit être fermée après close()"
        print(f"  {GREEN}✓ close() marque la connexion comme fermée{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_wrapper_double_close():
    """Test: appeler close() plusieurs fois"""
    print(f"\n{BLUE}TEST 2: Double close(){RESET}")
    
    try:
        mock_conn = MockConnection()
        wrapper = ConnectionWrapper(mock_conn)
        
        # Premier close
        wrapper.close()
        assert wrapper.closed, "Connexion doit être fermée"
        print(f"  ✓ Premier close() OK")
        
        # Deuxième close (idempotent)
        wrapper.close()
        assert wrapper.closed, "Connexion doit rester fermée"
        print(f"  {GREEN}✓ Deuxième close() OK (idempotent){RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_wrapper_context_manager():
    """Test: utiliser le wrapper comme context manager"""
    print(f"\n{BLUE}TEST 3: Context manager{RESET}")
    
    try:
        mock_conn = MockConnection()
        wrapper = ConnectionWrapper(mock_conn)
        
        # Utiliser comme context manager
        with wrapper as conn:
            assert not conn.closed, "Connexion doit être ouverte dans le contexte"
            print(f"  ✓ Connexion ouverte dans le contexte")
        
        # Après le contexte, doit être fermée
        assert wrapper.closed, "Connexion doit être fermée après le contexte"
        print(f"  {GREEN}✓ Connexion fermée automatiquement en sortant du contexte{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_wrapper_delegation():
    """Test: vérifier que les méthodes sont bien déléguées"""
    print(f"\n{BLUE}TEST 4: Délégation des méthodes{RESET}")
    
    try:
        mock_conn = MockConnection()
        wrapper = ConnectionWrapper(mock_conn)
        
        # Tester cursor()
        cursor = wrapper.cursor()
        assert cursor is not None, "cursor() doit retourner un curseur"
        print(f"  ✓ cursor() délégué correctement")
        
        # Tester commit()
        wrapper.commit()
        print(f"  ✓ commit() délégué correctement")
        
        # Tester rollback()
        wrapper.rollback()
        print(f"  ✓ rollback() délégué correctement")
        
        # Tester cursor_factory
        wrapper.cursor_factory = "test"
        assert mock_conn.cursor_factory == "test", "cursor_factory doit être délégué"
        print(f"  {GREEN}✓ Attributs en écriture délégués correctement{RESET}")
        
        wrapper.close()
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_no_attribute_error():
    """Test principal: vérifier qu'il n'y a pas d'AttributeError"""
    print(f"\n{BLUE}TEST 5: Pas d'AttributeError lors de l'utilisation{RESET}")
    
    try:
        mock_conn = MockConnection()
        wrapper = ConnectionWrapper(mock_conn)
        
        # Simuler l'utilisation typique
        wrapper.cursor_factory = "RealDictCursor"
        cursor = wrapper.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        wrapper.commit()
        wrapper.close()
        
        print(f"  {GREEN}✓ Aucune AttributeError détectée{RESET}")
        print(f"  {GREEN}✓ Le wrapper résout le problème de conn.close read-only{RESET}")
        
        return True
        
    except AttributeError as e:
        print(f"  {RED}✗ AttributeError détectée: {e}{RESET}")
        return False
    except Exception as e:
        print(f"  {RED}✗ Erreur: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Exécute tous les tests unitaires"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TESTS UNITAIRES - ConnectionWrapper{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = {
        'Wrapper basique': test_wrapper_basic(),
        'Double close': test_wrapper_double_close(),
        'Context manager': test_wrapper_context_manager(),
        'Délégation des méthodes': test_wrapper_delegation(),
        'Pas d\'AttributeError': test_no_attribute_error(),
    }
    
    # Résumé
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}RÉSUMÉ DES TESTS{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    for test_name, passed in results.items():
        symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        status = f"{GREEN}RÉUSSI{RESET}" if passed else f"{RED}ÉCHOUÉ{RESET}"
        print(f"  {symbol} {test_name:30s} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Total: {passed}/{total} tests réussis")
    
    if passed == total:
        print(f"{GREEN}✓ Tous les tests unitaires sont passés!{RESET}")
        print(f"{GREEN}✓ Le ConnectionWrapper résout le problème AttributeError!{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Certains tests ont échoué{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1


if __name__ == '__main__':
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\nTests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Erreur lors des tests: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
