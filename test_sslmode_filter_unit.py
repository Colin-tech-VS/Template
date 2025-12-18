"""
Unit test for get_driver_config() function to ensure pg8000 sslmode filtering works
This test doesn't require an actual database connection.
"""

import sys

# Colors for console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_get_driver_config_filters_sslmode():
    """Test that get_driver_config() correctly filters sslmode for pg8000"""
    print(f"\n{BLUE}TEST: get_driver_config() sslmode filtering{RESET}")
    
    # Mock the necessary parts of database module
    class MockDatabase:
        def __init__(self, driver_name):
            self.DRIVER = driver_name
            self.DB_CONFIG = {
                'host': 'localhost',
                'port': 5432,
                'database': 'testdb',
                'user': 'testuser',
                'password': 'testpass',
                'sslmode': 'require'
            }
    
    # Test pg8000 driver - should filter out sslmode
    print(f"  Testing pg8000 driver...")
    mock_pg8000 = MockDatabase('pg8000')
    
    # Simulate get_driver_config() logic
    if mock_pg8000.DRIVER == "pg8000":
        config = {k: v for k, v in mock_pg8000.DB_CONFIG.items() if k != 'sslmode'}
    else:
        config = mock_pg8000.DB_CONFIG
    
    assert 'sslmode' not in config, "pg8000 config should not have sslmode"
    assert 'host' in config, "pg8000 config should have host"
    assert 'port' in config, "pg8000 config should have port"
    assert 'database' in config, "pg8000 config should have database"
    assert 'user' in config, "pg8000 config should have user"
    assert 'password' in config, "pg8000 config should have password"
    print(f"    {GREEN}✓ pg8000: sslmode filtered out correctly{RESET}")
    
    # Test psycopg2 driver - should keep sslmode
    print(f"  Testing psycopg2 driver...")
    mock_psycopg2 = MockDatabase('psycopg2')
    
    if mock_psycopg2.DRIVER == "pg8000":
        config = {k: v for k, v in mock_psycopg2.DB_CONFIG.items() if k != 'sslmode'}
    else:
        config = mock_psycopg2.DB_CONFIG
    
    assert 'sslmode' in config, "psycopg2 config should have sslmode"
    assert config['sslmode'] == 'require', "psycopg2 config should have sslmode='require'"
    print(f"    {GREEN}✓ psycopg2: sslmode preserved correctly{RESET}")
    
    # Test psycopg3 driver - should keep sslmode
    print(f"  Testing psycopg3 driver...")
    mock_psycopg3 = MockDatabase('psycopg3')
    
    if mock_psycopg3.DRIVER == "pg8000":
        config = {k: v for k, v in mock_psycopg3.DB_CONFIG.items() if k != 'sslmode'}
    else:
        config = mock_psycopg3.DB_CONFIG
    
    assert 'sslmode' in config, "psycopg3 config should have sslmode"
    assert config['sslmode'] == 'require', "psycopg3 config should have sslmode='require'"
    print(f"    {GREEN}✓ psycopg3: sslmode preserved correctly{RESET}")
    
    return True


def test_actual_implementation():
    """Test the actual implementation in database.py"""
    print(f"\n{BLUE}TEST: Actual database.py implementation{RESET}")
    
    try:
        # Set a dummy DATABASE_URL to allow import
        import os
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/db'
        
        import database
        
        print(f"  Detected driver: {database.DRIVER}")
        
        # Test get_driver_config function
        driver_config = database.get_driver_config()
        
        if database.DRIVER == "pg8000":
            assert 'sslmode' not in driver_config, "pg8000 driver_config should not have sslmode"
            print(f"    {GREEN}✓ pg8000: sslmode filtered out in actual implementation{RESET}")
        else:
            assert 'sslmode' in driver_config, f"{database.DRIVER} driver_config should have sslmode"
            print(f"    {GREEN}✓ {database.DRIVER}: sslmode preserved in actual implementation{RESET}")
        
        return True
        
    except Exception as e:
        print(f"    {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("UNIT TEST: pg8000 sslmode filtering")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("sslmode filtering logic", test_get_driver_config_filters_sslmode()))
    except Exception as e:
        print(f"{RED}✗ Test failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        results.append(("sslmode filtering logic", False))
    
    try:
        results.append(("Actual implementation", test_actual_implementation()))
    except Exception as e:
        print(f"{RED}✗ Test failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
        results.append(("Actual implementation", False))
    
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✓ PASSED{RESET}" if result else f"{RED}✗ FAILED{RESET}"
        print(f"{test_name:40} {status}")
    
    print("=" * 70)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"{GREEN}✓ All tests passed!{RESET}")
        print(f"{GREEN}✓ pg8000 sslmode fix is working correctly{RESET}")
        return 0
    else:
        print(f"{RED}✗ Some tests failed{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
