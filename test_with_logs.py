#!/usr/bin/env python
import requests
import json
import time
import subprocess
import sys
import threading

BASE_URL = "http://localhost:5000"
API_KEY = "template-master-key-2025"

print("Demarrage du serveur Flask...")
flask_process = subprocess.Popen(
    [sys.executable, "app.py"], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    bufsize=1
)

def read_logs():
    print("\n" + "="*80)
    print("LOGS DU SERVEUR FLASK")
    print("="*80)
    for line in flask_process.stdout:
        if line.strip():
            print(line.rstrip())
        if "[API]" in line:
            print("[LOG CAPTURED] " + line.rstrip())

log_thread = threading.Thread(target=read_logs, daemon=True)
log_thread.start()

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

time.sleep(1)

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

time.sleep(1)

print("\n" + "="*80)
print("ATTENTE DES LOGS...")
print("="*80)
time.sleep(2)

flask_process.terminate()
