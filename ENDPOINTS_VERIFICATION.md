# 📋 Vérification Complète des Endpoints - Enregistrement & Gestion

**Date:** 14/12/2025  
**Projet:** JB Art Dashboard/Template  

---

## 🎨 ENDPOINTS DE CRÉATION/MODIFICATION DE PEINTURES

### 1️⃣ **POST `/admin/add` - Ajouter une peinture (Web Form)**
- **Ligne:** 2233-2310
- **Authentification:** `@require_admin`
- **Méthode:** POST (form-data)
- **Paramètres:**
  - `name` ✓ (obligatoire)
  - `price` ✓ (obligatoire, float)
  - `quantity` ✓ (obligatoire, int)
  - `description` (optionnel)
  - `description_long` (optionnel)
  - `dimensions` (optionnel)
  - `technique` (optionnel)
  - `year` (optionnel)
  - `category` (optionnel)
  - `status` (optionnel)
  - `weight` (optionnel)
  - `framed` (checkbox → 0/1)
  - `certificate` (checkbox → 0/1)
  - `unique_piece` (checkbox → 0/1)
  - `image` ✓ (fichier image, obligatoire)
  - `image_2`, `image_3`, `image_4` (optionnels)

- **Comportement:**
  - Télécharge les images dans `static/Images/`
  - Insère dans table `paintings`
  - Redirige vers `/admin/paintings`
  - Flash message: "Peinture ajoutée avec succès !"

- **Validation:**
  - ✅ Fichier présent et avec extension autorisée
  - ✅ Filename sécurisé avec `secure_filename()`
  - ⚠️ Price et quantity pas validés avant conversion

---

### 2️⃣ **POST/GET `/admin/painting/edit/<int:painting_id>` - Modifier une peinture**
- **Ligne:** 3073-3181
- **Authentification:** `@require_admin`
- **Méthode:** GET (affiche formulaire) / POST (met à jour)
- **Paramètres POST:** Mêmes que `/admin/add`

- **Comportement:**
  - GET: Récupère la peinture et affiche le formulaire
  - POST: Valide, met à jour images si présentes, met à jour BD
  - Gère les 4 images (image, image_2, image_3, image_4)
  - Supprime les anciennes images si remplacées

- **Validation:**
  - ✅ `name`, `price`, `quantity` obligatoires
  - ✅ `price` et `quantity` convertis en float/int
  - ✅ Extensions fichiers vérifiées
  - ✅ Anciennes images supprimées physiquement

- **Bug potentiel:**
  - Comparaison de chemins peut échouer sur Windows (Path normalization)

---

### 3️⃣ **POST `/admin/painting/remove/<int:painting_id>` - Supprimer une peinture**
- **Ligne:** 3060-3061 (wrapper)
- **Authentification:** `@require_admin`
- **Méthode:** POST
- **Comportement:**
  - Appelle `delete_painting()` (ligne 3185-3212)
  - Supprime l'image physiquement
  - Supprime de la BD

---

### 4️⃣ **POST `/api/reorder_paintings` - Réorganiser l'ordre d'affichage**
- **Ligne:** 2523-2533+
- **Authentification:** `@require_admin`
- **Méthode:** POST (JSON)
- **Body:**
  ```json
  {
    "order": [1, 3, 2, 4, ...]
  }
  ```
- **Comportement:**
  - Met à jour `display_order` pour chaque peinture
  - Permet la réorganisation en drag-drop

---

## 🎭 ENDPOINTS DE CRÉATION/MODIFICATION D'EXPOSITIONS

### 5️⃣ **POST/GET `/admin/exhibitions/add` - Ajouter une exposition**
- **Ligne:** 1608-1649
- **Authentification:** `@require_admin`
- **Méthode:** GET (formulaire) / POST (création)
- **Paramètres:**
  - `title` ✓ (obligatoire)
  - `location` ✓ (obligatoire)
  - `date` ✓ (obligatoire)
  - `start_time` (optionnel)
  - `end_time` (optionnel)
  - `description` (optionnel)
  - `venue_details` (optionnel)
  - `organizer` (optionnel)
  - `entry_price` (optionnel)
  - `contact_info` (optionnel)
  - `image` (optionnel, fichier)

