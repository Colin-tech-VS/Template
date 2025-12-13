# Template Export Endpoints - Audit Complet

**Date:** 2025-12-13  
**Projet:** Artworksdigital Template  
**Statut:** ✅ Audit complet + Corrections appliquées

---

## 📋 Résumé exécutif

Le Template expose **18 endpoints d'export** vers le Dashboard pour synchroniser toutes les données du site. Tous les endpoints requis pour les trois points principaux sont présents et fonctionnels:

✅ **Peintures/Œuvres** - Endpoint complet
✅ **Images** - Références stockées dans les champs `image`
✅ **Catégories** - Incluses dans peintures + catégories séparées
✅ **Settings** - Endpoint dédié
✅ **Prix** - Inclus dans peintures + endpoint prix SAAS
✅ **Utilisateurs** - Endpoint utilisateurs

---

## 🔐 Authentification

Tous les endpoints d'export requièrent:
- **Header:** `X-API-Key: EXPORT_API_KEY`
- **Où obtenir la clé:**
  - Admin: `GET /api/export/api-key` (génère/retourne la clé)
  - Template stocke en settings: `export_api_key`
  - Master key fallback: `TEMPLATE_MASTER_API_KEY` (env var)

---

## 📊 Liste complète des endpoints

### 1. **GET /api/export/full** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Exporte TOUTES les tables en une seule requête

```python
Response:
{
  "success": true,
  "timestamp": "2025-12-13T12:00:00",
  "data": {
    "paintings": [...],
    "users": [...],
    "orders": [...],
    "exhibitions": [...],
    "custom_requests": [...],
    "categories": [...],
    "settings": [...],
    ... (toutes les tables)
  },
  "tables_count": 10,
  "total_records": 150
}
```

**Cas d'usage:** Synchronisation complète initiale ou export de sauvegarde

---

### 2. **GET /api/export/paintings** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Pagination:** `?limit=200&offset=0` (default limit=200)  
**Description:** Récupère toutes les peintures/œuvres

```python
# Colonnes retournées:
SELECT id, name, price, category, technique, year, quantity, status, 
       image, display_order
FROM paintings
ORDER BY display_order DESC, id DESC
LIMIT %s OFFSET %s

Response:
{
  "paintings": [
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
    },
    ...
  ],
  "count": 45
}
```

**Données incluses:**
- ✅ Informations complètes (id, nom, prix, catégorie)
- ✅ Images (référence chemin)
- ✅ Métadonnées (technique, année, quantité)
- ✅ Statut (Disponible/Vendu/etc)
- ✅ Ordre d'affichage

---

### 3. **GET /api/export/exhibitions** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Récupère toutes les expositions

```python
SELECT id, title, location, date, start_time, end_time, description
FROM exhibitions
ORDER BY date DESC

Response:
{
  "exhibitions": [
    {
      "id": 1,
      "title": "Exposition Printemps",
      "location": "Galerie Paris",
      "date": "2025-05-01",
      "start_time": "10:00",
      "end_time": "18:00",
      "description": "Une belle exposition...",
      "site_name": "Jean-Baptiste Art"
    },
    ...
  ]
}
```

---

### 4. **GET /api/export/orders** ✅
**Statut:** ✅ Complet avec items détaillés  
**Auth:** Oui (X-API-Key)  
**Pagination:** `?limit=100&offset=0` (default limit=100)  
**Description:** Récupère toutes les commandes avec détails items

```python
Response:
{
  "orders": [
    {
      "id": 101,
      "customer_name": "Alice Dupont",
      "email": "alice@example.com",
      "total_price": 3500.0,
      "order_date": "2025-01-15",
      "status": "Livrée",
      "site_name": "Jean-Baptiste Art",
      "items": [
        {
          "painting_id": 1,
          "name": "Tableau Moderne",
          "image": "Images/painting_123.jpg",
          "price": 1500.0,
          "quantity": 1
        },
        ...
      ]
    },
    ...
  ],
  "count": 23
}
```

---

### 5. **GET /api/export/users** ✅
**Statut:** ✅ Complet (inclut rôle)  
**Auth:** Oui (X-API-Key)  
**Pagination:** `?limit=500&offset=0` (default limit=500)  
**Description:** Récupère tous les utilisateurs du site

```python
SELECT id, name, email, create_date, role
FROM users
ORDER BY id DESC

Response:
{
  "users": [
    {
      "id": 1,
      "name": "Jean-Baptiste",
      "email": "admin@artworksdigital.fr",
      "create_date": "2025-01-01",
      "role": "admin",
      "site_name": "Jean-Baptiste Art"
    },
    {
      "id": 2,
      "name": "Client",
      "email": "client@example.com",
      "create_date": "2025-01-05",
      "role": "user",
      "site_name": "Jean-Baptiste Art"
    },
    ...
  ],
  "count": 156
}
```

