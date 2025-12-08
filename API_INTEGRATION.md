# Intégration API avec admin.artworksdigital.fr

## 📋 Résumé

Ce guide explique comment le **Template** (template.artworksdigital.fr) communique avec le **Dashboard** (admin.artworksdigital.fr) pour synchroniser les données.

---

## 1. Architecture de Communication

```
┌─────────────────────────────┐
│  admin.artworksdigital.fr   │
│      (Dashboard)             │
│  - Gère les templates        │
│  - Récupère les données      │
│  - Envoie les paramètres     │
└──────────────┬──────────────┘
               │
               │ API Calls
               │ (X-API-Key)
               ▼
┌─────────────────────────────┐
│ template.artworksdigital.fr │
│      (Template)              │
│  - Expose les données        │
│  - Reçoit les paramètres     │
│  - Exporte les statistiques  │
└─────────────────────────────┘
               │
               │
               ▼
┌─────────────────────────────┐
│   Supabase (PostgreSQL)     │
│   - Stocke les données      │
│   - Partage avec Dashboard  │
└─────────────────────────────┘
```

---

## 2. Endpoints API Disponibles

### 2.1 Export Complet

**Endpoint :** `GET /api/export/full`

**Description :** Exporte TOUTES les données du site

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "success": true,
  "timestamp": "2025-12-07T10:30:00.000000",
  "data": {
    "paintings": [...],
    "orders": [...],
    "users": [...],
    "exhibitions": [...],
    "custom_requests": [...],
    "settings": [...],
    "saas_sites": [...]
  },
  "tables_count": 7,
  "total_records": 1234
}
```

---

### 2.2 Export des Commandes

**Endpoint :** `GET /api/export/orders`

**Description :** Récupère toutes les commandes avec les articles

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "orders": [
    {
      "id": 1,
      "customer_name": "Jean Dupont",
      "email": "jean@example.com",
      "total_price": 250.00,
      "order_date": "2025-12-01T10:00:00",
      "status": "Livré",
      "items": [
        {
          "painting_id": 5,
          "name": "Peinture 1",
          "image": "path/to/image.jpg",
          "price": 250.00,
          "quantity": 1
        }
      ],
      "site_name": "JB Art"
    }
  ]
}
```

---

### 2.3 Export des Utilisateurs

**Endpoint :** `GET /api/export/users`

**Description :** Récupère tous les utilisateurs

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "users": [
    {
      "id": 1,
      "name": "Jean Dupont",
      "email": "jean@example.com",
      "role": "customer",
      "created_at": "2025-11-01T10:00:00"
    }
  ]
}
```

---

### 2.4 Export des Peintures

**Endpoint :** `GET /api/export/paintings`

**Description :** Récupère toutes les peintures

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "paintings": [
    {
      "id": 1,
      "name": "Peinture 1",
      "image": "path/to/image.jpg",
      "price": 250.00,
      "quantity": 5,
      "description": "Description courte",
      "category": "Paysage",
      "status": "disponible"
    }
  ]
}
```

---

### 2.5 Export des Expositions

**Endpoint :** `GET /api/export/exhibitions`

**Description :** Récupère toutes les expositions

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "exhibitions": [
    {
      "id": 1,
      "title": "Exposition 2025",
      "location": "Paris",
      "date": "2025-12-15",
      "description": "Description de l'exposition"
    }
  ]
}
```

---

### 2.6 Export des Demandes Personnalisées

**Endpoint :** `GET /api/export/custom-requests`

**Description :** Récupère toutes les demandes de commandes personnalisées

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "custom_requests": [
    {
      "id": 1,
      "client_name": "Jean Dupont",
      "client_email": "jean@example.com",
      "project_type": "Peinture personnalisée",
      "description": "Je voudrais une peinture de mon chat",
      "budget": "500-1000",
      "status": "En attente",
      "created_at": "2025-12-01T10:00:00"
    }
  ]
}
```

---

### 2.7 Export des Paramètres

**Endpoint :** `GET /api/export/settings`

**Description :** Récupère tous les paramètres du site

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "settings": [
    {
      "key": "site_name",
      "value": "JB Art"
    },
    {
      "key": "color_primary",
      "value": "#6366f1"
    },
    {
      "key": "stripe_publishable_key",
      "value": "pk_test_..."
    }
  ]
}
```

---

### 2.8 Mise à Jour d'un Paramètre

**Endpoint :** `PUT /api/export/settings/<key>`

**Description :** Met à jour un paramètre du site

**Headers :**
```
X-API-Key: your-master-key-here
Content-Type: application/json
```

**Body :**
```json
{
  "value": "Nouvelle valeur"
}
```

**Réponse :**
```json
{
  "success": true,
  "key": "site_name",
  "value": "Nouvelle valeur"
}
```

---

### 2.9 Export des Statistiques

**Endpoint :** `GET /api/export/stats`

**Description :** Récupère les statistiques du site

**Headers :**
```
X-API-Key: your-master-key-here
```

**Réponse :**
```json
{
  "stats": {
    "total_paintings": 50,
    "total_orders": 25,
    "total_revenue": 5000.00,
    "total_users": 100,
    "delivered_orders": 20,
    "pending_orders": 5
  }
}
```

---

## 3. Authentification API

### Clé API Maître

La clé API maître est définie dans les variables d'environnement :

```bash
# Scalingo
scalingo env-set TEMPLATE_MASTER_API_KEY="your-master-key-here"
```

Cette clé donne accès complet à tous les endpoints.

### Clé API du Site

Une clé API unique est générée pour chaque site :

1. Lors du premier appel API, une clé est générée automatiquement
2. Elle est stockée dans la table `settings` avec la clé `export_api_key`
3. Elle peut être régénérée via l'endpoint `/api/export/regenerate-key`

### Vérification de la Clé

```python
# Dans le décorateur @require_api_key
api_key = request.headers.get('X-API-Key')

