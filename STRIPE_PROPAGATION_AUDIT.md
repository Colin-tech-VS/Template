# 🔐 Audit Complet: Propagation Stripe et Gestion des Prix

**Date:** 2025-12-13  
**Projet:** Artworksdigital (Dashboard → Template → Vitrine)  
**Statut:** ✅ Architecture correcte, points mineurs à améliorer

---

## 1. Vue d'ensemble du flux Stripe

### 1.1 Flux théorique (CORRECT)

```
Dashboard (admin.artworksdigital.fr)
    │
    ├─→ (1) PUT /api/export/settings/stripe_publishable_key
    │        { "value": "pk_test_..." }
    │        Header: X-API-Key: TEMPLATE_MASTER_API_KEY
    │
    └─→ (2) PUT /api/export/settings/stripe_secret_key
             { "value": "sk_test_..." }
             Header: X-API-Key: TEMPLATE_MASTER_API_KEY
             
        ↓↓↓ (Transmission sécurisée)
        
Template (template.artworksdigital.fr)
    │
    ├─→ Stocke dans Supabase:
    │   - settings.stripe_publishable_key (non-sensible)
    │   - settings.stripe_secret_key (ultra-sensible)
    │
    ├─→ Expose endpoint GET /api/stripe-pk
    │   Retourne: { "success": true, "publishable_key": "pk_..." }
    │
    └─→ Utilise le secret pour Stripe.js côté serveur

Vitrine (jeanbaptiste.artworksdigital.fr, example.com)
    │
    ├─→ Fetch GET /api/stripe-pk depuis le Template
    │   Obtient: "pk_test_..."
    │
    └─→ Initialise Stripe(publishable_key) côté frontend
```

---

## 2. Analyse Dashboard → Template

### 2.1 Propagation des clés (✅ CORRECTE)

**Fichier:** `dashboard_patch/stripe_propagate.py` (lignes 23-28)

```python
def push_to_site(site_url, publishable_key, master_key, timeout=8):
    api_path = '/api/export/settings/stripe_publishable_key'
    target = urljoin(site_url.rstrip('/') + '/', api_path.lstrip('/'))
    headers = {'Content-Type': 'application/json', 'X-API-Key': master_key}
    resp = requests.put(target, headers=headers, json={'value': publishable_key}, timeout=timeout)
```

**✅ Observations correctes:**
- Endpoint: `/api/export/settings/stripe_publishable_key` 
- Méthode: PUT
- Header: `X-API-Key` avec master key
- Payload: JSON `{"value": "pk_test_..."}`
- Timeout: 8 secondes

### 2.2 Dashboard push des prix (⚠️ A VÉRIFIER)

**Question clé:** Le Dashboard envoie-t-il les prix au Template?

**Réponse:** NON (par design, ce qui est CORRECT)

Le Dashboard n'envoie que les CLÉS Stripe, pas les prix. Les prix sont:
- Gérés côté Template (produits, peintures)
- Récupérés par le Dashboard depuis les endpoints de Template

---

## 3. Analyse Template → Routes Stripe

### 3.1 Endpoints de réception (✅ CORRECTS)

#### GET /api/stripe-pk (ligne 4022)
```python
@app.route('/api/stripe-pk', methods=['GET'])
def api_stripe_pk():
    # 1) lecture locale (Supabase settings)
    pk = get_setting('stripe_publishable_key')
    if pk: return jsonify({"success": True, "publishable_key": pk})
    
    # 2) fallback env var
    pk = os.getenv('STRIPE_PUBLISHABLE_KEY')
    if pk: return jsonify({"success": True, "publishable_key": pk})
    
    # 3) fallback server->server Dashboard
    # (endpoint: /api/sites/{site_id}/stripe-key)
```

