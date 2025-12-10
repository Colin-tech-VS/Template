import os
import sys
from dotenv import load_dotenv

load_dotenv()

TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY')

print("=== Stripe Endpoints Configuration Test ===\n")
print(f"1. TEMPLATE_MASTER_API_KEY loaded: {repr(TEMPLATE_MASTER_API_KEY)}")
print(f"   Expected: 'template-master-key-2025'")
print(f"   Status: {'OK' if TEMPLATE_MASTER_API_KEY == 'template-master-key-2025' else 'FAILED'}\n")

import hmac
test_key = 'template-master-key-2025'
comparison_result = hmac.compare_digest(TEMPLATE_MASTER_API_KEY, test_key) if TEMPLATE_MASTER_API_KEY else False
print(f"2. HMAC constant-time comparison test:")
print(f"   Result: {comparison_result}\n")

print("3. Ready for endpoint testing")
print(f"   - PUT /api/export/settings/stripe_secret_key")
print(f"   - PUT /api/export/settings/stripe_publishable_key")
print(f"   - GET /api/export/settings/stripe_publishable_key")
print(f"   - GET /api/export/settings/stripe_secret_key (should return 404)")
