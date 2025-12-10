import requests
import json

BASE_URL = "http://localhost:5000"
MASTER_KEY = "template-master-key-2025"

print("=== Testing Stripe API Endpoints ===\n")

test_pk = "pk_test_51234567890abcdefghijklmnop"
test_sk = "sk_test_51234567890abcdefghijklmnop"

headers_with_key = {
    "X-API-Key": MASTER_KEY,
    "Content-Type": "application/json"
}

headers_without_key = {
    "Content-Type": "application/json"
}

print("Test 1: PUT stripe_publishable_key WITH master key")
print("-" * 60)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_publishable_key",
    json={"value": test_pk},
    headers=headers_with_key
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

print("Test 2: PUT stripe_secret_key WITH master key")
print("-" * 60)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_secret_key",
    json={"value": test_sk},
    headers=headers_with_key
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

print("Test 3: GET stripe_publishable_key (public access)")
print("-" * 60)
response = requests.get(f"{BASE_URL}/api/export/settings/stripe_publishable_key")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

print("Test 4: GET stripe_secret_key (should return 404)")
print("-" * 60)
response = requests.get(f"{BASE_URL}/api/export/settings/stripe_secret_key")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

print("Test 5: PUT WITHOUT API key (should fail)")
print("-" * 60)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_publishable_key",
    json={"value": test_pk},
    headers=headers_without_key
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