**✅ Correct:**
- Public (pas d'authentification requise)
- Expose UNIQUEMENT la clé publique (pk_)
- 3 niveaux de fallback (Supabase → env → Dashboard)
- CORS headers activés pour client JS

#### PUT /api/export/settings/stripe_publishable_key (ligne 3936)
```python
@app.route('/api/export/settings/stripe_publishable_key', methods=['PUT'])
def update_stripe_publishable_key():
    # 1) Vérifier X-API-Key (master ou stored)
    api_key = request.headers.get('X-API-Key')
    master_key = TEMPLATE_MASTER_API_KEY
    has_valid_master = hmac.compare_digest(api_key, master_key)  # Constant-time
    
    # 2) Validation format pk_test_... ou pk_live_...
    if not re.match(r'^pk_(test|live)_[A-Za-z0-9]+$', value):
        return error("invalid_publishable_format")
    
    # 3) Stocker dans Supabase
    set_setting('stripe_publishable_key', value)
```

**✅ Correct:**
- Auth par `X-API-Key` header
- Comparaison constant-time (sécurité)
- Validation regex stricte (format pk_)
- Stockage Supabase
- Jamais exposé via GET

#### PUT /api/export/settings/stripe_secret_key (ligne 3862)
```python
@app.route('/api/export/settings/stripe_secret_key', methods=['PUT'])
def update_stripe_secret_key():
    # Même logique que publishable_key
    # MAIS: validation format sk_test_... ou sk_live_...
    if not re.match(r'^sk_(test|live)_[A-Za-z0-9]+$', value):
        return error("invalid_secret_format")
    
    # Stockage Supabase (jamais exposé)
    set_setting('stripe_secret_key', value)
```

**✅ Correct:**
- Auth par `X-API-Key` header
- Validation regex stricte (format sk_)
- Stockage sécurisé Supabase
- **JAMAIS exposé via GET** (ligne 4013: return 404)

### 3.2 Sécurité du endpoint GET (ligne 4013-4019)

```python
@app.route('/api/export/settings/stripe_secret_key', methods=['GET'])
def get_stripe_secret_key_blocked():
    """Security: Never expose the secret key to GET requests."""
    return jsonify({'error': 'not_found'}), 404
```

**✅ EXCELLENT:**
- Empêche tout accès au secret_key via GET
- Retourne 404 pour éviter les fuites

---

## 4. Analyse de la gestion des prix

### 4.1 Prix SAAS (lancement du site)

**Fonction:** `fetch_dashboard_site_price()` (ligne 528)

```python
def fetch_dashboard_site_price():
    base_url = get_dashboard_base_url()
    site_id = get_setting("dashboard_id")
    
    # Priorité 0: override manuel
    manual = get_setting("saas_site_price_override")
    
    # Priorité 1: endpoint site price dédié
    endpoint_site_price = f"{base_url}/api/sites/{site_id}/price"
    
    # Priorité 2: endpoint config
    endpoint_config = f"{base_url}/api/config/artworks"
    
    # Récupère le prix depuis le Dashboard
    resp = requests.get(endpoint)
    base_price = float(data.get("price") or data.get("site_price") or 0)
    
    # Fallback cache
    cached = get_setting("saas_site_price_cache")
```

**✅ Observations:**
- Le Template DEMANDE les prix au Dashboard
- Le Dashboard NE POUSSE PAS les prix
- Caching local en Supabase
- Plusieurs fallbacks pour robustesse

### 4.2 Prix des produits Stripe

**Question:** Les prix des produits (peintures, objets) sont-ils propagés du Dashboard?

**Réponse:** NON - Par design, c'est CORRECT

**Raison:** Les produits/peintures sont créés et gérés côté Template:
- Table: `paintings` (app.py:2698)
- Chaque peinture a un prix
- Le Template expose ces prix via `/api/export/paintings`
- Le Dashboard lit ces prix depuis le Template (pas l'inverse)

**Flux réel:**
```
Template (stocke données produits)
    ├─→ paintings.id, paintings.name, paintings.price
    └─→ /api/export/paintings → Dashboard lit les prix
    
Dashboard (lit les données)
    ├─→ Affiche les prix des peintures
    └─→ NE modifie pas les prix
```

---

## 5. Flux de Stripe Checkout

### 5.1 Checkout boutique (ligne 4349-4368)

```python
@app.route('/checkout', methods=['POST'])
def checkout():
    stripe_secret = get_stripe_secret_key()
    stripe.api_key = stripe_secret  # SECRET récupéré depuis Supabase
    
    session_obj = stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {'name': painting.name},
                'unit_amount': int(painting.price * 100)  # Prix depuis DB locale
            }
        }]
    )
```

**✅ Correct:**
- Utilise le secret_key pour l'API serveur
- Crée des sessions Stripe côté serveur
- Pas d'exposition de secret au client

### 5.2 Checkout lancement du site (ligne 4350-4356)

```python
@app.route('/saas/launch-site', methods=['GET'])
def saas_launch_site():
    price = fetch_dashboard_site_price()  # Récupère du Dashboard
    
    stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'eur',
                'product_data': {'name': 'Lancement de votre site'},
                'unit_amount': int(price * 100)
            }
        }]
    )
```

**✅ Correct:**
- Récupère le prix du Dashboard
- Crée la session Stripe avec ce prix

---

## 6. Problèmes identifiés

### 6.1 ⚠️ MINEUR: Pas de endpoint pour price_id Stripe

**Situation:**
- Les clés Stripe (pk, sk) sont propagées ✅
- Les prix SAAS sont propagés ✅
- **MANQUANT:** Les `price_id` Stripe ne sont pas propagés

**Exemples de price_id:**
```
price_1A4Xc...  (Pour un produit Stripe)
price_1A4Xd...  (Pour une peinture)
```

**Quand c'est un problème:**
- Si le Dashboard crée des produits Stripe (ex: abonnements, bundles)
- Si le Template doit utiliser les `price_id` du Dashboard
- Actuellement, le Template crée les prix inline (pas un problème réel)

**Recommandation:** Ajouter un endpoint optionnel pour propager price_id

### 6.2 ⚠️ MINEUR: Validation regex stricte sur les clés

**Situation:**
```python
if not re.match(r'^pk_(test|live)_[A-Za-z0-9]+$', value):
    return error("invalid_format")
```

**Issue:** Les clés Stripe peuvent contenir d'autres caractères (`-`, `_`)

**Exemple valide rejeté:**
```
pk_test_51H7gXXXXXXXX-aBc123
        ↑
     (tiret non autorisé dans regex)
```

**Fix:** Utiliser `[A-Za-z0-9_-]+` au lieu de `[A-Za-z0-9]+`

### 6.3 ⚠️ MINEUR: Pas de versioning pour les clés

**Situation:**
- Quand une nouvelle clé Stripe est poussée, l'ancienne est écrasée
- Aucune trace d'historique

**Recommandation (optionnel):**
- Ajouter une colonne `updated_at` dans `settings`
- Loguer les changements de clés sensibles

### 6.4 ✅ CORRECT: Sécurité des clés secrètes

**Points forts:**
- Secret key jamais exposée via GET ✅
- Stockage sécurisé en Supabase (chiffré en transit) ✅
- Authentification par X-API-Key obligatoire ✅
- Comparaison constant-time (prévient timing attacks) ✅

---

## 7. Recommandations

### 7.1 Correctif immédiat (Niveau: FAIBLE)

**Améliorer la validation des clés Stripe:**

```python
# Avant
if not re.match(r'^pk_(test|live)_[A-Za-z0-9]+$', value):

# Après (accepte tirets et underscores)
if not re.match(r'^pk_(test|live)_[A-Za-z0-9_-]+$', value):
```

**Aussi pour secret_key:**
```python
if not re.match(r'^sk_(test|live)_[A-Za-z0-9_-]+$', value):
```

### 7.2 Enhancement optionnel (Niveau: MOYEN)

**Ajouter endpoint pour price_id:**

```python
@app.route('/api/export/settings/stripe_price_id', methods=['PUT'])
@require_api_key
def update_stripe_price_id():
    """
    Permet au Dashboard de propager un price_id Stripe au Template.
    Utile pour les produits Stripe gérés centralement.
    
    Body: {"value": "price_1A4Xc..."}
    """
    api_key = request.headers.get('X-API-Key')
    # Même auth que pour pk/sk
    
    value = request.get_json().get('value')
    
    # Validation loose (juste vérifier que ça ressemble à un price_id)
    if not re.match(r'^(price_)?[A-Za-z0-9_-]+$', value):
        return error("invalid_price_id_format"), 400
    
    # Stocker
    set_setting('stripe_price_id', value)
    return jsonify({'success': True})
```

### 7.3 Logging et monitoring (Niveau: MOYEN)

**Ajouter audit log pour les changements de clés:**

```python
def log_api_change(endpoint, old_value, new_value, source_ip):
    """Log les changements sensibles"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Enregistrer dans un tableau audit (créer si n'existe pas)
    cursor.execute(adapt_query("""
        INSERT INTO api_audit_log (endpoint, changed_at, source_ip)
        VALUES (?, NOW(), ?)
    """), (endpoint, source_ip))
    
    conn.commit()
    conn.close()
```

---

## 8. Checklist de validation

### Infrastructure Stripe
- [x] Clé publishable (pk_) propagée du Dashboard
- [x] Clé secrète (sk_) propagée du Dashboard  
- [x] Clés stockées en Supabase (sécurisé)
- [x] Clé secrète jamais exposée au client
- [x] GET /api/stripe-pk retourne la clé publique
- [x] Authentification X-API-Key obligatoire pour PUT

### Gestion des prix
- [x] Prix SAAS récupérés du Dashboard
- [x] Prix des produits gérés par Template
- [x] Fallback cache en Supabase
- [x] Stripe checkout utilise les prix corrects
- [x] Validation des prix (> 0)

### Sécurité
- [x] Comparaison constant-time (HMAC)
- [x] Validation regex sur les clés
- [x] CORS correct pour /api/stripe-pk
- [x] Pas de logs avec clés complètes
- [x] Timeout sur les requêtes HTTP

### Robustesse
- [x] Fallbacks multiples pour les clés
- [x] Caching local en cas d'indisponibilité Dashboard
- [x] Gestion des erreurs HTTP
- [x] Timeout configurés

---

## 9. Conclusion

### État général: ✅ **ARCHITECTURE CORRECTE**

**Points forts:**
1. Séparation claire des rôles
   - Dashboard: gère les clés Stripe uniquement
   - Template: gère les produits et prix
   
2. Sécurité robuste
   - Clés secrètes jamais exposées
   - Authentification par header X-API-Key
   - Comparaison constant-time
   
3. Pas de transmission de prix du Dashboard au Template
   - Design correct: Template est source de vérité pour ses données
   - Dashboard lit depuis Template, ne pousse pas
   
4. Fallbacks et caching
   - Résilience en cas d'indisponibilité Dashboard
   - Performance optimisée

### Points mineurs à améliorer:
1. ⚠️ Regex de validation trop stricte (refuser les tirets dans les clés)
2. ⚠️ Pas d'endpoint pour propager price_id (optionnel, à ajouter si besoin)
3. ⚠️ Pas d'audit log pour les changements de clés

### Actions recommandées (par priorité):

| Priorité | Action | Risque | Effort |
|----------|--------|--------|--------|
| 🔴 CRITIQUE | - | Aucun | - |
| 🟠 HAUTE | Corriger regex validation | Bas | ~5 min |
| 🟡 MOYENNE | Ajouter endpoint price_id | Très bas | ~30 min |
| 🟢 BASSE | Ajouter audit log | Très bas | ~1h |

---

## 10. Prochaines étapes

1. **Immédiat:** Appliquer le correctif regex (si désiré)
2. **Court terme:** Ajouter support price_id (si besoin du Dashboard)
3. **Moyen terme:** Implémenter audit log pour conformité
4. **Validation:** Tester la propagation Stripe en production

---

**Rapport généré automatiquement.**  
**Prêt pour commit et déploiement.**
