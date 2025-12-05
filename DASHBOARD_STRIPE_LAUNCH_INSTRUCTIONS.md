# Dashboard — Comment modifier la clé Stripe pour le "Launch Site"

Objectif
-------
Ce document explique pas-à-pas ce que doit faire le dashboard (ou une IA qui l'automatise) pour **modifier la clé publishable Stripe utilisée par la template pour le front / launch flow**, sans toucher à la clé serveur (secret) stockée dans `admin_settings` ou en variables d'environnement.

Contexte technique (rappel)
- `stripe_publishable_key` : clé publique (pk_...) — utilisée côté client (Stripe.js). Peut être poussée depuis le dashboard et exposée via `GET /api/stripe-pk`.
- `stripe_secret_key` : clé secrète (sk_...) — utilisée côté serveur pour créer des sessions Checkout, PaymentIntents, etc. À stocker en variable d'environnement sur l'instance template (ou, si nécessaire, poussée via un canal sécurisé serveur-à-serveur).

Principe opérationnel
---------------------
1. Pour mettre à jour la clé publishable utilisée par une template, le dashboard doit appeler l'endpoint template suivant :

   PUT https://<TEMPLATE_SITE>/api/export/settings/stripe_publishable_key

   - Entête requis : `X-API-Key: <TEMPLATE_MASTER_API_KEY>` (clé maître que vous avez partagée entre dashboard et templates).
   - Corps JSON : `{"value":"<nouvelle_publishable_key>"}`

2. Après un PUT réussi, la template doit retourner un status HTTP 200 et le dashboard peut vérifier immédiatement via :

   GET https://<TEMPLATE_SITE>/api/stripe-pk

   Résultat attendu :
   {
     "success": true,
     "publishable_key": "pk_..."
   }

Consignes pour l'IA (ou le script automatisé)
--------------------------------------------
- Ne jamais modifier `stripe_secret_key` sauf si explicitement demandé par un administrateur et via un canal sécurisé. Le secret a des implications de sécurité importantes.
- Pour le **launch site flow** (paiement de mise en production) :
  - Vérifier si la template a une `stripe_secret_key` configurée (via `get_setting('stripe_secret_key')` serveur ou `STRIPE_SECRET_KEY` env). Sans secret, la génération de session Checkout échouera.
  - La clé publishable peut être changée pour mettre à jour l'expérience front (Stripe.js). Modifier `stripe_publishable_key` ne change pas la clé secrète côté serveur.
- Toujours valider le format de la publishable key côté dashboard avant de la pousser : regex simple `^pk_(test|live)_[A-Za-z0-9]+$`.

Exemples pratiques
------------------

1) Exemple curl pour pousser la publishable key vers une template

```bash
curl -X PUT "https://site1.artworksdigital.fr/api/export/settings/stripe_publishable_key" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: template-master-key-2025" \
  -d '{"value":"pk_live_xxx..."}'
```

2) Exemple PowerShell (Invoke-RestMethod)

```powershell
$hdr = @{ 'X-API-Key' = 'template-master-key-2025' }
Invoke-RestMethod -Uri 'https://site1.artworksdigital.fr/api/export/settings/stripe_publishable_key' -Method Put -Headers $hdr -Body '{"value":"pk_live_xxx..."}' -ContentType 'application/json'
```

3) Exemple Python (requests) — sync push + vérification

```python
import requests

TEMPLATE_MASTER_KEY = 'template-master-key-2025'
PK = 'pk_live_xxx...'
SITE = 'https://site1.artworksdigital.fr'

headers = {'Content-Type':'application/json', 'X-API-Key': TEMPLATE_MASTER_KEY}
resp = requests.put(f"{SITE}/api/export/settings/stripe_publishable_key", json={'value': PK}, headers=headers, timeout=10)
print('put', resp.status_code, resp.text)

# verify
resp2 = requests.get(f"{SITE}/api/stripe-pk", timeout=10)
print('get', resp2.status_code, resp2.json())
```

Vérifications recommandées après push
-----------------------------------
- Le dashboard doit relire `GET /api/stripe-pk` et vérifier `success: true` et la bonne `publishable_key`.
- Tester côté client (sur une page qui charge Stripe.js) que `window.STRIPE_PK` ou l'initialisation de Stripe.js charge la nouvelle clé.
- Pour le flow `saas_launch_site` : vérifier que le backend (template) possède bien une `stripe_secret_key` (env ou settings) — sinon la création de la session Checkout échouera même si la publishable key est mise à jour.

Sécurité & bonnes pratiques
---------------------------
- N'envoyer que la `stripe_publishable_key` via l'API publique fournie (PUT `/api/export/settings/...`).
- Ne jamais inclure une `stripe_secret_key` dans les clients ou pages non sécurisées. Préférer storage en variable d'environnement sur le serveur template.
- Le dashboard doit stocker `TEMPLATE_MASTER_API_KEY` dans un secret manager/variable d'environnement et le transmettre uniquement via HTTPS.
- Loguer les opérations de propagation (admin user, horodatage, site, résultat), masquer partiellement les clés dans les logs (p.ex. `pk_live_xxx...` → `pk_live_xxx...` ok mais ne loggez pas les secrets).

Comment rédiger les instructions pour une IA (prompts utiles)
---------------------------------------------------------
Si vous demandez à une IA d'exécuter la modification, fournissez un prompt clair du type :

```
Action: Push the new Stripe publishable key to the target template site(s).
Target sites: ["https://site1.artworksdigital.fr", "https://site2.artworksdigital.fr"]
Master API key: template-master-key-2025
New publishable key: pk_live_ABC123...
Verify: GET /api/stripe-pk after each successful PUT
Do not modify stripe_secret_key.
Return: JSON report with per-site status and response body.
```

Le point clé pour que l'IA n'altère pas la mauvaise valeur : insister sur `Do not modify stripe_secret_key` et demander explicitement l'endpoint `stripe_publishable_key`.

Annexes — endpoints template impliqués
-------------------------------------
- PUT `/api/export/settings/stripe_publishable_key` — (Auth: `X-API-Key`) => met à jour la clé publishable exposée
- PUT `/api/export/settings/stripe_secret_key` — (Auth: `X-API-Key`) => met à jour la clé secrète (ATTENTION : usage restreint)
- GET `/api/stripe-pk` — renvoie la clé publishable pour le client

---
Fichier créé automatiquement pour l'administrateur / intégrateur.
