# 🎯 Démarrage Rapide - API Artistes Supabase

Guide ultra-rapide pour lancer l'API de gestion des artistes.

---

## ⚡ En 4 Étapes

### 1️⃣ Initialiser la Base de Données

```bash
# Définir l'URL PostgreSQL Supabase
export SUPABASE_DB_URL='postgresql://postgres:VOTRE_PASSWORD@db.xxxxx.supabase.co:5432/postgres'

# Créer les tables
python init_artist_tables.py
```

**Résultat**: Tables `template_artists` et `artworks_artist_actions` créées avec indexes.

---

### 2️⃣ Configurer l'Environnement

```bash
# Copier l'exemple
cp .env.example .env

# Éditer .env et remplir ces 3 variables OBLIGATOIRES:
# SUPABASE_URL=https://xxxxx.supabase.co
# SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

nano .env
```

**Où trouver les clés?**
1. Allez sur [app.supabase.com](https://app.supabase.com)
2. Sélectionnez votre projet
3. Settings > API > Project API keys
   - `anon public` → SUPABASE_ANON_KEY
   - `service_role` → SUPABASE_SERVICE_KEY
4. Settings > API > Config > URL → SUPABASE_URL

---

### 3️⃣ Tester

```bash
# Charger les variables
source .env  # ou export SUPABASE_URL=... etc.

# Tester l'API artistes
python test_artists_api.py

# Tester les webhooks (optionnel)
python test_webhooks.py
```

**Résultat attendu**: 19 tests passent (ou mode mock si pas de connexion réelle).

---

### 4️⃣ Lancer

```bash
# Développement
python app.py

# Production
gunicorn app:app --workers 4 --bind 0.0.0.0:5000
```

**Test rapide**:
```bash
curl http://localhost:5000/webhook/dashboard/ping
# Réponse: {"ok": true, "status": "active"}
```

---

## 📋 Endpoints Disponibles

### Artistes

```bash
# Créer un artiste
curl -X POST http://localhost:5000/api/artists \
  -H "Content-Type: application/json" \
  -d '{"name": "Jean Dupont", "email": "jean@example.com", "price": 550}'

# Lire un artiste
curl http://localhost:5000/api/artists/1

# Lister les artistes
curl http://localhost:5000/api/artists?limit=10&status=approved

# Mettre à jour
curl -X PATCH http://localhost:5000/api/artists/1 \
  -H "Content-Type: application/json" \
  -d '{"price": 600}'

# Approuver
curl -X PATCH http://localhost:5000/api/artists/1/approve

# Rejeter
curl -X PATCH http://localhost:5000/api/artists/1/reject \
  -H "Content-Type: application/json" \
  -d '{"reason": "Profil incomplet"}'

# Supprimer
curl -X DELETE http://localhost:5000/api/artists/1

# Historique actions
curl http://localhost:5000/api/artists/1/actions
```

### Webhooks (Dashboard → Template)

```bash
# Ping
curl http://localhost:5000/webhook/dashboard/ping

# Test webhook (avec signature)
# Voir test_webhooks.py pour exemples complets
```

---

## 🔧 Variables d'Environnement

### Obligatoires

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Optionnelles

```bash
# Pour webhooks Dashboard
DASHBOARD_WEBHOOK_SECRET=secret_partagé_2025

# Mode dev webhook (⚠️ DEV UNIQUEMENT!)
WEBHOOK_DEV_MODE=true

# URL du dashboard central
DASHBOARD_URL=https://admin.artworksdigital.fr
```

---

## 🚨 Dépannage Rapide

### "SUPABASE_URL non définie"
```bash
# Vérifier que la variable est chargée
echo $SUPABASE_URL

# Si vide, charger depuis .env
source .env
# ou export directement
export SUPABASE_URL='https://xxxxx.supabase.co'
```

### "Signature invalide" (webhooks)
```bash
# En développement, activer mode dev
export WEBHOOK_DEV_MODE=true

# En production, définir le secret
export DASHBOARD_WEBHOOK_SECRET='secret_partagé'
```

### "Table template_artists does not exist"
```bash
# Relancer l'initialisation
python init_artist_tables.py
```

### Tests échouent
```bash
# Mode mock (sans connexion Supabase)
unset SUPABASE_URL
python test_artists_api.py

# Avec connexion réelle
export SUPABASE_URL='https://xxxxx.supabase.co'
export SUPABASE_ANON_KEY='...'
export SUPABASE_SERVICE_KEY='...'
python test_artists_api.py
```

---

## 📚 Documentation Complète

- **ARTISTS_API_DOCUMENTATION.md**: Guide API complet (13KB)
- **SUPABASE_AUDIT_SUMMARY.md**: Résumé audit (12KB)
- **README**: Guide utilisateur général

---

## ✅ Checklist Déploiement Production

- [ ] Tables Supabase créées (`init_artist_tables.py`)
- [ ] Variables d'environnement définies (SUPABASE_URL, keys)
- [ ] Tests passent (`python test_artists_api.py`)
- [ ] HTTPS activé
- [ ] DASHBOARD_WEBHOOK_SECRET défini (pas WEBHOOK_DEV_MODE!)
- [ ] Rate limiting configuré (recommandé)
- [ ] Monitoring logs actif

---

## 🎉 C'est Tout!

Votre API artistes est prête. Pour plus de détails:
- Voir **ARTISTS_API_DOCUMENTATION.md**
- Consulter **SUPABASE_AUDIT_SUMMARY.md**

---

**Besoin d'aide?** Consultez les logs avec:
```bash
# Flask dev
python app.py  # Logs visibles directement

# Gunicorn production
gunicorn app:app --log-level info --access-logfile - --error-logfile -
```
