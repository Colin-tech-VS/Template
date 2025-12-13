# 🚀 Prompt Zencoder - Dashboard Implementation

**Pour:** Implémenter l'importation des données du Template vers le Dashboard  
**Contexte:** Le Template expose 18 endpoints d'export complets et sécurisés  
**Référence:** `DASHBOARD_TEMPLATE_SYNC_PROMPT.md`, `TEMPLATE_EXPORT_ENDPOINTS_AUDIT.md`

---

## 🎯 Objectif global

Créer un système de synchronisation bidirectionnel Dashboard ↔ Template:

1. **Template → Dashboard:** Exporter peintures, utilisateurs, commandes, settings
2. **Dashboard → Template:** Envoyer clés Stripe, prix SAAS, configuration

---

## ✅ État du Template (TERMINÉ)

Le Template a terminé:
- ✅ 18 endpoints d'export fonctionnels
- ✅ Authentification X-API-Key
- ✅ Rôles utilisateurs (admin/user)
- ✅ Images: références chemin (`Images/painting_123.jpg`)
- ✅ Sécurité: secrets masqués (`***MASKED***`)

**Endpoints disponibles:**
```
GET  /api/export/paintings        → Liste peintures + images
GET  /api/export/users            → Liste utilisateurs + rôles
GET  /api/export/orders           → Commandes + items détaillés
GET  /api/export/exhibitions      → Expositions
GET  /api/export/settings         → Paramètres du site
GET  /api/export/stats            → Statistiques
PUT  /api/export/settings/stripe_publishable_key  → Reçoit clé Stripe
```

---

## 📋 Phase 1: Client Template (Backend)

### 1.1 Créer la classe `TemplateClient`

**Fichier:** `backend/clients/template_client.py`

**Fonctionnalités:**
- Requêtes HTTP vers Template avec X-API-Key
- Gestion des timeouts et erreurs
- Méthodes pour chaque endpoint principal

**Méthodes requises:**
```python
class TemplateClient:
    def __init__(self, base_url: str, api_key: str)
    
    def get_paintings(self, limit=200, offset=0) → List[Dict]
    def get_users(self, limit=500, offset=0) → List[Dict]
    def get_orders(self, limit=100, offset=0) → List[Dict]
    def get_settings() → List[Dict]
    def get_exhibitions() → List[Dict]
    def get_stats() → Dict
```

**Exemple de réponse `get_paintings()`:**
```json
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
    }
  ],
  "count": 45
}
```

### 1.2 Créer la classe `TemplateSynchronizer`

**Fichier:** `backend/services/template_synchronizer.py`

**Fonctionnalités:**
- Orchestrer la synchronisation complète
- Valider chaque donnée reçue
- UPSERT (insert or update) en base de données
- Logging détaillé avec timestamps

**Méthode principale:**
```python
def sync_all() → Dict:
    """Synchronise TOUTES les données"""
    return {
        'success': bool,
        'timestamp': ISO8601,
        'paintings': {'success': bool, 'count': int},
        'users': {'success': bool, 'count': int},
        'orders': {'success': bool, 'count': int},
        'settings': {'success': bool, 'count': int},
        'exhibitions': {'success': bool, 'count': int},
        'log': [{'entity': str, 'level': str, 'message': str}]
    }
```

---

## 📋 Phase 2: Routes API Dashboard (Backend)

### 2.1 Créer les routes de synchronisation

**Fichier:** `backend/routes/sync.py`

**Routes requises:**
```python
POST /api/sync/template/{site_id}
    # Synchronise manuellement un Template
    # Response: {success: true, summary: {...}, log: [...]}

POST /api/sync/template/{site_id}/paintings
    # Synchronise JUSTE les peintures

POST /api/sync/template/{site_id}/users
    # Synchronise JUSTE les utilisateurs

GET /api/sync/template/{site_id}/status
    # Retourne le statut de la dernière synchro
```

### 2.2 Implémenter le webhook (optionnel mais recommandé)

**Route:**
```python
POST /api/sync/webhook/template
    # Template notifie Dashboard quand les données changent
    # Body: {event: "painting_created", site_id: "...", data: {...}}
```

---

## 📋 Phase 3: Models & Database

### 3.1 Créer les modèles ORM

**Fichiers:**
- `models/template_painting.py`
- `models/template_user.py`
- `models/template_order.py`
- `models/template_settings.py`

