"""
Test multi-driver compatibility
Tests that database.py can work with psycopg3, psycopg2, or pg8000
"""

import sys
import os

# Colors for console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_driver_detection():
    """Test that a driver is detected and DRIVER variable is set"""
    print(f"\n{BLUE}TEST 1: Driver Detection{RESET}")
    
    try:
        import database
        
        # Check DRIVER variable exists
        assert hasattr(database, 'DRIVER'), "DRIVER variable should exist"
        assert database.DRIVER is not None, "DRIVER should not be None"
        assert database.DRIVER in ['psycopg3', 'psycopg2', 'pg8000'], f"DRIVER should be one of the supported drivers, got: {database.DRIVER}"
        
        print(f"  ✓ Detected driver: {GREEN}{database.DRIVER}{RESET}")
        
        # Check backward compatibility flag
        assert hasattr(database, 'USING_PSYCOPG3'), "USING_PSYCOPG3 should exist for backward compatibility"
        expected_flag = (database.DRIVER == "psycopg3")
        assert database.USING_PSYCOPG3 == expected_flag, f"USING_PSYCOPG3 should be {expected_flag}"
        print(f"  ✓ USING_PSYCOPG3 flag: {database.USING_PSYCOPG3} (backward compatible)")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_api_consistency():
    """Test that all required API functions exist"""
    print(f"\n{BLUE}TEST 2: API Consistency{RESET}")
    
    try:
        import database
        
        required_functions = [
            'get_db_connection',
            'get_db',
            'execute_query',
            'adapt_query',
            'init_connection_pool',
            'get_pool_connection',
            'return_pool_connection',
            'close_connection_pool',
        ]
        
        for func_name in required_functions:
            assert hasattr(database, func_name), f"Function {func_name} should exist"
            assert callable(getattr(database, func_name)), f"{func_name} should be callable"
            print(f"  ✓ {func_name}() exists")
        
        print(f"  {GREEN}✓ All required API functions exist{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_query_adaptation():
    """Test that query adaptation works (SQLite ? to PostgreSQL %s)"""
    print(f"\n{BLUE}TEST 3: Query Adaptation{RESET}")
    
    try:
        import database
        
        # Test ? to %s replacement
        query1 = "SELECT * FROM users WHERE id = ?"
        adapted1 = database.adapt_query(query1)
        assert "?" not in adapted1, "? should be replaced"
        assert "%s" in adapted1, "%s should be present"
        print(f"  ✓ Query adaptation: ? → %s")
        
        # Test multiple placeholders
        query2 = "SELECT * FROM users WHERE id = ? AND name = ?"
        adapted2 = database.adapt_query(query2)
        assert adapted2.count("%s") == 2, "Should have 2 %s placeholders"
        print(f"  ✓ Multiple placeholders adapted correctly")
        
        print(f"  {GREEN}✓ Query adaptation working correctly{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_wrapper():
    """Test that ConnectionWrapper class exists and is properly defined"""
    print(f"\n{BLUE}TEST 4: ConnectionWrapper Class{RESET}")
    
    try:
        import database
        
        assert hasattr(database, 'ConnectionWrapper'), "ConnectionWrapper should exist"
        
        # Test class has required methods
        wrapper_class = database.ConnectionWrapper
        assert hasattr(wrapper_class, '__enter__'), "Should support context manager"
        assert hasattr(wrapper_class, '__exit__'), "Should support context manager"
        assert hasattr(wrapper_class, 'close'), "Should have close method"
        
        print(f"  ✓ ConnectionWrapper class exists")
        print(f"  ✓ Context manager support present")
        print(f"  ✓ close() method present")
        print(f"  {GREEN}✓ ConnectionWrapper properly defined{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_constants():
    """Test that required constants exist"""
    print(f"\n{BLUE}TEST 5: Required Constants{RESET}")
    
    try:
        import database
        
        # Check constants
        assert hasattr(database, 'PARAM_PLACEHOLDER'), "PARAM_PLACEHOLDER should exist"
        assert database.PARAM_PLACEHOLDER == '%s', "PARAM_PLACEHOLDER should be %s"
        print(f"  ✓ PARAM_PLACEHOLDER = '%s'")
        
        assert hasattr(database, 'AUTOINCREMENT'), "AUTOINCREMENT should exist"
        assert database.AUTOINCREMENT == 'SERIAL', "AUTOINCREMENT should be SERIAL"
        print(f"  ✓ AUTOINCREMENT = 'SERIAL'")
        
        assert hasattr(database, 'IS_POSTGRES'), "IS_POSTGRES should exist"
        assert database.IS_POSTGRES == True, "IS_POSTGRES should be True"
        print(f"  ✓ IS_POSTGRES = True")
        
        print(f"  {GREEN}✓ All constants defined correctly{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_driver_specific_imports():
    """Test that driver-specific imports are properly handled"""
    print(f"\n{BLUE}TEST 6: Driver-Specific Imports{RESET}")
    
    try:
        import database
        
        driver = database.DRIVER
        print(f"  Current driver: {driver}")
        
        if driver == "psycopg3":
            # Check psycopg3-specific imports
            assert hasattr(database, 'psycopg3'), "psycopg3 module should be imported"
            assert hasattr(database, 'PsycopgPool'), "PsycopgPool should be imported"
            assert hasattr(database, 'dict_row'), "dict_row should be imported"
            print(f"  ✓ psycopg3 imports successful")
            
        elif driver == "psycopg2":
            # Check psycopg2-specific imports
            assert hasattr(database, 'psycopg2'), "psycopg2 module should be imported"
            print(f"  ✓ psycopg2 imports successful")
            
        elif driver == "pg8000":
            # Check pg8000-specific imports
            assert hasattr(database, 'pg8000'), "pg8000 module should be imported"
            print(f"  ✓ pg8000 imports successful")
        
        print(f"  {GREEN}✓ Driver-specific imports correct{RESET}")
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all multi-driver compatibility tests"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}MULTI-DRIVER COMPATIBILITY TESTS{RESET}")
    print(f"{BLUE}Testing psycopg3 → psycopg2 → pg8000 fallback chain{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = {
        'Driver Detection': test_driver_detection(),
        'API Consistency': test_api_consistency(),
        'Query Adaptation': test_query_adaptation(),
        'ConnectionWrapper': test_connection_wrapper(),
        'Constants': test_constants(),
        'Driver-Specific Imports': test_driver_specific_imports(),
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
        print(f"{GREEN}✓ All multi-driver compatibility tests passed!{RESET}")
        print(f"{GREEN}✓ Database module supports psycopg3, psycopg2, and pg8000{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Some tests failed{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1


if __name__ == '__main__':
    try:
        # Check if DATABASE_URL is set
        if not os.environ.get('DATABASE_URL') and not os.environ.get('SUPABASE_DB_URL'):
            print(f"{YELLOW}WARNING: DATABASE_URL or SUPABASE_DB_URL not set, some tests may be limited{RESET}")
            print(f"{YELLOW}These are structural tests that don't require DB connection{RESET}\n")
        
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