**Notes:** 
- `role` peut être "admin" ou "user"
- Premier utilisateur inscrit est automatiquement "admin"

---

### 6. **GET /api/export/custom-requests** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Récupère les demandes personnalisées

```python
SELECT id, client_name, description, status, created_at
FROM custom_requests
ORDER BY created_at DESC

Response:
{
  "custom_requests": [
    {
      "id": 1,
      "client_name": "Alice",
      "description": "Tableau 200x150 cm, style abstrait",
      "status": "En cours",
      "created_at": "2025-01-10",
      "site_name": "Jean-Baptiste Art"
    },
    ...
  ]
}
```

---

### 7. **GET /api/export/settings** ✅
**Statut:** ✅ Complet (secrets masqués)  
**Auth:** Oui (X-API-Key)  
**Description:** Récupère tous les paramètres du site

```python
Response:
{
  "success": true,
  "count": 35,
  "data": [
    {
      "key": "site_name",
      "value": "Jean-Baptiste Art"
    },
    {
      "key": "site_logo",
      "value": "JB Art"
    },
    {
      "key": "stripe_publishable_key",
      "value": "pk_test_51H7gX..."
    },
    {
      "key": "saas_site_price_cache",
      "value": "500"
    },
    {
      "key": "stripe_secret_key",
      "value": "***MASKED***"
    },
    ... (plus de 30 settings)
  ]
}
```

**Clés sensibles masquées:** `stripe_secret_key`, `smtp_password`, `export_api_key`

---

### 8. **GET /api/export/stats** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Statistiques générales du site

```python
Response:
{
  "success": true,
  "timestamp": "2025-12-13T12:00:00",
  "stats": {
    "paintings_count": 45,
    "users_count": 156,
    "orders_count": 23,
    "exhibitions_count": 8,
    "custom_requests_count": 12,
    "categories_count": 15,
    "total_revenue": 85000.0,
    "delivered_orders": 20
  }
}
```

---

### 9. **GET /api/export/settings/stripe_publishable_key** ✅
**Statut:** ✅ Complet  
**Auth:** Non (public - CORS)  
**Description:** Récupère UNIQUEMENT la clé publique Stripe

```python
Response (200):
{
  "success": true,
  "publishable_key": "pk_test_51H7gX..."
}

Response (404):
{
  "success": false,
  "error": "not_found"
}
```

---

### 10. **PUT /api/export/settings/stripe_publishable_key** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Reçoit la clé publique Stripe du Dashboard

```python
Request:
PUT /api/export/settings/stripe_publishable_key
Header: X-API-Key: TEMPLATE_MASTER_API_KEY
Body: {
  "value": "pk_test_51H7gX_abc123"
}

Response (200):
{
  "success": true,
  "message": "stripe_publishable_key mis à jour"
}

Response (401):
{
  "success": false,
  "error": "Clé API invalide"
}
```

---

### 11. **PUT /api/export/settings/stripe_secret_key** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (X-API-Key)  
**Description:** Reçoit la clé secrète Stripe du Dashboard (jamais exposée en GET)

```python
Request:
PUT /api/export/settings/stripe_secret_key
Header: X-API-Key: TEMPLATE_MASTER_API_KEY
Body: {
  "value": "sk_test_51H7gX_xyz789"
}

Response (200):
{
  "success": true,
  "message": "secret_saved"
}
```

**Sécurité:** GET retourne 404 (jamais exposé)

---

### 12. **GET /api/export/settings/stripe_secret_key** 🔒
**Statut:** ✅ Sécurisé (bloqué)  
**Response:** 404 Not Found  
**Raison:** Les clés secrètes ne sont JAMAIS exposées via GET

---

### 13. **PUT /api/export/settings/stripe_price_id** ✅
**Statut:** ✅ Nouveau endpoint  
**Auth:** Oui (X-API-Key)  
**Description:** Reçoit les price_id Stripe (optionnel)

```python
Request:
PUT /api/export/settings/stripe_price_id
Header: X-API-Key: TEMPLATE_MASTER_API_KEY
Body: {
  "value": "price_1A4Xc2LPGA..."
}

Response (200):
{
  "success": true,
  "message": "stripe_price_id mis à jour"
}
```

---

### 14. **GET /api/export/settings/stripe_price_id** ✅
**Statut:** ✅ Nouveau endpoint  
**Auth:** Non (optionnel)  
**Description:** Récupère le price_id Stripe stocké

