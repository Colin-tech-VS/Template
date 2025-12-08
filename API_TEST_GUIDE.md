# Guide de test des endpoints API - Template

Ce document fournit des exemples de commandes curl pour tester tous les endpoints modifiés.

## Configuration préalable

1. Démarrez l'application Flask :
```bash
python app.py
```

2. Définissez votre clé API maître :
```bash
export TEMPLATE_MASTER_API_KEY="template-master-key-2025"
```

## 1. Test de l'endpoint /api/export/orders

### Récupérer toutes les commandes avec leurs items

```bash
# Avec clé API dans le header (recommandé)
curl -X GET http://localhost:5000/api/export/orders \
  -H "X-API-Key: template-master-key-2025"

# Avec clé API en paramètre
curl -X GET "http://localhost:5000/api/export/orders?api_key=template-master-key-2025"
```

**Réponse attendue :**
```json
{
  "orders": [
    {
      "id": 1,
      "customer_name": "John Doe",
      "email": "john@example.com",
      "total_price": 150.00,
      "order_date": "2025-01-15 10:30:00",
      "status": "En cours",
      "site_name": "Site Artiste",
      "items": [
        {
          "painting_id": 5,
          "name": "Peinture XYZ",
          "image": "Images/painting.jpg",
          "price": 150.00,
          "quantity": 1
        }
      ]
    }
  ]
}
```

### Test avec clé API invalide (devrait retourner 403)

```bash
curl -X GET http://localhost:5000/api/export/orders \
  -H "X-API-Key: invalid-key"
```

**Réponse attendue :**
```json
{
  "error": "API key invalide"
}
```

## 2. Test de l'endpoint /api/stripe-pk

### Récupérer la clé publishable Stripe

```bash
curl -X GET http://localhost:5000/api/stripe-pk
```

**Réponses possibles :**

**Succès (clé trouvée) :**
```json
{
  "success": true,
  "publishable_key": "pk_test_51..."
}
```

**Pas de clé configurée :**
```json
{
  "success": false,
  "message": "no_publishable_key"
}
```

**Vérification de sécurité :** La clé retournée ne doit JAMAIS commencer par `sk_` (clé secrète).

## 3. Test des autres endpoints d'export

### Récupérer tous les utilisateurs

```bash
curl -X GET http://localhost:5000/api/export/users \
  -H "X-API-Key: template-master-key-2025"
```

### Récupérer toutes les peintures

```bash
curl -X GET http://localhost:5000/api/export/paintings \
  -H "X-API-Key: template-master-key-2025"
```

### Récupérer toutes les expositions

```bash
curl -X GET http://localhost:5000/api/export/exhibitions \
  -H "X-API-Key: template-master-key-2025"
```

### Récupérer les demandes personnalisées

```bash
curl -X GET http://localhost:5000/api/export/custom-requests \
  -H "X-API-Key: template-master-key-2025"
```

### Récupérer les statistiques

```bash
curl -X GET http://localhost:5000/api/export/stats \
  -H "X-API-Key: template-master-key-2025"
```

### Export complet de toutes les données

```bash
curl -X GET http://localhost:5000/api/export/full \
  -H "X-API-Key: template-master-key-2025"
```

## 4. Test de modification de paramètres

### Mettre à jour un paramètre via l'API

```bash
curl -X PUT http://localhost:5000/api/export/settings/site_name \
  -H "X-API-Key: template-master-key-2025" \
  -H "Content-Type: application/json" \
  -d '{"value": "Mon Nouveau Site"}'
```

**Réponse attendue :**
```json
{
  "success": true,
  "message": "Paramètre site_name mis à jour"
}
```

### Mettre à jour la clé publishable Stripe

```bash
curl -X PUT http://localhost:5000/api/export/settings/stripe_publishable_key \
  -H "X-API-Key: template-master-key-2025" \
  -H "Content-Type: application/json" \
  -d '{"value": "pk_test_51..."}'
```

## 5. Tests de sécurité à vérifier

### ✅ Tests qui doivent RÉUSSIR :

1. Accès avec clé maître TEMPLATE_MASTER_API_KEY
2. Accès avec clé export_api_key générée automatiquement
3. /api/stripe-pk accessible sans authentification (public)
4. Clés publishable Stripe accessibles côté client

