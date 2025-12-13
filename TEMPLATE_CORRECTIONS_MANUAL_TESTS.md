# Tests Manuels - Template Corrections & Dashboard Sync

**Date:** 2025-12-13  
**Corrections appliquées:**
1. ✅ Bouton "Lancer mon site" - Condition preview-
2. ✅ Premier utilisateur = admin automatique
3. ✅ Endpoints export - Audit complet

---

## 📋 Test 1: Bouton "Lancer mon site" disparaît en production

### Objectif
Vérifier que le bouton "🚀 Lancer mon site" s'affiche UNIQUEMENT quand le domaine commence par "preview-"

### Préparation
- Template en local: `http://localhost:5000`
- Template preview: `https://preview-jb.artworksdigital.fr`
- Template prod: `https://jb.artworksdigital.fr`

### Cas 1: En preview (should show button)
```bash
# Terminal
curl -X GET "https://preview-jb.artworksdigital.fr/" -H "Accept: text/html"

# Vérification
❌ ÉCHEC: Bouton visible dans HTML (class="preview-fab")
✅ SUCCÈS: Bouton "🚀 Lancer mon site" présent
```

**Étape manuelle:**
1. Ouvrir `https://preview-jb.artworksdigital.fr` dans le navigateur
2. Vérifier le bouton en bas-gauche
3. Cliquer dessus → devrait ouvrir le formulaire de lancement

### Cas 2: En production (should NOT show button)
```bash
# Terminal
curl -X GET "https://jb.artworksdigital.fr/" -H "Accept: text/html"

# Vérification
❌ ÉCHEC: Bouton visible dans le HTML
✅ SUCCÈS: Pas de bouton "🚀 Lancer mon site"
```

**Étape manuelle:**
1. Ouvrir `https://jb.artworksdigital.fr` dans le navigateur
2. Scroller en bas-gauche
3. Vérifier que le bouton est ABSENT
4. Vérifier que le reste du site fonctionne normalement

### Cas 3: Local dev (should NOT show)
```bash
# Terminal
python app.py
curl -X GET "http://localhost:5000/" -H "Accept: text/html"

# Vérification
✅ SUCCÈS: Pas de bouton en local (localhost n'est pas "preview-")
```

### Code de vérification
```python
# Vérifier la condition dans app.py:2285
conn = get_db()
host = request.host  # Doit être "preview-jb.artworksdigital.fr"
is_preview = (
    host.startswith("preview-")
    or ".preview." in host
    or host.startswith("preview.")
    or "sandbox" in host
)
print(f"Host: {host}, is_preview: {is_preview}")
```

---

## 📋 Test 2: Premier utilisateur devient administrateur

### Objectif
Vérifier que le premier utilisateur inscrit reçoit automatiquement le rôle "admin"

### Préparation
```bash
# 1. Nettoyer la table users (démarrer avec zéro utilisateurs)
psql -U postgres -d artworksdigital -c "DELETE FROM users;"

# 2. Vérifier qu'il n'y a pas d'utilisateurs
psql -U postgres -d artworksdigital -c "SELECT COUNT(*) FROM users;"
# Résultat: 0
```

### Cas 1: Premier utilisateur
**Étapes:**
1. Naviguer vers `https://template.artworksdigital.fr/register`
2. Inscrire un nouvel utilisateur:
   - Nom: "Jean-Baptiste"
   - Email: "admin@example.com"
   - Mot de passe: "Test1234!"
3. Soumettre le formulaire

**Vérifications:**
```bash
# Vérifier en base de données
psql -U postgres -d artworksdigital -c "SELECT id, name, email, role FROM users WHERE email='admin@example.com';"

# Résultat attendu:
# id | name           | email               | role
# 1  | Jean-Baptiste  | admin@example.com   | admin  ← DOIT être "admin"
```

