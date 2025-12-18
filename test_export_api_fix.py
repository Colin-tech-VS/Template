#!/usr/bin/env python3
"""
Test script to verify that export API endpoints can authenticate
when called with correct API keys, even when the host header doesn't match a tenant.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up environment before importing app
os.environ['TEMPLATE_MASTER_API_KEY'] = 'test-master-key-12345'
# Don't set DATABASE_URL - let it use the default database driver

from app import app, set_setting, get_setting, DEFAULT_TENANT_ID
import json
import secrets

def test_api_key_authentication():
    """Test that API key authentication works with fallback to default tenant"""
    print("\n=== Testing API Key Authentication ===\n")
    
    with app.app_context():
        # Generate a test API key
        test_api_key = secrets.token_urlsafe(32)
        print(f"1. Generated test API key: {test_api_key[:20]}...")
        
        # Store the API key in the default tenant
        set_setting('export_api_key', test_api_key)
        print(f"2. Stored API key in default tenant (tenant_id={DEFAULT_TENANT_ID})")
        
        # Verify it was stored
        retrieved_key = get_setting('export_api_key')
        if retrieved_key == test_api_key:
            print("3. ✓ API key successfully retrieved from settings")
        else:
            print(f"3. ✗ API key mismatch! Expected: {test_api_key[:20]}..., Got: {retrieved_key}")
            return False
    
    # Test with Flask test client
    with app.test_client() as client:
        print("\n--- Test 1: Request without API key (should fail) ---")
        response = client.get('/api/export/stats')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        if response.status_code == 401:
            print("✓ Correctly rejected request without API key")
        else:
            print("✗ Should have returned 401 without API key")
            return False
        
        print("\n--- Test 2: Request with wrong API key (should fail) ---")
        response = client.get(
            '/api/export/stats',
            headers={'X-API-Key': 'wrong-key-123'}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        if response.status_code == 401:
            print("✓ Correctly rejected request with wrong API key")
        else:
            print("✗ Should have returned 401 with wrong API key")
            return False
        
        print("\n--- Test 3: Request with correct API key (should succeed) ---")
        response = client.get(
            '/api/export/stats',
            headers={'X-API-Key': test_api_key}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Response: {json.dumps(data, indent=2)[:200]}...")
            print("✓ Successfully authenticated with correct API key")
        else:
            print(f"✗ Should have returned 200 with correct API key. Response: {response.get_json()}")
            return False
        
        print("\n--- Test 4: Request with master API key (should succeed) ---")
        response = client.get(
            '/api/export/stats',
            headers={'X-API-Key': 'test-master-key-12345'}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Successfully authenticated with master API key")
        else:
            print(f"✗ Should have returned 200 with master key. Response: {response.get_json()}")
            return False
        
        print("\n--- Test 5: Different endpoints with correct API key ---")
        endpoints = [
            '/api/export/users',
            '/api/export/orders',
            '/api/export/paintings',
            '/api/export/exhibitions',
            '/api/export/custom-requests',
        ]
        
        all_passed = True
        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={'X-API-Key': test_api_key}
            )
            status_symbol = "✓" if response.status_code == 200 else "✗"
            print(f"{status_symbol} {endpoint}: {response.status_code}")
            if response.status_code != 200:
                all_passed = False
                print(f"   Error: {response.get_json()}")
        
        if not all_passed:
            print("\n✗ Some endpoints failed authentication")
            return False
        
        print("\n✓ All export endpoints successfully authenticated")
    
    return True

def test_host_header_scenarios():
    """Test that authentication works with various Host headers"""
    print("\n=== Testing Host Header Scenarios ===\n")
    
    with app.app_context():
        # Generate a test API key and store it
        test_api_key = secrets.token_urlsafe(32)
        set_setting('export_api_key', test_api_key)
        print(f"Stored API key: {test_api_key[:20]}...")
    
    with app.test_client() as client:
        # Test with various host headers that might not match any tenant
        test_hosts = [
            'localhost',
            '127.0.0.1',
            'unknown-site.com',
            '10.0.0.195',  # Internal IP like in the logs
            'preview-site-123.onrender.com',
        ]
        
        print("\nTesting authentication with different Host headers:\n")
        all_passed = True
        for host in test_hosts:
            response = client.get(
                '/api/export/stats',
                headers={
                    'X-API-Key': test_api_key,
                    'Host': host
                }
            )
            status_symbol = "✓" if response.status_code == 200 else "✗"
            print(f"{status_symbol} Host: {host:30} Status: {response.status_code}")
            if response.status_code != 200:
                all_passed = False
                print(f"   Error: {response.get_json()}")
        
        if not all_passed:
            print("\n✗ Some host scenarios failed")
            return False
        
        print("\n✓ All host scenarios passed")
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Export API Authentication Fix - Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        test1_passed = test_api_key_authentication()
        test2_passed = test_host_header_scenarios()
        
        # Clean up test database
        if os.path.exists('test_export_fix.db'):
            os.remove('test_export_fix.db')
            print("\nCleaned up test database")
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"API Key Authentication: {'✓ PASSED' if test1_passed else '✗ FAILED'}")
        print(f"Host Header Scenarios:  {'✓ PASSED' if test2_passed else '✗ FAILED'}")
        
        if test1_passed and test2_passed:
            print("\n🎉 All tests passed! The fix is working correctly.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please review the output above.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