**Exemple `TemplatePainting`:**
```python
class TemplatePainting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, unique=True)  # ID depuis Template
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float)
    category = db.Column(db.String(100))
    technique = db.Column(db.String(100))
    year = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50))  # "Disponible", "Vendu", etc.
    image = db.Column(db.String(255))  # "Images/painting_123.jpg"
    display_order = db.Column(db.Integer)
    site_name = db.Column(db.String(255))
    sync_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
```

### 3.2 Créer les migrations

```bash
flask db migrate -m "Add template data models"
flask db upgrade
```

---

## 📋 Phase 4: UI Frontend

### 4.1 Affichage des peintures

**Route:** `/sites/{site_id}/paintings`

**Affichage:**
```html
<div class="paintings-grid">
  {% for painting in paintings %}
  <div class="painting-card">
    <img src="{{ painting.image_full_url }}" alt="{{ painting.name }}">
    <h3>{{ painting.name }}</h3>
    <p class="category">{{ painting.category }}</p>
    <p class="price">{{ painting.price }} €</p>
    <span class="status">{{ painting.status }}</span>
  </div>
  {% endfor %}
</div>
```

**Données à afficher:**
- Nom, prix, image, statut, catégorie
- Lien pour éditer
- Lien vers Template original

### 4.2 Affichage des utilisateurs

**Route:** `/sites/{site_id}/users`

**Tableau:**
```html
<table class="users-table">
  <tr>
    <th>Nom</th>
    <th>Email</th>
    <th>Rôle</th>
    <th>Date d'inscription</th>
  </tr>
  <tr>
    <td>Jean-Baptiste</td>
    <td>admin@example.com</td>
    <td><span class="role-admin">👤 Admin</span></td>
    <td>2025-01-01</td>
  </tr>
  <tr>
    <td>Alice</td>
    <td>alice@example.com</td>
    <td><span class="role-user">👥 User</span></td>
    <td>2025-01-05</td>
  </tr>
</table>
```

**Validations:**
- ✅ Afficher les rôles (admin/user) avec icône
- ✅ Colorier différemment les admins
- ✅ Compter utilisateurs par rôle

### 4.3 Affichage des commandes

**Route:** `/sites/{site_id}/orders`

**Format:** Cartes ou liste
```html
<div class="order-card">
  <h3>Commande #101</h3>
  <p>Client: Alice Dupont</p>
  <p>Total: 3500 €</p>
  <p>Statut: Livrée</p>
  <ul class="items">
    <li>Tableau Moderne - 1500 € (x1)</li>
  </ul>
</div>
```

### 4.4 Affichage des settings

**Route:** `/sites/{site_id}/settings`

**Format:** Formulaire en lecture seule
```html
<div class="settings-view">
  <p><strong>Site Name:</strong> {{ site_name }}</p>
  <p><strong>Site Logo:</strong> {{ site_logo }}</p>
  <p><strong>Stripe Key:</strong> {{ stripe_pk[:10] }}...</p>
  <p><strong>SAAS Price:</strong> {{ saas_price }} €</p>
</div>
```

### 4.5 Bouton de synchronisation manuelle

```html
<button class="btn-sync" onclick="syncTemplate()">
  🔄 Synchroniser maintenant
</button>

<div id="sync-status" style="display:none;">
  <p>Synchronisation en cours...</p>
  <progress id="sync-progress"></progress>
</div>
```

**JavaScript:**
```javascript
async function syncTemplate() {
    const response = await fetch(`/api/sync/template/${siteId}`, {
        method: 'POST'
    });
    const data = await response.json();
    
    if (data.success) {
        showSuccess(`Synchronisation réussie: ${data.summary.paintings.count} peintures`);
        reloadPage();
    } else {
        showError('Erreur de synchronisation');
    }
}
```

---

## 📊 Phase 5: Validation & Sécurité

### 5.1 Validation des données reçues

**Pour chaque type de donnée:**

**Peintures:**
- ✅ id, name, price requis (non-empty)
- ✅ price > 0
- ✅ image commence par "Images/"
- ✅ status in ["Disponible", "Vendu", ...]

**Utilisateurs:**
- ✅ id, name, email requis
- ✅ email format valide
- ✅ role in ["admin", "user"]

**Commandes:**
- ✅ id, customer_name, email, total_price, order_date requis
- ✅ total_price > 0
- ✅ items: tableau (peut être vide)

### 5.2 Gestion des erreurs

**Cas à gérer:**
- 401 Unauthorized → API key invalide
- 404 Not Found → Endpoint n'existe pas
- 500 Internal Server Error → Template crash
- Timeout → Template indisponible
- Données invalides → Log + skip

