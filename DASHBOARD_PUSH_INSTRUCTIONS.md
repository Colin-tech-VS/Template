# Dashboard — Propagation de la Stripe Publishable Key vers les sites template

But: fournir un script et des instructions pour que le dashboard pousse automatiquement la `stripe_publishable_key` aux sites templates.

Endpoints cible (template):
- PUT /api/export/settings/stripe_publishable_key
  - Headers: `X-API-Key: <TEMPLATE_MASTER_API_KEY>`
  - Body: `{ "value": "pk_test_..." }`

Pré-requis côté dashboard
- Avoir la `TEMPLATE_MASTER_API_KEY` (clé maître partagée avec les templates)
- Liste des sites à mettre à jour (URL publique de chaque site template)

Fichiers fournis
- `dashboard_push_stripe_pk.py` — script synchrone (requests)
- `dashboard_push_stripe_pk_async.py` — script asynchrone (aiohttp) pour pousser en parallèle

Exemple simple (bash / cURL)

```bash
curl -X PUT https://template.artworksdigital.fr/api/export/settings/stripe_publishable_key \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value":"pk_test_51Hxxxx..."}'
```

Exemple Python (dashboard)

```python
import requests

TEMPLATE_MASTER_KEY = 'template-master-key-2025'
PUBLISHABLE_KEY = 'pk_test_51Hxxxx...'

sites = [
    'https://site1.preview.artworksdigital.fr',
    'https://site2.preview.artworksdigital.fr',
]

for s in sites:
    url = f"{s.rstrip('/')}/api/export/settings/stripe_publishable_key"
    resp = requests.put(url, headers={
        'Content-Type': 'application/json',
        'X-API-Key': TEMPLATE_MASTER_KEY
    }, json={'value': PUBLISHABLE_KEY}, timeout=8)
    print(s, resp.status_code, resp.text)
```

Bonnes pratiques
- Utiliser HTTPS
- Ne pas pousser la `stripe_secret_key` via un endpoint public. Si vous devez pousser la clé secrète, limitez fortement l'accès et chiffrez la communication.
- Throttle/Réguler les appels pour éviter de surcharger les sites (ex: 5-10 req/s)
- Journaliser chaque tentative (succès/échec), possibilité de retry pour erreurs temporaires

Test
1. Pusher une clé via cURL ou script
2. Tester la lecture côté site:
```bash
curl -i https://template.artworksdigital.fr/api/stripe-pk
```
Réponse attendue:
```json
{"success": true, "publishable_key": "pk_test_..."}
```

---

Si tu veux, je peux également :
- Ajouter l'option au dashboard pour "Propager à tous les sites" (bouton + background job)
- Générer un script d'exemple côté dashboard qui lit ses sites depuis la base et lance le push en lot
