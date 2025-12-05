#!/usr/bin/env python3
"""
Script de test pour valider l'intégration de la clé API maître
Usage: python test_master_api_key.py
"""

import os
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Configuration
TEMPLATE_URL = "http://localhost:5000"  # Changer pour https://template.artworksdigital.fr en prod
MASTER_KEY = os.getenv('TEMPLATE_MASTER_API_KEY')

if not MASTER_KEY:
    print("❌ Erreur: TEMPLATE_MASTER_API_KEY non trouvée dans .env")
    exit(1)

print(f"🔑 Clé maître chargée: {MASTER_KEY[:15]}...{MASTER_KEY[-10:]}")
print(f"🌐 URL du template: {TEMPLATE_URL}")
print("\n" + "="*60)

# Test 1: Récupérer les stats
print("\n📊 Test 1: GET /api/export/stats")
try:
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/stats",
        headers={"X-API-Key": MASTER_KEY},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Succès! Stats reçues:")
        print(f"   - Tables: {len([k for k in data.get('stats', {}).keys() if k.endswith('_count')])}")
        print(f"   - Revenue total: {data.get('stats', {}).get('total_revenue', 0)}€")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Lire un paramètre
print("\n📖 Test 2: GET /api/export/settings")
try:
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/settings",
        headers={"X-API-Key": MASTER_KEY},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Succès! {data.get('count', 0)} paramètres récupérés")
        # Chercher le prix cache
        settings = data.get('data', [])
        price_cache = next((s for s in settings if s['key'] == 'saas_site_price_cache'), None)
        if price_cache:
            print(f"   - Prix cache actuel: {price_cache.get('value', 'N/A')}")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 3: Mettre à jour le prix
print("\n✏️  Test 3: PUT /api/export/settings/saas_site_price_cache")
test_price = "550.00"  # 500€ base + 10% commission
try:
    response = requests.put(
        f"{TEMPLATE_URL}/api/export/settings/saas_site_price_cache",
        headers={
            "X-API-Key": MASTER_KEY,
            "Content-Type": "application/json"
        },
        json={"value": test_price},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Succès! Prix mis à jour: {test_price}€")
        else:
            print(f"⚠️  Réponse inattendue: {data}")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 4: Vérifier la mise à jour
print("\n🔍 Test 4: Vérification du prix mis à jour")
try:
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/settings",
        headers={"X-API-Key": MASTER_KEY},
        timeout=5
    )
    if response.status_code == 200:
        data = response.json()
        settings = data.get('data', [])
        price_cache = next((s for s in settings if s['key'] == 'saas_site_price_cache'), None)
        if price_cache:
            current_value = price_cache.get('value', 'N/A')
            if current_value == test_price:
                print(f"✅ Validation OK! Prix = {current_value}€")
            else:
                print(f"⚠️  Différence: attendu {test_price}€, obtenu {current_value}€")
        else:
            print(f"⚠️  Paramètre 'saas_site_price_cache' non trouvé")
    else:
        print(f"❌ Erreur {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "="*60)
print("\n🎉 Tests terminés!")
print("\n💡 Pour tester en production:")
print("   1. Changez TEMPLATE_URL vers https://template.artworksdigital.fr")
print("   2. Assurez-vous que le .env est déployé sur le serveur")
print("   3. Relancez ce script")
