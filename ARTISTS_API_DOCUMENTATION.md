# 📚 API Artistes - Documentation Complète

## Vue d'ensemble

Cette API permet de gérer les artistes du site vitrine Artworksdigital via Supabase REST API (PostgREST). Tous les endpoints communiquent avec Supabase en utilisant les standards HTTP REST.

## 🔐 Configuration Requise

### Variables d'Environnement

```bash
# URL de votre projet Supabase (sans /rest/v1)
SUPABASE_URL=https://xxxxx.supabase.co

# Clé anonyme pour lectures publiques
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Clé service pour opérations admin (côté serveur uniquement)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# URL de connexion PostgreSQL pour migrations
SUPABASE_DB_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

⚠️ **Sécurité**: `SUPABASE_SERVICE_KEY` ne doit JAMAIS être exposée au navigateur!

## 📊 Schéma de Base de Données

### Table `template_artists`

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `name` | TEXT | NOT NULL | Nom de l'artiste |
| `email` | TEXT | UNIQUE NOT NULL | Email (unique) |
| `phone` | TEXT | NULL | Téléphone |
| `bio` | TEXT | NULL | Biographie |
| `website` | TEXT | NULL | Site web |
| `price` | DECIMAL(10,2) | DEFAULT 500.00 | Prix (€) |
| `status` | TEXT | DEFAULT 'pending' | Statut: pending, approved, rejected |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Date de création |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Date de mise à jour (auto-update) |

### Table `artworks_artist_actions`

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `artist_id` | INTEGER | NOT NULL, FK | Référence à template_artists |
| `action` | TEXT | NOT NULL | Type: created, updated, approved, rejected, deleted |
| `action_date` | TIMESTAMP | DEFAULT NOW() | **Date de l'action** (différent de created_at) |
| `performed_by` | TEXT | NULL | Utilisateur ayant effectué l'action |
| `details` | TEXT | NULL | Détails supplémentaires (JSON) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Date d'enregistrement du log |

**⚠️ Important**: Utiliser `action_date` pour le tri et les filtres, pas `created_at`!

## 🚀 Endpoints

### 1. Créer un Artiste

**POST** `/api/artists`

Crée un nouvel artiste avec statut `pending` et log l'action `created`.

**Headers Supabase (automatiques)**:
```
apikey: {SUPABASE_SERVICE_KEY}
Authorization: Bearer {SUPABASE_SERVICE_KEY}
Content-Type: application/json
Prefer: return=representation
```

**Body (JSON)**:
```json
{
  "name": "Jean Dupont",
  "email": "jean@example.com",
  "phone": "+33612345678",
  "bio": "Artiste peintre contemporain",
  "website": "https://jean-dupont.art",
  "price": 550.00
}
```

**Réponse 201**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Jean Dupont",
    "email": "jean@example.com",
    "phone": "+33612345678",
    "bio": "Artiste peintre contemporain",
    "website": "https://jean-dupont.art",
    "price": 550.00,
    "status": "pending",
    "created_at": "2025-12-10T22:30:00Z",
    "updated_at": "2025-12-10T22:30:00Z"
  }
}
```

**Erreurs**:
- `400`: Champs manquants (name, email requis)
- `400`: Email déjà existant (contrainte UNIQUE)
- `500`: Erreur serveur

---

### 2. Lire un Artiste

**GET** `/api/artists/:id`

Récupère un artiste par son ID avec toutes les colonnes (`select="*"`).

**Headers Supabase (automatiques)**:
```
apikey: {SUPABASE_ANON_KEY}
Authorization: Bearer {SUPABASE_ANON_KEY}
```

**Réponse 200**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Jean Dupont",
    "email": "jean@example.com",
    "phone": "+33612345678",
    "bio": "Artiste peintre contemporain",
    "website": "https://jean-dupont.art",
    "price": 550.00,
    "status": "approved",
    "created_at": "2025-12-10T22:30:00Z",
    "updated_at": "2025-12-10T22:35:00Z"
  }
}
```

**Erreurs**:
- `404`: Artiste non trouvé
- `500`: Erreur serveur

---

### 3. Lister les Artistes

**GET** `/api/artists`

Liste tous les artistes avec pagination, tri et filtres.

**Query Parameters**:
- `status` (optionnel): `pending`, `approved`, `rejected`
- `limit` (défaut: 50, max: 200): Nombre de résultats
- `offset` (défaut: 0): Décalage pour pagination
- `order` (défaut: `created_at.desc`): Tri (ex: `name.asc`, `price.desc`)

**Exemple**:
```
GET /api/artists?status=approved&limit=20&offset=0&order=name.asc
```

**Réponse 200**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "Jean Dupont",
      "email": "jean@example.com",
      "status": "approved",
      "...": "..."
    },
    {
      "id": 2,
      "name": "Marie Martin",
      "email": "marie@example.com",
      "status": "approved",
      "...": "..."
    }
  ],
  "count": 2,
  "limit": 20,
  "offset": 0
}
```

