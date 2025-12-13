# 🔄 Dashboard Template Sync - Guide d'Intégration

**Date:** 2025-12-13  
**Objectif:** Récupérer les données du Template et les stocker dans le Dashboard avec `site_id`

---

## 📋 Fichiers générés

Trois fichiers ont été créés pour toi (à adapter):

1. **`migrations_dashboard_template.py`** - Ajoute `site_id` aux tables
2. **`template_sync_service.py`** - Service de synchronisation (logique métier)
3. **`sync_routes_template.py`** - Routes Flask (API endpoints)

---

## 🚀 Étape 1: Exécuter la migration

```bash
# Sur ton serveur prod (ou local)
python migrations_dashboard_template.py
```

**Ce que ça fait:**
- ✅ Ajoute `site_id` à la table `paintings`
- ✅ Ajoute `site_id` à la table `users`
- ✅ Ajoute `site_id` à la table `orders`
- ✅ Crée `template_sync_log` (historique des synchros)
- ✅ Crée les index pour perf

**Après migration:**
```sql
paintings:
  - id (PK)
  - site_id (FK→sites) ← NOUVEAU
  - template_id ← NOUVEAU (ID du Template original)
  - name, price, image, ...

users:
  - id (PK)
  - site_id (FK→sites) ← NOUVEAU
  - template_id ← NOUVEAU
  - name, email, role, ...

orders:
  - id (PK)
  - site_id (FK→sites) ← NOUVEAU
  - customer_name, email, ...
```

---

## 🔧 Étape 2: Intégrer au Dashboard Flask

### 2.1 Copier les fichiers

```bash
# Dans ton repo MyDashboard:
cp template_sync_service.py backend/services/
cp sync_routes_template.py backend/routes/
```

### 2.2 Adapter `template_sync_service.py`

Regarder les variables d'environnement exactes du Dashboard et adapter si besoin:

```python
# Dans backend/services/template_sync_service.py

class TemplateSyncService:
    def __init__(self, db_conn, template_url, api_key, site_id):
        self.db_conn = db_conn  # ← Utilise ta connection Supabase
        self.template_url = template_url  # ← URL du Template
        self.api_key = api_key  # ← Clé API d'export du Template
        self.site_id = site_id  # ← ID du site au Dashboard
```

### 2.3 Adapter `sync_routes_template.py`

Remplacer `DB_CONFIG` par la config exacte du Dashboard:

```python
# Dans backend/routes/sync_routes_template.py

DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD'),
    'database': os.getenv('SUPABASE_DB'),
    'port': 5432
}
```

### 2.4 Enregistrer le blueprint dans ton app Flask

```python
# Dans ton app.py ou main.py du Dashboard:

from routes.sync_routes_template import sync_bp

app.register_blueprint(sync_bp)
# Ou:
# app.register_blueprint(sync_bp, url_prefix='/api')
```

---

## 🧪 Étape 3: Tester la synchronisation

### Test 1: Vérifier la connexion au Template

```bash
curl -X GET "https://jb.artworksdigital.fr/api/export/paintings" \
  -H "X-API-Key: EXPORT_API_KEY_DU_TEMPLATE"
```

**Résultat attendu:**
```json
{
  "paintings": [
    {
      "id": 1,
      "name": "Tableau Moderne",
      "price": 1500.0,
      "image": "Images/painting_123.jpg"
    }
  ],
  "count": 45
}
```

### Test 2: Lancer la synchronisation

```bash
# Remplacer SITE_ID par l'ID réel du site au Dashboard
curl -X POST "http://localhost:5000/api/sync/template/1" \
  -H "Content-Type: application/json"
```

**Réponse attendue:**
```json
{
  "success": true,
  "timestamp": "2025-12-13T12:00:00.000000",
  "paintings": {
    "success": true,
    "count": 45
  },
  "users": {
    "success": true,
    "count": 2
  },
  "orders": {
    "success": true,
    "count": 15
  },
  "settings": {
    "success": true,
    "count": 10
  }
}
```

### Test 3: Vérifier en base de données

