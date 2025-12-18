"""
Test that pg8000 driver works without sslmode parameter error
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Colors for console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_driver_config_filter():
    """Test that get_driver_config() filters sslmode for pg8000"""
    print(f"\n{BLUE}TEST 1: Driver Config Filter{RESET}")
    
    try:
        import database
        
        # Get the driver-specific config
        driver_config = database.get_driver_config()
        
        print(f"  Current driver: {database.DRIVER}")
        print(f"  Original DB_CONFIG has 'sslmode': {'sslmode' in database.DB_CONFIG}")
        print(f"  Driver config has 'sslmode': {'sslmode' in driver_config}")
        
        if database.DRIVER == "pg8000":
            # For pg8000, sslmode should be filtered out
            assert 'sslmode' not in driver_config, "pg8000 config should not have sslmode"
            print(f"  {GREEN}✓ sslmode correctly filtered for pg8000{RESET}")
        else:
            # For psycopg2/psycopg3, sslmode should be present
            assert 'sslmode' in driver_config, f"{database.DRIVER} config should have sslmode"
            print(f"  {GREEN}✓ sslmode correctly preserved for {database.DRIVER}{RESET}")
        
        # All configs should have the basic parameters
        required_params = ['host', 'port', 'database', 'user', 'password']
        for param in required_params:
            assert param in driver_config, f"Config should have {param}"
        print(f"  {GREEN}✓ All required parameters present{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_creation():
    """Test that we can create a connection without sslmode error"""
    print(f"\n{BLUE}TEST 2: Connection Creation{RESET}")
    
    try:
        import database
        
        # Initialize the connection pool
        database.init_connection_pool(minconn=1, maxconn=2)
        
        # If we're using pg8000, test that we can create a connection
        if database.DRIVER == "pg8000":
            print(f"  Testing pg8000 connection...")
            # The get_pool_connection should not raise sslmode error
            try:
                conn = database.get_pool_connection()
                print(f"  {GREEN}✓ pg8000 connection created successfully (no sslmode error){RESET}")
                database.return_pool_connection(conn)
                return True
            except TypeError as e:
                if 'sslmode' in str(e):
                    print(f"  {RED}✗ sslmode error still present: {e}{RESET}")
                    return False
                else:
                    # Different error, might be connection issue
                    print(f"  {RED}⚠ Connection error (not sslmode): {e}{RESET}")
                    return False
        else:
            print(f"  Skipping pg8000 specific test (using {database.DRIVER})")
            return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("PG8000 SSLMODE FIX VERIFICATION")
    print("Testing that pg8000 driver works without sslmode parameter error")
    print("=" * 70)
    
    results = []
    
    results.append(("Driver Config Filter", test_driver_config_filter()))
    results.append(("Connection Creation", test_connection_creation()))
    
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