**Stratégie:**
```python
try:
    data = client.get_paintings()
except TemplateConnectionError:
    log("ERROR", "Template indisponible")
    notify_admin("Connection failed")
except TemplateAuthenticationError:
    log("ERROR", "API key invalide")
    notify_admin("Auth failed - update key")
except TemplateValidationError:
    log("WARNING", "Données invalides - skip")
```

---

## 🧪 Phase 6: Tests

### 6.1 Tests unitaires

**Fichier:** `tests/test_template_client.py`

```python
def test_get_paintings():
    client = TemplateClient(base_url, api_key)
    paintings = client.get_paintings()
    assert len(paintings) > 0
    assert 'id' in paintings[0]
    assert 'image' in paintings[0]

def test_invalid_api_key():
    client = TemplateClient(base_url, "invalid")
    with pytest.raises(TemplateAuthenticationError):
        client.get_paintings()
```

### 6.2 Tests d'intégration

**Fichier:** `tests/test_sync_integration.py`

```python
def test_sync_all():
    synchronizer = TemplateSynchronizer(db, client)
    result = synchronizer.sync_all()
    
    assert result['success'] == True
    assert result['paintings']['count'] > 0
    assert result['users']['count'] >= 1
    
    # Vérifier en DB
    assert PaintingModel.query.count() > 0
```

### 6.3 Tests manuels

**Voir:** `TEMPLATE_CORRECTIONS_MANUAL_TESTS.md`

---

## 📋 Checklist d'implémentation

### Backend
- [ ] TemplateClient créé et testé
- [ ] TemplateSynchronizer créé et testé
- [ ] Routes API `/api/sync/...` implémentées
- [ ] Modèles ORM créés (Painting, User, Order, Settings)
- [ ] Migrations base de données
- [ ] Validation des données
- [ ] Gestion des erreurs
- [ ] Logging complet
- [ ] Webhook (optionnel)

### Frontend
- [ ] Page `/sites/{id}/paintings` avec grid
- [ ] Page `/sites/{id}/users` avec tableau
- [ ] Page `/sites/{id}/orders` avec détails
- [ ] Page `/sites/{id}/settings` avec paramètres
- [ ] Bouton "Synchroniser maintenant"
- [ ] Affichage des rôles (admin vs user)
- [ ] Images s'affichent correctement
- [ ] Messages d'erreur/succès

### Tests & Documentation
- [ ] Tests unitaires passent
- [ ] Tests d'intégration passent
- [ ] Tests manuels passés (voir autre doc)
- [ ] Documentation API mise à jour
- [ ] README avec instructions de sync

---

## 🎯 Priorités

**Critique (P1):**
1. TemplateClient + GET /api/export/paintings
2. Affichage peintures au Dashboard
3. Synchronisation manuelle

**Important (P2):**
1. Utilisateurs + rôles
2. Commandes
3. Settings

**Nice to have (P3):**
1. Webhook automatique
2. Caching des données
3. Monitoring de synchro

---

## 📚 Documentation de référence

**À consulter:**
1. `TEMPLATE_EXPORT_ENDPOINTS_AUDIT.md` - Tous les endpoints détaillés
2. `DASHBOARD_TEMPLATE_SYNC_PROMPT.md` - Architecture complète
3. `TEMPLATE_CORRECTIONS_MANUAL_TESTS.md` - Tests manuels

---

## 🚀 Commandes utiles

```bash
# Tester la connexion Template
curl -X GET "https://template.artworksdigital.fr/api/export/paintings" \
  -H "X-API-Key: YOUR_KEY"

# Récupérer la clé API du Template
curl -X GET "https://template.artworksdigital.fr/api/export/api-key" \
  -H "Cookie: user_id=1" | jq '.api_key'

# Lancer les migrations
flask db upgrade

# Exécuter les tests
pytest tests/

# Lancer le serveur dev
flask run
```

---

## 📞 Questions?

**Voir la documentation complète:**
- Endpoints: `TEMPLATE_EXPORT_ENDPOINTS_AUDIT.md`
- Architecture: `DASHBOARD_TEMPLATE_SYNC_PROMPT.md`
- Tests: `TEMPLATE_CORRECTIONS_MANUAL_TESTS.md`
- Résumé: `TEMPLATE_CORRECTIONS_SUMMARY.md`

---

## ✨ Notes finales

- ✅ Le Template est prêt (endpoints complets)
- ✅ L'authentification X-API-Key fonctionne
- ✅ Les rôles utilisateurs sont gérés automatiquement
- ✅ Les images sont servies statiquement
- ✅ La sécurité est robuste (secrets masqués)

**Vous pouvez commencer l'implémentation Dashboard maintenant!**

