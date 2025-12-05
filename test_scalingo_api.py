#!/usr/bin/env python3
"""
Script de test pour valider l'API Scalingo avec la clé maître
Usage: python test_scalingo_api.py
"""

import requests
import json

# Configuration
TEMPLATE_URL = "https://template.artworksdigital.fr"
MASTER_KEY = "template-master-key-2025"

print("="*70)
print("🧪 TEST DE L'API TEMPLATE SCALINGO")
print("="*70)
print(f"\n🌐 URL: {TEMPLATE_URL}")
print(f"🔑 Clé maître: {MASTER_KEY[:15]}...{MASTER_KEY[-10:]}\n")

# Test 1: Vérifier les stats (GET)
print("📊 Test 1: GET /api/export/stats")
print("-" * 70)
try:
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/stats",
        headers={"X-API-Key": MASTER_KEY},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Succès!")
        print(f"   Stats récupérées: {len(data.get('stats', {}))}")
        print(f"   Revenue total: {data.get('stats', {}).get('total_revenue', 0)}€")
    else:
        print(f"❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 2: Mettre à jour un paramètre de test
print("\n✏️  Test 2: PUT /api/export/settings/test_dashboard_key")
print("-" * 70)
test_value = "test_from_dashboard_2025"
try:
    response = requests.put(
        f"{TEMPLATE_URL}/api/export/settings/test_dashboard_key",
        headers={
            "X-API-Key": MASTER_KEY,
            "Content-Type": "application/json"
        },
        json={"value": test_value},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Succès! Paramètre 'test_dashboard_key' = '{test_value}'")
        else:
            print(f"⚠️  Réponse inattendue: {data}")
    else:
        print(f"❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 3: Configurer le prix SAAS (cas d'usage principal)
print("\n💰 Test 3: PUT /api/export/settings/saas_site_price_cache")
print("-" * 70)
price_value = "550.00"  # 500€ base + 10% commission
try:
    response = requests.put(
        f"{TEMPLATE_URL}/api/export/settings/saas_site_price_cache",
        headers={
            "X-API-Key": MASTER_KEY,
            "Content-Type": "application/json"
        },
        json={"value": price_value},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Succès! Prix SAAS configuré: {price_value}€")
            print(f"   Le bouton 'Lancer mon site' affichera ce prix")
        else:
            print(f"⚠️  Réponse inattendue: {data}")
    else:
        print(f"❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 4: Vérifier que le prix est bien sauvegardé
print("\n🔍 Test 4: Vérification du prix dans GET /api/export/settings")
print("-" * 70)
try:
    response = requests.get(
        f"{TEMPLATE_URL}/api/export/settings",
        headers={"X-API-Key": MASTER_KEY},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        settings = data.get('data', [])
        
        # Chercher saas_site_price_cache
        price_setting = next((s for s in settings if s['key'] == 'saas_site_price_cache'), None)
        if price_setting:
            saved_value = price_setting.get('value', 'N/A')
            if saved_value == price_value:
                print(f"✅ Validation OK! Prix sauvegardé: {saved_value}€")
            else:
                print(f"⚠️  Différence: attendu {price_value}€, obtenu {saved_value}€")
        else:
            print(f"⚠️  Paramètre 'saas_site_price_cache' non trouvé dans les settings")
    else:
        print(f"❌ Erreur: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Test 5: Tester avec une mauvaise clé (doit échouer)
print("\n🔒 Test 5: Tentative avec une mauvaise clé (doit échouer)")
print("-" * 70)
try:
    response = requests.put(
        f"{TEMPLATE_URL}/api/export/settings/test_key",
        headers={
            "X-API-Key": "wrong-key-12345",
            "Content-Type": "application/json"
        },
        json={"value": "should_fail"},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 403 or response.status_code == 401:
        print(f"✅ Sécurité OK! Accès refusé avec une mauvaise clé")
    else:
        print(f"⚠️  Attendu 403/401, obtenu {response.status_code}")
        print(f"   Réponse: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")

# Résumé
print("\n" + "="*70)
print("🎉 RÉSUMÉ DES TESTS")
print("="*70)
print("""
✅ Si tous les tests sont verts, l'intégration dashboard est prête !

Le dashboard peut maintenant :
1. Créer un site preview
2. Configurer automatiquement le prix (500€ + 10%)
3. Le prix s'affiche sur le bouton "Lancer mon site"

📋 Prochaines étapes dashboard :
- Implémenter l'appel PUT lors de la création du site preview
- Passer le prix calculé (base + commission)
- Gérer les erreurs API (timeouts, 403, 500)
""")
print("="*70)