**Vérification via l'API:**
```bash
# 1. Récupérer la clé API
curl -X GET "https://template.artworksdigital.fr/api/export/api-key" \
  -H "Cookie: user_id=1" \
  | jq '.api_key'

# 2. Exporter les utilisateurs
curl -X GET "https://template.artworksdigital.fr/api/export/users" \
  -H "X-API-Key: YOUR_API_KEY" \
  | jq '.users[0]'

# Résultat attendu:
{
  "id": 1,
  "name": "Jean-Baptiste",
  "email": "admin@example.com",
  "create_date": "2025-12-13T12:00:00",
  "role": "admin",
  "site_name": "Jean-Baptiste Art"
}
```

**Vérification dans les logs:**
```
[REGISTER] Premier utilisateur admin@example.com créé avec rôle 'admin'
```

### Cas 2: Deuxième utilisateur
**Étapes:**
1. Naviguer vers `/register`
2. Inscrire un second utilisateur:
   - Nom: "Alice"
   - Email: "alice@example.com"
   - Mot de passe: "Test1234!"
3. Soumettre

**Vérifications:**
```bash
# Vérifier en base de données
psql -U postgres -d artworksdigital -c "SELECT id, name, email, role FROM users;"

# Résultat attendu:
# id | name           | email               | role
# 1  | Jean-Baptiste  | admin@example.com   | admin
# 2  | Alice          | alice@example.com   | user   ← DOIT être "user"
```

### Cas 3: Race condition (simuler 2 inscriptions quasi-simultanées)
```bash
# Terminal 1
curl -X POST "https://template.artworksdigital.fr/register" \
  -d "name=User1&email=user1@example.com&password=Test1234!" &

# Terminal 2 (immédiatement après)
curl -X POST "https://template.artworksdigital.fr/register" \
  -d "name=User2&email=user2@example.com&password=Test1234!" &

wait

# Vérifier que SEULEMENT le premier est admin
psql -U postgres -d artworksdigital -c "SELECT email, role FROM users ORDER BY id;"
# user1@example.com → admin (✅)
# user2@example.com → user (✅)
```

### Vérification du code
```python
# Vérifier app.py:1100-1111
c.execute(adapt_query("SELECT COUNT(*) FROM users"))
user_count = c.fetchone()[0]

is_first_user = (user_count == 0)  # ← Doit être True pour le premier

if is_first_user:
    c.execute(..., (name, email, hashed_password, 'admin'))  # ← 'admin'
    print(f"[REGISTER] Premier utilisateur {email} créé avec rôle 'admin'")
else:
    c.execute(..., (name, email, hashed_password, 'user'))   # ← 'user'
```

---

## 📋 Test 3: Export des données - Peintures

### Objectif
Vérifier que l'endpoint `/api/export/paintings` retourne les données complètes

### Préparation
```bash
# 1. Ajouter une peinture via l'UI admin
# ou via SQL:
psql -U postgres -d artworksdigital -c "
INSERT INTO paintings (name, price, category, technique, year, quantity, status, image, display_order)
VALUES (
  'Tableau Moderne',
  1500.00,
  'Peintures à l''huile',
  'Huile sur toile',
  2024,
  1,
  'Disponible',
  'Images/painting_123.jpg',
  10
);"
```

### Test
```bash
# Récupérer la clé API
export API_KEY=$(curl -s -X GET "https://template.artworksdigital.fr/api/export/api-key" \
  -H "Cookie: user_id=1" \
  | jq -r '.api_key')

# Exporter les peintures
curl -X GET "https://template.artworksdigital.fr/api/export/paintings?limit=200" \
  -H "X-API-Key: $API_KEY" \
  | jq '.paintings[0]'
```

### Vérifications attendues
```json
{
  "id": 1,
  "name": "Tableau Moderne",
  "price": 1500.0,
  "category": "Peintures à l'huile",
  "technique": "Huile sur toile",
  "year": 2024,
  "quantity": 1,
  "status": "Disponible",
  "image": "Images/painting_123.jpg",
  "display_order": 10,
  "site_name": "Jean-Baptiste Art"
}
```

**Validations:**
- ✅ `id` présent (entier)
- ✅ `name` présent et non vide
- ✅ `price` présent et > 0 (float)
- ✅ `category` présent et non vide
- ✅ `image` commence par "Images/"
- ✅ `display_order` présent (entier)
- ✅ `site_name` présent