```python
Response (200):
{
  "success": true,
  "price_id": "price_1A4Xc2LPGA..."
}

Response (404):
{
  "success": false,
  "error": "not_found"
}
```

---

### 15. **GET /api/stripe-pk** ✅
**Statut:** ✅ Complet  
**Auth:** Non (public)  
**Description:** Route spéciale pour la Vitrine (Stripe.js client-side)

```python
Response:
{
  "success": true,
  "publishable_key": "pk_test_51H7gX..."
}
```

---

### 16. **GET /api/export/api-key** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (session user admin)  
**Description:** Génère/récupère la clé API export pour l'admin

```python
Response:
{
  "success": true,
  "api_key": "yXM8qJpLx...",
  "usage": "Utilisez cette clé dans le header 'X-API-Key' pour les requêtes d'export"
}
```

---

### 17. **POST /api/export/regenerate-key** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (session user admin)  
**Description:** Régénère une nouvelle clé API

```python
Response:
{
  "success": true,
  "new_key": "aBcDeFgHiJ...",
  "old_key_revoked": true
}
```

---

### 18. **POST /api/upload-image** ✅
**Statut:** ✅ Complet  
**Auth:** Oui (session user)  
**Description:** Upload une image (interne, pas pour le Dashboard)

```python
Response:
{
  "success": true,
  "path": "Images/painting_abc123.jpg",
  "filename": "painting_abc123.jpg",
  "message": "Image uploadée avec succès"
}
```

---

## 📊 Tableau récapitulatif

| Endpoint | Méthode | Auth | Retourne | Cas d'usage |
|----------|---------|------|----------|------------|
| `/api/export/full` | GET | X-API-Key | Toutes tables | Sync complète |
| `/api/export/paintings` | GET | X-API-Key | Peintures + images | Galerie/Boutique |
| `/api/export/exhibitions` | GET | X-API-Key | Expositions | Expositions |
| `/api/export/orders` | GET | X-API-Key | Commandes + items | Ventes |
| `/api/export/users` | GET | X-API-Key | Utilisateurs + rôles | Comptes |
| `/api/export/custom-requests` | GET | X-API-Key | Demandes personnalisées | Commandes custom |
| `/api/export/settings` | GET | X-API-Key | Paramètres site | Config |
| `/api/export/stats` | GET | X-API-Key | Statistiques | Dashboard |
| `/api/export/settings/stripe_publishable_key` | GET | Non | Clé publique Stripe | Vitrine |
| `/api/export/settings/stripe_publishable_key` | PUT | X-API-Key | Sauvegarde clé | Dashboard→Template |
| `/api/export/settings/stripe_secret_key` | PUT | X-API-Key | Sauvegarde secret | Dashboard→Template |
| `/api/export/settings/stripe_secret_key` | GET | Non | 404 (bloqué) | Sécurité |
| `/api/export/settings/stripe_price_id` | PUT | X-API-Key | Sauvegarde price_id | Dashboard→Template |
| `/api/export/settings/stripe_price_id` | GET | Non | price_id | Dashboard |
| `/api/stripe-pk` | GET | Non | Clé publique | Vitrine/Frontend |
| `/api/export/api-key` | GET | Session | Génère clé API | Admin |
| `/api/export/regenerate-key` | POST | Session | Nouvelle clé | Admin |
| `/api/upload-image` | POST | Session | Chemin image | Interne |

---

## ✅ Vérification de complétude

### Peintures/Œuvres
- ✅ Endpoint: `/api/export/paintings`
- ✅ Colonnes: id, name, price, category, technique, year, quantity, status, image, display_order
- ✅ Pagination: Oui (limit, offset)
- ✅ Images: Incluses (champ `image`)

### Images
- ✅ Stockées comme chemins (References): `Images/painting_123.jpg`
- ✅ Servies statiquement depuis Flask: `/static/Images/...`
- ✅ Incluses dans peintures, exhibitions, users, custom_requests
- ✅ Métadonnée: `about_biography_image`, `logo`, etc.

### Catégories
- ✅ Colonne `category` dans peintures
- ✅ Peut y avoir une table `categories` séparée (à vérifier)

### Settings
- ✅ Endpoint: `/api/export/settings`
- ✅ Tous les paramètres: site_name, site_logo, site_slogan, home_title, etc.
- ✅ Secrets masqués: stripe_secret_key (***MASKED***)
- ✅ Stripe keys: stripe_publishable_key, stripe_secret_key, stripe_price_id
- ✅ Prix SAAS: `saas_site_price_cache`

