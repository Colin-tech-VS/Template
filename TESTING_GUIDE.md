# Guide de test pour les corrections de sécurité

## Configuration préalable

1. **Créer un fichier .env local** :
```bash
cp .env.example .env
```

2. **Définir les variables d'environnement requises** :
```bash
# Clé API maître (pour le dashboard)
TEMPLATE_MASTER_API_KEY=votre-cle-master-unique

# Clé secrète Flask (IMPORTANT pour la production)
FLASK_SECRET=votre-cle-secrete-tres-longue-et-aleatoire

# Configuration SMTP (optionnel pour les tests)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=votre.email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe_application

# Email administrateur
ADMIN_EMAIL=admin@example.com
```

## Tests des endpoints API

### 1. Test de l'API Key Authentication

#### a) Test avec la clé maître (TEMPLATE_MASTER_API_KEY)
```bash
# Définir la clé
MASTER_KEY="votre-cle-master-unique"

# Test endpoint orders
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/orders
```

**Résultat attendu** : Code 200, liste des commandes avec items et site_name

#### b) Test sans API key
```bash
curl http://localhost:5000/api/export/orders
```

**Résultat attendu** : Code 401, `{"error": "API key manquante"}`

#### c) Test avec API key invalide
```bash
curl -H "X-API-Key: invalid-key" \
  http://localhost:5000/api/export/orders
```

**Résultat attendu** : Code 403, `{"error": "API key invalide"}`

### 2. Test de l'endpoint /api/export/orders

#### a) Test basique (sans pagination)
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/orders
```

**Vérifications** :
- Chaque commande contient : id, customer_name, email, total_price, order_date, status
- Chaque commande a une clé 'items' avec les détails des peintures
- Chaque commande a 'site_name'
- Le champ 'pagination' est présent avec page, per_page, total, pages

#### b) Test avec pagination
```bash
# Page 1, 10 résultats par page
curl -H "X-API-Key: $MASTER_KEY" \
  "http://localhost:5000/api/export/orders?page=1&per_page=10"

# Page 2
curl -H "X-API-Key: $MASTER_KEY" \
  "http://localhost:5000/api/export/orders?page=2&per_page=10"
```

**Vérifications** :
- La pagination fonctionne correctement
- Le nombre de commandes par page ne dépasse pas la limite demandée
- Les métadonnées de pagination sont correctes

### 3. Test de l'endpoint /api/stripe-pk

#### a) Test de récupération de clé publishable
```bash
curl http://localhost:5000/api/stripe-pk
```

**Résultat attendu** : 
- Code 200 avec `{"success": true, "publishable_key": "pk_..."}`
- OU Code 404 avec `{"success": false, "message": "no_publishable_key"}`

#### b) Vérification de sécurité
```bash
# S'assurer qu'aucune clé secrète (sk_) ou restreinte (rk_) n'est jamais exposée
# Vérifier les logs pour le message [SECURITY]
```

**Vérifications** :
- Aucune clé commençant par 'sk_' ou 'rk_' ne doit être retournée
- Les logs doivent afficher un message de sécurité si tentative d'exposition

### 4. Test des autres endpoints API

#### a) Test /api/export/full
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/full
```

**Résultat attendu** : Export complet de toutes les tables

#### b) Test /api/export/paintings
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/paintings
```

**Résultat attendu** : Liste des peintures avec site_name

#### c) Test /api/export/users
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/users
```

**Résultat attendu** : Liste des utilisateurs (sans mots de passe) avec site_name

#### d) Test /api/export/settings
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/settings
```

**Résultat attendu** : Paramètres avec clés sensibles masquées (***MASKED***)

### 5. Test de la configuration via paramètre

#### a) Test PUT /api/export/settings/:key
```bash
# Mettre à jour un paramètre
curl -X PUT \
  -H "X-API-Key: $MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": "Mon Site Artiste"}' \
  http://localhost:5000/api/export/settings/site_name
```

**Résultat attendu** : Code 200, `{"success": true, "message": "Paramètre site_name mis à jour"}`

#### b) Vérifier la mise à jour
```bash
curl -H "X-API-Key: $MASTER_KEY" \
  http://localhost:5000/api/export/settings | grep site_name
```

## Tests de sécurité

### 1. Vérification des credentials
```bash
# S'assurer qu'aucun credential n'est codé en dur
grep -r "coco.cayre@" app.py || echo "✅ Pas d'email hardcodé trouvé"
grep -r "motdepassepardefaut" app.py || echo "✅ Pas de mot de passe hardcodé trouvé"
grep -r "psgk wjhd" app.py || echo "✅ Pas de token Gmail hardcodé trouvé"
```

### 2. Vérification de la secret_key Flask
```bash
# Lancer l'app et vérifier les logs
python app.py 2>&1 | grep "secret_key"
```

**Résultats attendus** :
- Avec FLASK_SECRET défini : "🔐 Flask secret_key configurée depuis l'environnement"
- Sans FLASK_SECRET : "⚠️  Flask secret_key générée aléatoirement - Les sessions seront réinitialisées au redémarrage!"

### 3. Vérification de la configuration SMTP
```bash
# Vérifier que les credentials SMTP ne sont pas en clair
python app.py 2>&1 | grep "SMTP configuré"
```

**Résultat attendu** : Affichage avec indicateurs ✓ ou ✗ pour user/pass

## Tests fonctionnels

### 1. Test du mode preview
```bash
# Tester avec paramètre preview
curl "http://localhost:5000/?preview=true"
curl "http://localhost:5000/?preview=1"
curl "http://localhost:5000/?preview=on"
```

**Vérification** : Les logs doivent afficher "[DEBUG] is_preview_request - Mode preview détecté"

### 2. Test de récupération des prix
Vérifier dans les logs que `fetch_dashboard_site_price` accepte différents noms de champs:
- price
- site_price
- artwork_price
- basePrice
- base_price

## Résumé des corrections appliquées

✅ **Sécurité** :
1. Secret key Flask depuis environnement (FLASK_SECRET/SECRET_KEY)
2. Credentials SMTP depuis environnement (MAIL_USERNAME/MAIL_PASSWORD)
3. Admin email configurable (ADMIN_EMAIL)
4. Validation des clés Stripe (blocage sk_ et rk_)
5. API key avec priorité TEMPLATE_MASTER_API_KEY

✅ **Fonctionnalités** :
1. Route /api/export/orders corrigée avec JOIN et gestion curseur
2. Pagination sur /api/export/orders (max 500)
3. Support de différents noms de champs pour prix et clés Stripe
4. Logs DEBUG améliorés

✅ **Code Quality** :
1. Constantes SMTP pour éviter duplication
2. Gestion d'erreurs améliorée
3. Documentation .env.example complète
4. Messages d'avertissement pour config auto-générée

## Commandes curl de test rapide

```bash
# Export des variables
export MASTER_KEY="votre-cle-master-unique"
export BASE_URL="http://localhost:5000"

# Tests rapides
echo "Test 1: Stats"
curl -s -H "X-API-Key: $MASTER_KEY" $BASE_URL/api/export/stats | jq .

echo "Test 2: Orders (page 1)"
curl -s -H "X-API-Key: $MASTER_KEY" "$BASE_URL/api/export/orders?page=1&per_page=5" | jq .

echo "Test 3: Stripe PK"
curl -s $BASE_URL/api/stripe-pk | jq .

echo "Test 4: Settings"
curl -s -H "X-API-Key: $MASTER_KEY" $BASE_URL/api/export/settings | jq .

echo "✅ Tests terminés"
```
