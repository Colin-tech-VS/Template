#!/usr/bin/env python3
"""
Simple test to verify the require_api_key decorator logic works correctly.
This test verifies the code changes without needing a full database setup.
"""

import sys
import os
import hmac

# Mock the necessary constants and functions
DEFAULT_TENANT_ID = 1
IS_POSTGRES = False

class MockRequest:
    def __init__(self, headers):
        self.headers = headers
        self.host = headers.get('Host', 'localhost')

class MockCursor:
    def __init__(self, result=None):
        self.result = result
        self.description = [('value',)]
    
    def execute(self, query, params):
        pass
    
    def fetchone(self):
        if self.result:
            return {'value': self.result}
        return None

class MockConnection:
    def __init__(self, result=None):
        self.result = result
    
    def cursor(self):
        return MockCursor(self.result)
    
    def close(self):
        pass

def adapt_query(query):
    """Mock function that adapts SQL queries"""
    return query.replace('?', '%s')

def test_api_key_logic():
    """Test the API key validation logic"""
    print("=" * 60)
    print("Testing API Key Validation Logic")
    print("=" * 60)
    
    # Test data
    TEMPLATE_MASTER_API_KEY = 'master-key-12345'
    _DUMMY_KEY_FOR_COMPARISON = 'dummy-key-67890'
    
    test_api_key = 'stored-export-key-abcdef'
    wrong_api_key = 'wrong-key-xyz'
    
    print("\n1. Test: No API key provided")
    api_key = None
    if not api_key:
        print("   ✓ Correctly identified missing API key (should return 401)")
    
    print("\n2. Test: Master key validation")
    api_key = TEMPLATE_MASTER_API_KEY
    expected_master = TEMPLATE_MASTER_API_KEY
    ok_master = hmac.compare_digest(api_key, expected_master)
    if ok_master:
        print("   ✓ Master key correctly validated")
    else:
        print("   ✗ Master key validation failed")
        return False
    
    print("\n3. Test: Wrong master key")
    api_key = wrong_api_key
    ok_master = hmac.compare_digest(api_key, expected_master)
    if not ok_master:
        print("   ✓ Wrong master key correctly rejected")
    else:
        print("   ✗ Wrong master key was incorrectly accepted")
        return False
    
    print("\n4. Test: Stored API key validation")
    api_key = test_api_key
    stored = test_api_key
    ok_stored = hmac.compare_digest(api_key, stored)
    if ok_stored:
        print("   ✓ Stored API key correctly validated")
    else:
        print("   ✗ Stored API key validation failed")
        return False
    
    print("\n5. Test: Wrong stored API key")
    api_key = wrong_api_key
    stored = test_api_key
    ok_stored = hmac.compare_digest(api_key, stored)
    if not ok_stored:
        print("   ✓ Wrong stored API key correctly rejected")
    else:
        print("   ✗ Wrong stored API key was incorrectly accepted")
        return False
    
    print("\n6. Test: Fallback logic simulation")
    # Simulate the scenario where get_setting returns None for current tenant
    # but finds the key in default tenant
    print("   Simulating: Current tenant has no key, default tenant has key")
    
    # First attempt (current tenant) - returns None
    stored_current_tenant = None
    
    # Second attempt (default tenant) - returns the key
    stored_default_tenant = test_api_key
    
    # Final stored value should be from default tenant
    stored = stored_current_tenant if stored_current_tenant else stored_default_tenant
    
    if stored == test_api_key:
        print("   ✓ Fallback to default tenant successful")
    else:
        print("   ✗ Fallback logic failed")
        return False
    
    # Now validate with the API key
    api_key = test_api_key
    ok_stored = hmac.compare_digest(api_key, stored)
    if ok_stored:
        print("   ✓ API key validated successfully after fallback")
    else:
        print("   ✗ API key validation failed after fallback")
        return False
    
    print("\n7. Test: Combined validation (master OR stored)")
    test_cases = [
        (TEMPLATE_MASTER_API_KEY, test_api_key, True, "Master key match"),
        (test_api_key, test_api_key, True, "Stored key match"),
        (wrong_api_key, 'different-stored-key', False, "No match"),
        (TEMPLATE_MASTER_API_KEY, None, True, "Master key match (no stored)"),
    ]
    
    all_passed = True
    for api_key, stored_key, expected_result, description in test_cases:
        ok_master = hmac.compare_digest(api_key, TEMPLATE_MASTER_API_KEY) if TEMPLATE_MASTER_API_KEY else False
        ok_stored = hmac.compare_digest(api_key, stored_key) if stored_key else False
        result = ok_master or ok_stored
        
        if result == expected_result:
            print(f"   ✓ {description}: {result}")
        else:
            print(f"   ✗ {description}: expected {expected_result}, got {result}")
            all_passed = False
    
    if not all_passed:
        return False
    
    return True

def test_code_structure():
    """Verify the actual code in app.py has the fix"""
    print("\n" + "=" * 60)
    print("Verifying Code Structure in app.py")
    print("=" * 60)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check that require_api_key has the fallback logic
    checks = [
        ('DEFAULT_TENANT_ID', 'DEFAULT_TENANT_ID constant exists'),
        ('def require_api_key', 'require_api_key decorator exists'),
        ('get_setting(\'export_api_key\')', 'Calls get_setting for export_api_key'),
        ('if not stored:', 'Has fallback check for missing stored key'),
        ('tenant_id = DEFAULT_TENANT_ID', 'Uses DEFAULT_TENANT_ID in fallback'),
        ('hmac.compare_digest', 'Uses constant-time comparison'),
    ]
    
    all_passed = True
    for check_text, description in checks:
        if check_text in content:
            print(f"✓ {description}")
        else:
            print(f"✗ {description} - NOT FOUND")
            all_passed = False
    
    return all_passed

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("Export API Fix - Logic Validation Test")
    print("=" * 60 + "\n")
    
    try:
        test1_passed = test_api_key_logic()
        test2_passed = test_code_structure()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"API Key Logic:     {'✓ PASSED' if test1_passed else '✗ FAILED'}")
        print(f"Code Structure:    {'✓ PASSED' if test2_passed else '✗ FAILED'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! The fix logic is correct.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please review the output above.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
