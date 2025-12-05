# Intégration de la clé Stripe (publishable) — Guide pour le site template

But

Ce document explique, pas à pas, ce qu'il faut ajouter côté "site template" (ex: https://template.artworksdigital.fr) pour recevoir et utiliser la clé Stripe publique (publishable key) fournie par le dashboard (`https://admin.artworksdigital.fr`). Le dashboard expose désormais une route pour récupérer la publishable key et peut pousser la clé aux sites. Le template doit : exposer un endpoint local pour fournir la clé côté client, accepter un push depuis le dashboard et initialiser Stripe.js côté frontend.

Résumé rapide

- Ajouter côté template :
  - `GET /api/stripe-pk` → retourne la `publishable_key` (sécurisée côté serveur, safe à exposer au client)
  - `PUT /api/export/settings/stripe_publishable_key` → reçoit la clé poussée par le dashboard (auth via `X-API-Key`)
  - JS client : fetch `/api/stripe-pk` et initialiser `Stripe(publishable_key)`
- Variables d'environnement recommandées : `STRIPE_PUBLISHABLE_KEY`, `DASHBOARD_URL`, `SITE_NAME`, `TEMPLATE_MASTER_API_KEY`
- Tests fournis via `curl`

Variables d'environnement (recommandées)

- `STRIPE_PUBLISHABLE_KEY` — (optionnel) clé locale publishable.
- `DASHBOARD_URL` — URL du dashboard central (ex: `https://admin.artworksdigital.fr`) si on active le fallback server→server.
- `SITE_NAME` — identifiant unique du site (tel que connu par le dashboard), utilisé si template interroge le dashboard.
- `TEMPLATE_MASTER_API_KEY` — secret partagé pour authentifier les PUTs depuis le dashboard.

Exemples de code (Flask)

> Note : adaptez `get_config` et `save_config` à votre méthode de persistance (DB, SQLite, JSON, env vars...).

1) Utilitaire (ex: stockage simple JSON local)

```python
# utils_config.py
import json, os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'site_config.json')

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config_dict(d):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def get_config(key):
    d = load_config()
    return d.get(key) or os.getenv(key.upper())

def save_config(key, value):
    d = load_config()
    d[key] = value
    save_config_dict(d)
    return True
```

2) Endpoint `GET /api/stripe-pk` — fournir la publishable key au client

```python
# dans app.py (template site)
from flask import jsonify
import os, requests
from utils_config import get_config

DASHBOARD_URL = os.getenv('DASHBOARD_URL')
SITE_NAME = os.getenv('SITE_NAME')

@app.route('/api/stripe-pk', methods=['GET'])
def api_stripe_pk():
    # 1) lecture locale
    pk = get_config('stripe_publishable_key') or os.getenv('STRIPE_PUBLISHABLE_KEY')
    if pk:
        return jsonify({"success": True, "publishable_key": pk})

    # 2) fallback server->server: interroger le dashboard si configuré
    try:
        if DASHBOARD_URL and SITE_NAME:
            resp = requests.get(f"{DASHBOARD_URL}/api/sites/{SITE_NAME}/stripe-key", timeout=5)
            if resp.ok:
                data = resp.json()
                if data.get('success') and data.get('publishable_key'):
                    return jsonify({"success": True, "publishable_key": data.get('publishable_key')})
    except Exception as e:
        app.logger.debug(f"stripe pk fallback error: {e}")

    return jsonify({"success": False, "message": "no_publishable_key"}), 404
```

3) Endpoint `PUT /api/export/settings/stripe_publishable_key` — accepter la clé poussée par le dashboard

```python
from flask import request, jsonify
import os
from utils_config import save_config

@app.route('/api/export/settings/stripe_publishable_key', methods=['PUT'])
def import_setting_stripe_pk():
    api_key = request.headers.get('X-API-Key')
    expected = os.getenv('TEMPLATE_MASTER_API_KEY')
    if not expected or api_key != expected:
        return jsonify({"success": False, "error": "unauthorized"}), 403

    body = request.get_json(silent=True) or {}
    value = body.get('value')
    if not value:
        return jsonify({"success": False, "error": "missing_value"}), 400

    try:
        save_config('stripe_publishable_key', value)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
```

Frontend — initialiser Stripe.js

1) Charger Stripe v3 (dans `<head>` ou avant usage) :

```html
<script src="https://js.stripe.com/v3/"></script>
```

2) JS d'initialisation (ex: `static/js/stripe-init.js`) :

```javascript
async function initStripeFromServer() {
  try {
    const res = await fetch('/api/stripe-pk');
    if (!res.ok) {
      console.warn('Stripe publishable key not found on server');
      return null;
    }
    const json = await res.json();
    if (json.success && json.publishable_key) {
      window.STRIPE_PK = json.publishable_key;
      window.STRIPE = Stripe(window.STRIPE_PK);
      return window.STRIPE;
    } else {
      console.warn('No publishable key in response:', json);
      return null;
    }
  } catch (e) {
    console.error('initStripeFromServer error', e);
    return null;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const stripe = await initStripeFromServer();
  if (stripe) {
    // initialiser Elements / checkout
  } else {
    // masquer formulaire / afficher message admin
  }
});
```

Commandes de test

- Vérifier la presence de la clé (GET):

```
curl -i http://localhost:5000/api/stripe-pk
```

- Simuler le push depuis le dashboard :

```
curl -X PUT http://localhost:5000/api/export/settings/stripe_publishable_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_template_master_key" \
  -d '{"value":"pk_test_51Hxxxx..."}'
```

- Retester la lecture après le PUT :

```
curl -i http://localhost:5000/api/stripe-pk
```

Dashboard : comment pusher depuis le dashboard (exemple)

- Le dashboard peut itérer ses sites (`db_manager.get_all_sites()`) et pour chaque site effectuer :

```
PUT https://<site.url>/api/export/settings/stripe_publishable_key
Headers: { 'Content-Type': 'application/json', 'X-API-Key': site.api_key }
Body: { "value": "pk_live_..." }
```

Bonnes pratiques & sécurité

- Ne jamais exposer la `stripe_secret_key` (clé `sk_...`) côté client ni via endpoint public.
- Authentifier les endpoints d'import (`PUT /api/export/*`) via `X-API-Key` ou autre token secret.
- Utiliser HTTPS en production.
- Limiter le fallback server→server si vous ne voulez pas de dépendance réseau continue.
- Cacher/mettre en cache la clé côté template si vous appelez souvent le dashboard.

Options avancées

- Si vous préférez que le site n'appelle jamais le dashboard, utilisez uniquement la propagation (dashboard pousse la clé aux sites) ; le site stocke la clé localement et `GET /api/stripe-pk` la lit directement.
- Si vous souhaitez que le dashboard fournisse la clé directement au navigateur (moins recommandé), il faut configurer le CORS sur le dashboard et accepter les requêtes cross-origin.

Prochaines étapes proposées (je peux faire):

- Générer un patch prêt à coller dans le repo du template (`utils_config.py` + modifications `app.py` + `static/js/stripe-init.js`).
- Implémenter côté dashboard la route de propagation et un bouton "Propager à tous les sites".

---

Copiez-collez ce fichier dans l'admin ou dans votre gestionnaire SI ; il contient tout ce qu'il faut pour que `https://template.artworksdigital.fr` lise et utilise correctement la clé Stripe publique fournie par `https://admin.artworksdigital.fr`.
