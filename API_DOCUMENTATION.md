# API Documentation - Template ArtworksDigital

## Vue d'ensemble

Le Template expose plusieurs endpoints API pour permettre au Dashboard et aux services externes de récupérer/modifier les données du site.

Tous les endpoints API requièrent une **authentification par clé API**.

---

## Authentification

### Header requis
```
X-API-Key: <votre_clé_api>
```

### Types de clés API acceptées

Le Template accepte **deux types de clés API** (en ordre de priorité):

1. **Clé maître (Master Key)**: `TEMPLATE_MASTER_API_KEY`
   - Variable d'environnement définie sur le serveur
   - La même pour toutes les requêtes
   - Pour les services système/Dashboard

2. **Clé stockée (Custom Export Key)**: `export_api_key`
   - Stockée dans la table `settings` de la base de données
   - Peut être définie via admin settings
   - Alternative/fallback si clé maître non disponible

### Comment configurer les clés API

#### 1. Clé maître (recommandé pour production)
```bash
# Sur le serveur Template, définir la variable d'environnement:
export TEMPLATE_MASTER_API_KEY="votre-clé-sécurisée-ici"

# Exemple de génération sécurisée:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 2. Clé personnalisée (fallback)
- Peut être définie via `/admin/settings` si disponible
- Stockée dans settings avec la clé `export_api_key`

---

## Endpoints API

### 1. Récupérer les Settings

**Endpoint**: `GET /api/export/settings`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "count": 35,
  "data": [
    {
      "id": 1,
      "key": "primary_color",
      "value": "#1E3A8A"
    },
    {
      "id": 2,
      "key": "secondary_color",
      "value": "#3B65C4"
    },
    {
      "id": 3,
      "key": "site_name",
      "value": "Jean-Baptiste Art"
    },
    {
      "id": 4,
      "key": "stripe_secret_key",
      "value": "***MASKED***"
    }
  ]
}
```

**Erreur - Clé API invalide (401)**:
```json
{
  "error": "invalid_api_key",
  "success": false
}
```

**Notes**:
- Masque automatiquement les clés sensibles: `stripe_secret_key`, `smtp_password`, `export_api_key`
- Retourne toutes les settings sauf les valeurs sensibles

---

### 2. Récupérer les Commandes

**Endpoint**: `GET /api/export/orders`

**Authentification**: X-API-Key (header)

**Paramètres optionnels**:
- `limit` (default: 100) - Nombre d'enregistrements
- `offset` (default: 0) - Offset pour pagination

**Réponse réussie (200)**:
```json
{
  "success": true,
  "total": 42,
  "count": 5,
  "data": [
    {
      "id": 1,
      "customer_name": "Jean Dupont",
      "email": "jean@example.com",
      "total_price": 150.00,
      "order_date": "2025-12-14T10:30:00",
      "status": "Livré",
      "items": [
        {
          "order_id": 1,
          "painting_id": 5,
          "name": "Peinture #1",
          "image": "paintings/img1.jpg",
          "price": 150.00,
          "quantity": 1
        }
      ]
    }
  ]
}
```

---

### 3. Récupérer les Utilisateurs

**Endpoint**: `GET /api/export/users`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "id": 1,
      "name": "Admin User",
      "email": "admin@example.com",
      "role": "admin",
      "create_date": "2025-01-01T00:00:00"
    }
  ]
}
```

---

### 4. Récupérer les Peintures

**Endpoint**: `GET /api/export/paintings`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "count": 12,
  "data": [
    {
      "id": 1,
      "name": "Titre de la peinture",
      "image": "paintings/img1.jpg",
      "price": 500.00,
      "quantity": 1,
      "description": "Description courte",
      "category": "Acrylique",
      "status": "disponible",
      "display_order": 1
    }
  ]
}
```

---

### 5. Récupérer les Expositions

**Endpoint**: `GET /api/export/exhibitions`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "id": 1,
      "title": "Exposition 2025",
      "location": "Paris",
      "date": "2025-06-15",
      "start_time": "14:00",
      "end_time": "18:00",
      "description": "Description de l'exposition",
      "venue_details": "Détails du lieu"
    }
  ]
}
```

---

### 6. Récupérer les Demandes Personnalisées

**Endpoint**: `GET /api/export/custom-requests`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "id": 1,
      "client_name": "Client Name",
      "client_email": "client@example.com",
      "project_type": "Peinture sur mesure",
      "description": "Description du projet",
      "status": "En attente",
      "created_at": "2025-12-14T10:00:00"
    }
  ]
}
```

---

### 7. Récupérer TOUTES les données