- **Comportement:**
  - Crée dossier `expo_images` s'il n'existe pas
  - Insère dans table `exhibitions`
  - Redirige vers `/admin/exhibitions`

- **Validation:**
  - ✅ Extension fichier vérifiée
  - ✅ Filename sécurisé
  - ⚠️ Autres champs pas validés

---

### 6️⃣ **POST/GET `/admin/exhibitions/edit/<int:exhibition_id>` - Modifier une exposition**
- **Ligne:** 1653-1698
- **Authentification:** `@require_admin`
- **Méthode:** GET / POST
- **Paramètres:** Mêmes que création

- **Comportement:**
  - GET: Récupère et affiche
  - POST: Met à jour tout
  - Gère remplacement image

---

### 7️⃣ **POST `/admin/exhibitions/remove/<int:exhibition_id>` - Supprimer une exposition**
- **Ligne:** 1701-1718
- **Authentification:** `@require_admin`
- **Méthode:** POST

- **Comportement:**
  - Supprime l'image physiquement
  - Supprime de la BD

---

## 👥 ENDPOINTS DE GESTION UTILISATEURS

### 8️⃣ **POST `/register` - Enregistrement utilisateur**
- **Ligne:** 1126-1184
- **Authentification:** Aucune
- **Méthode:** GET / POST
- **Paramètres:**
  - `name` ✓
  - `email` ✓
  - `password` ✓
  - `password_confirm` ✓

- **Validation:**
  - ✅ Email unique
  - ✅ Passwords égaux
  - ✅ Hash avec `generate_password_hash()`

---

### 9️⃣ **POST `/login` - Connexion utilisateur**
- **Ligne:** 1185-1302
- **Authentification:** Aucune
- **Méthode:** GET / POST
- **Paramètres:**
  - `email` ✓
  - `password` ✓

- **Validation:**
  - ✅ Email existe
  - ✅ Password correct avec `check_password_hash()`

---

### 🔟 **POST `/admin/user/<int:user_id>/role` - Changer le rôle d'un utilisateur**
- **Ligne:** 3460-3491
- **Authentification:** `@require_admin`
- **Méthode:** POST
- **Body:**
  ```json
  {
    "role": "admin" ou "user"
  }
  ```

- **Validation:**
  - ✅ Rôle valide
  - ✅ Ne change pas le rôle de l'utilisateur courant

---

## 📋 ENDPOINTS DE COMMANDES

### 1️⃣1️⃣ **POST `/add_to_cart/<int:painting_id>` - Ajouter au panier**
- **Ligne:** 1723-1749
- **Authentification:** Aucune
- **Méthode:** POST
- **Paramètres:**
  - `quantity` (optionnel, défaut 1)

- **Comportement:**
  - Crée ou met à jour le panier
  - Ajoute/incrémente la quantité

---

### 1️⃣2️⃣ **POST `/checkout` - Créer une commande (Paiement Stripe)**
- **Ligne:** 1838-2080
- **Authentification:** Aucune
- **Méthode:** GET (formulaire) / POST (création)
- **Paramètres:**
  - `customer_name` ✓
  - `email` ✓
  - `address` ✓
  - `stripeToken` (Stripe)

- **Comportement:**
  - Valide le panier
  - Crée une commande
  - Appelle Stripe API
  - Envoie email de confirmation

---

## 🎁 ENDPOINTS DE COMMANDES PERSONNALISÉES

### 1️⃣3️⃣ **POST `/creations-sur-mesure/submit` - Soumettre une demande**
- **Ligne:** 1303-1542
- **Authentification:** Aucune
- **Méthode:** POST
- **Paramètres:**
  - `client_name` ✓
  - `email` ✓
  - `description` ✓
  - `budget` (optionnel)
  - `deadline` (optionnel)
  - `contact_preference` (optionnel)
  - `image` (optionnel, fichier)

- **Comportement:**
  - Télécharge image si présente
  - Insère dans `custom_requests`
  - Envoie email à l'admin

---

### 1️⃣4️⃣ **POST `/admin/custom-requests/<int:request_id>/status` - Mettre à jour le statut**
- **Ligne:** 1544-1556
- **Authentification:** `@require_admin`
- **Méthode:** POST
- **Paramètres:**
  - `status` ✓

