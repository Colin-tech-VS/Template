"""
Simple validation test for multi-driver compatibility
Verifies the code structure and logic without trying to block imports
"""

import sys
import os

# Colors for console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Set dummy DATABASE_URL
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'

def test_driver_variable():
    """Test that DRIVER variable is properly set"""
    print(f"\n{BLUE}TEST 1: DRIVER variable{RESET}")
    
    try:
        import database
        
        assert hasattr(database, 'DRIVER'), "DRIVER variable must exist"
        assert database.DRIVER is not None, "DRIVER must not be None"
        assert database.DRIVER in ['psycopg3', 'psycopg2', 'pg8000'], \
            f"DRIVER must be one of the supported drivers, got: {database.DRIVER}"
        
        print(f"  ✓ DRIVER variable exists: {GREEN}{database.DRIVER}{RESET}")
        print(f"  {GREEN}✓ DRIVER properly set{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that USING_PSYCOPG3 flag is set for backward compatibility"""
    print(f"\n{BLUE}TEST 2: Backward compatibility flag{RESET}")
    
    try:
        import database
        
        assert hasattr(database, 'USING_PSYCOPG3'), "USING_PSYCOPG3 must exist"
        expected = (database.DRIVER == 'psycopg3')
        assert database.USING_PSYCOPG3 == expected, \
            f"USING_PSYCOPG3 should be {expected}, got {database.USING_PSYCOPG3}"
        
        print(f"  ✓ USING_PSYCOPG3 flag: {database.USING_PSYCOPG3}")
        print(f"  ✓ Matches DRIVER: {database.DRIVER == 'psycopg3'}")
        print(f"  {GREEN}✓ Backward compatibility maintained{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_driver_specific_code():
    """Test that driver-specific code branches exist"""
    print(f"\n{BLUE}TEST 3: Driver-specific code branches{RESET}")
    
    try:
        import database
        import inspect
        
        # Check init_connection_pool has branches for all drivers
        source = inspect.getsource(database.init_connection_pool)
        assert 'DRIVER == "psycopg3"' in source or 'if DRIVER == "psycopg3"' in source, \
            "init_connection_pool must check for psycopg3"
        assert 'DRIVER == "psycopg2"' in source or 'elif DRIVER == "psycopg2"' in source, \
            "init_connection_pool must check for psycopg2"
        assert 'DRIVER == "pg8000"' in source or 'elif DRIVER == "pg8000"' in source, \
            "init_connection_pool must check for pg8000"
        print(f"  ✓ init_connection_pool has branches for all drivers")
        
        # Check get_db_connection has branches for all drivers
        source = inspect.getsource(database.get_db_connection)
        assert 'DRIVER == "psycopg3"' in source or 'if DRIVER == "psycopg3"' in source, \
            "get_db_connection must check for psycopg3"
        assert 'DRIVER == "psycopg2"' in source or 'elif DRIVER == "psycopg2"' in source, \
            "get_db_connection must check for psycopg2"
        assert 'DRIVER == "pg8000"' in source or 'elif DRIVER == "pg8000"' in source, \
            "get_db_connection must check for pg8000"
        print(f"  ✓ get_db_connection has branches for all drivers")
        
        # Check get_db has branches for all drivers
        source = inspect.getsource(database.get_db)
        assert 'DRIVER == "psycopg3"' in source or 'if DRIVER == "psycopg3"' in source, \
            "get_db must check for psycopg3"
        assert 'DRIVER == "psycopg2"' in source or 'elif DRIVER == "psycopg2"' in source, \
            "get_db must check for psycopg2"
        assert 'DRIVER == "pg8000"' in source or 'elif DRIVER == "pg8000"' in source, \
            "get_db must check for pg8000"
        print(f"  ✓ get_db has branches for all drivers")
        
        print(f"  {GREEN}✓ All driver-specific code branches present{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_api():
    """Test that unified API functions exist"""
    print(f"\n{BLUE}TEST 4: Unified API{RESET}")
    
    try:
        import database
        
        # Test required functions
        required = ['get_db_connection', 'get_db', 'execute_query', 
                   'init_connection_pool', 'close_connection_pool']
        
        for func in required:
            assert hasattr(database, func), f"Function {func} must exist"
            assert callable(getattr(database, func)), f"{func} must be callable"
            print(f"  ✓ {func}() exists and is callable")
        
        print(f"  {GREEN}✓ Unified API complete{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_placeholder_conversion():
    """Test that SQLite placeholders are converted to PostgreSQL format"""
    print(f"\n{BLUE}TEST 5: Placeholder conversion{RESET}")
    
    try:
        import database
        
        # Test single placeholder
        query1 = "SELECT * FROM users WHERE id = ?"
        adapted1 = database.adapt_query(query1)
        assert "%s" in adapted1 and "?" not in adapted1, \
            f"Query should have %s not ?, got: {adapted1}"
        print(f"  ✓ Single ? → %s")
        
        # Test multiple placeholders
        query2 = "SELECT * FROM users WHERE id = ? AND name = ?"
        adapted2 = database.adapt_query(query2)
        assert adapted2.count("%s") == 2 and "?" not in adapted2, \
            f"Query should have 2x %s not ?, got: {adapted2}"
        print(f"  ✓ Multiple ? → %s")
        
        # Test PARAM_PLACEHOLDER constant
        assert database.PARAM_PLACEHOLDER == '%s', \
            f"PARAM_PLACEHOLDER should be %s, got: {database.PARAM_PLACEHOLDER}"
        print(f"  ✓ PARAM_PLACEHOLDER = '%s'")
        
        print(f"  {GREEN}✓ Placeholder conversion working{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_wrapper():
    """Test that ConnectionWrapper exists and has required methods"""
    print(f"\n{BLUE}TEST 6: ConnectionWrapper{RESET}")
    
    try:
        import database
        
        assert hasattr(database, 'ConnectionWrapper'), "ConnectionWrapper class must exist"
        wrapper_class = database.ConnectionWrapper
        
        # Check context manager support
        assert hasattr(wrapper_class, '__enter__'), "Must support context manager (__enter__)"
        assert hasattr(wrapper_class, '__exit__'), "Must support context manager (__exit__)"
        print(f"  ✓ Context manager support")
        
        # Check close method
        assert hasattr(wrapper_class, 'close'), "Must have close() method"
        print(f"  ✓ close() method exists")
        
        # Check property
        assert hasattr(wrapper_class, 'closed'), "Must have closed property"
        print(f"  ✓ closed property exists")
        
        print(f"  {GREEN}✓ ConnectionWrapper properly defined{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_import_logic():
    """Test that import logic tries drivers in correct order"""
    print(f"\n{BLUE}TEST 7: Import logic order{RESET}")
    
    try:
        # Read database.py source to verify import order
        with open('database.py', 'r') as f:
            source = f.read()
        
        # Find positions of driver imports
        psycopg3_pos = source.find('import psycopg as psycopg3')
        psycopg2_pos = source.find('import psycopg2')
        pg8000_pos = source.find('import pg8000')
        
        assert psycopg3_pos < psycopg2_pos, "psycopg3 must be tried before psycopg2"
        assert psycopg2_pos < pg8000_pos, "psycopg2 must be tried before pg8000"
        
        print(f"  ✓ Import order: psycopg3 → psycopg2 → pg8000")
        
        # Check that DRIVER is set after each successful import
        assert 'DRIVER = "psycopg3"' in source, "Must set DRIVER to psycopg3"
        assert 'DRIVER = "psycopg2"' in source, "Must set DRIVER to psycopg2"
        assert 'DRIVER = "pg8000"' in source, "Must set DRIVER to pg8000"
        print(f"  ✓ DRIVER set correctly for each driver")
        
        # Check error message when no driver found
        assert 'No PostgreSQL driver found' in source, "Must have error message for no driver"
        print(f"  ✓ Error message present")
        
        print(f"  {GREEN}✓ Import logic correct{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all validation tests"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}MULTI-DRIVER VALIDATION TESTS{RESET}")
    print(f"{BLUE}Validating code structure for psycopg3 → psycopg2 → pg8000{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = {
        'DRIVER Variable': test_driver_variable(),
        'Backward Compatibility': test_backward_compatibility(),
        'Driver-Specific Code': test_driver_specific_code(),
        'Unified API': test_unified_api(),
        'Placeholder Conversion': test_placeholder_conversion(),
        'ConnectionWrapper': test_connection_wrapper(),
        'Import Logic': test_import_logic(),
    }
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    for test_name, passed in results.items():
        symbol = f"{GREEN}✓{RESET}" if passed else f"{RED}✗{RESET}"
        status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
        print(f"  {symbol} {test_name:30s} {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"{GREEN}✓ All validation tests passed!{RESET}")
        print(f"{GREEN}✓ Multi-driver compatibility properly implemented{RESET}")
        print(f"{GREEN}✓ Code structure supports: psycopg3, psycopg2, pg8000{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Some tests failed{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1


if __name__ == '__main__':
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Error during tests: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