**Endpoint**: `GET /api/export/full`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "timestamp": "2025-12-14T11:00:00",
  "data": {
    "users": [...],
    "paintings": [...],
    "orders": [...],
    "exhibitions": [...],
    "settings": [...],
    "custom_requests": [...]
  },
  "tables_count": 13,
  "total_records": 150
}
```

---

### 8. Récupérer les Statistiques

**Endpoint**: `GET /api/export/stats`

**Authentification**: X-API-Key (header)

**Réponse réussie (200)**:
```json
{
  "success": true,
  "stats": {
    "total_users": 5,
    "total_paintings": 12,
    "total_orders": 42,
    "total_revenue": 25500.00,
    "exhibitions_count": 3,
    "custom_requests_count": 8
  }
}
```

---

## Code d'exemple - Python (avec Requests)

### Tester la connexion

```python
import requests

BASE_URL = "https://example.artworksdigital.fr"
API_KEY = "votre-clé-api-ici"

headers = {
    "X-API-Key": API_KEY
}

# Test: Récupérer les settings
response = requests.get(
    f"{BASE_URL}/api/export/settings",
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Connecté! {data['count']} settings trouvés")
else:
    print(f"❌ Erreur {response.status_code}: {response.json()}")
```

### Récupérer et traiter les données

```python
import requests
import json

BASE_URL = "https://example.artworksdigital.fr"
API_KEY = "votre-clé-api-ici"

def fetch_template_data(endpoint):
    """Récupère les données d'un endpoint du Template"""
    headers = {"X-API-Key": API_KEY}
    response = requests.get(
        f"{BASE_URL}/api/export/{endpoint}",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

try:
    # Récupérer toutes les données
    settings = fetch_template_data("settings")
    paintings = fetch_template_data("paintings")
    orders = fetch_template_data("orders")
    users = fetch_template_data("users")
    
    print(f"Settings: {settings['count']} items")
    print(f"Paintings: {paintings['count']} items")
    print(f"Orders: {orders['count']} items")
    print(f"Users: {users['count']} items")
    
    # Sauvegarder les données
    with open('template_backup.json', 'w') as f:
        json.dump({
            'settings': settings['data'],
            'paintings': paintings['data'],
            'orders': orders['data'],
            'users': users['data']
        }, f, indent=2)
    
except requests.exceptions.HTTPError as e:
    print(f"Erreur API: {e.response.status_code}")
    print(f"Message: {e.response.json()}")
except Exception as e:
    print(f"Erreur: {e}")
```

---

## Dépannage

### Erreur 401 Unauthorized

**Cause possible**: Clé API invalide ou non configurée

**Solutions**:
1. ✅ Vérifier que la clé API est présente dans le header `X-API-Key`
2. ✅ Vérifier la valeur de `TEMPLATE_MASTER_API_KEY` sur le serveur Template
3. ✅ Vérifier les logs du Template pour voir le message d'erreur exact
4. ✅ Générer une nouvelle clé avec: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

### Erreur 500 Internal Server Error

**Solutions**:
1. ✅ Vérifier les logs du Template
2. ✅ S'assurer que la base de données est accessible
3. ✅ Vérifier que les tables existent (`SELECT * FROM settings;`)

---

## Configuration du Dashboard

Pour que le Dashboard puisse accéder au Template:

1. **Stocker la clé API**:
   ```python
   # Dans le Dashboard
   TEMPLATE_API_KEY = os.getenv('TEMPLATE_API_KEY')  # Venir du fichier .env
   TEMPLATE_BASE_URL = "https://example.artworksdigital.fr"
   ```

2. **Faire des requêtes**:
   ```python
   import requests
   
   def sync_from_template():
       headers = {"X-API-Key": TEMPLATE_API_KEY}
       resp = requests.get(
           f"{TEMPLATE_BASE_URL}/api/export/full",
           headers=headers,
           timeout=30
       )
       resp.raise_for_status()
       return resp.json()
   ```

3. **Ajouter un schedule**:
   ```python
   # Sync toutes les 24h
   from celery.schedules import crontab
   
   app.conf.beat_schedule = {
       'sync-template-data': {
           'task': 'tasks.sync_from_template',
           'schedule': crontab(hour=2, minute=0),  # À 2h du matin
       },
   }
   ```

---

## Checklist d'intégration

- [ ] Clé API maître générée et stockée en variable d'environnement
- [ ] Dashboard peut accéder à `GET /api/export/settings` avec succès
- [ ] Tests manuels réussis via cURL ou Postman
- [ ] Code Python teste la connexion avant de faire d'autres requêtes
- [ ] Erreurs 401 gérées proprement (retry, notification)
- [ ] Syncing automatique configuré
- [ ] Logs configurés pour tracer les appels API
- [ ] Rate limiting considéré (si besoin)
- [ ] Timeout configuré (30s recommandé)
- [ ] Clé API JAMAIS loggée ou exposée en plaintext