---

## 📋 Test 4: Export des données - Utilisateurs avec rôles

### Test
```bash
# Exporter les utilisateurs
curl -X GET "https://template.artworksdigital.fr/api/export/users?limit=500" \
  -H "X-API-Key: $API_KEY" \
  | jq '.users'
```

### Vérifications attendues
```json
[
  {
    "id": 1,
    "name": "Jean-Baptiste",
    "email": "admin@example.com",
    "create_date": "2025-12-13T...",
    "role": "admin"
  },
  {
    "id": 2,
    "name": "Alice",
    "email": "alice@example.com",
    "create_date": "2025-12-13T...",
    "role": "user"
  }
]
```

**Validations:**
- ✅ Au moins 2 utilisateurs
- ✅ Premier utilisateur a `role: "admin"`
- ✅ Deuxième utilisateur a `role: "user"`
- ✅ Tous les utilisateurs ont `email`, `create_date`, `name`

---

## 📋 Test 5: Export des données - Commandes

### Préparation
```bash
# Simuler une commande via l'UI
# ou ajouter manuellement:
psql -U postgres -d artworksdigital -c "
INSERT INTO orders (customer_name, email, total_price, status)
VALUES ('Alice Dupont', 'alice@example.com', 1500.00, 'Livrée');
"
```

### Test
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/orders?limit=100" \
  -H "X-API-Key: $API_KEY" \
  | jq '.orders[0]'
```

### Vérifications attendues
```json
{
  "id": 1,
  "customer_name": "Alice Dupont",
  "email": "alice@example.com",
  "total_price": 1500.0,
  "order_date": "2025-12-13T...",
  "status": "Livrée",
  "items": [
    {
      "painting_id": 1,
      "name": "Tableau Moderne",
      "image": "Images/painting_123.jpg",
      "price": 1500.0,
      "quantity": 1
    }
  ]
}
```

**Validations:**
- ✅ `id` présent
- ✅ `customer_name`, `email`, `total_price`, `order_date`, `status` présents
- ✅ `items` est un tableau (peut être vide)
- ✅ Chaque item a `painting_id`, `name`, `image`, `price`, `quantity`

---

## 📋 Test 6: Export des données - Settings

### Test
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/settings" \
  -H "X-API-Key: $API_KEY" \
  | jq '.data[] | select(.key == "site_name")'
```

### Vérifications attendues
```json
{
  "key": "site_name",
  "value": "Jean-Baptiste Art"
}
```

**Validations:**
- ✅ Settings contient `site_name`
- ✅ Settings contient `stripe_publishable_key`
- ✅ Settings contient `saas_site_price_cache`
- ✅ `stripe_secret_key` a valeur `***MASKED***`
- ✅ `export_api_key` a valeur `***MASKED***`

---

## 📋 Test 7: Authentification - Clé API invalide

### Test 1: Sans X-API-Key
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/paintings"
```

**Résultat attendu:**
```json
{
  "error": "invalid_api_key",
  "success": false
}
```
**HTTP Status:** 401

### Test 2: Avec clé invalide
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/paintings" \
  -H "X-API-Key: invalid_key_xyz"
```

**Résultat attendu:** 401

### Test 3: Endpoint public (sans auth)
```bash
curl -X GET "https://template.artworksdigital.fr/api/stripe-pk"
```

**Résultat attendu:** 200 avec `publishable_key`

---

## 📋 Test 8: Sécurité - Secret key jamais exposé

### Test 1: GET secret key (should fail)
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/settings/stripe_secret_key" \
  -H "X-API-Key: $API_KEY"
```

**Résultat attendu:**
```json
{
  "error": "not_found"
}
```
**HTTP Status:** 404

### Test 2: Vérifier que PUT marche
```bash
curl -X PUT "https://template.artworksdigital.fr/api/export/settings/stripe_secret_key" \
  -H "X-API-Key: TEMPLATE_MASTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": "sk_test_abc123"}'
