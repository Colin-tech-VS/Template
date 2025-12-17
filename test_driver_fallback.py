"""
Test driver fallback scenarios by hiding drivers temporarily
Tests the fallback chain: psycopg3 → psycopg2 → pg8000
"""

import sys
import os
import importlib

# Colors for console
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def hide_module(module_name):
    """Temporarily hide a module from imports"""
    if module_name in sys.modules:
        return sys.modules.pop(module_name)
    return None


def restore_module(module_name, module_obj):
    """Restore a previously hidden module"""
    if module_obj is not None:
        sys.modules[module_name] = module_obj


def test_psycopg3_driver():
    """Test with psycopg3 available (normal scenario)"""
    print(f"\n{BLUE}TEST 1: Using psycopg3 (primary driver){RESET}")
    
    try:
        # Clear any cached database module
        if 'database' in sys.modules:
            del sys.modules['database']
        
        # Set dummy DATABASE_URL
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        
        # Import database (should use psycopg3)
        import database
        
        assert database.DRIVER == "psycopg3", f"Expected psycopg3, got {database.DRIVER}"
        assert database.USING_PSYCOPG3 == True, "USING_PSYCOPG3 should be True"
        
        print(f"  ✓ Driver detected: {GREEN}{database.DRIVER}{RESET}")
        print(f"  ✓ USING_PSYCOPG3 flag: {database.USING_PSYCOPG3}")
        print(f"  {GREEN}✓ psycopg3 driver working correctly{RESET}")
        
        return True
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False


def test_psycopg2_fallback():
    """Test fallback to psycopg2 when psycopg3 is not available"""
    print(f"\n{BLUE}TEST 2: Fallback to psycopg2 (when psycopg3 unavailable){RESET}")
    
    # Hide psycopg modules
    hidden_modules = {}
    modules_to_hide = ['psycopg', 'psycopg_pool', 'psycopg.rows']
    
    try:
        # Hide psycopg3
        for mod in modules_to_hide:
            hidden = hide_module(mod)
            if hidden:
                hidden_modules[mod] = hidden
        
        # Also hide from database module if it was imported
        if 'database' in sys.modules:
            del sys.modules['database']
        
        # Install psycopg2 if not present
        try:
            import psycopg2
            print(f"  ℹ️  psycopg2 is available for fallback test")
        except ImportError:
            print(f"  {YELLOW}⚠ psycopg2 not installed, skipping test{RESET}")
            return True  # Skip test, not an error
        
        # Block psycopg import by modifying sys.meta_path temporarily
        class BlockPsycopg3Import:
            def find_module(self, fullname, path=None):
                if fullname in ['psycopg', 'psycopg_pool']:
                    raise ImportError(f"Blocked for testing: {fullname}")
                return None
        
        blocker = BlockPsycopg3Import()
        sys.meta_path.insert(0, blocker)
        
        try:
            # Import database (should fallback to psycopg2)
            import database
            
            assert database.DRIVER == "psycopg2", f"Expected psycopg2, got {database.DRIVER}"
            assert database.USING_PSYCOPG3 == False, "USING_PSYCOPG3 should be False"
            
            print(f"  ✓ Driver detected: {GREEN}{database.DRIVER}{RESET}")
            print(f"  ✓ USING_PSYCOPG3 flag: {database.USING_PSYCOPG3}")
            print(f"  {GREEN}✓ psycopg2 fallback working correctly{RESET}")
            
            return True
        finally:
            sys.meta_path.remove(blocker)
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore hidden modules
        for mod, obj in hidden_modules.items():
            restore_module(mod, obj)


