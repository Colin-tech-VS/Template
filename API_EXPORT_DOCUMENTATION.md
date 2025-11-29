# 🔌 Documentation API Export

## Vue d'ensemble

Cette API permet d'exporter toutes les données de votre site JB Artiste Peintre vers un autre site ou une application externe. L'authentification se fait via une clé API sécurisée.

## 🔑 Authentification

Toutes les requêtes nécessitent un header `X-API-Key` contenant votre clé API.

**Récupérer votre clé API :**
1. Connectez-vous en tant qu'administrateur
2. Allez dans Admin > API Export
3. Copiez votre clé API

**En cas de compromission :**
Cliquez sur "Régénérer une nouvelle clé" - l'ancienne cessera immédiatement de fonctionner.

## 📡 Endpoints Disponibles

### 1. Export Complet
```
GET /api/export/full
```
Exporte TOUTES les tables du site en une seule requête.

**Réponse :**
```json
{
  "success": true,
  "timestamp": "2025-11-29T10:30:00",
  "data": {
    "paintings": [...],
    "orders": [...],
    "users": [...],
    "exhibitions": [...],
    "custom_requests": [...],
    "settings": [...],
    "favorites": [...],
    "notifications": [...]
  },
  "tables_count": 10,
  "total_records": 487
}
```

---

### 2. Export Peintures
```
GET /api/export/paintings
```
Exporte uniquement les peintures avec tous leurs champs (23 colonnes).

**Champs inclus :**
- id, name, image, price, quantity
- description, description_long
- dimensions, technique, year, category, status
- image_2, image_3, image_4
- weight, framed, certificate, unique_piece
- display_order, create_date

**Réponse :**
```json
{
  "success": true,
  "count": 45,
  "data": [
    {
      "id": 1,
      "name": "Coucher de soleil",
      "price": 350.0,
      "category": "Paysage",
      ...
    }
  ]
}
```

---

### 3. Export Commandes
```
GET /api/export/orders
```
Exporte les commandes avec leurs items (produits commandés).

**Réponse :**
```json
{
  "success": true,
  "count": 12,
  "data": [
    {
      "id": 1,
      "customer_name": "Jean Dupont",
      "email": "jean@example.com",
      "address": "123 rue de Paris, 75001 Paris",
      "total_price": 850.0,
      "order_date": "2025-11-28 14:30:00",
      "status": "Livrée",
      "items": [
        {
          "id": 1,
          "painting_id": 5,
          "quantity": 2,
          "price": 350.0,
          "name": "Coucher de soleil",
          "image": "Images/sunset.jpg"
        }
      ]
    }
  ]
}
```

---

### 4. Export Utilisateurs
```
GET /api/export/users
```
Exporte les utilisateurs (mots de passe exclus pour sécurité).

**Réponse :**
```json
{
  "success": true,
  "count": 24,
  "data": [
    {
      "id": 1,
      "name": "Marie Martin",
      "email": "marie@example.com",
      "role": "user",
      "created_at": "2025-01-15 10:00:00"
    }
  ]
}
```

---

### 5. Export Expositions
```
GET /api/export/exhibitions
```
Exporte toutes les expositions passées et futures.

---

### 6. Export Demandes Personnalisées
```
GET /api/export/custom-requests
```
Exporte les demandes de créations sur mesure.

---

### 7. Export Paramètres
```
GET /api/export/settings
```
Exporte les paramètres du site (clés sensibles masquées).

---

### 8. Export Statistiques
```
GET /api/export/stats
```
Exporte des statistiques agrégées.

**Réponse :**
```json
{
  "success": true,
  "timestamp": "2025-11-29T10:30:00",
  "stats": {
    "paintings_count": 45,
    "orders_count": 12,
    "users_count": 24,
    "total_revenue": 8450.50,
    "delivered_orders": 10
  }
}
```

---

## 💻 Exemples d'Utilisation

### Python avec requests
```python
import requests
import json

API_KEY = "votre_cle_api_ici"
BASE_URL = "http://127.0.0.1:5000"  # Changez en production

headers = {
    "X-API-Key": API_KEY
}

# Exporter toutes les données
response = requests.get(f"{BASE_URL}/api/export/full", headers=headers)
data = response.json()

# Sauvegarder dans un fichier
with open('export_complet.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ {data['total_records']} enregistrements exportés")

# Exporter uniquement les peintures
paintings_response = requests.get(f"{BASE_URL}/api/export/paintings", headers=headers)
paintings = paintings_response.json()['data']

print(f"✅ {len(paintings)} peintures exportées")
```

---

### JavaScript (Node.js)
```javascript
const fetch = require('node-fetch');
const fs = require('fs');

const API_KEY = 'votre_cle_api_ici';
const BASE_URL = 'http://127.0.0.1:5000';

async function exportData() {
    const response = await fetch(`${BASE_URL}/api/export/full`, {
        headers: {
            'X-API-Key': API_KEY
        }
    });
    
    const data = await response.json();
    
    // Sauvegarder dans un fichier
    fs.writeFileSync('export_complet.json', JSON.stringify(data, null, 2));
    
    console.log(`✅ ${data.total_records} enregistrements exportés`);
}

exportData();
```

---

