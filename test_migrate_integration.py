#!/usr/bin/env python3
"""
Integration test for the audit report JSON serialization in migrate_apply_tenant_ids.py
This test simulates the actual audit report structure as it would be created during migration.
"""

import json
import sys
import tempfile
import os
from datetime import datetime

# Import the DateTimeEncoder and TenantMigrationAuditor
sys.path.insert(0, '/home/runner/work/Template/Template')
from migrate_apply_tenant_ids import DateTimeEncoder, TenantMigrationAuditor


def test_audit_report_serialization():
    """Test that a full audit report can be serialized to JSON"""
    
    print("Testing full audit report serialization...\n")
    
    # Create an auditor instance
    auditor = TenantMigrationAuditor()
    
    # Simulate data that would come from the database
    # This includes datetime objects that would cause serialization errors
    auditor.audit_report = {
        'execution_date': datetime.now().isoformat(),
        'tenants_found': [
            {
                'id': 1,
                'host': 'example.com',
                'name': 'Example Tenant',
                'created_at': datetime(2023, 1, 15, 10, 30, 45)  # datetime from DB
            },
            {
                'id': 2,
                'host': 'test.com',
                'name': 'Test Tenant',
                'created_at': datetime(2023, 3, 20, 14, 15, 30)  # datetime from DB
            }
        ],
        'sites_processed': [
            {
                'site_id': 1,
                'user_id': 10,
                'final_domain': 'site1.example.com',
                'sandbox_url': 'https://sandbox1.example.com',
                'old_tenant_id': 1,
                'new_tenant_id': 2,
                'tenant_host': 'example.com',
                'match_type': 'final_domain',
                'tables_updated': {
                    'users': 1,
                    'paintings': 5,
                    'saas_sites': 1
                },
                'total_rows': 7
            }
        ],
        'tables_updated': {
            'users': 1,
            'paintings': 5,
            'saas_sites': 1
        },
        'total_rows_updated': 7,
        'anomalies': [],
        'warnings': ['Test warning'],
        'errors': []
    }
    
    try:
        # Create a temporary file for the report
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            temp_filename = f.name
            # This is the exact line that was failing before the fix
            json.dump(auditor.audit_report, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        print(f"✅ Successfully wrote audit report to: {temp_filename}")
        
        # Verify the file can be read back and is valid JSON
        with open(temp_filename, 'r', encoding='utf-8') as f:
            loaded_report = json.load(f)
        
        print("✅ Successfully loaded audit report from file")
        
        # Verify structure
        assert 'execution_date' in loaded_report
        assert 'tenants_found' in loaded_report
        assert 'sites_processed' in loaded_report
        assert len(loaded_report['tenants_found']) == 2
        
        # Verify datetime objects were converted to strings
        assert isinstance(loaded_report['tenants_found'][0]['created_at'], str)
        assert isinstance(loaded_report['tenants_found'][1]['created_at'], str)
        
        # Verify ISO format
        assert loaded_report['tenants_found'][0]['created_at'] == '2023-01-15T10:30:45'
        assert loaded_report['tenants_found'][1]['created_at'] == '2023-03-20T14:15:30'
        
        print("✅ All datetime objects were properly converted to ISO format strings")
        print("✅ Audit report structure is correct")
        
        # Clean up
        os.unlink(temp_filename)
        print(f"✅ Cleaned up temporary file")
        
        return True
        
    except TypeError as e:
        print(f"❌ JSON serialization failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_without_custom_encoder():
    """Verify that without the custom encoder, the serialization would fail"""
    
    print("\nVerifying that the fix is necessary...\n")
    
    test_data = {
        'tenants_found': [
            {
                'id': 1,
                'host': 'example.com',
                'created_at': datetime(2023, 1, 15, 10, 30, 45)
            }
        ]
    }
    
    try:
        # Try without custom encoder - should fail
        json.dumps(test_data, indent=2, ensure_ascii=False)
        print("❌ Should have raised TypeError without custom encoder")
        return False
    except TypeError as e:
        print(f"✅ Confirmed: Without DateTimeEncoder, serialization fails with: {e}")
        return True


if __name__ == '__main__':
    print("="*80)
    print("INTEGRATION TEST: Audit Report JSON Serialization")
    print("="*80 + "\n")
    
    test1 = test_without_custom_encoder()
    test2 = test_audit_report_serialization()
    
    print("\n" + "="*80)
    if test1 and test2:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("="*80)
        sys.exit(0)
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("="*80)
        sys.exit(1)
