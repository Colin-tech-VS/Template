# 🚀 Guide de Déploiement sur Render avec PostgreSQL

## 📋 Prérequis

- Un compte Render (https://render.com)
- Ce projet Flask avec support SQLite/PostgreSQL
- Les données locales dans `paintings.db`

## 🔧 Étapes de Déploiement

### 1. Créer une Base PostgreSQL sur Render

1. Connectez-vous à Render
2. Cliquez sur **"New +"** → **"PostgreSQL"**
3. Configurez :
   - **Name**: `jb-art-database` (ou autre nom)
   - **Database**: `jb_art_db`
   - **User**: (généré automatiquement)
   - **Region**: Choisissez le plus proche
   - **Plan**: Free (pour commencer)
4. Cliquez sur **"Create Database"**
5. **Notez l'URL de connexion** (Internal Database URL)

### 2. Migrer les Données SQLite → PostgreSQL

Sur votre machine locale :

```bash
# Installer les dépendances
pip install psycopg2-binary

# Définir l'URL PostgreSQL de Render
export DATABASE_URL="postgresql://user:pass@host/database"
# Remplacez par l'URL Internal Database URL de Render

# Exécuter la migration
python migrate_to_postgres.py
```

Le script va :
- ✅ Créer toutes les tables dans PostgreSQL
- ✅ Transférer toutes vos données (peintures, commandes, utilisateurs, etc.)
- ✅ Adapter automatiquement le schéma SQLite → PostgreSQL

### 3. Créer le Web Service sur Render

1. Sur Render, cliquez sur **"New +"** → **"Web Service"**
2. Connectez votre repository GitHub
3. Configurez :
   - **Name**: `jb-art-website`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free (pour commencer)

### 4. Configurer les Variables d'Environnement

Dans les **Environment Variables** du Web Service :

```
DATABASE_URL = postgresql://user:pass@host/database
(Copiez l'Internal Database URL de votre base PostgreSQL)

SECRET_KEY = votre_cle_secrete_aleatoire_longue
(Générez une clé secrète forte)
```

**Optionnel** : Si vous avez des clés API qui ne sont pas dans la table `settings` :
```
STRIPE_SECRET_KEY = sk_live_...
SMTP_PASSWORD = ...
```

### 5. Déployer

1. Cliquez sur **"Create Web Service"**
2. Render va :
   - Cloner votre code
   - Installer les dépendances
   - Démarrer l'application
3. Votre site sera accessible sur : `https://jb-art-website.onrender.com`

## 🔄 Fonctionnement Automatique

Le code détecte automatiquement l'environnement :

- **En local** (sans `DATABASE_URL`) → Utilise SQLite (`paintings.db`)
- **Sur Render** (avec `DATABASE_URL`) → Utilise PostgreSQL

Aucun changement de code nécessaire ! 🎉

## 📁 Structure des Fichiers

```
Projet_JB/
├── app.py                      # Application Flask principale
├── database.py                 # Module de gestion BDD (SQLite + PostgreSQL)
├── migrate_to_postgres.py      # Script de migration SQLite → PostgreSQL
├── requirements.txt            # Dépendances Python (avec psycopg2-binary)
├── .env.example                # Exemple de variables d'environnement
├── .gitignore                  # Fichiers à ignorer dans Git
├── paintings.db                # Base SQLite (local uniquement, non commitée)
└── README_DEPLOYMENT.md        # Ce fichier
```

## 🧪 Tester en Local

Avant de déployer, testez que SQLite fonctionne toujours :

```bash
# Sans DATABASE_URL, utilise SQLite
python app.py

# Avec DATABASE_URL, utilise PostgreSQL
export DATABASE_URL="postgresql://..."
python app.py
```

## 🐛 Dépannage

### Erreur "relation does not exist"
Les tables n'ont pas été créées. Relancez `migrate_to_postgres.py`.

### Erreur de connexion PostgreSQL
Vérifiez que :
- L'URL `DATABASE_URL` est correcte
- La base PostgreSQL est bien démarrée sur Render
- Vous utilisez l'**Internal Database URL** (pas l'External)

### Les données n'apparaissent pas
- Vérifiez que la migration a bien fonctionné
- Connectez-vous à PostgreSQL avec un client (ex: DBeaver) pour vérifier

### L'application ne démarre pas
- Vérifiez les logs sur Render
- Assurez-vous que `gunicorn` est dans `requirements.txt`
- Vérifiez que `DATABASE_URL` est définie

## 📊 Tables Migrées

Le script migre automatiquement :
- ✅ `users` - Utilisateurs
- ✅ `paintings` - Peintures
- ✅ `orders` - Commandes
- ✅ `order_items` - Détails des commandes
- ✅ `exhibitions` - Expositions
- ✅ `custom_requests` - Demandes sur mesure
- ✅ `notifications` - Notifications
- ✅ `settings` - Paramètres (clés API, SMTP, etc.)
- ✅ `favorites` - Favoris

## 🔐 Sécurité

⚠️ **Important** :
- Ne commitez JAMAIS le fichier `.env` sur Git
- Ne commitez JAMAIS `paintings.db` (données sensibles)
- Utilisez une `SECRET_KEY` forte en production
- Sur Render, utilisez l'**Internal Database URL** (plus sécurisé)

## 💡 Commandes Utiles

```bash
# Installer les dépendances
pip install -r requirements.txt

# Créer les tables (app.py le fait automatiquement au démarrage)
python -c "from database import init_database; init_database()"

# Vérifier la connexion
python -c "from database import get_db, IS_POSTGRES; print('Mode:', 'PostgreSQL' if IS_POSTGRES else 'SQLite')"

# Exporter les données SQLite avant migration (backup)
sqlite3 paintings.db .dump > backup.sql
```

## 📞 Support

En cas de problème :
1. Vérifiez les logs sur Render
2. Testez en local avec PostgreSQL (définissez `DATABASE_URL`)
3. Vérifiez que toutes les dépendances sont installées

---

**Bon déploiement ! 🚀**