**Erreurs**:
- `400`: Paramètres invalides (limit hors limites, offset négatif)
- `500`: Erreur serveur

---

### 4. Mettre à Jour un Artiste

**PATCH** `/api/artists/:id`

Met à jour les informations d'un artiste et log l'action `updated`.

**Headers Supabase (automatiques)**:
```
apikey: {SUPABASE_SERVICE_KEY}
Authorization: Bearer {SUPABASE_SERVICE_KEY}
Content-Type: application/json
Prefer: return=representation
```

**Body (JSON)** - Champs à mettre à jour uniquement:
```json
{
  "name": "Jean Dupont Modifié",
  "price": 600.00,
  "bio": "Nouvelle biographie"
}
```

**Réponse 200**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Jean Dupont Modifié",
    "email": "jean@example.com",
    "price": 600.00,
    "bio": "Nouvelle biographie",
    "status": "approved",
    "created_at": "2025-12-10T22:30:00Z",
    "updated_at": "2025-12-10T22:40:00Z"
  }
}
```

**Erreurs**:
- `404`: Artiste non trouvé
- `400`: Données invalides
- `500`: Erreur serveur

---

### 5. Approuver un Artiste

**PATCH** `/api/artists/:id/approve`

Change le statut en `approved` et log l'action `approved`.

**Réponse 200**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Jean Dupont",
    "status": "approved",
    "updated_at": "2025-12-10T22:45:00Z",
    "...": "..."
  }
}
```

**Erreurs**:
- `404`: Artiste non trouvé
- `500`: Erreur serveur

---

### 6. Rejeter un Artiste

**PATCH** `/api/artists/:id/reject`

Change le statut en `rejected` et log l'action `rejected` avec raison.

**Body (JSON, optionnel)**:
```json
{
  "reason": "Profil incomplet"
}
```

**Réponse 200**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Jean Dupont",
    "status": "rejected",
    "updated_at": "2025-12-10T22:50:00Z",
    "...": "..."
  }
}
```

**Erreurs**:
- `404`: Artiste non trouvé
- `500`: Erreur serveur

---

### 7. Supprimer un Artiste

**DELETE** `/api/artists/:id`

Supprime un artiste et log l'action `deleted`.

⚠️ **Pas de JSON body** conformément à PostgREST!

**Réponse 200**:
```json
{
  "success": true,
  "message": "Artiste supprimé"
}
```

**Erreurs**:
- `404`: Artiste non trouvé
- `500`: Erreur serveur

---

### 8. Historique des Actions

**GET** `/api/artists/:id/actions`

Récupère l'historique des actions pour un artiste, **trié par `action_date` DESC**.

**Query Parameters**:
- `limit` (défaut: 50, max: 200): Nombre de résultats
- `offset` (défaut: 0): Décalage pour pagination

**Exemple**:
```
GET /api/artists/1/actions?limit=20&offset=0
```

**Réponse 200**:
```json
{
  "success": true,
  "data": [
    {
      "id": 5,
      "artist_id": 1,
      "action": "approved",
      "action_date": "2025-12-10T22:45:00Z",
      "performed_by": "admin",
      "details": "Artiste Jean Dupont approuvé",
      "created_at": "2025-12-10T22:45:01Z"
    },
    {
      "id": 4,
      "artist_id": 1,
      "action": "updated",
      "action_date": "2025-12-10T22:40:00Z",
      "performed_by": "system",
      "details": "Champs mis à jour: name, price, bio",
      "created_at": "2025-12-10T22:40:01Z"
    },
    {
      "id": 1,
      "artist_id": 1,
      "action": "created",
      "action_date": "2025-12-10T22:30:00Z",
      "performed_by": "system",
      "details": "Artiste Jean Dupont créé",
      "created_at": "2025-12-10T22:30:01Z"
    }
  ],
  "count": 3,
  "limit": 20,
  "offset": 0
}
```

**Erreurs**:
- `400`: Paramètres invalides
- `500`: Erreur serveur

---

## 🔧 Gestion d'Erreurs PostgREST

Le client Supabase gère automatiquement les erreurs suivantes:

### Erreur 400 - Bad Request
Payload invalide ou données manquantes.
```json
{
  "error": "Payload invalide: Missing required field 'email'"
}
```

### Erreur 404 - Not Found
Ressource inexistante.
```json
{
  "error": "Artiste non trouvé"
}
```

### Erreur PGRST204 - Colonne Inexistante
Tentative d'accès à une colonne qui n'existe pas.
```json
{
  "error": "Colonne inexistante: unknown_column"
}
```

### Erreur PGRST205 - Table Inexistante
Tentative d'accès à une table qui n'existe pas.
```json
{
  "error": "Table inexistante: unknown_table"
}
```

---

## 🔄 Synchronisation Dashboard

### Propagation des Changements

Lorsque le Dashboard modifie un artiste (nom, email, prix, statut), la synchronisation se fait via:

1. **Polling GET**: Le site vitrine rafraîchit périodiquement
2. **Webhook**: Le Dashboard envoie un webhook au site vitrine
3. **Supabase Realtime** (optionnel): Écoute des changements en temps réel

### Webhook Handler (à implémenter)

```python
@app.route('/webhook/dashboard', methods=['POST'])
def dashboard_webhook():
    # Valider la signature
    signature = request.headers.get('X-Dashboard-Signature')
    if not validate_signature(signature, request.data):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Traiter le payload
    data = request.get_json()
    event_type = data.get('event')
    artist_id = data.get('artist_id')
    
    if event_type == 'artist.updated':
        # Rafraîchir le cache de l'artiste
        refresh_artist_cache(artist_id)
    
    return jsonify({'received': True}), 200