def test_pg8000_fallback():
    """Test fallback to pg8000 when neither psycopg3 nor psycopg2 are available"""
    print(f"\n{BLUE}TEST 3: Fallback to pg8000 (when psycopg3 and psycopg2 unavailable){RESET}")
    
    try:
        # Check if pg8000 is available
        try:
            import pg8000
            print(f"  ℹ️  pg8000 is available for fallback test")
        except ImportError:
            print(f"  {YELLOW}⚠ pg8000 not installed, skipping test{RESET}")
            return True  # Skip test, not an error
        
        # Clear database module and all psycopg modules
        modules_to_clear = ['database', 'psycopg', 'psycopg_pool', 'psycopg.rows', 
                           'psycopg2', 'psycopg2.extras', 'psycopg2.pool']
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Block psycopg and psycopg2 imports
        class BlockPsycopgImports:
            def find_spec(self, fullname, path, target=None):
                if fullname in ['psycopg', 'psycopg_pool', 'psycopg2', 'psycopg.rows']:
                    raise ImportError(f"Blocked for testing: {fullname}")
                return None
            
            def find_module(self, fullname, path=None):
                if fullname in ['psycopg', 'psycopg_pool', 'psycopg2', 'psycopg.rows']:
                    raise ImportError(f"Blocked for testing: {fullname}")
                return None
        
        blocker = BlockPsycopgImports()
        sys.meta_path.insert(0, blocker)
        
        try:
            # Import database (should fallback to pg8000)
            import database
            
            assert database.DRIVER == "pg8000", f"Expected pg8000, got {database.DRIVER}"
            assert database.USING_PSYCOPG3 == False, "USING_PSYCOPG3 should be False"
            
            print(f"  ✓ Driver detected: {GREEN}{database.DRIVER}{RESET}")
            print(f"  ✓ USING_PSYCOPG3 flag: {database.USING_PSYCOPG3}")
            print(f"  {GREEN}✓ pg8000 fallback working correctly{RESET}")
            
            return True
        finally:
            sys.meta_path.remove(blocker)
        
    except Exception as e:
        print(f"  {RED}✗ Error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up blocker from meta_path if it's still there
        if 'blocker' in locals():
            try:
                if blocker in sys.meta_path:
                    sys.meta_path.remove(blocker)
            except Exception:
                pass


def test_no_driver_error():
    """Test that appropriate error is raised when no driver is available"""
    print(f"\n{BLUE}TEST 4: Error when no driver is available{RESET}")
    
    try:
        # Clear database module and all driver modules
        modules_to_clear = ['database', 'psycopg', 'psycopg_pool', 'psycopg.rows',
                           'psycopg2', 'psycopg2.extras', 'psycopg2.pool',
                           'pg8000', 'pg8000.native', 'pg8000.dbapi']
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]
        
        # Block all driver imports
        class BlockAllDrivers:
            def find_spec(self, fullname, path, target=None):
                if fullname in ['psycopg', 'psycopg_pool', 'psycopg2', 'pg8000', 'psycopg.rows', 'pg8000.native', 'pg8000.dbapi']:
                    raise ImportError(f"Blocked for testing: {fullname}")
                return None
            
            def find_module(self, fullname, path=None):
                if fullname in ['psycopg', 'psycopg_pool', 'psycopg2', 'pg8000', 'psycopg.rows', 'pg8000.native', 'pg8000.dbapi']:
                    raise ImportError(f"Blocked for testing: {fullname}")
                return None
        
        blocker = BlockAllDrivers()
        sys.meta_path.insert(0, blocker)
        
        try:
            # This should raise ImportError
            import database
            print(f"  {RED}✗ Should have raised ImportError{RESET}")
            return False
        except ImportError as e:
            error_msg = str(e)
            assert "No PostgreSQL driver found" in error_msg, "Error message should mention no driver found"
            print(f"  ✓ Correct error raised: {error_msg}")
            print(f"  {GREEN}✓ Error handling working correctly{RESET}")
            return True
        finally:
            sys.meta_path.remove(blocker)
        
    except Exception as e:
        print(f"  {RED}✗ Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up blocker from meta_path if it's still there
        if 'blocker' in locals():
            try:
                if blocker in sys.meta_path:
                    sys.meta_path.remove(blocker)
            except Exception:
                pass


def run_all_tests():
    """Run all driver fallback tests"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}DRIVER FALLBACK TESTS{RESET}")
    print(f"{BLUE}Testing automatic fallback: psycopg3 → psycopg2 → pg8000{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    results = {
        'psycopg3 Driver': test_psycopg3_driver(),
        'psycopg2 Fallback': test_psycopg2_fallback(),
        'pg8000 Fallback': test_pg8000_fallback(),
        'No Driver Error': test_no_driver_error(),
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
        print(f"{GREEN}✓ All driver fallback tests passed!{RESET}")
        print(f"{GREEN}✓ Multi-driver compatibility is working correctly{RESET}")
        print(f"{GREEN}✓ Fallback chain: psycopg3 → psycopg2 → pg8000{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 0
    else:
        print(f"{RED}✗ Some tests failed{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")
        return 1


if __name__ == '__main__':
    try:
        # Set dummy DATABASE_URL for tests
        os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test'
        
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