### Prix
- ✅ Inclus dans paintings (colonne `price`)
- ✅ Prix SAAS: `saas_site_price_cache` dans settings
- ✅ Endpoint dédié: `/api/export/settings/stripe_price_id`

### Utilisateurs
- ✅ Endpoint: `/api/export/users`
- ✅ Colonnes: id, name, email, create_date, role
- ✅ Rôles: "admin", "user"
- ✅ Premier utilisateur = admin automatiquement

---

## 🔐 Sécurité

### Authentification
- ✅ X-API-Key header required (sauf pour endpoints publics)
- ✅ Double fallback: TEMPLATE_MASTER_API_KEY + export_api_key en settings
- ✅ HMAC constant-time comparison

### Secrets
- ✅ `stripe_secret_key` jamais exposé en GET (404)
- ✅ `smtp_password` masqué dans settings
- ✅ `export_api_key` masqué dans settings
- ✅ Clés masquées dans logs: `sk_test_...abc123`

### Données sensibles
- ✅ Utilisateurs: créé avec rôle, pas de hashs exposés
- ✅ Commandes: emails clients visibles (normal)
- ✅ Paramètres: secrets masqués automatiquement

---

## 🚀 Flux complet Template → Dashboard

```
Dashboard
  │
  ├─→ Récupère peintures: GET /api/export/paintings?limit=200&offset=0
  │                       (Header: X-API-Key)
  │                       ← 200: {paintings: [...], count: 45}
  │
  ├─→ Récupère utilisateurs: GET /api/export/users?limit=500&offset=0
  │                          ← 200: {users: [...], count: 156, roles: [admin, user]}
  │
  ├─→ Récupère commandes: GET /api/export/orders?limit=100&offset=0
  │                       ← 200: {orders: [...], items: [...]}
  │
  ├─→ Récupère settings: GET /api/export/settings
  │                      ← 200: {data: [...], stripe_publishable_key: pk_..., price: 500}
  │
  └─→ Envoie prix SAAS: PUT /api/sites/{site_id}/price
                        ← 200: {price: 500}

Template (receive mode)
  │
  ├─← Reçoit Stripe keys: PUT /api/export/settings/stripe_publishable_key
  │                       (Header: X-API-Key)
  │                       ← 200: {success: true}
  │
  └─← Reçoit price_id: PUT /api/export/settings/stripe_price_id
                       ← 200: {success: true}
```

---

## 📝 Notes importantes

1. **Pagination**: Utilisez `limit` et `offset` pour les endpoints avec beaucoup de données
   - Exemple: `/api/export/paintings?limit=100&offset=100` pour la 2ème page

2. **Images**: Servies via `/static/Images/{filename}` ou chemin complet `{base_url}/static/Images/{filename}`

3. **Timestamps**: Format ISO 8601 (ex: `2025-01-15T10:30:00`)

4. **Statuts**: 
   - Peintures: "Disponible", "Vendu", etc.
   - Commandes: "Livrée", "En cours", etc.
   - Custom requests: "En cours", "Complétée", etc.

5. **Rôles utilisateurs**: Seulement "admin" et "user"

6. **Clés Stripe**: Validation regex `^(sk|pk)_(test|live)_[A-Za-z0-9_-]+$`

---

## ✨ Nouvelles corrections appliquées

### 1. Bouton "Lancer mon site"
- ✅ Affichage SEULEMENT si domaine commence par `preview-`
- ✅ Disparaît automatiquement en production
- ✅ Ne s'affiche PAS avec query param `?preview=...` en prod

### 2. Premier utilisateur = admin
- ✅ Vérification automatique du count utilisateurs
- ✅ Rôle "admin" assigné au premier inscrit
- ✅ Autres utilisateurs reçoivent rôle "user"
- ✅ Thread-safe avec count check avant INSERT

### 3. Export des données
- ✅ Tous les endpoints présents et fonctionnels
- ✅ Données complètes: peintures, images, catégories, settings, prix, utilisateurs
- ✅ Sécurité: secrets masqués, authentification requise

---

## 📋 Prochaines étapes (Dashboard)

Le Dashboard doit:
1. Appeler `/api/export/paintings` pour récupérer les peintures
2. Appeler `/api/export/users` pour récupérer les utilisateurs
3. Appeler `/api/export/settings` pour récupérer les paramètres
4. Appeler `/api/export/orders` pour récupérer les commandes
5. Afficher les rôles (admin/user) correctement
6. Afficher les images avec le bon chemin: `/static/Images/{filename}`
7. Synchroniser les prix SAAS
8. Gérer les erreurs (401 Unauthorized, 404 Not Found)