### ❌ Tests qui doivent ÉCHOUER :

1. Accès aux endpoints /api/export/* sans clé API → 401
2. Accès avec clé API invalide → 403
3. /api/stripe-pk ne doit JAMAIS retourner une clé commençant par `sk_`
4. Aucune clé secrète dans les logs ou réponses

## 6. Test du mode preview

### Vérifier la détection du mode preview

```bash
# Via paramètre URL
curl -X GET "http://localhost:5000/?preview=true"

# Via hostname (nécessite configuration DNS ou /etc/hosts)
curl -X GET http://preview.example.com/
```

## 7. Variables d'environnement à tester

### Configuration minimale pour les tests

Créez un fichier `.env` :
```bash
TEMPLATE_MASTER_API_KEY=template-master-key-2025
FLASK_SECRET=test-secret-key-do-not-use-in-prod
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=test@example.com
MAIL_PASSWORD=test-password
ADMIN_EMAIL=admin@example.com
```

### Vérifier que les variables sont bien chargées

```bash
# Démarrez l'application et vérifiez les logs
python app.py

# Vous devriez voir dans les logs :
# 🔑 Clé maître dashboard chargée: template-m...y-2025
# SMTP_SERVER : smtp.gmail.com
# SMTP_PORT   : 587
# SMTP_USER   : test@example.com
# SMTP_PASSWORD défini : True
```

## 8. Test d'intégration complet

### Script de test automatisé

```bash
# Utiliser le script de test fourni
python test_fixes.py
```

Ce script vérifie :
- ✓ Configuration Flask (secret key, SMTP)
- ✓ Authentification API key
- ✓ Sécurité des clés Stripe
- ✓ Logique preview
- ✓ Syntaxe SQL
- ✓ Endpoints API

## 9. Tests spécifiques PostgreSQL

Si vous utilisez PostgreSQL (via DATABASE_URL), vérifiez que :

1. Les requêtes utilisent `%s` au lieu de `?` (fait automatiquement par `adapt_query`)
2. Les types `SERIAL` sont utilisés au lieu de `AUTOINCREMENT`
3. Les JOINs fonctionnent correctement

```bash
# Vérifier la connexion PostgreSQL
python -c "from database import IS_POSTGRES; print('Using PostgreSQL:', IS_POSTGRES)"
```

## 10. Monitoring et logs

### Activer les logs de debug

Les logs de debug sont maintenant intégrés. Surveillez la console pour :

```
[DEBUG] require_api_key: Clé maître validée
[DEBUG] /api/export/orders: Début récupération des commandes
[DEBUG] /api/export/orders: 5 commandes récupérées
[DEBUG] /api/stripe-pk: Recherche de la clé publishable Stripe
[DEBUG] fetch_dashboard_site_price: Prix trouvé (price) = 99.0
[DEBUG] is_preview_request: host=example.com, preview_param=, result=False
```

## Troubleshooting

### Problème : "API key manquante"
**Solution :** Ajoutez le header `X-API-Key` ou le paramètre `api_key`

### Problème : "API key invalide"
**Solution :** Vérifiez que vous utilisez la bonne clé (TEMPLATE_MASTER_API_KEY ou export_api_key)

### Problème : "no_publishable_key"
**Solution :** Configurez stripe_publishable_key dans la table settings ou STRIPE_PUBLISHABLE_KEY en env

### Problème : Erreur de connexion à la base de données
**Solution :** Vérifiez que les migrations sont exécutées (`migrate_db()` au démarrage)

## Sécurité - Checklist finale

- [ ] Aucun mot de passe en clair dans app.py
- [ ] app.secret_key utilise FLASK_SECRET ou SECRET_KEY depuis env
- [ ] Toutes les configs SMTP utilisent des variables d'environnement
- [ ] Les clés Stripe secrètes (sk_*) ne sont jamais exposées côté client
- [ ] Les endpoints /api/export/* nécessitent une authentification
- [ ] Les logs ne contiennent pas de secrets complets
- [ ] Le fichier .env est dans .gitignore
- [ ] La documentation recommande des clés fortes en production