```

---

## 🛡️ Sécurité et Auth

### Clés API

- **ANON_KEY**: Utilisée pour lectures publiques (GET)
- **SERVICE_KEY**: Utilisée pour opérations admin (POST, PATCH, DELETE)

### Règles de Sécurité

✅ **À faire**:
- Utiliser ANON_KEY pour GET public
- Utiliser SERVICE_KEY pour opérations admin (côté serveur)
- Valider tous les inputs
- Logger toutes les opérations sensibles

❌ **À ne JAMAIS faire**:
- Exposer SERVICE_KEY au navigateur
- Désactiver la validation des inputs
- Ignorer les erreurs PostgREST

---

## 🚀 Robustesse

### Retry Automatique

Le client Supabase implémente un retry exponentiel (3 tentatives max):
- 1ère tentative: immédiate
- 2ème tentative: après 1s
- 3ème tentative: après 2s

### Timeout

Toutes les requêtes ont un timeout de 10 secondes.

### Nettoyage des Données

Les champs `None` sont automatiquement retirés avant l'insertion/mise à jour.

---

## 📝 Exemple Complet

### Flux Complet: Création → Modification → Approbation

```bash
# 1. Créer un artiste
curl -X POST http://localhost:5000/api/artists \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jean Dupont",
    "email": "jean@example.com",
    "price": 550.00
  }'
# Réponse: {"success": true, "data": {"id": 1, "status": "pending", ...}}

# 2. Lire l'artiste
curl http://localhost:5000/api/artists/1
# Réponse: {"success": true, "data": {"id": 1, "name": "Jean Dupont", ...}}

# 3. Mettre à jour
curl -X PATCH http://localhost:5000/api/artists/1 \
  -H "Content-Type: application/json" \
  -d '{
    "price": 600.00,
    "bio": "Nouvelle bio"
  }'
# Réponse: {"success": true, "data": {"id": 1, "price": 600.00, ...}}

# 4. Approuver
curl -X PATCH http://localhost:5000/api/artists/1/approve
# Réponse: {"success": true, "data": {"id": 1, "status": "approved", ...}}

# 5. Voir l'historique
curl http://localhost:5000/api/artists/1/actions
# Réponse: {"success": true, "data": [{"action": "approved", ...}, ...]}
```

---

## 🧪 Tests

Exécuter la suite de tests complète:

```bash
# Définir les variables d'environnement
export SUPABASE_URL='https://xxxxx.supabase.co'
export SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
export SUPABASE_SERVICE_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'

# Lancer les tests
python test_artists_api.py
```

Les tests couvrent:
- ✅ CREATE - Insertion avec retour complet
- ✅ READ - GET avec toutes colonnes
- ✅ UPDATE - Modification et propagation
- ✅ APPROVE/REJECT - Mise à jour statut + log
- ✅ DELETE - Suppression (200 ou 404)
- ✅ ACTIONS - Tri par action_date
- ✅ ERREURS - 400, 404, PGRST204/PGRST205
- ✅ HEADERS - Présents sur chaque requête
- ✅ PAGINATION - Cohérente

---

## 📦 Initialisation

### 1. Créer les Tables

```bash
# Définir l'URL de connexion PostgreSQL
export SUPABASE_DB_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'

# Exécuter le script d'initialisation
python init_artist_tables.py
```

Ce script crée:
- Table `template_artists`
- Table `artworks_artist_actions`
- Indexes de performance
- Trigger auto-update `updated_at`

### 2. Vérifier la Configuration

```bash
# Tester la connexion
python -c "from supabase_client import get_public_client; print('✅ Connexion OK')"
```

---

## 📞 Support

Pour toute question ou problème:
1. Vérifiez les logs: `logger.info()` et `logger.error()`
2. Testez avec: `python test_artists_api.py`
3. Consultez la documentation Supabase: [supabase.com/docs](https://supabase.com/docs)

---

**Version**: 1.0  
**Date**: 10 décembre 2025  
**Statut**: ✅ Production ready