# Vérifier contre la clé maître
if api_key == TEMPLATE_MASTER_API_KEY:
    return True

# Ou vérifier contre la clé du site
if api_key == get_setting('export_api_key'):
    return True

# Sinon, erreur 403
return False
```

---

## 4. Exemples de Requêtes

### Avec curl

```bash
# Export complet
curl -X GET https://template.artworksdigital.fr/api/export/full \
  -H "X-API-Key: your-master-key-here"

# Export des commandes
curl -X GET https://template.artworksdigital.fr/api/export/orders \
  -H "X-API-Key: your-master-key-here"

# Mise à jour d'un paramètre
curl -X PUT https://template.artworksdigital.fr/api/export/settings/site_name \
  -H "X-API-Key: your-master-key-here" \
  -H "Content-Type: application/json" \
  -d '{"value": "Nouveau nom"}'
```

### Avec Python

```python
import requests

# Configuration
API_URL = "https://template.artworksdigital.fr"
API_KEY = "your-master-key-here"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Export complet
response = requests.get(f"{API_URL}/api/export/full", headers=headers)
data = response.json()
print(data)

# Export des commandes
response = requests.get(f"{API_URL}/api/export/orders", headers=headers)
orders = response.json()
for order in orders['orders']:
    print(f"Commande {order['id']}: {order['customer_name']}")

# Mise à jour d'un paramètre
response = requests.put(
    f"{API_URL}/api/export/settings/site_name",
    headers=headers,
    json={"value": "Nouveau nom"}
)
print(response.json())
```

### Avec JavaScript

```javascript
// Configuration
const API_URL = "https://template.artworksdigital.fr";
const API_KEY = "your-master-key-here";

const headers = {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json"
};

// Export complet
fetch(`${API_URL}/api/export/full`, { headers })
  .then(res => res.json())
  .then(data => console.log(data));

// Export des commandes
fetch(`${API_URL}/api/export/orders`, { headers })
  .then(res => res.json())
  .then(orders => {
    orders.orders.forEach(order => {
      console.log(`Commande ${order.id}: ${order.customer_name}`);
    });
  });

// Mise à jour d'un paramètre
fetch(`${API_URL}/api/export/settings/site_name`, {
  method: "PUT",
  headers,
  body: JSON.stringify({ value: "Nouveau nom" })
})
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## 5. Gestion des Erreurs

### Erreur 401 : API Key manquante

```json
{
  "error": "API key manquante"
}
```

**Solution :** Ajouter le header `X-API-Key`

### Erreur 403 : API Key invalide

```json
{
  "error": "API key invalide"
}
```

**Solution :** Vérifier la clé API

### Erreur 500 : Erreur serveur

```json
{
  "error": "Description de l'erreur"
}
```

**Solution :** Vérifier les logs Scalingo

---

## 6. Synchronisation avec le Dashboard

### Flux de Synchronisation

1. **Dashboard** appelle `GET /api/export/full`
2. **Template** retourne toutes les données
3. **Dashboard** stocke les données dans sa propre base de données
4. **Dashboard** affiche les données dans son interface

### Fréquence de Synchronisation

Recommandé : **Toutes les heures** ou **à la demande**

```python
# Exemple de synchronisation périodique
import schedule
import time

def sync_template_data():
    response = requests.get(
        "https://template.artworksdigital.fr/api/export/full",
        headers={"X-API-Key": MASTER_KEY}
    )
    data = response.json()
    # Stocker dans la base de données du dashboard
    save_to_database(data)

# Synchroniser toutes les heures
schedule.every(1).hours.do(sync_template_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 7. Sécurité

### ✅ Bonnes Pratiques

1. **Clé API forte** : Utilisez une clé API longue et aléatoire
2. **HTTPS obligatoire** : Toutes les requêtes doivent être en HTTPS
3. **Rotation de clé** : Changez la clé API régulièrement
4. **Logging** : Enregistrez tous les accès API
5. **Rate limiting** : Limitez le nombre de requêtes par minute

### ❌ À Éviter

1. **Clé API en clair** : Ne mettez jamais la clé dans le code
2. **HTTP** : N'utilisez jamais HTTP (non chiffré)
3. **Clé partagée** : Ne partagez pas la clé avec d'autres
4. **Logs publics** : Ne loggez pas les clés API

---

## 8. Checklist de Configuration

- [ ] TEMPLATE_MASTER_API_KEY configurée dans Scalingo
- [ ] Endpoints API testés avec curl
- [ ] Clé API du site générée
- [ ] Dashboard peut accéder aux endpoints
- [ ] Synchronisation des données fonctionne
- [ ] Erreurs gérées correctement
- [ ] Logs vérifiés

---

## 📞 Support

Pour toute question ou problème :

1. Vérifier les logs : `scalingo logs`
2. Tester l'API avec curl
3. Vérifier la clé API
4. Consulter la documentation Supabase
5. Contacter le support Scalingo

---

**Dernière mise à jour :** 2025-12-07
**Version :** 1.0
