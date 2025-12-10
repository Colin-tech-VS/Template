"""
Script de test pour les webhooks Dashboard → Site Vitrine
Teste la validation de signature et le traitement des événements
"""

import requests
import hmac
import hashlib
import json
import os
import time

# Configuration
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')
WEBHOOK_SECRET = os.environ.get('DASHBOARD_WEBHOOK_SECRET', 'test_secret_key')

print("="*60)
print("🧪 TESTS WEBHOOK DASHBOARD → SITE VITRINE")
print("="*60)
print(f"URL Site: {SITE_URL}")
print(f"Secret configuré: {'Oui' if WEBHOOK_SECRET else 'Non'}")
print()


def generate_signature(payload: str, secret: str) -> str:
    """
    Génère une signature HMAC-SHA256 pour le payload
    
    Args:
        payload: Payload JSON (string)
        secret: Secret partagé
    
    Returns:
        Signature au format sha256=xxx
    """
    computed = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={computed}"


def test_ping():
    """Test 1: Vérifier que le service webhook est actif"""
    print("📡 Test 1: Ping webhook...")
    
    try:
        response = requests.get(f"{SITE_URL}/webhook/dashboard/ping", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Service actif: {data.get('status')}")
            print(f"   📍 Endpoints disponibles:")
            for name, path in data.get('endpoints', {}).items():
                print(f"      - {name}: {path}")
            return True
        else:
            print(f"   ❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def test_signature_validation():
    """Test 2: Vérifier la validation de signature"""
    print("\n🔐 Test 2: Validation de signature...")
    
    payload = json.dumps({
        'event': 'test.ping',
        'timestamp': time.time()
    })
    
    # Test avec signature valide
    print("   2a. Signature valide...")
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard/test",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"      ✅ Signature acceptée")
        else:
            print(f"      ❌ Status: {response.status_code}")
            print(f"      Response: {response.text}")
    except Exception as e:
        print(f"      ❌ Erreur: {e}")
    
    # Test avec signature invalide
    print("   2b. Signature invalide...")
    invalid_signature = "sha256=invalidhash12345"
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard/test",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': invalid_signature
            },
            timeout=5
        )
        
        if response.status_code == 401:
            print(f"      ✅ Signature rejetée (401)")
        else:
            print(f"      ⚠️  Status attendu: 401, reçu: {response.status_code}")
    except Exception as e:
        print(f"      ❌ Erreur: {e}")


def test_artist_updated_event():
    """Test 3: Événement artist.updated"""
    print("\n✏️  Test 3: Événement artist.updated...")
    
    payload = json.dumps({
        'event': 'artist.updated',
        'artist_id': 1,
        'data': {
            'name': 'Jean Dupont Modifié',
            'price': 650.00
        },
        'timestamp': time.time()
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Événement traité")
            print(f"      Action: {data.get('action')}")
            print(f"      Artist ID: {data.get('artist_id')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def test_artist_created_event():
    """Test 4: Événement artist.created"""
    print("\n➕ Test 4: Événement artist.created...")
    
    payload = json.dumps({
        'event': 'artist.created',
        'artist_id': 999,
        'data': {
            'name': 'Nouvel Artiste',
            'email': 'nouveau@example.com'
        },
        'timestamp': time.time()
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Événement traité")
            print(f"      Action: {data.get('action')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def test_artist_approved_event():
    """Test 5: Événement artist.approved"""
    print("\n✅ Test 5: Événement artist.approved...")
    
    payload = json.dumps({
        'event': 'artist.approved',
        'artist_id': 1,
        'data': {
            'status': 'approved',
            'approved_by': 'admin'
        },
        'timestamp': time.time()
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Événement traité")
            print(f"      Action: {data.get('action')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def test_artist_deleted_event():
    """Test 6: Événement artist.deleted"""
    print("\n🗑️  Test 6: Événement artist.deleted...")
    
    payload = json.dumps({
        'event': 'artist.deleted',
        'artist_id': 999,
        'timestamp': time.time()
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Événement traité")
            print(f"      Action: {data.get('action')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def test_unknown_event():
    """Test 7: Événement inconnu (doit être ignoré)"""
    print("\n❓ Test 7: Événement inconnu...")
    
    payload = json.dumps({
        'event': 'unknown.event',
        'artist_id': 1,
        'timestamp': time.time()
    })
    
    signature = generate_signature(payload, WEBHOOK_SECRET)
    
    try:
        response = requests.post(
            f"{SITE_URL}/webhook/dashboard",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'X-Dashboard-Signature': signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('action') == 'ignored':
                print(f"   ✅ Événement ignoré correctement")
                print(f"      Raison: {data.get('reason')}")
            else:
                print(f"   ⚠️  Événement traité (devrait être ignoré)")
        else:
            print(f"   ❌ Status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")


def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "="*60)
    print("🚀 LANCEMENT DES TESTS")
    print("="*60 + "\n")
    
    tests = [
        test_ping,
        test_signature_validation,
        test_artist_updated_event,
        test_artist_created_event,
        test_artist_approved_event,
        test_artist_deleted_event,
        test_unknown_event
    ]
    
    for test in tests:
        test()
        time.sleep(0.5)  # Pause entre tests
    
    print("\n" + "="*60)
    print("✅ TESTS TERMINÉS")
    print("="*60)
    print("\n💡 Pour tester en production:")
    print("   1. Définir SITE_URL='https://votre-site.com'")
    print("   2. Définir DASHBOARD_WEBHOOK_SECRET='secret_partagé'")
    print("   3. Relancer: python test_webhooks.py")


if __name__ == '__main__':
    run_all_tests()