```bash
# Peintures synchronisées
psql -U postgres -d dashboard_db -c \
  "SELECT COUNT(*) FROM paintings WHERE site_id=1"
# Résultat: 45

# Utilisateurs avec rôles
psql -U postgres -d dashboard_db -c \
  "SELECT name, role FROM users WHERE site_id=1"
# Résultat:
# Jean-Baptiste | admin
# Alice         | user

# Historique des synchros
psql -U postgres -d dashboard_db -c \
  "SELECT synced_at, status, records_processed FROM template_sync_log WHERE site_id=1"
```

---

## 🎯 Routes disponibles au Dashboard

```
POST   /api/sync/template/{site_id}              → Synchro complète
POST   /api/sync/template/{site_id}/paintings   → Juste peintures
POST   /api/sync/template/{site_id}/users       → Juste users
POST   /api/sync/template/{site_id}/orders      → Juste orders
GET    /api/sync/template/{site_id}/status      → Historique synchro
```

---

## 📊 Affichage au Dashboard

### Les peintures maintenant ont:

```python
# Récupérer les peintures d'un site spécifique
cursor.execute("""
    SELECT id, name, price, image, status 
    FROM paintings 
    WHERE site_id=%s
    ORDER BY display_order DESC
""", (site_id,))
```

### Les utilisateurs ont leurs rôles:

```python
cursor.execute("""
    SELECT name, email, role 
    FROM users 
    WHERE site_id=%s AND role='admin'
""", (site_id,))
```

### Les commandes sont liées au site:

```python
cursor.execute("""
    SELECT id, customer_name, total_price, status 
    FROM orders 
    WHERE site_id=%s
    ORDER BY order_date DESC
""", (site_id,))
```

---

## ⚙️ Configuration Scalingo (Prod)

Si tu utilises Scalingo pour le Dashboard:

```bash
# Dans l'environnement Scalingo Dashboard:

# Variables à ajouter/vérifier:
export SUPABASE_HOST=xxx.supabase.co
export SUPABASE_USER=postgres
export SUPABASE_PASSWORD=xxx
export SUPABASE_DB=postgres

# Puis tester:
scalingo --remote scalingo run python migrations_dashboard_template.py
```

---

## 🔍 Dépannage

### Erreur: "API key invalide"
```
❌ Vérifier que EXPORT_API_KEY du Template est correct
✅ Récupérer depuis: https://template.site.com/api/export/api-key (auth requis)
```

### Erreur: "site_id not found"
```
❌ Le site n'existe pas dans la table `sites` du Dashboard
✅ Créer d'abord le site via: /api/sites/create ou le Dashboard UI
```

### Erreur: "Connection refused"
```
❌ Impossible d'accéder au Template depuis le Dashboard
✅ Vérifier les firewall/DNS/HTTPS
✅ Tester avec curl depuis le serveur Dashboard
```

---

## 📈 Prochaines étapes

Après la synchronisation:

1. **Créer les pages de visualisation:**
   - `/sites/{site_id}/paintings` → Grid
   - `/sites/{site_id}/users` → Tableau
   - `/sites/{site_id}/orders` → Détails

2. **Ajouter un bouton "Synchroniser maintenant"** dans le Dashboard UI

3. **Configurer une synchro automatique** (cron job ou webhook):
   ```bash
   # Tous les jours à minuit
   0 0 * * * curl -X POST http://dashboard.local/api/sync/template/1
   ```

4. **Afficher les rôles utilisateurs** avec couleurs:
   ```html
   <span class="role {% if user.role == 'admin' %}admin{% endif %}">
     {{ user.role }}
   </span>
   ```

---

## 📞 Questions?

- **Schema complet:** Voir `TEMPLATE_EXPORT_ENDPOINTS_AUDIT.md`
- **Endpoints Template:** Voir `ZENCODEUR_DASHBOARD_PROMPT.md`
- **Tests manuels:** Voir `TEMPLATE_CORRECTIONS_MANUAL_TESTS.md`

---

✨ **À bientôt au Dashboard!**
