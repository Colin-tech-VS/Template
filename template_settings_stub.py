"""Template helper: minimal Flask endpoints for settings (stripe keys)

This file is a small, self-contained example to deploy on a template
site. It implements:
- PUT /api/export/settings/<key>  (protected by X-API-Key)
- GET /api/export/settings/stripe_publishable_key

Replace the simple file-based persistence with your real DB logic
and adapt the API key lookup per-site as needed.
"""
from flask import Flask, request, jsonify
import os
import re
import hmac
import json

app = Flask(__name__)

# Master key fallback. In production, set this to a secure value per-site.
TEMPLATE_MASTER_API_KEY = os.getenv('TEMPLATE_MASTER_API_KEY', 'template-master-key-2025')
STORE_FILE = os.getenv('TEMPLATE_SETTINGS_STORE', 'settings_store.json')


def load_store():
    try:
        with open(STORE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_store(d):
    with open(STORE_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f)


def valid_api_key(provided, expected=None):
    if not provided:
        return False
    expected = expected or TEMPLATE_MASTER_API_KEY
    try:
        return hmac.compare_digest(provided, expected)
    except Exception:
        return False


@app.route('/api/export/settings/<key>', methods=['PUT'])
def put_setting(key):
    api_key = request.headers.get('X-API-Key', '')
    
    if not valid_api_key(api_key):
        print(f"[API] ❌ Clé API rejettée pour {key}")
        return jsonify({"error": "invalid_api_key", "success": False}), 401

    print(f"[API] 🔑 Clé maître acceptée - Configuration {key}")

    data = request.get_json(silent=True) or {}
    if 'value' not in data:
        print(f"[API] ❌ Valeur manquante pour {key}")
        return jsonify({"error": "missing_value", "success": False}), 400
    value = data['value']

    if key == 'stripe_secret_key':
        if not re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', value):
            print(f"[API] ❌ Format invalide pour stripe_secret_key: {value[:10] if len(value) >= 10 else value}...")
            return jsonify({"error": "invalid_secret_key_format", "success": False}), 400
        
        store = load_store()
        store[key] = value
        try:
            save_store(store)
            sanitized_key = value[:20] + '...' if len(value) > 20 else value
            print(f"[API] ✅ stripe_secret_key mis à jour: {sanitized_key}")
            return jsonify({"success": True, "message": "secret_saved"}), 200
        except Exception as e:
            print(f"[API] ❌ Erreur sauvegarde stripe_secret_key: {str(e)}")
            return jsonify({"error": "save_failed", "detail": str(e), "success": False}), 500
    
    elif key == 'stripe_publishable_key':
        if not re.match(r'^pk_(test|live)_[A-Za-z0-9]+$', value):
            print(f"[API] ❌ Format invalide pour stripe_publishable_key: {value[:10] if len(value) >= 10 else value}...")
            return jsonify({"error": "invalid_publishable_key_format", "success": False}), 400
        
        store = load_store()
        store[key] = value
        try:
            save_store(store)
            sanitized_key = value[:20] + '...' if len(value) > 20 else value
            print(f"[API] ✅ stripe_publishable_key mis à jour: {sanitized_key}")
            return jsonify({"success": True, "message": "publishable_saved"}), 200
        except Exception as e:
            print(f"[API] ❌ Erreur sauvegarde stripe_publishable_key: {str(e)}")
            return jsonify({"error": "save_failed", "detail": str(e), "success": False}), 500
    
    else:
        print(f"[API] ℹ️  Mise à jour paramètre générique: {key} = {value}")
        store = load_store()
        store[key] = value
        try:
            save_store(store)
            print(f"[API] ✅ {key} mis à jour avec succès")
            return jsonify({"success": True, "message": f"{key}_saved"}), 200
        except Exception as e:
            print(f"[API] ❌ Erreur sauvegarde {key}: {str(e)}")
            return jsonify({"error": "save_failed", "detail": str(e), "success": False}), 500


@app.route('/api/export/settings/stripe_publishable_key', methods=['GET'])
def get_pk():
    store = load_store()
    pk = store.get('stripe_publishable_key')
    if not pk:
        return jsonify({"success": False, "error": "not_set"}), 404
    # If this endpoint will be called directly from browsers, enable CORS
    return jsonify({"success": True, "publishable_key": pk}), 200


if __name__ == '__main__':
    # Simple runner for local testing
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')))
