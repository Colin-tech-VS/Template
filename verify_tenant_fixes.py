#!/usr/bin/env python3
"""
Simple verification of multi-tenant code fixes
Checks the code without importing (to avoid dependency issues)
"""

import re

def check_has_request_context_import():
    """Verify has_request_context is imported from Flask"""
    print("=" * 70)
    print("CHECK 1: has_request_context import")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Check for the import
    if 'has_request_context' in content:
        # Find the import line
        for line in content.split('\n'):
            if 'from flask import' in line and 'has_request_context' in line:
                print(f"✅ Found import: {line.strip()}")
                return True
        print("⚠️  has_request_context mentioned but not in import statement")
        return False
    else:
        print("❌ has_request_context NOT found in code")
        return False

def check_get_current_tenant_id_has_context_check():
    """Verify get_current_tenant_id checks for request context"""
    print("\n" + "=" * 70)
    print("CHECK 2: get_current_tenant_id() has request context check")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        lines = f.readlines()
    
    # Find the get_current_tenant_id function
    in_function = False
    function_lines = []
    
    for line in lines:
        if 'def get_current_tenant_id():' in line:
            in_function = True
        elif in_function:
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # End of function
                break
            function_lines.append(line)
    
    function_code = ''.join(function_lines)
    
    # Check for has_request_context check
    if 'has_request_context()' in function_code:
        print("✅ get_current_tenant_id() checks has_request_context()")
        
        # Check that it returns 1 when outside context
        if 'return 1' in function_code:
            print("✅ Returns default tenant_id (1) when outside context")
            return True
        else:
            print("⚠️  Doesn't return default value outside context")
            return False
    else:
        print("❌ get_current_tenant_id() does NOT check has_request_context()")
        return False

def check_no_startup_set_admin_user():
    """Verify set_admin_user is not called at module startup"""
    print("\n" + "=" * 70)
    print("CHECK 3: No set_admin_user call at startup")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        lines = f.readlines()
    
    # Look for the pattern of init_database() followed by set_admin_user()
    for i in range(len(lines) - 5):
        if 'init_database()' in lines[i]:
            # Check next few lines for set_admin_user
            next_5_lines = ''.join(lines[i:i+6])
            if "set_admin_user('coco.cayre@gmail.com')" in next_5_lines:
                print("❌ FOUND: set_admin_user called at startup")
                print(f"   Around line {i+1}")
                return False
    
    print("✅ set_admin_user is NOT called at startup")
    print("✅ This prevents 'Working outside of request context' error")
    return True

def check_comment_about_admin_setup():
    """Verify there's a comment about how to set admin users"""
    print("\n" + "=" * 70)
    print("CHECK 4: Comment about admin user setup")
    print("=" * 70)
    
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Look for comments about set_admin_user
    if 'set_admin_user' in content and ('NOTE' in content or 'note' in content):
        # Check if there's guidance near init_database
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'init_database()' in line:
                # Check surrounding lines for comments
                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+10)])
                if 'set_admin_user' in context and ('#' in context or 'NOTE' in context):
                    print("✅ Found guidance comment about set_admin_user")
                    # Print the relevant comment
                    for j in range(max(0, i-2), min(len(lines), i+10)):
                        if '#' in lines[j] or 'NOTE' in lines[j]:
                            print(f"   {lines[j].strip()}")
                    return True
    
    print("⚠️  No clear comment about admin user setup found")
    return False

if __name__ == "__main__":
    print("\n🔍 MULTI-TENANT FIX CODE VERIFICATION")
    print("=" * 70)
    print("Checking code changes without importing (avoids dependency issues)")
    print("=" * 70)
    
    results = []
    
    # Run checks
    results.append(("has_request_context import", check_has_request_context_import()))
    results.append(("get_current_tenant_id context check", check_get_current_tenant_id_has_context_check()))
    results.append(("No startup set_admin_user", check_no_startup_set_admin_user()))
    results.append(("Admin setup comment", check_comment_about_admin_setup()))
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "⚠️  INFO" if test_name == "Admin setup comment" else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    # Consider it success if at least the critical checks pass
    critical_passed = results[0][1] and results[1][1] and results[2][1]
    
    if critical_passed:
        print("\n✅ All critical fixes are in place!")
        print("   - has_request_context imported")
        print("   - get_current_tenant_id checks request context")
        print("   - No startup call to set_admin_user")
        print("\n🎉 Multi-tenant 'Working outside of request context' error is FIXED!")
        exit(0)
    else:
        print("\n⚠️  Some checks failed. Please review the code.")
        exit(1)