```

**Résultat attendu:** 200

### Test 3: Vérifier qu'on ne peut pas le relire
```bash
curl -X GET "https://template.artworksdigital.fr/api/export/settings/stripe_secret_key"
```

**Résultat attendu:** 404

---

## 📋 Test 9: Pagination des données

### Test
```bash
# Page 1 (0-50)
curl -X GET "https://template.artworksdigital.fr/api/export/paintings?limit=50&offset=0" \
  -H "X-API-Key: $API_KEY" \
  | jq '.count'

# Page 2 (50-100)
curl -X GET "https://template.artworksdigital.fr/api/export/paintings?limit=50&offset=50" \
  -H "X-API-Key: $API_KEY" \
  | jq '.count'
```

**Vérifications:**
- ✅ Première page retourne jusqu'à 50 résultats
- ✅ Deuxième page retourne les 50 suivants
- ✅ Pas de doublon entre pages

---

## 📋 Test 10: Intégration Dashboard

### Préparation
```bash
# Créer un site test sur le Dashboard
# URL Template: https://template.artworksdigital.fr
# API Key: (copier depuis le Template)
```

### Test 1: Synchronisation manuelle
```bash
# Appel API Dashboard
curl -X POST "https://dashboard.artworksdigital.fr/api/sync/template/site-001" \
  -H "Authorization: Bearer YOUR_DASHBOARD_TOKEN" \
  | jq '.'
```

**Résultat attendu:**
```json
{
  "success": true,
  "timestamp": "2025-12-13T12:00:00",
  "summary": {
    "paintings": {
      "success": true,
      "count": 5
    },
    "users": {
      "success": true,
      "count": 2
    },
    "orders": {
      "success": true,
      "count": 1
    },
    "settings": {
      "success": true,
      "count": 35
    }
  },
  "log": [
    {
      "entity": "paintings",
      "level": "SUCCESS",
      "message": "5/5 peintures synchronisées"
    },
    ...
  ]
}
```

### Test 2: Vérifier l'affichage
1. Ouvrir `https://dashboard.artworksdigital.fr/sites/site-001/paintings`
2. Vérifier que les 5 peintures du Template sont affichées
3. Cliquer sur une peinture → détails complets
4. Vérifier l'image s'affiche (`/static/Images/painting_123.jpg`)

### Test 3: Vérifier les utilisateurs
1. Ouvrir `https://dashboard.artworksdigital.fr/sites/site-001/users`
2. Vérifier que "Jean-Baptiste" a le badge "admin"
3. Vérifier que "Alice" a le badge "user"

---

## 🎯 Checklist finale

- [ ] Bouton "Lancer mon site" visible en preview
- [ ] Bouton "Lancer mon site" absent en production
- [ ] Premier utilisateur a rôle "admin"
- [ ] Deuxième utilisateur a rôle "user"
- [ ] Export peintures complet (id, name, price, image, etc.)
- [ ] Export utilisateurs avec rôles
- [ ] Export commandes avec items
- [ ] Export settings sans secrets masqués
- [ ] Secret key jamais exposé en GET
- [ ] Authentification X-API-Key requise
- [ ] Endpoints publics accessibles sans auth
- [ ] Pagination fonctionne
- [ ] Dashboard synchronise les données
- [ ] Images s'affichent correctement
- [ ] Rôles admin/user affichés correctement
- [ ] Logs de synchronisation visibles
- [ ] Pas d'erreurs en production

---

## 📝 Rapporter les résultats

Créer un fichier `TEST_RESULTS.md`:

```markdown
# Résultats des tests

## ✅ Réussis
- [x] Bouton preview disparaît en production
- [x] Premier utilisateur est admin
- [x] Export peintures complet
- ...

## ❌ Échoués
- [ ] API key validation
- [ ] Image path incorrect
- ...

## ⚠️ À vérifier
- [ ] Pagination limit=0
- [ ] Très grands datasets
- ...

## Notes
- Toutes les données exportées correctement
- Images servies avec le bon chemin
- Sécurité validée (secrets masqués)
```

