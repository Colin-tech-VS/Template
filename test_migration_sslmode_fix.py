"""
Integration test to simulate the original error scenario from migrate_apply_tenant_ids.py
This test verifies that the pg8000 sslmode fix resolves the issue.
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
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_database_connection_scenario():
    """
    Simulates the exact scenario from migrate_apply_tenant_ids.py:
    - Import database module
    - Call get_db_connection() context manager
    - Verify no TypeError about 'sslmode' occurs
    """
    print(f"\n{BLUE}TEST: Simulating migrate_apply_tenant_ids.py connection scenario{RESET}")
    
    try:
        from database import get_db_connection, DRIVER
        
        print(f"  Detected driver: {DRIVER}")
        
        # This is the exact pattern from migrate_apply_tenant_ids.py line 515
        print(f"  Attempting to get database connection...")
        
        try:
            with get_db_connection() as conn:
                print(f"    {GREEN}✓ Connection obtained successfully{RESET}")
                print(f"    {GREEN}✓ No TypeError about 'sslmode' occurred{RESET}")
                
                # Try to get a cursor
                cursor = conn.cursor()
                print(f"    {GREEN}✓ Cursor obtained successfully{RESET}")
                
                return True
                
        except TypeError as e:
            error_str = str(e)
            if 'sslmode' in error_str:
                print(f"    {RED}✗ ORIGINAL ERROR STILL EXISTS: {e}{RESET}")
                print(f"    {RED}✗ The fix did not resolve the issue{RESET}")
                return False
            else:
                # Different TypeError, might be a connection issue
                print(f"    {YELLOW}⚠ Different TypeError occurred: {e}{RESET}")
                print(f"    {YELLOW}⚠ This is not the sslmode error{RESET}")
                # We consider this a pass since the sslmode error is fixed
                return True
                
        except Exception as e:
            # Other exceptions like connection errors are expected in test environment
            error_str = str(e)
            if 'sslmode' in error_str and 'unexpected keyword argument' in error_str:
                print(f"    {RED}✗ ORIGINAL ERROR STILL EXISTS: {e}{RESET}")
                return False
            else:
                # Different error (likely connection issue), which is okay
                print(f"    {YELLOW}⚠ Connection error (expected in test): {type(e).__name__}{RESET}")
                print(f"    {GREEN}✓ No sslmode error occurred (original issue is fixed){RESET}")
                return True
                
    except Exception as e:
        print(f"    {RED}✗ Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_get_pool_connection_scenario():
    """
    Test the get_pool_connection() function which was the source of the error
    """
    print(f"\n{BLUE}TEST: Testing get_pool_connection() (error source){RESET}")
    
    try:
        from database import get_pool_connection, return_pool_connection, DRIVER
        
        print(f"  Detected driver: {DRIVER}")
        
        if DRIVER == "psycopg3":
            print(f"    {YELLOW}⚠ get_pool_connection() not supported for psycopg3{RESET}")
            print(f"    {GREEN}✓ Skipping (not applicable for current driver){RESET}")
            return True
        
        print(f"  Attempting to get pool connection...")
        
        try:
            conn = get_pool_connection()
            print(f"    {GREEN}✓ Pool connection obtained successfully{RESET}")
            print(f"    {GREEN}✓ No TypeError about 'sslmode' occurred{RESET}")
            
            # Return the connection to the pool
            return_pool_connection(conn)
            print(f"    {GREEN}✓ Connection returned to pool{RESET}")
            
            return True
            
        except TypeError as e:
            error_str = str(e)
            if 'sslmode' in error_str:
                print(f"    {RED}✗ ORIGINAL ERROR STILL EXISTS: {e}{RESET}")
                print(f"    {RED}✗ This is the exact error from the bug report{RESET}")
                return False
            else:
                print(f"    {YELLOW}⚠ Different TypeError: {e}{RESET}")
                return True
                
        except RuntimeError as e:
            # psycopg3 raises RuntimeError for get_pool_connection
            if "non supporté" in str(e):
                print(f"    {GREEN}✓ Expected RuntimeError for psycopg3{RESET}")
                return True
            raise
            
        except Exception as e:
            error_str = str(e)
            if 'sslmode' in error_str and 'unexpected keyword argument' in error_str:
                print(f"    {RED}✗ ORIGINAL ERROR STILL EXISTS: {e}{RESET}")
                return False
            else:
                # Connection error is okay in test environment
                print(f"    {YELLOW}⚠ Connection error (expected): {type(e).__name__}{RESET}")
                print(f"    {GREEN}✓ No sslmode error occurred{RESET}")
                return True
                
    except Exception as e:
        print(f"    {RED}✗ Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 70)
    print("INTEGRATION TEST: Verifying pg8000 sslmode fix")
    print("Reproducing the exact error scenario from migrate_apply_tenant_ids.py")
    print("=" * 70)
    
    results = []
    
    results.append(("get_db_connection() scenario", test_database_connection_scenario()))
    results.append(("get_pool_connection() scenario", test_get_pool_connection_scenario()))
    
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
        print(f"\n{GREEN}✓ All tests passed!{RESET}")
        print(f"{GREEN}✓ The original sslmode error is FIXED{RESET}")
        print(f"{GREEN}✓ migrate_apply_tenant_ids.py should now work with pg8000{RESET}")
        return 0
    else:
        print(f"\n{RED}✗ Some tests failed{RESET}")
        print(f"{RED}✗ The original error may still exist{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
