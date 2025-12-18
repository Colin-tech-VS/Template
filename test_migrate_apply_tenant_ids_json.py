#!/usr/bin/env python3
"""
Test for JSON serialization fix in migrate_apply_tenant_ids.py
"""

import json
import sys
from datetime import datetime

# Import the DateTimeEncoder from the migration script
sys.path.insert(0, '/home/runner/work/Template/Template')
from migrate_apply_tenant_ids import DateTimeEncoder


def test_datetime_encoder():
    """Test that DateTimeEncoder properly handles datetime objects"""
    
    # Create a sample audit report structure with datetime objects
    test_data = {
        'execution_date': datetime.now().isoformat(),
        'tenants_found': [
            {
                'id': 1,
                'host': 'example.com',
                'name': 'Test Tenant',
                'created_at': datetime(2023, 1, 15, 10, 30, 45)  # datetime object
            }
        ],
        'sites_processed': [
            {
                'site_id': 1,
                'user_id': 10,
                'final_domain': 'test.example.com',
                'created_at': datetime(2023, 2, 20, 14, 15, 30)  # datetime object
            }
        ],
        'total_rows_updated': 42,
        'warnings': [],
        'errors': []
    }
    
    try:
        # Try to serialize with the custom encoder
        json_str = json.dumps(test_data, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        
        # Verify datetime objects were converted to strings
        assert isinstance(parsed['tenants_found'][0]['created_at'], str)
        assert isinstance(parsed['sites_processed'][0]['created_at'], str)
        
        # Verify the format is ISO 8601
        assert parsed['tenants_found'][0]['created_at'] == '2023-01-15T10:30:45'
        assert parsed['sites_processed'][0]['created_at'] == '2023-02-20T14:15:30'
        
        print("✅ Test passed: DateTimeEncoder correctly serializes datetime objects")
        return True
        
    except TypeError as e:
        print(f"❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_standard_encoder_fails():
    """Verify that the standard encoder fails with datetime objects"""
    
    test_data = {
        'created_at': datetime(2023, 1, 15, 10, 30, 45)
    }
    
    try:
        json.dumps(test_data)  # Should fail
        print("❌ Test failed: Standard encoder should have raised TypeError")
        return False
    except TypeError:
        print("✅ Test passed: Standard encoder correctly raises TypeError for datetime")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == '__main__':
    print("Testing JSON serialization fix for datetime objects...\n")
    
    test1 = test_standard_encoder_fails()
    print()
    test2 = test_datetime_encoder()
    
    if test1 and test2:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)
