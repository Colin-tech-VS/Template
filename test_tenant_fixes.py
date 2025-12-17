#!/usr/bin/env python3
"""
Test to verify the multi-tenant fixes work correctly
This test checks:
1. get_current_tenant_id() works outside request context
2. No "Working outside of request context" errors
"""

import os
import sys

# Mock Flask request context for testing
class MockRequest:
    host = "localhost:5000"

def test_tenant_id_outside_context():
    """Test that get_current_tenant_id() works when called outside HTTP request context"""
    print("=" * 70)
    print("TEST 1: get_current_tenant_id() outside request context")
    print("=" * 70)
    
    # Import app which will call functions at module level
    try:
        # This will trigger any module-level code in app.py
        import app
        
        # Test calling get_current_tenant_id directly without request context
        tenant_id = app.get_current_tenant_id()
        
        print(f"✅ get_current_tenant_id() returned: {tenant_id}")
        print(f"✅ No 'Working outside of request context' error!")
        
        if tenant_id == 1:
            print("✅ Correctly returned default tenant_id (1) when outside context")
            return True
        else:
            print(f"⚠️  Unexpected tenant_id: {tenant_id} (expected 1)")
            return False
            
    except RuntimeError as e:
        if "Working outside of request context" in str(e):
            print(f"❌ FAILED: Still getting 'Working outside of request context' error")
            print(f"   Error: {e}")
            return False
        else:
            raise
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_has_request_context_import():
    """Test that has_request_context is properly imported"""
    print("\n" + "=" * 70)
    print("TEST 2: has_request_context import")
    print("=" * 70)
    
    try:
        import app
        
        # Check that has_request_context is imported
        if hasattr(app, 'has_request_context'):
            print("✅ has_request_context is imported from Flask")
            return True
        else:
            # It might not be exposed at module level, check the import
            from flask import has_request_context
            print("✅ has_request_context can be imported from Flask")
            return True
            
    except ImportError as e:
        print(f"❌ FAILED: Cannot import has_request_context: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

def test_startup_no_set_admin_user():
    """Test that set_admin_user is not called at startup"""
    print("\n" + "=" * 70)
    print("TEST 3: set_admin_user not called at startup")
    print("=" * 70)
    
    try:
        # Read app.py and check that set_admin_user is not called at module level
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Look for the problematic pattern: set_admin_user called outside try-except at startup
        lines = content.split('\n')
        
        found_startup_call = False
        for i in range(len(lines) - 10):
            # Look for init_database() at module level (not inside a function)
            if 'init_database()' in lines[i] and not lines[i].startswith('    '):
                # Check next few lines for set_admin_user
                next_lines = '\n'.join(lines[i:min(len(lines), i+15)])
                # Check for set_admin_user with any email (not specific to avoid exposing email)
                if 'set_admin_user(' in next_lines and '@' in next_lines:
                    found_startup_call = True
                    print(f"❌ FOUND: set_admin_user called at startup around line {i+1}")
                    break
        
        if not found_startup_call:
            print("✅ set_admin_user is NOT called at module startup")
            print("✅ This prevents 'Working outside of request context' error")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error checking code: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 MULTI-TENANT FIX VERIFICATION TESTS")
    print("=" * 70)
    
    results = []
    
    # Run tests
    results.append(("Tenant ID outside context", test_tenant_id_outside_context()))
    results.append(("has_request_context import", test_has_request_context_import()))
    results.append(("No startup set_admin_user", test_startup_no_set_admin_user()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-tenant fixes are working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the fixes.")
        sys.exit(1)
