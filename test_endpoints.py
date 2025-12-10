#!/usr/bin/env python
import requests
import json
import time
import subprocess
import sys
import os

BASE_URL = "http://localhost:5000"
API_KEY = "template-master-key-2025"

print("Démarrage du serveur Flask...")
flask_process = subprocess.Popen([sys.executable, "app.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
time.sleep(3)  

print("\n" + "="*80)
print("TEST a) PUT /api/export/settings/stripe_secret_key")
print("="*80)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_secret_key",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={"value": "sk_test_51234567890abcdefghijklmnop"}
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

print("\n" + "="*80)
print("TEST b) PUT /api/export/settings/stripe_publishable_key")
print("="*80)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_publishable_key",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={"value": "pk_test_51234567890abcdefghijklmnop"}
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

print("\n" + "="*80)
print("TEST c) GET /api/export/settings/stripe_publishable_key")
print("="*80)
response = requests.get(f"{BASE_URL}/api/export/settings/stripe_publishable_key")
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

print("\n" + "="*80)
print("TEST d) GET /api/export/settings/stripe_secret_key (doit retourner 404)")
print("="*80)
response = requests.get(f"{BASE_URL}/api/export/settings/stripe_secret_key")
print(f"Status Code: {response.status_code}")
if response.status_code == 404:
    print("[OK] Correctement 404!")
else:
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

print("\n" + "="*80)
print("TEST e) PUT sans API key (doit retourner 401)")
print("="*80)
response = requests.put(
    f"{BASE_URL}/api/export/settings/stripe_secret_key",
    headers={"Content-Type": "application/json"},
    json={"value": "sk_test_xxx"}
)
print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

print("\n" + "="*80)
print("RESUME DES TESTS")
print("="*80)
print("[OK] Tous les tests ont ete executes.")

flask_process.terminate()