### JavaScript (Frontend - Fetch API)
```javascript
const API_KEY = 'votre_cle_api_ici';

async function loadPaintings() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/export/paintings', {
            headers: {
                'X-API-Key': API_KEY
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            const paintings = result.data;
            console.log(`✅ ${paintings.length} peintures chargées`);
            
            // Afficher dans votre site
            displayPaintings(paintings);
        }
    } catch (error) {
        console.error('❌ Erreur:', error);
    }
}

function displayPaintings(paintings) {
    const container = document.getElementById('paintings-grid');
    
    paintings.forEach(painting => {
        const card = `
            <div class="painting-card">
                <img src="${painting.image}" alt="${painting.name}">
                <h3>${painting.name}</h3>
                <p>${painting.price} €</p>
                <p>${painting.description}</p>
            </div>
        `;
        container.innerHTML += card;
    });
}

// Appeler au chargement de la page
loadPaintings();
```

---

### cURL (ligne de commande)
```bash
# Export complet
curl -H "X-API-Key: votre_cle_api_ici" \
     http://127.0.0.1:5000/api/export/full \
     -o export.json

# Export peintures
curl -H "X-API-Key: votre_cle_api_ici" \
     http://127.0.0.1:5000/api/export/paintings \
     -o paintings.json

# Export statistiques
curl -H "X-API-Key: votre_cle_api_ici" \
     http://127.0.0.1:5000/api/export/stats
```

---

### PHP
```php
<?php
$api_key = 'votre_cle_api_ici';
$url = 'http://127.0.0.1:5000/api/export/full';

$options = [
    'http' => [
        'method' => 'GET',
        'header' => "X-API-Key: $api_key\r\n"
    ]
];

$context = stream_context_create($options);
$response = file_get_contents($url, false, $context);
$data = json_decode($response, true);

if ($data['success']) {
    echo "✅ " . $data['total_records'] . " enregistrements exportés\n";
    
    // Sauvegarder
    file_put_contents('export.json', json_encode($data, JSON_PRETTY_PRINT));
}
?>
```

---

## 🔒 Sécurité

### Bonnes Pratiques

1. **Ne commitez JAMAIS votre clé API**
   ```bash
   # .gitignore
   .env
   config.json
   *api_key*
   ```

2. **Utilisez des variables d'environnement**
   ```python
   import os
   API_KEY = os.environ.get('JB_API_KEY')
   ```

3. **HTTPS en Production**
   ```python
   BASE_URL = "https://votre-site.com"  # Pas http://
   ```

4. **Vérifiez les réponses**
   ```python
   if response.status_code == 401:
       print("❌ Clé API invalide")
   elif response.status_code == 403:
       print("❌ Accès refusé")
   ```

5. **Limitez les accès**
   - Ne partagez pas la clé API
   - Régénérez-la si compromise
   - Loggez les accès en production

---

## 🚀 Intégration dans un Nouveau Site

### Étape 1 : Configuration
```python
# config.py
JB_API_KEY = "votre_cle_api_ici"
JB_API_URL = "http://127.0.0.1:5000"
```

### Étape 2 : Créer un Service
```python
# services/jb_api.py
import requests
from config import JB_API_KEY, JB_API_URL

class JBApiClient:
    def __init__(self):
        self.headers = {"X-API-Key": JB_API_KEY}
        self.base_url = JB_API_URL
    
    def get_all_paintings(self):
        response = requests.get(
            f"{self.base_url}/api/export/paintings",
            headers=self.headers
        )
        return response.json()['data']
    
    def get_all_orders(self):
        response = requests.get(
            f"{self.base_url}/api/export/orders",
            headers=self.headers
        )
        return response.json()['data']
    
    def get_stats(self):
        response = requests.get(
            f"{self.base_url}/api/export/stats",
            headers=self.headers
        )
        return response.json()['stats']
```

### Étape 3 : Utilisation
```python
# app.py
from services.jb_api import JBApiClient

client = JBApiClient()

# Récupérer toutes les peintures
paintings = client.get_all_paintings()

# Afficher dans votre template
return render_template('gallery.html', paintings=paintings)
```

---

## 📊 Gestion des Données

### Synchronisation Périodique
```python
import schedule
import time

def sync_data():
    client = JBApiClient()
    data = client.get_all_paintings()
    # Sauvegarder dans votre BDD
    save_to_database(data)
    print(f"✅ Synchronisation: {len(data)} peintures")

# Synchroniser toutes les heures
schedule.every(1).hours.do(sync_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Cache Local
```python
import json
from datetime import datetime, timedelta

CACHE_FILE = 'paintings_cache.json'
CACHE_DURATION = timedelta(hours=1)

def get_paintings_cached():
    # Vérifier le cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            cache_time = datetime.fromisoformat(cache['timestamp'])
            
            if datetime.now() - cache_time < CACHE_DURATION:
                return cache['data']
    
    # Cache expiré, récupérer depuis l'API
    client = JBApiClient()
    paintings = client.get_all_paintings()
    
    # Sauvegarder le cache
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'data': paintings
        }, f)
    
    return paintings
```

---

## ❓ Dépannage

### Erreur 401 (Non autorisé)
- Vérifiez que le header `X-API-Key` est présent
- Vérifiez l'orthographe de votre clé API

### Erreur 403 (Accès refusé)
- Votre clé API est invalide ou expirée
- Régénérez une nouvelle clé depuis le dashboard admin

### Erreur 500 (Erreur serveur)
- Vérifiez que le serveur Flask est démarré
- Consultez les logs du serveur

### Données vides
- Vérifiez que les tables contiennent des données
- Utilisez `/api/export/stats` pour voir les compteurs

---

## 📞 Support

Pour toute question :
1. Consultez cette documentation
2. Vérifiez les logs du serveur Flask
3. Testez avec cURL avant d'intégrer dans votre code

---

**Version:** 1.0  
**Dernière mise à jour:** 29 novembre 2025