---

## 📊 ENDPOINTS D'EXPORT API

### 1️⃣5️⃣ **GET `/api/export/paintings` - Récupérer toutes les peintures**
- **Ligne:** 3880-3908
- **Authentification:** `@require_api_key` (header `X-API-Key`)
- **Paramètres Query:**
  - `limit` (défaut: 200)
  - `offset` (défaut: 0)

- **Réponse:**
  ```json
  {
    "paintings": [
      {
        "id": 1,
        "name": "...",
        "price": 1500.0,
        "category": "...",
        "technique": "...",
        "year": 2024,
        "quantity": 1,
        "status": "...",
        "image": "Images/...",
        "display_order": 10,
        "site_name": "..."
      }
    ],
    "count": 45
  }
  ```

- **Colonnes retournées:**
  - ✅ id, name, price, category, technique, year, quantity, status, image, display_order

- **Optimisation:**
  - ✅ Pagination avec LIMIT/OFFSET
  - ✅ Colonnes spécifiques (pas *)

---

### 1️⃣6️⃣ **GET `/api/export/exhibitions` - Récupérer les expositions**
- **Ligne:** 3911-3927
- **Authentification:** `@require_api_key`
- **Réponse:**
  ```json
  {
    "exhibitions": [
      {
        "id": 1,
        "title": "...",
        "location": "...",
        "date": "2025-01-15",
        "start_time": "14:00",
        "end_time": "18:00",
        "description": "...",
        "site_name": "..."
      }
    ]
  }
  ```

---

### 1️⃣7️⃣ **GET `/api/export/users` - Récupérer les utilisateurs**
- **Ligne:** 3849-3877
- **Authentification:** `@require_api_key`
- **Paramètres Query:**
  - `limit` (défaut: 500)
  - `offset` (défaut: 0)

- **Réponse:**
  ```json
  {
    "users": [
      {
        "id": 1,
        "name": "...",
        "email": "...",
        "create_date": "2025-01-01",
        "role": "admin",
        "site_name": "..."
      }
    ],
    "count": 10
  }
  ```

---

### 1️⃣8️⃣ **GET `/api/export/orders` - Récupérer les commandes**
- **Ligne:** 3791-3846
- **Authentification:** `@require_api_key`
- **Paramètres Query:**
  - `limit` (défaut: 100)
  - `offset` (défaut: 0)

- **Réponse:**
  ```json
  {
    "orders": [
      {
        "id": 1,
        "customer_name": "...",
        "email": "...",
        "total_price": 1500.0,
        "order_date": "2025-01-01",
        "status": "Livrée",
        "items": [
          {
            "painting_id": 1,
            "name": "...",
            "image": "Images/...",
            "price": 1500.0,
            "quantity": 1
          }
        ],
        "site_name": "..."
      }
    ],
    "count": 25
  }
  ```

---

### 1️⃣9️⃣ **GET `/api/export/custom-requests` - Récupérer les demandes perso**
- **Ligne:** 3930-3947
- **Authentification:** `@require_api_key`
- **Réponse:**
  ```json
  {
    "custom_requests": [
      {
        "id": 1,
        "client_name": "...",
        "description": "...",
        "status": "En attente",
        "created_at": "2025-01-01",
        "site_name": "..."
      }
    ]
  }
  ```

---

### 2️⃣0️⃣ **GET `/api/export/settings` - Récupérer les paramètres**
- **Ligne:** 3950-3979
- **Authentification:** `@require_api_key`
- **Réponse:**
  ```json
  {
    "success": true,
    "count": 25,
    "data": [
      {
        "key": "site_name",
        "value": "Jean-Baptiste Art"
      },
      {
        "key": "stripe_secret_key",
        "value": "***MASKED***"
      }
    ]
  }
  ```

- **Sécurité:**
  - ✅ Clés sensibles masquées avec `***MASKED***`
  - Clés masquées: `stripe_secret_key`, `smtp_password`, `export_api_key`

---

### 2️⃣1️⃣ **GET `/api/export/stats` - Récupérer les stats**
- **Ligne:** 3982-4026
- **Authentification:** `@require_api_key`
- **Réponse:**
  ```json
  {
    "paintings_count": 45,
    "users_count": 10,
    "orders_count": 25,
    "total_revenue": 45000.0,
    "exhibitions_count": 5,
    "...": "..."
  }
  ```

---

### 2️⃣2️⃣ **GET `/api/export/full` - Export complet**
- **Ligne:** 3752-3790
- **Authentification:** `@require_api_key`
- **Réponse:** Union de tous les exports

---

## 🔐 ENDPOINTS DE CONFIGURATION STRIPE

### 2️⃣3️⃣ **PUT `/api/export/settings/stripe_publishable_key` - Configurer clé publique**
- **Ligne:** 4127-4201
- **Authentification:** `@require_api_key`
- **Méthode:** PUT (JSON)
- **Body:**
  ```json
  {
    "value": "pk_test_..."
  }
  ```

- **Validation:**
  - ✅ Format regex: `^pk_(test|live)_[A-Za-z0-9_-]+$`
  - ✅ API key valide (TEMPLATE_MASTER_API_KEY ou export_api_key)

- **Réponse:**
  ```json
  {
    "success": true,
    "message": "stripe_publishable_key mis à jour"
  }
  ```

---

### 2️⃣4️⃣ **PUT `/api/export/settings/stripe_secret_key` - Configurer clé secrète**
- **Ligne:** 4053-4124
- **Authentification:** `@require_api_key`
- **Méthode:** PUT (JSON)
- **Body:**
  ```json
  {
    "value": "sk_test_..."
  }
  ```

- **Validation:**
  - ✅ Format regex: `^sk_(test|live)_[A-Za-z0-9_-]+$`
  - ✅ API key valide

- **Sécurité:**
  - ✅ Jamais exposée via GET
  - ✅ Stockée serveur-side uniquement
  - ✅ Masked logging

---

### 2️⃣5️⃣ **PUT `/api/export/settings/stripe_price_id` - Configurer price ID**
- **Ligne:** 4213-4281
- **Authentification:** `@require_api_key`
- **Méthode:** PUT (JSON)
- **Body:**
  ```json
  {
    "value": "price_1A4Xc..."
  }
  ```

---

### 2️⃣6️⃣ **PUT `/api/export/settings/<key>` - Configurer un paramètre générique**
- **Ligne:** 669-684
- **Authentification:** `@require_api_key`
- **Méthode:** PUT (JSON)
- **Body:**
  ```json
  {
    "value": "nouvelle_valeur"
  }
  ```

---

## 🌐 ENDPOINTS SAAS

### 2️⃣7️⃣ **POST `/api/saas/register-site` - Enregistrer un site au Dashboard**
- **Ligne:** 4658-4800+
- **Authentification:** Session utilisateur
- **Méthode:** POST (JSON)
- **Body:**
  ```json
  {
    "user_id": 1,
    "domain": "example.com",
    "api_key": "..."
  }
  ```

- **Comportement:**
  - Envoie requête au dashboard
  - Initialise BD pour le site
  - Envoie email de confirmation
  - Supprime preview domain

---

### 2️⃣8️⃣ **POST `/saas/apply` - Candidature SAAS**
- **Ligne:** 4487-4495

### 2️⃣9️⃣ **POST `/saas/approve/<int:user_id>` - Approuver candidat**
- **Ligne:** 4497-4505

### 3️⃣0️⃣ **POST `/saas/paid/<int:user_id>` - Marquer comme payé**
- **Ligne:** 4507-4514

### 3️⃣1️⃣ **POST `/saas/domain/<int:user_id>` - Configurer domaine**
- **Ligne:** 4515-4524

### 3️⃣2️⃣ **POST `/saas/clone/<int:user_id>` - Cloner le site**
- **Ligne:** 4526-4534

### 3️⃣3️⃣ **POST `/saas/activate/<int:user_id>` - Activer le site**
- **Ligne:** 4536-4656

---

## ⚙️ AUTRES ENDPOINTS UTILES

### 3️⃣4️⃣ **POST `/api/upload/image` - Télécharger une image**
- **Ligne:** 4343-4399
- **Authentification:** `@require_api_key`
- **Méthode:** POST (multipart/form-data)
- **Body:**
  ```
  files: [image_file]
  ```

- **Réponse:**
  ```json
  {
    "success": true,
    "files": [
      {
        "filename": "...",
        "path": "static/Images/..."
      }
    ]
  }
  ```

---

### 3️⃣5️⃣ **POST `/api/export/regenerate-key` - Régénérer la clé API**
- **Ligne:** 4401-4484
- **Authentification:** `@require_admin`
- **Méthode:** POST
- **Réponse:** Nouvelle clé API

---

### 3️⃣6️⃣ **POST `/contact` - Soumettre un formulaire de contact**
- **Ligne:** 2626-2724

---

## 🔒 AUTHENTIFICATION

### Décorateurs disponibles:
1. **`@require_admin`** (ligne ~1100)
   - Vérifie que l'utilisateur est admin
   - Redirige vers home sinon

2. **`@require_api_key`** (ligne ~4350)
   - Vérifie header `X-API-Key`
   - Retourne 401 si invalide

---

## 📌 RÉSUMÉ DES DONNÉES DE PEINTURES

### Champs de `paintings`:
- `id` (INT, PRIMARY KEY)
- `name` (VARCHAR)
- `image` (VARCHAR) - Chemin principal
- `image_2`, `image_3`, `image_4` (VARCHAR) - Images additionnelles
- `price` (FLOAT)
- `quantity` (INT)
- `description` (TEXT)
- `description_long` (TEXT)
- `dimensions` (VARCHAR)
- `technique` (VARCHAR)
- `year` (INT)
- `category` (VARCHAR)
- `status` (VARCHAR)
- `weight` (VARCHAR)
- `framed` (INT) - Boolean
- `certificate` (INT) - Boolean
- `unique_piece` (INT) - Boolean
- `display_order` (INT)
- `create_date` (DATETIME)

---

## 📌 RÉSUMÉ DES DONNÉES D'EXPOSITIONS

### Champs de `exhibitions`:
- `id` (INT, PRIMARY KEY)
- `title` (VARCHAR)
- `location` (VARCHAR)
- `date` (DATE)
- `start_time` (TIME)
- `end_time` (TIME)
- `description` (TEXT)
- `venue_details` (TEXT)
- `organizer` (VARCHAR)
- `entry_price` (FLOAT)
- `contact_info` (VARCHAR)
- `image` (VARCHAR)

---

## ✅ VALIDATION CHECKLIST

### Pour ajouter une peinture:
- [ ] Nom obligatoire
- [ ] Prix obligatoire et > 0
- [ ] Quantité obligatoire et >= 0
- [ ] Image obligatoire (jpeg, png, gif, webp)
- [ ] Images additionnelles optionnelles
- [ ] Tous les autres champs optionnels

### Pour ajouter une exposition:
- [ ] Titre obligatoire
- [ ] Localisation obligatoire
- [ ] Date obligatoire
- [ ] Image optionnelle
- [ ] Autres champs optionnels

### Pour les exports API:
- [ ] Header `X-API-Key` valide
- [ ] Pagination avec limit/offset
- [ ] Clés sensibles masquées
- [ ] Format JSON valide

---

## 🐛 PROBLÈMES IDENTIFIÉS

1. **Validation insuffisante de price/quantity à la création**
   - Pas de try/except au moment du form.get()
   - Pourrait crash si valeur non-numeric

2. **Gestion des chemins d'images Windows**
   - Comparaison de chemins fragile sur Windows
   - Utilise `os.path.join()` mais mélange avec strings

3. **Pas de validation d'unicité**
   - Plusieurs peintures peuvent avoir même nom
   - Pas de unique constraint en BD

4. **Masquage des clés sensibles**
   - Masquage uniquement côté export API
   - Pas de masquage ailleurs

5. **Pas de soft-delete**
   - Suppressions physiques
   - Pas d'historique

---

## 📋 RECOMMANDATIONS

1. ✅ Ajouter validation stricter à la création/modification
2. ✅ Normaliser les chemins d'images
3. ✅ Ajouter unique constraints optionnels
4. ✅ Implémenter soft-delete avec archived flag
5. ✅ Ajouter tests unitaires pour chaque endpoint
6. ✅ Documenter les formats de réponse d'erreur
7. ✅ Ajouter rate limiting sur les endpoints publics
8. ✅ Mettre en place logging des modifications

